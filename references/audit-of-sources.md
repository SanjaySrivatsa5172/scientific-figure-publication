# Audit of the source repositories

What this skill took from each repository, what it changed, what it dropped, and the evidence for each decision. Repositories as cloned on 2026-11-14: qhy991/Scientific-Figure-Design (commit d88f87d, MIT), zhoy0409-debug/polish-sci-figures (commit 8750662, MIT), ChenLiu-1996/figures4papers (commit 0ddfbd3, CC BY-NC 4.0).

## Scientific-Figure-Design (SFD)

Kept (scripts bundled with their tests; all 17 upstream tests pass in this skill):
- Figure contract: claim, five-second takeaway, audience, width, evidence, visual anchor, encoding map, provenance, deliverables (merged into `assets/figure-contract.yaml`).
- Archetype selection, grayscale skeleton first, one claim per figure, the five-second and caption tests.
- Academic aesthetics limits (`assets/academic-style.yaml`): at least 7 pt, at most three type sizes, one sans family, strokes 0.8 to 1.6 pt, at most five semantic hues, no gradients, shadows, glass, 3-D, emoji, or dark backgrounds, at least 4.5:1 text contrast.
- Paper palette contract with frozen ID and SHA-256 and a cross-figure drift audit.
- draw.io builder, strict validator, exporter, palette validator; icon composer, search, recolor, validator; the 581-icon library with license manifest.
- arXiv corpus collection and visual statistics, with the evidence-level discipline.
- The AI-agent self-evolution figure guide (`references/ai-agent-evolution-figures.md`, unchanged).

Changed:
- Default semantic palette. "accent" #2563EB and "secondary" #7C3AED (the defaults for "ours" and "strong baseline") differ by CIEDE2000 0.5 under simulated deuteranopia, so the two most important series were indistinguishable to deuteranopes. Replaced with #0072B2 and #882255 (and warning #8C510A, danger #BB5566), chosen by exhaustive search for the best minimum ΔE00 across protanopia, deuteranopia, and tritanopia with every color at 4.5:1 contrast or better (minimum 8.7, limited by the green-versus-red status pair, which the style already requires to carry labels or shapes). Updated in `academic-style.yaml`, `paper-palette.yaml` (now `academic-paper-default-v2-cvd`), the draw.io builder fallback, and the composer.
- Fixed widths of 85 and 178 mm replaced by verified per-journal presets (42 journals, publishers, and venues). SFD's ranges were reasonable generic values but miss Nature (89/183 mm), Elsevier (90/190 mm), Cell (85/174 mm), PNAS (87/178 mm), and the clinical journals entirely.
- Its matplotlib recipe used `savefig.bbox: tight`, which changes the physical canvas; replaced by fixed canvases with constrained layout.
- Composer PDF and PNG export needed `rsvg-convert`; added a `cairosvg` fallback, with PNGs rasterized from the vector PDF by poppler because cairo's direct PNG text rendering garbled bold labels in testing.
- Added 38 clinical Lucide icons with clinical search hints; the library was 619 icons at v1.0.0.
- v1.0.1: removed the 39 Lobe Icons vendor logos (trademark exposure not covered by the MIT license on the SVG code); the library is now 580 icons.
- The nested `paper-icons/SKILL.md` became `GUIDE.md`: claude.ai rejects skills containing more than one SKILL.md.
- Dropped `style-tokens.json` (a manual copy of `academic-style.yaml` that no script read).

## polish-sci-figures (PSF)

Kept (as rules and re-implemented checks; the Windows Figure Studio editor, web app, and 218-template gallery are a separate product and are not bundled):
- Delivery modes (manuscript, presentation, web display) that must not be mixed.
- Fixed canvas and slot classes; no tight bounding box; insert at 100%; same-slot canvases identical (now `figure_qa --same-size`).
- One font family enforced for every text object including mathtext; no silent fallback (now `resolve_font` and the `FONT_NOT_REQUIRED` and `MISSING_GLYPH` checks).
- Scientific typography: italic only for statistical symbols, true subscripts and superscripts, minus, ±, ×, spacing, units, species and gene conventions (now `pf.notation`, `rich_text`, and the notation checks).
- Zero-overlap gate, reserved annotation zones, forest-plot values in columns, stacked comparison brackets, grid alignment of axes (re-implemented in `figure_qa.audit_figure` with text-over-data detection added).
- Experimental-unit-first statistics; estimation graphics instead of bars; no test switching on normality tests; global tests do not license pairwise claims; supplied model results are displayed, not refit.
- Image standardization contract (manifest, batch-locked display, calibration-only scale bars, no resampling, audits with hashes) and duplicate screening as review leads (re-implemented in `image_panels.py` without the OpenCV requirement; OpenCV is optional).
- Source portability check and document page rendering (re-implemented in `figure_qa.py`).
- Compare candidate with original at the same size; record scientific updates separately.

Changed:
- PSF omits panel letters by default. Clinical and general journals reference panels by letter, and AHA, EHJ, and EJVES specify uppercase letters at the top left, so manuscript figures with two or more panels get labels in the journal's convention; reusable panels still get them only at assembly.
- PSF forbids panel titles in manuscript artwork. Kept as a default for conclusions and long titles, relaxed for short endpoint headings that many clinical journals print; AHA's "no headings on the figure" is encoded in its preset rules.
- PSF's baseline style (9.5 pt base, 12 pt titles, 15 pt figure titles) exceeds Nature's 7 pt maximum and is replaced by per-preset final-size type.
- PSF's default gallery palette (`zhoy_muted`) has a minimum ΔE00 of 2.5 under simulated deuteranopia; not used.
- PSF shows P values only after the user confirms a confirmatory analysis. Kept as the rule for brackets and asterisks; clinical figures (log-rank, interaction P) print supplied P values in the journal's house style, which PSF did not model.

## figures4papers (F4P)

License: CC BY-NC 4.0. Its code is not copied; its ideas are re-implemented and credited, so this skill's code stays MIT.

Kept as ideas: matplotlib helper API (style setup, grouped bars, trends with bands, heatmaps, scatter, illustration helpers, finalize/export), semantic color roles (strong hue for the proposed method, neutrals for baselines), dedicated legend panel, black edges and hatching for grayscale-safe bars, value labels, uncertainty bands, minimal spines and frameless legends, 300 to 600 dpi export, radar and concept illustrations for ML papers.

Changed, with reasons:
- Oversized canvases with 16 to 36 pt type print at about 4 pt at column width; build at final size.
- "Tighten the y axis to the data range" is applied to points and lines only; truncated bars exaggerate differences (Cleveland and McGill 1984; journals such as JAMA require bar axes from zero).
- Radar charts with per-spoke ranges replaced by one shared scale.
- Alpha-graded ablation bars replaced by opaque tints (print and EPS fidelity).
- Hidden category tick labels with legend look-up replaced by direct labels.
- Palette replaced by checked colors (its blue-green-red family: minimum ΔE00 6.8 under protanopia, ΔL* 0.3).
- `font.family = "helvetica"` silently falls back to DejaVu Sans on systems without Helvetica; fonts are now resolved and reported.

## First published version of this repository

The manuscript-draft-bot handoff (request JSON in, `figure_packet.json` out, PASS only after the automated and manual checks) came from the first version published in this repository, a figure lane for a manuscript drafting bot. It is kept in `references/manuscript-bot.md` with `scripts/figure_packet.py` so that bot keeps working; that version's matplotlib package and 85/178 mm defaults were superseded by the verified presets and the toolkit here.

## Additions not present in any source

- Verified presets for 42 journals, publishers, and venues with quotes, URLs, retrieval date, and recorded conflicts (`assets/journal-specs/`).
- Journal statistics house styles (AMA, NEJM, Annals, Lancet, EHJ, EJVES, JEVT, Vascular Medicine, AHA) and a legend checker with journal word limits.
- Clinical figure builders validated against reference implementations: Kaplan-Meier with log(-log) Greenwood CIs and log-rank (lifelines, to machine precision), Aalen-Johansen cumulative incidence (lifelines on untied data; exact KM identity on tied data), ROC, AUC, and average precision (scikit-learn), DeLong SE (agrees with a 3,000-resample bootstrap to within 0.0001); forest plots, Bland-Altman with CI bands, calibration with recalibration slope, CONSORT 2025-style and PRISMA 2020 flow diagrams with count checks.
- Statistical edge cases hardened after an audit against lifelines 0.30, statsmodels 0.15, scikit-learn, and scipy (300 simulated datasets per function, tied times included): missing or non-finite survival input raises instead of silently leaving the risk set; the DeLong interval defaults to Wald (the R pROC form) with the logit interval as `ci="logit"`; the Greenwood SE is NaN once S(t) = 0 and the SE truncation rule stops before it; undefined log-rank tests raise a clear `ValueError`; the no-scipy normal quantile is exact for any level.
- Color-vision simulation (Machado 2009; identical to colorspacious) and CIEDE2000 (matches the Sharma et al test pairs and colour-science), used by `check_colors` and the CVD preview.
- File-level QA for PDF fonts (Type 3 detection), embedded image resolution, raster DPI at target width, alpha, and color mode.
- Journal Kaplan-Meier rules applied, not only checked: per-arm follow-up ends, Greenwood-SE and at-risk truncation from the preset (JVS, EJVES, JEVT), CI bands or the JVS vertical-bar alternative, and a QA report of which rule ran and which curves it shortened; added after a test run on a JVS task.
- Multi-panel survival and forest figures (forest plot as a subfigure or gridspec panel), and a settle pass that redoes automatic placements (statistics annotations, ROC legends, panel labels) once the final layout exists, so late panels cannot push them onto data.
