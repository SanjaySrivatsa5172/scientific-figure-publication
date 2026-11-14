"""Acceptance checks for contracts and SVG masters.

A warning is a failure. The script does not grant silent waivers.
"""

from __future__ import annotations

import colorsys
import json
import re
import sys
from pathlib import Path

_REQUIRED = (
    "claim",
    "takeaway",
    "mode",
    "lane",
    "width_mm",
    "palette_id",
    "palette_status",
    "data_provenance",
)


def audit_contract(contract: dict) -> list[str]:
    issues = []
    for key in _REQUIRED:
        if key not in contract or contract[key] in ("", None):
            issues.append(f"contract missing {key}")
    claim = str(contract.get("claim", "")).strip()
    if claim and len(claim) > 280:
        issues.append("claim is longer than one sentence-worth of text (280 characters)")
    mode = contract.get("mode")
    if mode not in {"manuscript", "slide", "poster"}:
        issues.append(f"unknown mode {mode!r}")
    lane = contract.get("lane")
    if lane not in {"data", "schematic", "image", "polish"}:
        issues.append(f"unknown lane {lane!r}")
    if contract.get("synthetic") and "synthetic" not in str(contract.get("data_provenance", "")).lower():
        issues.append("synthetic data must say so in data_provenance")
    if contract.get("palette_status") == "frozen" and not contract.get("palette_digest"):
        issues.append("frozen palette needs palette_digest")
    width = contract.get("width_mm")
    guide = str(contract.get("journal_guide") or "").strip()
    if mode == "manuscript" and isinstance(width, (int, float)):
        if not guide and not (82 <= float(width) <= 190):
            issues.append("manuscript width is outside 82 to 190 mm and no journal guide is cited")
    if contract.get("design") == "unspecified" and contract.get("lane") == "data":
        issues.append("data lane needs a declared design (independent, paired, repeated, or summary-metric)")
    if contract.get("axis_includes_zero") is False and not contract.get("truncation_disclosed"):
        issues.append("an axis that omits zero must set truncation_disclosed")
    return issues


def _length_to_mm(raw: str) -> float | None:
    match = re.match(r"^\s*([0-9.]+)\s*(mm|pt|px)?\s*$", raw)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2) or "px"
    if unit == "mm":
        return value
    if unit == "pt":
        return value * 25.4 / 72.0
    return value * 25.4 / 96.0


def _hex_channels(token: str) -> tuple[int, int, int] | None:
    if re.fullmatch(r"[0-9A-Fa-f]{6}", token):
        return int(token[0:2], 16), int(token[2:4], 16), int(token[4:6], 16)
    return None


def _hue_deg(r: int, g: int, b: int) -> float | None:
    rf, gf, bf = r / 255, g / 255, b / 255
    mx = max(rf, gf, bf)
    mn = min(rf, gf, bf)
    if mx < 0.12 or (mx - mn) < 0.08:
        return None
    _h, _s, _v = colorsys.rgb_to_hsv(rf, gf, bf)
    if _s < 0.22:
        return None
    return _h * 360.0


def _hue_families(svg_text: str) -> list[float]:
    found: list[float] = []
    for token in re.findall(r"#([0-9A-Fa-f]{6})", svg_text):
        channels = _hex_channels(token)
        if channels is None:
            continue
        hue = _hue_deg(*channels)
        if hue is None:
            continue
        if any(min(abs(hue - prev), 360 - abs(hue - prev)) < 28 for prev in found):
            continue
        found.append(hue)
    for r, g, b in re.findall(r"rgb\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)", svg_text):
        hue = _hue_deg(int(float(r)), int(float(g)), int(float(b)))
        if hue is None:
            continue
        if any(min(abs(hue - prev), 360 - abs(hue - prev)) < 28 for prev in found):
            continue
        found.append(hue)
    return found


def audit_svg(svg_text: str, expected_width_mm: float | None = None, mode: str = "manuscript") -> list[str]:
    issues = []
    lowered = svg_text.lower()
    for token in ("lineargradient", "radialgradient", "fedropshadow", "feblend"):
        if token in lowered:
            issues.append(f"forbidden effect: {token}")
    if re.search(r"\bfilter\s*=", lowered):
        issues.append("forbidden effect: filter")

    width_attr = re.search(r"<svg\b[^>]*\bwidth=\"([^\"]+)\"", svg_text)
    view_attr = re.search(r'viewBox="\s*[-0-9.]+\s+[-0-9.]+\s+([0-9.]+)\s+([0-9.]+)\s*"', svg_text)
    if not width_attr:
        issues.append("svg has no width")
        width_mm = None
    else:
        width_mm = _length_to_mm(width_attr.group(1))
        if width_mm is None:
            issues.append(f"could not read svg width {width_attr.group(1)!r}")
        elif expected_width_mm is not None and abs(width_mm - expected_width_mm) > 2.5:
            issues.append(
                f"svg width {width_mm:.1f} mm differs from declared {expected_width_mm:.1f} mm"
            )

    sizes = set()
    if width_mm and view_attr:
        vb_w = float(view_attr.group(1))
        user_mm = width_mm / vb_w if vb_w else None
    else:
        user_mm = None
    for raw in re.findall(r"font-size\s*:\s*([0-9.]+)(pt|px|mm)?", svg_text):
        sizes.add(_to_pt(raw[0], raw[1], user_mm))
    for raw in re.findall(r'font-size="([0-9.]+)(pt|px|mm)?"', svg_text):
        sizes.add(_to_pt(raw[0], raw[1], user_mm))
    sizes.discard(None)
    if not sizes:
        issues.append("no live font-size found; text may have been outlined")
    else:
        floor = 7.0 if mode == "manuscript" else 10.0
        small = sorted(s for s in sizes if s < floor - 0.2)
        if small:
            issues.append(f"text below {floor:.0f} pt: {small}")
        # Matplotlib can emit sub-point differences for the same nominal size.
        snapped = {round(s * 2) / 2 for s in sizes}
        if len(snapped) > 3:
            issues.append(f"more than three type sizes: {sorted(snapped)}")

    families = _hue_families(svg_text)
    if len(families) > 5:
        issues.append(f"more than five semantic hue families ({len(families)})")

    if "<text" not in lowered and "<tspan" not in lowered:
        issues.append("no live text elements")
    return issues


def _to_pt(number: str, unit: str, user_mm: float | None) -> float | None:
    value = float(number)
    if unit == "pt":
        return value
    if unit == "mm":
        return value * 72.0 / 25.4
    if user_mm is not None:
        return value * user_mm * 72.0 / 25.4
    return value * 72.0 / 96.0


def audit_svg_file(path: Path, expected_width_mm: float | None = None, mode: str = "manuscript") -> list[str]:
    return audit_svg(Path(path).read_text(encoding="utf-8"), expected_width_mm, mode)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: python -m pubfig.qa figure.svg [--width-mm 85] [--mode manuscript] [--contract c.json]")
        return 2
    issues: list[str] = []
    files = []
    width = None
    mode = "manuscript"
    contract = None
    i = 0
    while i < len(args):
        item = args[i]
        if item == "--width-mm":
            width = float(args[i + 1])
            i += 2
            continue
        if item == "--mode":
            mode = args[i + 1]
            i += 2
            continue
        if item == "--contract":
            contract = Path(args[i + 1])
            i += 2
            continue
        files.append(Path(item))
        i += 1
    if contract:
        data = json.loads(contract.read_text(encoding="utf-8"))
        issues.extend(audit_contract(data))
        if width is None and data.get("width_mm"):
            width = float(data["width_mm"])
        mode = str(data.get("mode", mode))
    for path in files:
        issues.extend(f"{path.name}: {item}" for item in audit_svg_file(path, width, mode))
    if issues:
        print("FAIL")
        for item in issues:
            print(f"- {item}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
