# Legends and alt text

The legend makes the figure interpretable without the main text (Scientific-Figure-Design caption test). It is manuscript prose, so the manuscript register applies: complete sentences or phrases, no em dashes (use parentheses, semicolons, or colons), units on every quantity, statistics in the target's house style, abbreviations defined.

## Structure

1. **Title**: a short descriptive phrase naming what is shown (JACC: 10 words or fewer; AHA: short title, not printed on the figure). Descriptive by default ("Cumulative Incidence of the Primary End Point by Treatment Group"); a conclusion-style title only when the journal asks for it.
2. **What each panel shows**, in panel order: population or sample, groups, outcome, time frame.
3. **Encodings**: what points, lines, bars, boxes, whiskers, shading, and colors mean. Name every error bar (SD, SEM, 95% CI, IQR) and every box-plot element (median, IQR, whisker rule).
4. **Numbers**: n per group (AHA: in every figure), events for survival plots, numbers at risk if not in the artwork.
5. **Statistics**: test, model, adjustment covariates, multiplicity handling, exact P values in house style, which analyses were prespecified.
6. **Images**: stain, magnification or scale-bar length (Nature Communications puts scale-bar length in the legend; Scientific Reports on the bar), acquisition details, any nonlinear adjustment, spliced lanes, software used to create illustrations (Vascular Medicine asks for it, for example "Created with BioRender").
7. **Abbreviations**, defined at the end (JACC: alphabetically).

## Limits stated by journals

JACC family: title 10 words or fewer, target 50 to 100 words, maximum 150 words; Central Illustration legend listed last. EHJ graphical abstract legend 80 words or fewer; EHJ Structured Graphical Abstract text up to 40 words per element. BMC: titles 15 words or fewer, legends 300 words or fewer. Check `figure_qa.check_legend_text(text, target, title=...)`, which also flags em dashes, P-value style mismatches, leading-zero errors, undefined error bars, and "mean ± SD" for Annals.

## Template (fill, then cut)

```text
Figure N. [Descriptive title in 10 words or fewer]
(A) [Outcome] in [population] by [group]; points are individual patients and bars are means with 95% CIs (n = [n1] and [n2]).
(B) [Time-to-event outcome] by [group]; shaded bands are pointwise 95% CIs and the table gives numbers at risk. [Effect measure], [value] (95% CI, [lo]-[hi]) from [model, covariates]; [P in house style].
[Any image processing or truncation rule, for example: curves are truncated when fewer than 10 patients remain at risk.]
[ABBREV], [definition]; [ABBREV], [definition].
```

## Alt text

ACM requires a description for every figure (`\Description{}` or `alt=`), EHJ requires "Alt text:" under each caption, and Nature Portfolio and others increasingly request it. Alt text is not the legend:
- one or two sentences on the chart type and the main pattern, then the key numbers a reader needs (for example "Step curves of cumulative incidence over 4 years; the intervention curve lies below control from year 1, reaching 24% versus 37% at 4 years");
- describe what is visible, not the methods;
- no "image of" or "figure showing";
- keep data values consistent with the legend and text.

## Common legend defects

- Error bars undefined, or SEM used to describe spread (Wullschleger et al found this in 64% of 441 articles in three cardiovascular journals).
- n missing, or n given as observations rather than experimental units.
- Abbreviations introduced in the artwork but never defined.
- Different P-value formats between legend, artwork, and text.
- Results that the artwork does not show, or claims stronger than the analysis supports.
