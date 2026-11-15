# Typography and notation

Type is set at final printed size. A label specified as 7 pt on a 183 mm canvas is 7 pt in print only if the figure is placed at 183 mm; a canvas drawn at 45 × 12 in with 24 pt text (a figures4papers pattern) prints at about 4 pt when reduced to 183 mm. `audit_figure(fig, target=..., column=...)` reports the effective size after placement.

## Fonts

- One family per figure and per paper; Arial unless the target states otherwise (Cell: Arial only; Science: Helvetica; Science Advances: Myriad; Royal Society: Times New Roman suggested; ML venues: any clear sans or the template's Times). Mathematical text uses the same family (`pubfig.setup` sets mathtext to the chosen family).
- `pubfig.resolve_font` tries the requested family, then metric-compatible substitutes (Liberation Sans or Arimo for Arial; Liberation Serif or Tinos for Times New Roman; Carlito for Calibri), then lookalikes. A metric-compatible substitute gives identical layout, but the embedded font name differs; install the real font before final export and rerun QA.
- Embed fonts. PDF: TrueType (`pdf.fonttype = 42`); matplotlib's default Type 3 is rejected by several production systems. SVG: live text (`svg.fonttype = "none"`) so a phrase stays editable as one object. Outlined text is required by a few (BMJ EPS) and forbidden by others (Nature); follow the target.
- Missing glyphs (µ, ±, −, ≥, subscript digits, arrows) are release failures, not warnings: `audit_figure` fails `MISSING_GLYPH`.

## Sizes

- At most three sizes plus panel labels: tick labels, axis labels and legend, panel labels. More sizes read as noise (Scientific-Figure-Design limit).
- Typical print range 6.5 to 9 pt; the presets carry each target's rule. Notable outliers: Nature 5 to 7 pt; Science Advances 8 pt (minimum 6); PLOS 8 to 12 pt; Springer 8 to 12 pt; AHA at least 10 pt; JVS at least 10 pt; JACC: CI, Advances, and BTS 12 pt optimal, 10 pt minimum, at 7 in width or more; EuroIntervention 12 pt optimal; EHJ text at least 2 mm high (about 8 pt); Vascular Medicine 16 to 18 pt at 5 in or wider.
- Panel labels: Nature 8 pt bold lowercase; Science 10 pt bold uppercase; Science Advances 9 pt bold uppercase; Cell uppercase; IEEE, ACM, and ML venues "(a)"; Royal Society italic "(a)". Presets set this automatically.
- Do not shrink text to rescue a crowded layout; redesign or move to a larger slot.

## Scientific notation (from polish-sci-figures, verified rules)

- Italicize only symbols that convention italicizes: P, n, r, t, F, z, and variables. Keep numbers, operators, units, and words upright. Do not italicize a whole annotation because it contains P.
- True subscripts and superscripts as live text: IC₅₀, EC₅₀, log₂, log₁₀, CO₂, SpO₂, m², 10⁻⁴. `pf.notation("IC50 in log2 units")` converts the common cases; check glyph coverage.
- Signs: true minus (−, U+2212; matplotlib ticks use it via `axes.unicode_minus`), ±, ×, ≤, ≥. Never "x" for multiplication or "+/-".
- Spaces: around =, <, > in AMA style; between a number and its unit (0.72 µM, 120 mmHg); none before % or °. Some styles write P<0.001 without spaces (NEJM, Annals): follow the preset.
- Units in parentheses after the quantity: "Systolic BP (mmHg)", "eGFR (mL/min/1.73 m²)".
- Genus and species italic; gene symbols per organism convention (human uppercase italic genes, mouse sentence case italic genes, proteins roman). Preserve the author's labels when unsure and ask.
- Keep abbreviations identical across panels and define them in the legend.

## P values and confidence intervals by journal

Implemented in `pf.STATS_STYLES` and selected by each preset's `stats` key. Quoted rules (journal instructions retrieved 2026-11-14):
- AMA style (JAMA Network; the default for JACC, JVS, Elsevier presets): "for P values less than .001, report as P <.001; for P values between .001 and .01, report the value to the nearest thousandth; for P values greater than or equal to .01, report the value to the nearest hundredth; and for P values greater than .99, report as P >.99"; italic capital P, no leading zero; example "0.8%, 95% CI −0.2% to 1.8%; P = .13". The skill prints "P < .001" with spaces, matching typeset JAMA articles and the user's default; set a custom style if a target wants the instruction page's spacing literally.
- NEJM: "P values larger than 0.01 should be reported to two decimal places, and those between 0.01 and 0.001 to three decimal places; P values smaller than 0.001 should be reported as P<0.001."
- Annals: 0.001 to 0.20 to the nearest thousandth, above 0.20 to the nearest hundredth, below 0.001 as "P<0.001"; "mean (SD)" rather than "mean ± SD".
- The Lancet: midline decimal point (23·4); "p values should be given to two significant figures, unless p<0·0001".
- European Heart Journal: legend example "P = 0.003" (italic); statistics page "p=0.14" and "p<0.0001" for very small values. The two pages disagree; the preset follows the legend example with a 0.0001 floor.
- EJVES: "p = .043" with no leading zero; 3 decimals for p ≤ .099, 2 decimals for .10 to .99; exact unless < .001; 95% CI values to 2 decimals.
- JEVT: "p=0.XXX", limited to 3 digits.
- Vascular Medicine: exact values with two significant digits ("p = 0.023", "p = 0.58"), "p > 0.99" near 1; odds, risk, and hazard ratios with 2 decimals.
- AHA journals: point estimate, then confidence interval, then the actual P value, at least two significant digits, scientific notation for small values; never "NS".
- JACC family: AMA Manual of Style "with minor modifications"; the instructions do not define the P format, so check a current issue before final formatting.
- No P format stated: EuroIntervention, CCI, The BMJ, Heart, Phlebology, Lymphatic Research and Biology; `generic_lz` (italic P, leading zero) is used and should be checked.

Helpers:
```python
pf.fmt_p(0.0042, "ama", markup="plain")            # 'P = .004'
pf.fmt_p(0.00004, "lancet", markup="plain")        # 'p<0·0001'
pf.fmt_estimate(0.78, 0.65, 0.94, "HR")            # 'HR, 0.78 (95% CI, 0.65-0.94)'
pf.fmt_estimate(0.78, 0.65, 0.94, compact=True)    # '0.78 (0.65-0.94)' for forest columns
pf.rich_text(ax, 0.03, 0.05, [("Log-rank ", "normal")] + pf.fmt_p(0.04, "ama"))  # italic P, live SVG text
```
`fmt_p(..., markup="parts")` returns runs for `rich_text`, which keeps phrases as whole editable text objects in SVG; mathtext (`$\mathit{P}$`) renders glyph by glyph in SVG and fragments editing.

Report statistics with their data: absolute numbers or rates and a measure of uncertainty before the P value (JAMA); absolute as well as relative risk (EHJ, Heart); raw numbers alongside percentages (The BMJ). In tables and legends JAMA writes "No. (%)" and drops decimals in percentages when n < 100.
