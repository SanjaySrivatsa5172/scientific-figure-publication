"""Editable SVG schematics. No icon catalog, no Draw.io dependency.

Labels do the semantic work. A small role mark is optional and never replaces
the words. Feedback is a dashed corridor, not a decorative loop.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from .palette import load_palette

PT_TO_MM = 25.4 / 72.0

ROLE_KEY = {
    "data": "sky",
    "input": "sky",
    "model": "ours",
    "ours": "ours",
    "process": "strong_baseline",
    "check": "positive",
    "success": "positive",
    "fail": "negative",
    "baseline": "other_baselines",
    "neutral": "other_baselines",
}


def _esc(text: str) -> str:
    return escape(text, quote=True)


def build_schematic(spec: dict, out_svg: Path, palette_name: str = "okabe_ito") -> Path:
    stages = spec.get("stages") or []
    if not 2 <= len(stages) <= 5:
        raise ValueError("A schematic has 2 to 5 stages. Split the figure if you need more.")
    width = float(spec.get("width_mm", 178))
    height = float(spec.get("height_mm", 78))
    palette = load_palette(palette_name)
    roles = palette["roles"]
    ink = roles["ink"]
    muted = roles["muted"]
    grid = roles["grid"]

    margin_x = 8.0
    gap = 7.0
    n = len(stages)
    node_w = (width - 2 * margin_x - (n - 1) * gap) / n
    node_h = 22.0
    node_y = (height - node_h) / 2 + 2
    font_mm = 8.5 * PT_TO_MM
    small_mm = 7.5 * PT_TO_MM

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.2f}mm" height="{height:.2f}mm" '
        f'viewBox="0 0 {width:.2f} {height:.2f}" role="img">',
        "<title>Method schematic</title>",
        f'<rect width="{width:.2f}" height="{height:.2f}" fill="#FFFFFF"/>',
        '<desc>Editable text. No gradients, shadows, or embedded rasters.</desc>',
    ]

    centers = []
    for i, stage in enumerate(stages):
        x = margin_x + i * (node_w + gap)
        role = ROLE_KEY.get(str(stage.get("role", "neutral")), "other_baselines")
        fill = roles.get(role, roles["ours"])
        # Light card derived by mixing the role hue toward white, approximated
        # as a white card with a role-colored rail. Avoids a second invented hue.
        parts.append(
            f'<rect x="{x:.2f}" y="{node_y:.2f}" width="{node_w:.2f}" height="{node_h:.2f}" '
            f'rx="1.6" fill="#FFFFFF" stroke="{grid}" stroke-width="0.35"/>'
        )
        parts.append(
            f'<rect x="{x:.2f}" y="{node_y:.2f}" width="1.4" height="{node_h:.2f}" fill="{fill}"/>'
        )
        label = _esc(str(stage.get("label", f"Stage {i + 1}")))
        parts.append(
            f'<text x="{x + node_w / 2:.2f}" y="{node_y + node_h / 2 + font_mm * 0.35:.2f}" '
            f'text-anchor="middle" font-family="Arial, Liberation Sans, Helvetica, sans-serif" '
            f'font-size="{font_mm:.2f}" fill="{ink}">{label}</text>'
        )
        centers.append((x, x + node_w, node_y + node_h / 2))

    for i in range(n - 1):
        x1 = centers[i][1] + 0.6
        x2 = centers[i + 1][0] - 1.6
        y = centers[i][2]
        parts.append(
            f'<line x1="{x1:.2f}" y1="{y:.2f}" x2="{x2:.2f}" y2="{y:.2f}" '
            f'stroke="{ink}" stroke-width="0.45"/>'
        )
        parts.append(
            f'<polygon points="{x2:.2f},{y:.2f} {x2 - 1.8:.2f},{y - 0.9:.2f} {x2 - 1.8:.2f},{y + 0.9:.2f}" '
            f'fill="{ink}"/>'
        )

    feedback = spec.get("feedback")
    if feedback:
        src = int(feedback["from"])
        dst = int(feedback["to"])
        if not (0 <= dst < src < n):
            raise ValueError("Feedback must point to an earlier stage")
        y_top = node_y - 6.5
        x_src = (centers[src][0] + centers[src][1]) / 2
        x_dst = (centers[dst][0] + centers[dst][1]) / 2
        parts.append(
            f'<path d="M {x_src:.2f} {node_y:.2f} V {y_top:.2f} H {x_dst:.2f} V {node_y - 0.4:.2f}" '
            f'fill="none" stroke="{muted}" stroke-width="0.4" stroke-dasharray="1.2 0.8"/>'
        )
        parts.append(
            f'<polygon points="{x_dst:.2f},{node_y - 0.2:.2f} {x_dst - 0.8:.2f},{node_y - 2.0:.2f} '
            f'{x_dst + 0.8:.2f},{node_y - 2.0:.2f}" fill="{muted}"/>'
        )
        label = _esc(str(feedback.get("label", "reject")))
        parts.append(
            f'<text x="{(x_src + x_dst) / 2:.2f}" y="{y_top - 1.2:.2f}" text-anchor="middle" '
            f'font-family="Arial, Liberation Sans, Helvetica, sans-serif" '
            f'font-size="{small_mm:.2f}" fill="{muted}">{label}</text>'
        )

    parts.append("</svg>")
    out = Path(out_svg)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return out


def build_schematic_file(spec_path: Path, out_svg: Path, palette_name: str = "okabe_ito") -> Path:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    return build_schematic(spec, out_svg, palette_name=palette_name)
