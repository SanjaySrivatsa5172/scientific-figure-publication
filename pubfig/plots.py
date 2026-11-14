"""Data figures at a declared physical size.

Helpers follow the figures4papers contracts (grouped bars, trends, heatmaps)
and add an estimation plot so a group comparison does not default to a bar
of means. Statistics are descriptive intervals. This module does not invent
a test, a P value, or a biological unit.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .style import FigureStyle, apply_publication_style, figsize_mm

# Two-sided Student t critical values, alpha 0.05, df 1..30. Beyond 30, 1.96.
_T95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
    26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
}


def t_critical(df: float) -> float:
    if df <= 0:
        raise ValueError("Degrees of freedom must be positive")
    key = int(round(df))
    if key < 1:
        key = 1
    if key > 30:
        return 1.96
    return _T95[key]


def mean_ci(values, alpha_label: str = "95% CI") -> dict:
    y = np.asarray(values, dtype=float)
    if y.ndim != 1 or y.size < 2:
        raise ValueError("Need at least two observations for a mean interval")
    n = int(y.size)
    mean = float(np.mean(y))
    sd = float(np.std(y, ddof=1))
    se = sd / np.sqrt(n)
    t = t_critical(n - 1)
    return {
        "n": n,
        "mean": mean,
        "sd": sd,
        "se": se,
        "df": n - 1,
        "t": t,
        "low": mean - t * se,
        "high": mean + t * se,
        "label": alpha_label,
        "method": "Student t interval on the mean",
    }


def paired_diff_ci(before, after) -> dict:
    a = np.asarray(before, dtype=float)
    b = np.asarray(after, dtype=float)
    if a.shape != b.shape or a.ndim != 1 or a.size < 2:
        raise ValueError("Paired arrays must be the same length, at least 2")
    return mean_ci(a - b)


def finalize_figure(fig, out_path, formats=None, dpi=300, close=True):
    """Save vector masters and a review PNG. No tight bounding box.

    Panels that will be assembled later must share a physical canvas.
    bbox_inches='tight' breaks that contract, so it is not used.
    """
    path = Path(out_path)
    if formats is None:
        formats = ["svg", "pdf", "png"] if path.suffix == "" else [path.suffix.lstrip(".")]
    saved = []
    stem = path if path.suffix == "" else path.with_suffix("")
    stem.parent.mkdir(parents=True, exist_ok=True)
    for fmt in formats:
        target = stem.with_suffix("." + fmt.lower())
        kwargs = {"bbox_inches": None}
        if fmt.lower() in {"png", "jpg", "jpeg", "tif", "tiff"}:
            kwargs["dpi"] = dpi
        fig.savefig(target, **kwargs)
        saved.append(target)
    if close:
        import matplotlib.pyplot as plt

        plt.close(fig)
    return saved


def _colors(roles: dict, n: int) -> list[str]:
    order = ["ours", "strong_baseline", "positive", "negative", "highlight", "sky"]
    picked = [roles[k] for k in order if k in roles]
    if len(picked) < n:
        raise ValueError(f"Palette has {len(picked)} hues, need {n}. Stay within five.")
    if n > 5:
        raise ValueError("At most five semantic hues in one figure")
    return picked[:n]


def make_grouped_bar(
    ax,
    categories,
    series,
    labels,
    ylabel="Value",
    colors=None,
    hatches=None,
    annotate=False,
    ymin=None,
    ymax=None,
):
    categories = list(categories)
    series = [np.asarray(s, dtype=float) for s in series]
    if any(s.shape != (len(categories),) for s in series):
        raise ValueError("Each series must match the category count")
    if len(labels) != len(series):
        raise ValueError("labels and series must have the same length")
    n_cat = len(categories)
    n_ser = len(series)
    if colors is None:
        colors = ["#0072B2"] * n_ser
    if len(colors) < n_ser:
        raise ValueError("Need one color per series")
    hatches = list(hatches or ["", "///", "...", "\\\\\\", "xx"][:n_ser])
    width = 0.8 / n_ser
    x = np.arange(n_cat)
    containers = []
    for i, (s, lab) in enumerate(zip(series, labels)):
        offset = (i - (n_ser - 1) / 2) * width
        bars = ax.bar(
            x + offset,
            s,
            width=width * 0.92,
            label=lab,
            color=colors[i],
            edgecolor="#172033",
            linewidth=0.6,
            hatch=hatches[i] if i < len(hatches) else "",
            zorder=3,
        )
        containers.append(bars)
        if annotate:
            for rect, val in zip(bars, s):
                ax.text(
                    rect.get_x() + rect.get_width() / 2,
                    rect.get_height(),
                    f"{val:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=max(ax.figure.get_size_inches()[0], 1) and ax.yaxis.label.get_size(),
                    color="#172033",
                    clip_on=False,
                )
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.set_ylabel(ylabel)
    ax.legend(ncol=min(n_ser, 3), loc="lower center", bbox_to_anchor=(0.5, 1.02), frameon=False)
    if ymin is not None or ymax is not None:
        lo, hi = ax.get_ylim()
        ax.set_ylim(lo if ymin is None else ymin, hi if ymax is None else ymax)
    return containers


def make_estimation(ax, groups, colors, ylabel, show_points=True):
    """Mean and 95% t interval, with raw points.

    `groups` is a list of {name, values}. This is not a significance test.
    """
    if len(groups) < 2 or len(groups) > 5:
        raise ValueError("Estimation plot supports 2 to 5 groups")
    stats = []
    rng = np.random.default_rng(7)
    for i, group in enumerate(groups):
        y = np.asarray(group["values"], dtype=float)
        st = mean_ci(y)
        st["name"] = group["name"]
        stats.append(st)
        if show_points:
            jitter = rng.uniform(-0.12, 0.12, size=y.size)
            ax.scatter(
                np.full(y.size, i) + jitter,
                y,
                s=18,
                color=colors[i],
                edgecolor="#172033",
                linewidth=0.4,
                zorder=3,
                label=None,
            )
        ax.errorbar(
            i,
            st["mean"],
            yerr=[[st["mean"] - st["low"]], [st["high"] - st["mean"]]],
            fmt="o",
            color="#172033",
            ecolor="#172033",
            elinewidth=1.0,
            capsize=3,
            markersize=5,
            markerfacecolor=colors[i],
            markeredgecolor="#172033",
            zorder=4,
        )
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([g["name"] for g in groups])
    ax.set_ylabel(ylabel)
    ax.set_xlim(-0.55, len(groups) - 0.45)
    return stats


def make_paired_slopes(ax, before, after, names, color, ylabel):
    a = np.asarray(before, dtype=float)
    b = np.asarray(after, dtype=float)
    if a.shape != b.shape:
        raise ValueError("Paired vectors must match")
    for y0, y1 in zip(a, b):
        ax.plot([0, 1], [y0, y1], color="#8A93A0", lw=0.8, zorder=2)
    ax.scatter(np.zeros(a.size), a, s=22, color="#666666", edgecolor="#172033", linewidth=0.4, zorder=3, label=names[0])
    ax.scatter(np.ones(b.size), b, s=22, color=color, edgecolor="#172033", linewidth=0.4, zorder=3, label=names[1])
    ax.plot([0, 1], [np.mean(a), np.mean(b)], color="#172033", lw=1.4, zorder=4, label="Mean")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(names)
    ax.set_xlim(-0.35, 1.35)
    ax.set_ylabel(ylabel)
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3)
    return paired_diff_ci(a, b)


def make_trend(ax, x, y_series, labels, colors=None, ylabel=None, xlabel=None, bands=None):
    x = np.asarray(x, dtype=float)
    series = [np.asarray(y, dtype=float) for y in y_series]
    if any(s.shape != x.shape for s in series):
        raise ValueError("Each trend series must match x")
    if len(labels) != len(series):
        raise ValueError("labels and series must match")
    if colors is None:
        colors = ["#0072B2"] * len(series)
    markers = ["o", "D", "s", "^", "v"]
    for i, (y, lab) in enumerate(zip(series, labels)):
        if bands is not None:
            low, high = bands[i]
            tint = colors[i]
            ax.fill_between(x, low, high, color=tint, alpha=0.18, linewidth=0, zorder=1)
        ax.plot(
            x,
            y,
            color=colors[i],
            lw=1.3,
            marker=markers[i % len(markers)],
            markersize=3.5,
            markeredgecolor="#172033",
            markeredgewidth=0.3,
            label=lab,
            zorder=3,
        )
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.legend(frameon=False, loc="upper left")
    return ax


def make_heatmap(ax, matrix, x_labels=None, y_labels=None, cbar_label=None, vmin=None, vmax=None):
    """Vector cells (Rectangles), not a raster image, so the SVG stays editable."""
    from matplotlib.patches import Rectangle
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    m = np.asarray(matrix, dtype=float)
    if m.ndim != 2:
        raise ValueError("Heatmap matrix must be 2D")
    vmin = float(np.min(m) if vmin is None else vmin)
    vmax = float(np.max(m) if vmax is None else vmax)
    if vmax == vmin:
        vmax = vmin + 1.0
    cmap = __import__("matplotlib").colormaps["Blues"]
    norm = Normalize(vmin=vmin, vmax=vmax)
    nrows, ncols = m.shape
    for r in range(nrows):
        for c in range(ncols):
            ax.add_patch(
                Rectangle(
                    (c, nrows - 1 - r),
                    1,
                    1,
                    facecolor=cmap(norm(m[r, c])),
                    edgecolor="white",
                    linewidth=0.4,
                )
            )
            shade = norm(m[r, c])
            ink = "#172033" if shade < 0.62 else "#FFFFFF"
            ax.text(
                c + 0.5,
                nrows - 1 - r + 0.5,
                f"{m[r, c]:.2f}",
                ha="center",
                va="center",
                color=ink,
                fontsize=ax.yaxis.label.get_size(),
            )
    ax.set_xlim(0, ncols)
    ax.set_ylim(0, nrows)
    ax.set_xticks(np.arange(ncols) + 0.5)
    ax.set_yticks(np.arange(nrows) + 0.5)
    if x_labels is not None:
        ax.set_xticklabels(list(x_labels))
    if y_labels is not None:
        ax.set_yticklabels(list(reversed(list(y_labels))))
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.14)
    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array(m)
    cbar = ax.figure.colorbar(sm, cax=cax)
    if cbar_label:
        cbar.set_label(cbar_label)
    cbar.outline.set_linewidth(0.4)
    return {"vmin": vmin, "vmax": vmax, "cmap": "Blues", "note": "sequential, not a method palette"}


def new_figure(style: FigureStyle, height_mm: float):
    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    apply_publication_style(style)
    fig, ax = plt.subplots(figsize=figsize_mm(style.width_mm, height_mm))
    fig.subplots_adjust(left=0.20, right=0.96, bottom=0.18, top=0.84)
    return fig, ax
