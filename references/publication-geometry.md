# Publication geometry

Design in the slot the reader will actually see.

| Starting canvas | Width | When |
| --- | --- | --- |
| Single column | 85 mm (acceptable 82 to 90) | one panel, a slopegraph, a small heatmap |
| Double column | 178 mm (acceptable 170 to 190) | grouped comparisons, trends, schematics |
| Slide | the real slide grid, often near 254 mm of content width | talks only |
| Poster | the real poster cell | posters only |

These millimetres are starting canvases, not a journal's official spec. If the user names Nature, Science, JVS, or anyone else, ask for the current author guide or quote the page they provide. Do not fill official sizes in from memory or from a profile name.

## Type and stroke at that size

| | Manuscript | Slide | Poster |
| --- | --- | --- | --- |
| Body | 8 to 9 pt, floor 7 | 14 to 18 pt | 18 to 28 pt |
| Families | one sans, monospace only for code | same | same |
| Sizes on one figure | at most three | at most three | at most three |
| Primary stroke | 0.8 to 1.4 pt | up to 2 pt | up to 1.6 pt is still enough at arm's length if the cell is small; do not exceed the mode preset casually |

`pubfig.style.style_for(mode)` sets this. `final_delivery_allowed` is false when the requested font is missing. Liberation Sans may stand in for a draft. Say so. Do not call the draft the journal file.

Preferred sans: Arial. Fallback stack: Liberation Sans, Helvetica, DejaVu Sans.

## Layout

- One label-height of space between text and unrelated marks.
- Shared scales when the reader must compare panels.
- Equal gutters. Do not let `set_aspect("equal")` shrink one panel of a grid unless the geometry is the data.
- Whitespace groups objects. It is not a leftover to fill.
- Panel letters go on at final assembly, in the margin, only if the target asks for them.

## Export

SVG and PDF are the masters. PNG is the review image, at least 300 dpi, 600 dpi for a very dense bar panel. Final border is zero. Save the declared rectangle. `finalize_figure` does not use a tight bounding box.

Check the PNG at the real width, not zoomed in. Overlap that appears only at final size still fails.
