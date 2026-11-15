# Chart selection

Choose the chart from the question, the data structure, and the experimental unit. A chart type chosen by habit is the most common source of misleading figures in biomedicine (Weissgerber et al 2015; Riedel et al 2022).

## Decision order (polish-sci-figures, extended)

1. State the claim and the outcome scale (continuous, binary, count, time to event, rank, composition).
2. Identify the experimental unit: the entity randomized or independently sampled (patient, limb, lesion, animal, culture). Cells, fields, vessels within a patient, and repeated measurements are not independent units.
3. Identify pairing, repeated measures, nesting, clustering, censoring, competing events, and missingness.
4. Choose the estimand and its uncertainty (difference in means with 95% CI, hazard ratio, risk difference, AUC).
5. Choose the analysis that matches the design (it may already exist in the user's results).
6. Choose the graphic that shows both the data and the estimand.

Ask the user only for facts the file cannot reveal, typically the experimental unit, pairing, and which comparisons were prespecified.

## Question to form

- Compare a continuous outcome between groups, small n: every observation plus mean with 95% CI (`estimation_plot`); add box or violin only when n per group is at least about 10.
- Same, large n: raincloud (`raincloud`), box plot with points, or ECDF.
- Before and after on the same units: slopegraph (`paired_plot`) plus the mean within-unit change with CI.
- Many groups or methods on one scale, narrow range: Cleveland dot plot with intervals (`dot_plot`), sorted by value or by a meaningful order.
- Counts or proportions: bars from zero (`bar_plot`), or a dot plot of proportions with CIs.
- Trend over time or dose: line with uncertainty band (`line_band`), individual trajectories when units are repeated (`spaghetti_plot`).
- Time to event: step curves with numbers at risk (`km_plot`); competing risks: cumulative incidence (`cumulative_incidence`).
- Effect estimates across subgroups or studies: forest plot (`forest_plot`), ratios on a log axis.
- Agreement between two methods: Bland-Altman (`bland_altman`), not a correlation plot.
- Classification: ROC with AUC and CI (`roc_plot`), PR when outcomes are rare, calibration for risk models.
- Relationship between two continuous variables: scatter with fitted line and confidence band; show the unit-level points.
- Two-dimensional structure (genes by samples, correlation matrix): heatmap with an honest colormap (`heatmap`).
- Composition that sums to a whole: 100% stacked bar per sample or a normalized heatmap. JAMA does not accept stacked bars; use small multiples of proportions there.
- Distribution shape: histogram or ECDF; a density curve only with enough data.
- Individual response ranking: waterfall (`waterfall_plot`).
- Performance against a hardware bound: roofline (`roofline`).

## Encoding accuracy

Cleveland and McGill (1984) ranked elementary perceptual tasks from most to least accurate: position along a common scale; position along nonaligned scales; length, direction, and angle; area; volume and curvature; shading and color saturation. Consequences:
- Put the decisive comparison on a common aligned axis (adjacent points or bars sharing a baseline).
- Prefer dot plots to bars when the range is narrow; prefer bars to pies; avoid area and volume encodings for quantities that must be compared.
- Share axis scales across panels the reader must compare (`small_multiples`).

## Rules that prevent misleading charts

- Bars encode length from zero. A truncated bar axis exaggerates differences; `figure_qa` fails it. Use a dot plot instead of truncating.
- Show distributions for continuous data; a mean and error bar summarize many incompatible datasets (Weissgerber et al 2015).
- Say what the error bars are. SD describes spread; SEM and CI describe precision of the mean; they convey different information (Cumming, Fidler and Vaux 2007; Krzywinski and Altman 2013). Prefer 95% CI for inference; SEM bars invite misreading.
- No 3-D charts: perspective distorts values. In a clinical visualization study, 2-D representations of coronary shear stress were more accurate and efficient than 3-D (Borkin et al 2011).
- Avoid dual y axes: two unrelated scales make slopes and crossings meaningless. Use aligned panels sharing x (polish-sci-figures "aligned series").
- Pie and donut charts: angle and area are read poorly; several journals reject them (JAMA, Annals).
- Radar charts: area depends on axis order, and per-spoke rescaling exaggerates differences. If one is required, use one radial scale for all spokes (`radar(..., rlim=...)`) and say so; prefer dot plots or small multiples.
- Log axes for ratios and multiplicative effects, with ticks at meaningful values (0.5, 1, 2), labeled in natural units.
- Order categories by the analytical question (control first, then increasing dose; or sorted by effect), not alphabetically.
- One claim per figure. Supporting panels answer sub-questions with the same visual grammar.
- Remove decoration that encodes nothing: background fills, heavy gridlines, drop shadows, gradients, chart junk.

## Small samples and replicates

- Show every observation when n is small; do not draw a density or violin for a handful of points.
- Aggregate technical replicates to the experimental unit before plotting the inferential summary, or show the hierarchy (units as large points, replicates as small points).
- For paired designs, show the pairing; unpaired displays of paired data throw away the design.

## Statistics on the figure

- Lead with the effect estimate and its CI; a P value supports it, it does not replace it (Wasserstein and Lazar, ASA statement on P values, 2016; AHA instructions order estimate, CI, then actual P).
- Print exact P values in the target's house style (`pf.fmt_p`), not asterisks. If asterisks are unavoidable (dense blots), define them in the legend.
- Draw comparison brackets only for prespecified, tested comparisons (`pp.sig_bracket` stacks them without collisions). A global test does not license pairwise brackets.
- Distinguish raw P, adjusted P, and q values; state the adjustment method in the legend.

## Patterns kept from figures4papers (corrected)

- Semantic color roles: one strong hue for the proposed method or intervention, neutrals for baselines and context, a second hue for the strongest competitor. Kept, with CVD-checked colors (`references/color-and-accessibility.md`).
- Dedicated legend panel in dense grids (`legend_panel`). Kept; direct labels are still preferred when space allows.
- Black bar edges and hatching for grayscale-safe bars. Kept as options (`bar_plot(edgecolor=..., hatches=...)`).
- Value labels above bars. Kept sparingly (`value_labels=True`), at tick-label size, never 36 pt.
- Uncertainty bands on training curves. Kept, drawn as opaque tints instead of alpha so PDF, EPS, and print agree.
- Changed: "tighten y limits to the data range" applies to points and lines only; bars start at zero.
- Changed: oversized canvases (for example 45 × 12 in with 24 pt text) shrink to illegible type at column width; build at final size instead (`figure_qa` reports the effective size after scaling).
- Changed: hiding category tick labels and relying on a legend forces look-up; label categories on the axis or directly.
