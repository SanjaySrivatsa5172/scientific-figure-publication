# Third-party notices

## Source repositories

- **Scientific-Figure-Design** (https://github.com/qhy991/Scientific-Figure-Design, commit d88f87d), MIT License, copyright (c) 2026 qhy991 and contributors. Bundled with modifications: `scripts/build_drawio_figure.py`, `validate_drawio_figure.py`, `export_drawio_figure.py`, `validate_paper_palette.py`, `collect_arxiv_figures.py`, `analyze_visuals.py`, `analyze_agent_figures.py`; `assets/academic-style.yaml`, `paper-palette.yaml`, `drawio-system-overview.json`, `assets/paper-icons/` (with its own LICENSE and THIRD_PARTY_LICENSES.md); `references/ai-agent-evolution-figures.md`; `tests/test_drawio_hardening.py`, `test_bundled_icons.py`, `test_analyze_agent_figures.py`; `examples/drawio-kernel-agent-loop/`. Modifications: color-vision-checked default palette, cairosvg/poppler export fallback, clinical icon set and search hints, catalog counts, nested SKILL.md renamed to GUIDE.md.
- **polish-sci-figures** (https://github.com/zhoy0409-debug/polish-sci-figures, commit 8750662), MIT License, copyright (c) 2026 Wenting Zhou. Its rules and check designs (fixed canvases, font enforcement, scientific typography, collision and grid checks, SVG editability and canvas audits, accessibility audit, source portability, document rendering, image standardization, duplicate screening) are re-implemented in `scripts/figure_qa.py` and `scripts/image_panels.py`. Figure Studio and the template gallery are not included.
- **figures4papers** (https://github.com/ChenLiu-1996/figures4papers, commit 0ddfbd3), Creative Commons Attribution-NonCommercial 4.0. No code or images are copied. Its documented helper API, palette roles, and layout patterns informed `scripts/pubfig_plots.py`, which is an independent implementation. Credit: Chen Liu, figures4papers.

## Icons (assets/paper-icons/library)

- Lucide (https://github.com/lucide-icons/lucide), ISC License; some Feather-derived icons under MIT. Includes 70 icons in `library/fetched/`, 38 of them added on 2026-11-14 (clinical set).
- Tabler Icons (https://github.com/tabler/tabler-icons), MIT License.
- Phosphor Icons (https://github.com/phosphor-icons/core), MIT License.
- Lobe Icons brand marks (https://github.com/lobehub/lobe-icons), MIT License for SVG code; logos and names remain trademarks of their owners. Use only for accurate identification; no implied endorsement.
- Curation derived from Mizar77/ml-paper-icons (MIT).
Full texts: `assets/paper-icons/LICENSE`, `assets/paper-icons/THIRD_PARTY_LICENSES.md`, `assets/paper-icons/library/license-manifest.json`.

## Data and palettes

- Okabe-Ito color set: Okabe M, Ito K, Color Universal Design (J*FLY); popularized by Wong B, Nat Methods 2011.
- Paul Tol color schemes (SRON); values verified against the `tol-colors` package.
- Color-vision simulation matrices: Machado GM, Oliveira MM, Fernandes LAF, IEEE TVCG 2009.
- Journal specification quotes in `assets/journal-specs/` are short excerpts from publicly available author instructions, kept for verification; the instructions remain the publishers' property.
