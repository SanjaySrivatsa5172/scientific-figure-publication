"""Non-destructive image panels.

Raw files stay put. A scale bar is drawn only when the caller supplies
micrometres per pixel. Display windows, if set, are shared by the whole batch.
A hash match is a review candidate, not a misconduct judgment.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _font(size: int):
    candidates = list(Path("/usr/share/fonts").rglob("LiberationSans-Regular.ttf"))
    candidates += list(Path("/usr/share/fonts").rglob("DejaVuSans.ttf"))
    if candidates:
        return ImageFont.truetype(str(candidates[0]), size=size)
    return ImageFont.load_default(size=size)


def standardize_batch(
    manifest_csv: Path,
    outdir: Path,
    scale_bar_um: float | None = None,
    display: dict | None = None,
) -> dict:
    """Center-crop a batch to a shared canvas and write an audit.

    Manifest columns: file, output_name, and um_per_pixel when a scale bar
    is requested. Optional display keys: min, max, gamma. Applied to every
    image or not at all.
    """
    manifest_csv = Path(manifest_csv)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(manifest_csv.open(newline="", encoding="utf-8")))
    if not rows:
        raise ValueError("Image manifest is empty")

    if scale_bar_um is not None:
        missing = [row.get("file", "") for row in rows if not row.get("um_per_pixel")]
        if missing:
            raise ValueError(
                "Refusing to invent a scale bar. Missing um_per_pixel for: " + ", ".join(missing)
            )

    if display is not None:
        if set(display) - {"min", "max", "gamma"}:
            raise ValueError("Display window accepts only min, max, gamma")
        if "min" not in display or "max" not in display:
            raise ValueError("A display window needs both min and max, shared by the batch")

    opened = []
    for row in rows:
        src = Path(row["file"])
        if not src.is_file():
            raise FileNotFoundError(src)
        image = Image.open(src)
        image.load()
        opened.append((row, src, image, _sha256(src)))

    crop_w = min(image.width for _, _, image, _ in opened)
    crop_h = min(image.height for _, _, image, _ in opened)
    audit_rows = []

    for row, src, image, file_hash in opened:
        gray = ImageOps.grayscale(image) if image.mode != "L" else image
        left = max((gray.width - crop_w) // 2, 0)
        top = max((gray.height - crop_h) // 2, 0)
        cropped = gray.crop((left, top, left + crop_w, top + crop_h))
        if display is not None:
            lo = float(display["min"])
            hi = float(display["max"])
            gamma = float(display.get("gamma", 1.0))
            if hi <= lo:
                raise ValueError("display max must exceed min")

            def _map(pixel, lo=lo, hi=hi, gamma=gamma):
                x = (pixel - lo) / (hi - lo)
                if x < 0:
                    x = 0.0
                elif x > 1:
                    x = 1.0
                return int(round((x ** (1.0 / gamma)) * 255))

            cropped = cropped.point(_map)

        canvas = cropped.convert("RGB")
        draw = ImageDraw.Draw(canvas)
        bar = None
        if scale_bar_um is not None:
            um_per_px = float(row["um_per_pixel"])
            if um_per_px <= 0:
                raise ValueError(f"um_per_pixel must be positive for {src.name}")
            bar_px = int(round(float(scale_bar_um) / um_per_px))
            if bar_px < 8 or bar_px > crop_w * 0.5:
                raise ValueError(
                    f"Scale bar of {bar_px}px does not fit honestly in {src.name}. "
                    "Change the labelled length or the crop. Do not stretch the image."
                )
            margin = max(int(crop_h * 0.06), 8)
            x0 = crop_w - margin - bar_px
            y0 = crop_h - margin
            strip = canvas.crop((x0, max(0, y0 - 4), x0 + bar_px, min(crop_h, y0 + 6)))
            mean = sum(strip.resize((1, 1)).getpixel((0, 0))[:3]) / 3
            ink = (255, 255, 255) if mean < 140 else (23, 32, 51)
            width = max(2, crop_h // 80)
            draw.line([(x0, y0), (x0 + bar_px, y0)], fill=ink, width=width)
            label = f"{float(scale_bar_um):g} µm"
            font = _font(max(12, crop_h // 28))
            text_width = draw.textlength(label, font=font)
            draw.text((x0 + (bar_px - text_width) / 2, y0 - font.size - 2), label, fill=ink, font=font)
            bar = {"um": scale_bar_um, "px": bar_px, "um_per_pixel": um_per_px}

        name = row.get("output_name") or (src.stem + "_std.png")
        dest = outdir / name
        if dest.resolve() == src.resolve():
            raise ValueError("Refusing to overwrite the raw file")
        canvas.save(dest)
        audit_rows.append(
            {
                "source": str(src),
                "source_sha256": file_hash,
                "output": str(dest),
                "crop": [left, top, crop_w, crop_h],
                "display": display,
                "scale_bar": bar,
                "resampled": False,
            }
        )

    audit = {
        "operation": "center-crop shared canvas; optional shared display window; optional calibrated scale bar",
        "raw_files_modified": False,
        "rows": audit_rows,
    }
    (outdir / "image_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def average_hash(path: Path, size: int = 8) -> str:
    image = Image.open(path).convert("L").resize((size, size))
    pixels = list(image.getdata())
    avg = sum(pixels) / len(pixels)
    return "".join("1" if pixel > avg else "0" for pixel in pixels)


def duplicate_candidates(paths: list[Path], suspect_distance: int = 8) -> list[dict]:
    """Review aid only. A short distance is a candidate, not a finding of misconduct."""
    hashes = [(Path(path), average_hash(path)) for path in paths]
    reports = []
    for i, (left, left_hash) in enumerate(hashes):
        for right, right_hash in hashes[i + 1 :]:
            distance = sum(a != b for a, b in zip(left_hash, right_hash))
            if distance <= suspect_distance:
                reports.append(
                    {
                        "a": str(left),
                        "b": str(right),
                        "hash_distance": distance,
                        "status": "exact candidate" if distance == 0 else "transform candidate",
                        "judgment": "needs a person and the acquisition record",
                    }
                )
    return reports
