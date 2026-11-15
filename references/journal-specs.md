# Journal specifications

Rendered from `pubfig.PRESETS` by `scripts/build_reference_tables.py`; do not edit by hand. Values come from official author instructions retrieved 2026-11-14; verbatim quotes and URLs are in `assets/journal-specs/journal_specs_clinical.json` and `journal_specs_science.json`. Where a journal is silent, the preset uses its publisher's generic guide or the skill's generic values, and the note says so.

Before a real submission: open the journal's current instructions (URL below), confirm width, resolution, font, format, and panel-label rules, and record the URL and date with the figure files. For a journal not listed, read its instructions and call `pubfig.register_preset(key, {...})` with only the values it states.

Units: widths and heights in mm; type in pt at final size (label/tick/panel); lines in pt (axes/data/minimum); DPI as line art/halftone/combination.

## Cardiovascular, vascular, and general medical journals

### JACC (defers to Elsevier sizing) (`jacc`)
- Widths: single 90, onehalf 140, double 190; max height 230
- Font: Arial, 7 to 12 pt; labels 8, ticks 7, panel 9 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 1200/300/500; formats tif, eps, pdf; color RGB; statistics style `ama`
- Chart rules checked by figure_qa: avoid_bar_graphs, legend_title_max_10_words, legend_max_150_words
- Not stated by the source (default used): max height; panel style; line weight (Elsevier generic used)
- Note: Live instructions defer to Elsevier; superseded 2024 PDF required TIF, 1200 dpi line art, 12 pt lettering and >= 13 x 18 cm. Avoid bar graphs; legend title <= 10 words, legend <= 150 words; no trial logos; AMA style 'with minor modifications'; Central Illustration optional.
- Source: https://www.jacc.org/journal/jacc/author-center/for-authors (retrieved 2026-11-14)

### JACC: Cardiovascular Interventions / Advances / Basic to Translational Science (`jacc_family`)
- Widths: single 177.8, double 177.8; max height 230
- Font: Arial, 10 to 14 pt; labels 12, ticks 10, panel 14 pt bold 'A'
- Lines: axes 1, data 1.5, minimum 0.5 pt; DPI 1200/300/600; formats pdf, eps, svg, tif; color RGB; statistics style `ama`
- Chart rules checked by figure_qa: avoid_bar_graphs, no_dynamite_plots, black_white_not_gray
- Not stated by the source (default used): max height; line weight; panel style; resolution for JACC: CI
- Note: Typeset figures >= 7 in wide; lettering optimal 12 pt, minimum 10 pt; no column-with-error-bar plots (Advances/BTS); JACC: CI charts in black and white, not gray; Central Illustration required (JACC: CI) with boxed header and title <= 10 words.
- Source: https://www.jacc.org/journal/interventions/author-center/for-authors (retrieved 2026-11-14)

### AHA journals (Circulation, Circ Cardiovasc Interv, Hypertension, ATVB, Stroke) (`aha`)
- Widths: single 80, onehalf 127.5, double 177.5; max height 230
- Font: Arial, 10 to 12 pt; labels 10, ticks 10, panel 12 pt bold 'A'
- Lines: axes 0.75, data 1.25, minimum 0.5 pt; DPI 1200/600/600; formats tif, eps, pdf; color RGB; statistics style `aha`
- Chart rules checked by figure_qa: max_6_panels, no_headings_on_figure
- Not stated by the source (default used): widths on current pages (2012 PDF used); max height; line weight
- Note: Font conflict: Figure Guidelines 8-10 pt vs Submission Guidelines >= 10 pt (10 pt satisfies both). Widths only in a 2012 Hypertension PDF. Uppercase panel letters upper left; <= 6 panels; RGB not CMYK.
- Source: https://www.ahajournals.org/figure-guidelines (retrieved 2026-11-14)

### European Heart Journal (`ehj`)
- Widths: single 85, double 178; max height 230
- Font: Arial, 8 to 12 pt; labels 9, ticks 8, panel 10 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 1200/600/600; formats pdf, eps, tif; color RGB; statistics style `ehj`
- Chart rules checked by figure_qa: max_6_panels, km_numbers_at_risk
- Not stated by the source (default used): widths; max height; line weight (OUP generic used)
- Note: Widths not stated (measure a recent issue). Text >= 2 mm high (about 8 pt); Myriad Pro/Arial/Helvetica. Photos >= 350 dpi (600 rec.), line art >= 600 (1200 rec.). Graphical abstract 11.0 x 18.0 cm landscape, 300 ppi, 10-12 pt (>= 8), legend <= 80 words.
- Source: https://academic.oup.com/eurheartj/pages/general_instructions (retrieved 2026-11-14)

### EuroIntervention (`eurointervention`)
- Widths: single 80, double 170; max height 230
- Font: Arial, 9 to 14 pt; labels 12, ticks 10, panel 13 pt bold 'A'
- Lines: axes 0.75, data 1.25, minimum 0.5 pt; DPI 1200/300/600; formats pptx, eps, pdf; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): double width; max height; resolution; minimum font size; font family
- Note: Images >= 8 x 8 cm (one column); lettering optimal 12 pt (minimum not stated); Central Illustration mandatory for main article types; 7 display items (research). dpi not stated (values here are Elsevier-like defaults).
- Source: https://eurointervention.pcronline.com/author-centre/manuscript-contents (retrieved 2026-11-14)

### Journal of Vascular Surgery / JVS-VL (`jvs`)
- Widths: single 90, onehalf 140, double 190, reference 76.2; max height 230
- Font: Arial, 10 to 14 pt; labels 10, ticks 10, panel 12 pt bold 'A'
- Lines: axes 0.75, data 1.25, minimum 0.5 pt; DPI 1000/300/500; formats tif, eps, jpg; color RGB; statistics style `ama`
- Chart rules checked by figure_qa: km_numbers_at_risk, km_truncate_se_10pct
- Not stated by the source (default used): max height; line weight; font family; line-art and combination dpi (Elsevier generic used)
- Note: Images >= 300 dpi at 3 in wide (900 px); text >= 10 pt; survival curves need n at risk and truncation when SE > 10%; AMA Manual of Style (10th ed cited). Widths/line art dpi from Elsevier generic. Optional visual abstract (PowerPoint template).
- Source: https://www.jvascsurg.org/content/authorinfo (retrieved 2026-11-14)

### European Journal of Vascular and Endovascular Surgery (`ejves`)
- Widths: single 90, double 190; max height 230
- Font: Arial, 7 to 10 pt; labels 8, ticks 7, panel 9 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 1000/300/500; formats tif, eps, pdf; color RGB; statistics style `ejves`
- Chart rules checked by figure_qa: km_y_from_zero, km_numbers_at_risk, km_truncate_below_10_at_risk, portrait_only
- Not stated by the source (default used): widths; max height (one portrait page); resolution; fonts; line weight
- Note: Portrait only, one page max; panels A, B, C top left (sub-panels a, b, c); KM y-axis from 0, numbers at risk, truncate below 10 at risk. dpi not stated.
- Source: https://legacyfileshare.elsevier.com/promis_misc/ejves-instructions-for-authors.pdf (retrieved 2026-11-14)

### Catheterization and Cardiovascular Interventions (Wiley) (`ccv`)
- Widths: single 80, double 180; max height 230
- Font: Arial, 7 to 10 pt; labels 8, ticks 7, panel 9 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 600/300/600; formats tif, eps, pdf; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): fonts; line weight; panel style; max height
- Note: CCI: >= 300 dpi all figures; Wiley line art 600 dpi; print colour charged; central figure encouraged.
- Source: https://onlinelibrary.wiley.com/page/journal/1522726x/homepage/forauthors.html (retrieved 2026-11-14)

### Journal of Endovascular Therapy (Sage) (`jevt`)
- Widths: single 76.2, double 127; max height 230
- Font: Arial, 7 to 10 pt; labels 8, ticks 7, panel 9 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 600/400/600; formats tif, eps; color RGB; statistics style `jevt`
- Chart rules checked by figure_qa: km_valid_se_lt_10pct_and_10_at_risk, km_no_ci_bands
- Not stated by the source (default used): max width; max height; fonts; line weight; panel style
- Note: >= 3 in wide (vertical) / 5 in (horizontal); colour/grey 400 ppi, line 600 ppi (another section says 300 dpi); KM valid only while SE < 10% and >= 10 at risk, do not plot 95% CIs; visual abstract required (PowerPoint 13.33 x 7.5 in).
- Source: https://journals.sagepub.com/author-instructions/JET (retrieved 2026-11-14)

### Vascular Medicine (Sage/SVM) (`vascmed`)
- Widths: single 127, double 178; max height 230
- Font: Arial, 16 to 18 pt; labels 18, ticks 16, panel 18 pt bold 'A'
- Lines: axes 1.5, data 2.5, minimum 1 pt; DPI 800/300/600; formats tif, eps; color RGB; statistics style `vascmed`
- Not stated by the source (default used): double width; max height; line weight; line-art dpi (Sage generic used)
- Note: At least 5 in wide with 16 or 18 pt font (maximized); >= 300 dpi; panel labels must not be part of the image (Images in Vascular Medicine). Layouts built for 7-9 pt print need fewer elements at this type size; expect figure_qa to flag crowding.
- Source: https://journals.sagepub.com/author-instructions/VMJ (retrieved 2026-11-14)

### Sage journals (generic: Phlebology, Lymphatic Res Biol) (`sage`)
- Widths: single 85, double 170; max height 230
- Font: Arial, 7 to 10 pt; labels 8, ticks 7, panel 9 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 800/300/600; formats tif, eps; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): widths; max height; fonts; line weight; panel style
- Note: Raster >= 300 dpi, line art >= 800 dpi; EPS for graphs; widths not stated (match the journal, no upscaling).
- Source: https://www.sagepub.com/journals/information-for-authors/preparing-your-manuscript (retrieved 2026-11-14)

### JAMA Network (incl. JAMA Cardiology) (`jama`)
- Widths: single 85, double 178; max height 230
- Font: Arial, 7 to 10 pt; labels 8, ticks 7, panel 9 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 600/350/600; formats pdf, eps, svg; color RGB; statistics style `ama`
- Chart rules checked by figure_qa: no_pie, no_3d, no_stacked_bars, ratios_log_scale, errorbars_both_directions, max_4_panels, km_numbers_at_risk
- Not stated by the source (default used): widths (figures re-created by JAMA); max height; fonts; line weight; panel style
- Note: Graphs redrawn by JAMA staff (submit vector); images >= 350 ppi, line drawings >= 600 ppi; no pie, 3-D or stacked bars; error bars in both directions; ratios on a log scale; KM as step curve with numbers at risk; <= 4 panels.
- Source: https://jamanetwork.com/journals/jama/pages/instructions-for-authors (retrieved 2026-11-14)

### New England Journal of Medicine (`nejm`)
- Widths: single 85, double 178; max height 230
- Font: Arial, 7 to 10 pt; labels 8, ticks 7, panel 9 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 600/300/600; formats pdf, eps, svg; color RGB; statistics style `nejm`
- Not stated by the source (default used): widths (figures redrawn); max height; fonts; line weight; panel style
- Note: Figures redrawn by NEJM illustrators; data visualizations as editable vector (no SPSS/Stata files); photos >= 300 ppi; <= 5 figures/tables.
- Source: https://www.nejm.org/author-center/new-manuscripts (retrieved 2026-11-14)

### The Lancet family (`lancet`)
- Widths: single 85, photo_min 107, double 178; max height 230
- Font: Arial, 7 to 10 pt; labels 8, ticks 7, panel 9 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 600/300/600; formats pdf, eps, svg; color RGB; statistics style `lancet`
- Chart rules checked by figure_qa: forest_and_flow_printed_bw, no_3d
- Not stated by the source (default used): column widths (figures redrawn); max height; fonts; line weight; panel style
- Note: Figures redrawn in-house; editable vector with live text; photos >= 300 dpi and >= 107 mm wide; forest plots and trial profiles printed black and white.
- Source: https://www.thelancet.com/pb-assets/Lancet/authors/tl-info-for-authors-1787150940677.pdf (retrieved 2026-11-14)

### BMJ journals (Heart; The BMJ) (`bmj`)
- Widths: single 83, double 173.5; max height 233.5
- Font: Arial, 7 to 10 pt; labels 8, ticks 7, panel 9 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 1200/300/600; formats tif, eps, pdf; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): fonts; line weight; panel style
- Note: 8.3-17.35 cm wide, <= 23.35 cm high (2014 PDF linked from the Author Hub); EPS text outlined (conflicts with editable-text rules elsewhere); print colour charged; favour CIs over P values.
- Source: https://authors.bmj.com/writing-and-formatting/formatting-your-paper/ (retrieved 2026-11-14)

### Annals of Internal Medicine (`annals`)
- Widths: single 85, double 178; max height 230
- Font: Arial, 7 to 10 pt; labels 8, ticks 7, panel 9 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 600/300/600; formats pdf, eps; color RGB; statistics style `annals`
- Chart rules checked by figure_qa: forest_raw_numbers_in_margins, km_numbers_at_risk
- Not stated by the source (default used): widths; max height; resolution; fonts; line weight; panel style
- Note: No artwork specs stated; forest plots need raw numbers in the margins; numbers at risk on survival plots; 'mean (SD)' not ±.
- Source: https://www.acpjournals.org/journal/aim/authors (retrieved 2026-11-14)

## General science journals

### Nature (`nature`)
- Widths: single 89, onehalf 120, onehalf_max 136, double 183; max height 170
- Font: Arial, 5 to 7 pt; labels 7, ticks 6, panel 8 pt bold 'a'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 1200/450/600; formats pdf, eps, svg, png; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): lines.data
- Note: Nature pages conflict: 89/183 mm and 247 mm page depth (final submission) vs 90/180 mm and 170 mm (formatting guide); photos 300 dpi vs 450 dpi checklist. Main figures must be editable vector; no outlined text.
- Source: https://www.nature.com/nature/for-authors/final-submission (retrieved 2026-11-14)

### Nature Portfolio research journals (Nat Med, Nat Commun) (`natureportfolio`)
- Widths: single 88, double 180; max height 185
- Font: Arial, 5 to 7 pt; labels 7, ticks 6, panel 8 pt bold 'a'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 1200/300/600; formats pdf, eps, png; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): lines; panel style (example figure uses lowercase bold)
- Note: Max height depends on legend length (~130-225 mm). Nature Communications and Scientific Reports state lines >= 1 pt: use 'naturecomms'.
- Source: https://www.nature.com/documents/NRJs-guide-to-preparing-final-artwork.pdf (retrieved 2026-11-14)

### Nature Communications / Scientific Reports (`naturecomms`)
- Widths: single 88, double 180; max height 230
- Font: Arial, 5 to 7 pt; labels 7, ticks 6.5, panel 7 pt bold 'a'
- Lines: axes 1, data 1.25, minimum 1 pt; DPI 1200/300/600; formats pdf, eps, tif; color RGB; statistics style `generic_lz`
- Chart rules checked by figure_qa: legend_max_350_words
- Not stated by the source (default used): font sizes (Nature 5-7 pt used); max height (only the 210 x 276 mm PDF page is stated); 1.5-column width
- Note: States lines >= 1 pt and panel labels the same size as other text; no pt range stated (Nature 5-7 pt used).
- Source: https://www.nature.com/ncomms/submit/how-to-submit (retrieved 2026-11-14)

### Science (`science`)
- Widths: single 57, double 121, triple 184; max height 230
- Font: Helvetica, 5 to 9 pt; labels 7, ticks 6, panel 10 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.5 pt; DPI 1200/300/600; formats pdf, eps, tif; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): max height (page box only); dpi for line art
- Note: Web pages: ~7 pt (min 5), lines >= 0.5 pt; 2025 prep guide: 9/18.3 cm, 6-9 pt, max 3 sizes, lines >= 0.28 pt. No PowerPoint/Word.
- Source: https://www.science.org/content/page/instructions-preparing-initial-manuscript (retrieved 2026-11-14)

### Science Advances (`scienceadv`)
- Widths: single 90, onehalf 144, double 184; max height 199
- Font: Myriad Pro, 6 to 9 pt; labels 8, ticks 7, panel 9 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.28 pt; DPI 1200/300/300; formats pdf, ai, tif; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): font embedding
- Note: Myriad preferred (Arial is the usual substitute); RGB mandatory; files > 600 dpi are downsampled.
- Source: https://www.science.org/content/page/science-advances-information-authors (retrieved 2026-11-14)

### Cell Press (Cell, Cell Reports) (`cell`)
- Widths: single 85, onehalf 114, double 174; max height 200
- Font: Arial, 6 to 8 pt; labels 7, ticks 6.5, panel 8 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.5 pt; DPI 1000/300/500; formats tif, pdf; color RGB; statistics style `generic_lz`
- Note: Arial only. Recommended max 6.5 x 8 in (16.5 x 20 cm) although full width is 17.4 cm. Graphical abstract 1200 px square, Arial 8-12 pt.
- Source: https://www.cell.com/information-for-authors/figure-guidelines (retrieved 2026-11-14)

### PNAS (`pnas`)
- Widths: single 87, onehalf 114, double 178; max height 225
- Font: Arial, 6 to 12 pt; labels 7, ticks 6.5, panel 8 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 1200/300/600; formats pdf, eps, tif; color RGB; statistics style `generic_lz`
- Chart rules checked by figure_qa: numeric_axes_include_zero
- Not stated by the source (default used): panel style
- Note: Digital Art Guidelines: numerical axes must go to 0 except log axes. Panel style not stated.
- Source: https://www.pnas.org/pb-assets/authors/digitalart-1675347574760.pdf (retrieved 2026-11-14)

### PLOS journals (`plos`)
- Widths: single 132, full 190.5, min 66.8; max height 222.3
- Font: Arial, 8 to 12 pt; labels 9, ticks 8, panel 11 pt bold 'A'
- Lines: axes 0.75, data 1.25, minimum 0.5 pt; DPI 600/300/600; formats tif, eps; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): line weight
- Note: TIFF or EPS only; Arial/Times/Symbol 8-12 pt; panel labels '(A) or (a)'; > 600 dpi may be resized. Line weight not stated.
- Source: https://journals.plos.org/plosone/s/figures (retrieved 2026-11-14)

### eLife (`elife`)
- Widths: single 100, double 200; max height 250
- Font: Arial, 7 to 12 pt; labels 8, ticks 7, panel 10 pt bold 'A'
- Lines: axes 0.75, data 1.25, minimum 0.5 pt; DPI 600/300/300; formats tif, pdf, eps; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): fonts; line weight; panel style; max height
- Note: Only minimum widths (10 cm; 20 cm for full-page) and >= 300 dpi are stated; type and lines use generic values.
- Source: https://elife-rp.msubmit.net/html/elife-rp_author_instructions.html (retrieved 2026-11-14)

## Publishers (generic artwork guides)

### Elsevier (generic artwork instructions) (`elsevier`)
- Widths: single 90, onehalf 140, double 190, min 30; max height 230
- Font: Arial, 6 to 9 pt; labels 7, ticks 7, panel 9 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 1000/300/500; formats eps, pdf, tif; color RGB; statistics style `ama`
- Not stated by the source (default used): max height; panel style
- Note: 7 pt text, >= 6 pt sub/superscripts; lines 0.25 pt recommended (0.1 absolute minimum); 1200 dpi for very fine line art. Max height not stated.
- Source: https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions (retrieved 2026-11-14)

### Springer journals (generic) (`springer`)
- Widths: single 84, double 174, small_journal 119; max height 234
- Font: Arial, 8 to 12 pt; labels 9, ticks 8, panel 10 pt bold 'a'
- Lines: axes 0.6, data 1, minimum 0.3 pt; DPI 1200/300/600; formats eps, pdf, tif; color RGB; statistics style `generic_lz`
- Note: Text about 2-3 mm (8-12 pt); a 2021 PDF lists 39/84/129/174 mm. Small-format journals: 119 x 195 mm.
- Source: https://link.springer.com/journal/11145/submission-guidelines (retrieved 2026-11-14)

### BMC journals (`bmc`)
- Widths: single 85, double 170; max height 225
- Font: Arial, 6 to 12 pt; labels 8, ticks 7, panel 9 pt bold 'a'
- Lines: axes 0.5, data 1, minimum 0.3 pt; DPI 600/300/300; formats pdf, eps, tif, png; color RGB; statistics style `generic_lz`
- Chart rules checked by figure_qa: legend_title_max_15_words, legend_max_300_words
- Not stated by the source (default used): font family and size; color mode
- Note: Lines > 0.25 pt; height includes legend; fonts embedded. Font size not stated.
- Source: https://link.springer.com/journal/12916/submission-guidelines (retrieved 2026-11-14)

### Wiley journals (generic) (`wiley`)
- Widths: single 80, double 180; max height 230
- Font: Arial, 6 to 10 pt; labels 8, ticks 7, panel 9 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 600/300/600; formats pdf, eps, tif; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): max height; fonts; line weight; panel style; color mode
- Note: 80-180 mm; fonts, line weight, panel style and max height not stated.
- Source: https://authors.wiley.com/author-resources/Journal-Authors/Prepare/manuscript-preparation-guidelines.html/figure-preparation.html (retrieved 2026-11-14)

### Oxford University Press journals (generic) (`oup`)
- Widths: single 85, double 178; max height 230
- Font: Arial, 7 to 10 pt; labels 8, ticks 7, panel 9 pt bold 'A'
- Lines: axes 0.5, data 1, minimum 0.25 pt; DPI 1200/600/900; formats eps, pdf, tif; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): widths; max height; panel style
- Note: Widths not stated (measure the journal); colour halftone 300, greyscale 600, combination/line 600-900, mono line 1200 dpi; lines 0.25-1 pt.
- Source: https://academic.oup.com/pages/for-authors/journals/preparing-and-submitting-your-manuscript (retrieved 2026-11-14)

### Taylor & Francis journals (generic) (`tandf`)
- Widths: single 85, double 178; max height 230
- Font: Arial, 7 to 10 pt; labels 8, ticks 7, panel 9 pt bold '(a)'
- Lines: axes 0.5, data 1, minimum 0.3 pt; DPI 1200/600/600; formats eps, tif; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): widths; max height; color mode
- Note: PDF figures not accepted; colour photos 300, greyscale 600 dpi. Widths not stated.
- Source: https://authorservices.taylorandfrancis.com/editorial-policies/images-and-figures/ (retrieved 2026-11-14)

### ACS journals (JACS appendix) (`acs`)
- Widths: single 84.6, double 177.8, double_min 105.8; max height 232.8
- Font: Arial, 4.5 to 10 pt; labels 7, ticks 6.5, panel 8 pt bold 'a'
- Lines: axes 0.5, data 1, minimum 0.5 pt; DPI 1200/300/600; formats tif, pdf, eps; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): panel style; color mode
- Note: Lettering >= 4.5 pt (JACS Au checklist says >= 8 pt); max depth includes caption; TOC graphic <= 3.25 x 1.75 in.
- Source: https://researcher-resources.acs.org/publish/author_guidelines/pdf?coden=jacsat (retrieved 2026-11-14)

### Royal Society journals (`royalsociety`)
- Widths: single 85, double 178; max height 230
- Font: Times New Roman, 7.5 to 11 pt; labels 9, ticks 8, panel 9 pt normal '(a)'
- Lines: axes 0.5, data 1, minimum 0.3 pt; DPI 600/300/300; formats pdf, eps, tif; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): widths; max height; color mode; line weight
- Note: Panel labels italic letters in roman brackets '(a)'; widths not stated.
- Source: https://royalsociety.org/journals/authors/author-guidelines/ (retrieved 2026-11-14)

### Frontiers journals (`frontiers`)
- Widths: single 85, double 180; max height 230
- Font: Arial, 8 to 12 pt; labels 9, ticks 8, panel 10 pt bold 'A'
- Lines: axes 2, data 2, minimum 2 pt; DPI 300/300/300; formats tif, jpg, eps; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): font family
- Note: States lines 'no smaller than two points wide' (unusually heavy; confirm with the editorial office).
- Source: https://www.frontiersin.org/guidelines/author-guidelines (retrieved 2026-11-14)

### MDPI journals (`mdpi`)
- Widths: single 85, double 170; max height 230
- Font: Arial, 7 to 12 pt; labels 8, ticks 7, panel 9 pt normal '(a)'
- Lines: axes 0.5, data 1, minimum 0.3 pt; DPI 600/600/600; formats png, tif, jpg; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): widths; max height; fonts; line weight; panel style
- Note: Raster PNG/JPEG/TIFF >= 600 dpi preferred, 'no editable parts'; widths not stated.
- Source: https://www.mdpi.com/journal/sensors/instructions (retrieved 2026-11-14)

## Engineering and machine-learning venues

### IEEE journals (`ieee`)
- Widths: single 88.9, double 182; max height 220
- Font: Arial, 8 to 10 pt; labels 9, ticks 8, panel 10 pt normal '(a)'
- Lines: axes 0.5, data 1, minimum 0.5 pt; DPI 600/300/600; formats pdf, eps, tif; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): color mode; line weight; panel style
- Note: Text approx. 9-10 pt; Helvetica/Times/Arial/Cambria/Symbol; embed or outline fonts. Line weight and panel style not stated.
- Source: https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/ (retrieved 2026-11-14)

### ACM (acmart sigconf) (`acm`)
- Widths: single 84.8, double 178, acmsmall 139.1; max height 230
- Font: Arial, 6 to 9 pt; labels 8, ticks 7, panel 8 pt normal '(a)'
- Lines: axes 0.5, data 1, minimum 0.3 pt; DPI 600/300/600; formats pdf; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): resolution; line weight; panel style; figure fonts
- Note: Column 3.337 in, text 7.006 in (sigconf); body Linux Libertine; every figure needs a \Description (alt text).
- Source: https://www.acm.org/publications/authors/submissions (retrieved 2026-11-14)

### NeurIPS (neurips_2026.sty) (`neurips`)
- Widths: single 139.7, half 68; max height 200
- Font: Arial, 6 to 10 pt; labels 8, ticks 7, panel 9 pt normal '(a)'
- Lines: axes 0.6, data 1.2, minimum 0.3 pt; DPI 600/300/600; formats pdf; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): figure fonts; line weight; panel style; resolution
- Note: Text width 5.5 in, one column; body Times 10 pt. Figure fonts are not specified; keep >= 6-7 pt after \includegraphics scaling.
- Source: https://media.neurips.cc/Conferences/NeurIPS2026/Formatting_Instructions_For_NeurIPS_2026.zip (retrieved 2026-11-14)

### ICLR (iclr2027_conference.sty) (`iclr`)
- Widths: single 139.7, half 68; max height 200
- Font: Arial, 6 to 10 pt; labels 8, ticks 7, panel 9 pt normal '(a)'
- Lines: axes 0.6, data 1.2, minimum 0.3 pt; DPI 600/300/600; formats pdf; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): figure fonts; line weight; panel style; resolution
- Note: Text width 5.5 in.
- Source: https://raw.githubusercontent.com/ICLR/Master-Template/master/iclr2027/iclr2027_conference.sty (retrieved 2026-11-14)

### ICML (icml2026.sty) (`icml`)
- Widths: single 82.55, double 171.45; max height 200
- Font: Arial, 6 to 9 pt; labels 7.5, ticks 6.5, panel 8 pt normal '(a)'
- Lines: axes 0.6, data 1, minimum 0.3 pt; DPI 600/300/600; formats pdf; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): figure fonts; line weight; panel style; resolution
- Note: Two columns: 3.25 in column, 6.75 in text.
- Source: https://media.icml.cc/Conferences/ICML2026/Styles/icml2026.zip (retrieved 2026-11-14)

### CVPR/ICCV (cvpr.sty) (`cvpr`)
- Widths: single 83.34, double 174.6; max height 200
- Font: Arial, 6 to 9 pt; labels 7.5, ticks 6.5, panel 8 pt normal '(a)'
- Lines: axes 0.6, data 1, minimum 0.3 pt; DPI 600/300/600; formats pdf; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): figure fonts; line weight; panel style; resolution
- Note: Column 3.28125 in per the style file (template prose says 3.25 in); text 6.875 in.
- Source: https://raw.githubusercontent.com/cvpr-org/author-kit/main/cvpr.sty (retrieved 2026-11-14)

### ACL / ARR (acl.sty) (`acl`)
- Widths: single 77, double 160; max height 200
- Font: Arial, 6 to 9 pt; labels 7.5, ticks 6.5, panel 8 pt normal '(a)'
- Lines: axes 0.6, data 1, minimum 0.3 pt; DPI 600/300/600; formats pdf; color RGB; statistics style `generic_lz`
- Not stated by the source (default used): figure fonts; line weight; panel style; resolution
- Note: A4: column 7.7 cm, text 16 cm.
- Source: https://raw.githubusercontent.com/acl-org/acl-style-files/master/acl.sty (retrieved 2026-11-14)

## Non-print modes and fallback

### Generic print (no journal chosen) (`generic`)
- Widths: single 85, onehalf 120, double 178; max height 230.0
- Font: Arial, 6 to 9 pt; labels 7, ticks 6.5, panel 8 pt bold 'A'
- Lines: axes 0.6, data 1, minimum 0.25 pt; DPI 1000/300/600; formats pdf, svg, png; color RGB; statistics style `ama`

### Slide (16:9, 13.333 x 7.5 in) (`presentation`)
- Widths: full 310, half 150, third 98; max height 160.0
- Font: Arial, 12 to 28 pt; labels 16, ticks 14, panel 18 pt bold 'A'
- Lines: axes 1.2, data 2.5, minimum 1 pt; DPI 300/300/300; formats svg, png; color RGB; statistics style `ama`

### Poster panel (A0 portrait, 3-column grid) (`poster`)
- Widths: column 250, double 520; max height 400.0
- Font: Arial, 18 to 40 pt; labels 24, ticks 20, panel 28 pt bold 'A'
- Lines: axes 1.5, data 3, minimum 1 pt; DPI 300/300/300; formats pdf, png; color RGB; statistics style `ama`

### Web/README image readable at 1200 px wide (`showcase`)
- Widths: full 254; max height 300.0
- Font: Arial, 9 to 18 pt; labels 11, ticks 10, panel 13 pt bold 'A'
- Lines: axes 0.9, data 1.8, minimum 0.5 pt; DPI 120/120/120; formats png, svg; color RGB; statistics style `ama`
