# Color and accessibility

Color encodes meaning; it is never decoration. Color-vision deficiency is common enough that meaning carried by hue alone is lost for a predictable part of every audience: Stevens et al (eLife 2024) judged 12.8% of 4,964 eLife images hard for deuteranopes to interpret.

## Contents
1. Categorical palettes
2. Colormaps for continuous data
3. Checking colors (CVD simulation, CIEDE2000, grayscale, contrast)
4. One palette per paper (palette contract)
5. Audit of the source repositories' default palettes

## 1. Categorical palettes

`pubfig.CATEGORICAL` = Okabe-Ito hues in this order: blue #0072B2, orange #E69F00, black #000000, bluish green #009E73, vermillion #D55E00, sky blue #56B4E9, reddish purple #CC79A7, yellow #F0E442.

Why this order: an exhaustive search over Okabe-Ito orderings found that the first four keep a minimum CIEDE2000 difference of 12.4 under simulated protanopia, deuteranopia, and tritanopia (Machado et al 2009 model) and a minimum lightness difference of 11.8 L* in grayscale. No five-color set from these hues survives grayscale print, so from the fifth series onward add marker shape or line style.

Other verified sets in `pubfig`:
- `OKABE_ITO` (named dict; Wong, Nat Methods 2011, with the 2023 author correction crediting Okabe and Ito).
- `TOL["bright" | "vibrant" | "muted" | "high_contrast" | "light"]` (Paul Tol's schemes; values checked against his `tol-colors` package). `high_contrast` (#004488, #DDAA33, #BB5566) is the best three-color set for grayscale print (min ΔL* 20.3).
- `ARMS`: intervention #0072B2 and control #3B3B3B, separated by ΔE00 above 27 in every condition and ΔL* 21; pair with solid versus dashed lines.
- `NEUTRALS`: ink, muted text, grid, reference line, baseline, band.

Rules:
- Same entity, same color, in every panel and every figure of the paper.
- A strong hue for the focal group or method, neutrals for baselines and context (figures4papers and Scientific-Figure-Design both use this hierarchy).
- Never rely on red versus green alone; journals (Nature, Cell, Science) ask authors to avoid red-green combinations. For two-channel fluorescence use green-magenta (or the target's recommendation).
- Uncertainty bands and fills are tints of the series color (`pf.tint(color, 0.75)`), opaque rather than transparent, so PDF, EPS, and print reproduce them identically.
- Thin lines and small markers in light colors (yellow, sky blue) fall below 3:1 contrast on white; use them for fills or thick marks only.

## 2. Colormaps for continuous data

- Sequential (magnitude): `viridis` (default), `cividis` (optimized for CVD; Nuñez et al 2018), `magma`, `inferno`, or a single-hue ramp (`Blues`, `Greys`).
- Diverging (signed around a meaningful center): `RdBu_r`, `PuOr_r`, `BrBG`, or Crameri's `berlin`, `vanimo`, `managua` (bundled in matplotlib 3.10+). Center the norm at the reference value with symmetric limits (`heatmap(kind="diverging")` uses `TwoSlopeNorm`).
- Forbidden by default: `jet`, `rainbow`, `hsv`, `gist_rainbow`, `nipy_spectral`, `turbo`, `prism`, `flag`. Rainbow maps have uneven lightness steps that create false boundaries and are unreadable with CVD (Borland and Taylor 2007; Crameri, Shephard and Heron 2020). Contrary evidence exists: Reda and Szafir (2021) found multi-hue colormaps that cross many nameable colors improved accuracy in some graphical-inference tasks. The resolution in this skill: multi-hue is fine when lightness rises monotonically and CVD readers can still decode it (viridis, cividis, batlow-like maps); classic rainbow fails both conditions, so `figure_qa` still fails it. Borkin et al (2011) found a perceptual colormap caused fewer diagnostic errors than rainbow in a coronary shear-stress task.
- Record clipping, quantile-based limits (2nd to 98th percentile), or a fixed scientific domain in the legend. A correlation matrix keeps the domain −1 to 1.
- Always include a labeled colorbar with units.

## 3. Checking colors

`pf.check_colors(colors)` reports, for every pair:
- minimum CIEDE2000 (ΔE00) for normal vision and for simulated protanopia, deuteranopia, and tritanopia (Machado et al 2009 matrices, severity 1, applied in linear RGB; verified identical to the colorspacious implementation);
- minimum lightness difference ΔL* (grayscale print);
- colors below 3:1 contrast on white (WCAG 2 non-text contrast).
Thresholds (ΔE00 ≥ 10 for categorical marks, ΔL* ≥ 10 for grayscale) are working heuristics: ΔE00 near 2 is a just-noticeable difference for adjacent patches, and small plot marks need far more separation to be named apart. Treat a warning as a prompt to add redundancy (marker, line style, direct label), not as a verdict.

`figure_qa.py FILE --cvd-preview out.png` writes original, deuteranopia, protanopia, tritanopia, and luminance-only versions side by side. Open it and confirm the claim survives every panel.

Text contrast: at least 4.5:1 against its background (WCAG 2), which Scientific-Figure-Design enforces for diagram text.

## 4. One palette per paper (palette contract)

From Scientific-Figure-Design. A set of attractive figures is not a visual system if the same method, baseline, or status changes color between figures.
- Copy `assets/paper-palette.yaml` into the paper project; set `paper_id` and `palette_id`; assign roles once (`ours`, `strong_baseline`, `other_baselines`, `upper_bound`, `positive`, `negative`, `uncertainty`); set `status: frozen` before the final figures.
- Every plotting script and every draw.io figure reads the same file. `scripts/validate_paper_palette.py --palette paper-palette.yaml figures/*.drawio --strict` audits draw.io figures for drift; the builder embeds the palette ID and SHA-256.
- Derive card fills and bands from the base hue; do not invent new hues for lighter fills.
- Separate eligibility (what `assets/academic-style.yaml` allows: at most five semantic hues, white background, no gradients or shadows) from identity (which allowed color means what in this paper).
- Joining an existing manuscript: inventory current colors, keep the mapping that preserves established reader expectations, repair conflicts rather than averaging them.

## 5. Audit of the source repositories' default palettes

Measured with `check_colors` (minimum ΔE00 across the three simulated dichromacies; ΔL* in grayscale):
- Scientific-Figure-Design semantic palette (accent #2563EB, secondary #7C3AED, ...): accent versus secondary ΔE00 0.5 under deuteranopia, so "ours" and "strong baseline" were indistinguishable to deuteranopes. Replaced in this skill by accent #0072B2, secondary #882255, success #15803D, warning #8C510A, danger #BB5566 (all at least 4.5:1 contrast on white; minimum ΔE00 8.7, limited by the inherent green-versus-red status pair, which the style still requires to carry a label, icon, or line style).
- polish-sci-figures `zhoy_muted`: minimum ΔE00 2.5 (deuteranopia). Not used as a default.
- figures4papers blue-green-red family: minimum ΔE00 6.8 (protanopia), ΔL* 0.3. Kept only as a semantic idea.
- matplotlib `tab10` first four: minimum ΔE00 1.3 (protanopia). Replaced by `CATEGORICAL` in `pubfig.setup`.
