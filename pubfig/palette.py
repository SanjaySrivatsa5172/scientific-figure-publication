"""Palette registry. One frozen mapping per paper. Neutrals are not hues."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

_ASSET = Path(__file__).resolve().parents[1] / "assets" / "palettes.json"

NEUTRALS = {
    "#FFFFFF",
    "#FFF",
    "#000000",
    "#000",
    "#172033",
    "#272727",
    "#4D4D4D",
    "#5B6472",
    "#64748B",
    "#666666",
    "#767676",
    "#CBD5E1",
    "#CFCECE",
    "#E2E8F0",
}


def load_palette(name: str = "okabe_ito") -> dict:
    data = json.loads(_ASSET.read_text(encoding="utf-8"))
    if name not in data:
        known = ", ".join(sorted(data))
        raise KeyError(f"Unknown palette {name!r}. Known: {known}")
    return data[name]


def digest(roles: dict) -> str:
    payload = json.dumps(roles, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


PALETTES = json.loads(_ASSET.read_text(encoding="utf-8"))
