"""pubfig_plots: general publication chart builders on top of pubfig.

Each builder draws into an existing Axes created at final size by
pubfig.subplots(), so typography and stroke widths stay physical. Builders
return the statistics they drew so legends and captions can quote them.

Design rules encoded here (see references/chart-selection.md):
- show observations for small samples (estimation_plot, paired_plot, raincloud);
- bars always start at zero; narrow-range comparisons use dot_plot instead;
- error bars must be named (SD, SEM, or 95% CI) and are recorded on the Axes;
- colour bands are opaque tints, not alpha, so PDF/EPS/print stay faithful;
- heatmaps use perceptually uniform or diverging maps with an explicit centre.
"""
from __future__ import annotations

import math
import warnings
from typing import Mapping, Sequence

import numpy as np
import matplotlib as mpl
from matplotlib.colors import to_hex

import pubfig as pf

_ERROR_KINDS = {"SD", "SEM", "95% CI", "IQR", "range", "min-max"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _as_groups(data, order=None) -> dict[str, np.ndarray]:
    if isinstance(data, Mapping):
        groups = {str(k): np.asarray(v, dtype=float) for k, v in data.items()}
    else:  # (DataFrame, group_col, value_col)
        df, gcol, vcol = data
        groups = {str(k): df.loc[df[gcol] == k, vcol].to_numpy(dtype=float) for k in df[gcol].unique()}
    if order:
        missing = [o for o in order if o not in groups]
        if missing:
            raise KeyError(f"groups not found: {missing}")
        groups = {o: groups[o] for o in order}
    return {k: v[~np.isnan(v)] for k, v in groups.items()}


def t_quantile(level: float, df: int) -> float:
    try:
        from scipy import stats
        return float(stats.t.ppf(0.5 + level / 2, df))
    except ImportError:  # normal approximation, flagged
        warnings.warn("scipy missing: using normal quantile for CI (too narrow for small n)")
        return {0.9: 1.645, 0.95: 1.96, 0.99: 2.576}.get(level, 1.96)


def mean_ci(x: np.ndarray, level: float = 0.95) -> tuple[float, float, float]:
    x = np.asarray(x, float)
    n = x.size
    m = float(x.mean())
    if n < 2:
        return m, math.nan, math.nan
    half = t_quantile(level, n - 1) * x.std(ddof=1) / math.sqrt(n)
    return m, m - half, m + half


def bootstrap_ci(x: np.ndarray, stat=np.median, level: float = 0.95, n_boot: int = 4000,
                 seed: int = 20260101) -> tuple[float, float, float]:
    """Percentile bootstrap (fixed seed for reproducible figures)."""
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    boots = stat(rng.choice(x, size=(n_boot, x.size), replace=True), axis=1)
    lo, hi = np.quantile(boots, [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(stat(x)), float(lo), float(hi)


def sina_offsets(values: np.ndarray, width: float = 0.32, seed: int = 7) -> np.ndarray:
    """Density-scaled horizontal jitter (sina-style), deterministic."""
    v = np.asarray(values, float)
    if v.size < 3 or np.ptp(v) == 0:
        return np.zeros_like(v) if v.size < 2 else np.linspace(-width / 3, width / 3, v.size)
    bw = 1.06 * v.std(ddof=1) * v.size ** (-1 / 5) or np.ptp(v) / 10
    dens = np.exp(-0.5 * ((v[:, None] - v[None, :]) / bw) ** 2).sum(1)
    dens = dens / dens.max()
    rng = np.random.default_rng(seed)
    return rng.uniform(-1, 1, v.size) * width * dens


def _n_labels(ax, groups):
    """'(n = 7)' under each category tick with an italic n, as live text runs."""
    fs = mpl.rcParams["xtick.labelsize"]
    dy = -(mpl.rcParams["xtick.major.size"] + mpl.rcParams["xtick.major.pad"] + fs * 1.25)
    blend = mpl.transforms.blended_transform_factory(ax.transData, ax.transAxes)
    for i, v in enumerate(groups.values()):
        pf.rich_text(ax, i, 0, [("(", "normal"), ("n", "italic"), (f" = {np.asarray(v).size})", "normal")],
                     transform=blend, ha="center", va="top", fontsize=fs, offset_pt=(0, dy))


def _record_errors(ax, kind: str | None):
    if kind is None:
        return
    if kind not in _ERROR_KINDS:
        raise ValueError(f"error kind must be one of {sorted(_ERROR_KINDS)}; got {kind!r}")
    ax._pubfig_error_kind = kind


# ---------------------------------------------------------------------------
# distributions and group comparisons
# ---------------------------------------------------------------------------
def estimation_plot(ax, data, order=None, *, colors=None, center: str = "mean", level: float = 0.95,
                    summary_offset: float = 0.4, jitter: float = 0.24, point_size: float | None = None,
                    point_alpha_tint: float = 0.0, show_n: bool = True, ylabel: str | None = None,
                    rotate_labels: int = 0) -> dict:
    """Every observation plus mean (t-based CI) or median (bootstrap CI).

    The default replacement for bar-and-whisker ("dynamite") plots of
    continuous data. Summary markers sit beside the points so neither hides
    the other. Returns per-group n, centre, and CI.
    """
    groups = _as_groups(data, order)
    colors = colors or pf.CATEGORICAL
    ps = point_size or (mpl.rcParams["lines.markersize"] ** 2) * 0.9
    out = {}
    for i, (name, vals) in enumerate(groups.items()):
        col = colors[i % len(colors)]
        x = i + sina_offsets(vals, width=jitter)
        ow = pf.outline_width(ax)
        ax.scatter(x, vals, s=ps, color=pf.tint(col, point_alpha_tint) if point_alpha_tint else col,
                   edgecolor="white" if ow else "none", linewidths=ow, zorder=2, clip_on=False)
        if center == "mean":
            c, lo, hi = mean_ci(vals, level)
        else:
            c, lo, hi = bootstrap_ci(vals, np.median, level)
        xs = i + summary_offset
        ax.errorbar([xs], [c], yerr=[[c - lo], [hi - c]], fmt="o", color=pf.NEUTRALS["ink"],
                    ms=mpl.rcParams["lines.markersize"] * 1.1, capsize=0, lw=mpl.rcParams["lines.linewidth"], zorder=3)
        out[name] = {"n": int(vals.size), center: c, "ci_low": lo, "ci_high": hi, "level": level}
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(list(groups), rotation=rotate_labels, ha="right" if rotate_labels else "center")
    ax.set_xlim(-0.6, len(groups) - 0.4 + max(0.0, summary_offset - 0.3))
    if show_n:
        _n_labels(ax, groups)
    ax.spines["bottom"].set_visible(True)
    ax.tick_params(axis="x", length=0)
    if ylabel:
        ax.set_ylabel(ylabel)
    _record_errors(ax, "95% CI" if level == 0.95 else None)
    ax._pubfig_summary = f"points: individual observations; marker: {center} with {int(level * 100)}% CI"
    return out


def paired_plot(ax, before, after, labels=("Before", "After"), *, color_up=None, color_down=None,
                color_flat="#9A9A9A", show_summary: bool = True, level: float = 0.95, ylabel: str | None = None) -> dict:
    """Slopegraph for paired measurements; colour encodes direction of change.

    Pairing must be real (same subject); unpaired data drawn this way invents
    structure. Returns mean change with CI.
    """
    b, a = np.asarray(before, float), np.asarray(after, float)
    if b.shape != a.shape:
        raise ValueError("before and after must be paired arrays of equal length")
    ok = ~(np.isnan(b) | np.isnan(a))
    b, a = b[ok], a[ok]
    color_up = color_up or pf.CATEGORICAL[0]
    color_down = color_down or pf.CATEGORICAL[1]
    for y0, y1 in zip(b, a):
        col = color_up if y1 > y0 else color_down if y1 < y0 else color_flat
        ax.plot([0, 1], [y0, y1], color=col, lw=mpl.rcParams["lines.linewidth"] * 0.6, marker="o",
                ms=mpl.rcParams["lines.markersize"] * 0.7, zorder=2, solid_capstyle="round")
    d = a - b
    m, lo, hi = mean_ci(d, level)
    if show_summary:
        for x, arr in ((-0.18, b), (1.18, a)):
            c, l, h = mean_ci(arr, level)
            ax.errorbar([x], [c], yerr=[[c - l], [h - c]], fmt="o", color=pf.NEUTRALS["ink"], capsize=0, zorder=3)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(labels)
    ax.set_xlim(-0.45, 1.45)
    ax.tick_params(axis="x", length=0)
    if ylabel:
        ax.set_ylabel(ylabel)
    _record_errors(ax, "95% CI")
    return {"n_pairs": int(d.size), "mean_change": m, "ci_low": lo, "ci_high": hi,
            "n_increase": int((d > 0).sum()), "n_decrease": int((d < 0).sum())}


def raincloud(ax, data, order=None, *, colors=None, min_n_density: int = 10, bw: str | float = "scott",
              ylabel: str | None = None) -> dict:
    """Half-violin (KDE) + box (median, IQR) + jittered observations.

    Density is drawn only for groups with at least ``min_n_density``
    observations; a KDE of a handful of points invents shape.
    """
    groups = _as_groups(data, order)
    colors = colors or pf.CATEGORICAL
    out = {}
    for i, (name, v) in enumerate(groups.items()):
        col = colors[i % len(colors)]
        if v.size >= min_n_density and np.ptp(v) > 0:
            try:
                from scipy.stats import gaussian_kde
                kde = gaussian_kde(v, bw_method=bw)
                grid = np.linspace(v.min(), v.max(), 200)
                dens = kde(grid)
                dens = dens / dens.max() * 0.32
                ax.fill_betweenx(grid, i - 0.05, i - 0.05 - dens, color=pf.tint(col, 0.55), lw=0, zorder=1)
            except ImportError:
                warnings.warn("scipy missing: density half skipped")
        q1, med, q3 = np.percentile(v, [25, 50, 75])
        ax.add_patch(mpl.patches.Rectangle((i + 0.02, q1), 0.08, q3 - q1, fc="white",
                                           ec=pf.NEUTRALS["ink"], lw=mpl.rcParams["axes.linewidth"], zorder=3))
        ax.plot([i + 0.02, i + 0.10], [med, med], color=pf.NEUTRALS["ink"], lw=mpl.rcParams["lines.linewidth"], zorder=4)
        rng = np.random.default_rng(11 + i)
        ax.scatter(i + 0.2 + rng.uniform(-0.05, 0.05, v.size), v, s=mpl.rcParams["lines.markersize"] ** 2 * 0.6,
                   color=col, edgecolor="none", zorder=2)
        out[name] = {"n": int(v.size), "median": float(med), "q1": float(q1), "q3": float(q3)}
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(list(groups))
    ax.set_xlim(-0.5, len(groups) - 0.5)
    _n_labels(ax, groups)
    ax.tick_params(axis="x", length=0)
    if ylabel:
        ax.set_ylabel(ylabel)
    _record_errors(ax, "IQR")
    return out


# ---------------------------------------------------------------------------
# bars, dots, lines
# ---------------------------------------------------------------------------
def bar_plot(ax, categories: Sequence[str], values, errors=None, *, error_kind: str | None = None,
             series_labels: Sequence[str] | None = None, colors=None, hatches=None, width: float = 0.8,
             horizontal: bool = False, value_labels: bool = False, fmt: str = "{:.2f}",
             edgecolor: str | None = None) -> list:
    """Grouped bars for counts, proportions, or totals (not distributions).

    values: shape (n_categories,) or (n_series, n_categories). The value axis
    always starts at zero because bar length encodes magnitude. Errors require
    ``error_kind`` (SD, SEM, 95% CI) so the legend can define them.
    """
    vals = np.atleast_2d(np.asarray(values, float))
    errs = None if errors is None else np.atleast_2d(np.asarray(errors, float))
    if errs is not None and error_kind is None:
        raise ValueError("error bars need error_kind ('SD', 'SEM', or '95% CI') so they can be defined")
    ns, nc = vals.shape
    colors = colors or pf.CATEGORICAL
    w = width / ns
    containers = []
    pos = np.arange(nc)
    for s in range(ns):
        off = pos - width / 2 + w * (s + 0.5)
        kw = dict(color=colors[s % len(colors)], edgecolor=edgecolor or "none",
                  linewidth=mpl.rcParams["patch.linewidth"] if edgecolor else 0,
                  hatch=None if hatches is None else hatches[s % len(hatches)],
                  label=None if series_labels is None else series_labels[s], zorder=2)
        if horizontal:
            bars = ax.barh(off, vals[s], height=w * 0.92, xerr=None if errs is None else errs[s % len(errs)],
                           error_kw=dict(lw=mpl.rcParams["axes.linewidth"], capsize=0, ecolor=pf.NEUTRALS["ink"]), **kw)
        else:
            bars = ax.bar(off, vals[s], width=w * 0.92, yerr=None if errs is None else errs[s % len(errs)],
                          error_kw=dict(lw=mpl.rcParams["axes.linewidth"], capsize=0, ecolor=pf.NEUTRALS["ink"]), **kw)
        containers.append(bars)
        if value_labels:
            ax.bar_label(bars, labels=[fmt.format(v) for v in vals[s]], padding=1.5,
                         fontsize=mpl.rcParams["xtick.labelsize"])
    if horizontal:
        ax.set_yticks(pos, categories)
        ax.set_xlim(left=0)
        ax.tick_params(axis="y", length=0)
    else:
        ax.set_xticks(pos, categories)
        ax.set_ylim(bottom=0)
        ax.tick_params(axis="x", length=0)
    _record_errors(ax, error_kind)
    ax._pubfig_bars_from_zero = True
    return containers


def dot_plot(ax, labels: Sequence[str], values, lo=None, hi=None, *, highlight: str | Sequence[str] | None = None,
             highlight_color=None, base_color: str = "#5B6472", ref: float | None = None, sort: bool = True,
             xlabel: str | None = None, value_text: str | None = None, error_kind: str | None = None) -> list[str]:
    """Cleveland dot plot (optionally with intervals) for estimates on a common scale.

    Use instead of a truncated bar chart when the values occupy a narrow
    range: position on a common scale is read more accurately than length.
    """
    v = np.asarray(values, float)
    order = np.argsort(-v, kind="stable") if sort else np.arange(v.size)  # first row = top
    labels = [labels[i] for i in order]
    v = v[order]
    lo = None if lo is None else np.asarray(lo, float)[order]
    hi = None if hi is None else np.asarray(hi, float)[order]
    hl = {highlight} if isinstance(highlight, str) else set(highlight or [])
    hc = highlight_color or pf.CATEGORICAL[0]
    y = np.arange(v.size)
    for yi, lab, val in zip(y, labels, v):
        col = hc if lab in hl else base_color
        if lo is not None:
            ax.plot([lo[yi], hi[yi]], [yi, yi], color=col, lw=mpl.rcParams["lines.linewidth"], zorder=2,
                    solid_capstyle="butt")
        ax.plot(val, yi, "o", color=col, ms=mpl.rcParams["lines.markersize"] * (1.25 if lab in hl else 1), zorder=3)
        if value_text:
            ax.annotate(value_text.format(val), (1, yi), xycoords=("axes fraction", "data"), xytext=(2, 0),
                        textcoords="offset points", va="center", ha="left", fontsize=mpl.rcParams["xtick.labelsize"],
                        color=col, annotation_clip=False)
    ax.set_yticks(y, labels)
    ax.set_ylim(v.size - 0.5, -0.5)  # reading order top to bottom
    lo_all = np.nanmin(lo) if lo is not None else np.nanmin(v)
    hi_all = np.nanmax(hi) if hi is not None else np.nanmax(v)
    pad = (hi_all - lo_all) * 0.06 or 1.0
    ax.set_xlim(lo_all - pad, hi_all + pad)
    for t, lab in zip(ax.get_yticklabels(), labels):
        if lab in hl:
            t.set_fontweight("bold")
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", lw=mpl.rcParams["grid.linewidth"], color=pf.NEUTRALS["grid"])
    if ref is not None:
        pf.reference_line(ax, ref, "v")
    if xlabel:
        ax.set_xlabel(xlabel)
    _record_errors(ax, error_kind if lo is not None else None)
    return labels


def line_band(ax, x, y, lo=None, hi=None, *, color=None, label: str | None = None, band_tint: float = 0.72,
              marker: str | None = None, ls="-", **kw):
    """Line with an uncertainty band drawn as an opaque tint (print/EPS safe)."""
    color = color or pf.CATEGORICAL[len(ax.lines) % len(pf.CATEGORICAL)]
    if lo is not None and hi is not None:
        ax.fill_between(x, lo, hi, color=pf.tint(color, band_tint), lw=0, zorder=1)
    (line,) = ax.plot(x, y, color=color, label=label, marker=marker, ls=ls, zorder=2, **kw)
    return line


def direct_labels(ax, lines=None, labels=None, *, x: float | None = None, pad_pt: float = 2.5,
                  min_sep_pt: float | None = None, fontsize: float | None = None):
    """Label lines at their right end and push labels apart vertically.

    Direct labels remove legend look-up; keep the right margin free for them.
    """
    lines = lines or [ln for ln in ax.get_lines() if not ln.get_label().startswith("_")]
    labels = labels or [ln.get_label() for ln in lines]
    fontsize = fontsize or mpl.rcParams["legend.fontsize"]
    sep = (min_sep_pt or fontsize * 1.15)
    fig = ax.figure
    fig.canvas.draw()
    trans = ax.transData
    pts = []
    for ln in lines:
        xd, yd = np.asarray(ln.get_xdata(), float), np.asarray(ln.get_ydata(), float)
        idx = np.nanargmax(xd) if x is None else np.nanargmin(np.abs(xd - x))
        pts.append(trans.transform((xd[idx], yd[idx])))
    pts = np.array(pts)
    order = np.argsort(pts[:, 1])
    ys = pts[order, 1].copy()
    sep_px = sep * fig.dpi / 72
    for _ in range(50):  # simple 1D repel
        moved = False
        for k in range(1, len(ys)):
            if ys[k] - ys[k - 1] < sep_px:
                shift = (sep_px - (ys[k] - ys[k - 1])) / 2
                ys[k - 1] -= shift
                ys[k] += shift
                moved = True
        if not moved:
            break
    texts = []
    inv = ax.transData.inverted()
    for rank, i in enumerate(order):
        xy = inv.transform((pts[i, 0], ys[rank]))
        anchor = inv.transform(pts[i])
        texts.append(ax.annotate(labels[i], xy=(anchor[0], anchor[1]), xytext=(pad_pt, (ys[rank] - pts[i, 1]) * 72 / fig.dpi),
                                 textcoords="offset points", va="center", ha="left", fontsize=fontsize,
                                 color=lines[i].get_color(), annotation_clip=False))
    return texts


def legend_panel(ax, handles, labels, *, ncol: int = 1, title: str | None = None, loc: str = "center"):
    """Dedicated legend axes (keeps legends off the data in dense grids)."""
    ax.set_axis_off()
    return ax.legend(handles, labels, ncol=ncol, title=title, loc=loc, frameon=False)


# ---------------------------------------------------------------------------
# heatmap
# ---------------------------------------------------------------------------
def heatmap(ax, matrix, row_labels=None, col_labels=None, *, kind: str = "sequential", center: float | None = None,
            vmin: float | None = None, vmax: float | None = None, cmap: str | None = None, robust: bool = False,
            annotate: bool = False, fmt: str = "{:.2f}", cbar: bool = True, cbar_label: str | None = None,
            rasterize_over: int = 4000, mask=None, cbar_kw: dict | None = None):
    """Matrix display with an honest colour scale.

    kind="sequential" (magnitude) uses viridis by default; kind="diverging"
    (signed values around ``center``, default 0) uses RdBu_r with symmetric
    limits so equal deviations get equal colour weight. ``robust`` sets limits
    from the 2nd/98th percentiles (record this in the legend).
    Cells are vector unless the matrix exceeds ``rasterize_over`` cells.
    """
    M = np.ma.masked_array(np.asarray(matrix, float), mask=mask)
    if cmap in pf.FORBIDDEN_CMAPS:
        raise ValueError(f"{cmap!r} is not perceptually uniform; use viridis/cividis or a diverging map")
    finite = M.compressed()
    finite = finite[np.isfinite(finite)]
    if kind == "diverging":
        center = 0.0 if center is None else center
        dev = np.quantile(np.abs(finite - center), 0.98) if robust else np.max(np.abs(finite - center))
        vmin = center - dev if vmin is None else vmin
        vmax = center + dev if vmax is None else vmax
        cmap = cmap or "RdBu_r"
        norm = mpl.colors.TwoSlopeNorm(vcenter=center, vmin=vmin, vmax=vmax)
    else:
        lo_, hi_ = (np.quantile(finite, [0.02, 0.98]) if robust else (finite.min(), finite.max()))
        vmin = lo_ if vmin is None else vmin
        vmax = hi_ if vmax is None else vmax
        cmap = cmap or "viridis"
        norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)
    nr, nc = M.shape
    mesh = ax.pcolormesh(np.arange(nc + 1), np.arange(nr + 1), M, cmap=cmap, norm=norm,
                         edgecolors="white", linewidth=pf.outline_width(ax) if nr * nc <= 400 else 0,
                         rasterized=nr * nc > rasterize_over)
    ax.set_xlim(0, nc)
    ax.set_ylim(nr, 0)
    ax.set_xticks(np.arange(nc) + 0.5, col_labels if col_labels is not None else range(nc))
    ax.set_yticks(np.arange(nr) + 0.5, row_labels if row_labels is not None else range(nr))
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    if annotate:
        cm = mpl.colormaps[cmap]
        for i in range(nr):
            for j in range(nc):
                if M.mask is not np.ma.nomask and M.mask[i, j]:
                    continue
                val = M[i, j]
                rgba = cm(norm(val))
                txt = "#FFFFFF" if pf.relative_luminance(rgba[:3]) < 0.33 else "#000000"
                ax.text(j + 0.5, i + 0.5, fmt.format(val), ha="center", va="center", color=txt,
                        fontsize=mpl.rcParams["xtick.labelsize"] * 0.9)
    cb = None
    if cbar:
        cb = ax.figure.colorbar(mesh, ax=ax, **{"fraction": 0.06, "pad": 0.02, "aspect": 18, **(cbar_kw or {})})
        cb.outline.set_linewidth(mpl.rcParams["axes.linewidth"])
        cb.ax.tick_params(width=mpl.rcParams["axes.linewidth"], length=2)
        if cbar_label:
            cb.set_label(cbar_label)
    ax._pubfig_heatmap = {"kind": kind, "center": center, "vmin": vmin, "vmax": vmax, "cmap": cmap, "robust": robust}
    return mesh, cb


# ---------------------------------------------------------------------------
# annotation: significance brackets with automatic stacking
# ---------------------------------------------------------------------------
def sig_bracket(ax, x1: float, x2: float, text: str, *, y: float | None = None, h_frac: float = 0.025,
                gap_frac: float = 0.03, color: str | None = None):
    """Comparison bracket with its label, stacked above earlier brackets.

    Only draw brackets for comparisons that were pre-specified and actually
    tested; print the exact P value via pubfig.fmt_p, not asterisks.
    """
    color = color or pf.NEUTRALS["ink"]
    lo, hi = ax.get_ylim()
    span = hi - lo
    levels = getattr(ax, "_pubfig_bracket_tops", [])
    if y is None:
        data_top = max((np.nanmax(np.asarray(c.get_offsets())[:, 1]) for c in ax.collections
                        if hasattr(c, "get_offsets") and len(c.get_offsets())), default=hi)
        line_top = max((np.nanmax(ln.get_ydata()) for ln in ax.lines if len(ln.get_ydata())), default=data_top)
        from matplotlib.collections import LineCollection
        seg_top = max((max(np.nanmax(np.asarray(sg)[:, 1]) for sg in c.get_segments() if len(sg))
                       for c in ax.collections if isinstance(c, LineCollection) and len(c.get_segments())),
                      default=data_top)  # error-bar segments
        y = max([data_top, line_top, seg_top] + levels) + gap_frac * span
    h = h_frac * span
    ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], color=color, lw=mpl.rcParams["axes.linewidth"],
            clip_on=False, solid_joinstyle="miter")
    t = ax.text((x1 + x2) / 2, y + h, text, ha="center", va="bottom", color=color,
                fontsize=mpl.rcParams["xtick.labelsize"])
    top = y + h + span * 0.06
    ax._pubfig_bracket_tops = levels + [top]
    if top > hi:
        ax.set_ylim(lo, top + gap_frac * span)
    return t


# ---------------------------------------------------------------------------
# ML / engineering figures (from figures4papers and Scientific-Figure-Design)
# ---------------------------------------------------------------------------
def radar(ax, categories: Sequence[str], series: Mapping[str, Sequence[float]], *, rlim: tuple[float, float],
          colors=None, fill_tint: float | None = 0.85, ticks: Sequence[float] | None = None):
    """Radar chart on ONE shared radial scale.

    Radar area depends on axis order and per-spoke rescaling exaggerates
    differences; prefer dot_plot or small multiples. If a radar is required,
    every spoke uses the same ``rlim`` (stated in the legend) and ``ax`` must
    be polar: fig.add_subplot(projection="polar").
    """
    n = len(categories)
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ang_c = np.concatenate([ang, ang[:1]])
    colors = colors or pf.CATEGORICAL
    for i, (name, vals) in enumerate(series.items()):
        v = np.asarray(vals, float)
        if v.size != n:
            raise ValueError(f"series {name!r} has {v.size} values for {n} categories")
        vc = np.concatenate([v, v[:1]])
        col = colors[i % len(colors)]
        if fill_tint is not None:
            ax.fill(ang_c, vc, color=pf.tint(col, fill_tint), zorder=1)
        ax.plot(ang_c, vc, color=col, label=name, zorder=2)
    ax.set_xticks(ang, categories)
    ax.set_ylim(*rlim)
    if ticks is not None:
        ax.set_yticks(ticks)
    ax.tick_params(axis="y", labelsize=mpl.rcParams["xtick.labelsize"] * 0.9)
    ax.spines["polar"].set_linewidth(mpl.rcParams["axes.linewidth"])
    ax.grid(lw=mpl.rcParams["grid.linewidth"], color=pf.NEUTRALS["grid"])
    return ax


def roofline(ax, peak_perf: float, bandwidth: float, points: Sequence[tuple[str, float, float]], *,
             perf_unit: str = "GFLOP/s", ai_unit: str = "FLOP/byte", xlim=(0.01, 1000), colors=None,
             label_bound: bool = True):
    """Roofline: attainable performance = min(peak, bandwidth x arithmetic intensity).

    points: (label, arithmetic_intensity, achieved_performance). Label the
    bound, the ridge point, and whether points are measured or predicted.
    """
    ai = np.logspace(np.log10(xlim[0]), np.log10(xlim[1]), 400)
    roof = np.minimum(peak_perf, bandwidth * ai)
    ax.loglog(ai, roof, color=pf.NEUTRALS["ink"], lw=mpl.rcParams["lines.linewidth"] * 1.2, zorder=1)
    ridge = peak_perf / bandwidth
    if label_bound:
        ax.annotate(f"ridge {ridge:.3g} {ai_unit}", (ridge, peak_perf), xytext=(3, -8), textcoords="offset points",
                    fontsize=mpl.rcParams["xtick.labelsize"], color=pf.NEUTRALS["muted"])
    colors = colors or pf.CATEGORICAL
    for i, (lab, x, y) in enumerate(points):
        ax.plot(x, y, "o", color=colors[i % len(colors)], zorder=3, label=lab)
    ax.set_xlabel(f"Arithmetic intensity ({ai_unit})")
    ax.set_ylabel(f"Performance ({perf_unit})")
    ax.set_xlim(*xlim)
    return ridge


def small_multiples(spec, nrows: int, ncols: int, *, sharex: bool = True, sharey: bool = True, **kw):
    """Aligned grid with shared scales (compare panels without re-reading axes)."""
    fig, axes = pf.subplots(spec, nrows, ncols, sharex=sharex, sharey=sharey, squeeze=False, **kw)
    for ax in axes[:-1, :].ravel() if sharex else []:
        ax.tick_params(labelbottom=False)
    for ax in axes[:, 1:].ravel() if sharey else []:
        ax.tick_params(labelleft=False)
    return fig, axes


__all__ = ["estimation_plot", "paired_plot", "raincloud", "bar_plot", "dot_plot", "line_band", "direct_labels",
           "legend_panel", "heatmap", "sig_bracket", "radar", "roofline", "small_multiples", "mean_ci",
           "bootstrap_ci", "sina_offsets", "t_quantile"]
