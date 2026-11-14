# Color and the frozen palette

`assets/academic-style.yaml` says what is allowed. `assets/paper-palette.yaml` says which allowed color means which role in this paper. Do not copy hex values from the newest figure into the next one.

## Default roles (Okabe-Ito)

| Role | Hex | Counts as a hue |
| --- | --- | --- |
| Ours | `#0072B2` | yes |
| Strong baseline | `#E69F00` | yes |
| Positive | `#009E73` | yes |
| Negative | `#D55E00` | yes |
| Highlight, one callout | `#CC79A7` | yes |
| Other baselines | `#666666` | no, neutral |
| Ink, grid, canvas | near-black, gray, white | no |

Five hues is the cap. A sixth series gets a marker or a hatch, not a new color. A sequential heatmap is one hue family stretched across a declared domain. It is not a method palette. Do not reuse that ramp to identify methods.

Other named palettes in `assets/palettes.json`:

- `academic_ink`: diagram-first blue, purple, green, red, orange. Same roles.
- `figures4papers`: the blue / green / red house colors. Hatch or label them. Do not rely on red versus green.

## Freeze

1. Assign `ours`, the recurring baseline, success, failure, and the upper bound once.
2. Set `status` to `frozen` and store `digest(roles)`.
3. Every later figure must match that digest. A mismatch is drift, and drift fails.

Derive tints by mixing a role color toward white. Do not invent a pastel cousin. Uncertainty bands are a light tint of the series color, flat, not a gradient mesh.

## Grayscale and color vision

Build the layout with no semantic color first. Then add color. After that, confirm the claim still holds in grayscale and for a reader who cannot separate red and green. Direct labels do more than a clever palette.

Text on a card needs about 4.5:1 contrast against the fill behind it. No pastel ink.
