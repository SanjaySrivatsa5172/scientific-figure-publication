# Data figures

Read the table before asking questions. Ask only for facts the file cannot show: pairing, the experimental unit, the reference group, and whether the analysis was confirmatory.

## Which mark

| You have | Draw | Do not draw |
| --- | --- | --- |
| Individual observations, 2 to 5 groups, independent | Points, mean, 95% t interval | A bar that hides the points |
| Complete pairs | Slopegraph, one line per unit, mean on top | Unpaired dots that drop the pairing |
| Aggregated scores (accuracy, F1) where the unit is a metric, not a subject | Grouped bars, black edges, hatch for the second and later series | A fake distribution |
| A run over time | Few lines, markers that differ, a flat uncertainty band if one exists | A smoothed line that hides the replicates |
| A matrix | Vector cells, declared vmin and vmax, one sequential ramp | A rainbow, or a raster heatmap if the SVG must stay editable |
| Composition | Normalized stacks only when every sample's total is the denominator | A pie |
| Survival, dose-response, ROC, volcano | Only from the real columns (time and event, dose and response, label and score, supplied statistics) | A bar chart wearing that name |

If the specialist family is required and the columns are missing, stop. Do not impute the model.

## Statistics the figure may claim

- Report the estimand and the interval. Default interval: Student t 95% on the mean, or on the paired difference.
- For two independent groups the honest default is a difference in means with that interval. Welch or a rank test belongs in the analysis record, as a named sensitivity, not as stars.
- Do not choose the test because a tiny normality check crossed 0.05.
- Do not turn an omnibus test into pairwise letters.
- Exploratory P values stay off the art. Print an exact italic *P* only after the user says the comparison was confirmatory.
- n in the caption is the experimental unit. Technical replicates stay nested.
- Synthetic numbers stay labeled synthetic in the contract and the caption.

`pubfig.plots` implements `make_paired_slopes`, `make_estimation`, `make_grouped_bar`, `make_trend`, and `make_heatmap`. It checks that series lengths match. It does not compute a P value.

## Axes

Include zero for a bar of a quantity that has a meaningful zero, unless the contract says the claim is about a small gap. Then set `axis_includes_zero` false, `truncation_disclosed` true, and write the floor on the figure ("Axis starts at 0.60"). A quiet zoom is not allowed.

Order categories by the comparison the reader should make. Put the reference first unless the user has an order.

No dual axis. Split the panels. No 3D bars.

## Notation

Italicize the symbol, not the sentence: *P*, *n*, *r*. Use real subscripts and superscripts when the font has them: IC50 is wrong if you can write IC₅₀, log2 is wrong if you can write log₂. Use `×`, `−`, `±`, `≤`, `≥`. Put a space between a value and its unit.

Gene and protein case follow the organism. If you are not sure, keep the source label.

## Recipe

```python
import matplotlib
matplotlib.use("Agg")
from pubfig.palette import load_palette
from pubfig.plots import finalize_figure, make_paired_slopes, new_figure
from pubfig.style import style_for

style = style_for("manuscript", width_mm=85)
fig, ax = new_figure(style, 70)
make_paired_slopes(ax, before, after, ["Before", "After"], load_palette()["roles"]["ours"], "Time (s)")
finalize_figure(fig, "figures/fig1", formats=["svg", "pdf", "png"], dpi=300)
```

`new_figure` turns millimetres into inches and applies the style. Do not pass `figsize=(45, 12)` for a journal column.
