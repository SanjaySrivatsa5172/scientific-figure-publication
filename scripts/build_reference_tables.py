#!/usr/bin/env python3
"""Regenerate references/journal-specs.md and references/sources.md.

journal-specs.md is rendered from pubfig.PRESETS (the single source of truth
used by the code); sources.md from assets/journal-specs/citations_verified.json.
Run after editing a preset or the citation file:
    python scripts/build_reference_tables.py
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
warnings.simplefilter("ignore")
import pubfig as pf  # noqa: E402

GROUPS = [
    ("Cardiovascular, vascular, and general medical journals",
     ["jacc", "jacc_family", "aha", "ehj", "eurointervention", "jvs", "ejves", "ccv", "jevt", "vascmed", "sage",
      "jama", "nejm", "lancet", "bmj", "annals"]),
    ("General science journals", ["nature", "natureportfolio", "naturecomms", "science", "scienceadv", "cell", "pnas",
                                  "plos", "elife"]),
    ("Publishers (generic artwork guides)", ["elsevier", "springer", "bmc", "wiley", "oup", "tandf", "acs",
                                             "royalsociety", "frontiers", "mdpi"]),
    ("Engineering and machine-learning venues", ["ieee", "acm", "neurips", "iclr", "icml", "cvpr", "acl"]),
    ("Non-print modes and fallback", ["generic", "presentation", "poster", "showcase"]),
]


def fmt_widths(w):
    return ", ".join(f"{k} {v:g}" for k, v in w.items() if v)


def journal_specs() -> str:
    out = ["# Journal specifications",
           "",
           "Rendered from `pubfig.PRESETS` by `scripts/build_reference_tables.py`; do not edit by hand. Values come from "
           "official author instructions retrieved 2026-11-14; verbatim quotes and URLs are in "
           "`assets/journal-specs/journal_specs_clinical.json` and `journal_specs_science.json`. Where a journal is silent, "
           "the preset uses its publisher's generic guide or the skill's generic values, and the note says so.",
           "",
           "Before a real submission: open the journal's current instructions (URL below), confirm width, resolution, "
           "font, format, and panel-label rules, and record the URL and date with the figure files. For a journal not "
           "listed, read its instructions and call `pubfig.register_preset(key, {...})` with only the values it states.",
           "",
           "Units: widths and heights in mm; type in pt at final size (label/tick/panel); lines in pt (axes/data/minimum); "
           "DPI as line art/halftone/combination.",
           ""]
    for title, keys in GROUPS:
        out += [f"## {title}", ""]
        for k in keys:
            p = pf.PRESETS[k]
            t, ln, d = p["type"], p["lines"], p["dpi"]
            out.append(f"### {p['name']} (`{k}`)")
            out.append(f"- Widths: {fmt_widths(p['widths_mm'])}; max height {p.get('max_height_mm')}")
            out.append(f"- Font: {p['font']['family']}, {p['font']['min_pt']:g} to {p['font']['max_pt']:g} pt; "
                       f"labels {t['label']:g}, ticks {t['tick']:g}, panel {t['panel']:g} pt "
                       f"{p['panel']['weight']} '{p['panel']['style']}'")
            out.append(f"- Lines: axes {ln['axes']:g}, data {ln['data']:g}, minimum {ln['minimum']:g} pt; "
                       f"DPI {d['line']}/{d['halftone']}/{d['combination']}; formats {', '.join(p.get('formats', []))}; "
                       f"color {p.get('color_mode', 'RGB')}; statistics style `{p.get('stats', 'ama')}`")
            if p.get("rules"):
                out.append(f"- Chart rules checked by figure_qa: {', '.join(p['rules'])}")
            if p.get("unstated"):
                out.append(f"- Not stated by the source (default used): {'; '.join(p['unstated'])}")
            if p.get("note"):
                out.append(f"- Note: {p['note']}")
            if p.get("source"):
                out.append(f"- Source: {p['source']} (retrieved {p.get('retrieved')})")
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def sources() -> str:
    data = json.loads((ROOT / "assets/journal-specs/citations_verified.json").read_text(encoding="utf-8"))
    out = ["# Sources",
           "",
           "Every reference below was checked against PubMed, Crossref, or the DOI landing page on 2026-11-14 "
           "(`assets/journal-specs/citations_verified.json` records status, PMID, DOI, and any correction to draft "
           "metadata). None is retracted. The one-line summaries paraphrase the abstract; where no abstract exists, the "
           "summary is marked or omitted.",
           ""]
    for x in data:
        line = f"- {x['ama']}"
        if x.get("pmid"):
            line += f" PMID {x['pmid']}."
        out.append(line)
        if x.get("key_point"):
            out.append(f"  - {x['key_point']}")
    out += ["",
            "Other sources cited in the references:",
            "- Wasserstein RL, Lazar NA. The ASA statement on p-values: context, process, and purpose. Am Stat. 2016;70(2):129-133. doi:10.1080/00031305.2016.1154108 (checked against Crossref).",
            "- Paul Tol's color schemes: values checked against the `tol-colors` package; Okabe-Ito values checked against an independent palette registry (`pypalettes`).",
            "- Journal and publisher author instructions: URLs per preset in `references/journal-specs.md`, quotes in `assets/journal-specs/`.",
            "- Source repositories: qhy991/Scientific-Figure-Design (MIT), zhoy0409-debug/polish-sci-figures (MIT), ChenLiu-1996/figures4papers (CC BY-NC 4.0)."]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    (ROOT / "references/journal-specs.md").write_text(journal_specs(), encoding="utf-8")
    (ROOT / "references/sources.md").write_text(sources(), encoding="utf-8")
    print("wrote references/journal-specs.md and references/sources.md")
