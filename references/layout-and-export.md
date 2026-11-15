# Layout and export

## Contents
1. Fixed canvas and slot classes
2. Multi-panel grids and panel labels
3. Legends, annotations, whitespace
4. File formats, resolution, color mode
5. Placing figures in LaTeX, Word, PowerPoint
6. Verifying the exported files

## 1. Fixed canvas and slot classes

A nominal 9 pt label stops being 9 pt once a figure is scaled to fit a slot. Draw every figure at its final physical size and place it at 100%.
- `pf.setup(target, column)` fixes width from the preset; height from `height_mm` or `aspect`, capped at the preset's maximum.
- `pf.subplots(spec, ...)` uses constrained layout inside the fixed canvas. Never `bbox_inches="tight"`: it crops to content and changes the canvas, so identically coded panels come out at different sizes (polish-sci-figures root-cause analysis). `figure_qa --portability` fails scripts that use it.
- Slot classes (polish-sci-figures): panels that will sit in the same grid share one physical width, height, and SVG viewBox. Check with `figure_qa.py panels/*.svg --same-size`. If a slot changes, regenerate for the new slot rather than resizing the file in Illustrator, Word, or PowerPoint.
- Starting proportions (Scientific-Figure-Design visual grammar): system overviews and worked examples about 2:1; quantitative comparisons 1.6 to 1.8:1; ablations and rooflines about 1.4:1; heatmaps compact. The column width, not the proportion, is the real constraint.

## 2. Multi-panel grids and panel labels

- Build the grid before plotting: aligned outer edges, equal gutters, shared axis scales where the reader compares across panels (`pp.small_multiples`). `audit_figure` warns when axes in a row do not share top and bottom edges.
- `pf.panel_labels(fig, axes)` places labels in the preset's convention at the top left of each panel's decorations, so they never collide with y-axis labels, and snaps labels in the same row and column to one line. Use `inside=True` for image panels without axes. It measures in display space, so it works for axes in different subfigures and for a forest plot's host axes.
- Mixed panels whose margins differ a lot (a survival curve with a risk table beside or above a forest table) belong in separate subfigures (`fig.subfigures`), each with its own constrained layout; panels in one gridspec row or column share margins. Recipe in `references/clinical-figures.md`, section 2.
- For reusable panels assembled later, add panel labels at assembly time, not inside each panel file (polish-sci-figures). Manuscript figures with two or more panels need labels; journals reference panels in legends and text (AHA, EHJ, EJVES specify uppercase top left).
- Panel limits: JAMA 4; AHA and EHJ 6; Vascular Medicine image articles 4 panels per image.
- Do not let `set_aspect("equal", adjustable="box")` silently shrink one panel; use `adjustable="datalim"` or a matching slot when geometry must be undistorted.
- Separate the canvas, the allocated slot, and the axes box: equal GridSpec cells do not guarantee equal axes.

## 3. Legends, annotations, whitespace

- Prefer direct labels (`pp.direct_labels`, `km_plot(legend="direct")`) to a legend box; IEEE and Heart instructions ask for direct line labels.
- If a legend is needed, keep it off the data: reserved margin, empty region, or a dedicated legend axis (`pp.legend_panel`). `audit_figure` warns when a legend or annotation covers plotted points.
- Statistical annotations go in reserved space, never on markers or intervals; forest-plot values live in their own columns.
- Comparison brackets stack at distinct levels above the data (`pp.sig_bracket`).
- Whitespace is a budget: keep what separates groups and frames labels; remove accidental empty regions.
- No figure titles inside manuscript artwork (Science Advances, AHA "no headings on the figure"); the title belongs in the legend. Short panel headings that name an endpoint are accepted by many clinical journals; conclusions are not.

## 4. File formats, resolution, color mode

- Vector master for charts and diagrams: PDF (or EPS where required), plus SVG for editing. Raster only for photographs and images, or when the journal demands TIFF.
- DPI is meaningful only with a physical size: required pixels = width (in) × DPI. Presets carry three values: line art (often 1000 to 1200), halftone or photographs (300 to 600), combination (500 to 900). Examples: Elsevier 1000/300/500; Cell 1000/300/500 (500 for black and white); PNAS 1000-1200/≥300/600-900; AHA 1200 line art, ≥600 everything else; EHJ photographs ≥350 (600 recommended), line art ≥600 (1200 recommended); JAMA images ≥350, line drawings ≥600; JVS ≥300 at 3 in wide.
- `pf.save` chooses DPI from the preset (combination DPI if the figure contains images, line-art DPI otherwise), flattens rasters onto white RGB without alpha, and writes LZW-compressed TIFF. It tags each PNG and TIFF with its content type and role: a PNG is rendered at the submission DPI only when the preset lists PNG among the journal's formats; otherwise it is a 600 dpi preview for checking and slides, tagged so the QA does not judge it as the submission file.
- Color mode: RGB unless the target says otherwise. AHA asks for RGB, not CMYK; Science Advances requires RGB; some publishers accept both. `save(..., cmyk_tiff=True)` performs a naive conversion without an ICC profile and says so; prefer letting the publisher convert.
- JPEG is lossy: photographs only, never line art or text.
- Transparency: fine in PDF and SVG; PostScript and EPS cannot hold it. Use opaque tints (`pf.tint`) or `pf.flatten_alpha(fig)` before EPS export.
- Rasterized layers inside vector output (large heatmaps, dense scatter) keep file size sane but are not editable; `heatmap(rasterize_over=...)` controls this and QA reports it.
- Formats some journals reject: PLOS accepts only TIFF or EPS; Taylor & Francis does not accept PDF figures; MDPI wants raster files; Nature main figures must be editable vector (no JPEG, TIFF, or PNG for main figures per its research figure guide).

## 5. Placing figures in LaTeX, Word, PowerPoint

- LaTeX: `\includegraphics{Fig1.pdf}` without a width argument places it at its native size; `width=\columnwidth` rescales it, so draw at the column width of the template (presets for NeurIPS, ICML, ICLR, CVPR, ACL, ACM carry them).
- Word and PowerPoint: insert at 100%; if the slot is wrong, regenerate. SVG text may substitute fonts on another machine; embed fonts or send PDF.
- Presentation mode: derive the canvas from the slide grid; conclusion-style slide title and per-panel takeaways go in editable slide text outside the figure (polish-sci-figures).
- Render the real container to check placement: `python figure_qa.py --render-doc manuscript.docx --out qa/pages` (LibreOffice preview, not native Word or PowerPoint rendering).

## 6. Verifying the exported files

```bash
python "$SKILL_DIR"/scripts/figure_qa.py final_figures/Fig1.pdf final_figures/Fig1.tif \
    --target circulation --column single
```
Checks: page or pixel size against the target width, maximum height, embedded fonts and Type 3 detection (pypdf or `pdffonts`), embedded image resolution (`pdfimages -list`), transparency, CMYK objects, raster DPI at the target width, alpha channels, JPEG use, TIFF compression, SVG physical size, live text, fragmented text, leading or trailing spaces that SVG viewers drop (`SVG_EDGE_SPACE`; `pf.rich_text` writes no-break spaces), linked images, and color separation. Each finding names the file.
- Raster content type: `--kind auto` (default) reads the tag `pf.save` writes; for rasters from elsewhere pass `--kind line` (charts, diagrams), `--kind combination` (charts with images), or `--kind halftone` (photographs), because the required DPI differs by a factor of 2 to 4.
- `--cvd-preview out.png` rasterizes the first listed file it can (PNG or TIFF, then PDF with poppler, SVG with cairosvg, EPS with Ghostscript) and reports `CVD_PREVIEW_SKIPPED` instead of failing when none can be read.
