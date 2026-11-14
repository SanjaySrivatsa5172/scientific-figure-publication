# Image panels

Microscopy, fluorescence, histology, Western blot, electron microscopy, and ultrasound stills. The raster is evidence. Treat it as immutable.

## Required inputs

A CSV manifest with `file` and `output_name`. Add `um_per_pixel` when a scale bar is requested. Add `batch` when acquisition settings differ. A comparison batch shares calibration and display.

```python
from pubfig.images import standardize_batch, duplicate_candidates

standardize_batch("manifest.csv", "derived/", scale_bar_um=20)
```

The script center-crops to a shared canvas, writes derivatives beside an `image_audit.json`, and stores each source SHA-256. It will not overwrite the raw file.

If `scale_bar_um` is set and any row lacks `um_per_pixel`, it stops. Do not borrow calibration from a neighboring file unless the acquisition record says they share it. Do not read print DPI as a scale.

## Display

Default is no tone change. If the batch needs a window, pass the same `min`, `max`, and optional `gamma` for every image. Do not retune the treated group to look darker. Do not erase, clone, or locally enhance a structure. Do not resample to force a size. Crop, and record the box.

Keep the quantitative image or table separate from the pretty derivative. A display stretch is not a measurement.

## Scale bar

Same length and placement inside a comparison set. Center the label on the bar. Pick black or white from the local background. Judge the size at the final panel, not zoomed into the raw file. `standardize_batch` refuses a bar that is tiny or wider than half the frame.

## Duplicates

`duplicate_candidates` reports exact and near average-hash matches for a person to review. Related channels and a reused control can match on purpose. An empty report is not a certificate of uniqueness. Never delete a file because a hash was short.

## Ultrasound and blots, briefly

For a duplex still or a B-mode frame, the scale comes from the machine's recorded calibration, not from a guess at the sector width. Spectral traces that are measurements belong in the data lane, with axes. Do not decorate them into a schematic.

For a blot, keep the uncropped exposure, mark a splice or a reordered lane in the legend, and put densitometry in its own table. Do not invert or window one lane.

Panel letters and interpretive titles stay out of the montage unless the journal demands them at assembly.
