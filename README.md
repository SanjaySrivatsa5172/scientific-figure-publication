# scientific-figure-publication

Figure lane of **scientific manuscript draft bot**. Invoke it as `/scientific-figure-publication`.

The parent bot owns the manuscript. This skill draws the figure, writes the legend, and returns a packet the bot can drop into the draft. It does not write the paper. The handoff is `references/manuscript-bot.md`.

Working rules: `SKILL.md`. Drawing code: `pubfig/`.

```bash
pip install -r requirements.txt
python examples/demo_manuscript.py
```

That writes SVG, PDF, and 300 dpi PNG under `examples/output/`, plus a figure packet addressed to the manuscript bot. It exits non-zero if the acceptance gate fails. Arial is requested. If it is missing, the demo says so and does not call the file submission-ready.

`SOURCE.md` records what was absorbed from Scientific-Figure-Design, figures4papers, and polish-sci-figures, and what was dropped as redundant.
