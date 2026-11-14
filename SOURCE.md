# Sources and what changed

This skill is an original distillation, not a copy of the three repositories.

## qhy991/Scientific-Figure-Design

Kept: the figure contract, grayscale before color, 85 mm and 178 mm canvases, 7 pt floor, five-hue cap, frozen paper palette with a digest, redundant status encoding, prohibited effects, five-second test, caption test, and the rule that a written exception does not silence a validator.

Left out: the arXiv figure miner, the 581-icon catalog, and the Draw.io bridge. Those need extra licenses, a desktop CLI, and a corpus the user did not ask to download. Schematics are editable SVG from a small JSON spec. Role marks are a color rail plus a word, not a third-party icon.

## ChenLiu-1996/figures4papers (`scientific-figure-making`)

Kept: grouped bars with black edges and hatches, trends with a band, vector heatmaps, a legend that does not cover data, direct labels, semantic roles (proposed, improvement, contrast, neutral), live SVG text, 300 dpi (600 for very dense bars), and top/right spines removed.

Changed: the repository often draws on very large inch canvases (`figsize=(45, 12)`) with 15 to 24 pt type and 2 to 3 pt spines. That is readable on a monitor and too heavy, or unreadably small after a journal scales it down. Here, type and stroke are specified at the printed size. `style_for("slide")` and `style_for("poster")` are the only places large type is legal. The house palette `#0F4D92 / #8BCF8B / #B64342` remains available as `figures4papers`, but it is not the default, because green versus red fails many readers without a second encoding.

## zhoy0409-debug/polish-sci-figures

Kept: start from the question and the experimental unit, not from a favorite chart; estimand and 95% interval before a test; identical canvases across a series; no `bbox_inches="tight"` for later assembly; Arial (or one declared family) with live scientific notation; scale bars only from calibration; one display window per comparison batch; raw files immutable; duplicate screening as a review aid; panel letters off by default; separate manuscript, slide, and poster deliveries.

Left out: the Figure Studio desktop app, the 191-template gallery, and the Node discovery engine. Chart choice is a short decision table in `references/data-figures.md`. Survival, dose-response, and ROC are named so they are not faked with a bar chart. They are not reimplemented here.

## Additions

- One router instead of four overlapping skills.
- Okabe-Ito as the default quantitative palette, with a five-hue cap and neutrals that do not count.
- A paired slopegraph and a mean-plus-interval plot, so group comparisons do not default to bars.
- A style gate that fails manuscript mode when type exceeds 11 pt or spines exceed 1.6 pt.
- SHA-256 palette digests and an SVG audit (width, type size, hue families, live text, forbidden effects).
- Average-hash duplicate candidates that refuse to issue a misconduct verdict.
