"""Write figure_packet.json: the handoff from this skill back to the
scientific manuscript draft bot (see references/manuscript-bot.md).

The packet names the delivered files, the legend, one callout sentence, the
paper palette and its digest, the QA verdict, and the limits a reader of the
draft must know (font substitution, synthetic data, accepted warnings).

    python figure_qa.py final_figures/Fig1.pdf final_figures/Fig1.tif \
        --target jvs --column double --json > qa/Fig1_qa.json
    python figure_packet.py final_figures --figure-id Fig1 --manuscript-id M-001 \
        --legend-file legends/Fig1.txt --callout "Figure 1 shows ..." \
        --qa-json qa/Fig1_qa.json --palette paper-palette.yaml --manual-checks-done

qa is "PASS" only when the automated audit has no FAIL, every WARN is fixed
or accepted with a written reason, and the manual checks in
references/qa-checklist.md were done; "REVIEW" when the audit is clean but
the manual checks are not confirmed; "FAIL" otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FORMATS = ("pdf", "svg", "eps", "png", "tif", "tiff", "jpg", "jpeg")


def palette_identity(palette_file: str | Path) -> tuple[str, str]:
    """(palette_id, SHA-256) computed exactly as the draw.io pipeline does."""
    sys.path.insert(0, str(HERE))
    import build_drawio_figure as bdf
    try:
        payload, digest = bdf.read_paper_palette(Path(palette_file), bdf.read_academic_style())
    except SystemExit as exc:          # the pipeline exits on an invalid palette
        raise ValueError(f"paper palette rejected: {exc}") from None
    return str(payload.get("palette_id", "")), digest


def qa_verdict(findings: list[dict], accepted: dict[str, str] | None = None,
               manual_checks_done: bool = False) -> tuple[str, list[str]]:
    """Verdict plus the reasons it is not PASS."""
    accepted = accepted or {}
    reasons = [f"FAIL {f['code']}: {f['message']}" for f in findings if f.get("severity") == "FAIL"]
    reasons += [f"WARN {f['code']} not fixed or accepted: {f['message']}" for f in findings
                if f.get("severity") == "WARN" and f.get("code") not in accepted]
    if reasons:
        return "FAIL", reasons
    if not manual_checks_done:
        return "REVIEW", ["manual checks in references/qa-checklist.md not confirmed"]
    return "PASS", []


def build_packet(*, figure_id: str, files: dict[str, str], legend: str, callout: str,
                 findings: list[dict], manuscript_id: str = "", section: str = "results",
                 palette_file: str | Path | None = None, accepted_warnings: dict[str, str] | None = None,
                 limits: list[str] | tuple = (), synthetic: bool = False, manual_checks_done: bool = False,
                 preset: str | None = None, to: str = "scientific-manuscript-draft-bot") -> dict:
    accepted = dict(accepted_warnings or {})
    verdict, reasons = qa_verdict(findings, accepted, manual_checks_done)
    lim = list(limits)
    if synthetic:
        lim.insert(0, "Synthetic data; not a study result.")
    for f in findings:
        if f.get("code") == "FONT_NOT_REQUIRED":
            lim.append(f"Font substitution: {f['message']}. Not final until the required font is installed.")
            break
    lim += [f"Accepted {code}: {why}" for code, why in accepted.items()]
    palette_id, digest = palette_identity(palette_file) if palette_file else ("", "")
    counts = {s: sum(f.get("severity") == s for f in findings) for s in ("FAIL", "WARN", "REVIEW")}
    return {
        "to": to,
        "from_skill": "scientific-figure-publication",
        "manuscript_id": manuscript_id,
        "figure_id": figure_id,
        "section": section,
        "files": files,
        "legend": legend,
        "callout": callout,
        "palette_id": palette_id,
        "palette_digest": digest,
        "journal_preset": preset or "",
        "qa": verdict,
        "qa_counts": counts,
        "qa_open_items": reasons,
        "limits": lim,
    }


def collect_files(folder: Path, stem: str, source: str | None) -> dict[str, str]:
    files = {}
    for fmt in FORMATS:
        p = folder / f"{stem}.{fmt}"
        if p.exists():
            files["tif" if fmt == "tiff" else ("jpg" if fmt == "jpeg" else fmt)] = str(p)
    if source:
        files["source"] = source
    return files


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", help="folder holding the exported files (Fig1.pdf, Fig1.svg, ...)")
    ap.add_argument("--figure-id", required=True, help="file stem and figure id, e.g. Fig1")
    ap.add_argument("--manuscript-id", default="")
    ap.add_argument("--section", default="results")
    ap.add_argument("--legend", default="", help="legend text (or use --legend-file)")
    ap.add_argument("--legend-file")
    ap.add_argument("--callout", default="", help="one sentence the parent may edit into the text")
    ap.add_argument("--qa-json", required=True, help="output of figure_qa.py --json")
    ap.add_argument("--accept", action="append", default=[], metavar="CODE=REASON",
                    help="a WARN code accepted with its written reason (repeatable)")
    ap.add_argument("--palette", help="frozen paper palette (assets/paper-palette.yaml format)")
    ap.add_argument("--source", help="figure script path to record")
    ap.add_argument("--preset", help="journal preset used")
    ap.add_argument("--limit", action="append", default=[], help="a limit to state (repeatable)")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--manual-checks-done", action="store_true",
                    help="the manual checks in references/qa-checklist.md were actually done")
    ap.add_argument("--out", help="packet path (default: <folder>/<figure-id>_packet.json)")
    a = ap.parse_args(argv)
    legend = Path(a.legend_file).read_text(encoding="utf-8").strip() if a.legend_file else a.legend
    findings = json.loads(Path(a.qa_json).read_text(encoding="utf-8"))
    accepted = {}
    for item in a.accept:
        code, _, why = item.partition("=")
        if not why.strip():
            ap.error(f"--accept {code} needs a written reason (CODE=REASON)")
        accepted[code.strip()] = why.strip()
    folder = Path(a.folder)
    packet = build_packet(figure_id=a.figure_id, files=collect_files(folder, a.figure_id, a.source),
                          legend=legend, callout=a.callout, findings=findings, manuscript_id=a.manuscript_id,
                          section=a.section, palette_file=a.palette, accepted_warnings=accepted,
                          limits=a.limit, synthetic=a.synthetic, manual_checks_done=a.manual_checks_done,
                          preset=a.preset)
    out = Path(a.out) if a.out else folder / f"{a.figure_id}_packet.json"
    out.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}: qa={packet['qa']}" + "".join(f"\n  - {r}" for r in packet["qa_open_items"]))
    return 0 if packet["qa"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
