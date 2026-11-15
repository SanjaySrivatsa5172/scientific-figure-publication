#!/usr/bin/env python3
"""figure_qa: release gate for publication figures.

Two entry points:

1. Live matplotlib figure (most thorough; run before export):
       from figure_qa import audit_figure, report
       report(audit_figure(fig, target="jacc", column="single"))

2. Exported files (PDF, SVG, EPS, PNG, TIFF, JPEG) from the command line:
       python figure_qa.py Fig1.pdf Fig1.png --target nature --column double
       python figure_qa.py panels/*.svg --same-size
       python figure_qa.py Fig1.png --cvd-preview qa/Fig1_cvd.png
       python figure_qa.py --portability figure_sources/fig1.py
       python figure_qa.py --render-doc manuscript.docx --out qa/pages

Severity: FAIL blocks delivery; WARN needs a fix or a stated reason; REVIEW is
a human check the script cannot decide; INFO is context. Exit code 2 when any
FAIL (or any WARN with --strict).

Consolidates and extends checks from polish-sci-figures (text collisions,
grid alignment, SVG editability/canvas/accessibility, source portability,
document page rendering) and Scientific-Figure-Design (final-size type,
stroke, hue limits). Additions: effective size after journal scaling, PDF
font embedding and Type 3 detection, raster DPI at final width, truncated
bar axes, forbidden colormaps, CIEDE2000 distinguishability under simulated
colour-vision deficiency, text-over-data detection, CVD preview montage.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import warnings
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # QA runs from the skill; delivered sources must not do this
import pubfig as pf  # noqa: E402

MM = 25.4


@dataclass
class Finding:
    severity: str   # FAIL | WARN | REVIEW | INFO
    code: str
    message: str
    where: str = ""


def _f(sev, code, msg, where=""):
    return Finding(sev, code, msg, where)


# ---------------------------------------------------------------------------
# Live figure audit
# ---------------------------------------------------------------------------
_TOKEN_RULES = [
    (re.compile(r"\b(IC|EC|ED|LD)50\b"), "use subscript (IC₅₀) via pubfig.notation()"),
    (re.compile(r"\blog(2|10)\b(?![₀-₉])"), "use log₂/log₁₀ via pubfig.notation()"),
    (re.compile(r"\b(CO|O)2\b"), "use subscript ₂"),
    (re.compile(r"\d\s*[xX]\s*10\^?-?\d"), "use × 10⁻ⁿ notation, not x or ^"),
    (re.compile(r"\^-?\d"), "caret exponent: use superscript"),
    (re.compile(r"(?<![A-Za-z])p\s*[<=>]\s*0?\.\d"), "lowercase p: most styles use italic capital P (check house style)"),
    (re.compile(r"(?<![\w.])-\d"), "ASCII hyphen as minus: use U+2212 (pubfig.MINUS)"),
    (re.compile(r"\+/-"), "use ± not +/-"),
    (re.compile(r"\bmicro(?:meter|gram|liter|litre)s?\b|\bum\b|\bug\b"), "use µ (µm, µg, µL)"),
]


def _all_axes(fig):
    """Figure axes plus their inset (child) axes, e.g. an embedded forest plot."""
    out = []

    def walk(ax):
        out.append(ax)
        for ch in getattr(ax, "child_axes", []):
            walk(ch)
    for ax in fig.axes:
        walk(ax)
    return out


def _fig_frac(fig, ax):
    """Axes box in root-figure fractions (subfigure positions are relative to the subfigure)."""
    return fig.transFigure.inverted().transform_bbox(ax.get_window_extent())


def _texts(fig, renderer):
    """Visible, actually drawn text: in-range tick labels plus every other Text."""
    from matplotlib.text import Text
    out, all_ticks = [], set()
    for ax in _all_axes(fig):
        for axis in (ax.xaxis, ax.yaxis):
            labels = axis.get_ticklabels(which="both")
            all_ticks.update(id(t) for t in labels)
            if not ax.axison or not axis.get_visible():
                continue
            lo, hi = sorted(axis.get_view_interval())
            span = (hi - lo) * 1e-6
            for t in labels:
                pos = t.get_position()[0 if axis is ax.xaxis else 1]
                if t.get_visible() and t.get_text().strip() and lo - span <= pos <= hi + span:
                    out.append(("tick", t))
    for t in fig.findobj(Text):
        if id(t) in all_ticks or not t.get_visible() or not t.get_text().strip():
            continue
        out.append(("text", t))
    return out


def _categorical(labels) -> bool:
    txt = [t.get_text().replace("−", "-").replace(",", "") for t in labels if t.get_text().strip()]
    if not txt:
        return False
    def num(s):
        try:
            float(s.strip("%"))
            return True
        except ValueError:
            return False
    return not all(num(s) for s in txt)


def _data_points_px(ax, max_points: int = 20000) -> np.ndarray:
    from matplotlib.lines import Line2D
    from matplotlib.collections import PathCollection
    pts = []
    for ln in ax.get_lines():
        if not ln.get_visible() or ln.get_linestyle() in ("None", "none", "") and ln.get_marker() in (None, "None", "none", ""):
            continue
        xy = np.column_stack([np.asarray(ln.get_xdata(), float), np.asarray(ln.get_ydata(), float)])
        if xy.size == 0:
            continue
        ds = ln.get_drawstyle()
        if ds.startswith("steps") and len(xy) > 1:   # sample the drawn staircase, not the diagonal
            from matplotlib import cbook
            fn = {"steps-pre": cbook.pts_to_prestep, "steps": cbook.pts_to_prestep,
                  "steps-post": cbook.pts_to_poststep, "steps-mid": cbook.pts_to_midstep}.get(ds)
            if fn is not None:
                sx, sy = fn(xy[:, 0], xy[:, 1])
                xy = np.column_stack([sx, sy])
        px = ln.get_transform().transform(xy)
        px = px[np.isfinite(px).all(1)]
        if ln.get_linestyle() not in ("None", "none", "") and len(px) > 1:
            seg = np.diff(px, axis=0)
            lens = np.hypot(seg[:, 0], seg[:, 1])
            k = np.clip(np.ceil(lens / 3.0), 1, 400).astype(int)        # one sample every ~3 px
            idx = np.repeat(np.arange(len(seg)), k)
            frac = np.concatenate([np.arange(m) / m for m in k])
            px = np.vstack([px[:-1][idx] + seg[idx] * frac[:, None], px[-1:]])
            if len(px) > max_points:
                px = px[np.linspace(0, len(px) - 1, max_points).astype(int)]
        pts.append(px)
    for c in ax.collections:
        if isinstance(c, PathCollection) and c.get_visible():
            off = c.get_offsets()
            if len(off):
                pts.append(c.get_offset_transform().transform(off))
    if not pts:
        return np.empty((0, 2))
    allp = np.vstack(pts)
    if len(allp) > max_points:
        allp = allp[np.random.default_rng(0).choice(len(allp), max_points, replace=False)]
    return allp


def audit_figure(fig, *, target: str | None = None, column: str | float | None = None,
                 allow_titles: bool = True, allow_suptitle: bool = False, require_aligned_grid: bool = True,
                 required_font: str | None = None, min_pt: float | None = None, max_pt: float | None = None,
                 min_line_pt: float | None = None, expect_panel_labels: bool | None = None) -> list[Finding]:
    """Audit a live matplotlib figure at its final physical size.

    If the figure is not drawn at the target width, every size is scaled to
    what it will be after the journal shrinks or enlarges it, and that scale
    is reported. Thresholds default to the preset (target) or the spec the
    figure was created with.
    """
    import matplotlib as mpl
    from matplotlib import font_manager
    from matplotlib.container import BarContainer, ErrorbarContainer
    from matplotlib.patches import Wedge

    F: list[Finding] = []
    pf.settle(fig)          # audit the placements save() will write
    spec = getattr(fig, "_pubfig_spec", None)
    preset = pf.preset(target) if target else (spec.preset if spec else pf.GENERIC)
    w_mm, h_mm = (v * MM for v in fig.get_size_inches())
    target_w = None
    if column is not None:
        target_w = float(column) if isinstance(column, (int, float)) else preset["widths_mm"].get(column)
    elif spec is not None and target is None:
        target_w = spec.width_mm
    scale = (target_w / w_mm) if target_w else 1.0
    if target_w and abs(scale - 1) > 0.01:
        F.append(_f("WARN", "SCALED_OUTPUT", f"canvas is {w_mm:.1f} mm wide; placing it at {target_w:.1f} mm scales "
                    f"every font and line by {scale:.2f}. Redraw at final size instead of rescaling."))
    if target_w is None:
        widths = [v for v in preset["widths_mm"].values() if v]
        if widths and min(abs(w_mm - v) for v in widths) > 1.0:
            F.append(_f("WARN", "NONSTANDARD_WIDTH", f"width {w_mm:.1f} mm matches none of {preset['name']} widths "
                        f"{sorted(widths)} mm; the publisher will rescale it"))
    if preset.get("max_height_mm") and h_mm * scale > preset["max_height_mm"] + 0.5:
        F.append(_f("FAIL", "TOO_TALL", f"height {h_mm * scale:.1f} mm exceeds {preset['max_height_mm']} mm"))
    min_pt = min_pt or preset["font"]["min_pt"]
    max_pt = max_pt or preset["font"]["max_pt"]
    min_line = min_line_pt or preset["lines"]["minimum"]
    required_font = required_font or preset["font"]["family"]

    # draw, catching missing glyphs
    missing = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig.canvas.draw()
    for w in caught:
        if "missing from" in str(w.message) and "Glyph" in str(w.message):
            missing.append(str(w.message))
    for m in sorted(set(missing))[:5]:
        F.append(_f("FAIL", "MISSING_GLYPH", m))
    renderer = fig.canvas.get_renderer()
    fbox = fig.bbox
    texts = _texts(fig, renderer)

    # typography
    sizes, fonts = {}, {}
    for kind, t in texts:
        size = t.get_fontsize() * scale
        is_panel = getattr(t, "_pubfig_panel_label", False)
        sizes.setdefault(round(size * 2) / 2, []).append(t.get_text()[:30])
        if size < min_pt - 1e-6:
            F.append(_f("FAIL", "TEXT_TOO_SMALL", f"{size:.1f} pt < {min_pt:g} pt: {t.get_text()[:40]!r}"))
        if max_pt and size > max_pt + 1e-6 and not is_panel:
            F.append(_f("WARN", "TEXT_TOO_LARGE", f"{size:.1f} pt > {max_pt:g} pt: {t.get_text()[:40]!r}"))
        try:
            path = font_manager.findfont(t.get_fontproperties(), fallback_to_default=True)
            fonts.setdefault(font_manager.FontProperties(fname=path).get_name(), 0)
            fonts[font_manager.FontProperties(fname=path).get_name()] += 1
        except Exception:
            pass
    non_panel_sizes = {s for s, v in sizes.items()}
    if len(non_panel_sizes) > 4:
        F.append(_f("WARN", "TOO_MANY_TYPE_SIZES", f"{len(non_panel_sizes)} type sizes {sorted(non_panel_sizes)} pt; "
                    "use at most 3 plus panel labels"))
    fams = set(fonts)
    if len(fams) > 1:
        F.append(_f("WARN", "MIXED_FONTS", f"text renders in several families: {fonts}"))
    if required_font and fams and required_font.lower() not in {f.lower() for f in fams}:
        sub_ok = any(f.lower() in pf.METRIC_COMPATIBLE.get(required_font.lower(), set()) for f in fams)
        F.append(_f("WARN" if sub_ok else "FAIL", "FONT_NOT_REQUIRED",
                    f"required {required_font!r}; rendered {sorted(fams)}" +
                    (" (metric-compatible substitute: layout is right, install the real font before final export)" if sub_ok else "")))

    # clipping and collisions
    boxes = []
    for kind, t in texts:
        bb = t.get_window_extent(renderer)
        if bb.x0 < fbox.x0 - 1 or bb.y0 < fbox.y0 - 1 or bb.x1 > fbox.x1 + 1 or bb.y1 > fbox.y1 + 1:
            F.append(_f("FAIL", "TEXT_CLIPPED", f"text crosses the canvas edge: {t.get_text()[:40]!r}"))
        boxes.append((t, bb.padded(-1)))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if a[1].width <= 0 or b[1].width <= 0:
                continue
            if a[1].overlaps(b[1]):
                F.append(_f("FAIL", "TEXT_COLLISION", f"{a[0].get_text()[:30]!r} overlaps {b[0].get_text()[:30]!r}"))
    # text and legend over data
    for ax in _all_axes(fig):
        pts = _data_points_px(ax)
        if not len(pts):
            continue
        abox = ax.get_window_extent(renderer)
        cand = []
        for k_, t in texts:
            if k_ != "text" or getattr(t, "_pubfig_panel_label", False):
                continue
            if t.axes is ax:
                cand.append(t)
            elif t.axes is None:   # e.g. rich_text runs inside an AnnotationBbox
                bb = t.get_window_extent(renderer)
                cx, cy = (bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2
                if abox.x0 < cx < abox.x1 and abox.y0 < cy < abox.y1:
                    cand.append(t)
        leg = ax.get_legend()
        items = [(t.get_text()[:30], t.get_window_extent(renderer).padded(-1)) for t in cand]
        if leg is not None and leg.get_visible():
            items.append(("legend", leg.get_window_extent(renderer).padded(-2)))
        for name, bb in items:
            inside = ((pts[:, 0] > bb.x0) & (pts[:, 0] < bb.x1) & (pts[:, 1] > bb.y0) & (pts[:, 1] < bb.y1)).sum()
            if inside:
                F.append(_f("WARN", "TEXT_OVER_DATA", f"{name!r} covers {inside} plotted point(s)/segment sample(s); "
                            "move it to an empty region, into the legend text, or enlarge the panel"))

    # strokes
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    thin = set()
    for art in fig.findobj(Line2D):
        if art.get_visible() and art.get_linestyle() not in ("None", "none", "") and 0 < art.get_linewidth() * scale < min_line - 1e-6:
            thin.add(round(art.get_linewidth() * scale, 3))
    for ax in _all_axes(fig):
        for sp in ax.spines.values():
            if sp.get_visible() and 0 < sp.get_linewidth() * scale < min_line - 1e-6:
                thin.add(round(sp.get_linewidth() * scale, 3))
    for p in fig.findobj(Patch):
        ec = p.get_edgecolor()
        if p.get_visible() and ec is not None and len(ec) == 4 and ec[3] > 0 and 0 < p.get_linewidth() * scale < min_line - 1e-6:
            thin.add(round(p.get_linewidth() * scale, 3))
    from matplotlib.collections import Collection
    from matplotlib.collections import PathCollection
    for c in fig.findobj(Collection):   # marker outlines, error-bar segments, heatmap cell edges
        if not c.get_visible() or not len(c.get_paths()):
            continue                     # e.g. a colorbar's empty divider collection draws nothing
        if isinstance(c, PathCollection) and not len(c.get_offsets()):
            continue
        try:
            ecs = np.atleast_2d(c.get_edgecolor())
            lws = np.atleast_1d(c.get_linewidth())
        except Exception:
            continue
        if ecs.size == 0 or not (ecs[:, -1] > 0).any():
            continue
        for lw in lws:
            if 0 < lw * scale < min_line - 1e-6:
                thin.add(round(float(lw) * scale, 3))
    for ax in _all_axes(fig):             # tick marks (major and minor)
        if not ax.axison:
            continue
        for axis in (ax.xaxis, ax.yaxis):
            if not axis.get_visible():
                continue
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                tl = tick.tick1line
                if tl.get_visible() and tl.get_markersize() > 0 and 0 < tl.get_markeredgewidth() * scale < min_line - 1e-6:
                    thin.add(round(tl.get_markeredgewidth() * scale, 3))
    if thin:
        F.append(_f("FAIL", "LINE_TOO_THIN", f"stroke widths {sorted(thin)} pt below {min_line} pt disappear in print"))

    # per-axes chart integrity
    for k, ax in enumerate(_all_axes(fig)):
        where = f"axes {k + 1}"
        km = getattr(ax, "_pubfig_km", None)
        if km is not None and km.get("ci_range"):
            y0, y1 = sorted(ax.get_ylim())
            tol = (y1 - y0) * 0.002
            if km["ci_range"][1] > y1 + tol or km["ci_range"][0] < y0 - tol:
                F.append(_f("WARN", "KM_CI_CLIPPED", f"95% CI reaches {km['ci_range'][0]:.3g} to {km['ci_range'][1]:.3g} "
                            f"but the y axis shows {y0:.3g} to {y1:.3g}: widen ylim or state the clipping in the legend", where))
        if ax.name == "3d":
            F.append(_f("FAIL", "THREE_D", "3D axes distort comparison; use 2D small multiples or contours", where))
        for art in ax.get_children():
            cmap = getattr(art, "get_cmap", lambda: None)()
            if cmap is not None and getattr(cmap, "name", "").lower().replace("_r", "") in pf.FORBIDDEN_CMAPS:
                F.append(_f("FAIL", "RAINBOW_CMAP", f"colormap {cmap.name!r} is not perceptually uniform", where))
        if any(isinstance(p, Wedge) for p in ax.patches) and ax.name != "polar":
            F.append(_f("WARN", "PIE_CHART", "pie/donut: angles are read poorly; use bars or a dot plot", where))
        bars = [c for c in ax.containers if isinstance(c, BarContainer)]
        if bars and ax.get_yscale() == "linear" and ax.get_xscale() == "linear":
            vertical = getattr(bars[0], "orientation", "vertical") == "vertical"
            lo, hi = sorted(ax.get_ylim() if vertical else ax.get_xlim())
            heights = np.concatenate([[r.get_height() if vertical else r.get_width() for r in c] for c in bars])
            if (heights >= 0).all() and lo > 1e-12:
                F.append(_f("FAIL", "TRUNCATED_BARS", f"bar axis starts at {lo:g}; bars encode length from zero. "
                            "Start at 0 or switch to a dot plot", where))
        elif bars:
            F.append(_f("WARN", "BARS_ON_LOG_SCALE", "bars on a log axis have no zero; use points", where))
        if any(isinstance(c, ErrorbarContainer) for c in ax.containers) and not hasattr(ax, "_pubfig_error_kind"):
            F.append(_f("REVIEW", "ERRORBARS_UNDEFINED", "error bars present: state SD, SEM, or 95% CI and n in the legend", where))
        if ax.get_title() and not allow_titles:
            F.append(_f("WARN", "PANEL_TITLE", f"panel title {ax.get_title()!r}: move to legend unless the journal uses panel titles", where))
        has_data = bool(ax.lines or ax.collections or ax.patches or ax.images)
        if has_data and ax.axison and ax.name == "rectilinear" and not getattr(ax, "_pubfig_heatmap", None):
            xl, yl = ax.get_xticklabels(), ax.get_yticklabels()
            if ax.xaxis.get_visible() and any(t.get_text() for t in xl) and not ax.get_xlabel() and not _categorical(xl):
                F.append(_f("REVIEW", "NO_XLABEL", "numeric x axis without a label (quantity and unit)", where))
            if ax.yaxis.get_visible() and any(t.get_text() for t in yl) and not ax.get_ylabel() and not _categorical(yl):
                F.append(_f("REVIEW", "NO_YLABEL", "numeric y axis without a label (quantity and unit)", where))
    # journal-specific chart rules (from the preset's verified instructions)
    F += _journal_rules(fig, preset)
    # twin axes
    pos = [tuple(np.round(_fig_frac(fig, ax).bounds, 3)) for ax in fig.axes]
    if len(pos) != len(set(pos)):
        F.append(_f("WARN", "DUAL_AXES", "two axes share one position (twinx/twiny): readers compare slopes across "
                    "unrelated scales; prefer aligned panels"))
    if (fig._suptitle is not None and fig._suptitle.get_text().strip() and not allow_suptitle
            and not getattr(fig._suptitle, "_pubfig_synthetic_tag", False)):
        F.append(_f("WARN", "FIGURE_TITLE", "figure title inside artwork: put it in the legend (manuscript mode)"))

    # colour distinguishability of series colours per axes
    from matplotlib.colors import to_hex
    for k, ax in enumerate(_all_axes(fig)):
        cols, styles = [], {}
        for ln in ax.get_lines():
            if ln.get_visible() and not ln.get_label().startswith("_child") and ln.get_linestyle() not in ("None", "none", "") or ln.get_marker() not in (None, "None", "none", ""):
                c = to_hex(ln.get_color())
                cols.append(c)
                styles.setdefault(c, set()).add((str(ln.get_linestyle()), str(ln.get_marker())))
        for c in ax.containers:
            if isinstance(c, BarContainer) and len(c):
                cols.append(to_hex(c[0].get_facecolor()))
        from matplotlib.collections import PathCollection
        for coll in ax.collections:
            # bands/areas next to lines are uncertainty tints, not series identity
            if ax.get_lines() and not isinstance(coll, PathCollection):
                continue
            try:
                fc = np.unique(np.round(coll.get_facecolor(), 3), axis=0)
                if 0 < len(fc) <= 8 and getattr(coll, "get_array", lambda: None)() is None:
                    cols.extend(to_hex(x) for x in fc if x[3] > 0)
            except Exception:
                pass
        neutral = {to_hex(c) for c in ("#000000", "#ffffff")}
        uniq = [c for c in dict.fromkeys(cols) if c not in neutral and _saturated(c)]
        uniq = [c for c in uniq if not any(c != o and _is_tint_of(c, o) for o in uniq)]
        if len(uniq) >= 2:
            rep = pf.check_colors(uniq)
            for prob in rep["problems"]:
                if prob.startswith("contrast"):
                    continue
                F.append(_f("WARN", "COLOR_SEPARATION", prob, f"axes {k + 1}"))

    # grid alignment (polish-sci-figures rule)
    if require_aligned_grid:
        main = [ax for ax in fig.axes if ax.get_label() != "<colorbar>" and ax.axison and ax.name == "rectilinear"]
        bbs = [_fig_frac(fig, ax) for ax in main]
        for i in range(len(bbs)):
            for j in range(i + 1, len(bbs)):
                a, b = bbs[i], bbs[j]
                same_row = abs((a.y0 + a.y1) / 2 - (b.y0 + b.y1) / 2) < 0.08 and abs(a.height - b.height) < 0.2
                if same_row and max(abs(a.y0 - b.y0), abs(a.y1 - b.y1)) > 0.015:
                    F.append(_f("WARN", "GRID_MISALIGNED", f"axes {i + 1} and {j + 1} share a row but not top/bottom edges"))
    # panel labels expected?
    data_axes = [ax for ax in _all_axes(fig) if ax.get_label() != "<colorbar>" and (ax.lines or ax.collections or ax.patches or ax.images)]
    labels = [t for t in fig.findobj(lambda a: getattr(a, "_pubfig_panel_label", False))]
    if expect_panel_labels is None:
        expect_panel_labels = len(data_axes) >= 2 and spec is not None and spec.mode == "manuscript"
    if expect_panel_labels and not labels:
        F.append(_f("REVIEW", "NO_PANEL_LABELS", f"{len(data_axes)} panels without panel labels; journals reference panels "
                    f"in the legend ({preset['panel']['style']!r} style for {preset['name']})"))
    # notation
    for kind, t in texts:
        if kind == "tick":
            continue
        s = t.get_text()
        for rx, advice in _TOKEN_RULES:
            if rx.search(s):
                F.append(_f("WARN", "NOTATION", f"{s[:40]!r}: {advice}"))
    # transparency and rasterization
    if pf._has_transparency(fig):
        F.append(_f("INFO", "TRANSPARENCY", "semi-transparent artists: fine in PDF/SVG; EPS and some print workflows "
                    "flatten them (pubfig.flatten_alpha or opaque tints)"))
    if any(getattr(a, "get_rasterized", lambda: False)() for a in fig.findobj()):
        F.append(_f("INFO", "RASTERIZED_LAYER", "some artists are rasterized inside vector output: not fully editable"))
    F.append(_f("INFO", "TYPE_SIZES", "type sizes after placement (pt): " + ", ".join(f"{s:g}" for s in sorted(sizes))))
    return _dedupe(F)


_KM_RULES = {
    "km_numbers_at_risk": "show numbers at risk under the x axis (risk_ax=)",
    "km_truncate_se_10pct": "truncate curves where the standard error exceeds 10% (JVS)",
    "km_truncate_below_10_at_risk": "truncate curves where fewer than 10 remain at risk (EJVES)",
    "km_y_from_zero": "start the y axis at 0 (EJVES)",
    "km_valid_se_lt_10pct_and_10_at_risk": "plot only while SE < 10% and >= 10 at risk (JEVT)",
    "km_no_ci_bands": "do not plot 95% CI bands (JEVT): ci=False",
}


def _journal_rules(fig, preset) -> list[Finding]:
    from matplotlib.container import BarContainer, ErrorbarContainer
    from matplotlib.patches import Wedge
    F, rules, name = [], set(preset.get("rules", [])), preset["name"]
    if not rules:
        return F
    data_axes = [ax for ax in _all_axes(fig) if ax.get_label() != "<colorbar>" and (ax.lines or ax.collections or ax.patches or ax.images)]
    for k, ax in enumerate(_all_axes(fig)):
        where = f"axes {k + 1}"
        bars = [c for c in ax.containers if isinstance(c, BarContainer)]
        if bars and "avoid_bar_graphs" in rules:
            F.append(_f("WARN", "JOURNAL_AVOID_BARS", f"{name}: instructions say to avoid bar graphs; show observations or estimates with CIs", where))
        if bars and "no_dynamite_plots" in rules and any(isinstance(c, ErrorbarContainer) for c in ax.containers):
            F.append(_f("FAIL", "JOURNAL_NO_DYNAMITE", f"{name}: column-with-error-bar plots are not accepted", where))
        if bars and "no_stacked_bars" in rules:
            if any(abs(getattr(r, "get_y", lambda: 0)()) > 1e-12 for c in bars for r in c):
                F.append(_f("FAIL", "JOURNAL_NO_STACKED_BARS", f"{name}: stacked bars are not accepted", where))
        if "no_pie" in rules and any(isinstance(p, Wedge) for p in ax.patches):
            F.append(_f("FAIL", "JOURNAL_NO_PIE", f"{name}: pie charts are not accepted", where))
        if "ratios_log_scale" in rules:
            lab = (ax.get_xlabel() + " " + ax.get_ylabel()).lower()
            if "ratio" in lab and "log" not in (ax.get_xscale(), ax.get_yscale()):
                F.append(_f("WARN", "JOURNAL_RATIO_LOG", f"{name}: ratio measures belong on a log scale", where))
        if "numeric_axes_include_zero" in rules and ax.name == "rectilinear" and ax.axison:
            for axis, lim, scale in ((ax.xaxis, ax.get_xlim(), ax.get_xscale()), (ax.yaxis, ax.get_ylim(), ax.get_yscale())):
                if scale == "linear" and axis.get_visible() and not _categorical(axis.get_ticklabels()) and not (min(lim) <= 0 <= max(lim)):
                    F.append(_f("WARN", "JOURNAL_AXIS_ZERO", f"{name}: numerical axes must include 0 (except log axes)", where))
        km = getattr(ax, "_pubfig_km", None)
        if km is not None:
            tr = km.get("truncation") or {}
            se_ok = tr.get("max_se") is not None and tr["max_se"] <= 0.10 + 1e-12
            risk_ok = tr.get("min_at_risk") is not None and tr["min_at_risk"] >= 10
            cut = [str(g) for g, v in (km.get("truncated") or {}).items() if v]
            how = f"curves shortened: {', '.join(cut)}" if cut else "no curve needed shortening"
            for r in sorted(rules & set(_KM_RULES)):
                if r == "km_no_ci_bands" and km.get("ci"):
                    F.append(_f("FAIL", "JOURNAL_KM_CI", f"{name}: {_KM_RULES[r]}", where))
                elif r == "km_y_from_zero" and ax.get_ylim()[0] > 1e-9:
                    F.append(_f("FAIL", "JOURNAL_KM_Y0", f"{name}: {_KM_RULES[r]}", where))
                elif r == "km_numbers_at_risk":
                    if not km.get("risk_table"):
                        F.append(_f("WARN", "JOURNAL_KM_RISK", f"{name}: {_KM_RULES[r]}", where))
                elif r in ("km_truncate_se_10pct", "km_truncate_below_10_at_risk", "km_valid_se_lt_10pct_and_10_at_risk"):
                    ok = {"km_truncate_se_10pct": se_ok, "km_truncate_below_10_at_risk": risk_ok,
                          "km_valid_se_lt_10pct_and_10_at_risk": se_ok and risk_ok}[r]
                    if ok:
                        F.append(_f("INFO", "JOURNAL_KM_TRUNCATION", f"{name}: rule applied ({how})", where))
                    else:
                        F.append(_f("WARN", "JOURNAL_KM_TRUNCATION", f"{name}: {_KM_RULES[r]}; km_plot(truncate='auto') applies it", where))
                elif r != "km_no_ci_bands" and r != "km_y_from_zero":
                    F.append(_f("REVIEW", "JOURNAL_KM_RULE", f"{name}: {_KM_RULES[r]}", where))
    for lim in (4, 6):
        if f"max_{lim}_panels" in rules and len(data_axes) > lim:
            F.append(_f("WARN", "JOURNAL_PANEL_LIMIT", f"{name}: at most {lim} panels ({len(data_axes)} found)"))
    kinds = {getattr(fig, "_pubfig_kind", None)} | {getattr(ax, "_pubfig_kind", None) for ax in fig.axes}
    kind = "forest" if "forest" in kinds else ("flow" if "flow" in kinds else None)
    if "forest_and_flow_printed_bw" in rules and kind in ("forest", "flow"):
        F.append(_f("REVIEW", "JOURNAL_PRINTED_BW", f"{name}: forest plots and trial profiles print in black and white; check the grayscale preview"))
    if "forest_raw_numbers_in_margins" in rules and kind == "forest":
        F.append(_f("REVIEW", "JOURNAL_FOREST_COUNTS", f"{name}: forest plots need raw numbers (events/n) in the margins"))
    if "black_white_not_gray" in rules:
        F.append(_f("REVIEW", "JOURNAL_BW", f"{name}: charts in black and white, not gray"))
    if "errorbars_both_directions" in rules and any(isinstance(c, ErrorbarContainer) for ax in _all_axes(fig) for c in ax.containers):
        F.append(_f("REVIEW", "JOURNAL_ERRORBARS", f"{name}: draw error bars in both directions"))
    return F


def check_legend_text(text: str, target: str = "generic", *, title: str | None = None) -> list[Finding]:
    """Check a figure legend against journal word limits and house style.

    Flags word limits stated by the journal, em dashes (the skill's manuscript
    register uses parentheses, semicolons, or colons instead), lowercase or
    non-italic P conventions that contradict the target style, and undefined
    error bars.
    """
    p = pf.preset(target)
    F = []
    text = re.sub(r"</?(?:i|em|b|strong|sup|sub)>", "", text)
    text = re.sub(r"(\*{1,2}|_{1,2})(?=\S)(.+?)(?<=\S)\1", r"\2", text)
    words = len(re.findall(r"\b\w[\w'-]*\b", text))
    rules = set(p.get("rules", []))
    for r in rules:
        m = re.fullmatch(r"legend_max_(\d+)_words", r)
        if m and words > int(m.group(1)):
            F.append(_f("FAIL", "LEGEND_TOO_LONG", f"{words} words > {m.group(1)} ({p['name']})"))
        m = re.fullmatch(r"legend_title_max_(\d+)_words", r)
        if m and title is not None and len(title.split()) > int(m.group(1)):
            F.append(_f("FAIL", "LEGEND_TITLE_TOO_LONG", f"title {len(title.split())} words > {m.group(1)} ({p['name']})"))
    if "\u2014" in text or " -- " in text:
        F.append(_f("WARN", "EM_DASH", "em dash in legend prose: use parentheses, a semicolon, or a colon"))
    st = pf.STATS_STYLES.get(p.get("stats", "ama"), pf.STATS_STYLES["ama"])
    sym = st["symbol"]
    other = "p" if sym == "P" else "P"
    if re.search(rf"(?<![A-Za-z]){other}\s*[<=>]\s*[0.·]", text):
        F.append(_f("WARN", "P_STYLE", f"{p['name']} style uses '{sym}' ({'italic' if st['italic'] else 'roman'}); found '{other}'"))
    if not st["leading_zero"] and re.search(rf"\b{sym}\s*[<=>]\s*0\.", text):
        F.append(_f("WARN", "P_LEADING_ZERO", "this style writes P values without a leading zero (P = .03)"))
    if st["leading_zero"] and re.search(rf"\b{sym}\s*[<=>]\s*\.\d", text):
        F.append(_f("WARN", "P_LEADING_ZERO", "this style writes P values with a leading zero (P = 0.03)"))
    if re.search(r"error bars|whiskers", text, re.I) and not re.search(r"\b(SD|SEM|SE|standard (deviation|error)|confidence interval|95% CI|IQR|interquartile|range)\b", text, re.I):
        F.append(_f("WARN", "ERRORBARS_UNDEFINED", "legend mentions error bars without defining them"))
    if p.get("stats") == "annals" and "\u00b1" in text:
        F.append(_f("WARN", "ANNALS_MEAN_SD", "Annals uses 'mean (SD)' rather than 'mean ± SD'"))
    F.append(_f("INFO", "LEGEND_WORDS", f"{words} words"))
    return F


def _is_tint_of(c: str, base: str, tol: float = 0.03) -> bool:
    """True when c = base blended toward white (a derived fill, not a new hue)."""
    from matplotlib.colors import to_rgb
    c3, b3 = np.array(to_rgb(c)), np.array(to_rgb(base))
    denom = 1 - b3
    if np.all(denom < 1e-6):
        return False
    f = np.where(denom > 1e-6, (c3 - b3) / np.where(denom > 1e-6, denom, 1), np.nan)
    f = f[~np.isnan(f)]
    return f.size > 0 and 0.05 < f.mean() < 0.98 and np.ptp(f) < tol * 3


def _saturated(hexc: str) -> bool:
    from matplotlib.colors import to_rgb
    import colorsys
    r, g, b = to_rgb(hexc)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return s > 0.15 and 0.08 < l < 0.95


def _dedupe(F):
    seen, out = set(), []
    for f in F:
        key = (f.severity, f.code, f.message, f.where)
        if key not in seen:
            seen.add(key)
            out.append(f)
    order = {"FAIL": 0, "WARN": 1, "REVIEW": 2, "INFO": 3}
    return sorted(out, key=lambda f: order.get(f.severity, 9))


# ---------------------------------------------------------------------------
# File audits
# ---------------------------------------------------------------------------
_UNIT_MM = {"": MM / 96, "px": MM / 96, "pt": MM / 72, "pc": MM / 6, "in": MM, "cm": 10.0, "mm": 1.0}


def _len_mm(v):
    if not v:
        return None
    m = re.match(r"^\s*([-+]?\d*\.?\d+)\s*([a-z%]*)\s*$", v)
    if not m or m.group(2) == "%":
        return None
    return float(m.group(1)) * _UNIT_MM.get(m.group(2), MM / 96)


def _required_dpi(preset, kind="halftone"):
    return preset["dpi"].get(kind, 300)


def audit_pdf(path: Path, preset, target_w=None, required_font=None) -> list[Finding]:
    F = []
    data = path.read_bytes()
    size = pf._pdf_page_mm(path)
    if size:
        F.append(_f("INFO", "PAGE_SIZE", f"{size[0]:.1f} x {size[1]:.1f} mm", path.name))
        _check_width(F, size[0], size[1], preset, target_w, path.name)
    fonts = []
    try:
        from pypdf import PdfReader
        rd = PdfReader(str(path))
        for page in rd.pages:
            res = page.get("/Resources") or {}
            res = res.get_object() if hasattr(res, "get_object") else res
            fdict = res.get("/Font") if res else None
            if not fdict:
                continue
            fdict = fdict.get_object()
            for _, ref in fdict.items():
                f = ref.get_object()
                sub = str(f.get("/Subtype"))
                base = str(f.get("/BaseFont", "?")).lstrip("/")
                embedded = False
                desc = f.get("/FontDescriptor")
                if sub == "/Type0":
                    desc = f["/DescendantFonts"][0].get_object().get("/FontDescriptor")
                if desc is not None:
                    d = desc.get_object()
                    embedded = any(k in d for k in ("/FontFile", "/FontFile2", "/FontFile3"))
                if sub == "/Type3":
                    embedded = True
                fonts.append((base, sub, embedded))
    except ImportError:
        if shutil.which("pdffonts"):
            out = subprocess.run(["pdffonts", str(path)], capture_output=True, text=True).stdout.splitlines()[2:]
            for line in out:
                parts = line.split()
                if len(parts) >= 5:
                    emb = "yes" in parts[-5:-2]
                    typ = "Type 3" if "Type 3" in line else parts[1]
                    fonts.append((parts[0], typ, emb))
        else:
            F.append(_f("REVIEW", "FONTS_UNCHECKED", "install pypdf or poppler (pdffonts) to audit embedding", path.name))
    for base, sub, emb in fonts:
        if "Type3" in sub or "Type 3" in sub:
            F.append(_f("FAIL", "TYPE3_FONT", f"{base}: Type 3 font (set pdf.fonttype = 42 in matplotlib)", path.name))
        elif not emb:
            F.append(_f("FAIL", "FONT_NOT_EMBEDDED", f"{base} ({sub}) not embedded", path.name))
    if fonts:
        names = sorted({re.sub(r"^[A-Z]{6}\+", "", b) for b, _, _ in fonts})
        F.append(_f("INFO", "FONTS", ", ".join(names), path.name))
        if required_font:
            key = required_font.lower().replace(" ", "")
            if not any(key in n.lower().replace("-", "").replace(" ", "") or (key == "arial" and "arialmt" in n.lower()) for n in names):
                F.append(_f("WARN", "FONT_NOT_REQUIRED", f"required {required_font!r}; embedded {names}", path.name))
    if shutil.which("pdfimages"):
        rows = subprocess.run(["pdfimages", "-list", str(path)], capture_output=True, text=True).stdout.splitlines()[2:]
        need = _required_dpi(preset)
        for r in rows:
            p = r.split()
            if len(p) >= 14:
                try:
                    xppi = float(p[12])
                except ValueError:
                    continue
                if p[2] == "smask":
                    continue
                if xppi < need - 1:
                    F.append(_f("FAIL", "LOW_IMAGE_PPI", f"embedded image {p[3]}x{p[4]} px placed at {xppi:.0f} ppi "
                                f"(< {need} required)", path.name))
                else:
                    F.append(_f("INFO", "IMAGE_PPI", f"embedded image {p[3]}x{p[4]} px at {xppi:.0f} ppi", path.name))
    if b"/SMask" in data or re.search(rb"/ca\s+0?\.\d", data) or re.search(rb"/CA\s+0?\.\d", data):
        F.append(_f("INFO", "PDF_TRANSPARENCY", "contains transparency (fine for PDF; flatten before EPS/legacy print)", path.name))
    if b"/DeviceCMYK" in data:
        F.append(_f("INFO", "CMYK", "contains CMYK objects", path.name))
    return F


def _check_width(F, w, h, preset, target_w, name):
    if target_w and abs(w - target_w) > 0.5:
        F.append(_f("WARN", "WIDTH_MISMATCH", f"{w:.1f} mm wide; target {target_w:.1f} mm (rescaling changes type sizes)", name))
    elif not target_w:
        widths = [v for v in preset["widths_mm"].values() if v]
        if widths and min(abs(w - v) for v in widths) > 1.0:
            F.append(_f("WARN", "NONSTANDARD_WIDTH", f"{w:.1f} mm matches none of {sorted(widths)} mm", name))
    if preset.get("max_height_mm") and h > preset["max_height_mm"] + 0.5:
        F.append(_f("FAIL", "TOO_TALL", f"{h:.1f} mm exceeds {preset['max_height_mm']} mm", name))


def audit_svg(path: Path, preset, target_w=None, required_font=None, min_dpi=None) -> list[Finding]:
    F = []
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        return [_f("FAIL", "SVG_PARSE", str(e), path.name)]
    loc = lambda tag: tag.split("}")[-1]
    w, h = _len_mm(root.get("width")), _len_mm(root.get("height"))
    if w and h:
        F.append(_f("INFO", "SVG_SIZE", f"{w:.1f} x {h:.1f} mm", path.name))
        _check_width(F, w, h, preset, target_w, path.name)
    else:
        F.append(_f("WARN", "SVG_NO_PHYSICAL_SIZE", "width/height lack physical units; placement size is ambiguous", path.name))
    texts = [e for e in root.iter() if loc(e.tag) == "text"]
    tspans = [e for e in root.iter() if loc(e.tag) == "tspan"]
    if not texts:
        F.append(_f("WARN", "SVG_NO_LIVE_TEXT", "no <text>: text is outlined or absent (not editable)", path.name))
    frag = 0
    for t in texts:
        pieces = ["".join(s.itertext()).strip() for s in t.iter() if loc(s.tag) == "tspan"]
        pieces = [p for p in pieces if p]
        if len(pieces) >= 4 and sum(map(len, pieces)) / len(pieces) <= 2:
            frag += 1
    if frag:
        F.append(_f("WARN", "SVG_FRAGMENTED_TEXT", f"{frag} text object(s) split into 1-2 character tspans", path.name))
    xml_space = "{http://www.w3.org/XML/1998/namespace}space"
    edge = [e.text for e in root.iter() if loc(e.tag) in ("text", "tspan") and e.text and e.text.strip()
            and e.text != e.text.strip(" ") and e.get(xml_space) != "preserve"]
    if edge:
        F.append(_f("WARN", "SVG_EDGE_SPACE", f"{len(edge)} text object(s) start or end with a space, which SVG viewers "
                    f"drop (e.g. {edge[0]!r}); use no-break spaces (pubfig.rich_text does)", path.name))
    fams = set()
    for e in root.iter():
        for src in (e.get("font-family", ""), e.get("style", "")):
            for m in re.finditer(r"font-family\s*:\s*([^;\"}]+)", src) if "font-family" in src else []:
                fams.update(x.strip().strip("'\"") for x in m.group(1).split(","))
            if e.get("font-family"):
                fams.update(x.strip().strip("'\"") for x in e.get("font-family").split(","))
        if loc(e.tag) == "style":
            for m in re.finditer(r"font-family\s*:\s*([^;}]+)", "".join(e.itertext())):
                fams.update(x.strip().strip("'\"") for x in m.group(1).split(","))
    fams.discard("")
    if fams:
        F.append(_f("INFO", "SVG_FONTS", ", ".join(sorted(fams)), path.name))
    if required_font and fams and required_font.lower() not in {f.lower() for f in fams}:
        F.append(_f("WARN", "FONT_NOT_REQUIRED", f"required {required_font!r}; declared {sorted(fams)}", path.name))
    vb = [float(x) for x in re.split(r"[\s,]+", root.get("viewBox", "").strip()) if x]
    need = min_dpi or _required_dpi(preset)
    n_raster = 0
    for e in root.iter():
        if loc(e.tag) != "image":
            continue
        href = e.get("href") or e.get("{http://www.w3.org/1999/xlink}href", "")
        if not href.startswith("data:image/"):
            F.append(_f("FAIL", "SVG_EXTERNAL_IMAGE", f"linked image {href[:40]!r} will not travel with the file", path.name))
            continue
        n_raster += 1
        if w and len(vb) == 4:
            try:
                from PIL import Image
                im = Image.open(io.BytesIO(base64.b64decode(href.split(",", 1)[1])))
                disp_w = float(e.get("width", vb[2]))
                dpi = im.size[0] / (w * disp_w / vb[2] / MM)
                if dpi < need - 1:
                    F.append(_f("FAIL", "LOW_IMAGE_PPI", f"embedded raster at {dpi:.0f} ppi (< {need})", path.name))
            except Exception:
                F.append(_f("REVIEW", "RASTER_UNREADABLE", "could not decode an embedded raster", path.name))
    if n_raster:
        F.append(_f("INFO", "PARTIAL_EDITABILITY", f"{n_raster} embedded raster layer(s): not fully vector-editable", path.name))
    cols = sorted(set(c.upper() for c in re.findall(r"#[0-9A-Fa-f]{6}\b", raw)))
    sat = [c for c in cols if _saturated(c)]
    sat = [c for c in sat if not any(c != o and _is_tint_of(c, o) for o in sat)]
    if 2 <= len(sat) <= 12:
        rep = pf.check_colors(sat)
        for prob in rep["problems"]:
            if not prob.startswith("contrast"):
                F.append(_f("REVIEW", "COLOR_SEPARATION", prob + " (verify these colours encode different series)", path.name))
    return F


def audit_raster(path: Path, preset, target_w=None, kind="auto") -> list[Finding]:
    F = []
    from PIL import Image
    im = Image.open(path)
    desc = str(im.tag_v2.get(270, "")) if hasattr(im, "tag_v2") else ""
    role = im.info.get("pubfig-role") or ("preview" if "role=preview" in desc else "final")
    if kind == "auto":
        tag = str(im.info.get("pubfig-kind") or desc)
        if "line" in tag:
            kind = "line"
        elif "combination" in tag:
            kind = "combination"
        else:
            kind = "halftone"
            F.append(_f("REVIEW", "RASTER_KIND", "content type unknown; checked as halftone. Pass --kind line for charts "
                        "and diagrams or --kind combination for mixed figures", path.name))
    dpi = im.info.get("dpi", (None, None))[0]
    w_px, h_px = im.size
    F.append(_f("INFO", "RASTER", f"{w_px}x{h_px} px, mode {im.mode}, dpi tag {dpi}", path.name))
    if target_w:
        eff = w_px / (target_w / MM)
        need = _required_dpi(preset, kind)
        F.append(_f("INFO", "EFFECTIVE_DPI", f"{eff:.0f} dpi when placed {target_w:.0f} mm wide", path.name))
        if eff < need - 1 and role == "preview":
            F.append(_f("INFO", "PREVIEW_DPI", f"preview PNG at {eff:.0f} dpi; a submission raster of this {kind} figure "
                        f"needs {need} dpi (TIFF from pubfig.save, or dpi={need})", path.name))
        elif eff < need - 1:
            F.append(_f("FAIL", "LOW_DPI", f"{eff:.0f} dpi at {target_w:.0f} mm; {kind} needs {need}", path.name))
    elif dpi:
        need = _required_dpi(preset, kind)
        if dpi < need - 1 and role != "preview":
            F.append(_f("WARN", "LOW_DPI_TAG", f"dpi tag {dpi:.0f} < {need}; check the placed size", path.name))
        _check_width(F, w_px / dpi * MM, h_px / dpi * MM, preset, None, path.name)
    if im.mode in ("RGBA", "LA", "PA"):
        F.append(_f("WARN", "ALPHA_CHANNEL", "alpha channel: flatten to RGB on white (pubfig.save does)", path.name))
    if path.suffix.lower() in (".jpg", ".jpeg"):
        F.append(_f("WARN", "JPEG", "lossy JPEG: acceptable for photographs only, never for line art or text", path.name))
    if im.mode == "CMYK":
        F.append(_f("INFO", "CMYK", "CMYK raster (confirm the journal wants CMYK and the ICC profile used)", path.name))
    if path.suffix.lower() in (".tif", ".tiff"):
        comp = im.info.get("compression")
        F.append(_f("INFO", "TIFF_COMPRESSION", f"compression {comp}", path.name))
        if comp in ("jpeg", "tiff_jpeg"):
            F.append(_f("WARN", "TIFF_JPEG", "JPEG-compressed TIFF is lossy; use LZW or none", path.name))
    return F


def audit_eps(path: Path, preset, target_w=None) -> list[Finding]:
    F = []
    head = path.read_bytes()[:20000].decode("latin-1", errors="replace")
    m = re.search(r"%%BoundingBox:\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)", head)
    if m:
        x0, y0, x1, y1 = map(float, m.groups())
        w, h = (x1 - x0) / 72 * MM, (y1 - y0) / 72 * MM
        F.append(_f("INFO", "EPS_SIZE", f"{w:.1f} x {h:.1f} mm", path.name))
        _check_width(F, w, h, preset, target_w, path.name)
    full = path.read_bytes().decode("latin-1", errors="replace")
    if "%%DocumentNeededResources: font" in full or "%%DocumentNeededFonts" in full:
        F.append(_f("FAIL", "EPS_FONT_NOT_EMBEDDED", "EPS references fonts it does not embed", path.name))
    if "/FontType 3" in full:
        F.append(_f("WARN", "EPS_TYPE3", "Type 3 fonts in EPS (set ps.fonttype = 42)", path.name))
    return F


def audit_file(path, *, target: str = "generic", column=None, required_font=None, kind="auto") -> list[Finding]:
    path = Path(path)
    preset = pf.preset(target)
    target_w = None
    if column is not None:
        target_w = float(column) if _isnum(column) else preset["widths_mm"].get(column)
    required_font = required_font or preset["font"]["family"]
    suf = path.suffix.lower()
    if suf == ".pdf":
        return _dedupe(audit_pdf(path, preset, target_w, required_font))
    if suf == ".svg":
        return _dedupe(audit_svg(path, preset, target_w, required_font))
    if suf in (".eps", ".ps"):
        return _dedupe(audit_eps(path, preset, target_w))
    if suf in (".png", ".tif", ".tiff", ".jpg", ".jpeg", ".bmp", ".webp"):
        return _dedupe(audit_raster(path, preset, target_w, kind))
    return [_f("WARN", "UNKNOWN_TYPE", f"no audit for {suf}", path.name)]


def _isnum(x):
    try:
        float(x)
        return True
    except (TypeError, ValueError):
        return False


def audit_series(paths) -> list[Finding]:
    """Same-slot panels must share one physical canvas (polish-sci-figures rule)."""
    sizes = {}
    for p in map(Path, paths):
        s = None
        if p.suffix.lower() == ".svg":
            r = ET.fromstring(p.read_text(encoding="utf-8", errors="replace"))
            s = (_len_mm(r.get("width")), _len_mm(r.get("height")), r.get("viewBox"))
        elif p.suffix.lower() == ".pdf":
            s = pf._pdf_page_mm(p)
            s = tuple(round(v, 1) for v in s) if s else None
        else:
            from PIL import Image
            s = Image.open(p).size
        sizes[p.name] = s
    uniq = set(map(str, sizes.values()))
    if len(uniq) > 1:
        return [_f("FAIL", "CANVAS_MISMATCH", "same-slot files differ: " + json.dumps({k: str(v) for k, v in sizes.items()}))]
    return [_f("INFO", "CANVAS_MATCH", f"{len(sizes)} files share canvas {next(iter(uniq)) if uniq else ''}")]


# ---------------------------------------------------------------------------
# CVD preview montage
# ---------------------------------------------------------------------------
def rasterize(path: Path, dpi: int = 200):
    from PIL import Image
    suf = path.suffix.lower()
    if suf == ".pdf":
        if not shutil.which("pdftoppm"):
            raise RuntimeError("pdftoppm (poppler) needed to rasterize PDF")
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["pdftoppm", "-r", str(dpi), "-png", "-singlefile", str(path), str(Path(td) / "p")], check=True)
            return Image.open(Path(td) / "p.png").convert("RGB")
    if suf in (".eps", ".ps"):
        gs = shutil.which("gs")
        if not gs:
            raise RuntimeError("Ghostscript (gs) needed to rasterize EPS")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "p.png"
            subprocess.run([gs, "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-dEPSCrop", "-sDEVICE=png16m",
                            f"-r{dpi}", f"-sOutputFile={out}", str(path)], check=True)
            return Image.open(out).convert("RGB")
    if suf == ".svg":
        import cairosvg
        png = cairosvg.svg2png(url=str(path), dpi=dpi)
        im = Image.open(io.BytesIO(png)).convert("RGBA")
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[-1])
        return bg
    im = Image.open(path)
    if im.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
        return bg
    return im.convert("RGB")


def cvd_preview(path, out, width_px: int = 900) -> Path:
    """Original, deuteranopia, protanopia, tritanopia, grayscale side by side."""
    from PIL import Image, ImageDraw
    im = rasterize(Path(path))
    if im.width > width_px:
        im = im.resize((width_px, round(im.height * width_px / im.width)), Image.LANCZOS)
    arr = np.asarray(im, float) / 255
    panels = [("Original", arr)]
    for k in ("deuteranopia", "protanopia", "tritanopia", "achromatopsia"):
        panels.append(({"achromatopsia": "Grayscale (luminance)"}.get(k, k.capitalize()), pf.simulate_cvd(arr, k)))
    cols = 2
    rows = math.ceil(len(panels) / cols)
    lab_h = 22
    W, H = im.width, im.height + lab_h
    canvas = Image.new("RGB", (cols * W + (cols - 1) * 12, rows * H + (rows - 1) * 12), "white")
    d = ImageDraw.Draw(canvas)
    for i, (name, a) in enumerate(panels):
        x, y = (i % cols) * (W + 12), (i // cols) * (H + 12)
        canvas.paste(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)), (x, y + lab_h))
        d.text((x + 4, y + 4), name, fill=(0, 0, 0))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    return out


# ---------------------------------------------------------------------------
# Source portability (polish-sci-figures rule) and document rendering
# ---------------------------------------------------------------------------
_PORT_RULES = [
    (re.compile(r"\.claude[/\\]|\.codex[/\\]|CODEX_HOME|plugins?[/\\]cache|skills[/\\]scientific-figure-publication"),
     "FAIL", "reads a skill/plugin path at runtime; copy helpers into the project"),
    (re.compile(r"[\"'](?:/Users/|/home/|/root/|[A-Za-z]:\\\\Users\\\\)[^\"']+[\"']"), "FAIL",
     "machine-specific absolute path; resolve relative to the script or a declared project root"),
    (re.compile(r"sys\.path\.(?:insert|append)"), "WARN", "mutates sys.path (fine only for a project-local folder)"),
    (re.compile(r"os\.chdir\("), "WARN", "changes working directory implicitly"),
    (re.compile(r"plt\.savefig\([^)]*bbox_inches\s*=\s*[\"']tight"), "FAIL",
     "bbox_inches='tight' changes the physical canvas; use a fixed size (pubfig.save)"),
    (re.compile(r"fig\.savefig\([^)]*bbox_inches\s*=\s*[\"']tight"), "FAIL",
     "bbox_inches='tight' changes the physical canvas; use a fixed size (pubfig.save)"),
    (re.compile(r"pdf\.fonttype[\"']?\s*[:=,]\s*3"), "FAIL", "Type 3 fonts requested"),
    (re.compile(r"cmap\s*=\s*[\"'](?:jet|rainbow|hsv|gist_rainbow|nipy_spectral|turbo)[\"']"), "FAIL", "rainbow colormap"),
    (re.compile(r"np\.random\.(?:rand|randn|normal|uniform|choice)\(|random\.random\("), "REVIEW",
     "random numbers in a figure script: fixed seed? synthetic data must be labelled synthetic"),
]


def check_portability(script) -> list[Finding]:
    p = Path(script)
    text = p.read_text(encoding="utf-8", errors="replace")
    F = []
    in_doc = False
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        quotes = stripped.count('"""') + stripped.count("\'\'\'")
        if in_doc or (quotes and stripped[:3] in ('"""', "\'\'\'")):
            if quotes % 2 == 1:
                in_doc = not in_doc
            continue
        if stripped.startswith("#"):
            continue
        for rx, sev, msg in _PORT_RULES:
            if rx.search(line):
                F.append(_f(sev, "PORTABILITY", f"line {i}: {msg}: {line.strip()[:80]}", p.name))
    for mod in ("pubfig", "pubfig_plots", "pubfig_clinical"):
        if re.search(rf"^\s*(?:import|from)\s+{mod}\b", text, re.M) and not (p.parent / f"{mod}.py").exists():
            F.append(_f("FAIL", "MISSING_HELPER", f"imports {mod} but {mod}.py is not beside the script; copy it in", p.name))
    return F


def render_doc(path, outdir, dpi: int = 110) -> list[Path]:
    """Render DOCX/PPTX/PDF pages to PNG to inspect figures in their real container.

    Uses LibreOffice for Office files (a compatibility preview, not native
    Word/PowerPoint rendering) and pdftoppm for PDF.
    """
    path, outdir = Path(path), Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    pdf = path
    if path.suffix.lower() in (".docx", ".pptx", ".doc", ".ppt", ".odt", ".odp"):
        office = shutil.which("soffice") or shutil.which("libreoffice")
        if not office:
            raise RuntimeError("LibreOffice not found; export the document to PDF and pass the PDF")
        subprocess.run([office, "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(path)],
                       check=True, capture_output=True, timeout=240)
        pdf = outdir / (path.stem + ".pdf")
    if not shutil.which("pdftoppm"):
        raise RuntimeError("pdftoppm (poppler) not found")
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(outdir / path.stem)], check=True)
    return sorted(outdir.glob(path.stem + "*.png"))


# ---------------------------------------------------------------------------
# reporting / CLI
# ---------------------------------------------------------------------------
def report(findings, *, as_json: bool = False, show_info: bool = True) -> int:
    if as_json:
        print(json.dumps([asdict(f) for f in findings], indent=2, ensure_ascii=False))
    else:
        for f in findings:
            if f.severity == "INFO" and not show_info:
                continue
            where = f" [{f.where}]" if f.where else ""
            print(f"{f.severity:6s} {f.code:22s}{where} {f.message}")
        n = {s: sum(f.severity == s for f in findings) for s in ("FAIL", "WARN", "REVIEW")}
        print(f"-- {n['FAIL']} FAIL, {n['WARN']} WARN, {n['REVIEW']} REVIEW")
    return 2 if any(f.severity == "FAIL" for f in findings) else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--target", default="generic", help="journal/preset key (see pubfig.PRESETS)")
    ap.add_argument("--column", help="single | onehalf | double | full | width in mm")
    ap.add_argument("--font", help="required font family (default: preset)")
    ap.add_argument("--kind", default="auto", choices=["auto", "line", "halftone", "combination"],
                    help="raster content type for DPI rules (auto reads the tag pubfig.save writes)")
    ap.add_argument("--same-size", action="store_true", help="require identical canvases across files")
    ap.add_argument("--cvd-preview", help="write a CVD/grayscale montage PNG for the first file")
    ap.add_argument("--portability", nargs="*", default=[], help="figure scripts to check")
    ap.add_argument("--render-doc", help="render DOCX/PPTX/PDF pages to PNG")
    ap.add_argument("--out", default="qa/pages", help="output folder for --render-doc")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="treat WARN as blocking")
    a = ap.parse_args(argv)
    findings: list[Finding] = []
    for fpath in a.files:
        findings += audit_file(fpath, target=a.target, column=a.column, required_font=a.font, kind=a.kind)
    if a.same_size and len(a.files) > 1:
        findings += audit_series(a.files)
    for s in a.portability:
        findings += check_portability(s)
    if a.cvd_preview and a.files:
        rank = {".png": 0, ".tif": 0, ".tiff": 0, ".jpg": 1, ".jpeg": 1, ".pdf": 2, ".svg": 3, ".eps": 4, ".ps": 4}
        errors = []
        for fpath in sorted(a.files, key=lambda f: rank.get(Path(f).suffix.lower(), 9)):
            try:
                out = cvd_preview(fpath, a.cvd_preview)
            except Exception as e:          # missing rasterizer (poppler, cairosvg, Ghostscript) or unreadable file
                errors.append(f"{Path(fpath).name}: {e}")
                continue
            findings.append(_f("INFO", "CVD_PREVIEW", f"wrote {out} from {Path(fpath).name} "
                               "(inspect it: meaning must survive every panel)"))
            break
        else:
            findings.append(_f("WARN", "CVD_PREVIEW_SKIPPED", "no listed file could be rasterized (" + "; ".join(errors)
                               + "); pass the PNG or PDF export"))
    if a.render_doc:
        pages = render_doc(a.render_doc, a.out)
        findings.append(_f("INFO", "RENDERED", f"{len(pages)} page image(s) in {a.out}"))
    code = report(_dedupe(findings), as_json=a.json)
    if a.strict and any(f.severity == "WARN" for f in findings):
        code = 2
    return code


if __name__ == "__main__":
    raise SystemExit(main())
