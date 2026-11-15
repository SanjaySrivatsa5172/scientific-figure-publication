"""Regression tests for pubfig, pubfig_plots, pubfig_clinical, figure_qa, image_panels.

Reference values were computed once with independent libraries (lifelines 0.30,
scikit-learn, colorspacious, colour-science) and are hard-coded here so the
tests need only numpy, scipy, matplotlib, Pillow (pypdf optional).
Run: python -m unittest discover -s tests
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
warnings.simplefilter("ignore")

import pubfig as pf  # noqa: E402
import pubfig_plots as pp  # noqa: E402
import pubfig_clinical as pc  # noqa: E402
import figure_qa as qa  # noqa: E402
import image_panels as ip  # noqa: E402


def codes(findings, severity=None):
    return {f.code for f in findings if severity is None or f.severity == severity}


class Presets(unittest.TestCase):
    def test_required_keys(self):
        for key, p in pf.PRESETS.items():
            for k in ("name", "widths_mm", "font", "type", "lines", "panel", "dpi", "stats"):
                self.assertIn(k, p, f"{key} lacks {k}")
            self.assertIn(p["stats"], pf.STATS_STYLES, key)

    def test_verified_widths(self):
        self.assertEqual(pf.preset("Nature")["widths_mm"]["double"], 183)
        self.assertEqual(pf.preset("Cell Reports")["widths_mm"]["onehalf"], 114)
        self.assertEqual(pf.preset("elsevier")["widths_mm"]["double"], 190)
        self.assertEqual(pf.preset("PNAS")["widths_mm"]["single"], 87)
        self.assertAlmostEqual(pf.preset("IEEE")["widths_mm"]["single"], 88.9)
        self.assertNotIn("onehalf", pf.preset("ehj")["widths_mm"])  # never inherit unstated widths

    def test_aliases(self):
        self.assertEqual(pf.preset("Circulation")["name"], pf.PRESETS["aha"]["name"])
        self.assertEqual(pf.preset("JACC: Cardiovascular Interventions")["name"], pf.PRESETS["jacc_family"]["name"])
        self.assertEqual(pf.preset("Journal of Vascular Surgery")["name"], pf.PRESETS["jvs"]["name"])
        with self.assertRaises(KeyError):
            pf.preset("no such journal")


class StatsStyles(unittest.TestCase):
    CASES = {
        "ama": {0.5: "P = .50", 0.0042: "P = .004", 0.0004: "P < .001", 0.995: "P > .99"},
        "nejm": {0.5: "P=0.50", 0.0042: "P=0.004", 0.0004: "P<0.001"},
        "annals": {0.2: "P=0.200", 0.35: "P=0.35", 0.0004: "P<0.001"},
        "lancet": {0.046: "p=0·046", 0.00004: "p<0·0001"},
        "ejves": {0.043: "p = .043", 0.24: "p = .24", 0.0004: "p < .001"},
        "jevt": {0.5: "p=0.500"},
        "vascmed": {0.023: "p = 0.023", 0.58: "p = 0.58", 0.995: "p > 0.99"},
        "aha": {0.046: "P = 0.046", 0.00041: "P = 4.1 × 10⁻⁴"},
    }

    def test_house_styles(self):
        for style, cases in self.CASES.items():
            for p, expected in cases.items():
                self.assertEqual(pf.fmt_p(p, style, markup="plain"), expected, f"{style} {p}")

    def test_ci_and_estimates(self):
        self.assertEqual(pf.fmt_estimate(0.78, 0.65, 0.94, "HR"), "HR, 0.78 (95% CI, 0.65-0.94)")
        self.assertEqual(pf.fmt_ci(-0.2, 1.8, 1), "95% CI, −0.2 to 1.8")
        self.assertEqual(pf.fmt_p(0.03, "ama", markup="parts"), [("P", "italic"), (" = .03", "normal")])

    def test_notation(self):
        self.assertEqual(pf.notation("IC50 and log2 fold, CO2"), "IC₅₀ and log₂ fold, CO₂")


class Color(unittest.TestCase):
    def test_cvd_matches_colorspacious(self):
        ref = {  # colorspacious sRGB1+CVD severity 100 (Machado 2009)
            (1, 0, 0): [[0.426608, 0.372654, 0.0], [0.64006, 0.565807, 0.0], [1.0, 0.0, 0.058386]],
            (0.5, 0.3, 0.8): [[0.0, 0.412783, 0.815751], [0.050725, 0.407007, 0.789181], [0.430378, 0.410732, 0.522183]],
        }
        for col, rows in ref.items():
            for kind, exp in zip(("protanopia", "deuteranopia", "tritanopia"), rows):
                got = np.clip(pf.simulate_cvd(np.array(col, float), kind), 0, 1)
                np.testing.assert_allclose(got, exp, atol=2e-6)

    def test_ciede2000_sharma(self):
        pairs = [((50, 2.6772, -79.7751), (50, 0, -82.7485), 2.0425),
                 ((50, 0, 0), (50, -1, 2), 2.3669),
                 ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644)]
        for a, b, e in pairs:
            self.assertAlmostEqual(float(pf.delta_e2000(a, b)), e, places=4)

    def test_default_palette_first_four_safe(self):
        r = pf.check_colors(pf.CATEGORICAL[:4])
        self.assertTrue(r["pass"])
        self.assertGreaterEqual(r["grayscale"]["min_delta_L"], 10)

    def test_repo_palette_failure_is_detected(self):
        r = pf.check_colors(["#2563EB", "#7C3AED"])  # original SFD accent vs secondary
        self.assertFalse(r["pass"])


class Survival(unittest.TestCase):
    def test_km_hand_computed(self):
        km = pc.kaplan_meier([1, 2, 2, 3, 4, 5], [1, 1, 0, 1, 0, 1])
        np.testing.assert_allclose(km.surv, [1, 5 / 6, 2 / 3, 4 / 9, 4 / 9, 0], atol=1e-12)
        self.assertEqual(list(km.n_risk), [6, 6, 5, 3, 2, 1])

    def test_logrank_reference(self):
        rng = np.random.default_rng(42)
        n = 120
        g = np.repeat([0, 1], n // 2)
        t = np.round(rng.exponential(np.where(g == 0, 10, 16)), 1)
        c = rng.uniform(5, 25, n)
        e = (t <= c).astype(int)
        t = np.minimum(t, c)
        r = pc.logrank_test(t, e, g)
        self.assertAlmostEqual(r["chi2"], 12.127077788820499, places=8)  # lifelines 0.30
        self.assertAlmostEqual(r["p"], 0.0004969493054686045, places=10)

    def test_cif_identity(self):
        rng = np.random.default_rng(3)
        t = rng.integers(1, 40, 300).astype(float)
        s = rng.choice([0, 1, 2], 300, p=[0.4, 0.35, 0.25])
        _, c1 = pc.cumulative_incidence(t, s, 1)
        _, c2 = pc.cumulative_incidence(t, s, 2)
        km = pc.kaplan_meier(t, (s > 0).astype(int))
        np.testing.assert_allclose(c1 + c2, 1 - km.surv, atol=1e-12)

    def test_auc_delong_reference(self):
        rng = np.random.default_rng(42)
        g = np.repeat([0, 1], 60)
        rng.exponential(np.where(g == 0, 10, 16)); rng.uniform(5, 25, 120)  # advance as in the reference run
        y = rng.integers(0, 2, 200)
        s = y * 0.9 + rng.normal(0, 1, 200)
        st = pc.auc_delong(y, s)
        self.assertAlmostEqual(st["auc"], 0.6856597326901819, places=12)  # scikit-learn
        self.assertAlmostEqual(st["se"], 0.03752631566402746, places=12)


class CanvasAndExport(unittest.TestCase):
    def test_exact_canvas_and_files(self):
        spec = pf.setup("jacc", "single", aspect=0.75)
        fig, ax = pf.subplots(spec)
        ax.plot([0, 1], [0, 1])
        ax.set_xlabel("Time (y)")
        ax.set_ylabel("Risk (%)")
        with tempfile.TemporaryDirectory() as td:
            rep = pf.save(fig, Path(td) / "f", ["pdf", "png", "tif", "svg"], quiet=True)
            self.assertFalse([p for p in rep["problems"] if "SIZE" in p])
            size = pf._pdf_page_mm(Path(td) / "f.pdf")
            self.assertAlmostEqual(size[0], 90.0, delta=0.3)
            from PIL import Image
            im = Image.open(Path(td) / "f.tif")
            self.assertEqual(im.mode, "RGB")
            self.assertEqual(im.info.get("compression"), "tiff_lzw")
            self.assertLessEqual(abs(im.size[0] - 90 / 25.4 * spec.preset["dpi"]["line"]), 1.0)  # Agg truncates to whole pixels
            F = qa.audit_file(Path(td) / "f.pdf", target="jacc", column="single")
            self.assertNotIn("TYPE3_FONT", codes(F))
            self.assertNotIn("FONT_NOT_EMBEDDED", codes(F))
        plt.close(fig)


class QAChecks(unittest.TestCase):
    def test_bad_figure_fails(self):
        spec = pf.setup("generic", "single")
        fig, axes = pf.subplots(spec, 1, 2)
        axes[0].bar(["A", "B"], [0.91, 0.89])
        axes[0].set_ylim(0.85, 0.95)
        axes[1].imshow(np.random.default_rng(0).random((5, 5)), cmap="jet")
        axes[1].text(0.5, 0.5, "tiny", fontsize=4, transform=axes[1].transAxes)
        axes[1].text(0.5, 0.5, "overlap", fontsize=7, transform=axes[1].transAxes)
        F = qa.audit_figure(fig)
        fails = codes(F, "FAIL")
        for c in ("TRUNCATED_BARS", "RAINBOW_CMAP", "TEXT_TOO_SMALL", "TEXT_COLLISION"):
            self.assertIn(c, fails)
        plt.close(fig)

    def test_clean_figure_passes(self):
        spec = pf.setup("generic", "single")
        fig, ax = pf.subplots(spec)
        pp.estimation_plot(ax, {"A": np.arange(10.0), "B": np.arange(10.0) + 3}, ylabel="Value (units)")
        F = qa.audit_figure(fig)
        self.assertEqual(codes(F, "FAIL"), set())
        plt.close(fig)

    def test_journal_rules(self):
        spec = pf.setup("jama", "single")
        fig, ax = pf.subplots(spec)
        ax.bar([0, 1], [3, 4])
        ax.bar([0, 1], [1, 2], bottom=[3, 4])
        F = qa.audit_figure(fig)
        self.assertIn("JOURNAL_NO_STACKED_BARS", codes(F, "FAIL"))
        plt.close(fig)

    def test_type3_pdf_detected(self):
        with tempfile.TemporaryDirectory() as td:
            with matplotlib.rc_context({"pdf.fonttype": 3}):
                fig, ax = plt.subplots(figsize=(3.35, 2.5))
                ax.set_title("x")
                fig.savefig(Path(td) / "t3.pdf")
                plt.close(fig)
            try:
                import pypdf  # noqa: F401
            except ImportError:
                self.skipTest("pypdf not installed")
            self.assertIn("TYPE3_FONT", codes(qa.audit_file(Path(td) / "t3.pdf")))

    def test_portability(self):
        with tempfile.TemporaryDirectory() as td:
            s = Path(td) / "fig.py"
            s.write_text('fig.savefig("a.pdf", bbox_inches="tight")\ndf = load("/home/someone/data.csv")\n')
            F = qa.check_portability(s)
            self.assertGreaterEqual(sum(f.severity == "FAIL" for f in F), 2)

    def test_legend_checker(self):
        F = qa.check_legend_text("Survival — by group. Error bars shown. p = 0.03.", "jacc",
                                 title="An overly long legend title that clearly runs past the ten word limit here")
        self.assertTrue({"EM_DASH", "LEGEND_TITLE_TOO_LONG", "P_STYLE", "ERRORBARS_UNDEFINED"} <= codes(F))


class Clinical(unittest.TestCase):
    def test_consort_count_check(self):
        spec = pf.setup("generic", "double")
        counts = dict(assessed=100, excluded=10, randomized=80, allocated={"Intervention": 40, "Control": 40},
                      lost={"Intervention": 0, "Control": 0}, analysed={"Intervention": 40, "Control": 40})
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            fig, _ = pc.consort_diagram(spec, counts)
            self.assertTrue(any("inconsistent" in str(x.message) for x in w))
        plt.close(fig)

    def test_forest_and_km_render_without_fail(self):
        spec = pf.setup("generic", "double")
        rows = [dict(label="Overall", est=0.8, lo=0.7, hi=0.92, summary=True, cols=("10/100", "20/100")),
                dict(label="Age", header=True),
                dict(label="< 65 y", est=0.75, lo=0.6, hi=0.95, indent=1, weight=50, cols=("5/50", "10/50"), p_text=".40")]
        fig, _ = pc.forest_plot(spec, rows, col_titles=("A", "B"), xticks=[0.5, 1, 1.5], xlim=(0.45, 1.6),
                                favours=("Favors A", "Favors B"))
        self.assertEqual(codes(qa.audit_figure(fig), "FAIL"), set())
        plt.close(fig)
        rng = np.random.default_rng(1)
        t = rng.exponential(5, 200)
        e = rng.integers(0, 2, 200)
        g = np.repeat(["A", "B"], 100)
        spec = pf.setup("generic", "single", aspect=0.95)
        fig, ax, rax, out = pc.km_figure(spec, t, e, g, at_times=[0, 2, 4, 6], xmax=6, xlabel="Years")
        self.assertEqual(codes(qa.audit_figure(fig), "FAIL"), set())
        plt.close(fig)


FOREST_ROWS = [dict(label="Overall", est=0.8, lo=0.7, hi=0.92, summary=True, cols=("10/100", "20/100")),
               dict(label="Age", header=True),
               dict(label="< 65 y", est=0.75, lo=0.6, hi=0.95, indent=1, weight=50, cols=("5/50", "10/50"), p_text=".40"),
               dict(label="≥ 65 y", est=0.85, lo=0.7, hi=1.05, indent=1, weight=50, cols=("5/50", "10/50"))]


def _labelled(ax):
    ax.set_xlabel("x (units)")
    ax.set_ylabel("y (units)")


class SurvivalDisplay(unittest.TestCase):
    """Journal truncation rules, per-arm follow-up, CI styles (from the JVS test run)."""

    @staticmethod
    def data():
        rng = np.random.default_rng(7)
        ta, ca = rng.exponential(4, 60), rng.uniform(0, 8, 60)
        tb, cb = rng.exponential(3, 25), rng.uniform(0, 5, 25)
        t = np.r_[np.minimum(ta, ca), np.minimum(tb, cb)]
        e = np.r_[ta <= ca, tb <= cb].astype(int)
        g = np.array(["A"] * 60 + ["B"] * 25, dtype=object)
        return t, e, g

    def test_greenwood_se_hand_computed(self):
        km = pc.kaplan_meier([1, 2, 3, 4, 5], [1, 1, 0, 1, 1])
        # t=1: S=0.8, SE=0.8*sqrt(1/(5*4)); t=2: S=0.6, SE=0.6*sqrt(1/20+1/12)
        self.assertAlmostEqual(km.se[1], 0.8 * np.sqrt(1 / 20), places=12)
        self.assertAlmostEqual(km.se[2], 0.6 * np.sqrt(1 / 20 + 1 / 12), places=12)

    def test_truncation_time_rules(self):
        t, e, g = self.data()
        km = pc.kaplan_meier(t[g == "B"], e[g == "B"])
        for kw, ok in (({"min_at_risk": 10}, lambda k, m: k.n_risk[m] >= 10),
                       ({"max_se": 0.10}, lambda k, m: k.se[m] <= 0.10 + 1e-12)):
            cut = pc.km_truncation_time(km, **kw)
            shown = km.time <= cut
            self.assertTrue(np.all(ok(km, shown)), kw)
            if (~shown).any():                       # the first hidden row is the one that breaks the rule
                self.assertFalse(bool(ok(km, np.flatnonzero(~shown)[0])), kw)

    def test_jvs_rule_applied_and_reported(self):
        t, e, g = self.data()
        spec = pf.setup("jvs", "single", aspect=0.8)
        for truncate, want in (("auto", "INFO"), (None, "WARN")):
            fig = pf.figure(spec)
            gs = fig.add_gridspec(2, 1, height_ratios=[1, 0.3])
            ax, rax = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
            res = pc.km_plot(ax, t, e, g, risk_ax=rax, truncate=truncate, xlabel="Years")
            if truncate == "auto":
                self.assertEqual(res["truncation"], {"max_se": 0.10})
                self.assertLessEqual(res["ends"]["B"], float(t[g == "B"].max()))
                line_b = [ln for ln in ax.get_lines() if ln.get_label() == "B"][0]
                self.assertAlmostEqual(max(line_b.get_xdata()), res["ends"]["B"])   # no extension past its own end
            F = qa.audit_figure(fig)
            self.assertIn("JOURNAL_KM_TRUNCATION", codes(F, want))
            self.assertNotIn("JOURNAL_KM_RISK", codes(F))
            plt.close(fig)

    def test_ci_bars_stay_inside_and_clipping_is_flagged(self):
        t, e, g = self.data()
        spec = pf.setup("generic", "single")
        fig, ax = pf.subplots(spec)
        pc.km_plot(ax, t, e, g, ci_style="bars", at_times=[0, 2, 4, 6, 8], xmax=8, failure=True, ylim=(0, 20),
                   legend="legend", xlabel="Years")
        from matplotlib.container import ErrorbarContainer
        bars = [c for c in ax.containers if isinstance(c, ErrorbarContainer)]
        self.assertGreaterEqual(len(bars), 4)
        xs = [seg[0][0] for c in bars for seg in c.lines[2][0].get_segments()]
        self.assertTrue(all(0 < x < 8 for x in xs), xs)
        self.assertEqual(getattr(ax, "_pubfig_error_kind", None), "95% CI")
        self.assertIn("KM_CI_CLIPPED", codes(qa.audit_figure(fig), "WARN"))
        plt.close(fig)

    def test_jevt_auto_drops_ci(self):
        t, e, g = self.data()
        spec = pf.setup("jevt", "single", aspect=0.8)
        fig, ax = pf.subplots(spec)
        res = pc.km_plot(ax, t, e, g, xlabel="Years")
        self.assertEqual(res["truncation"], {"max_se": 0.10, "min_at_risk": 10})
        self.assertNotIn("JOURNAL_KM_CI", codes(qa.audit_figure(fig)))
        plt.close(fig)


class MultiPanel(unittest.TestCase):
    def test_forest_in_subfigure_with_km_panel(self):
        spec = pf.setup("generic", "double", height_mm=160)
        fig = pf.figure(spec)
        top, bottom = fig.subfigures(2, 1)
        ax = top.add_subplot(111)
        ax.plot([0, 1, 2], [0, 1, 4])
        _labelled(ax)
        _, fx = pc.forest_plot(spec, FOREST_ROWS, col_titles=("A", "B"), xticks=[0.5, 1, 1.5], xlim=(0.45, 1.6),
                               favours=("Favors A", "Favors B"), fig=bottom)
        self.assertIsNotNone(fx["host"])
        self.assertEqual(len(fx["host"].child_axes), 6)           # labels, 2 columns, plot, estimates, P
        pf.panel_labels(fig, [ax, fx["host"]])
        pf.synthetic_tag(fig)
        F = qa.audit_figure(fig)
        self.assertEqual(codes(F, "FAIL"), set())
        self.assertFalse({"NO_PANEL_LABELS", "FIGURE_TITLE", "DUAL_AXES"} & codes(F))
        plt.close(fig)

    def test_forest_in_gridspec_cell(self):
        spec = pf.setup("generic", "double", height_mm=90)
        fig = pf.figure(spec)
        gs = fig.add_gridspec(1, 2, width_ratios=[1, 2.4])
        ax = fig.add_subplot(gs[0, 0])
        ax.plot([0, 1], [1, 0])
        _labelled(ax)
        _, fx = pc.forest_plot(spec, FOREST_ROWS, col_titles=("A", "B"), p_title=None, xticks=[0.5, 1, 1.5],
                               xlim=(0.45, 1.6), fig=fig, subplotspec=gs[0, 1])
        pf.panel_labels(fig, [ax, fx["host"]])
        self.assertEqual(codes(qa.audit_figure(fig), "FAIL"), set())
        plt.close(fig)

    def test_synthetic_tag_free_corner_without_layout_engine(self):
        spec = pf.setup("generic", "double")
        fig, _ = pc.forest_plot(spec, FOREST_ROWS, col_titles=("A", "B"), xticks=[0.5, 1, 1.5], xlim=(0.45, 1.6))
        pf.synthetic_tag(fig)
        self.assertNotIn("TEXT_COLLISION", codes(qa.audit_figure(fig)))
        plt.close(fig)


class ExportDetails(unittest.TestCase):
    def test_svg_keeps_spaces_in_rich_text(self):
        spec = pf.setup("generic", "single")
        with tempfile.TemporaryDirectory() as td:
            fig, ax = pf.subplots(spec)
            ax.plot([0, 1], [0, 1])
            _labelled(ax)
            pf.rich_text(ax, 0.05, 0.9, [("Log-rank ", "normal")] + pf.fmt_p(0.003, "ama", markup="parts"),
                         transform=ax.transAxes)
            pf.save(fig, Path(td) / "ok", ["svg"], quiet=True)
            self.assertNotIn("SVG_EDGE_SPACE", codes(qa.audit_file(Path(td) / "ok.svg")))
            fig.text(0.5, 0.02, " = .003")
            pf.save(fig, Path(td) / "bad", ["svg"], quiet=True)
            self.assertIn("SVG_EDGE_SPACE", codes(qa.audit_file(Path(td) / "bad.svg"), "WARN"))
            plt.close(fig)

    def test_png_role_preview_versus_submission(self):
        from PIL import Image
        for target, role in (("aha", "preview"), ("nature", "final")):
            spec = pf.setup(target, "single")
            fig, ax = pf.subplots(spec)
            ax.plot([0, 1], [0, 1])
            _labelled(ax)
            with tempfile.TemporaryDirectory() as td:
                pf.save(fig, Path(td) / "f", ["png"], quiet=True)
                self.assertEqual(Image.open(Path(td) / "f.png").info.get("pubfig-role"), role)
                F = qa.audit_file(Path(td) / "f.png", target=target, column="single")
                self.assertNotIn("LOW_DPI", codes(F))
                self.assertEqual("PREVIEW_DPI" in codes(F), role == "preview")
            plt.close(fig)

    def test_cvd_preview_picks_a_rasterizable_file(self):
        import contextlib
        import io
        import shutil
        spec = pf.setup("generic", "single")
        fig, ax = pf.subplots(spec)
        ax.plot([0, 1], [0, 1])
        _labelled(ax)
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            pf.save(fig, Path(td) / "f", ["eps", "png"], quiet=True)
            out = Path(td) / "cvd.png"
            qa.main([str(Path(td) / "f.eps"), str(Path(td) / "f.png"), "--cvd-preview", str(out)])
            self.assertTrue(out.exists())
            out2 = Path(td) / "cvd_eps.png"
            qa.main([str(Path(td) / "f.eps"), "--cvd-preview", str(out2)])    # must not raise
            self.assertEqual(out2.exists(), shutil.which("gs") is not None)
        plt.close(fig)

    def test_legend_checker_reads_through_markdown(self):
        F = qa.check_legend_text("Cumulative incidence by arm; *P* < 0.001 by log-rank test.", "jama")
        self.assertIn("P_LEADING_ZERO", codes(F))


class ManuscriptBotPacket(unittest.TestCase):
    def test_packet_verdicts_and_palette_digest(self):
        import figure_packet as fp
        palette = ROOT / "assets" / "paper-palette.yaml"
        clean = [{"severity": "INFO", "code": "FONTS", "message": "x", "where": ""}]
        warn = clean + [{"severity": "WARN", "code": "TEXT_OVER_DATA", "message": "legend covers points", "where": ""}]
        fail = clean + [{"severity": "FAIL", "code": "LOW_DPI", "message": "300 dpi", "where": ""}]
        args = dict(figure_id="Fig1", files={"pdf": "Fig1.pdf"}, legend="Figure 1.", callout="Figure 1 shows.",
                    palette_file=palette)
        self.assertEqual(fp.build_packet(findings=clean, manual_checks_done=True, **args)["qa"], "PASS")
        self.assertEqual(fp.build_packet(findings=clean, **args)["qa"], "REVIEW")
        self.assertEqual(fp.build_packet(findings=warn, manual_checks_done=True, **args)["qa"], "FAIL")
        ok = fp.build_packet(findings=warn, manual_checks_done=True,
                             accepted_warnings={"TEXT_OVER_DATA": "points are background reference"}, **args)
        self.assertEqual(ok["qa"], "PASS")
        self.assertTrue(any("Accepted TEXT_OVER_DATA" in x for x in ok["limits"]))
        self.assertEqual(fp.build_packet(findings=fail, manual_checks_done=True, **args)["qa"], "FAIL")
        pk = fp.build_packet(findings=clean, synthetic=True, **args)
        self.assertEqual(pk["to"], "scientific-manuscript-draft-bot")
        self.assertEqual(pk["palette_id"], "academic-paper-default-v2-cvd")
        self.assertRegex(pk["palette_digest"], r"^[0-9a-f]{64}$")
        self.assertTrue(pk["limits"][0].startswith("Synthetic data"))


class Images(unittest.TestCase):
    def test_batch_lock_and_duplicates(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            rng = np.random.default_rng(0)
            a = (rng.random((120, 160)) * 255).astype(np.uint8)
            Image.fromarray(a).save(td / "a.png")
            Image.fromarray(a).transpose(Image.Transpose.ROTATE_90).save(td / "a_rot.png")
            Image.fromarray((rng.random((120, 160)) * 255).astype(np.uint8)).save(td / "b.png")
            rep = ip.screen_duplicates([td / "a.png", td / "a_rot.png", td / "b.png"], use_orb=False)
            pairs = {(f["a"], f["b"]) for f in rep["findings"]}
            self.assertIn(("a.png", "a_rot.png"), pairs)
            self.assertFalse(any("b.png" in p for p in pairs))
            (td / "m.csv").write_text("file,output_name,batch,display_min\na.png,x,A,0\nb.png,y,A,10\n")
            with self.assertRaises(SystemExit):
                ip.read_manifest(td / "m.csv")


if __name__ == "__main__":
    unittest.main()
