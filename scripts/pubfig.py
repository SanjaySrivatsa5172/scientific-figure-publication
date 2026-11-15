"""pubfig: publication-figure core for matplotlib.

Sizing at final physical size, journal presets, font resolution, palettes,
colour-vision-deficiency (CVD) checks, aligned panel labels, verified export,
and statistics/notation formatting.

Portability rule: copy this file (plus pubfig_plots.py / pubfig_clinical.py
when used) next to the figure script inside the user's project. A delivered
figure script must never import from the skill folder.

Dependencies: numpy, matplotlib >= 3.7. Optional: Pillow (TIFF/CMYK export,
raster checks), pypdf (PDF font audit lives in figure_qa.py).

Journal values in PRESETS were transcribed from official author instructions
retrieved on the date in each preset's ``retrieved`` field; re-verify before a
real submission because publishers revise them (see references/journal-specs.md).
"""
from __future__ import annotations

import io
import math
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import to_rgb, to_hex

MM_PER_INCH = 25.4
PT_PER_INCH = 72.0


def mm(value: float) -> float:
    """Millimetres to inches (matplotlib figsize unit)."""
    return value / MM_PER_INCH


def pt_to_mm(value: float) -> float:
    return value * MM_PER_INCH / PT_PER_INCH


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------
# Typography keys are final printed sizes in points. "lines" are stroke widths
# in points. "panel" describes the panel-label convention. Every journal entry
# carries its source URL and retrieval date; values not stated by the source
# are None and fall back to GENERIC defaults.

GENERIC = {
    "name": "Generic print (no journal chosen)",
    "widths_mm": {"single": 85.0, "onehalf": 120.0, "double": 178.0},
    "max_height_mm": 230.0,
    "font": {"family": "Arial", "min_pt": 6.0, "max_pt": 9.0},
    "type": {"label": 7.0, "tick": 6.5, "legend": 6.5, "annot": 6.5, "panel": 8.0, "title": 7.0},
    "lines": {"axes": 0.6, "data": 1.0, "minimum": 0.25, "grid": 0.4},
    "panel": {"style": "A", "weight": "bold"},
    "dpi": {"line": 1000, "halftone": 300, "combination": 600},
    "formats": ["pdf", "svg", "png"],
    "color_mode": "RGB",
    "stats": "ama",
    "source": None,
    "retrieved": None,
}

PRESETS: dict[str, dict] = {
    "generic": GENERIC,
    # Non-print delivery modes (polish-sci-figures "presentation"/"showcase").
    "presentation": {
        "name": "Slide (16:9, 13.333 x 7.5 in)",
        "widths_mm": {"full": 310.0, "half": 150.0, "third": 98.0},
        "max_height_mm": 160.0,
        "font": {"family": "Arial", "min_pt": 12.0, "max_pt": 28.0},
        "type": {"label": 16.0, "tick": 14.0, "legend": 14.0, "annot": 14.0, "panel": 18.0, "title": 18.0},
        "lines": {"axes": 1.2, "data": 2.5, "minimum": 1.0, "grid": 0.8},
        "panel": {"style": "A", "weight": "bold"},
        "dpi": {"line": 300, "halftone": 300, "combination": 300},
        "formats": ["svg", "png"],
        "color_mode": "RGB",
        "stats": "ama",
        "source": None,
        "retrieved": None,
    },
    "poster": {
        "name": "Poster panel (A0 portrait, 3-column grid)",
        "widths_mm": {"column": 250.0, "double": 520.0},
        "max_height_mm": 400.0,
        "font": {"family": "Arial", "min_pt": 18.0, "max_pt": 40.0},
        "type": {"label": 24.0, "tick": 20.0, "legend": 20.0, "annot": 20.0, "panel": 28.0, "title": 28.0},
        "lines": {"axes": 1.5, "data": 3.0, "minimum": 1.0, "grid": 1.0},
        "panel": {"style": "A", "weight": "bold"},
        "dpi": {"line": 300, "halftone": 300, "combination": 300},
        "formats": ["pdf", "png"],
        "color_mode": "RGB",
        "stats": "ama",
        "source": None,
        "retrieved": None,
    },
    "showcase": {
        "name": "Web/README image readable at 1200 px wide",
        "widths_mm": {"full": 254.0},
        "max_height_mm": 300.0,
        "font": {"family": "Arial", "min_pt": 9.0, "max_pt": 18.0},
        "type": {"label": 11.0, "tick": 10.0, "legend": 10.0, "annot": 10.0, "panel": 13.0, "title": 12.0},
        "lines": {"axes": 0.9, "data": 1.8, "minimum": 0.5, "grid": 0.6},
        "panel": {"style": "A", "weight": "bold"},
        "dpi": {"line": 120, "halftone": 120, "combination": 120},
        "formats": ["png", "svg"],
        "color_mode": "RGB",
        "stats": "ama",
        "source": None,
        "retrieved": None,
    },
}



_REPLACE_KEYS = {"widths_mm", "rules", "formats"}  # never inherit generic widths a journal did not state


def _merge(base: dict, override: dict) -> dict:
    out = {}
    for key, value in base.items():
        if key in _REPLACE_KEYS and key in override:
            out[key] = override[key]
        elif key in override and isinstance(value, dict) and isinstance(override[key], dict):
            out[key] = _merge(value, {k: v for k, v in override[key].items() if v is not None})
        elif key in override and override[key] is not None:
            out[key] = override[key]
        else:
            out[key] = value
    for key, value in override.items():
        if key not in out:
            out[key] = value
    return out


def register_preset(key: str, preset: dict) -> None:
    """Add or replace a preset (e.g. a journal not shipped with the skill)."""
    PRESETS[key.lower()] = _merge(GENERIC, preset)


# Journal presets. Values transcribed from official author instructions
# retrieved 2026-11-14 (verbatim quotes and URLs: assets/journal-specs/*.json).
# "note" records conflicts and values a journal does not state (filled from the
# publisher's generic guide or, failing that, GENERIC). Re-verify before submission.
R = "2026-11-14"
_T = lambda label, tick, panel, legend=None, annot=None, title=None: {  # noqa: E731
    "label": label, "tick": tick, "legend": legend or tick, "annot": annot or tick, "panel": panel, "title": title or label}
_L = lambda axes, data, minimum, grid=None: {"axes": axes, "data": data, "minimum": minimum, "grid": grid or max(minimum, axes * 0.6)}  # noqa: E731
_JOURNAL_PRESETS: dict[str, dict] = {
    # ---- general science -------------------------------------------------
    "nature": dict(name="Nature", widths_mm={"single": 89, "onehalf": 120, "onehalf_max": 136, "double": 183},
                   max_height_mm=170, font={"family": "Arial", "min_pt": 5, "max_pt": 7}, type=_T(7, 6, 8),
                   lines=_L(0.5, 1.0, 0.25), panel={"style": "a", "weight": "bold"},
                   dpi={"line": 1200, "halftone": 450, "combination": 600}, formats=["pdf", "eps", "svg", "png"],
                   stats="generic_lz", source="https://www.nature.com/nature/for-authors/final-submission", retrieved=R,
                   note="Nature pages conflict: 89/183 mm and 247 mm page depth (final submission) vs 90/180 mm and 170 mm "
                        "(formatting guide); photos 300 dpi vs 450 dpi checklist. Main figures must be editable vector; no outlined text."),
    "natureportfolio": dict(name="Nature Portfolio research journals (Nat Med, Nat Commun)", widths_mm={"single": 88, "double": 180},
                            max_height_mm=185, font={"family": "Arial", "min_pt": 5, "max_pt": 7}, type=_T(7, 6, 8),
                            lines=_L(0.5, 1.0, 0.25), panel={"style": "a", "weight": "bold"},
                            dpi={"line": 1200, "halftone": 300, "combination": 600}, formats=["pdf", "eps", "png"],
                            stats="generic_lz", source="https://www.nature.com/documents/NRJs-guide-to-preparing-final-artwork.pdf", retrieved=R,
                            note="Max height depends on legend length (~130-225 mm). Nature Communications and Scientific Reports state lines >= 1 pt: use 'naturecomms'."),
    "naturecomms": dict(name="Nature Communications / Scientific Reports", widths_mm={"single": 88, "double": 180},
                        max_height_mm=230, font={"family": "Arial", "min_pt": 5, "max_pt": 7}, type=_T(7, 6.5, 7),
                        lines=_L(1.0, 1.25, 1.0), panel={"style": "a", "weight": "bold"},
                        dpi={"line": 1200, "halftone": 300, "combination": 600}, formats=["pdf", "eps", "tif"],
                        stats="generic_lz", rules=["legend_max_350_words"], source="https://www.nature.com/ncomms/submit/how-to-submit", retrieved=R,
                        note="States lines >= 1 pt and panel labels the same size as other text; no pt range stated (Nature 5-7 pt used)."),
    "science": dict(name="Science", widths_mm={"single": 57, "double": 121, "triple": 184}, max_height_mm=230,
                    font={"family": "Helvetica", "min_pt": 5, "max_pt": 9}, type=_T(7, 6, 10), lines=_L(0.5, 1.0, 0.5),
                    panel={"style": "A", "weight": "bold"}, dpi={"line": 1200, "halftone": 300, "combination": 600},
                    formats=["pdf", "eps", "tif"], stats="generic_lz",
                    source="https://www.science.org/content/page/instructions-preparing-initial-manuscript", retrieved=R,
                    note="Web pages: ~7 pt (min 5), lines >= 0.5 pt; 2025 prep guide: 9/18.3 cm, 6-9 pt, max 3 sizes, lines >= 0.28 pt. No PowerPoint/Word."),
    "scienceadv": dict(name="Science Advances", widths_mm={"single": 90, "onehalf": 144, "double": 184}, max_height_mm=199,
                       font={"family": "Myriad Pro", "min_pt": 6, "max_pt": 9}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.28),
                       panel={"style": "A", "weight": "bold"}, dpi={"line": 1200, "halftone": 300, "combination": 300},
                       formats=["pdf", "ai", "tif"], stats="generic_lz",
                       source="https://www.science.org/content/page/science-advances-information-authors", retrieved=R,
                       note="Myriad preferred (Arial is the usual substitute); RGB mandatory; files > 600 dpi are downsampled."),
    "cell": dict(name="Cell Press (Cell, Cell Reports)", widths_mm={"single": 85, "onehalf": 114, "double": 174}, max_height_mm=200,
                 font={"family": "Arial", "min_pt": 6, "max_pt": 8}, type=_T(7, 6.5, 8), lines=_L(0.5, 1.0, 0.5),
                 panel={"style": "A", "weight": "bold"}, dpi={"line": 1000, "halftone": 300, "combination": 500},
                 formats=["tif", "pdf"], stats="generic_lz", source="https://www.cell.com/information-for-authors/figure-guidelines", retrieved=R,
                 note="Arial only. Recommended max 6.5 x 8 in (16.5 x 20 cm) although full width is 17.4 cm. Graphical abstract 1200 px square, Arial 8-12 pt."),
    "pnas": dict(name="PNAS", widths_mm={"single": 87, "onehalf": 114, "double": 178}, max_height_mm=225,
                 font={"family": "Arial", "min_pt": 6, "max_pt": 12}, type=_T(7, 6.5, 8), lines=_L(0.5, 1.0, 0.25),
                 panel={"style": "A", "weight": "bold"}, dpi={"line": 1200, "halftone": 300, "combination": 600},
                 formats=["pdf", "eps", "tif"], stats="generic_lz", rules=["numeric_axes_include_zero"],
                 source="https://www.pnas.org/pb-assets/authors/digitalart-1675347574760.pdf", retrieved=R,
                 note="Digital Art Guidelines: numerical axes must go to 0 except log axes. Panel style not stated."),
    "plos": dict(name="PLOS journals", widths_mm={"single": 132, "full": 190.5, "min": 66.8}, max_height_mm=222.3,
                 font={"family": "Arial", "min_pt": 8, "max_pt": 12}, type=_T(9, 8, 11), lines=_L(0.75, 1.25, 0.5),
                 panel={"style": "A", "weight": "bold"}, dpi={"line": 600, "halftone": 300, "combination": 600},
                 formats=["tif", "eps"], stats="generic_lz",
                 source="https://journals.plos.org/plosone/s/figures", retrieved=R,
                 note="TIFF or EPS only; Arial/Times/Symbol 8-12 pt; panel labels '(A) or (a)'; > 600 dpi may be resized. Line weight not stated."),
    "elife": dict(name="eLife", widths_mm={"single": 100, "double": 200}, max_height_mm=250,
                  font={"family": "Arial", "min_pt": 7, "max_pt": 12}, type=_T(8, 7, 10), lines=_L(0.75, 1.25, 0.5),
                  panel={"style": "A", "weight": "bold"}, dpi={"line": 600, "halftone": 300, "combination": 300},
                  formats=["tif", "pdf", "eps"], stats="generic_lz", source="https://elife-rp.msubmit.net/html/elife-rp_author_instructions.html", retrieved=R,
                  note="Only minimum widths (10 cm; 20 cm for full-page) and >= 300 dpi are stated; type and lines use generic values."),
    # ---- publishers ---------------------------------------------------------
    "elsevier": dict(name="Elsevier (generic artwork instructions)", widths_mm={"single": 90, "onehalf": 140, "double": 190, "min": 30},
                     max_height_mm=230, font={"family": "Arial", "min_pt": 6, "max_pt": 9}, type=_T(7, 7, 9),
                     lines=_L(0.5, 1.0, 0.25), panel={"style": "A", "weight": "bold"},
                     dpi={"line": 1000, "halftone": 300, "combination": 500}, formats=["eps", "pdf", "tif"], stats="ama",
                     source="https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions", retrieved=R,
                     note="7 pt text, >= 6 pt sub/superscripts; lines 0.25 pt recommended (0.1 absolute minimum); 1200 dpi for very fine line art. Max height not stated."),
    "springer": dict(name="Springer journals (generic)", widths_mm={"single": 84, "double": 174, "small_journal": 119},
                     max_height_mm=234, font={"family": "Arial", "min_pt": 8, "max_pt": 12}, type=_T(9, 8, 10),
                     lines=_L(0.6, 1.0, 0.3), panel={"style": "a", "weight": "bold"},
                     dpi={"line": 1200, "halftone": 300, "combination": 600}, formats=["eps", "pdf", "tif"], stats="generic_lz",
                     source="https://link.springer.com/journal/11145/submission-guidelines", retrieved=R,
                     note="Text about 2-3 mm (8-12 pt); a 2021 PDF lists 39/84/129/174 mm. Small-format journals: 119 x 195 mm."),
    "bmc": dict(name="BMC journals", widths_mm={"single": 85, "double": 170}, max_height_mm=225,
                font={"family": "Arial", "min_pt": 6, "max_pt": 12}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.3),
                panel={"style": "a", "weight": "bold"}, dpi={"line": 600, "halftone": 300, "combination": 300},
                formats=["pdf", "eps", "tif", "png"], stats="generic_lz",
                rules=["legend_title_max_15_words", "legend_max_300_words"], source="https://link.springer.com/journal/12916/submission-guidelines", retrieved=R,
                note="Lines > 0.25 pt; height includes legend; fonts embedded. Font size not stated."),
    "wiley": dict(name="Wiley journals (generic)", widths_mm={"single": 80, "double": 180}, max_height_mm=230,
                  font={"family": "Arial", "min_pt": 6, "max_pt": 10}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.25),
                  panel={"style": "A", "weight": "bold"}, dpi={"line": 600, "halftone": 300, "combination": 600},
                  formats=["pdf", "eps", "tif"], stats="generic_lz", source="https://authors.wiley.com/author-resources/Journal-Authors/Prepare/manuscript-preparation-guidelines.html/figure-preparation.html", retrieved=R,
                  note="80-180 mm; fonts, line weight, panel style and max height not stated."),
    "oup": dict(name="Oxford University Press journals (generic)", widths_mm={"single": 85, "double": 178}, max_height_mm=230,
                font={"family": "Arial", "min_pt": 7, "max_pt": 10}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.25),
                panel={"style": "A", "weight": "bold"}, dpi={"line": 1200, "halftone": 600, "combination": 900},
                formats=["eps", "pdf", "tif"], stats="generic_lz", source="https://academic.oup.com/pages/for-authors/journals/preparing-and-submitting-your-manuscript", retrieved=R,
                note="Widths not stated (measure the journal); colour halftone 300, greyscale 600, combination/line 600-900, mono line 1200 dpi; lines 0.25-1 pt."),
    "tandf": dict(name="Taylor & Francis journals (generic)", widths_mm={"single": 85, "double": 178}, max_height_mm=230,
                  font={"family": "Arial", "min_pt": 7, "max_pt": 10}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.3),
                  panel={"style": "(a)", "weight": "bold"}, dpi={"line": 1200, "halftone": 600, "combination": 600},
                  formats=["eps", "tif"], stats="generic_lz", source="https://authorservices.taylorandfrancis.com/editorial-policies/images-and-figures/", retrieved=R,
                  note="PDF figures not accepted; colour photos 300, greyscale 600 dpi. Widths not stated."),
    "acs": dict(name="ACS journals (JACS appendix)", widths_mm={"single": 84.6, "double": 177.8, "double_min": 105.8},
                max_height_mm=232.8, font={"family": "Arial", "min_pt": 4.5, "max_pt": 10}, type=_T(7, 6.5, 8),
                lines=_L(0.5, 1.0, 0.5), panel={"style": "a", "weight": "bold"},
                dpi={"line": 1200, "halftone": 300, "combination": 600}, formats=["tif", "pdf", "eps"], stats="generic_lz",
                source="https://researcher-resources.acs.org/publish/author_guidelines/pdf?coden=jacsat", retrieved=R,
                note="Lettering >= 4.5 pt (JACS Au checklist says >= 8 pt); max depth includes caption; TOC graphic <= 3.25 x 1.75 in."),
    "royalsociety": dict(name="Royal Society journals", widths_mm={"single": 85, "double": 178}, max_height_mm=230,
                         font={"family": "Times New Roman", "min_pt": 7.5, "max_pt": 11}, type=_T(9, 8, 9),
                         lines=_L(0.5, 1.0, 0.3), panel={"style": "(a)", "weight": "normal"},
                         dpi={"line": 600, "halftone": 300, "combination": 300}, formats=["pdf", "eps", "tif"], stats="generic_lz",
                         source="https://royalsociety.org/journals/authors/author-guidelines/", retrieved=R,
                         note="Panel labels italic letters in roman brackets '(a)'; widths not stated."),
    "frontiers": dict(name="Frontiers journals", widths_mm={"single": 85, "double": 180}, max_height_mm=230,
                      font={"family": "Arial", "min_pt": 8, "max_pt": 12}, type=_T(9, 8, 10), lines=_L(2.0, 2.0, 2.0),
                      panel={"style": "A", "weight": "bold"}, dpi={"line": 300, "halftone": 300, "combination": 300},
                      formats=["tif", "jpg", "eps"], stats="generic_lz", source="https://www.frontiersin.org/guidelines/author-guidelines", retrieved=R,
                      note="States lines 'no smaller than two points wide' (unusually heavy; confirm with the editorial office)."),
    "mdpi": dict(name="MDPI journals", widths_mm={"single": 85, "double": 170}, max_height_mm=230,
                 font={"family": "Arial", "min_pt": 7, "max_pt": 12}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.3),
                 panel={"style": "(a)", "weight": "normal"}, dpi={"line": 600, "halftone": 600, "combination": 600},
                 formats=["png", "tif", "jpg"], stats="generic_lz", source="https://www.mdpi.com/journal/sensors/instructions", retrieved=R,
                 note="Raster PNG/JPEG/TIFF >= 600 dpi preferred, 'no editable parts'; widths not stated."),
    "ieee": dict(name="IEEE journals", widths_mm={"single": 88.9, "double": 182}, max_height_mm=220,
                 font={"family": "Arial", "min_pt": 8, "max_pt": 10}, type=_T(9, 8, 10), lines=_L(0.5, 1.0, 0.5),
                 panel={"style": "(a)", "weight": "normal"}, dpi={"line": 600, "halftone": 300, "combination": 600},
                 formats=["pdf", "eps", "tif"], stats="generic_lz", source="https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/", retrieved=R,
                 note="Text approx. 9-10 pt; Helvetica/Times/Arial/Cambria/Symbol; embed or outline fonts. Line weight and panel style not stated."),
    "acm": dict(name="ACM (acmart sigconf)", widths_mm={"single": 84.8, "double": 178.0, "acmsmall": 139.1}, max_height_mm=230,
                font={"family": "Arial", "min_pt": 6, "max_pt": 9}, type=_T(8, 7, 8), lines=_L(0.5, 1.0, 0.3),
                panel={"style": "(a)", "weight": "normal"}, dpi={"line": 600, "halftone": 300, "combination": 600},
                formats=["pdf"], stats="generic_lz", source="https://www.acm.org/publications/authors/submissions", retrieved=R,
                note="Column 3.337 in, text 7.006 in (sigconf); body Linux Libertine; every figure needs a \\Description (alt text)."),
    "neurips": dict(name="NeurIPS (neurips_2026.sty)", widths_mm={"single": 139.7, "half": 68.0}, max_height_mm=200,
                    font={"family": "Arial", "min_pt": 6, "max_pt": 10}, type=_T(8, 7, 9), lines=_L(0.6, 1.2, 0.3),
                    panel={"style": "(a)", "weight": "normal"}, dpi={"line": 600, "halftone": 300, "combination": 600},
                    formats=["pdf"], stats="generic_lz", source="https://media.neurips.cc/Conferences/NeurIPS2026/Formatting_Instructions_For_NeurIPS_2026.zip", retrieved=R,
                    note="Text width 5.5 in, one column; body Times 10 pt. Figure fonts are not specified; keep >= 6-7 pt after \\includegraphics scaling."),
    "iclr": dict(name="ICLR (iclr2027_conference.sty)", widths_mm={"single": 139.7, "half": 68.0}, max_height_mm=200,
                 font={"family": "Arial", "min_pt": 6, "max_pt": 10}, type=_T(8, 7, 9), lines=_L(0.6, 1.2, 0.3),
                 panel={"style": "(a)", "weight": "normal"}, dpi={"line": 600, "halftone": 300, "combination": 600},
                 formats=["pdf"], stats="generic_lz", source="https://raw.githubusercontent.com/ICLR/Master-Template/master/iclr2027/iclr2027_conference.sty", retrieved=R, note="Text width 5.5 in."),
    "icml": dict(name="ICML (icml2026.sty)", widths_mm={"single": 82.55, "double": 171.45}, max_height_mm=200,
                 font={"family": "Arial", "min_pt": 6, "max_pt": 9}, type=_T(7.5, 6.5, 8), lines=_L(0.6, 1.0, 0.3),
                 panel={"style": "(a)", "weight": "normal"}, dpi={"line": 600, "halftone": 300, "combination": 600},
                 formats=["pdf"], stats="generic_lz", source="https://media.icml.cc/Conferences/ICML2026/Styles/icml2026.zip", retrieved=R, note="Two columns: 3.25 in column, 6.75 in text."),
    "cvpr": dict(name="CVPR/ICCV (cvpr.sty)", widths_mm={"single": 83.34, "double": 174.6}, max_height_mm=200,
                 font={"family": "Arial", "min_pt": 6, "max_pt": 9}, type=_T(7.5, 6.5, 8), lines=_L(0.6, 1.0, 0.3),
                 panel={"style": "(a)", "weight": "normal"}, dpi={"line": 600, "halftone": 300, "combination": 600},
                 formats=["pdf"], stats="generic_lz", source="https://raw.githubusercontent.com/cvpr-org/author-kit/main/cvpr.sty", retrieved=R,
                 note="Column 3.28125 in per the style file (template prose says 3.25 in); text 6.875 in."),
    "acl": dict(name="ACL / ARR (acl.sty)", widths_mm={"single": 77.0, "double": 160.0}, max_height_mm=200,
                font={"family": "Arial", "min_pt": 6, "max_pt": 9}, type=_T(7.5, 6.5, 8), lines=_L(0.6, 1.0, 0.3),
                panel={"style": "(a)", "weight": "normal"}, dpi={"line": 600, "halftone": 300, "combination": 600},
                formats=["pdf"], stats="generic_lz", source="https://raw.githubusercontent.com/acl-org/acl-style-files/master/acl.sty", retrieved=R, note="A4: column 7.7 cm, text 16 cm."),
    # ---- clinical and cardiovascular ----------------------------------------
    "jacc": dict(name="JACC (defers to Elsevier sizing)", widths_mm={"single": 90, "onehalf": 140, "double": 190},
                 max_height_mm=230, font={"family": "Arial", "min_pt": 7, "max_pt": 12}, type=_T(8, 7, 9),
                 lines=_L(0.5, 1.0, 0.25), panel={"style": "A", "weight": "bold"},
                 dpi={"line": 1200, "halftone": 300, "combination": 500}, formats=["tif", "eps", "pdf"], stats="ama",
                 rules=["avoid_bar_graphs", "legend_title_max_10_words", "legend_max_150_words"],
                 source="https://www.jacc.org/journal/jacc/author-center/for-authors", retrieved=R,
                 note="Live instructions defer to Elsevier; superseded 2024 PDF required TIF, 1200 dpi line art, 12 pt lettering and >= 13 x 18 cm. "
                      "Avoid bar graphs; legend title <= 10 words, legend <= 150 words; no trial logos; AMA style 'with minor modifications'; Central Illustration optional."),
    "jacc_family": dict(name="JACC: Cardiovascular Interventions / Advances / Basic to Translational Science",
                        widths_mm={"single": 177.8, "double": 177.8}, max_height_mm=230,
                        font={"family": "Arial", "min_pt": 10, "max_pt": 14}, type=_T(12, 10, 14, legend=10, annot=10),
                        lines=_L(1.0, 1.5, 0.5), panel={"style": "A", "weight": "bold"},
                        dpi={"line": 1200, "halftone": 300, "combination": 600}, formats=["pdf", "eps", "svg", "tif"], stats="ama",
                        rules=["avoid_bar_graphs", "no_dynamite_plots", "black_white_not_gray"],
                        source="https://www.jacc.org/journal/interventions/author-center/for-authors", retrieved=R,
                        note="Typeset figures >= 7 in wide; lettering optimal 12 pt, minimum 10 pt; no column-with-error-bar plots (Advances/BTS); "
                             "JACC: CI charts in black and white, not gray; Central Illustration required (JACC: CI) with boxed header and title <= 10 words."),
    "aha": dict(name="AHA journals (Circulation, Circ Cardiovasc Interv, Hypertension, ATVB, Stroke)",
                widths_mm={"single": 80, "onehalf": 127.5, "double": 177.5}, max_height_mm=230,
                font={"family": "Arial", "min_pt": 10, "max_pt": 12}, type=_T(10, 10, 12), lines=_L(0.75, 1.25, 0.5),
                panel={"style": "A", "weight": "bold"}, dpi={"line": 1200, "halftone": 600, "combination": 600},
                formats=["tif", "eps", "pdf"], color_mode="RGB", stats="aha", rules=["max_6_panels", "no_headings_on_figure"],
                source="https://www.ahajournals.org/figure-guidelines", retrieved=R,
                note="Font conflict: Figure Guidelines 8-10 pt vs Submission Guidelines >= 10 pt (10 pt satisfies both). Widths only in a 2012 Hypertension PDF. "
                     "Uppercase panel letters upper left; <= 6 panels; RGB not CMYK."),
    "ehj": dict(name="European Heart Journal", widths_mm={"single": 85, "double": 178}, max_height_mm=230,
                font={"family": "Arial", "min_pt": 8, "max_pt": 12}, type=_T(9, 8, 10), lines=_L(0.5, 1.0, 0.25),
                panel={"style": "A", "weight": "bold"}, dpi={"line": 1200, "halftone": 600, "combination": 600},
                formats=["pdf", "eps", "tif"], stats="ehj", rules=["max_6_panels", "km_numbers_at_risk"],
                source="https://academic.oup.com/eurheartj/pages/general_instructions", retrieved=R,
                note="Widths not stated (measure a recent issue). Text >= 2 mm high (about 8 pt); Myriad Pro/Arial/Helvetica. Photos >= 350 dpi (600 rec.), "
                     "line art >= 600 (1200 rec.). Graphical abstract 11.0 x 18.0 cm landscape, 300 ppi, 10-12 pt (>= 8), legend <= 80 words."),
    "eurointervention": dict(name="EuroIntervention", widths_mm={"single": 80, "double": 170}, max_height_mm=230,
                             font={"family": "Arial", "min_pt": 9, "max_pt": 14}, type=_T(12, 10, 13), lines=_L(0.75, 1.25, 0.5),
                             panel={"style": "A", "weight": "bold"}, dpi={"line": 1200, "halftone": 300, "combination": 600},
                             formats=["pptx", "eps", "pdf"], stats="generic_lz",
                             source="https://eurointervention.pcronline.com/author-centre/manuscript-contents", retrieved=R,
                             note="Images >= 8 x 8 cm (one column); lettering optimal 12 pt (minimum not stated); Central Illustration mandatory "
                                  "for main article types; 7 display items (research). dpi not stated (values here are Elsevier-like defaults)."),
    "jvs": dict(name="Journal of Vascular Surgery / JVS-VL", widths_mm={"single": 90, "onehalf": 140, "double": 190, "reference": 76.2},
                max_height_mm=230, font={"family": "Arial", "min_pt": 10, "max_pt": 14}, type=_T(10, 10, 12),
                lines=_L(0.75, 1.25, 0.5), panel={"style": "A", "weight": "bold"},
                dpi={"line": 1000, "halftone": 300, "combination": 500}, formats=["tif", "eps", "jpg"], stats="ama",
                rules=["km_numbers_at_risk", "km_truncate_se_10pct"],
                source="https://www.jvascsurg.org/content/authorinfo", retrieved=R,
                note="Images >= 300 dpi at 3 in wide (900 px); text >= 10 pt; survival curves need n at risk and truncation when SE > 10%; "
                     "AMA Manual of Style (10th ed cited). Widths/line art dpi from Elsevier generic. Optional visual abstract (PowerPoint template)."),
    "ejves": dict(name="European Journal of Vascular and Endovascular Surgery", widths_mm={"single": 90, "double": 190}, max_height_mm=230,
                  font={"family": "Arial", "min_pt": 7, "max_pt": 10}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.25),
                  panel={"style": "A", "weight": "bold"}, dpi={"line": 1000, "halftone": 300, "combination": 500},
                  formats=["tif", "eps", "pdf"], stats="ejves", rules=["km_y_from_zero", "km_numbers_at_risk", "km_truncate_below_10_at_risk", "portrait_only"],
                  source="https://legacyfileshare.elsevier.com/promis_misc/ejves-instructions-for-authors.pdf", retrieved=R,
                  note="Portrait only, one page max; panels A, B, C top left (sub-panels a, b, c); KM y-axis from 0, numbers at risk, truncate below 10 at risk. dpi not stated."),
    "ccv": dict(name="Catheterization and Cardiovascular Interventions (Wiley)", widths_mm={"single": 80, "double": 180}, max_height_mm=230,
                font={"family": "Arial", "min_pt": 7, "max_pt": 10}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.25),
                panel={"style": "A", "weight": "bold"}, dpi={"line": 600, "halftone": 300, "combination": 600},
                formats=["tif", "eps", "pdf"], stats="generic_lz", source="https://onlinelibrary.wiley.com/page/journal/1522726x/homepage/forauthors.html", retrieved=R,
                note="CCI: >= 300 dpi all figures; Wiley line art 600 dpi; print colour charged; central figure encouraged."),
    "jama": dict(name="JAMA Network (incl. JAMA Cardiology)", widths_mm={"single": 85, "double": 178}, max_height_mm=230,
                 font={"family": "Arial", "min_pt": 7, "max_pt": 10}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.25),
                 panel={"style": "A", "weight": "bold"}, dpi={"line": 600, "halftone": 350, "combination": 600},
                 formats=["pdf", "eps", "svg"], stats="ama",
                 rules=["no_pie", "no_3d", "no_stacked_bars", "ratios_log_scale", "errorbars_both_directions", "max_4_panels", "km_numbers_at_risk"],
                 source="https://jamanetwork.com/journals/jama/pages/instructions-for-authors", retrieved=R,
                 note="Graphs redrawn by JAMA staff (submit vector); images >= 350 ppi, line drawings >= 600 ppi; no pie, 3-D or stacked bars; "
                      "error bars in both directions; ratios on a log scale; KM as step curve with numbers at risk; <= 4 panels."),
    "nejm": dict(name="New England Journal of Medicine", widths_mm={"single": 85, "double": 178}, max_height_mm=230,
                 font={"family": "Arial", "min_pt": 7, "max_pt": 10}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.25),
                 panel={"style": "A", "weight": "bold"}, dpi={"line": 600, "halftone": 300, "combination": 600},
                 formats=["pdf", "eps", "svg"], stats="nejm", source="https://www.nejm.org/author-center/new-manuscripts", retrieved=R,
                 note="Figures redrawn by NEJM illustrators; data visualizations as editable vector (no SPSS/Stata files); photos >= 300 ppi; <= 5 figures/tables."),
    "lancet": dict(name="The Lancet family", widths_mm={"single": 85, "photo_min": 107, "double": 178}, max_height_mm=230,
                   font={"family": "Arial", "min_pt": 7, "max_pt": 10}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.25),
                   panel={"style": "A", "weight": "bold"}, dpi={"line": 600, "halftone": 300, "combination": 600},
                   formats=["pdf", "eps", "svg"], stats="lancet", rules=["forest_and_flow_printed_bw", "no_3d"],
                   source="https://www.thelancet.com/pb-assets/Lancet/authors/tl-info-for-authors-1787150940677.pdf", retrieved=R,
                   note="Figures redrawn in-house; editable vector with live text; photos >= 300 dpi and >= 107 mm wide; forest plots and trial profiles printed black and white."),
    "bmj": dict(name="BMJ journals (Heart; The BMJ)", widths_mm={"single": 83, "double": 173.5}, max_height_mm=233.5,
                font={"family": "Arial", "min_pt": 7, "max_pt": 10}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.25),
                panel={"style": "A", "weight": "bold"}, dpi={"line": 1200, "halftone": 300, "combination": 600},
                formats=["tif", "eps", "pdf"], stats="generic_lz", source="https://authors.bmj.com/writing-and-formatting/formatting-your-paper/", retrieved=R,
                note="8.3-17.35 cm wide, <= 23.35 cm high (2014 PDF linked from the Author Hub); EPS text outlined (conflicts with editable-text rules elsewhere); "
                     "print colour charged; favour CIs over P values."),
    "annals": dict(name="Annals of Internal Medicine", widths_mm={"single": 85, "double": 178}, max_height_mm=230,
                   font={"family": "Arial", "min_pt": 7, "max_pt": 10}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.25),
                   panel={"style": "A", "weight": "bold"}, dpi={"line": 600, "halftone": 300, "combination": 600},
                   formats=["pdf", "eps"], stats="annals", rules=["forest_raw_numbers_in_margins", "km_numbers_at_risk"],
                   source="https://www.acpjournals.org/journal/aim/authors", retrieved=R,
                   note="No artwork specs stated; forest plots need raw numbers in the margins; numbers at risk on survival plots; 'mean (SD)' not ±."),
    "sage": dict(name="Sage journals (generic: Phlebology, Lymphatic Res Biol)", widths_mm={"single": 85, "double": 170}, max_height_mm=230,
                 font={"family": "Arial", "min_pt": 7, "max_pt": 10}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.25),
                 panel={"style": "A", "weight": "bold"}, dpi={"line": 800, "halftone": 300, "combination": 600},
                 formats=["tif", "eps"], stats="generic_lz", source="https://www.sagepub.com/journals/information-for-authors/preparing-your-manuscript", retrieved=R,
                 note="Raster >= 300 dpi, line art >= 800 dpi; EPS for graphs; widths not stated (match the journal, no upscaling)."),
    "jevt": dict(name="Journal of Endovascular Therapy (Sage)", widths_mm={"single": 76.2, "double": 127}, max_height_mm=230,
                 font={"family": "Arial", "min_pt": 7, "max_pt": 10}, type=_T(8, 7, 9), lines=_L(0.5, 1.0, 0.25),
                 panel={"style": "A", "weight": "bold"}, dpi={"line": 600, "halftone": 400, "combination": 600},
                 formats=["tif", "eps"], stats="jevt", rules=["km_valid_se_lt_10pct_and_10_at_risk", "km_no_ci_bands"],
                 source="https://journals.sagepub.com/author-instructions/JET", retrieved=R,
                 note=">= 3 in wide (vertical) / 5 in (horizontal); colour/grey 400 ppi, line 600 ppi (another section says 300 dpi); KM valid only while SE < 10% "
                      "and >= 10 at risk, do not plot 95% CIs; visual abstract required (PowerPoint 13.33 x 7.5 in)."),
    "vascmed": dict(name="Vascular Medicine (Sage/SVM)", widths_mm={"single": 127, "double": 178}, max_height_mm=230,
                    font={"family": "Arial", "min_pt": 16, "max_pt": 18}, type=_T(18, 16, 18), lines=_L(1.5, 2.5, 1.0),
                    panel={"style": "A", "weight": "bold"}, dpi={"line": 800, "halftone": 300, "combination": 600},
                    formats=["tif", "eps"], stats="vascmed", source="https://journals.sagepub.com/author-instructions/VMJ", retrieved=R,
                    note="At least 5 in wide with 16 or 18 pt font (maximized); >= 300 dpi; panel labels must not be part of the image (Images in Vascular Medicine). "
                         "Layouts built for 7-9 pt print need fewer elements at this type size; expect figure_qa to flag crowding."),
}
# Fields filled with publisher-generic or skill defaults because the journal's
# own instructions do not state them (from the "not stated" entries in
# assets/journal-specs/*.json). Rendered in references/journal-specs.md.
_UNSTATED = {
    "nature": ["lines.data"], "natureportfolio": ["lines", "panel style (example figure uses lowercase bold)"],
    "naturecomms": ["font sizes (Nature 5-7 pt used)", "max height (only the 210 x 276 mm PDF page is stated)", "1.5-column width"],
    "science": ["max height (page box only)", "dpi for line art"], "scienceadv": ["font embedding"],
    "cell": [], "pnas": ["panel style"], "plos": ["line weight"],
    "elife": ["fonts", "line weight", "panel style", "max height"],
    "elsevier": ["max height", "panel style"], "springer": [], "bmc": ["font family and size", "color mode"],
    "wiley": ["max height", "fonts", "line weight", "panel style", "color mode"],
    "oup": ["widths", "max height", "panel style"], "tandf": ["widths", "max height", "color mode"],
    "acs": ["panel style", "color mode"], "royalsociety": ["widths", "max height", "color mode", "line weight"],
    "frontiers": ["font family"], "mdpi": ["widths", "max height", "fonts", "line weight", "panel style"],
    "ieee": ["color mode", "line weight", "panel style"], "acm": ["resolution", "line weight", "panel style", "figure fonts"],
    "neurips": ["figure fonts", "line weight", "panel style", "resolution"], "iclr": ["figure fonts", "line weight", "panel style", "resolution"],
    "icml": ["figure fonts", "line weight", "panel style", "resolution"], "cvpr": ["figure fonts", "line weight", "panel style", "resolution"],
    "acl": ["figure fonts", "line weight", "panel style", "resolution"],
    "jacc": ["max height", "panel style", "line weight (Elsevier generic used)"],
    "jacc_family": ["max height", "line weight", "panel style", "resolution for JACC: CI"],
    "aha": ["widths on current pages (2012 PDF used)", "max height", "line weight"],
    "ehj": ["widths", "max height", "line weight (OUP generic used)"],
    "eurointervention": ["double width", "max height", "resolution", "minimum font size", "font family"],
    "jvs": ["max height", "line weight", "font family", "line-art and combination dpi (Elsevier generic used)"],
    "ejves": ["widths", "max height (one portrait page)", "resolution", "fonts", "line weight"],
    "ccv": ["fonts", "line weight", "panel style", "max height"],
    "jama": ["widths (figures re-created by JAMA)", "max height", "fonts", "line weight", "panel style"],
    "nejm": ["widths (figures redrawn)", "max height", "fonts", "line weight", "panel style"],
    "lancet": ["column widths (figures redrawn)", "max height", "fonts", "line weight", "panel style"],
    "bmj": ["fonts", "line weight", "panel style"],
    "annals": ["widths", "max height", "resolution", "fonts", "line weight", "panel style"],
    "sage": ["widths", "max height", "fonts", "line weight", "panel style"],
    "jevt": ["max width", "max height", "fonts", "line weight", "panel style"],
    "vascmed": ["double width", "max height", "line weight", "line-art dpi (Sage generic used)"],
}
for _k, _v in _JOURNAL_PRESETS.items():
    _v["unstated"] = _UNSTATED.get(_k, [])
    register_preset(_k, _v)


def _norm(key: str) -> str:
    return "".join(ch for ch in key.lower() if ch.isalnum())


_ALIASES = {
    "newenglandjournalofmedicine": "nejm", "jamacardiology": "jama", "jamanetwork": "jama",
    "thelancet": "lancet", "jacccardiovascularinterventions": "jacc_family", "jaccci": "jacc_family",
    "jaccintv": "jacc_family", "jaccadvances": "jacc_family", "jaccbts": "jacc_family",
    "jaccbasictotranslationalscience": "jacc_family", "jacccasereports": "jacc",
    "circulation": "aha", "circcvinterv": "aha", "circulationcardiovascularinterventions": "aha",
    "hypertension": "aha", "atvb": "aha", "stroke": "aha",
    "europeanheartjournal": "ehj", "eurheartj": "ehj", "journalofvascularsurgery": "jvs", "jvsvl": "jvs",
    "jvsvenousandlymphaticdisorders": "jvs", "cci": "ccv", "catheterizationandcardiovascularinterventions": "ccv",
    "heart": "bmj", "thebmj": "bmj", "annalsofinternalmedicine": "annals", "phlebology": "sage",
    "lymphaticresearchandbiology": "sage", "lrb": "sage", "journalofendovasculartherapy": "jevt",
    "vascularmedicine": "vascmed", "naturemedicine": "natureportfolio", "naturecommunications": "naturecomms",
    "scientificreports": "naturecomms", "scirep": "naturecomms", "scienceadvances": "scienceadv",
    "cellreports": "cell", "plosone": "plos", "taylorandfrancis": "tandf", "iccv": "cvpr",
    "arr": "acl", "royalsoc": "royalsociety", "biomedcentral": "bmc", "oxford": "oup",
}


def preset(key: str) -> dict:
    """Look up a preset by key or common journal name (case/punctuation-insensitive)."""
    table = {_norm(k): k for k in PRESETS}
    n = _norm(key)
    resolved = table.get(n) or table.get(_norm(_ALIASES.get(n, "")))
    if resolved is None:
        raise KeyError(f"unknown preset {key!r}; known: {', '.join(sorted(PRESETS))}. "
                       "Use register_preset() with values from the journal's current instructions.")
    return PRESETS[resolved]


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
FONT_SUBSTITUTES = {
    # Metric-compatible substitutes first (same advance widths), then lookalikes.
    "arial": ["Arial", "Liberation Sans", "Arimo", "Helvetica", "Helvetica Neue",
              "Nimbus Sans", "TeX Gyre Heros", "DejaVu Sans"],
    "helvetica": ["Helvetica", "Helvetica Neue", "Arial", "Nimbus Sans", "TeX Gyre Heros",
                  "Liberation Sans", "Arimo", "DejaVu Sans"],
    "times new roman": ["Times New Roman", "Times", "Liberation Serif", "Tinos",
                        "Nimbus Roman", "TeX Gyre Termes", "STIXGeneral", "DejaVu Serif"],
    "times": ["Times", "Times New Roman", "Liberation Serif", "Tinos", "Nimbus Roman",
              "TeX Gyre Termes", "STIXGeneral", "DejaVu Serif"],
    "myriad pro": ["Myriad Pro", "Arial", "Liberation Sans", "DejaVu Sans"],
    "calibri": ["Calibri", "Carlito", "Arial", "Liberation Sans", "DejaVu Sans"],
}
METRIC_COMPATIBLE = {
    "arial": {"liberation sans", "arimo"},
    "helvetica": {"nimbus sans", "tex gyre heros"},
    "times new roman": {"liberation serif", "tinos"},
    "calibri": {"carlito"},
}


@dataclass
class FontChoice:
    requested: str
    actual: str
    path: str | None
    exact: bool
    metric_compatible: bool

    @property
    def final_ok(self) -> bool:
        """True when the requested family is installed (submission-safe)."""
        return self.exact


def resolve_font(requested: str = "Arial") -> FontChoice:
    """Find the requested family or the closest installed substitute.

    Never silently accept a fallback: inspect ``exact`` before calling a figure
    final. Liberation Sans/Arimo share Arial's metrics, so layout is identical,
    but the embedded font name differs from what some journals request.
    """
    candidates = FONT_SUBSTITUTES.get(requested.lower(), [requested, "DejaVu Sans"])
    if candidates[0].lower() != requested.lower():
        candidates = [requested] + candidates
    for name in candidates:
        try:
            path = font_manager.findfont(font_manager.FontProperties(family=name),
                                         fallback_to_default=False)
        except ValueError:
            continue
        actual = font_manager.FontProperties(fname=path).get_name()
        exact = actual.lower() == requested.lower()
        compatible = exact or actual.lower() in METRIC_COMPATIBLE.get(requested.lower(), set())
        return FontChoice(requested, actual, path, exact, compatible)
    return FontChoice(requested, "DejaVu Sans", None, False, False)


# ---------------------------------------------------------------------------
# Figure specification and style
# ---------------------------------------------------------------------------
@dataclass
class FigSpec:
    target: str
    preset: dict
    column: str
    width_mm: float
    height_mm: float
    font: FontChoice
    type: dict
    lines: dict
    panel_style: str
    stats_style: str
    mode: str = "manuscript"
    notes: list[str] = field(default_factory=list)

    @property
    def figsize(self) -> tuple[float, float]:
        return (mm(self.width_mm), mm(self.height_mm))

    def summary(self) -> str:
        font = self.font.actual + ("" if self.font.exact else f" (requested {self.font.requested}; substitute)")
        return (f"{self.preset['name']} | {self.column}: {self.width_mm:.1f} x {self.height_mm:.1f} mm | "
                f"font {font} | labels {self.type['label']} pt, ticks {self.type['tick']} pt, "
                f"panel {self.type['panel']} pt {self.preset['panel']['weight']} '{self.panel_style}'")


def setup(target: str = "generic", column: str | float = "single", *, height_mm: float | None = None,
          aspect: float | None = None, font: str | None = None, mode: str | None = None,
          scale_type: float = 1.0, strict_font: bool = False) -> FigSpec:
    """Apply final-size rcParams for a target and return its FigSpec.

    column: a key of the preset's ``widths_mm`` (single, onehalf, double, full...)
    or an explicit width in mm. Height defaults to width * aspect (0.75 single,
    0.5 double), capped at the preset's maximum height.
    """
    p = preset(target)
    if isinstance(column, (int, float)):
        width = float(column)
        column_name = f"{width:g} mm"
    else:
        widths = {k: v for k, v in p["widths_mm"].items() if v}
        alias = {"double": ["full", "triple"], "full": ["double", "triple"], "page": ["full", "double", "triple"],
                 "single": ["column"], "column": ["single"]}
        if column not in widths:
            for alt in alias.get(column, []):
                if alt in widths:
                    notes_alias = f"{p['name']} has no {column!r} width; using {alt!r} ({widths[alt]:g} mm)"
                    warnings.warn(notes_alias, stacklevel=2)
                    column = alt
                    break
            else:
                if column in ("full", "page", "double") and widths:
                    column = max(widths, key=widths.get)
                else:
                    raise KeyError(f"{p['name']} has no {column!r} width; available: {list(widths)}")
        width = float(widths[column])
        column_name = column
    if height_mm is None:
        if aspect is None:
            aspect = 0.75 if width < 130 else 0.5
        height_mm = width * aspect
    notes: list[str] = []
    max_h = p.get("max_height_mm")
    if max_h and height_mm > max_h:
        notes.append(f"height {height_mm:.0f} mm capped at preset maximum {max_h:.0f} mm")
        height_mm = max_h
    fc = resolve_font(font or p["font"]["family"])
    if not fc.exact:
        msg = (f"font {fc.requested!r} is not installed; using {fc.actual!r}"
               + (" (metric-compatible: layout identical)" if fc.metric_compatible else ""))
        if strict_font:
            raise RuntimeError(msg + "; install the font before final export")
        notes.append(msg + ". Not final until the requested font is installed.")
    type_pt = {k: round(v * scale_type, 2) for k, v in p["type"].items()}
    lines = dict(p["lines"])
    style = p["panel"]["style"]
    spec = FigSpec(target=target, preset=p, column=column_name, width_mm=width, height_mm=height_mm,
                   font=fc, type=type_pt, lines=lines, panel_style=style,
                   stats_style=p.get("stats", "ama"), mode=mode or ("presentation" if target == "presentation" else "manuscript"),
                   notes=notes)
    apply_style(spec)
    for note in notes:
        warnings.warn(note, stacklevel=2)
    return spec


def apply_style(spec: FigSpec) -> None:
    t, ln, fam = spec.type, spec.lines, spec.font.actual
    mpl.rcParams.update({
        "font.family": "sans-serif" if spec.font.path is None else fam,
        "font.sans-serif": [fam, "DejaVu Sans"],
        "font.size": t["label"],
        "axes.labelsize": t["label"],
        "axes.titlesize": t["title"],
        "axes.titleweight": "normal",
        "figure.titlesize": t["title"],
        "xtick.labelsize": t["tick"],
        "ytick.labelsize": t["tick"],
        "legend.fontsize": t["legend"],
        "legend.title_fontsize": t["legend"],
        "mathtext.fontset": "custom",
        "mathtext.rm": fam,
        "mathtext.it": f"{fam}:italic",
        "mathtext.bf": f"{fam}:bold",
        "mathtext.sf": fam,
        "mathtext.default": "regular",
        "axes.unicode_minus": True,
        "axes.linewidth": ln["axes"],
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#222222",
        "axes.labelcolor": "#222222",
        "axes.labelpad": 2.5,
        "axes.titlepad": 3.0,
        "axes.axisbelow": True,
        "axes.grid": False,
        "axes.prop_cycle": mpl.cycler(color=CATEGORICAL),
        "grid.linewidth": ln["grid"],
        "grid.color": "#D9D9D9",
        "lines.linewidth": ln["data"],
        "lines.markersize": max(2.5, t["tick"] * 0.55),
        "lines.markeredgewidth": max(ln["minimum"], 0.5),
        "patch.linewidth": ln["axes"],
        "hatch.linewidth": max(ln["minimum"], 0.5),
        "errorbar.capsize": max(1.5, t["tick"] * 0.3),
        "xtick.color": "#222222",
        "ytick.color": "#222222",
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.width": ln["axes"],
        "ytick.major.width": ln["axes"],
        "xtick.minor.width": max(ln["axes"] * 0.75, ln["minimum"]),
        "ytick.minor.width": max(ln["axes"] * 0.75, ln["minimum"]),
        "xtick.major.size": max(2.0, t["tick"] * 0.4),
        "ytick.major.size": max(2.0, t["tick"] * 0.4),
        "xtick.major.pad": 1.8,
        "ytick.major.pad": 1.8,
        "legend.frameon": False,
        "legend.borderaxespad": 0.3,
        "legend.handlelength": 1.6,
        "legend.handletextpad": 0.5,
        "legend.columnspacing": 1.0,
        "legend.labelspacing": 0.35,
        "image.cmap": "viridis",
        "image.interpolation": "nearest",
        "figure.dpi": 150,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.dpi": 600,
        # Fixed canvas: never "tight". Tight cropping changes the physical size
        # and silently rescales typography when panels are placed later.
        "savefig.bbox": None,
        "savefig.pad_inches": 0.0,
        "pdf.fonttype": 42,   # embed TrueType (Type 42), never Type 3
        "ps.fonttype": 42,
        "svg.fonttype": "none",  # live, editable SVG text
        "svg.hashsalt": "pubfig",  # deterministic SVG ids for version control
        "pdf.compression": 6,
        "path.simplify": True,
    })


def subplots(spec: FigSpec, nrows: int = 1, ncols: int = 1, *, pad_pt: float = 2.0,
             wspace: float = 0.04, hspace: float = 0.04, **kwargs):
    """Figure at the exact final size with constrained layout (no tight bbox)."""
    fig, axes = plt.subplots(nrows, ncols, figsize=spec.figsize, layout="constrained", **kwargs)
    fig.get_layout_engine().set(w_pad=pad_pt / 72, h_pad=pad_pt / 72, wspace=wspace, hspace=hspace)
    fig._pubfig_spec = spec  # read by save() and figure_qa
    return fig, axes


def figure(spec: FigSpec, *, pad_pt: float = 2.0, **kwargs):
    fig = plt.figure(figsize=spec.figsize, layout="constrained", **kwargs)
    fig.get_layout_engine().set(w_pad=pad_pt / 72, h_pad=pad_pt / 72, wspace=0.04, hspace=0.04)
    fig._pubfig_spec = spec
    return fig


# ---------------------------------------------------------------------------
# Colour: palettes, tints, CVD simulation, CIEDE2000
# ---------------------------------------------------------------------------
OKABE_ITO = {  # Okabe & Ito, Color Universal Design (J*FLY); Wong, Nat Methods 2011
    "black": "#000000", "orange": "#E69F00", "sky_blue": "#56B4E9", "bluish_green": "#009E73",
    "yellow": "#F0E442", "blue": "#0072B2", "vermillion": "#D55E00", "reddish_purple": "#CC79A7",
}
# Default categorical order (Okabe-Ito hues), searched so the first four stay
# apart under simulated protanopia/deuteranopia/tritanopia (min CIEDE2000 12.4)
# and in grayscale (min L* difference 11.8). Beyond four series, add marker or
# line-style redundancy: no 5+ colour set survives grayscale print.
CATEGORICAL = ["#0072B2", "#E69F00", "#000000", "#009E73", "#D55E00", "#56B4E9", "#CC79A7", "#F0E442"]
TOL = {  # Paul Tol's qualitative schemes (verified against the tol-colors package)
    "bright": ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"],
    "vibrant": ["#0077BB", "#33BBEE", "#009988", "#EE7733", "#CC3311", "#EE3377", "#BBBBBB"],
    "muted": ["#332288", "#88CCEE", "#44AA99", "#117733", "#999933", "#DDCC77", "#CC6677",
              "#882255", "#AA4499"],
    "high_contrast": ["#004488", "#DDAA33", "#BB5566"],
    "light": ["#77AADD", "#99DDFF", "#44BB99", "#BBCC33", "#AAAA00", "#EEDD88", "#EE8866",
              "#FFAABB", "#DDDDDD"],
}
NEUTRALS = {"ink": "#222222", "muted": "#5B6472", "grid": "#D9D9D9", "reference": "#7F7F7F",
            "baseline": "#9A9A9A", "band": "#E6E6E6"}
# Two-arm clinical default: intervention in blue, control in near-black; pair
# with solid/dashed line styles so print and CVD readers keep the distinction.
ARMS = {"intervention": "#0072B2", "control": "#3B3B3B"}
SEQUENTIAL_CMAPS = ["viridis", "cividis", "magma", "inferno", "Blues", "Greys"]
DIVERGING_CMAPS = ["RdBu_r", "PuOr_r", "BrBG", "coolwarm", "berlin", "vanimo", "managua"]
FORBIDDEN_CMAPS = {"jet", "rainbow", "hsv", "gist_rainbow", "nipy_spectral", "gist_ncar",
                   "spectral", "prism", "flag", "turbo"}


def tint(color, fraction: float) -> str:
    """Blend toward white (opaque). Use instead of alpha for print/EPS-safe fills."""
    r, g, b = to_rgb(color)
    return to_hex((r + (1 - r) * fraction, g + (1 - g) * fraction, b + (1 - b) * fraction))


def shade(color, fraction: float) -> str:
    r, g, b = to_rgb(color)
    return to_hex((r * (1 - fraction), g * (1 - fraction), b * (1 - fraction)))


def _srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = np.asarray(c, dtype=float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(np.asarray(c, dtype=float), 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


# Machado, Oliveira & Fernandes (2009), IEEE TVCG 15(6):1291-1298, severity 1.0.
# Applied to linear RGB (the convention used by colorspacious and DaltonLens).
_MACHADO = {
    "protanopia": np.array([[0.152286, 1.052583, -0.204868],
                            [0.114503, 0.786281, 0.099216],
                            [-0.003882, -0.048116, 1.051998]]),
    "deuteranopia": np.array([[0.367322, 0.860646, -0.227968],
                              [0.280085, 0.672501, 0.047413],
                              [-0.011820, 0.042940, 0.968881]]),
    "tritanopia": np.array([[1.255528, -0.076749, -0.178779],
                            [-0.078411, 0.930809, 0.147602],
                            [0.004733, 0.691367, 0.303900]]),
}


def simulate_cvd(rgb, kind: str = "deuteranopia", severity: float = 1.0) -> np.ndarray:
    """Simulate dichromacy on sRGB values in [0, 1] (array shape (..., 3)).

    kind: protanopia, deuteranopia, tritanopia, or achromatopsia (luminance only).
    severity < 1 interpolates linearly toward normal vision (an approximation of
    Machado's anomalous-trichromacy tables).
    """
    rgb = np.asarray(rgb, dtype=float)
    lin = _srgb_to_linear(rgb)
    if kind == "achromatopsia":
        y = lin @ np.array([0.2126, 0.7152, 0.0722])
        out = np.repeat(y[..., None], 3, axis=-1)
    else:
        m = _MACHADO[kind]
        m = severity * m + (1 - severity) * np.eye(3)
        out = lin @ m.T
    return _linear_to_srgb(out)


def _srgb_to_lab(rgb) -> np.ndarray:
    lin = _srgb_to_linear(np.asarray(rgb, dtype=float))
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    eps, kappa = 216 / 24389, 24389 / 27
    f = np.where(xyz > eps, np.cbrt(xyz), (kappa * xyz + 16) / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def delta_e2000(lab1, lab2) -> np.ndarray:
    """CIEDE2000 colour difference (Sharma, Wu & Dalal 2005 implementation notes)."""
    lab1, lab2 = np.asarray(lab1, float), np.asarray(lab2, float)
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cbar = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cbar ** 7 / (Cbar ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2 - L1
    dCp = C2p - C1p
    dhp = h2p - h1p
    dhp = np.where(C1p * C2p == 0, 0, np.where(dhp > 180, dhp - 360, np.where(dhp < -180, dhp + 360, dhp)))
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp / 2))
    Lbarp = (L1 + L2) / 2
    Cbarp = (C1p + C2p) / 2
    hsum = h1p + h2p
    hbarp = np.where(C1p * C2p == 0, hsum,
                     np.where(np.abs(h1p - h2p) <= 180, hsum / 2,
                              np.where(hsum < 360, (hsum + 360) / 2, (hsum - 360) / 2)))
    T = (1 - 0.17 * np.cos(np.radians(hbarp - 30)) + 0.24 * np.cos(np.radians(2 * hbarp))
         + 0.32 * np.cos(np.radians(3 * hbarp + 6)) - 0.20 * np.cos(np.radians(4 * hbarp - 63)))
    dtheta = 30 * np.exp(-(((hbarp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbarp ** 7 / (Cbarp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbarp - 50) ** 2 / np.sqrt(20 + (Lbarp - 50) ** 2)
    Sc = 1 + 0.045 * Cbarp
    Sh = 1 + 0.015 * Cbarp * T
    Rt = -np.sin(np.radians(2 * dtheta)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def relative_luminance(color) -> float:
    return float(_srgb_to_linear(np.array(to_rgb(color))) @ np.array([0.2126, 0.7152, 0.0722]))


def contrast_ratio(fg, bg="#FFFFFF") -> float:
    """WCAG 2.x contrast ratio (text needs >= 4.5:1; large text and marks >= 3:1)."""
    a, b = sorted((relative_luminance(fg), relative_luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def check_colors(colors: Sequence, *, min_de: float = 10.0, min_dl: float = 10.0,
                 background: str = "#FFFFFF") -> dict:
    """Pairwise distinguishability of categorical colours.

    Reports the minimum CIEDE2000 difference for normal vision and simulated
    protanopia, deuteranopia and tritanopia, the minimum lightness difference
    (grayscale print), and contrast against the background. Thresholds are
    working heuristics, not standards: Delta E00 near 2 is a just-noticeable
    difference; categorical marks need far more separation to be named apart.
    """
    hexes = [to_hex(c) for c in colors]
    rgb = np.array([to_rgb(c) for c in hexes])
    report: dict = {"colors": hexes, "conditions": {}, "pass": True, "problems": []}
    pairs = [(i, j) for i in range(len(hexes)) for j in range(i + 1, len(hexes))]
    if not pairs:
        return report
    for cond in ["normal", "protanopia", "deuteranopia", "tritanopia"]:
        sim = rgb if cond == "normal" else simulate_cvd(rgb, cond)
        lab = _srgb_to_lab(sim)
        des = {(i, j): float(delta_e2000(lab[i], lab[j])) for i, j in pairs}
        (i, j), worst = min(des.items(), key=lambda kv: kv[1])
        report["conditions"][cond] = {"min_delta_e00": round(worst, 1), "pair": (hexes[i], hexes[j])}
        if worst < min_de:
            report["pass"] = False
            report["problems"].append(
                f"{cond}: {hexes[i]} vs {hexes[j]} Delta E00 = {worst:.1f} (< {min_de:g}); add marker/line-style redundancy or change one colour")
    L = _srgb_to_lab(rgb)[:, 0]
    dl = {(i, j): abs(float(L[i] - L[j])) for i, j in pairs}
    (i, j), worst_l = min(dl.items(), key=lambda kv: kv[1])
    report["grayscale"] = {"min_delta_L": round(worst_l, 1), "pair": (hexes[i], hexes[j])}
    if worst_l < min_dl:
        report["problems"].append(
            f"grayscale: {hexes[i]} vs {hexes[j]} differ by L* {worst_l:.1f} (< {min_dl:g}); they merge in black-and-white print")
    low = [h for h in hexes if contrast_ratio(h, background) < 3.0]
    report["low_contrast"] = low
    if low:
        report["problems"].append(f"contrast < 3:1 against {background}: {', '.join(low)} (thin lines/small marks fade)")
    return report


# ---------------------------------------------------------------------------
# Panel labels
# ---------------------------------------------------------------------------
def _label_text(style: str, index: int) -> str:
    letter = chr(ord("a") + index)
    if style in ("A", "(A)", "A.", "A)"):
        letter = letter.upper()
    if style.startswith("("):
        return f"({letter})"
    if style.endswith("."):
        return f"{letter}."
    if style.endswith(")"):
        return f"{letter})"
    return letter


def _clusters(values: Sequence[float], tol: float) -> list[int]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ids = [0] * len(values)
    group, prev = 0, None
    for i in order:
        if prev is not None and values[i] - prev > tol:
            group += 1
        ids[i] = group
        prev = values[i]
    return ids


def root_figure(obj):
    """Root Figure of an Axes, SubFigure, or Figure (subfigures have their own coordinates)."""
    try:
        return obj.get_figure(root=True)
    except (TypeError, AttributeError):
        f = getattr(obj, "figure", obj)
        while getattr(f, "figure", f) is not f:
            f = f.figure
        return f


def on_settle(obj, fn) -> None:
    """Register a placement to redo once the layout is final (see settle)."""
    root = root_figure(obj)
    if not hasattr(root, "_pubfig_settle"):
        root._pubfig_settle = []
    root._pubfig_settle.append(fn)


def settle(fig) -> None:
    """Redo automatic placements after every panel, label, and tag exists.

    Statistics annotations, ROC legends, and panel labels are placed from the
    layout at the moment they are created; adding panels later shrinks axes and
    can push a placement onto the data. save() and figure_qa.audit_figure call
    this first, so what is audited and written is placed for the final layout.
    """
    root = root_figure(fig)
    for fn in list(getattr(root, "_pubfig_settle", [])):
        try:
            fn()
        except Exception as exc:          # an artist the user removed by hand, for example
            warnings.warn(f"could not redo an automatic placement: {exc}")
    root.canvas.draw()


def panel_labels(fig, axes, *, style: str | None = None, size: float | None = None,
                 weight: str | None = None, labels: Sequence[str] | None = None,
                 inside: bool = False, color: str = "#000000", gap_pt: float = 1.5):
    """Add journal-convention panel labels aligned by row and column.

    Labels sit above each panel at the left edge of its decorations (tick
    labels and axis label), so they never collide with the y-axis label, and
    labels in the same column share x while labels in the same row share y.
    ``inside=True`` places them inside the top-left corner (image panels).
    Returns the created Text artists.
    """
    spec = getattr(root_figure(fig), "_pubfig_spec", None)
    style = style or (spec.panel_style if spec else "A")
    size = size or (spec.type["panel"] if spec else 8)
    weight = weight or (spec.preset["panel"]["weight"] if spec else "bold")
    axes = list(np.ravel(axes))
    texts = labels or [_label_text(style, i) for i in range(len(axes))]
    created = []
    if inside:
        for ax, txt in zip(axes, texts):
            created.append(ax.text(0.02, 0.98, txt, transform=ax.transAxes, ha="left", va="top",
                                   fontsize=size, fontweight=weight, color=color,
                                   bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none")))
        return created
    from matplotlib.transforms import ScaledTranslation
    for ax, txt in zip(axes, texts):
        t = ax.text(0, 1, txt, transform=ax.transAxes, ha="left", va="bottom",
                    fontsize=size, fontweight=weight, color=color)
        t._pubfig_panel_label = True
        created.append(t)
    # Two passes: measure decoration widths, then align columns/rows. Work in
    # display pixels so axes in subfigures and inset hosts share one frame.
    root = root_figure(fig)
    _align_panel_labels(root, axes, created, gap_pt)
    on_settle(root, lambda: _align_panel_labels(root, axes, created, gap_pt))
    return created


def _align_panel_labels(root, axes, created, gap_pt):
    from matplotlib.transforms import ScaledTranslation
    for _ in range(2):
        root.canvas.draw()
        renderer = root.canvas.get_renderer()
        W, H = root.bbox.width, root.bbox.height
        lefts, tops, x0s, y1s = [], [], [], []
        for ax, t in zip(axes, created):
            t.set_visible(False)
            tb = ax.get_tightbbox(renderer)
            t.set_visible(True)
            wb = ax.get_window_extent(renderer)
            # top of everything drawn for this panel (title, top tick label, an
            # over-long rotated y label), so the label never sits on a decoration
            lefts.append(tb.x0)
            tops.append(max(wb.y1, tb.y1))
            x0s.append(wb.x0)
            y1s.append(wb.y1)
        cols = _clusters([x / W for x in x0s], 0.05)
        rows = _clusters([y / H for y in y1s], 0.05)
        col_left = {c: min(l for l, cc in zip(lefts, cols) if cc == c) for c in set(cols)}
        row_top = {r: max(tp for tp, rr in zip(tops, rows) if rr == r) for r in set(rows)}
        for t, c, r, x0, y1, ax in zip(created, cols, rows, x0s, y1s, axes):
            dx_in = (col_left[c] - x0) / root.dpi
            dy_in = (row_top[r] - y1) / root.dpi + gap_pt / 72
            t.set_transform(ax.transAxes + ScaledTranslation(dx_in, dy_in, root.dpi_scale_trans))


# ---------------------------------------------------------------------------
# Annotation helpers
# ---------------------------------------------------------------------------
def min_line(obj) -> float:
    """Preset minimum stroke (pt) for a Figure or Axes made by pubfig; 0.25 otherwise."""
    spec = getattr(root_figure(obj), "_pubfig_spec", None)
    return spec.lines["minimum"] if spec else 0.25


def outline_width(obj, wanted: float = 0.3) -> float:
    """A hairline outline that respects the preset: dropped (0) when the
    journal's minimum stroke is heavier than the outline should be."""
    return wanted if min_line(obj) <= wanted else 0.0


def synthetic_tag(fig, text: str = "Synthetic data", fontsize: float | None = None):
    """Mark artwork built from synthetic or illustrative data.

    Call it after the panels are built. With constrained layout the tag takes
    the figure-title slot at the top right, so the layout reserves a strip for
    it and nothing can collide with it (figure_qa does not count it as a
    title). Otherwise it goes to the first figure corner free of text and axes.
    """
    fs = fontsize or mpl.rcParams["xtick.labelsize"]
    style = dict(color=NEUTRALS["muted"], fontsize=fs, style="italic", fontweight="normal")
    eng = fig.get_layout_engine()
    has_title = fig._suptitle is not None and fig._suptitle.get_text().strip()
    if eng is not None and type(eng).__name__ == "ConstrainedLayoutEngine" and not has_title:
        t = fig.suptitle(text, x=0.995, ha="right", **style)
        t._pubfig_synthetic_tag = True
        return t
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    from matplotlib.text import Text as _Text
    occupied = [a.get_window_extent(r) for a in fig.axes if a.get_visible() and a.axison]
    occupied += [a.get_window_extent(r) for a in fig.findobj(_Text) if a.get_visible() and a.get_text().strip()]
    for x, y, ha, va in ((0.995, 0.995, "right", "top"), (0.995, 0.005, "right", "bottom"),
                         (0.005, 0.005, "left", "bottom"), (0.005, 0.995, "left", "top")):
        t = fig.text(x, y, text, ha=ha, va=va, **style)
        bb = t.get_window_extent(r).padded(fs * fig.dpi / 72)      # keep a line of clearance
        if not any(bb.overlaps(o) for o in occupied):
            break
        t.remove()
    else:
        t = fig.text(0.995, 0.995, text, ha="right", va="top", **style)
        warnings.warn("no free corner for the synthetic-data tag; state it in the legend instead")
    t._pubfig_synthetic_tag = True
    return t


def reference_line(ax, value: float, orientation: str = "h", label: str | None = None, **kw):
    style = dict(color=NEUTRALS["reference"], lw=mpl.rcParams["axes.linewidth"], ls=(0, (3, 2)), zorder=0.5)
    style.update(kw)
    line = ax.axhline(value, **style) if orientation == "h" else ax.axvline(value, **style)
    if label:
        if orientation == "h":
            ax.annotate(label, (1, value), xycoords=("axes fraction", "data"), xytext=(-2, 2),
                        textcoords="offset points", ha="right", va="bottom",
                        fontsize=mpl.rcParams["xtick.labelsize"], color=style["color"])
        else:
            ax.annotate(label, (value, 1), xycoords=("data", "axes fraction"), xytext=(2, -2),
                        textcoords="offset points", ha="left", va="top",
                        fontsize=mpl.rcParams["xtick.labelsize"], color=style["color"])
    return line


def flatten_alpha(fig, background: str = "#FFFFFF") -> int:
    """Replace semi-transparent fills/edges with opaque blends over the background.

    PostScript/EPS has no transparency; some print workflows flatten it badly.
    Exact only where the translucent artist sits over the background colour.
    Returns the number of artists changed.
    """
    from matplotlib.colors import to_rgba
    bg = np.array(to_rgb(background))
    changed = 0

    def blend(c):
        r, g, b, a = to_rgba(c)
        return to_hex(np.array([r, g, b]) * a + bg * (1 - a))

    for artist in fig.findobj():
        alpha = getattr(artist, "get_alpha", lambda: None)()
        try:
            if hasattr(artist, "get_facecolor") and hasattr(artist, "set_facecolor"):
                fc = artist.get_facecolor()
                arr = np.atleast_2d(fc)
                if arr.size and arr.shape[-1] == 4 and (arr[:, 3] < 0.999).any():
                    artist.set_facecolor([blend(c) for c in arr] if arr.shape[0] > 1 else blend(arr[0]))
                    changed += 1
            if alpha is not None and alpha < 0.999 and hasattr(artist, "set_alpha"):
                artist.set_alpha(None)
                changed += 1
        except (TypeError, ValueError):
            continue
    return changed


# ---------------------------------------------------------------------------
# Notation and statistics formatting
# ---------------------------------------------------------------------------
_SUB = str.maketrans("0123456789+-=()aeoxhklmnpst", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜ")
_SUP = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
MINUS = "−"


def sub(text: str) -> str:
    return text.translate(_SUB)


def sup(text: str) -> str:
    return text.translate(_SUP)


_NOTATION = [
    (re.compile(r"\b(IC|EC|ED|LD|TD|CC)(50|90|95)\b"), lambda m: m.group(1) + sub(m.group(2))),
    (re.compile(r"\blog(2|10)\b"), lambda m: "log" + sub(m.group(1))),
    (re.compile(r"\b(CO|O|H|N)2\b"), lambda m: m.group(1) + "₂"),
    (re.compile(r"\bSpO2\b"), lambda m: "SpO₂"),
    (re.compile(r"\bm\^?2\b"), lambda m: "m²"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*[xX]\s*10\^?(-?\d+)"), lambda m: f"{m.group(1)} × 10" + sup(m.group(2).replace('-', '−'))),
]


def notation(text: str) -> str:
    """Convert plain-ASCII scientific tokens to publication notation.

    IC50 -> IC₅₀, log2 -> log₂, CO2 -> CO₂, m^2 -> m², 3 x 10^-4 -> 3 × 10⁻⁴.
    Check glyph support in the chosen font (figure_qa reports missing glyphs).
    """
    for pattern, repl in _NOTATION:
        text = pattern.sub(repl, text)
    return text


# House statistics styles, from each journal's instructions (quotes in
# assets/journal-specs/journal_specs_clinical.json). Where italics or spacing
# are not stated, the AMA convention (italic capital P) is kept and flagged in
# references/typography-and-notation.md.
#   rule "decimals": list of (upper_bound, decimals) applied in order;
#   rule "sigfig": significant figures; sci_below: scientific notation threshold.
STATS_STYLES: dict[str, dict] = {
    # AMA 11th ed as written in JAMA instructions: P < .001; .001-.01 thousandths;
    # >= .01 hundredths; > .99 as P > .99; no leading zero; italic capital P.
    "ama": {"symbol": "P", "italic": True, "leading_zero": False, "decimal": ".", "spaces": True,
            "floor": 0.001, "ceiling": 0.99, "rule": "decimals", "decimals": [(0.01, 3), (1.0, 2)],
            "ci_sep": "-", "ci_neg_sep": " to ", "ci_label": "95% CI"},
    # NEJM: P<0.001; 0.001-0.01 three decimals; > 0.01 two decimals; capital P.
    "nejm": {"symbol": "P", "italic": True, "leading_zero": True, "decimal": ".", "spaces": False,
             "floor": 0.001, "ceiling": None, "rule": "decimals", "decimals": [(0.01, 3), (1.0, 2)],
             "ci_sep": " to ", "ci_neg_sep": " to ", "ci_label": "95% CI"},
    # Annals: 0.001-0.20 to thousandths; > 0.20 hundredths; P<0.001.
    "annals": {"symbol": "P", "italic": True, "leading_zero": True, "decimal": ".", "spaces": False,
               "floor": 0.001, "ceiling": None, "rule": "decimals", "decimals": [(0.2000001, 3), (1.0, 2)],
               "ci_sep": " to ", "ci_neg_sep": " to ", "ci_label": "95% CI"},
    # The Lancet: lowercase p, two significant figures unless p<0·0001, midline decimal point.
    "lancet": {"symbol": "p", "italic": False, "leading_zero": True, "decimal": "\u00b7", "spaces": False,
               "floor": 0.0001, "ceiling": None, "rule": "sigfig", "sigfigs": 2,
               "ci_sep": "\u2013", "ci_neg_sep": " to ", "ci_label": "95% CI"},
    # EHJ: legend example 'P = 0.003' (italic), statistics page 'p<0.0001' for very small values.
    "ehj": {"symbol": "P", "italic": True, "leading_zero": True, "decimal": ".", "spaces": True,
            "floor": 0.0001, "ceiling": None, "rule": "decimals", "decimals": [(0.001, 4), (0.01, 3), (1.0, 2)],
            "ci_sep": "\u2013", "ci_neg_sep": " to ", "ci_label": "95% CI"},
    # EJVES: 'p = .043'; 3 decimals for p <= .099, 2 for >= .10; exact unless < .001; roman lowercase.
    "ejves": {"symbol": "p", "italic": False, "leading_zero": False, "decimal": ".", "spaces": True,
              "floor": 0.001, "ceiling": None, "rule": "decimals", "decimals": [(0.0995, 3), (1.0, 2)],
              "ci_sep": "\u2013", "ci_neg_sep": " to ", "ci_label": "95% CI"},
    # JEVT: 'p=0.XXX', limited to 3 digits.
    "jevt": {"symbol": "p", "italic": False, "leading_zero": True, "decimal": ".", "spaces": False,
             "floor": 0.001, "ceiling": None, "rule": "decimals", "decimals": [(1.0, 3)],
             "ci_sep": "\u2013", "ci_neg_sep": " to ", "ci_label": "95% CI"},
    # Vascular Medicine: 'p = 0.023', two significant digits, 'p > 0.99'.
    "vascmed": {"symbol": "p", "italic": False, "leading_zero": True, "decimal": ".", "spaces": True,
                "floor": 0.0001, "ceiling": 0.99, "rule": "sigfig", "sigfigs": 2,
                "ci_sep": "\u2013", "ci_neg_sep": " to ", "ci_label": "95% CI"},
    # AHA: estimate, CI, then actual P to >= 2 significant digits; scientific notation for small values.
    "aha": {"symbol": "P", "italic": True, "leading_zero": True, "decimal": ".", "spaces": True,
            "floor": None, "ceiling": None, "rule": "sigfig", "sigfigs": 2, "sci_below": 0.001,
            "ci_sep": "\u2013", "ci_neg_sep": " to ", "ci_label": "95% CI"},
    # Fallback when a journal states nothing: italic P, leading zero, NEJM-like decimals.
    "generic_lz": {"symbol": "P", "italic": True, "leading_zero": True, "decimal": ".", "spaces": True,
                   "floor": 0.001, "ceiling": None, "rule": "decimals", "decimals": [(0.01, 3), (1.0, 2)],
                   "ci_sep": "\u2013", "ci_neg_sep": " to ", "ci_label": "95% CI"},
}


def _fmt_number(x: float, digits: int, style: dict) -> str:
    s = f"{x:.{digits}f}"
    if not style["leading_zero"] and s.lstrip("-").startswith("0."):
        s = s.replace("0.", ".", 1)
    s = s.replace("-", MINUS)
    if style["decimal"] != ".":
        s = s.replace(".", style["decimal"])
    return s


def p_digits(p: float, style: dict) -> int:
    """Decimal places for P under a 'decimals' rule (first bound that p is below)."""
    for bound, dec in style.get("decimals", [(1.0, 2)]):
        if p < bound:
            return dec
    return style.get("decimals", [(1.0, 2)])[-1][1]


def _sig(p: float, n: int) -> int:
    return max(n - 1 - int(math.floor(math.log10(abs(p)))), 0) if p > 0 else n


def fmt_p(p: float, style: str | dict = "ama", markup: str = "parts"):
    """Format a P value in a house style.

    markup:
      "parts"    -> [("P", "italic"), (" < .001", "normal")] for rich_text(); keeps
                    SVG text live and unfragmented (preferred inside figures);
      "mathtext" -> "$\\mathit{P}$ < .001" (matplotlib renders glyph-by-glyph in SVG);
      "plain"    -> "P < .001"; "html" -> "<i>P</i> < .001".
    Exact P values are preferred over thresholds; values below the style's
    floor print as "< floor".
    """
    st = STATS_STYLES[style] if isinstance(style, str) else style
    if not (0 <= p <= 1):
        raise ValueError(f"P must be in [0, 1], got {p}")
    sp = " " if st["spaces"] else ""
    floor = st.get("floor")
    if floor and p < floor:
        rest = f"{sp}<{sp}{_fmt_number(floor, len(f'{floor:.10f}'.rstrip('0').split('.')[-1]), st)}"
    elif st.get("ceiling") and p > st["ceiling"]:
        rest = f"{sp}>{sp}{_fmt_number(st['ceiling'], 2, st)}"
    elif st.get("sci_below") and 0 < p < st["sci_below"]:
        mant, ex = f"{p:.{st.get('sigfigs', 2) - 1}e}".split("e")
        rest = f"{sp}={sp}{mant.replace('.', st['decimal'])} \u00d7 10" + sup(str(int(ex)))
    elif st.get("rule") == "sigfig":
        rest = f"{sp}={sp}{_fmt_number(p, _sig(p, st.get('sigfigs', 2)), st)}"
    else:
        rest = f"{sp}={sp}{_fmt_number(p, p_digits(p, st), st)}"
    sym = st["symbol"]
    if markup == "parts":
        return [(sym, "italic" if st["italic"] else "normal"), (rest, "normal")]
    if st["italic"]:
        sym = {"mathtext": f"$\\mathit{{{sym}}}$", "html": f"<i>{sym}</i>", "plain": sym}[markup]
    return sym + rest


def rich_text(ax, x: float, y: float, parts, *, transform=None, ha: str = "left", va: str = "bottom",
              fontsize: float | None = None, color: str = "#222222", linespacing: float = 1.25, zorder: float = 5,
              offset_pt: tuple[float, float] = (0.0, 0.0)):
    """Mixed-style text as separate live text runs sharing one baseline.

    parts: [(text, style), ...] where style is "normal", "italic", "bold",
    "bolditalic", or a dict of Text properties; "\\n" inside a text starts a
    new line. Used for italic statistical symbols (P, n, r, t, F, z) without
    mathtext, so SVG text stays editable phrase by phrase.
    """
    from matplotlib.offsetbox import AnnotationBbox, HPacker, TextArea, VPacker
    fs = fontsize or mpl.rcParams["legend.fontsize"]
    lines: list[list] = [[]]
    for txt, style in parts:
        for k, seg in enumerate(str(txt).split("\n")):
            if k:
                lines.append([])
            if seg:
                lines[-1].append((seg, style))

    def props(style):
        base = {"fontsize": fs, "color": color}
        if isinstance(style, dict):
            base.update(style)
        else:
            base["fontstyle"] = "italic" if "italic" in style else "normal"
            base["fontweight"] = "bold" if "bold" in style else "normal"
        return base

    def keep_spaces(seg):
        # SVG viewers collapse leading/trailing spaces of a <text> element; use no-break spaces at the edges
        core = seg.strip(" ")
        lead, trail = len(seg) - len(seg.lstrip(" ")), len(seg) - len(seg.rstrip(" "))
        return "\u00a0" * lead + core + "\u00a0" * trail if core else "\u00a0" * len(seg)

    rows = []
    for line in lines:
        kids = [TextArea(keep_spaces(seg), textprops=props(st)) for seg, st in line] or [TextArea("\u00a0", textprops=props("normal"))]
        rows.append(HPacker(children=kids, align="baseline", pad=0, sep=0))
    box = VPacker(children=rows, align={"left": "left", "center": "center", "right": "right"}[ha],
                  pad=0, sep=fs * (linespacing - 1))
    hx = {"left": 0.0, "center": 0.5, "right": 1.0}[ha]
    vy = {"bottom": 0.0, "center": 0.5, "top": 1.0, "baseline": 0.0}[va]
    ab = AnnotationBbox(box, (x, y), xycoords=transform if transform is not None else ax.transAxes,
                        xybox=offset_pt, boxcoords="offset points",
                        box_alignment=(hx, vy), frameon=False, pad=0, annotation_clip=False, zorder=zorder)
    ax.add_artist(ab)
    return ab


def fmt_ci(lo: float, hi: float, digits: int = 2, style: str | dict = "ama", label: bool = True) -> str:
    st = STATS_STYLES[style] if isinstance(style, str) else style
    sep = st["ci_neg_sep"] if (lo < 0 or hi < 0) else st["ci_sep"]
    keep = dict(st, leading_zero=True)  # estimates keep leading zeros; only P drops them in AMA
    body = f"{_fmt_number(lo, digits, keep)}{sep}{_fmt_number(hi, digits, keep)}"
    return f"{st['ci_label']}, {body}" if label else body


def fmt_estimate(est: float, lo: float, hi: float, measure: str | None = None, digits: int = 2,
                 style: str | dict = "ama", compact: bool = False) -> str:
    """'HR, 0.78 (95% CI, 0.65-0.94)' or compact '0.78 (0.65-0.94)' for forest columns."""
    st = STATS_STYLES[style] if isinstance(style, str) else style
    keep = dict(st, leading_zero=True)
    e = _fmt_number(est, digits, keep)
    if compact:
        return f"{e} ({fmt_ci(lo, hi, digits, st, label=False)})"
    head = f"{measure}, {e}" if measure else e
    return f"{head} ({fmt_ci(lo, hi, digits, st)})"


def fmt_mean_sd(mean: float, sd: float, digits: int = 1, unit: str = "") -> str:
    u = f" {unit}" if unit else ""
    return f"{mean:.{digits}f} ± {sd:.{digits}f}{u}".replace("-", MINUS)


def fmt_n_pct(n: int, total: int, digits: int = 1) -> str:
    return f"{n} ({100 * n / total:.{digits}f}%)"


# ---------------------------------------------------------------------------
# Export with verification
# ---------------------------------------------------------------------------
def _has_raster_content(fig) -> bool:
    from matplotlib.image import AxesImage, FigureImage
    return any(isinstance(a, (AxesImage, FigureImage)) for a in fig.findobj())


def _has_transparency(fig) -> bool:
    from matplotlib.colors import to_rgba
    for a in fig.findobj():
        alpha = getattr(a, "get_alpha", lambda: None)()
        if alpha is not None and alpha < 0.999:
            return True
        if hasattr(a, "get_facecolor"):
            try:
                arr = np.atleast_2d(a.get_facecolor())
                if arr.size and arr.shape[-1] == 4 and ((arr[:, 3] > 0.001) & (arr[:, 3] < 0.999)).any():
                    return True
            except (TypeError, ValueError):
                pass
    return False


def _pdf_page_mm(path: Path) -> tuple[float, float] | None:
    data = path.read_bytes()
    m = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", data)
    if not m:
        return None
    return (float(m.group(1)) / 72 * MM_PER_INCH, float(m.group(2)) / 72 * MM_PER_INCH)


def _render_rgb(fig, dpi: int):
    from PIL import Image
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    buf.seek(0)
    im = Image.open(buf)
    im.load()
    if im.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[-1])
        im = bg
    return im.convert("RGB")


def save(fig, stem: str | Path, formats: Iterable[str] | None = None, *, dpi: int | None = None,
         cmyk_tiff: bool = False, verify: bool = True, quiet: bool = False) -> dict:
    """Export at the fixed physical size and verify what was written.

    Vector masters (PDF/SVG/EPS) keep live text with embedded TrueType fonts.
    Raster outputs (PNG/TIFF/JPEG) are flattened onto white RGB without an
    alpha channel at the preset's DPI for the content (combination DPI when the
    figure contains images, line-art DPI otherwise). A PNG is rendered at that
    DPI only when the preset lists PNG as a submission format; otherwise it is
    a 600 dpi preview, tagged as such so figure_qa does not mistake it for the
    submission file. ``dpi=`` overrides both.
    Returns {"files": [...], "checks": [...], "problems": [...]}.
    """
    spec: FigSpec | None = getattr(fig, "_pubfig_spec", None)
    p = spec.preset if spec else GENERIC
    settle(fig)
    formats = [f.lower().lstrip(".") for f in (formats or p.get("formats", ["pdf", "svg", "png"]))]
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    raster_content = _has_raster_content(fig)
    report: dict = {"files": [], "checks": [], "problems": []}
    meta_pdf = {"Creator": None, "Producer": None, "CreationDate": None}
    w_in, h_in = fig.get_size_inches()
    for fmt in formats:
        out = stem.with_suffix("." + ("tif" if fmt in ("tif", "tiff") else fmt))
        if fmt == "pdf":
            fig.savefig(out, format="pdf", metadata=meta_pdf)
        elif fmt == "svg":
            fig.savefig(out, format="svg", metadata={"Date": None})
        elif fmt == "eps":
            if _has_transparency(fig):
                report["problems"].append("EPS cannot hold transparency; call flatten_alpha(fig) first or deliver PDF")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fig.savefig(out, format="eps")
        elif fmt in ("png", "tif", "tiff", "jpg", "jpeg"):
            req = p["dpi"]["combination"] if raster_content else p["dpi"]["line"]
            if dpi is not None:
                use_dpi = dpi
            elif fmt == "png" and "png" not in p.get("formats", []):
                use_dpi = min(req, max(600, p["dpi"]["combination"]))     # preview, not a submission file
            else:
                use_dpi = req
            role = "final" if use_dpi >= req else "preview"
            im = _render_rgb(fig, use_dpi)
            kind = "combination" if raster_content else "line"
            if fmt == "png":
                from PIL import PngImagePlugin
                info = PngImagePlugin.PngInfo()
                info.add_text("pubfig-kind", kind)
                info.add_text("pubfig-role", role)
                im.save(out, dpi=(use_dpi, use_dpi), optimize=True, pnginfo=info)
            elif fmt in ("tif", "tiff"):
                if cmyk_tiff:
                    report["problems"].append(
                        "CMYK via naive conversion (no ICC profile): colours shift; prefer RGB unless the journal requires CMYK")
                    im = im.convert("CMYK")
                im.save(out, dpi=(use_dpi, use_dpi), compression="tiff_lzw", tiffinfo={270: f"pubfig-kind={kind};role={role}"})
            else:
                report["problems"].append("JPEG is lossy: use only for photographs, never for line art or text")
                im.save(out, dpi=(use_dpi, use_dpi), quality=95, subsampling=0)
            if verify:
                exp_w, exp_h = round(w_in * use_dpi), round(h_in * use_dpi)
                ok = abs(im.size[0] - exp_w) <= 1 and abs(im.size[1] - exp_h) <= 1
                report["checks"].append(f"{out.name}: {im.size[0]}x{im.size[1]} px at {use_dpi} dpi "
                                        f"= {im.size[0] / use_dpi * MM_PER_INCH:.1f} x {im.size[1] / use_dpi * MM_PER_INCH:.1f} mm"
                                        + ("" if ok else " (SIZE MISMATCH)"))
        else:
            raise ValueError(f"unsupported format {fmt!r}")
        report["files"].append(str(out))
        if verify and fmt == "pdf":
            size = _pdf_page_mm(out)
            if size:
                ok = abs(size[0] - w_in * MM_PER_INCH) < 0.3 and abs(size[1] - h_in * MM_PER_INCH) < 0.3
                report["checks"].append(f"{out.name}: page {size[0]:.1f} x {size[1]:.1f} mm" + ("" if ok else " (SIZE MISMATCH)"))
                if not ok:
                    report["problems"].append(f"{out.name} page size differs from the figure canvas")
    if spec and spec.notes:
        report["problems"].extend(spec.notes)
    if not quiet:
        for line in report["checks"]:
            print("[saved]", line)
        for line in report["problems"]:
            print("[warn] ", line)
    return report


__all__ = [
    "mm", "pt_to_mm", "PRESETS", "preset", "register_preset", "resolve_font", "FontChoice", "FigSpec",
    "setup", "apply_style", "subplots", "figure", "OKABE_ITO", "CATEGORICAL", "TOL", "NEUTRALS", "ARMS",
    "SEQUENTIAL_CMAPS", "DIVERGING_CMAPS", "FORBIDDEN_CMAPS", "tint", "shade", "simulate_cvd",
    "delta_e2000", "contrast_ratio", "relative_luminance", "check_colors", "panel_labels",
    "reference_line", "min_line", "outline_width", "synthetic_tag", "settle", "on_settle", "root_figure", "flatten_alpha", "notation", "sub", "sup", "MINUS", "STATS_STYLES", "fmt_p", "rich_text",
    "fmt_ci", "fmt_estimate", "fmt_mean_sd", "fmt_n_pct", "save",
]
