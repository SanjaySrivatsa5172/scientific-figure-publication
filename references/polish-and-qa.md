# Polish and acceptance

Use this lane for artwork that already exists, and as the last pass on every other lane.

## Order of work

1. Confirm the file in front of you is the latest data and the latest source. Do not polish an old export.
2. Lock the slot class. Every SVG in that class shares width, height, and viewBox. If the slot changes, redraw. Do not scale the SVG in Word or PowerPoint.
3. One font family, applied to ticks, labels, legends, and colorbars.
4. Remove overlap. Text may not sit on a point, an error bar, a bar, a neighbor label, or a scale bar. Move the label or redraw. Do not shrink type below the floor to squeeze it in.
5. Open the PNG at the real millimetre width.

`python -m pubfig.qa figure.svg --width-mm 85 --mode manuscript --contract figure.contract.json`

The gate fails on: missing contract fields, undeclared synthetic data, a frozen palette without a digest, manuscript width outside 82 to 190 mm with no journal guide, an undisclosed truncated axis, SVG width drift beyond 2.5 mm, type below 7 pt, more than three type sizes, more than five hue families, outlined text, gradients, and filters.

It does not check science. A passing SVG can still have the wrong denominator. Read the contract.

## Do not deliver while any of these is true

- The unit, the pairing, the direction, or the provenance is unverified.
- A manuscript panel contains a title, a conclusion, or a serial number nobody asked for.
- Same-slot files differ in canvas, or they only line up after someone scales them.
- The font is a fallback and the note still says submission-ready.
- Scientific notation is baseline ASCII (`IC50`, `log2`, `x` used as multiply) when the font can do better.
- A raster wrapped in SVG is described as fully editable.
- Image display settings differ inside one comparison batch.
- The real page or slide was never looked at.

## Package

```text
final_figures/    Fig1.svg  Fig1.pdf  Fig1.png
figure_sources/   Fig1.py   source_data.csv
qa/               contract.json  qa.txt
```

Caption and legend live outside the artwork. State material limits in a sentence: font substitution, synthetic data, exploratory statistics, or a scale bar you could not draw.

## Multipanel

Align outer edges and gutters. Same type hierarchy, same stroke weight, same palette digest, same statistical syntax. Letters, if required, go on last, then recheck collisions.

Compare the new figure with the old one at the same physical size. Replace the old one only if the claim is unchanged and the new one is actually easier to read, or if the numbers were wrong and you are correcting them on purpose. Say which.
