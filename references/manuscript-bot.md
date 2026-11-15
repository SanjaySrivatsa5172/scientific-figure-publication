# Handoff with the scientific manuscript draft bot

This skill can work as the figure lane of `scientific-manuscript-draft-bot`. The bot owns the manuscript; this skill owns each figure and its legend. When the bot is not running, a session using this skill still returns the packet below, addressed to the bot. This contract was carried over from the first published version of this repository so the bot keeps working.

## Division of labor

The bot: outline, prose, citations, cover letter, journal checklist; decides the claim and the figure's job in the argument; holds the manuscript id, section, and figure number; freezes the paper palette once and reuses its digest; inserts the legend under the figure and the callout in the text.

This skill: one figure or one plate and its legend; refuses a claim it cannot draw without inventing data; holds geometry, palette, statistics, and files; rejects a figure that drifts from the palette digest; does not rewrite the paragraph around the callout. If the bot asks for a results paragraph, return the legend and one suggested callout sentence, and stop.

## Handoff in

The bot passes JSON. Missing fields are asked for, not guessed.

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
  "palette_id": "",
  "palette_digest": "",
  "design": "paired",
  "experimental_unit": "",
  "estimand": "",
  "data_path": "",
  "synthetic": false,
  "neighbors": []
}
```

- `journal`: resolved with `pubfig.preset(...)`. Widths, type, DPI, and formats then come from the verified preset (quotes and URLs in `assets/journal-specs/`). For a journal outside the 42 presets, use the generic preset and ask for `journal_guide` (a quotation or a path the user supplied); never invent a column width from a journal's name.
- `slot`: a preset column (`single`, `onehalf`, `double`) or a width in mm; `slide` and `poster` select presentation or poster mode.
- `palette_id` and `palette_digest`: the frozen paper palette (`assets/paper-palette.yaml` format). Recompute the digest with `scripts/figure_packet.py` (it uses the draw.io pipeline's canonical SHA-256); if it differs from the bot's, stop and report the drift instead of recoloring.
- `neighbors`: figures already bound to the palette, so this figure does not recolor an entity.
- `synthetic`: when true, the artwork carries `pf.synthetic_tag(fig)` and the legend says so.

## Handoff out

`scripts/figure_packet.py` writes `<figure_id>_packet.json` beside the masters:

```json
{
  "to": "scientific-manuscript-draft-bot",
  "from_skill": "scientific-figure-publication",
  "manuscript_id": "",
  "figure_id": "Fig1",
  "section": "results",
  "files": {"pdf": "", "svg": "", "png": "", "tif": "", "source": ""},
  "legend": "",
  "callout": "Figure 1 shows ...",
  "palette_id": "",
  "palette_digest": "",
  "journal_preset": "",
  "qa": "PASS",
  "qa_counts": {"FAIL": 0, "WARN": 0, "REVIEW": 0},
  "qa_open_items": [],
  "limits": []
}
```

- `legend`: the caption, written per `references/legends-and-alt-text.md` and checked with `figure_qa.check_legend_text`.
- `callout`: one sentence the bot may edit into the section.
- `qa`: `PASS` only when `figure_qa.py` reports no FAIL, every WARN is fixed or accepted with a written reason (`--accept CODE=REASON`), and the manual checks in `references/qa-checklist.md` were actually done (`--manual-checks-done`); `REVIEW` when the audit is clean but the manual checks are not confirmed; `FAIL` otherwise, with the reasons in `qa_open_items`.
- `limits`: font substitution, synthetic data, accepted warnings, exploratory statistics, a refused scale bar, or a `[CONFIRM]` value still open, in plain language.

## What the bot must not assume

- A passing gate is not a statistical review.
- The skill will not invent a journal's column width or relabel synthetic output as a study result.
- Panel letters follow the journal preset for multi-panel manuscript figures; a reusable single panel carries none until assembly.
- A `[CONFIRM]` mark or a `DATA CHECK FAILED` line means the figure is not for submission until the bot or the user resolves it.
