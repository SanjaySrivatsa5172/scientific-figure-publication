#!/usr/bin/env python3
"""image_panels: comparable, documented image panels (microscopy, histology,
angiography, echocardiography, CT/MR stills, blots) and duplicate screening.

Subcommands
  standardize MANIFEST.csv --outdir DIR [--scale-bar-um 20] [--fit-box-mm W H]
      Locked batch display (window/gamma/LUT), common centre crop, optional
      masking of burned-in identifiers, calibrated scale bars on an editable SVG
      layer, montage, and an audit JSON with SHA-256 of every source.
  duplicates IMG [IMG ...] [--out report.json]
      Screens for reused images: exact pixel duplicates and perceptual-hash
      near duplicates under the 8 rotations/flips, with resized variants.
      Optional ORB feature matching (OpenCV, if installed) for partial overlaps.

Integrity rules this tool enforces (Rossner & Yamada 2004; Cromey 2010;
Schmied et al. 2024 checklists; polish-sci-figures standardize-sci-images):
- sources are never modified; outputs go to a new folder with hashes recorded;
- one display policy per comparison batch, declared in the manifest;
- no local edits (no cloning, selective blur, local contrast);
- no resampling by default (equal size by common crop);
- scale bars only from authoritative calibration (um_per_pixel); never guessed;
- 16-bit data need explicit display bounds in native units.
Similarity findings are leads for review, not evidence of misconduct.

Manifest columns: file, output_name, um_per_pixel (for scale bars), batch,
display_min, display_max, gamma, lut (gray|green|magenta|cyan|red|blue),
scale_bar_um, label, mask ("x0 y0 x1 y1; x0 y0 x1 y1" pixel boxes blacked out,
for burned-in patient identifiers in clinical screenshots; quote the field if
you use commas).
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

LUTS = {"gray": (1, 1, 1), "green": (0, 1, 0), "magenta": (1, 0, 1), "cyan": (0, 1, 1), "red": (1, 0, 0), "blue": (0, 0, 1)}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _float(v, default=None):
    try:
        return float(v) if v not in (None, "") else default
    except ValueError:
        return default


def read_manifest(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit("manifest is empty")
    for r in rows:
        if not r.get("file") or not r.get("output_name"):
            raise SystemExit("each row needs file and output_name")
        src = Path(r["file"])
        r["_src"] = src if src.is_absolute() else (path.parent / src)
        if not r["_src"].exists():
            raise SystemExit(f"missing source: {r['_src']}")
    # batch consistency: same display policy and calibration inside a batch
    batches: dict[str, list[dict]] = {}
    for r in rows:
        batches.setdefault(r.get("batch") or "default", []).append(r)
    for b, rs in batches.items():
        for key in ("um_per_pixel", "display_min", "display_max", "gamma", "lut"):
            vals = {(r.get(key) or "").strip() for r in rs}
            if len(vals) > 1:
                raise SystemExit(f"batch {b!r}: {key} differs across rows {sorted(vals)}; "
                                 "a comparison batch must share calibration and display settings")
    return rows


def load_native(path: Path) -> np.ndarray:
    im = Image.open(path)
    arr = np.array(im)
    return arr


def display_map(arr: np.ndarray, dmin, dmax, gamma: float, lut: str) -> np.ndarray:
    """Global, whole-image display mapping to 8-bit RGB (never local)."""
    if arr.ndim == 3 and arr.shape[2] in (3, 4):
        if arr.dtype != np.uint8 and (dmin is None or dmax is None):
            raise SystemExit("multichannel high-bit-depth image needs display_min/display_max")
        rgb = arr[..., :3].astype(float)
        lo = 0.0 if dmin is None else dmin
        hi = 255.0 if dmax is None else dmax
        out = np.clip((rgb - lo) / (hi - lo), 0, 1) ** (1 / gamma)
        return (out * 255 + 0.5).astype(np.uint8)
    if arr.dtype != np.uint8 and (dmin is None or dmax is None):
        raise SystemExit(f"{arr.dtype} data need explicit display_min/display_max in native units "
                         "(no silent 16-to-8-bit conversion)")
    lo = 0.0 if dmin is None else dmin
    hi = 255.0 if dmax is None else dmax
    g = np.clip((arr.astype(float) - lo) / (hi - lo), 0, 1) ** (1 / gamma)
    tint = np.array(LUTS.get(lut or "gray", (1, 1, 1)), float)
    return (g[..., None] * tint * 255 + 0.5).astype(np.uint8)


def apply_masks(img: np.ndarray, spec: str | None) -> tuple[np.ndarray, list]:
    boxes = []
    if spec:
        img = img.copy()
        for part in spec.split(";"):
            if part.strip():
                vals = [v for v in re.split(r"[\s,]+", part.strip()) if v]
                if len(vals) != 4:
                    raise SystemExit(f"mask box needs 4 numbers 'x0 y0 x1 y1', got {part!r}")
                x0, y0, x1, y1 = (int(float(v)) for v in vals)
                img[y0:y1, x0:x1] = 0
                boxes.append([x0, y0, x1, y1])
    return img, boxes


def center_crop(img: np.ndarray, w: int, h: int):
    H, W = img.shape[:2]
    x0, y0 = (W - w) // 2, (H - h) // 2
    return img[y0:y0 + h, x0:x0 + w], [x0, y0, x0 + w, y0 + h]


def nice_bar_um(field_um: float) -> float:
    target = field_um * 0.2
    for v in [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000]:
        if v >= target * 0.6:
            return float(v)
    return float(10 ** round(math.log10(target)))


def _font(size_px: int):
    for name in ("Arial.ttf", "arial.ttf", "LiberationSans-Regular.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size_px), name
        except OSError:
            continue
    return ImageFont.load_default(), "PIL default"


def write_svg(display: np.ndarray, out: Path, width_mm: float, bar: dict | None, label: str | None, font_family="Arial"):
    h_px, w_px = display.shape[:2]
    height_mm = width_mm * h_px / w_px
    buf = io.BytesIO()
    Image.fromarray(display).save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
             f'width="{width_mm:.3f}mm" height="{height_mm:.3f}mm" viewBox="0 0 {w_px} {h_px}">',
             f'<image width="{w_px}" height="{h_px}" href="data:image/png;base64,{b64}"/>']
    if bar:
        x1 = w_px - bar["margin_px"]
        x0 = x1 - bar["len_px"]
        y = h_px - bar["margin_px"]
        col = bar["color"]
        parts.append(f'<rect x="{x0:.1f}" y="{y - bar["thick_px"]:.1f}" width="{bar["len_px"]:.1f}" height="{bar["thick_px"]:.1f}" fill="{col}"/>')
        parts.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{y - bar["thick_px"] - bar["gap_px"]:.1f}" text-anchor="middle" '
                     f'font-family="{font_family}" font-size="{bar["font_px"]:.1f}" fill="{col}">{bar["text"]}</text>')
    if label:
        parts.append(f'<text x="{w_px * 0.03:.1f}" y="{h_px * 0.08:.1f}" font-family="{font_family}" '
                     f'font-size="{max(10, w_px * 0.045):.1f}" fill="#FFFFFF">{label}</text>')
    parts.append("</svg>")
    out.write_text("\n".join(parts), encoding="utf-8")
    return height_mm


def standardize(manifest: Path, outdir: Path, scale_bar_um: float | None, fit_box_mm=None, panel_width_mm=None,
                min_dpi: float = 300.0, columns: int = 3):
    rows = read_manifest(manifest)
    outdir.mkdir(parents=True, exist_ok=True)
    loaded = []
    for r in rows:
        arr = load_native(r["_src"])
        disp = display_map(arr, _float(r.get("display_min")), _float(r.get("display_max")),
                           _float(r.get("gamma"), 1.0), (r.get("lut") or "gray").strip())
        disp, masks = apply_masks(disp, r.get("mask"))
        loaded.append((r, arr, disp, masks))
    w = min(d.shape[1] for _, _, d, _ in loaded)
    h = min(d.shape[0] for _, _, d, _ in loaded)
    audit = {"manifest": str(manifest), "tool": "image_panels.py standardize", "common_canvas_px": [w, h],
             "policy": "common centre crop, no resampling, global display mapping only", "images": []}
    previews = []
    for r, arr, disp, masks in loaded:
        crop, box = center_crop(disp, w, h)
        name = r["output_name"]
        Image.fromarray(crop).save(outdir / f"{name}_display.png")
        # physical width: largest that keeps >= min_dpi unless a slot is given
        max_w_mm = w / min_dpi * 25.4
        width_mm = panel_width_mm or max_w_mm
        if fit_box_mm:
            bw, bh = fit_box_mm
            width_mm = min(bw, bh * w / h)
        eff_dpi = w / (width_mm / 25.4)
        if eff_dpi < min_dpi - 1e-6:
            raise SystemExit(f"{name}: {width_mm:.1f} mm would be {eff_dpi:.0f} dpi (< {min_dpi}); "
                             "use a smaller slot or higher-resolution source")
        upp = _float(r.get("um_per_pixel"))
        bar = None
        want = _float(r.get("scale_bar_um"), scale_bar_um)
        if want is not None or scale_bar_um is not None:
            if upp is None:
                raise SystemExit(f"{name}: scale bar requested but um_per_pixel is missing; "
                                 "calibration must come from the acquisition record")
            field_um = w * upp
            length_um = want or nice_bar_um(field_um)
            len_px = length_um / upp
            region = crop[int(h * 0.82):, int(w * 0.6):]
            bright = float(region.mean()) if region.size else 0
            bar = {"len_px": len_px, "thick_px": max(2.0, h * 0.012), "margin_px": w * 0.04, "gap_px": h * 0.012,
                   "font_px": max(10.0, h * 0.05), "color": "#000000" if bright > 128 else "#FFFFFF",
                   "text": f"{length_um:g} µm", "um": length_um}
        label = (r.get("label") or "").strip() or None
        hmm = write_svg(crop, outdir / f"{name}.svg", width_mm, bar, label)
        prev = Image.fromarray(crop).convert("RGB")
        if bar:
            d = ImageDraw.Draw(prev)
            x1 = w - bar["margin_px"]
            y = h - bar["margin_px"]
            d.rectangle([x1 - bar["len_px"], y - bar["thick_px"], x1, y], fill=bar["color"])
            fnt, _ = _font(int(bar["font_px"]))
            d.text((x1 - bar["len_px"] / 2, y - bar["thick_px"] - bar["gap_px"]), bar["text"], fill=bar["color"],
                   font=fnt, anchor="ms")
        prev.save(outdir / f"{name}_preview.png")
        previews.append(prev)
        audit["images"].append({
            "source": str(r["_src"]), "sha256": sha256(r["_src"]), "native_dtype": str(arr.dtype),
            "native_shape": list(arr.shape), "batch": r.get("batch") or "default", "crop_box_px": box,
            "display": {"min": _float(r.get("display_min")), "max": _float(r.get("display_max")),
                        "gamma": _float(r.get("gamma"), 1.0), "lut": (r.get("lut") or "gray").strip()},
            "masked_boxes_px": masks, "um_per_pixel": upp,
            "scale_bar": None if not bar else {"length_um": bar["um"], "length_px": round(bar["len_px"], 2)},
            "panel_mm": [round(width_mm, 2), round(hmm, 2)], "effective_dpi": round(eff_dpi, 1),
            "outputs": [f"{name}_display.png", f"{name}_preview.png", f"{name}.svg"]})
    # montage of previews (review only)
    cols = min(columns, len(previews))
    rows_n = math.ceil(len(previews) / cols)
    gut = max(4, w // 60)
    sheet = Image.new("RGB", (cols * w + (cols - 1) * gut, rows_n * h + (rows_n - 1) * gut), "white")
    for i, p in enumerate(previews):
        sheet.paste(p, ((i % cols) * (w + gut), (i // cols) * (h + gut)))
    sheet.save(outdir / "montage.png")
    (outdir / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"standardized {len(previews)} image(s) to {w}x{h} px; audit: {outdir / 'audit.json'}")
    return audit


# ---------------------------------------------------------------------------
# duplicate screening
# ---------------------------------------------------------------------------
def _gray(img: Image.Image, size: int) -> np.ndarray:
    return np.asarray(img.convert("L").resize((size, size), Image.LANCZOS), float)


def dhash(img: Image.Image, n: int = 16) -> np.ndarray:
    a = np.asarray(img.convert("L").resize((n + 1, n), Image.LANCZOS), float)
    return (a[:, 1:] > a[:, :-1]).ravel()


def phash(img: Image.Image, n: int = 16) -> np.ndarray:
    a = _gray(img, n * 4)
    N = a.shape[0]
    k = np.arange(N)
    C = np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * N))
    d = C @ a @ C.T
    low = d[:n, :n].ravel()[1:]
    return low > np.median(low)


def _variants(img: Image.Image):
    T = Image.Transpose
    yield "identity", img
    yield "rot90", img.transpose(T.ROTATE_90)
    yield "rot180", img.transpose(T.ROTATE_180)
    yield "rot270", img.transpose(T.ROTATE_270)
    yield "flip_lr", img.transpose(T.FLIP_LEFT_RIGHT)
    yield "flip_tb", img.transpose(T.FLIP_TOP_BOTTOM)
    yield "transpose", img.transpose(T.TRANSPOSE)
    yield "transverse", img.transpose(T.TRANSVERSE)


def _load_images(paths):
    out = []
    for p in map(Path, paths):
        if p.suffix.lower() == ".svg":
            import re
            raw = p.read_text(encoding="utf-8", errors="replace")
            for i, m in enumerate(re.finditer(r'data:image/[a-z]+;base64,([A-Za-z0-9+/=]+)', raw)):
                out.append((f"{p.name}#img{i + 1}", Image.open(io.BytesIO(base64.b64decode(m.group(1)))).convert("RGB")))
        else:
            out.append((p.name, Image.open(p).convert("RGB")))
    return out


def screen_duplicates(paths, *, threshold: int = 22, use_orb: bool = True) -> dict:
    """Exact and near-duplicate screening across 2+ images (incl. SVG-embedded rasters).

    threshold: max Hamming distance (of 255 pHash + 256 dHash bits, summed)
    for a 'suspected' pair. Heavy crops and low-texture strips (blots) are
    expected misses; a clean report does not certify uniqueness.
    """
    imgs = _load_images(paths)
    if len(imgs) < 2:
        raise SystemExit("need at least two images")
    sig = []
    for name, im in imgs:
        exact = hashlib.sha256(np.asarray(im).tobytes() + str(im.size).encode()).hexdigest()
        sig.append((name, im, exact, {v: (phash(t), dhash(t)) for v, t in _variants(im)}))
    findings = []
    for i in range(len(sig)):
        for j in range(i + 1, len(sig)):
            ni, imi, ei, hi = sig[i]
            nj, imj, ej, hj = sig[j]
            if ei == ej:
                findings.append({"a": ni, "b": nj, "kind": "exact pixel duplicate", "distance": 0})
                continue
            base_p, base_d = hi["identity"]
            best = min(((int((base_p != pv).sum() + (base_d != dv).sum()), v) for v, (pv, dv) in hj.items()))
            if best[0] <= threshold:
                findings.append({"a": ni, "b": nj, "kind": f"near duplicate ({best[1]})", "distance": best[0]})
            elif use_orb:
                orb = _orb_overlap(imi, imj)
                if orb and orb["inliers"] >= 25:
                    findings.append({"a": ni, "b": nj, "kind": "partial overlap (ORB + homography)", **orb})
    return {"images": [s[0] for s in sig], "pairs_compared": len(sig) * (len(sig) - 1) // 2, "findings": findings,
            "method": "SHA-256 of decoded pixels; pHash+dHash over 8 dihedral variants; ORB/RANSAC when OpenCV is installed",
            "limits": "crops below ~50% overlap, low-texture strips, and heavy re-staining can be missed; "
                      "matches are review leads, not misconduct findings"}


def _orb_overlap(a: Image.Image, b: Image.Image):
    try:
        import cv2
    except ImportError:
        return None
    ga = cv2.cvtColor(np.asarray(a), cv2.COLOR_RGB2GRAY)
    gb = cv2.cvtColor(np.asarray(b), cv2.COLOR_RGB2GRAY)
    orb = cv2.ORB_create(2000)
    ka, da = orb.detectAndCompute(ga, None)
    kb, db = orb.detectAndCompute(gb, None)
    if da is None or db is None or len(ka) < 10 or len(kb) < 10:
        return None
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(da, db)
    if len(m) < 10:
        return None
    src = np.float32([ka[x.queryIdx].pt for x in m]).reshape(-1, 1, 2)
    dst = np.float32([kb[x.trainIdx].pt for x in m]).reshape(-1, 1, 2)
    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
    if H is None:
        return None
    return {"inliers": int(mask.sum()), "matches": len(m)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("standardize")
    s.add_argument("manifest", type=Path)
    s.add_argument("--outdir", type=Path, required=True)
    s.add_argument("--scale-bar-um", type=float)
    s.add_argument("--fit-box-mm", type=float, nargs=2)
    s.add_argument("--panel-width-mm", type=float)
    s.add_argument("--min-dpi", type=float, default=300.0)
    d = sub.add_parser("duplicates")
    d.add_argument("images", nargs="+")
    d.add_argument("--out", type=Path)
    d.add_argument("--threshold", type=int, default=22)
    a = ap.parse_args(argv)
    if a.cmd == "standardize":
        standardize(a.manifest, a.outdir, a.scale_bar_um, a.fit_box_mm, a.panel_width_mm, a.min_dpi)
    else:
        rep = screen_duplicates(a.images, threshold=a.threshold)
        txt = json.dumps(rep, indent=2)
        if a.out:
            a.out.write_text(txt, encoding="utf-8")
        print(txt)
        return 1 if rep["findings"] else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
