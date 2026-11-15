"""pubfig_clinical: clinical-research figures on top of pubfig.

Survival (Kaplan-Meier with numbers-at-risk table, log-rank; Aalen-Johansen
cumulative incidence for competing risks), forest plots with aligned text
columns, Bland-Altman agreement, ROC/PR with DeLong CI, calibration, and
CONSORT/PRISMA-style flow diagrams.

Scope rule: estimates that come from a model the user fitted elsewhere (Cox
HR, adjusted OR, subgroup interaction P) are displayed as supplied, never
recomputed here. This module computes only transparent nonparametric
quantities from raw data: Kaplan-Meier, log-rank, Aalen-Johansen, empirical
ROC/AUC with DeLong variance, Bland-Altman limits, binned calibration.
"""
from __future__ import annotations

import math
import re
import textwrap
import warnings
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

import pubfig as pf


def _norm_ppf(q: float) -> float:
    try:
        from scipy.stats import norm
        return float(norm.ppf(q))
    except ImportError:
        return {0.975: 1.959964, 0.95: 1.644854, 0.995: 2.575829}.get(q, 1.959964)


def _chi2_sf(x: float, df: int) -> float:
    try:
        from scipy.stats import chi2
        return float(chi2.sf(x, df))
    except ImportError:
        if df == 1:
            return math.erfc(math.sqrt(x / 2))
        raise


# ---------------------------------------------------------------------------
# Kaplan-Meier
# ---------------------------------------------------------------------------
@dataclass
class KMTable:
    time: np.ndarray        # step times, starting at 0
    surv: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    n_risk: np.ndarray
    n_event: np.ndarray
    n_censor: np.ndarray
    censor_times: np.ndarray
    se: np.ndarray | None = None  # Greenwood standard error of S(t)

    def at(self, t: float) -> float:
        idx = np.searchsorted(self.time, t, side="right") - 1
        return float(self.surv[max(idx, 0)])


def kaplan_meier(time, event, level: float = 0.95) -> KMTable:
    """Product-limit estimate with pointwise log(-log) (exponential Greenwood) CI."""
    t = np.asarray(time, float)
    e = np.asarray(event).astype(int)
    if t.shape != e.shape:
        raise ValueError("time and event must have equal length")
    if (t < 0).any() or not set(np.unique(e)) <= {0, 1}:
        raise ValueError("time must be >= 0 and event coded 0 (censored) / 1 (event)")
    z = _norm_ppf(0.5 + level / 2)
    uniq = np.unique(t)
    times, surv, lo, hi, nr, ne, nc, ses = [0.0], [1.0], [1.0], [1.0], [len(t)], [0], [0], [0.0]
    s, gw = 1.0, 0.0
    for u in uniq:
        at_risk = int((t >= u).sum())
        d = int(((t == u) & (e == 1)).sum())
        c = int(((t == u) & (e == 0)).sum())
        if d > 0:
            s *= 1 - d / at_risk
            if at_risk > d:
                gw += d / (at_risk * (at_risk - d))
        if s > 0 and s < 1:
            se = math.sqrt(gw) / abs(math.log(s))
            l_, h_ = s ** math.exp(z * se), s ** math.exp(-z * se)
        else:
            l_, h_ = (s, s)
        times.append(float(u)); surv.append(s); lo.append(l_); hi.append(h_)
        nr.append(at_risk); ne.append(d); nc.append(c); ses.append(s * math.sqrt(gw))
    return KMTable(np.array(times), np.array(surv), np.array(lo), np.array(hi), np.array(nr),
                   np.array(ne), np.array(nc), np.unique(t[e == 0]), np.array(ses))


def km_truncation_time(km: KMTable, *, min_at_risk: int | None = None, max_se: float | None = None) -> float:
    """Last time the curve is shown under the stated rules (journal or protocol).

    min_at_risk: stop before the number at risk falls below this (EJVES, JEVT: 10).
    max_se: stop before the Greenwood SE of S(t) exceeds this (JVS, JEVT: 0.10).
    The SE rule is absolute: at low survival it can stay under 10% with very
    few patients left, so pair it with an at-risk floor when follow-up is long.
    """
    end = float(km.time[-1])
    for i in range(1, len(km.time)):
        bad = (min_at_risk is not None and km.n_risk[i] < min_at_risk) or \
              (max_se is not None and km.se is not None and km.se[i] > max_se)
        if bad:
            cut = float(km.time[i - 1])
            if cut <= 0:
                warnings.warn("truncation rule fails from the first time point (arm too small); curve shown "
                              "untruncated: report this arm in the text or state the exception in the legend")
                return end
            return cut
    return end


def number_at_risk(time, at_times) -> list[int]:
    t = np.asarray(time, float)
    return [int((t >= a).sum()) for a in at_times]


def cumulative_counts(time, event, at_times) -> tuple[list[int], list[int]]:
    """Cumulative events and censored by each time (KMunicate extended table)."""
    t, e = np.asarray(time, float), np.asarray(event).astype(int)
    ev = [int(((t <= a) & (e == 1)).sum()) for a in at_times]
    ce = [int(((t <= a) & (e == 0)).sum()) for a in at_times]
    return ev, ce


def logrank_test(time, event, group) -> dict:
    """k-sample log-rank (Mantel-Haenszel) test; returns chi2, df, p."""
    t = np.asarray(time, float)
    e = np.asarray(event).astype(int)
    g = np.asarray(group)
    labels = list(dict.fromkeys(g.tolist()))
    k = len(labels)
    if k < 2:
        raise ValueError("need at least two groups")
    O = np.zeros(k); E = np.zeros(k); V = np.zeros((k, k))
    for u in np.unique(t[e == 1]):
        at = t >= u
        n = at.sum()
        d = ((t == u) & (e == 1)).sum()
        nj = np.array([(at & (g == lab)).sum() for lab in labels], float)
        dj = np.array([((t == u) & (e == 1) & (g == lab)).sum() for lab in labels], float)
        O += dj
        E += d * nj / n
        if n > 1:
            V += d * (n - d) / (n - 1) * (np.diag(nj / n) - np.outer(nj, nj) / n ** 2)
    diff = (O - E)[:-1]
    Vr = V[:-1, :-1]
    chi2 = float(diff @ np.linalg.solve(Vr, diff))
    return {"chi2": chi2, "df": k - 1, "p": _chi2_sf(chi2, k - 1), "observed": dict(zip(labels, O.tolist())),
            "expected": dict(zip(labels, E.tolist()))}


def cumulative_incidence(time, status, cause: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Aalen-Johansen cumulative incidence for one cause with competing risks.

    status: 0 censored, 1..K cause codes. Returns (times, CIF). Use this
    instead of 1 - KM when a competing event (e.g. non-cardiovascular death)
    precludes the event of interest: 1 - KM overstates incidence there.
    """
    t = np.asarray(time, float)
    s = np.asarray(status).astype(int)
    times, cif = [0.0], [0.0]
    surv, F = 1.0, 0.0
    for u in np.unique(t):
        n = (t >= u).sum()
        d_all = ((t == u) & (s > 0)).sum()
        d_k = ((t == u) & (s == cause)).sum()
        if n == 0:
            continue
        F += surv * d_k / n
        surv *= 1 - d_all / n
        times.append(float(u)); cif.append(F)
    return np.array(times), np.array(cif)


def km_plot(ax, time, event, group=None, *, order: Sequence | None = None, labels: Mapping | None = None,
            colors: Sequence[str] | None = None, linestyles: Sequence | None = None, failure: bool = False,
            ci: bool = True, ci_tint: float = 0.8, ci_style: str = "auto", ci_times: Sequence[float] | None = None,
            truncate: str | dict | None = "auto", censor_marks: bool = True, xmax: float | None = None,
            at_times: Sequence[float] | None = None, risk_ax=None, risk_extended: bool = False,
            xlabel: str = "Time", ylabel: str | None = None, percent: bool = True, ylim: tuple | None = None,
            show_logrank: bool = False, stats_style: str = "ama", annotation: str | None = None,
            annotation_xy: tuple[float, float] | str = "auto", legend: str = "direct") -> dict:
    """Kaplan-Meier (or cumulative-incidence 1 - S when failure=True) plot.

    Follows Pocock, Clayton & Altman (Lancet 2002) and KMunicate (Morris et al,
    BMJ Open 2019): numbers at risk under the x-axis (risk_ax), confidence
    bands, censoring marks, and no extrapolation beyond reliable follow-up
    (set xmax where numbers at risk become small). With ``failure=True`` plot
    upward cumulative incidence and choose a y-limit that does not exaggerate
    small differences; state the axis range in the legend.

    annotation: supplied effect text, e.g. pubfig.fmt_estimate(hr, lo, hi, "HR")
    from the user's Cox model. This function never fits a hazard ratio.

    Each arm ends at its own last follow-up (never extended to a common xmax).
    truncate: "auto" applies the target journal's rule from the preset
    (JVS: SE > 10%; EJVES: < 10 at risk; JEVT: both), a dict such as
    {"min_at_risk": 10, "max_se": 0.10}, or None.
    ci_style: "band" (tinted band; translucent when arms overlap), "bars"
    (vertical 95% CI bars at ci_times, the JVS alternative), "none", or "auto"
    (bands, or none when the journal forbids CI display, as JEVT does).
    """
    t = np.asarray(time, float)
    e = np.asarray(event).astype(int)
    g = np.zeros(t.size, dtype=object) if group is None else np.asarray(group, dtype=object)
    groups = list(order) if order is not None else list(dict.fromkeys(g.tolist()))
    colors = colors or ([pf.ARMS["intervention"], pf.ARMS["control"]] if len(groups) == 2 else pf.CATEGORICAL)
    linestyles = linestyles or (["-", (0, (4, 2))] if len(groups) == 2 else ["-"] * len(groups))
    labels = labels or {gr: str(gr) for gr in groups}
    xmax = xmax or float(t.max())
    spec = getattr(pf.root_figure(ax), "_pubfig_spec", None)
    rules = set(spec.preset.get("rules", [])) if spec else set()
    if truncate == "auto":
        trunc = {}
        if "km_truncate_se_10pct" in rules or "km_valid_se_lt_10pct_and_10_at_risk" in rules:
            trunc["max_se"] = 0.10
        if "km_truncate_below_10_at_risk" in rules or "km_valid_se_lt_10pct_and_10_at_risk" in rules:
            trunc["min_at_risk"] = 10
    else:
        trunc = dict(truncate or {})
    if ci_style == "auto":
        ci_style = "none" if ("km_no_ci_bands" in rules or not ci) else "band"
    if not ci:
        ci_style = "none"
    results, ends, cut, ci_rng = {}, {}, {}, [math.inf, -math.inf]
    lw = mpl.rcParams["lines.linewidth"]
    for i, gr in enumerate(groups):
        m = g == gr
        km = kaplan_meier(t[m], e[m])
        y, lo, hi = km.surv, km.lower, km.upper
        if failure:
            y, lo, hi = 1 - y, 1 - hi, 1 - lo
        scale = 100 if percent else 1
        last = float(t[m].max())                       # this arm's own follow-up
        end = min(xmax, last, km_truncation_time(km, **trunc) if trunc else last)
        ends[gr] = end
        cut[gr] = end < min(xmax, last) - 1e-12      # shortened by the truncation rule
        keep = km.time <= end
        tt = np.append(km.time[keep], end)
        yy = np.append(y[keep], y[keep][-1]) * scale
        col = colors[i % len(colors)]
        if ci_style != "none":
            ci_rng = [min(ci_rng[0], float(np.min(lo[keep])) * scale), max(ci_rng[1], float(np.max(hi[keep])) * scale)]
        if ci_style == "band":
            translucent = len(groups) > 1
            ax.fill_between(tt, np.append(lo[keep], lo[keep][-1]) * scale, np.append(hi[keep], hi[keep][-1]) * scale,
                            step="post", color=col if translucent else pf.tint(col, ci_tint),
                            alpha=0.16 if translucent else None, lw=0, zorder=1)
        elif ci_style == "bars":
            marks = ci_times if ci_times is not None else [x for x in (at_times or []) if 0 < x <= end]
            step = 0.012 * xmax                                   # offset arms so bars do not overlap
            edge = (len(groups) - 1) / 2 * step + 0.004 * xmax     # keep the outermost bar inside the axes
            for j, x in enumerate(marks):
                if x > end:
                    continue
                k = np.searchsorted(km.time, x, side="right") - 1
                xo = min(max(x, edge), xmax - edge) + (i - (len(groups) - 1) / 2) * step
                ax.errorbar([xo], [y[k] * scale], yerr=[[(y[k] - lo[k]) * scale], [(hi[k] - y[k]) * scale]],
                            fmt="none", ecolor=col, elinewidth=mpl.rcParams["axes.linewidth"],
                            capsize=mpl.rcParams["errorbar.capsize"], zorder=2)
            ax._pubfig_error_kind = "95% CI"
        ax.step(tt, yy, where="post", color=col, lw=lw, ls=linestyles[i % len(linestyles)],
                label=labels.get(gr, str(gr)), zorder=3)
        if censor_marks and km.censor_times.size:
            ct = km.censor_times[km.censor_times <= end]
            cy = np.array([km.at(c) for c in ct])
            cy = (1 - cy if failure else cy) * scale
            ax.plot(ct, cy, ls="none", marker="|", ms=mpl.rcParams["lines.markersize"] * 0.9,
                    mew=mpl.rcParams["axes.linewidth"], color=col, zorder=4)
        results[gr] = km
    ax._pubfig_km = {"failure": failure, "ci": ci_style != "none", "ends": ends, "truncation": trunc,
                     "truncated": cut, "risk_table": risk_ax is not None,
                     "ci_range": tuple(ci_rng) if ci_style != "none" else None}
    ax.set_xlim(0, xmax)
    if ylim is not None:
        ax.set_ylim(*ylim)
    elif not failure:
        ax.set_ylim(0, 100 if percent else 1)
    else:
        ax.set_ylim(bottom=0)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel or (("Cumulative incidence" if failure else "Survival probability") + (" (%)" if percent else "")))
    if at_times is not None:
        ax.set_xticks(at_times)
    ticks = [x for x in ax.get_xticks() if 0 <= x <= xmax + 1e-9]
    if legend == "direct":
        _km_direct_labels(ax, groups, labels, colors, results, failure, percent, ends)
    elif legend == "legend":
        ax.legend(loc="lower left" if not failure else "upper left")
    lr = None
    parts = []
    if annotation:
        parts = [(annotation, "normal")] if isinstance(annotation, str) else list(annotation)
    if show_logrank and len(groups) > 1:
        keep = np.isin(g, groups)
        lr = logrank_test(t[keep], e[keep], g[keep])
        parts += [("\nLog-rank " if parts else "Log-rank ", "normal")] + pf.fmt_p(lr["p"], stats_style, markup="parts")
    risk = None
    if risk_ax is not None:
        risk = risk_table(risk_ax, t, e, g, groups, labels, colors, ticks, extended=risk_extended, xmax=xmax, main_ax=ax)
    if parts:   # after the risk table: its row labels change the panel's width
        _place_annotation(ax, parts, annotation_xy)
    return {"km": results, "logrank": lr, "risk_table": risk, "ticks": ticks, "ends": ends, "truncation": trunc}


def _drawn_points(ax) -> np.ndarray:
    """Display-space samples of step curves and band outlines (for placement)."""
    from matplotlib import cbook
    pts = []
    for ln in ax.get_lines():
        if not ln.get_visible():
            continue
        xy = np.column_stack([np.asarray(ln.get_xdata(), float), np.asarray(ln.get_ydata(), float)])
        if len(xy) < 1:
            continue
        if ln.get_drawstyle().startswith("steps") and len(xy) > 1:
            sx, sy = cbook.pts_to_poststep(xy[:, 0], xy[:, 1])
            xy = np.column_stack([sx, sy])
        px = ln.get_transform().transform(xy)
        px = px[np.isfinite(px).all(1)]
        if ln.get_linestyle() in ("None", "none", "", " "):
            pts.append(px)          # markers only (censor ticks): never join them with segments
            continue
        if len(px) < 2:
            continue
        seg = np.diff(px, axis=0)
        k = np.clip(np.ceil(np.hypot(seg[:, 0], seg[:, 1]) / 3.0), 1, 400).astype(int)   # a sample every ~3 px
        idx = np.repeat(np.arange(len(seg)), k)
        frac = np.concatenate([np.arange(m) / m for m in k])
        pts.append(np.vstack([px[:-1][idx] + seg[idx] * frac[:, None], px[-1:]]))
    return np.vstack(pts) if pts else np.empty((0, 2))


def _pt(size) -> float:
    """rcParams font size (number or name such as 'medium') in points."""
    from matplotlib.font_manager import FontProperties
    return FontProperties(size=size).get_size_in_points()


def _legend_clear_of_data(ax, **kw):
    """Legend inside the axes at kw['loc'] if it covers no drawn line; otherwise
    below the x-axis label, offset in points so later layout changes keep the gap.
    Re-decided by pubfig.settle once the layout is final."""
    leg = _place_legend(ax, dict(kw))

    def redo():
        if ax.get_legend() is not None:
            ax.get_legend().remove()
        _place_legend(ax, dict(kw))
    pf.on_settle(ax, redo)
    return leg


def _place_legend(ax, kw):
    leg = ax.legend(**kw)
    fig = ax.figure
    fig.canvas.draw()
    bb = leg.get_window_extent(fig.canvas.get_renderer())
    pts = _drawn_points(ax)
    if not len(pts) or not ((pts[:, 0] > bb.x0) & (pts[:, 0] < bb.x1) & (pts[:, 1] > bb.y0) & (pts[:, 1] < bb.y1)).any():
        return leg
    leg.remove()
    rc = mpl.rcParams
    dy = (rc["xtick.major.size"] + rc["xtick.major.pad"] + _pt(rc["xtick.labelsize"]) * 1.2
          + rc["axes.labelpad"] + _pt(rc["axes.labelsize"]) * 1.3 + 2)
    from matplotlib.transforms import ScaledTranslation
    kw = {k: v for k, v in kw.items() if k != "loc"}
    return ax.legend(loc="upper center", bbox_to_anchor=(0.5, 0),
                     bbox_transform=ax.transAxes + ScaledTranslation(0, -dy / 72, fig.dpi_scale_trans), **kw)


def _place_annotation(ax, parts, xy):
    """Put a statistics annotation where it covers the fewest curve and band samples.

    xy="auto" tries the four inner corners; an explicit (x, y) in axes
    fraction is used as given (bottom-left anchored).
    """
    fs = mpl.rcParams["legend.fontsize"]
    if xy != "auto":
        return pf.rich_text(ax, *xy, parts, ha="left", va="bottom", fontsize=fs)
    state = {"ab": _best_corner(ax, parts, fs)}

    def redo():
        state["ab"].remove()
        state["ab"] = _best_corner(ax, parts, fs)
    pf.on_settle(ax, redo)
    return state["ab"]


def _best_corner(ax, parts, fs):
    fig = ax.figure
    fig.canvas.draw()
    pts = _drawn_points(ax)
    bands = [c for c in ax.collections if hasattr(c, "get_paths")]
    best, best_cost = None, None
    for x, y, ha, va in [(0.03, 0.97, "left", "top"), (0.97, 0.03, "right", "bottom"),
                         (0.03, 0.03, "left", "bottom"), (0.97, 0.97, "right", "top")]:
        ab = pf.rich_text(ax, x, y, parts, ha=ha, va=va, fontsize=fs)
        fig.canvas.draw()
        bb = ab.get_window_extent(fig.canvas.get_renderer())
        cost = int(((pts[:, 0] > bb.x0) & (pts[:, 0] < bb.x1) & (pts[:, 1] > bb.y0) & (pts[:, 1] < bb.y1)).sum()) * 10 if len(pts) else 0
        grid = np.array([[gx, gy] for gx in np.linspace(bb.x0, bb.x1, 9) for gy in np.linspace(bb.y0, bb.y1, 5)])
        for c in bands:
            for path in c.get_paths():
                cost += int(path.transformed(c.get_transform()).contains_points(grid).sum())
        ab.remove()
        if best_cost is None or cost < best_cost:
            best, best_cost = (x, y, ha, va), cost
    x, y, ha, va = best
    return pf.rich_text(ax, x, y, parts, ha=ha, va=va, fontsize=fs)


def _km_direct_labels(ax, groups, labels, colors, results, failure, percent, ends):
    fig = ax.figure
    fig.canvas.draw()
    scale = 100 if percent else 1
    ys = []
    for gr in groups:
        v = results[gr].at(ends[gr])
        ys.append((1 - v if failure else v) * scale)
    disp = [ax.transData.transform((ends[gr], y))[1] for gr, y in zip(groups, ys)]
    sep = mpl.rcParams["legend.fontsize"] * 1.2 * fig.dpi / 72
    pos = np.array(disp, float)
    for _ in range(40):
        moved = False
        idx = np.argsort(pos)
        for a, b in zip(idx[:-1], idx[1:]):
            if pos[b] - pos[a] < sep:
                sh = (sep - (pos[b] - pos[a])) / 2
                pos[a] -= sh; pos[b] += sh; moved = True
        if not moved:
            break
    for k, gr in enumerate(groups):
        dy = (pos[k] - disp[k]) * 72 / fig.dpi
        ax.annotate(labels.get(gr, str(gr)), (ends[gr], ys[k]), xytext=(3, dy), textcoords="offset points",
                    ha="left", va="center", color=colors[k % len(colors)], fontsize=mpl.rcParams["legend.fontsize"],
                    annotation_clip=False)


def risk_table(ax, time, event, group, groups, labels, colors, ticks, *, extended: bool = False, xmax=None,
               main_ax=None, title: str = "No. at risk"):
    """Numbers at risk aligned to the survival plot's x ticks.

    extended=True adds cumulative events and censored per KMunicate:
    'at risk (events) [censored]'.
    """
    t, e, g = np.asarray(time, float), np.asarray(event).astype(int), np.asarray(group, dtype=object)
    n = len(groups)
    ax.set_xlim(main_ax.get_xlim() if main_ax is not None else (0, xmax))
    ax.set_ylim(n - 0.5, -0.5 - (0.9 if title else 0))
    ax.axis("off")
    fs = mpl.rcParams["xtick.labelsize"]
    table = {}
    rows = {}
    for gr in groups:
        m = g == gr
        nr = number_at_risk(t[m], ticks)
        row = [str(x) for x in nr]
        if extended:
            ev, ce = cumulative_counts(t[m], e[m], ticks)
            row = [f"{a} ({b}) [{c}]" for a, b, c in zip(nr, ev, ce)]
        rows[gr] = row
    # labels end left of the widest first-column entry (centred on x = 0)
    first_w = max(len(r[0]) for r in rows.values()) * fs * 0.56 / 2 + fs * 0.6
    blend = mpl.transforms.blended_transform_factory(ax.transAxes, ax.transData)
    if title:
        head = title + (" (events) [censored]" if extended else "")
        ax.annotate(head, (0, -0.5 - 0.45), xycoords=blend, xytext=(-first_w, 0), textcoords="offset points",
                    ha="right", va="center", fontsize=fs, fontweight="bold", annotation_clip=False)
    for i, gr in enumerate(groups):
        row = rows[gr]
        table[gr] = row
        for x, s in zip(ticks, row):
            ax.text(x, i, s, ha="center", va="center", fontsize=fs, color=pf.NEUTRALS["ink"], clip_on=False)
        ax.annotate(labels.get(gr, str(gr)), (0, i), xycoords=blend, xytext=(-first_w, 0), textcoords="offset points",
                    ha="right", va="center", fontsize=fs, color=colors[i % len(colors)], annotation_clip=False)
    return table


def km_figure(spec, time, event, group, *, risk_rows: int | None = None, height_ratio: float = 0.24, **kwargs):
    """Survival figure with its risk table on a shared x-axis at final size."""
    n = risk_rows or len(set(np.asarray(group, dtype=object).tolist()))
    fig = pf.figure(spec)
    gs = fig.add_gridspec(2, 1, height_ratios=[1, height_ratio * max(1, n / 2)], hspace=0.0)
    ax = fig.add_subplot(gs[0])
    rax = fig.add_subplot(gs[1], sharex=ax)
    out = km_plot(ax, time, event, group, risk_ax=rax, **kwargs)
    return fig, ax, rax, out


# ---------------------------------------------------------------------------
# Forest plot
# ---------------------------------------------------------------------------
@dataclass
class ForestRow:
    label: str
    est: float | None = None
    lo: float | None = None
    hi: float | None = None
    cols: Sequence[str] = ()
    indent: int = 0
    header: bool = False
    summary: bool = False
    weight: float | None = None
    p_text: str | None = None


def forest_plot(spec, rows: Sequence[ForestRow | Mapping], *, col_titles: Sequence[str] = (),
                est_title: str = "HR (95% CI)", p_title: str | None = "P for interaction",
                log: bool = True, ref: float = 1.0, xlim: tuple[float, float] | None = None,
                xticks: Sequence[float] | None = None, xlabel: str = "Hazard ratio (95% CI)",
                favours: tuple[str, str] | None = None, color: str | None = None, digits: int = 2,
                label_width_mm: float | None = None, col_width_mm: float | None = None, est_width_mm: float | None = None,
                p_width_mm: float | None = None, row_pt: float | None = None, stats_style: str = "ama",
                fig=None, subplotspec=None):
    """Forest plot with aligned text columns at final size.

    Values sit in their own columns, never on the markers (polish-sci-figures
    rule). Square area scales with ``weight`` (e.g. inverse variance) when
    supplied; ``summary`` rows draw a diamond. Ratio measures use a log axis
    with the null line at 1 so equal ratios look equally large in each
    direction. Estimates are displayed as supplied (from the user's model).
    Returns (fig, axes dict).

    Standalone, the figure is spec.width_mm wide and as tall as the rows need.
    To make the forest plot one panel of a larger figure, pass ``fig`` and a
    ``subplotspec`` (for example ``gs[:, 1]`` beside a survival panel), or a
    SubFigure as ``fig`` alone (stacked panels: a subfigure keeps the forest
    from inheriting the other panel's margins). The columns are built as inset
    axes of an invisible host axes filling that region, so constrained layout
    keeps headers, tick labels, and favours labels clear of the other panels.
    Give the region enough height for the rows (a warning says how much) and
    label the panel with ``axes["host"]``.
    """
    rows = [r if isinstance(r, ForestRow) else ForestRow(**r) for r in rows]
    color = color or pf.CATEGORICAL[0]
    fs = mpl.rcParams["xtick.labelsize"]
    row_pt = row_pt or fs * 1.75
    n = len(rows)
    ncol = len(col_titles)
    host = None
    if fig is not None and subplotspec is None:
        subplotspec = fig.add_gridspec(1, 1)[0]      # fill the given (sub)figure
    if subplotspec is not None:
        fig = fig or subplotspec.get_gridspec().figure
        if fig is None:
            raise ValueError("pass fig= with subplotspec=")
        host = fig.add_subplot(subplotspec)
        host.set_axis_off()
        fig.canvas.draw()                 # resolve the layout so the region's width is known
        W = host.get_window_extent().width / fig.dpi * 25.4
    else:
        W = spec.width_mm
    pad_mm = 2.0
    _probe = plt.figure(figsize=(4, 1))
    _r = _probe.canvas.get_renderer()

    def text_w(strings, bold=False):
        """Exact rendered width (mm) of the widest line, measured with the current font."""
        lines = [ln for s_ in strings if s_ for ln in str(s_).split("\n")]
        if not lines:
            return pad_mm
        widths = []
        for ln in lines:
            t = _probe.text(0, 0, ln, fontsize=fs, fontweight="bold" if bold else "normal")
            widths.append(t.get_window_extent(_r).width / _probe.dpi * 25.4)
            t.remove()
        return max(widths) + pad_mm

    if col_width_mm is None:
        col_widths = [max(text_w([t], bold=True), text_w([r.cols[i] if i < len(r.cols) else "" for r in rows]))
                      for i, t in enumerate(col_titles)]
    else:
        col_widths = [col_width_mm] * ncol
    est_strings = [pf.fmt_estimate(r.est, r.lo, r.hi, digits=digits, style=stats_style, compact=True)
                   for r in rows if r.est is not None]
    est_w = est_width_mm or max(text_w([est_title], bold=True), text_w(est_strings, bold=True))
    p_w = (p_width_mm or max(text_w(["P " + p_title[2:].replace(" ", "\n", 1)] if p_title.startswith("P ") else [p_title], bold=True),
                             text_w([r.p_text for r in rows if r.p_text]))) if p_title else 0.0
    indent_mm = fs * 0.5 * 25.4 / 72 * 2
    label_w = label_width_mm or min(0.42 * W, max(text_w(["Subgroup"], bold=True),
                                                  max((text_w([r.label], bold=r.header or r.summary) + indent_mm * r.indent
                                                       for r in rows), default=0)))
    plt.close(_probe)
    plot_w = W - label_w - sum(col_widths) - est_w - p_w - 2
    if plot_w < 25:
        where = (f"the forest region is {W:.0f} mm wide: widen it (width_ratios) or stack the panels"
                 if host is not None else "use a wider figure")
        raise ValueError(f"forest plot area only {plot_w:.0f} mm wide at {fs:g} pt text; {where}, "
                         "or use fewer columns or shorter labels")
    widths = [label_w] + col_widths + [plot_w, est_w] + ([p_w] if p_title else [])
    if host is None:
        bottom_mm = (fs * (2.6 if favours else 1.5) + fs * 1.6) * 25.4 / 72 + 3
        height_mm = (n + 2.6) * row_pt * 25.4 / 72 + bottom_mm
        fig = plt.figure(figsize=(pf.mm(W), pf.mm(height_mm)))
        fig._pubfig_spec = spec
        gs = fig.add_gridspec(1, len(widths), width_ratios=widths, left=0.01, right=0.99,
                              bottom=bottom_mm / height_mm, top=1 - (row_pt * 1.6 * 25.4 / 72) / height_mm, wspace=0.0)
        axes = [fig.add_subplot(gs[0, i]) for i in range(len(widths))]
    else:
        tot = float(sum(widths))
        x0s = np.concatenate([[0.0], np.cumsum(widths)[:-1]]) / tot
        axes = [host.inset_axes([x0, 0.0, w / tot, 1.0]) for x0, w in zip(x0s, widths)]
    ylim = (n - 0.5, -0.6)
    for a in axes:
        a.patch.set_visible(False)   # never let one column's background hide another column's text
        a.set_ylim(*ylim)
        a.set_yticks([])
        for s in a.spines.values():
            s.set_visible(False)
        a.tick_params(left=False, bottom=False, labelbottom=False)
    lab_ax = axes[0]
    col_axes = axes[1:1 + ncol]
    pax = axes[1 + ncol]
    est_ax = axes[2 + ncol]
    p_ax = axes[3 + ncol] if p_title else None
    head_y = -1.15
    lab_ax.text(0, head_y, "Subgroup", ha="left", va="center", fontsize=fs, fontweight="bold", transform=_bt(lab_ax))
    for a, title in zip(col_axes, col_titles):
        a.text(0.5, head_y, title, ha="center", va="center", fontsize=fs, fontweight="bold", transform=_bt(a))
    est_ax.text(0.5, head_y, est_title, ha="center", va="center", fontsize=fs, fontweight="bold", transform=_bt(est_ax))
    if p_ax:
        if isinstance(p_title, str) and p_title.startswith("P "):
            # italic P, rest wrapped onto a second line: "P for" / "interaction"
            ptitle = [("P", "bolditalic"), (" " + p_title[2:].replace(" ", "\n", 1), "bold")]
            pf.rich_text(p_ax, 0.5, head_y, ptitle, transform=_bt(p_ax), ha="center", va="center", fontsize=fs)
        else:
            p_ax.text(0.5, head_y, p_title, ha="center", va="center", fontsize=fs, fontweight="bold", transform=_bt(p_ax))
    weights = np.array([r.weight for r in rows if r.weight], float)
    wmax = weights.max() if weights.size else None
    ests = [v for r in rows for v in (r.lo, r.hi) if v is not None]
    if xlim is None:
        lo_, hi_ = min(ests + [ref]), max(ests + [ref])
        if log:
            xlim = (10 ** math.floor(math.log10(lo_) * 4) / 4, 10 ** math.ceil(math.log10(hi_) * 4) / 4)
            xlim = (min(xlim[0], ref / 1.25), max(xlim[1], ref * 1.25))
        else:
            pad = (hi_ - lo_) * 0.08
            xlim = (lo_ - pad, hi_ + pad)
    if log:
        pax.set_xscale("log")
    pax.set_xlim(*xlim)
    pax.axvline(ref, color=pf.NEUTRALS["reference"], lw=mpl.rcParams["axes.linewidth"], zorder=0)
    ms_base = mpl.rcParams["lines.markersize"]
    for i, r in enumerate(rows):
        weight = "bold" if (r.header or r.summary) else "normal"
        lab_ax.text(0.01 + indent_mm * r.indent / label_w, i, r.label, ha="left", va="center", fontsize=fs,
                    fontweight=weight, transform=_bt(lab_ax))
        for a, val in zip(col_axes, r.cols):
            a.text(0.5, i, val, ha="center", va="center", fontsize=fs, transform=_bt(a))
        if r.est is None:
            continue
        if r.summary:
            h = 0.32
            pax.add_patch(Polygon([[r.lo, i], [r.est, i - h], [r.hi, i], [r.est, i + h]], closed=True,
                                  facecolor=pf.NEUTRALS["ink"], edgecolor="none", zorder=3))
        else:
            pax.plot([r.lo, r.hi], [i, i], color=color, lw=mpl.rcParams["lines.linewidth"], zorder=2,
                     solid_capstyle="butt")
            size = ms_base * (0.7 + 1.1 * math.sqrt(r.weight / wmax)) if (r.weight and wmax) else ms_base * 1.1
            pax.plot([r.est], [i], marker="s", ms=size, color=color, mec="none", zorder=3)
            if r.lo < xlim[0] or r.hi > xlim[1]:
                warnings.warn(f"row {r.label!r}: CI extends beyond xlim; add an arrow or widen xlim")
        est_ax.text(0.5, i, pf.fmt_estimate(r.est, r.lo, r.hi, digits=digits, style=stats_style, compact=True),
                    ha="center", va="center", fontsize=fs, fontweight=weight, transform=_bt(est_ax))
        if p_ax and r.p_text:
            p_ax.text(0.5, i, r.p_text, ha="center", va="center", fontsize=fs, transform=_bt(p_ax))
    pax.spines["bottom"].set_visible(True)
    pax.spines["bottom"].set_linewidth(mpl.rcParams["axes.linewidth"])
    pax.tick_params(bottom=True, labelbottom=True, length=2.5)
    if xticks is not None:
        pax.set_xticks(xticks)
        pax.set_xticklabels([f"{x:g}" for x in xticks])
        pax.minorticks_off()
    pax.set_xlabel(xlabel)
    if favours:
        # below the axis label: tick labels + x label occupy ~2.9 font heights
        trans = mpl.transforms.blended_transform_factory(pax.transData, pax.transAxes)
        dy = -(fs * 1.2 + fs * 1.35 + mpl.rcParams["xtick.major.size"] + mpl.rcParams["xtick.major.pad"] + 3.0)
        pax.annotate("← " + favours[0], (ref, 0), xycoords=trans, xytext=(-2, dy), textcoords="offset points",
                     ha="right", va="top", fontsize=fs, color=pf.NEUTRALS["muted"], annotation_clip=False)
        pax.annotate(favours[1] + " →", (ref, 0), xycoords=trans, xytext=(2, dy), textcoords="offset points",
                     ha="left", va="top", fontsize=fs, color=pf.NEUTRALS["muted"], annotation_clip=False)
    if host is None:
        fig._pubfig_kind = "forest"
    else:
        host._pubfig_kind = "forest"
        fig.canvas.draw()
        pitch_pt = pax.get_window_extent().height / fig.dpi * 72 / (n + 0.1)   # display px -> pt
        if pitch_pt < fs * 1.25:
            need_mm = (n + 0.1) * fs * 1.6 * 25.4 / 72
            warnings.warn(f"forest rows are {pitch_pt:.1f} pt apart at {fs:g} pt text; give the forest region "
                          f"about {need_mm:.0f} mm of plot height (plus headers and axis labels)")
    return fig, {"labels": lab_ax, "columns": col_axes, "plot": pax, "estimates": est_ax, "p": p_ax, "host": host}


def _bt(ax):
    return mpl.transforms.blended_transform_factory(ax.transAxes, ax.transData)


# ---------------------------------------------------------------------------
# Bland-Altman
# ---------------------------------------------------------------------------
def bland_altman(ax, method_a, method_b, *, unit: str = "", percent: bool = False, show_ci: bool = True,
                 color: str | None = None, label_a: str = "A", label_b: str = "B", digits: int = 1,
                 proportional_bias: bool = True) -> dict:
    """Bland-Altman agreement plot (Bland & Altman, Lancet 1986).

    Plots difference (A - B) against the mean of A and B with the mean bias
    and 95% limits of agreement (bias +/- 1.96 SD). ``show_ci`` shades the
    approximate 95% CI of the bias (t-based) and of each limit
    (SE approx sqrt(3 s^2 / n), per the 1986 paper). ``percent`` uses
    100*(A-B)/mean for ratio-scaled error. Reports a regression slope of
    difference on mean as a proportional-bias check.
    """
    a, b = np.asarray(method_a, float), np.asarray(method_b, float)
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok], b[ok]
    mean = (a + b) / 2
    diff = a - b
    if percent:
        diff = 100 * diff / mean
    n = diff.size
    bias = float(diff.mean())
    sd = float(diff.std(ddof=1))
    loa = (bias - 1.96 * sd, bias + 1.96 * sd)
    from pubfig_plots import t_quantile
    tq = t_quantile(0.95, n - 1)
    se_b = sd / math.sqrt(n)
    se_l = math.sqrt(3 * sd ** 2 / n)
    color = color or pf.CATEGORICAL[0]
    ax.scatter(mean, diff, s=mpl.rcParams["lines.markersize"] ** 2 * 0.8, color=color, edgecolor="white",
               linewidths=pf.outline_width(ax), zorder=3)
    x0, x1 = mean.min(), mean.max()
    pad = (x1 - x0) * 0.04
    ax.set_xlim(x0 - pad, x1 + pad)
    lw = mpl.rcParams["axes.linewidth"]
    for val, ls in ((bias, "-"), (loa[0], (0, (4, 2))), (loa[1], (0, (4, 2)))):
        ax.axhline(val, color=pf.NEUTRALS["ink"], lw=lw * 1.2, ls=ls, zorder=2)
    if show_ci:
        for val, se in ((bias, se_b), (loa[0], se_l), (loa[1], se_l)):
            ax.axhspan(val - tq * se, val + tq * se, color=pf.NEUTRALS["band"], lw=0, zorder=1)
    u = f" {unit}" if unit and not percent else ("%" if percent else "")
    fs = mpl.rcParams["legend.fontsize"]
    for val, txt in ((loa[1], "+1.96 SD"), (bias, "Mean"), (loa[0], f"{pf.MINUS}1.96 SD")):
        ax.annotate(f"{txt}\n{val:.{digits}f}{u}".replace("-", pf.MINUS), (1, val),
                    xycoords=("axes fraction", "data"), xytext=(3, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=fs, annotation_clip=False, linespacing=1.1)
    ax.set_xlabel(f"Mean of {label_a} and {label_b}" + (f" ({unit})" if unit else ""))
    ax.set_ylabel(f"{label_a} {pf.MINUS} {label_b}" + (" (% of mean)" if percent else (f" ({unit})" if unit else "")))
    out = {"n": n, "bias": bias, "sd": sd, "loa_low": loa[0], "loa_high": loa[1],
           "bias_ci": (bias - tq * se_b, bias + tq * se_b), "loa_ci_halfwidth": tq * se_l}
    if proportional_bias and n > 2:
        slope, intercept = np.polyfit(mean, diff, 1)
        r = np.corrcoef(mean, diff)[0, 1]
        out.update({"pb_slope": float(slope), "pb_intercept": float(intercept), "pb_r": float(r)})
    return out


# ---------------------------------------------------------------------------
# ROC, PR, calibration
# ---------------------------------------------------------------------------
def roc_curve(y, score) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    y = np.asarray(y).astype(int)
    s = np.asarray(score, float)
    order = np.argsort(-s, kind="mergesort")
    s, y = s[order], y[order]
    distinct = np.where(np.diff(s))[0]
    idx = np.r_[distinct, y.size - 1]
    tps = np.cumsum(y)[idx]
    fps = 1 + idx - tps
    tpr = np.r_[0, tps / y.sum()]
    fpr = np.r_[0, fps / (y.size - y.sum())]
    thr = np.r_[np.inf, s[idx]]
    return fpr, tpr, thr


def auc_delong(y, score, level: float = 0.95) -> dict:
    """AUC with DeLong variance (fast midrank algorithm, Sun & Xu 2014)."""
    y = np.asarray(y).astype(int)
    s = np.asarray(score, float)
    pos, neg = s[y == 1], s[y == 0]
    m, n = pos.size, neg.size
    if m == 0 or n == 0:
        raise ValueError("need both outcome classes")

    def midrank(x):
        order = np.argsort(x, kind="mergesort")
        xs = x[order]
        ranks = np.empty(x.size)
        i = 0
        while i < x.size:
            j = i
            while j < x.size and xs[j] == xs[i]:
                j += 1
            ranks[order[i:j]] = 0.5 * (i + j - 1) + 1
            i = j
        return ranks

    allr = midrank(np.r_[pos, neg])
    tx, ty = midrank(pos), midrank(neg)
    auc = (allr[:m].sum() - m * (m + 1) / 2) / (m * n)
    v01 = (allr[:m] - tx) / n
    v10 = 1 - (allr[m:] - ty) / m
    var = np.var(v01, ddof=1) / m + np.var(v10, ddof=1) / n
    se = math.sqrt(var)
    z = _norm_ppf(0.5 + level / 2)
    # logit-transformed interval stays inside (0, 1)
    if 0 < auc < 1:
        lg = math.log(auc / (1 - auc))
        se_lg = se / (auc * (1 - auc))
        lo, hi = 1 / (1 + math.exp(-(lg - z * se_lg))), 1 / (1 + math.exp(-(lg + z * se_lg)))
    else:
        lo = hi = auc
    return {"auc": float(auc), "se": se, "ci_low": lo, "ci_high": hi, "n_pos": int(m), "n_neg": int(n)}


def roc_plot(ax, y, scores: Mapping[str, Sequence[float]], *, colors=None, level: float = 0.95, digits: int = 2,
             legend_loc: str = "auto") -> dict:
    """Empirical ROC curves with AUC (DeLong CI) in the legend; chance diagonal.

    legend_loc="auto" keeps the legend in the lower right when it clears the
    curves and the diagonal, and moves it below the axis label when it does not
    (large journal type in a narrow panel); any matplotlib loc forces a place.
    """
    colors = colors or pf.CATEGORICAL
    ax.plot([0, 1], [0, 1], color=pf.NEUTRALS["reference"], lw=mpl.rcParams["axes.linewidth"], ls=(0, (3, 2)), zorder=1)
    out = {}
    for i, (name, sc) in enumerate(scores.items()):
        fpr, tpr, _ = roc_curve(y, sc)
        st = auc_delong(y, sc, level)
        ax.step(fpr, tpr, where="post", color=colors[i % len(colors)], zorder=2,
                label=f"{name}: AUC {st['auc']:.{digits}f} ({st['ci_low']:.{digits}f}{pf.MINUS if False else '-'}{st['ci_high']:.{digits}f})")
        out[name] = st
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(f"1 {pf.MINUS} specificity")
    ax.set_ylabel("Sensitivity")
    if legend_loc == "auto":
        _legend_clear_of_data(ax, loc="lower right", handlelength=1.2)
    else:
        ax.legend(loc=legend_loc, handlelength=1.2)
    return out


def precision_recall(ax, y, scores: Mapping[str, Sequence[float]], *, colors=None):
    """PR curves with the prevalence baseline (informative when classes are imbalanced)."""
    y = np.asarray(y).astype(int)
    colors = colors or pf.CATEGORICAL
    prev = y.mean()
    ax.axhline(prev, color=pf.NEUTRALS["reference"], lw=mpl.rcParams["axes.linewidth"], ls=(0, (3, 2)))
    out = {}
    for i, (name, sc) in enumerate(scores.items()):
        s = np.asarray(sc, float)
        order = np.argsort(-s, kind="mergesort")
        yy = y[order]
        tp = np.cumsum(yy)
        k = np.arange(1, yy.size + 1)
        prec, rec = tp / k, tp / y.sum()
        ap = float(np.sum(np.diff(np.r_[0, rec]) * prec))
        ax.step(np.r_[0, rec], np.r_[1, prec], where="post", color=colors[i % len(colors)], label=f"{name}: AP {ap:.2f}")
        out[name] = {"average_precision": ap, "prevalence": float(prev)}
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Recall (sensitivity)")
    ax.set_ylabel("Precision (PPV)")
    ax.legend(loc="upper right")
    return out


def _wilson(k, n, z=1.959964):
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    d = 1 + z ** 2 / n
    c = (p + z ** 2 / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / d
    return c - h, c + h


def _logistic_recalibration(y, p):
    """Fit logit(P(y=1)) = a + b * logit(p) by Newton-Raphson; returns (a, b)."""
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    x = np.log(p / (1 - p))
    X = np.c_[np.ones_like(x), x]
    beta = np.array([0.0, 1.0])
    for _ in range(50):
        mu = 1 / (1 + np.exp(-(X @ beta)))
        W = mu * (1 - mu)
        H = X.T @ (X * W[:, None])
        g = X.T @ (np.asarray(y) - mu)
        step = np.linalg.solve(H, g)
        beta += step
        if np.abs(step).max() < 1e-9:
            break
    return float(beta[0]), float(beta[1])


def calibration_plot(ax, y, p, *, bins: int = 10, strategy: str = "quantile", color: str | None = None,
                     hist_ax=None) -> dict:
    """Binned observed vs predicted risk with Wilson 95% CIs and the ideal line.

    Reports calibration-in-the-large (observed - mean predicted) and the
    logistic recalibration slope. For development vs validation claims follow
    TRIPOD: internal performance is not external validation.
    """
    y = np.asarray(y).astype(int)
    p = np.asarray(p, float)
    color = color or pf.CATEGORICAL[0]
    if strategy == "quantile":
        edges = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
    else:
        edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, len(edges) - 2)
    mp, ob, lo, hi = [], [], [], []
    for b in range(len(edges) - 1):
        m = idx == b
        if m.sum() == 0:
            continue
        mp.append(p[m].mean())
        k = y[m].sum()
        ob.append(k / m.sum())
        l_, h_ = _wilson(k, m.sum())
        lo.append(l_); hi.append(h_)
    mp, ob, lo, hi = map(np.array, (mp, ob, lo, hi))
    ax.plot([0, 1], [0, 1], color=pf.NEUTRALS["reference"], lw=mpl.rcParams["axes.linewidth"], ls=(0, (3, 2)))
    ax.errorbar(mp, ob, yerr=[ob - lo, hi - ob], fmt="o", color=color, capsize=0, lw=mpl.rcParams["axes.linewidth"])
    top = float(max(mp.max(), hi.max()) * 1.1)
    top = min(1.0, max(top, 0.1))
    ax.set_xlim(0, top)
    ax.set_ylim(0, top)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Predicted risk")
    ax.set_ylabel("Observed proportion")
    ax._pubfig_error_kind = "95% CI"  # Wilson intervals per bin
    a, b = _logistic_recalibration(y, p)
    if hist_ax is not None:
        hist_ax.hist(p, bins=40, range=(0, top), color=pf.NEUTRALS["baseline"], lw=0)
        hist_ax.set_xlim(0, top)
        hist_ax.axis("off")
    return {"citl": float(y.mean() - p.mean()), "recal_intercept": a, "slope": b, "bins": len(mp)}


# ---------------------------------------------------------------------------
# Flow diagrams (CONSORT / PRISMA / STROBE participant flow)
# ---------------------------------------------------------------------------
@dataclass
class Box:
    id: str
    text: str
    col: float = 0.5         # box CENTRE in column units (0.5 = middle of first column)
    row: int = 0             # row index (top = 0)
    width: float = 0.9       # box width in column units
    kind: str = "main"       # main | side (exclusions, reached by a horizontal arrow)
    align: str = "center"    # text alignment inside the box


def flow_diagram(spec, boxes: Sequence[Box | Mapping], edges: Sequence[tuple[str, str]] = (), *,
                 n_cols: int = 2, gap_mm: float = 5.0, stages: Sequence[tuple[str, int, int]] = (),
                 edge_color: str | None = None):
    """Participant-flow layout: boxes on a column/row grid with orthogonal arrows.

    edges: (from_id, to_id). Rules: a side box on the same row as its source
    is reached from the source's edge; a side box between rows is reached from
    the vertical trunk; boxes below are reached by a vertical arrow or an
    elbow. stages: (label, first_row, last_row) drawn as a left-hand band
    (e.g. Enrollment, Allocation, Follow-up, Analysis). All text is live.
    """
    boxes = [b if isinstance(b, Box) else Box(**b) for b in boxes]
    fs = mpl.rcParams["xtick.labelsize"]
    W = spec.width_mm
    char_mm = fs * 0.52 * 25.4 / 72
    line_mm = fs * 1.22 * 25.4 / 72
    stage_w = 0.0
    if stages:
        stage_w = max(len(s[0]) for s in stages) * char_mm + 4.0
    left = 1.0 + stage_w + (1.5 if stages else 0)
    col_w = (W - left - 1.0) / n_cols
    wrapped, heights = {}, {}
    for b in boxes:
        width_mm = b.width * col_w
        chars = max(10, int((width_mm - 3.0) / char_mm))
        lines = []
        for para in b.text.split("\n"):
            para = re.sub(r"\(n = ([\d,]+)\)", lambda m: "(n\u00a0=\u00a0" + m.group(1) + ")", para)
            lines.extend(textwrap.wrap(para, chars, subsequent_indent="  " if para.startswith("\u2022") else "") or [""])
        wrapped[b.id] = "\n".join(lines)
        heights[b.id] = len(lines) * line_mm + 2.6
    n_rows = max(b.row for b in boxes) + 1
    row_h = {r: max([heights[b.id] for b in boxes if b.row == r] or [4.0]) for r in range(n_rows)}
    y_top, y = {}, 1.0
    for r in range(n_rows):
        y_top[r] = y
        y += row_h[r] + gap_mm
    H = y - gap_mm + 1.0
    fig = plt.figure(figsize=(pf.mm(W), pf.mm(H)))
    fig._pubfig_spec = spec
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    lw = max(spec.lines["axes"], 0.5)
    ink = pf.NEUTRALS["ink"]
    geom, kinds = {}, {}
    for b in boxes:
        cx = left + b.col * col_w
        w = b.width * col_w
        h = heights[b.id]
        top = y_top[b.row] + (row_h[b.row] - h) / 2
        x0 = cx - w / 2
        ax.add_patch(Rectangle((x0, top), w, h, fc="white", ec=ink, lw=lw, zorder=2))
        if b.align == "left":
            ax.text(x0 + 1.4, top + h / 2, wrapped[b.id], ha="left", va="center", fontsize=fs, linespacing=1.15, zorder=3)
        else:
            ax.text(cx, top + h / 2, wrapped[b.id], ha="center", va="center", fontsize=fs, linespacing=1.15,
                    multialignment="center", zorder=3)
        geom[b.id] = (x0, top, w, h, cx)
        kinds[b.id] = b.kind
    ec = edge_color or ink
    arrow = dict(arrowstyle="-|>", color=ec, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=6)
    for src, dst in edges:
        x0, t0, w0, h0, c0 = geom[src]
        x1, t1, w1, h1, c1 = geom[dst]
        b0, b1 = t0 + h0, t1 + h1
        right = c1 > c0
        if kinds[dst] == "side":
            if t1 < b0 and b1 > t0:                     # same row: leave from the source edge
                yy = (max(t0, t1) + min(b0, b1)) / 2
                xs = x0 + w0 if right else x0
            else:                                        # between rows: leave from the trunk
                yy = t1 + h1 / 2
                xs = c0
            xt = x1 if right else x1 + w1
            ax.annotate("", (xt, yy), (xs, yy), arrowprops=arrow, zorder=1)
        elif abs(c0 - c1) < 0.5:
            ax.annotate("", (c1, t1), (c1, b0), arrowprops=arrow, zorder=1)
        else:
            mid = (b0 + t1) / 2
            ax.plot([c0, c0, c1], [b0, mid, mid], color=ec, lw=lw, solid_joinstyle="miter", zorder=1)
            ax.annotate("", (c1, t1), (c1, mid), arrowprops=arrow, zorder=1)
    band = pf.tint(pf.CATEGORICAL[0], 0.82)
    for label, r0, r1 in stages:
        top, bot = y_top[r0], y_top[r1] + row_h[r1]
        ax.add_patch(FancyBboxPatch((1.0, top), stage_w, bot - top, boxstyle="round,pad=0,rounding_size=1.0",
                                    fc=band, ec="none", zorder=1))
        ax.text(1.0 + stage_w / 2, (top + bot) / 2, label, ha="center", va="center", fontsize=fs,
                fontweight="bold", zorder=3)
    fig._pubfig_kind = "flow"
    return fig, ax


def consort_diagram(spec, counts: Mapping[str, object], arms: Sequence[str] = ("Intervention", "Control")):
    """Two-arm parallel-group CONSORT flow (enrollment, allocation, follow-up, analysis).

    counts keys (all n are integers; check they add up before drawing):
      assessed, excluded, excluded_reasons (list of 'reason (n = x)'), randomized,
      allocated[arm], received[arm], not_received[arm], lost[arm], discontinued[arm],
      analysed[arm], excluded_analysis[arm]. Optional keys may be omitted.
    """
    c = counts
    _check_consort(c, arms)
    reasons = c.get("excluded_reasons", [])
    excl = f"Excluded (n = {c['excluded']})" + "".join(f"\n\u2022 {r}" for r in reasons)
    boxes = [
        Box("assessed", f"Assessed for eligibility (n = {c['assessed']})", col=1.0, row=0, width=0.8),
        Box("excluded", excl, col=1.62, row=1, width=0.74, kind="side", align="left"),
        Box("randomized", f"Randomized (n = {c['randomized']})", col=1.0, row=2, width=0.8),
    ]
    edges = [("assessed", "randomized"), ("assessed", "excluded")]
    for j, arm in enumerate(arms):
        alloc = f"Allocated to {arm.lower()} (n = {c['allocated'][arm]})"
        if "received" in c:
            alloc += f"\n\u2022 Received allocated intervention (n = {c['received'][arm]})"
        if "not_received" in c:
            alloc += f"\n\u2022 Did not receive allocated intervention (n = {c['not_received'][arm]})"
        fu = f"Lost to follow-up (n = {c.get('lost', {}).get(arm, 0)})"
        if "discontinued" in c:
            fu += f"\nDiscontinued intervention (n = {c['discontinued'][arm]})"
        an = f"Analyzed (n = {c['analysed'][arm]})"
        if "excluded_analysis" in c:
            an += f"\n\u2022 Excluded from analysis (n = {c['excluded_analysis'][arm]})"
        col = 0.5 + j
        boxes += [Box(f"alloc{j}", alloc, col=col, row=3, width=0.94, align="left"),
                  Box(f"fu{j}", fu, col=col, row=4, width=0.94, align="left"),
                  Box(f"an{j}", an, col=col, row=5, width=0.94, align="left")]
        edges += [("randomized", f"alloc{j}"), (f"alloc{j}", f"fu{j}"), (f"fu{j}", f"an{j}")]
    return flow_diagram(spec, boxes, edges, n_cols=2,
                        stages=[("Enrollment", 0, 2), ("Allocation", 3, 3), ("Follow-up", 4, 4), ("Analysis", 5, 5)])


def _check_consort(c, arms):
    problems = []
    if c["assessed"] - c["excluded"] != c["randomized"]:
        problems.append(f"assessed {c['assessed']} - excluded {c['excluded']} != randomized {c['randomized']}")
    if sum(c["allocated"][a] for a in arms) != c["randomized"]:
        problems.append("allocated arms do not sum to randomized")
    for a in arms:
        if "received" in c and "not_received" in c and c["received"][a] + c["not_received"][a] != c["allocated"][a]:
            problems.append(f"{a}: received + not received != allocated")
    if problems:
        warnings.warn("CONSORT counts inconsistent: " + "; ".join(problems))


def prisma2020_diagram(spec, counts: Mapping[str, object]):
    """PRISMA 2020 flow for new systematic reviews (databases and registers only).

    counts keys: databases, registers, duplicates, automation_removed, other_removed,
    screened, screened_excluded, sought, not_retrieved, assessed,
    assessed_excluded_reasons (list of 'reason (n = x)'), studies_included, reports_included
    """
    c = counts
    reasons = "".join(f"\n{r}" for r in c.get("assessed_excluded_reasons", []))
    boxes = [
        Box("ident", f"Records identified from:\nDatabases (n = {c['databases']})\nRegisters (n = {c['registers']})",
            col=0.5, row=0, align="left"),
        Box("removed", "Records removed before screening:\n"
            f"Duplicate records (n = {c['duplicates']})\n"
            f"Marked ineligible by automation tools (n = {c.get('automation_removed', 0)})\n"
            f"Removed for other reasons (n = {c.get('other_removed', 0)})", col=1.5, row=0, align="left", kind="side"),
        Box("screened", f"Records screened (n = {c['screened']})", col=0.5, row=1),
        Box("screen_ex", f"Records excluded (n = {c['screened_excluded']})", col=1.5, row=1, kind="side"),
        Box("sought", f"Reports sought for retrieval (n = {c['sought']})", col=0.5, row=2),
        Box("notret", f"Reports not retrieved (n = {c['not_retrieved']})", col=1.5, row=2, kind="side"),
        Box("assessed", f"Reports assessed for eligibility (n = {c['assessed']})", col=0.5, row=3),
        Box("assess_ex", "Reports excluded:" + reasons, col=1.5, row=3, align="left", kind="side"),
        Box("included", f"Studies included in review (n = {c['studies_included']})\n"
            f"Reports of included studies (n = {c['reports_included']})", col=0.5, row=4),
    ]
    edges = [("ident", "screened"), ("ident", "removed"), ("screened", "sought"), ("screened", "screen_ex"),
             ("sought", "assessed"), ("sought", "notret"), ("assessed", "included"), ("assessed", "assess_ex")]
    return flow_diagram(spec, boxes, edges, n_cols=2,
                        stages=[("Identification", 0, 0), ("Screening", 1, 3), ("Included", 4, 4)])


# ---------------------------------------------------------------------------
# Individual-response displays
# ---------------------------------------------------------------------------
def waterfall_plot(ax, values, *, thresholds: Sequence[float] = (), color_pos: str | None = None,
                   color_neg: str | None = None, ylabel: str = "Change from baseline (%)", sort_desc: bool = True):
    """Per-patient change sorted by magnitude (one bar per patient).

    Bars start at zero by construction; thresholds draw reference lines
    (e.g. a response definition). Each bar is one experimental unit.
    """
    v = np.asarray(values, float)
    v = v[~np.isnan(v)]
    v = np.sort(v)[::-1] if sort_desc else v
    color_pos = color_pos or pf.CATEGORICAL[1]
    color_neg = color_neg or pf.CATEGORICAL[0]
    ax.bar(np.arange(v.size), v, width=0.85, color=[color_pos if x > 0 else color_neg for x in v], lw=0)
    ax.axhline(0, color=pf.NEUTRALS["ink"], lw=mpl.rcParams["axes.linewidth"])
    for th in thresholds:
        pf.reference_line(ax, th, "h")
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    ax.set_xlabel(f"Individual participants (n = {v.size})")
    ax.set_ylabel(ylabel)
    return {"n": int(v.size), "n_increase": int((v > 0).sum()), "n_decrease": int((v < 0).sum())}


def spaghetti_plot(ax, times, values, ids, groups=None, *, colors=None, level: float = 0.95,
                   individual_tint: float = 0.7, xlabel: str = "Time", ylabel: str | None = None) -> dict:
    """Individual trajectories (light) plus group mean with pointwise CI (dark).

    Pointwise intervals are descriptive; a longitudinal model is needed for
    inference about trajectories.
    """
    from pubfig_plots import mean_ci
    t = np.asarray(times, float)
    v = np.asarray(values, float)
    i_ = np.asarray(ids, dtype=object)
    g = np.zeros(t.size, dtype=object) if groups is None else np.asarray(groups, dtype=object)
    colors = colors or pf.CATEGORICAL
    out = {}
    for k, gr in enumerate(dict.fromkeys(g.tolist())):
        col = colors[k % len(colors)]
        m = g == gr
        for pid in dict.fromkeys(i_[m].tolist()):
            mm = m & (i_ == pid)
            o = np.argsort(t[mm])
            ax.plot(t[mm][o], v[mm][o], color=pf.tint(col, individual_tint), lw=mpl.rcParams["lines.linewidth"] * 0.5, zorder=1)
        ut = np.unique(t[m])
        stats = [mean_ci(v[m & (t == u)], level) for u in ut]
        mu = np.array([s[0] for s in stats]); lo = np.array([s[1] for s in stats]); hi = np.array([s[2] for s in stats])
        ax.errorbar(ut, mu, yerr=[mu - lo, hi - mu], color=col, marker="o", capsize=0, zorder=3,
                    lw=mpl.rcParams["lines.linewidth"] * 1.2, label=str(gr) if groups is not None else None)
        out[gr] = {"times": ut.tolist(), "mean": mu.tolist(), "lo": lo.tolist(), "hi": hi.tolist()}
    ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax._pubfig_error_kind = "95% CI"
    return out


__all__ = ["KMTable", "kaplan_meier", "number_at_risk", "cumulative_counts", "logrank_test",
           "cumulative_incidence", "km_plot", "risk_table", "km_figure", "ForestRow", "forest_plot",
           "bland_altman", "roc_curve", "auc_delong", "roc_plot", "precision_recall", "calibration_plot",
           "Box", "flow_diagram", "consort_diagram", "prisma2020_diagram", "waterfall_plot", "spaghetti_plot"]
