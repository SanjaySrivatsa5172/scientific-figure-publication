# Images and integrity

Microscopy, histology, fluorescence, electron microscopy, blots, angiography, echocardiography, CT, MR, ultrasound, and clinical photographs. The goal is a montage a skeptical reviewer can trace back to raw acquisitions.

Evidence: Rossner and Yamada (J Cell Biol 2004) set out why selective enhancement and misleading juxtaposition compromise images. Bik, Casadevall and Fang (mBio 2016) found problematic duplicated images in 3.8% of 20,621 papers, at least half suggesting deliberate manipulation. At Molecular and Cellular Biology, pre-publication screening flagged 12 of 83 accepted manuscripts (14.5%) and took about 30 minutes per problem paper against about 6 hours of staff time after publication (Bik et al 2018), which is the case for screening before submission rather than after. Cromey (2010) gives ethical rules for digital images; Schmied et al (Nat Methods 2024) give community checklists for publishing images and image analyses.

## Three layers (polish-sci-figures)

1. Raw acquisition: immutable original files and metadata (keep DICOM, proprietary microscope files, OME-TIFF).
2. Quantitative derivative: segmentation, measurements, masks, calibrated intensities from a declared pipeline.
3. Display derivative: crop, global window, LUT, scale bar, layout for communication.
Never measure from the display derivative, and never present display mapping as quantitative preprocessing.

## Rules journals share

From the instructions in `assets/journal-specs/` (JACC, AHA, JAMA, NEJM, Nature Portfolio, Cell, Science, Elsevier, Wiley, Sage):
- Adjust brightness, contrast, or color only linearly, to the whole image, and equally to controls; disclose nonlinear (gamma) changes in the legend.
- No cloning, healing, selective blurring, moving, removing, or introducing features; generative AI may not create or alter scientific or clinical images (NEJM, JAMA, Nature, Science Advances, Cell).
- Mark spliced or regrouped lanes with dividing lines and say so; keep uncropped blots for the supplement (Nature, AHA, BMC, Vascular Medicine).
- Scale bars rather than magnification factors (Nature Medicine).
- Keep originals; NEJM requests clean, unannotated versions at revision.

## Standardize a batch

```bash
python "$SKILL_DIR"/scripts/image_panels.py standardize manifest.csv --outdir panels --scale-bar-um 20 --fit-box-mm 55 45
```
Manifest columns: `file, output_name, um_per_pixel, batch, display_min, display_max, gamma, lut, scale_bar_um, label, mask`.
- One display policy per comparison batch; the tool refuses a batch whose rows disagree on calibration, window, gamma, or LUT.
- 16-bit data need explicit `display_min`/`display_max` in native units; there is no silent 16-to-8-bit conversion.
- Equal size by common center crop, no resampling; crop boxes go into `audit.json` with source SHA-256 hashes, effective DPI, and physical size.
- Scale bars only from recorded calibration (`um_per_pixel` from metadata or the acquisition record); the bar and its centered label are editable vector elements in the SVG, the image stays faithful raster.
- `--fit-box-mm W H` gives the largest proportional placement inside a slot while keeping at least 300 dpi (raise `--min-dpi` for journals that require more, for example AHA 600, EHJ 350 minimum and 600 recommended, Nature checklist 450).
- `mask` blacks out pixel boxes ("x0 y0 x1 y1; ...") for burned-in identifiers and records them.

## Clinical captures

- Remove names, MRNs, dates of birth, study dates, accession numbers, and institution names burned into angiography, echo, CT, MR, and ultrasound frames; Vascular Medicine explicitly asks to remove time and date stamps.
- Prefer exporting frames from the DICOM viewer without overlays; mask only what cannot be avoided, and crop rather than blur.
- Black bars over eyes are not accepted as anonymization by JAMA, The Lancet, Heart, or The BMJ; identifiable photographs need the journal's consent form.
- Keep the frame number and run from which each still was taken, and the window/level used, in the audit.
- Video-capable journals (JACC: Case Reports expects videos for fluoroscopy) take moving images as supplementary files; stills in the figure must match them.

## Duplicate screening before submission

```bash
python "$SKILL_DIR"/scripts/image_panels.py duplicates panels/*.png figure_with_images.svg --out qa/duplicates.json
```
Exact pixel duplicates (SHA-256 of decoded pixels) and near duplicates by perceptual hashes across the eight rotations and flips, including resized copies; partial overlaps by ORB features and homography when OpenCV is installed. Compare one source per acquisition, not a raw file and its own derivative. Findings are review leads: shared controls and related channels legitimately match; heavy crops and low-texture blot strips are expected misses. A clean report does not certify uniqueness.

## Fluorescence and electron microscopy

- Avoid saturating highlights; keep channel colors stable across the series and state LUTs in the legend; recolor red-green pairs to green-magenta (Nature Communications, Elsevier).
- For composites, keep the single-channel images and disclose the channel mapping.
- Electron micrographs: calibration from the acquisition record; never move or reconstruct structures for composition.
