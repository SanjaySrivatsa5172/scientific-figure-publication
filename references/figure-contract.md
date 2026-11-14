# Figure contract

Copy `assets/figure-contract.json` and fill it before drawing. Required fields:

| Field | What to write |
| --- | --- |
| claim | One sentence. The result, not the chart type. |
| takeaway | What a reader should say after five seconds. |
| mode | `manuscript`, `slide`, or `poster`. |
| lane | `data`, `schematic`, `image`, or `polish`. |
| width_mm | Final slot width. |
| palette_id | Stable name. |
| palette_status | `draft` until the paper mapping is frozen, then `frozen`. |
| palette_digest | SHA-256 of the role map once frozen. `pubfig.palette.digest`. |
| data_provenance | File, experiment, or the word synthetic. |
| design | For data: `paired`, `independent`, `repeated`, or `summary-metric`. |

Also record, when they apply: experimental unit, estimand, uncertainty definition, whether the axis includes zero, whether truncation is disclosed, journal guide citation, and any human waiver.

## Tests before export

Five-second test: can someone name the comparison and which way is better?

Caption test: without the paper, does the caption state the conditions, the unit, the baseline, the uncertainty, and the conclusion?

If either fails, change the figure. Do not bury a broken hierarchy in a longer caption.

## Assumptions

If the claim is ambiguous, write the narrowest claim you can defend and name the assumption in the contract. Do not polish over a missing comparison.
