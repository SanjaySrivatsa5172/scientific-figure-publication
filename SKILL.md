---
name: scientific-figure-publication
description: >
  Figure lane of the scientific manuscript draft bot. Design, draw, and accept
  publication figures for a manuscript in progress: claim-first contract,
  frozen paper palette, physical-size type, estimation and bar and trend and
  heatmap plots, editable SVG schematics, and calibrated image panels. Use for
  /scientific-figure-publication, or when that bot needs a figure, legend,
  plate, method diagram, microscopy or ultrasound panel, or a figure QA pass.
  Do not draft the paper body, cover letter, or reference list. Do not use for
  dashboards or decorative infographics.
---

# Scientific figure publication

This skill is a lane of **scientific manuscript draft bot**. The bot owns the manuscript. This skill owns the figures and the legends that go back into that draft.

If the parent bot is not running yet, still do the work, and address the returned packet to `scientific-manuscript-draft-bot`. Read `references/manuscript-bot.md` for the handoff. Do not write the introduction, methods prose, discussion, or cover letter. If the claim is missing, ask the bot (or the user) for it. Do not invent one to keep the draft moving.

One skill, four lanes. Open a reference only when that lane is in play.

| Lane | Open | Use when |
| --- | --- | --- |
| data | `references/data-figures.md` | tables, metrics, distributions, curves |
| schematic | `references/schematics.md` | method, mechanism, architecture, pipeline |
| image | `references/images.md` | microscopy, blot, histology, ultrasound, EM |
| polish | `references/polish-and-qa.md` | existing artwork, multipanel assembly, export |

Before drawing, read `references/figure-contract.md` and `references/publication-geometry.md`. Before coloring a second figure, read `references/color-and-palette.md`.

## Hard rules

1. One primary claim. A reader should state the takeaway in five seconds.
2. Design at the final physical size. Start from 85 mm or 178 mm. If a journal is named, use its current author guide. Do not invent millimetres from the journal's name.
3. Manuscript text is 8 to 9 pt, never below 7 pt, at most three sizes and two families. Strokes are 0.8 to 1.4 pt. Emphasis stops at 1.6 pt.
4. Slide and poster type may be larger. Do not put a 24 pt face and a 3 pt spine on an 85 mm manuscript canvas. That oversized-canvas habit is slide mode only.
5. At most five semantic hues, plus neutrals. Freeze one paper palette before final Figure 1 to N. The same entity keeps the same color. Status is never color alone: add a label, hatch, marker, or line style.
6. No gradients, glow, glass, bevels, drop shadows, emoji, 3D bars, or decorative dark backgrounds in the submitted figure.
7. Do not invent data, error bars, P values, scale bars, calibrations, or experimental units. Lead with an estimand and an interval. Show raw observations when they exist. Technical replicates are not biological replicates.
8. Deliver SVG or PDF plus a 300 dpi PNG. Keep SVG text live. Do not use `bbox_inches="tight"` on panels that will be assembled later.
9. If the claim fails in grayscale, fix the structure before adding color.
10. Do not use a generative image model for a figure that contains numbers, axes, topology, or labels.

## Workflow

1. Read the parent handoff if one exists (`references/manuscript-bot.md`). Otherwise fill `assets/figure-contract.json`. Narrow a fuzzy claim only by stating the assumption.
2. Pick one lane and one chart grammar.
3. Lock width, height, font, and palette (`assets/palettes.json`, default `okabe_ito`). Reuse the manuscript's frozen palette digest when the bot sends one.
4. Draw with `pubfig`. Set the matplotlib backend before importing pyplot:

```bash
python examples/demo_manuscript.py
python -m pubfig.qa examples/output/paired_slopes.svg --width-mm 85 --contract examples/output/paired_slopes.contract.json
```

5. Run the acceptance list in `references/polish-and-qa.md`. A warning is a failure. A written exception does not silence the gate. Only a person can waive it, and the waiver is recorded.
6. Return a figure packet to the manuscript bot: contract, source, SVG, PDF, 300 dpi PNG, a legend that can sit under the figure without the rest of the paper, provenance, and the validation note. Do not paste the legend into the discussion.

Run commands from this skill directory. Python 3.10+, numpy, matplotlib, and Pillow (`requirements.txt`). The schematic builder and the SVG gate use the standard library plus the palette file.

## What this skill refuses

- Writing or "improving" the manuscript body. That is the parent bot's job.
- A bar of means when the raw distribution can be shown.
- A P value stamped on the art for an exploratory comparison. Keep the test in the analysis record unless the user declares a confirmatory family.
- A scale bar without micrometres per pixel from the acquisition record.
- A different crop, LUT, or gamma per experimental group.
- Panel letters, serial numbers, and conclusions inside reusable artwork, unless the journal or the user explicitly wants them at final assembly.
- Calling a hash match misconduct, or calling an empty duplicate screen proof of uniqueness.

## Sources and changes

`SOURCE.md` names the three repositories this skill absorbs and the contradictions it resolves. Do not preload those repos. The code here is the implementation.
