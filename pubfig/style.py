"""Physical-size matplotlib style.

Manuscript type is 8 to 9 pt on the real column width. The 24 pt / 3 pt-spine
look from large demo scripts is slide or poster only. Using it on an 85 mm
canvas fails the style gate.
"""

from __future__ import annotations

from dataclasses import dataclass

MM_PER_IN = 25.4


@dataclass(frozen=True)
class FigureStyle:
    mode: str = "manuscript"
    font_size: float = 8.5
    axes_linewidth: float = 0.9
    font_family: str = "Arial"
    width_mm: float = 85.0
    resolved_font: str = "Arial"
    font_exact: bool = True

    @property
    def final_delivery_allowed(self) -> bool:
        return self.font_exact and self.mode_matches_type()

    def mode_matches_type(self) -> bool:
        if self.mode == "manuscript":
            return 7.0 <= self.font_size <= 11.0 and self.axes_linewidth <= 1.6
        if self.mode == "slide":
            return 12.0 <= self.font_size <= 22.0 and self.axes_linewidth <= 2.0
        if self.mode == "poster":
            return 16.0 <= self.font_size <= 32.0
        return False


def figsize_mm(width_mm: float, height_mm: float) -> tuple[float, float]:
    if width_mm <= 0 or height_mm <= 0:
        raise ValueError("Canvas millimetres must be positive")
    return (width_mm / MM_PER_IN, height_mm / MM_PER_IN)


def resolve_font(requested: str) -> tuple[str, bool]:
    from matplotlib import font_manager

    names = {f.name for f in font_manager.fontManager.ttflist}
    if requested in names:
        return requested, True
    for fallback in ("Liberation Sans", "Helvetica", "DejaVu Sans"):
        if fallback in names:
            return fallback, False
    return "DejaVu Sans", False


def style_for(mode: str = "manuscript", width_mm: float = 85.0, font: str = "Arial") -> FigureStyle:
    presets = {
        "manuscript": (8.5, 0.9),
        "slide": (16.0, 1.4),
        "poster": (22.0, 1.6),
    }
    if mode not in presets:
        raise ValueError(f"Unknown mode {mode!r}")
    size, spine = presets[mode]
    resolved, exact = resolve_font(font)
    return FigureStyle(
        mode=mode,
        font_size=size,
        axes_linewidth=spine,
        font_family=font,
        width_mm=width_mm,
        resolved_font=resolved,
        font_exact=exact,
    )


def apply_publication_style(style: FigureStyle | None = None) -> FigureStyle:
    import matplotlib as mpl

    style = style or style_for("manuscript")
    family = style.resolved_font
    mpl.rcParams.update(
        {
            "font.family": family,
            "font.size": style.font_size,
            "axes.labelsize": style.font_size,
            "axes.titlesize": style.font_size,
            "xtick.labelsize": style.font_size,
            "ytick.labelsize": style.font_size,
            "legend.fontsize": style.font_size,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": style.axes_linewidth,
            "xtick.major.width": style.axes_linewidth,
            "ytick.major.width": style.axes_linewidth,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "legend.frameon": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "axes.facecolor": "white",
            "text.color": "#172033",
            "axes.labelcolor": "#172033",
            "xtick.color": "#172033",
            "ytick.color": "#172033",
            "axes.edgecolor": "#172033",
        }
    )
    return style
