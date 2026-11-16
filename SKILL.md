---
name: scientific-figure-publication
description: "Publication-ready scientific figures at final journal size: charts, Kaplan-Meier and forest plots, CONSORT, diagrams, image panels, 42 journal presets, QA. Use for any figure, graph, or legend."
license: MIT (bundled third-party icons keep their own licenses; see THIRD_PARTY_NOTICES.md)
---

# Scientific figure publication

A finished figure carries one defensible claim, reads at the size it will be printed, shows the data honestly, and can be rebuilt from source. Every rule below serves one of those four properties; when a style preference conflicts with them, the four properties win.

`SKILL_DIR` below means the folder containing this file.

## Non-negotiable rules

These protect the science, so they hold even when the user asks for something prettier.

1. Never invent or alter data, statistics, error bars, P values, confidence intervals, sample sizes, or labels. A missing value gets a visible placeholder and a question, never a guess.
2. Do not recompute model-based estimates (Cox hazard ratios, adjusted odds ratios, interaction P values) from display data. Plot what the user's analysis produced and say where it came from. The toolkit computes only transparent nonparametric quantities (Kaplan-Meier, log-rank, Aalen-Johansen, empirical ROC with DeLong CI, Bland-Altman limits, binned calibration).
3. Identify the experimental unit (patient, limb, lesion, animal, culture) before any statistic. Technical replicates are not independent observations.
4. Show the observations for continuous outcomes when groups are small. A bar with an error bar ("dynamite plot") hides the distribution; bars are for counts, proportions, and totals, and their axis starts at zero.
5. Name every error bar (SD, SEM, 95% CI, IQR) and every n in the legend.
6. Image integrity: whole-image, batch-locked adjustments only; no cloning, local edits, or selective enhancement; scale bars only from recorded calibration; originals kept.
7. Patient privacy: remove burned-in names, MRNs, dates, and accession numbers from angiography, echocardiography, CT, and MR screenshots; identifiable photographs need documented consent.
8. Label synthetic or illustrative data as synthetic, in the artwork (`pf.synthetic_tag(fig)`) and in the legend.
9. When the supplied data contradict the requested claim, title, annotation, or P value (curves that do not separate, a P value the data cannot produce), draw what the data show and raise the contradiction; never bend the figure toward the claim.
10. When inputs conflict (a registry total against subgroup counts, a table against a text value), do not pick one silently: mark the affected values `[CONFIRM]`, print `DATA CHECK FAILED` with both numbers in the run output, and ask. In a run nobody can answer, deliver the figure watermarked or labeled not for submission and list the open items.
11. Verification computations (re-deriving a total, a log-rank test beside a supplied P) are allowed and encouraged, but report them as checks; they never replace the user's numbers in the artwork.
12. Journal presets were transcribed from official instructions retrieved 2026-11-14 (quotes and URLs in `assets/journal-specs/`). For a real submission, recheck the live instructions and record the URL and date with the files.

## Route the request

Read only the reference that matches the job:

- New chart from data, or choosing a chart type: `references/chart-selection.md`.
- Clinical or epidemiological figure (survival, forest, flow diagram, agreement, diagnostic accuracy, prediction, central illustration, visual abstract), including a survival curve and forest plot in one figure: `references/clinical-figures.md`.
- Journal sizes, fonts, DPI, formats, panel-label style, chart rules for a named journal: `references/journal-specs.md`.
- Fonts, sizes, scientific notation, P-value and CI formatting per journal: `references/typography-and-notation.md`.
- Color, colormaps, color-vision deficiency, one palette across a paper: `references/color-and-accessibility.md`.
- Multi-panel layout, fixed canvases, file formats, DPI, font embedding, placing figures in Word, PowerPoint, or LaTeX: `references/layout-and-export.md`.
- Schematics, method or system overviews, study-design diagrams, icons, draw.io: `references/diagrams-and-icons.md`.
- Microscopy, histology, angiography, echo, blots, image montages, duplicate screening: `references/images-and-integrity.md`.
- Figure legends, captions, alt text: `references/legends-and-alt-text.md`.
- Machine-learning or CS venue figures (ablations, training curves, rooflines): `references/ml-and-cs-figures.md`; self-evolving or agent-loop diagrams: `references/ai-agent-evolution-figures.md`.
- Auditing or polishing an existing figure, final acceptance: `references/qa-checklist.md`.
- Called by the scientific manuscript draft bot, or asked to return a figure packet (handoff JSON in, `figure_packet.json` out): `references/manuscript-bot.md`.
- Mining figures from arXiv papers to study a field's visual conventions: `references/corpus-mining.md`.
- Why a rule exists, and what was kept, changed, or dropped from the source repositories: `references/audit-of-sources.md`; full bibliography: `references/sources.md`.

## Workflow

Work through these steps in order. A small request (resize one plot) may compress steps 1 to 3 into a sentence each, but do not skip step 8.

1. **Write the figure contract.** One sentence stating the claim, the five-second takeaway, the comparison the reader must make, the visual anchor (reference line, null value, baseline, bound), the target journal and column, and the data provenance. Use `assets/figure-contract.yaml` for multi-panel or multi-figure work. If the claim is ambiguous, propose the narrowest defensible version and name the assumption.
2. **Fix the target.** Pick a preset (`pubfig.preset("Circulation")` resolves journal names) and read its `note` for conflicts and unstated values. Physical width comes from the column; height from the content, capped by the preset. Presentation, poster, and web-display (`showcase` preset) modes use larger type; never reuse manuscript artwork on a slide without regenerating it.
3. **Choose the form from the question and the data structure,** not from habit: distributions or estimates with uncertainty for continuous outcomes, step curves for time to event, ratio estimates on a log axis, agreement on a Bland-Altman plot, composition as a normalized stack only when parts sum to a whole. Generate two candidate forms when the choice is not obvious and compare them at the same size.
4. **Build at final size.** Copy the helpers the figure needs into the user's project so the delivered script runs without this skill installed (`pubfig.py` always; `pubfig_plots.py` for chart builders; `pubfig_clinical.py`, which also needs `pubfig_plots.py`, for clinical figures; `image_panels.py` only for image panels):
   ```bash
   mkdir -p figure_sources && cp "$SKILL_DIR"/scripts/pubfig*.py figure_sources/
   ```
   ```python
   import matplotlib; matplotlib.use("Agg")
   import pubfig as pf, pubfig_plots as pp, pubfig_clinical as pc
   spec = pf.setup("jacc", "single", aspect=0.8)   # final-size rcParams; warns on font substitutes
   fig, axes = pf.subplots(spec, 1, 2)              # exact physical canvas, constrained layout
   ```
   Lay out a grayscale skeleton first: reading order, panel grid, axes, anchors. If the figure fails in grayscale, fix structure before adding color. Never export with `bbox_inches="tight"`: it changes the physical canvas and silently rescales the type.
5. **Encode color for meaning.** Default categorical order is Okabe-Ito blue, orange, black, green; the first four stay distinguishable under simulated protanopia, deuteranopia, and tritanopia and in grayscale. Beyond four series add marker or line-style redundancy. Two-arm trials use `pf.ARMS` with solid versus dashed lines. Sequential data use viridis or cividis; signed data use a diverging map centered on the meaningful zero. For a multi-figure paper freeze one palette (`assets/paper-palette.yaml`) so the same entity keeps the same color in every figure.
6. **Annotate.** Label the anchor, label lines directly where space allows, write statistics in the target's house style (`pf.fmt_p`, `pf.fmt_estimate`, `pf.rich_text` for italic P without breaking SVG text), and add panel labels in the journal's convention (`pf.panel_labels`). Keep conclusions, long titles, and methods out of the artwork; they belong in the legend.
7. **Export and verify.** `pf.save(fig, "final_figures/Fig1", ["pdf", "svg", "png", "tif"])` writes vector masters with embedded TrueType fonts and live text, and RGB rasters without alpha at the preset DPI, then reports the measured size of each file.
8. **Run the QA gate and look.** Structure the figure script as a `make_figure()` function that returns the figure, then audit it from a separate QA step so the delivered script never imports from the skill:
   ```python
   # qa step (not part of the delivered script)
   import sys; sys.path.insert(0, f"{SKILL_DIR}/scripts"); sys.path.insert(0, "figure_sources")
   from figure_qa import audit_figure, report
   from fig1 import make_figure
   report(audit_figure(make_figure()))
   ```
   ```bash
   python "$SKILL_DIR"/scripts/figure_qa.py final_figures/Fig1.pdf final_figures/Fig1.tif \
       --target jacc --column single --cvd-preview qa/Fig1_cvd.png
   ```
   Raster audits read the content type that `pf.save` tags into PNG and TIFF files; for other rasters pass `--kind line`, `--kind combination`, or `--kind halftone`. A PNG that `pf.save` wrote as a preview (the journal does not take PNG) is reported as a preview, not judged as the submission file. Fix every FAIL. Fix each WARN or state the reason it stands. Then open the PNG and the CVD preview with the Read tool and inspect them at final size: overlaps, clipping, crowding, misleading scales. Run the five-second test (can a reader state the takeaway, the comparison, and the direction of benefit?) and the caption test (does the legend alone define groups, n, measure, uncertainty, and test?). Automated checks are necessary, not sufficient.
9. **Deliver.** Unless the project has its own convention:
   ```text
   final_figures/   Fig1.pdf  Fig1.svg  Fig1.png  Fig1.tif
   figure_sources/  fig1.py  pubfig*.py  source_data/  (or the user's data path)
   qa/              Fig1_cvd.png  qa_report.txt  original_vs_new.png
   ```
   Include the legend draft (`references/legends-and-alt-text.md`), alt text when the venue asks for it, the preset used with its retrieval date, a provenance note for data and any third-party visual element, and the QA findings that were accepted with reasons. Run `python "$SKILL_DIR"/scripts/figure_qa.py --portability figure_sources/fig1.py` so the script carries no machine-specific paths.

## Improving an existing figure

Start from the authoritative data and plotting source when they exist; polish of an obsolete intermediate is wasted work. Compare original and candidate at the same physical size. Replace only when the candidate is clearly better in readability, honesty, or compliance, and say what changed. If the statistics or data changed, call it a scientific update, not a cosmetic one. When only a flattened image exists, say which fixes are impossible without the source (rescaling axes, recoloring series) rather than painting over pixels.

## Toolkit at a glance

- `scripts/pubfig.py`: presets (42 verified journal, publisher, and venue presets plus generic, presentation, poster, and showcase modes), `setup`, `subplots`, `figure`, `save`, `panel_labels` (works across subfigures), `synthetic_tag`, palettes (`CATEGORICAL`, `OKABE_ITO`, `TOL`, `ARMS`), `tint`, `check_colors` (CIEDE2000 under simulated CVD), `simulate_cvd`, `fmt_p`, `fmt_ci`, `fmt_estimate`, `rich_text`, `notation` (IC50 to IC₅₀, log2 to log₂), `flatten_alpha`.
- `scripts/pubfig_plots.py`: `estimation_plot`, `paired_plot`, `raincloud`, `bar_plot` (zero-based, named error bars), `dot_plot`, `line_band`, `direct_labels`, `legend_panel`, `heatmap`, `sig_bracket`, `small_multiples`, `radar` (one shared scale), `roofline`.
- `scripts/pubfig_clinical.py`: `kaplan_meier` (with Greenwood SE), `km_truncation_time`, `logrank_test`, `cumulative_incidence`, `km_plot`/`km_figure` (risk table, KMunicate extended table, journal truncation rules, CI bands or bars), `forest_plot` (standalone or as one panel via `fig=`/`subplotspec=`), `bland_altman`, `roc_plot`, `auc_delong`, `precision_recall`, `calibration_plot`, `flow_diagram`, `consort_diagram`, `prisma2020_diagram`, `waterfall_plot`, `spaghetti_plot`.
- `scripts/figure_qa.py`: live-figure and file audits, journal chart rules, legend checker (`check_legend_text`), CVD preview, canvas consistency (`--same-size`), source portability, document page rendering (`--render-doc` for DOCX, PPTX, PDF).
- `scripts/image_panels.py`: image standardization with batch-locked display, PHI masks, calibrated scale bars, audit hashes, and duplicate screening.
- `scripts/figure_packet.py`: the figure packet for the manuscript draft bot (files, legend, callout, palette digest, QA verdict, limits).
- `scripts/build_drawio_figure.py`, `validate_drawio_figure.py`, `export_drawio_figure.py`, `validate_paper_palette.py`, `assets/paper-icons/`: editable schematic pipeline (see `references/diagrams-and-icons.md`).
- `scripts/collect_arxiv_figures.py`, `analyze_visuals.py`, `analyze_agent_figures.py`: corpus mining.
- `scripts/demo_gallery.py`: renders and audits the example gallery in `examples/gallery/` (synthetic data); run it after editing the toolkit.

Dependencies: Python 3.10+, numpy, matplotlib 3.7+ (3.10+ for subfigure panels), Pillow; scipy recommended (t and normal quantiles, KDE). Optional: pypdf (PDF font audit), poppler (`pdffonts`, `pdfimages`, `pdftoppm`), cairosvg (SVG rasterizing), Ghostscript (`gs`, rasterizing EPS for previews), LibreOffice (page rendering), OpenCV (partial-overlap duplicate screening), draw.io desktop (diagram export). Check what is installed before promising an output; if the requested font is missing, `setup` names the substitute, and the figure is not final until the real font is installed.

## Defaults and the reasons for them

- Type at final size: 6.5 to 9 pt for most print journals, exact values per preset (Nature 5 to 7 pt; AHA 10 pt; JVS and the JACC family 10 pt minimum; Vascular Medicine 16 to 18 pt). At most three sizes plus panel labels, because more sizes read as noise.
- Strokes: axes 0.5 to 0.75 pt, data 1 to 1.5 pt, never below the preset minimum (often 0.25 pt; 1 pt for Nature Communications).
- Fonts: Arial unless the target says otherwise; one family per figure; TrueType embedded (PDF Type 42), SVG text live. Type 3 fonts fail many production systems.
- Rasters: flattened RGB, LZW TIFF, at the preset DPI for the content type (line art, halftone, combination).
- Panel labels: preset convention (Nature lowercase bold a; Cell, JAMA, AHA, EHJ uppercase A; IEEE and ML venues (a)), aligned by row and column, outside the data region.
- Statistics: AMA style by default (italic P, no leading zero, P < .001), switched by preset (NEJM P<0.001, Lancet p<0·0001, EJVES p = .043, AHA 2 significant digits).

## Acceptance gate

Do not deliver while any of these is true; `references/qa-checklist.md` has the full list and the manual checks.

- Data, denominators, groups, units, direction of effect, or statistical scope are unverified.
- Any text is below the preset minimum, clipped, overlapping, in a fallback font, or uses the wrong P-value or notation style for the target.
- A bar axis does not start at zero, a continuous outcome with small n hides its observations, or an error bar is undefined.
- Colors fail the CVD or grayscale check without redundant encoding, or a rainbow colormap encodes data.
- Width, height, DPI, font embedding, format, or color mode violates the preset, or same-slot panels have different canvases.
- An image panel has unlocked display settings, an uncalibrated scale bar, visible patient identifiers, or local edits.
- The final PNG and CVD preview were not opened and inspected.

## Provenance

This skill merges and audits three open repositories: Scientific-Figure-Design (MIT; figure contract, archetypes, grayscale-first design, paper palette contract, draw.io and icon pipeline, corpus mining), polish-sci-figures (MIT; delivery modes, fixed canvases, scientific typography, collision and grid checks, experimental-unit statistics, image standardization, duplicate screening, portability, container rendering), and figures4papers (CC BY-NC 4.0; matplotlib helper API and semantic palette roles, re-implemented rather than copied). `references/audit-of-sources.md` lists every correction, including defaults that failed the color-vision and final-size checks. `THIRD_PARTY_NOTICES.md` carries the licenses.
