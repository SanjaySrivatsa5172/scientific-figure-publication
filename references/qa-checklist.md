# QA checklist and acceptance gate

Automated checks catch what geometry and metadata reveal; they cannot judge whether the figure tells the truth. Run both halves.

## Automated

```python
from figure_qa import audit_figure, report, check_legend_text
report(audit_figure(fig, target="ehj", column="single"))
report(check_legend_text(legend_text, "jacc", title=legend_title))
```
```bash
python figure_qa.py final_figures/*.pdf final_figures/*.tif --target ehj --column single
python figure_qa.py panels/*.svg --same-size              # same-slot canvases
python figure_qa.py final_figures/Fig1.png --cvd-preview qa/Fig1_cvd.png
python figure_qa.py --portability figure_sources/fig1.py
python figure_qa.py --render-doc manuscript.docx --out qa/pages
python image_panels.py duplicates panels/*.png --out qa/duplicates.json
python demo_gallery.py            # regression check after editing the toolkit
```
Live-figure checks: effective size after placement; height limit; type sizes against the preset, number of distinct sizes, font family and substitutes, missing glyphs; clipped and colliding text; legends and annotations over data; stroke widths; 3-D axes, pie charts, rainbow colormaps, truncated bar axes, bars on log axes, dual axes, figure titles; undefined error bars; numeric axes without labels; CIEDE2000 and grayscale separation of series colors; grid alignment; missing panel labels; notation (IC50, log2, x for ×, caret exponents, lowercase p, hyphen minus, +/-, "um"); transparency; rasterized layers; journal rules (bar graphs at JACC, dynamite plots at JACC: Advances and BTS, stacked bars and pies at JAMA, ratios on log scale, panel limits, PNAS zero-including axes, Kaplan-Meier rules at JVS, EJVES, JEVT with a report of whether the truncation rule was applied and which curves it shortened, black-and-white printing at The Lancet); Kaplan-Meier confidence intervals cut by the y-axis limit (`KM_CI_CLIPPED`). Inset axes (an embedded forest plot) and subfigure axes are audited like any other axes.
File checks: page or pixel size, embedded fonts and Type 3, image resolution inside PDFs, transparency, CMYK, raster DPI at target width (previews reported as `PREVIEW_DPI`, not failed), alpha channels, JPEG, TIFF compression, SVG physical size, live and fragmented text, SVG edge spaces, linked images.

Severity: FAIL blocks delivery. WARN needs a fix or a written reason. REVIEW is a human decision the script cannot make. INFO records context (type sizes used, fonts embedded, DPI).

## Manual (do every time)

1. Open the final PNG at 100% of print size and the CVD preview with the Read tool. Look for overlaps, crowding, ambiguous proximity (a label that could belong to the wrong line), clipped arrowheads, misleading scales, and anything the meaning depends on that disappears in grayscale or a CVD panel.
2. Five-second test: a reader can state the takeaway, the comparison, and the direction of benefit.
3. Caption test: the legend alone defines groups, n (experimental units), outcome and unit, uncertainty, test or model, and abbreviations.
4. Check every number in the artwork against the source table: estimates, CIs, P values, n, numbers at risk, event counts.
5. Check consistency across the figure set: same entity same color, same group order, same statistical syntax, same type hierarchy.
6. For an existing figure: compare old and new at the same size; keep the better one; record scientific changes separately from cosmetic ones.
7. Place the figure in its real container (manuscript page, slide, poster region) and render it.

## Acceptance gate (all must hold)

Science
- Data, groups, denominators, units, direction of effect, and experimental unit verified against the source.
- No invented or recomputed model estimates; synthetic data labeled.
- Continuous outcomes with small n show observations; bars start at zero; every error bar defined; n per group stated.
- Statistics written in the target's house style; exact P values; prespecified comparisons only on brackets.

Legibility and layout
- Text within the preset's range at final size, at most three sizes plus panel labels, one font family, required font installed and embedded, no missing glyphs.
- Zero unintended overlap or clipping; legends and annotations off the data.
- Panels aligned; same-slot panels share one canvas; panel labels in the journal's convention.

Color and accessibility
- Categorical colors separable under simulated protanopia, deuteranopia, tritanopia, and in grayscale, or redundantly encoded by marker, line style, or direct label.
- Perceptually uniform or properly centered diverging colormaps with labeled colorbars; no rainbow maps.
- Text contrast at least 4.5:1.

Files
- Width and height within the preset; vector master for charts and diagrams; raster DPI at the target width meets the content type; RGB unless the target says otherwise; no alpha in TIFF; fonts embedded (Type 42), no Type 3.
- Delivered script is portable: no skill paths, no machine-specific absolute paths, no tight bounding box.

Images
- Batch-locked display settings, calibrated scale bars, documented crops, no local edits, originals retained, duplicate screen run, no patient identifiers.

Provenance
- Preset and retrieval date recorded; journal instructions rechecked for a real submission; icon and illustration sources and licenses listed.

## Redesign reports

When auditing someone else's figure, lead with the highest-impact communication failure, attach each correction to a specific panel, element, or encoding, and separate facts (measured sizes, colors, metadata) from visual inference (a likely tool or method). A missing metadata field does not prove a figure was made by hand (Scientific-Figure-Design evidence levels).
