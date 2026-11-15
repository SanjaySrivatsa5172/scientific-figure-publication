# Machine-learning and computer-science figures

Conference figures follow the template's text width, not a journal column. Presets (values read from the official style files, 2026-11-14):
- NeurIPS (`neurips`): one column, text width 5.5 in (139.7 mm); `half` 68 mm for side-by-side subfigures.
- ICLR (`iclr`): 5.5 in.
- ICML (`icml`): two columns, 3.25 in column (82.55 mm), 6.75 in text (171.45 mm).
- CVPR and ICCV (`cvpr`): 3.28125 in column per `cvpr.sty` (the template prose says 3.25 in), 6.875 in text.
- ACL and ARR (`acl`): A4, 7.7 cm column, 16 cm text.
- ACM sigconf (`acm`): 3.337 in column, 7.006 in text; every figure needs a `\Description` (alt text).
- IEEE journals (`ieee`): 3.5 in and 7.16 in; maximum 7.16 × 8.8 in; text about 9 to 10 pt; readable in grayscale with color and shape redundancy; direct line labels.
Body text in these templates is Times at 9 to 11 pt. Sans-serif figure text is the common practice; matching the template's Times is acceptable if used for every figure. Keep figure text at least 6 to 7 pt after `\includegraphics` scaling, which means drawing at the column or text width (`pf.setup("icml", "single")`) instead of a large canvas.

## Patterns

- **Ablation**: the full method stays visually stable; compare two to five meaningful removals; show uncertainty across seeds; prefer a dot plot with intervals (`pp.dot_plot(..., sort=False, highlight="Full model")`) to bars when values sit in a narrow band; annotate where degradation begins.
- **Training and search dynamics**: separate metrics with different meanings or scales (reward, entropy, gradient norm, clip ratio) into aligned panels with a shared x axis; bands for seed variability (`pp.line_band`); label events (collapse, plateau, phase change, policy update) directly.
- **Benchmarks against baselines**: a visible anchor (1× speedup line, named baseline, theoretical bound, diagonal); categories ordered by the comparison, not alphabetically; one global legend for small multiples; consistent scales across panels.
- **Rooflines**: `pp.roofline(ax, peak, bandwidth, points)`; label the bound, the ridge point, the hardware, the precision, and whether points are measured or predicted.
- **Scaling**: log axes with stated base; aligned small multiples across model sizes or datasets.
- **Embeddings (t-SNE, UMAP, PCA)**: show the supplied coordinates; never recompute or invent clusters; state the method, metric, seed, and preprocessing; distances in t-SNE and UMAP are not quantitative.
- **Radar charts**: only on one shared radial scale (`pp.radar(..., rlim=...)`); figures4papers drew spokes with different ranges, which makes polygon areas incomparable. Prefer a dot plot or small multiples.
- **Concept illustrations** (manifolds, distributions, spheres): label them as schematic; muted fills, saturated accents for the relation that matters; no axes ticks when the axes have no units.
- **Worked examples**: source or problem, intermediate representation, generated artifact; only the 5 to 15 relevant code lines in monospace; corresponding variables or tensor tiles share stable colors; numbered steps.
- **System overviews**: input, core (generation, search, training), execution and verification, left to right; concrete artifacts on the arrows; one bounded feedback loop; see `references/diagrams-and-icons.md`.

## figures4papers house style, adapted

figures4papers (CC BY-NC 4.0) documents a consistent house style: Helvetica or Arial, top and right spines removed, frameless legends, a blue for the proposed method, green tints for improvements, red-pink for alternatives, neutral grays for background categories, black-edged or hatched bars for print, uncertainty bands on curves, a dedicated legend panel, 300 to 600 dpi export. Its ideas are re-implemented here, not copied. Changes and why:
- Its canvases (for example 45 × 12 in with 24 to 36 pt text) only work if the reader's PDF viewer zooms in; at column width the text shrinks to about 4 pt. Draw at the template width instead.
- Its advice to tighten y limits to the data range is correct for points and lines and wrong for bars; truncated bars exaggerate differences. Use dot plots.
- Its alpha-varied ablation bars become muddy in print and EPS; use opaque tints (`pf.tint`).
- Its radar charts rescale each spoke; use one scale.
- Its blue-green-red palette has a minimum CIEDE2000 of 6.8 under simulated protanopia and almost no lightness separation; `pf.CATEGORICAL` keeps the semantic roles with checked colors.
- `tight_layout(pad=2)` plus `bbox_inches="tight"` changes canvas size between figures; `pf.subplots` uses constrained layout inside a fixed canvas.
