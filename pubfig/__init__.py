"""Publication figures: physical size, frozen palette, editable masters."""

from .palette import PALETTES, digest, load_palette
from .style import FigureStyle, apply_publication_style, style_for
from .plots import (
    finalize_figure,
    make_estimation,
    make_grouped_bar,
    make_heatmap,
    make_trend,
)
from .qa import audit_contract, audit_svg

__all__ = [
    "FigureStyle",
    "PALETTES",
    "apply_publication_style",
    "audit_contract",
    "audit_svg",
    "digest",
    "finalize_figure",
    "load_palette",
    "make_estimation",
    "make_grouped_bar",
    "make_heatmap",
    "make_trend",
    "style_for",
]
