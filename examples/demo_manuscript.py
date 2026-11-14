"""Build the four demo masters and refuse a deliberately bad SVG.

Run from anywhere:
  python examples/demo_manuscript.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pubfig.images import standardize_batch  # noqa: E402
from pubfig.palette import digest, load_palette  # noqa: E402
from pubfig.plots import (  # noqa: E402
    finalize_figure,
    make_grouped_bar,
    make_heatmap,
    make_paired_slopes,
    make_trend,
    new_figure,
)
from pubfig.qa import audit_contract, audit_svg  # noqa: E402
from pubfig.schematic import build_schematic  # noqa: E402
from pubfig.style import style_for  # noqa: E402

OUT = ROOT / "examples" / "output"


def _style(width, mode="manuscript"):
    style = style_for(mode, width_mm=width)
    if not style.font_exact:
        print(
            f"note: {style.font_family} is not installed. "
            f"Using {style.resolved_font}. final_delivery_allowed=false until the requested face is embedded."
        )
    return style


def estimation():
    style = _style(85)
    fig, ax = new_figure(style, 70)
    fig.subplots_adjust(left=0.22, right=0.97, bottom=0.16, top=0.78)
    before = [0.48, 0.55, 0.42, 0.61, 0.39, 0.52, 0.44, 0.58, 0.47, 0.50]
    after = [0.26, 0.31, 0.22, 0.34, 0.21, 0.28, 0.25, 0.36, 0.24, 0.29]
    roles = load_palette("okabe_ito")["roles"]
    stats = make_paired_slopes(ax, before, after, ["Before", "After"], roles["ours"], "Reflux time (s)")
    ax.set_ylim(0, 0.75)
    saved = finalize_figure(fig, OUT / "paired_slopes", dpi=300)
    contract = {
        "parent_bot": "scientific-manuscript-draft-bot",
        "manuscript_id": "demo",
        "figure_id": "Fig1",
        "section": "results",
        "claim": "In this synthetic pair, reflux time is shorter after the second time point.",
        "takeaway": "Every pair falls, and the mean difference is about two tenths of a second.",
        "mode": "manuscript",
        "lane": "data",
        "width_mm": 85,
        "palette_id": "okabe-ito-manuscript-v1",
        "palette_status": "frozen",
        "palette_digest": digest(roles),
        "design": "paired",
        "experimental_unit": "synthetic subject",
        "estimand": "mean paired difference, before minus after",
        "uncertainty": "95% Student t interval",
        "axis_includes_zero": True,
        "truncation_disclosed": False,
        "data_provenance": "synthetic demo, not a clinical measurement",
        "synthetic": True,
        "journal_guide": "",
        "stats": {k: stats[k] for k in ("n", "mean", "low", "high", "method")},
    }
    (OUT / "paired_slopes.contract.json").write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    return saved, contract


def bars():
    style = _style(178)
    fig, ax = new_figure(style, 78)
    fig.subplots_adjust(left=0.12, right=0.98, bottom=0.18, top=0.74)
    roles = load_palette("okabe_ito")["roles"]
    colors = [roles["ours"], roles["strong_baseline"], roles["other_baselines"]]
    make_grouped_bar(
        ax,
        ["Accuracy", "F1", "AUROC", "Calibration"],
        [
            [0.91, 0.88, 0.93, 0.90],
            [0.86, 0.84, 0.88, 0.82],
            [0.79, 0.77, 0.81, 0.74],
        ],
        ["Proposed", "Named baseline", "Other"],
        ylabel="Score",
        colors=colors,
        ymin=0.60,
        ymax=1.0,
    )
    ax.text(
        0.02,
        0.06,
        "Axis starts at 0.60",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=style.font_size,
        color="#5B6472",
    )
    saved = finalize_figure(fig, OUT / "grouped_bars", dpi=300)
    return saved


def trend():
    style = _style(178)
    fig, ax = new_figure(style, 72)
    fig.subplots_adjust(left=0.12, right=0.98, bottom=0.18, top=0.90)
    x = np.arange(0, 21)
    a = 0.55 + 0.35 * (1 - np.exp(-x / 6))
    b = 0.52 + 0.28 * (1 - np.exp(-x / 8))
    roles = load_palette("okabe_ito")["roles"]
    band_a = (a - 0.03, a + 0.03)
    band_b = (b - 0.035, b + 0.035)
    make_trend(
        ax,
        x,
        [a, b],
        ["Proposed", "Baseline"],
        colors=[roles["ours"], roles["strong_baseline"]],
        xlabel="Epoch",
        ylabel="Held-out score",
        bands=[band_a, band_b],
    )
    ax.set_ylim(0.4, 1.0)
    return finalize_figure(fig, OUT / "trends", dpi=300)


def heatmap():
    style = _style(89)
    fig, ax = new_figure(style, 78)
    fig.subplots_adjust(left=0.18, right=0.86, bottom=0.16, top=0.92)
    rng = np.random.default_rng(4)
    matrix = rng.random((5, 5))
    matrix = (matrix + matrix.T) / 2
    labels = [f"F{i}" for i in range(1, 6)]
    meta = make_heatmap(ax, matrix, labels, labels, cbar_label="Correlation")
    saved = finalize_figure(fig, OUT / "heatmap", dpi=300)
    (OUT / "heatmap.scale.json").write_text(json.dumps(meta) + "\n", encoding="utf-8")
    return saved


def schematic():
    spec = {
        "width_mm": 178,
        "height_mm": 72,
        "stages": [
            {"id": "in", "label": "Acquire", "role": "data"},
            {"id": "core", "label": "Segment", "role": "model"},
            {"id": "check", "label": "Verify", "role": "check"},
            {"id": "out", "label": "Report", "role": "success"},
        ],
        "feedback": {"from": 2, "to": 1, "label": "reject"},
    }
    return build_schematic(spec, OUT / "schematic.svg")


def images():
    raw = OUT / "raw_images"
    raw.mkdir(parents=True, exist_ok=True)
    Image.new("L", (240, 180), 40).save(raw / "a.png")
    Image.new("L", (300, 200), 180).save(raw / "b.png")
    manifest = OUT / "images.csv"
    manifest.write_text(
        "file,output_name,um_per_pixel\n"
        f"{raw / 'a.png'},a_std.png,0.5\n"
        f"{raw / 'b.png'},b_std.png,0.5\n",
        encoding="utf-8",
    )
    return standardize_batch(manifest, OUT / "images", scale_bar_um=20)


def bad_svg_must_fail():
    text = """<svg xmlns="http://www.w3.org/2000/svg" width="85mm" height="40mm" viewBox="0 0 85 40">
      <defs><linearGradient id="g"><stop offset="0" stop-color="#0072B2"/></linearGradient></defs>
      <rect width="85" height="40" fill="url(#g)"/>
      <text x="4" y="20" font-size="1.2" fill="#0072B2">tiny</text>
    </svg>
    """
    issues = audit_svg(text, expected_width_mm=85, mode="manuscript")
    if not issues:
        raise SystemExit("QA failed to catch a bad SVG")
    return issues


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    saved, contract = estimation()
    contract_issues = audit_contract(contract)
    svg_issues = []
    for folder_item in [saved, bars(), trend(), heatmap()]:
        for path in folder_item:
            if path.suffix == ".svg":
                width = 85 if "paired" in path.name else (89 if "heatmap" in path.name else 178)
                svg_issues.extend(f"{path.name}: {item}" for item in audit_svg(path.read_text(encoding="utf-8"), width))
    schematic_path = schematic()
    svg_issues.extend(
        f"schematic.svg: {item}" for item in audit_svg(schematic_path.read_text(encoding="utf-8"), 178)
    )
    audit = images()
    caught = bad_svg_must_fail()
    print("contract", "PASS" if not contract_issues else contract_issues)
    print("svg", "PASS" if not svg_issues else svg_issues)
    print("images", len(audit["rows"]), "scale", audit["rows"][0]["scale_bar"])
    print("bad svg caught", len(caught), "issues")
    if contract_issues or svg_issues:
        raise SystemExit(1)
    stats = contract["stats"]
    packet = {
        "to": "scientific-manuscript-draft-bot",
        "from_skill": "scientific-figure-publication",
        "manuscript_id": contract["manuscript_id"],
        "figure_id": contract["figure_id"],
        "section": contract["section"],
        "files": {
            "svg": "paired_slopes.svg",
            "pdf": "paired_slopes.pdf",
            "png": "paired_slopes.png",
            "source": "examples/demo_manuscript.py",
        },
        "legend": (
            "Figure 1. Synthetic pairs (n = {n}). Mean reflux time fell by {mean:.2f} s "
            "(95% CI {low:.2f} to {high:.2f}, {method}). Not a clinical result."
        ).format(**stats),
        "callout": "Figure 1 shows a shorter reflux time at the second point in every synthetic pair.",
        "palette_id": contract["palette_id"],
        "palette_digest": contract["palette_digest"],
        "qa": "PASS",
        "limits": [
            "Synthetic data.",
            "Arial was requested. If the log says a fallback font, final_delivery_allowed is false.",
        ],
    }
    (OUT / "figure_packet.json").write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    print("DEMO PASS")


if __name__ == "__main__":
    main()
