# Parent: scientific manuscript draft bot

This skill does not stand alone in the drafting system. The parent bot is `scientific-manuscript-draft-bot`. It will call `/scientific-figure-publication` when a draft needs a figure. Until that bot exists, any session using this skill still returns the packet below, addressed to that bot.

## Division of labor

| Scientific manuscript draft bot | This skill |
| --- | --- |
| Outline, prose, citations, cover letter, journal checklist | One figure, or one plate, and its legend |
| Decides the claim and the figure's job in the argument | Refuses a claim it cannot draw without inventing data |
| Holds the manuscript id, section, and figure number | Holds geometry, palette, statistics, and files |
| Freezes the paper palette once, then reuses the digest | Rejects a figure that drifts from that digest |
| Inserts the legend under the figure and the callout in the text | Does not rewrite the paragraph around the callout |

If the parent asks this skill to draft a results paragraph, return the legend and a single suggested callout sentence, and stop.

## Handoff in

The parent should pass JSON. Missing fields are asked for, not guessed.

```json
{
  "from": "scientific-manuscript-draft-bot",
  "manuscript_id": "",
  "figure_id": "Fig1",
  "section": "results",
  "claim": "",
  "takeaway": "",
  "journal": "",
  "journal_guide": "",
  "mode": "manuscript",
  "slot": "single",
  "palette_id": "okabe-ito-manuscript-v1",
  "palette_digest": "",
  "design": "paired",
  "experimental_unit": "",
  "estimand": "",
  "data_path": "",
  "synthetic": false,
  "neighbors": []
}
```

`slot` is `single` (85 mm), `double` (178 mm), `slide`, or `poster`. A named journal does not imply a width. `journal_guide` is a quotation or a path the user supplied.

`neighbors` lists other figures already bound to the palette, so this figure does not recolor `ours`.

## Handoff out

Write `figure_packet.json` beside the masters.

```json
{
  "to": "scientific-manuscript-draft-bot",
  "from_skill": "scientific-figure-publication",
  "manuscript_id": "",
  "figure_id": "Fig1",
  "section": "results",
  "files": {"svg": "", "pdf": "", "png": "", "source": ""},
  "legend": "",
  "callout": "Figure 1 shows ...",
  "palette_id": "",
  "palette_digest": "",
  "qa": "PASS",
  "limits": []
}
```

`legend` is the caption. `callout` is one sentence the parent may edit into the section. `limits` is where font substitution, synthetic data, exploratory statistics, or a refused scale bar are stated in plain language. `qa` is `PASS` only when `python -m pubfig.qa` is clean and the scientific checks in `polish-and-qa.md` were actually done.

## What the parent must not assume

- A passing gate is not a statistical review.
- The skill will not invent a journal's column width.
- The skill will not relabel synthetic demo output as a study result.
- Panel letters are off unless the parent asks at final assembly.
