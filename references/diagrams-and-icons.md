# Diagrams and icons

Method overviews, system architectures, study-design schemas, mechanism diagrams, central illustrations, and visual abstracts. Most of this file distills Scientific-Figure-Design (MIT); its scripts are bundled unchanged except for the color-vision-checked palette and a pure-Python export fallback.

## Contents
1. Design before drawing
2. Archetypes and composition
3. Arrow, shape, and type grammar
4. Choosing the production path
5. Icon composer (SVG/PDF/PNG without draw.io)
6. Editable draw.io pipeline
7. Icons: selection, licenses, clinical set
8. Summary graphics for journals

## 1. Design before drawing

- Write the figure sentence: "This figure shows that [mechanism or comparison] transforms or relates [inputs] into [outcome] under [constraint]." If you cannot write it, do not draw yet.
- Semantic inventory: entities (patients, devices, data, models), transformations (randomize, treat, measure, train), states (candidate, verified, failed), boundaries (trial arms, sites, trust or device boundaries), evidence (metrics, results), relations (data flow, control, feedback, comparison). Represent different classes differently; do not draw every item as the same card.
- Grayscale skeleton first: reading order, hierarchy, the main path, the anchor. If it fails in grayscale, fix the structure.
- One primary claim; three to five major stages in the main scan; the novel component visually dominant; context and baselines neutral.

## 2. Archetypes and composition

- Ordered transformations: pipeline (left to right for processes, top to bottom for hierarchies).
- Components and interfaces: layered architecture.
- Iteration or control: one bounded feedback loop in its own corridor, not long return arrows across the figure.
- A versus B: mirrored comparison with identical geometry.
- Repeated configurations or ablations: aligned grid.
- Taxonomy or dependency: tree.
- Evidence for a claim: chart plus callouts, never icons standing in for numbers.
- Study design (clinical): population, allocation, intervention and comparator, follow-up, outcomes, left to right, with n at each step.
- Self-evolving or agent loops: `references/ai-agent-evolution-figures.md`.
Starting proportions: overviews about 2:1, double column; single column only for genuinely simple diagrams.

## 3. Arrow, shape, and type grammar

- Solid arrow: primary data or execution flow. Dashed: feedback, optional, supervisory, or failure path. Thin neutral line: dependency or grouping. Double-headed: symmetric exchange only.
- Label any non-obvious edge with a short relation; keep labels off arrowheads and node interiors; arrowheads stop at the target boundary.
- Rounded rectangles for modules, not for data bars or axes. Containers only for real ownership, phase, device, or trust boundaries.
- Parallel phrasing: "Collect → Filter → Train → Evaluate", not "Data collection → Filtering stage → We train".
- One sans-serif family; monospace only for code; at least 7 pt at final size (8 to 9 pt for main labels); panel labels 8 pt or larger; no all-caps labels, no paragraphs inside nodes.
- Strokes 0.8 to 1.4 pt, emphasis up to 1.6 pt; no gradients, shadows, glass, faux 3-D, comic styles, emoji, dark backgrounds, or decorative illustration (`assets/academic-style.yaml`; the strict validators fail them).

## 4. Choosing the production path

- Matplotlib: anything data-bound (the rest of this skill), and simple flow charts (`pc.flow_diagram`).
- Icon composer: structured pipelines, grids, and loops that must look consistent, exported as SVG, PDF, and PNG without draw.io.
- draw.io: editable, irregular, or dense layouts the user will keep editing.
- Graphviz or Mermaid: topology-first diagrams under version control.
- TikZ: exact LaTeX typography and equation alignment.
- Illustrator, Inkscape, Affinity, Figma, BioRender: free-form illustration; keep text live and export vector.
- Do not use generative image tools for final figures containing numbers, axes, formulas, anatomy claims, or topology; several journals forbid generative AI in scientific images (NEJM, JAMA, Nature, Science Advances, Cell).

## 5. Icon composer

```bash
ICONS="$SKILL_DIR/assets/paper-icons"
cp "$ICONS/assets/templates/pipeline.json" trial-schema.json        # or grid / feedback-loop
python3 "$ICONS/scripts/search_icons.py" "injection drug" --limit 5   # semantic search
python3 "$ICONS/scripts/compose_figure.py" trial-schema.json --out fig.svg --pdf fig.pdf --png fig.png
python3 "$ICONS/scripts/validate_figure.py" fig.svg
python3 "$SKILL_DIR/scripts/figure_qa.py" fig.pdf --target jacc --column double
```
Spec format: `assets/paper-icons/references/spec-schema.md` (nodes with `id`, `label`, optional `subtitle`, `icon`, `tone` of neutral, accent, secondary, success, warning, danger; edges with `from`, `to`, optional `label` and `style`; layouts `pipeline`, `grid`, `freeform`; `figure.column` single or double). Keep labels to two short lines; the validator warns when a label may overflow its node. PDF export uses `rsvg-convert` when installed, otherwise `cairosvg`; the PNG is rasterized from the vector PDF with poppler when available.

## 6. Editable draw.io pipeline

```bash
cp "$SKILL_DIR/assets/drawio-system-overview.json" figure-spec.json      # edit nodes, edges, groups
cp "$SKILL_DIR/assets/paper-palette.yaml" paper-palette.yaml             # set paper_id; freeze before finals
python3 "$SKILL_DIR/scripts/build_drawio_figure.py" figure-spec.json --paper-palette paper-palette.yaml --out figure.drawio
python3 "$SKILL_DIR/scripts/validate_drawio_figure.py" figure.drawio --paper-palette paper-palette.yaml --strict
python3 "$SKILL_DIR/scripts/export_drawio_figure.py" figure.drawio --mode preview      # needs draw.io desktop
python3 "$SKILL_DIR/scripts/export_drawio_figure.py" figure.drawio --mode final --formats svg,pdf,png
python3 "$SKILL_DIR/scripts/validate_paper_palette.py" --palette paper-palette.yaml figures/*.drawio --strict
```
- The builder embeds icons as vector data URIs, distributes connector ports, binds the palette ID and SHA-256, and writes an icon manifest (`figure.icons.json`) with sources and hashes.
- Strict validation fails sub-7 pt text, more than three type sizes, mixed fonts, illegible strokes, more than five semantic hues, mixed icon families, out-of-scale icons, forbidden effects, hidden text, bad edge endpoints, and unbound or drifted palettes. A documented exception in the figure contract does not pass the gate; only an explicit human-reviewed waiver does.
- Export needs the draw.io desktop CLI. Without it, deliver the validated `.drawio` file and let the user export from draw.io (desktop or app.diagrams.net); do not substitute a raster.
- Regenerate from the spec for topology changes; patch the `.drawio` XML for isolated label, color, or size edits.

## 7. Icons

- Icons are semantic anchors, at most one per node, 20 to 32% of node height, one family per figure (Lucide or Tabler outline for technical figures). Omit an icon that adds nothing; never replace a number or code with a pictogram.
- Library: 580 SVG icons (`assets/paper-icons/library/catalog.json`): Lucide (ISC), Tabler (MIT), Phosphor (MIT), project originals (MIT), plus 70 on-demand Lucide icons including a clinical set added for this skill (heart, heart-pulse, heart-crack, scan-heart, syringe, pill, pill-bottle, hospital, ambulance, bed, droplet, test-tube, clipboard-list, clipboard-check, user-round, users-round, person-standing, footprints, timer, calendar-days, shield-plus, bandage, weight, cigarette, baby, radiation, monitor-dot, circle-check, circle-x, triangle-alert, bone, eye, ear, thermometer, scale, file-text, flask-conical, hand-heart). Fetch more Lucide icons with `scripts/fetch_icon.py NAME` (network needed), which rebuilds the catalog.
- No vendor or product logos are bundled (removed in v1.0.1; the icon licenses do not cover trademarks). Identify a product, framework, or vendor with a text label. If a logo is unavoidable, the author obtains it from the owner and follows the owner's brand guidelines; no implied endorsement; no trial logos in JACC figures.
- Record every icon's source and license in the figure's provenance note. For anatomical or biomedical illustration libraries outside this bundle, check the license of each item before use (attribution terms differ), and name the software when the journal asks (Vascular Medicine: for example "Created with BioRender").

## 8. Summary graphics for journals

Canvas sizes and content rules for central illustrations, visual abstracts, and graphical abstracts are in `references/clinical-figures.md` section 7 (JACC family, AHA journals, EHJ, EuroIntervention, JVS, JEVT, CCI, Elsevier, Cell). Build them with the composer or draw.io at the stated canvas, keep every number identical to the paper, and check the result at thumbnail size: if the main finding is unreadable at 500 × 200 px (the Elsevier display window), simplify.
