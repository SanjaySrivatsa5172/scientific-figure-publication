# Corpus mining: learning a field's visual conventions

From Scientific-Figure-Design. Use it to study how figures in a target venue or subfield are built before designing new ones, or to audit a set of related papers.

## Collect

arXiv HTML preserves figure grouping, captions, subfigures, alt text, and linked assets; prefer it to PDF.
```bash
python "$SKILL_DIR"/scripts/collect_arxiv_figures.py --readme paper-list.md --output-dir corpus --workers 4
python "$SKILL_DIR"/scripts/collect_arxiv_figures.py --id 2401.01234 --output-dir corpus
python "$SKILL_DIR"/scripts/collect_arxiv_figures.py --id-file missing-ids.txt \
    --html-base-url https://ar5iv.labs.arxiv.org/html --output-dir corpus/fallback/ar5iv
```
Needs `requests` and `beautifulsoup4` and network access to arxiv.org. Keep `papers.json`, `figures.jsonl`, `summary.json`, each paper's `manifest.json`, `source.html`, and original assets. Do not claim full coverage until every paper has an HTML manifest or a documented PDF fallback.

Clinical and biomedical journals are rarely on arXiv. For those, collect figures manually from open-access articles (PubMed Central) the user is entitled to read, keep the source URL and license of each, and use them only as private references; do not redistribute published figures.

## Measure

```bash
python "$SKILL_DIR"/scripts/analyze_visuals.py --root corpus --output-dir corpus/analysis        # needs Pillow, cairosvg
python "$SKILL_DIR"/scripts/analyze_agent_figures.py --root corpus --output-dir corpus/analysis/agent-audit
```
Useful measurements: coverage by provider, figure and asset counts, formats, median aspect ratio by figure type, white, grayscale, dark, and saturated pixel fractions, direct tool metadata, panel counts, final-size text and stroke dimensions. Contact sheets grouped by a caption taxonomy support visual review.

## Interpret honestly

- Separate three evidence levels: direct evidence (SVG metadata, PNG software tags, source files, captions); structural observation (aspect ratio, panel count, whitespace, saturation); visual inference (a likely tool or authoring method). Never report an inference as a fact.
- Asset count is not figure count; a figure can hold many subfigure assets.
- Caption-derived classes and role tags are review aids, not ground truth or quality scores.
- Publish counts, fallbacks, errors, and caveats with any conclusion; confirm patterns on contact sheets.
