#!/usr/bin/env python3
"""Render the example gallery and run the QA gate on every figure.

All data are SYNTHETIC (fixed seeds) and exist only to exercise the builders.
Usage: python demo_gallery.py [--out DIR] [--target generic]
Exit code 2 if any figure has a FAIL finding.
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pubfig as pf  # noqa: E402
import pubfig_plots as pp  # noqa: E402
import pubfig_clinical as pc  # noqa: E402
import figure_qa as qa  # noqa: E402

rng = np.random.default_rng(2026)


def synthetic_trial(n=400):
    arm = np.repeat(["Intervention", "Control"], n // 2)
    hazard = np.where(arm == "Intervention", 0.075, 0.11)
    t_event = rng.exponential(1 / hazard)
    t_cens = rng.uniform(1.5, 5.0, n)
    time = np.minimum(t_event, t_cens)
    event = (t_event <= t_cens).astype(int)
    return time, event, arm


def fig_estimation(spec, out):
    fig, axes = pf.subplots(spec, 1, 2, width_ratios=[1.5, 1])
    data = {"Control": rng.normal(132, 14, 18), "Low dose": rng.normal(126, 13, 17), "High dose": rng.normal(119, 15, 19)}
    pp.estimation_plot(axes[0], data, ylabel="Systolic BP (mmHg)")
    before = rng.normal(0.62, 0.12, 14)
    after = before + rng.normal(0.08, 0.06, 14)
    pp.paired_plot(axes[1], before, after, labels=("Baseline", "6 mo"), ylabel="Ankle-brachial index")
    pf.panel_labels(fig, axes)
    return fig


def fig_km(spec, out):
    t, e, arm = synthetic_trial()
    hr_text = "HR, 0.68\n(95% CI, 0.50-0.92)"  # supplied from the user's Cox model
    fig, ax, rax, res = pc.km_figure(spec, t, e, arm, order=["Intervention", "Control"], failure=True,
                                     at_times=[0, 1, 2, 3, 4], xmax=4, xlabel="Years since randomization",
                                     ylabel="Cumulative incidence (%)", ylim=(0, 50),
                                     annotation=hr_text, show_logrank=True)
    return fig


def fig_forest(spec, out):
    rows = [
        dict(label="Overall", est=0.78, lo=0.67, hi=0.91, cols=("412/2100", "498/2096"), summary=True),
        dict(label="Age", header=True),
        dict(label="< 65 y", est=0.74, lo=0.58, hi=0.94, cols=("160/1010", "205/1002"), indent=1, weight=365, p_text=".52"),
        dict(label="≥ 65 y", est=0.82, lo=0.67, hi=1.00, cols=("252/1090", "293/1094"), indent=1, weight=545),
        dict(label="Diabetes", header=True),
        dict(label="Yes", est=0.71, lo=0.55, hi=0.91, cols=("150/760", "199/751"), indent=1, weight=349, p_text=".31"),
        dict(label="No", est=0.83, lo=0.69, hi=0.99, cols=("262/1340", "299/1345"), indent=1, weight=561),
        dict(label="Chronic kidney disease", header=True),
        dict(label="eGFR < 60 mL/min/1.73 m²", est=0.69, lo=0.51, hi=0.93, cols=("120/520", "160/515"), indent=1, weight=280, p_text=".27"),
        dict(label="eGFR ≥ 60 mL/min/1.73 m²", est=0.82, lo=0.69, hi=0.98, cols=("292/1580", "338/1581"), indent=1, weight=630),
    ]
    fig, axd = pc.forest_plot(spec, rows, col_titles=("Intervention\nevents/n", "Control\nevents/n"),
                              xticks=[0.5, 0.75, 1, 1.5], xlim=(0.45, 1.6),
                              favours=("Favors intervention", "Favors control"))
    return fig


def fig_bland_altman(spec, out):
    fig, ax = pf.subplots(spec)
    truth = rng.normal(70, 12, 60)
    a = truth + rng.normal(0, 4, 60)
    b = truth + 1.5 + rng.normal(0, 4, 60)
    res = pc.bland_altman(ax, a, b, unit="mmHg", label_a="Invasive", label_b="Cuff")
    return fig


def fig_roc_cal(spec, out):
    fig, axes = pf.subplots(spec, 1, 2)
    n = 600
    y = rng.binomial(1, 0.22, n)
    s1 = y * 1.2 + rng.normal(0, 1, n)
    s2 = y * 0.7 + rng.normal(0, 1, n)
    pc.roc_plot(axes[0], y, {"Model A": s1, "Model B": s2})
    p = 1 / (1 + np.exp(-(-1.4 + 0.9 * s1)))
    pc.calibration_plot(axes[1], y, p)
    pf.panel_labels(fig, axes)
    return fig


def fig_consort(spec, out):
    counts = dict(assessed=1520, excluded=1120, excluded_reasons=["Did not meet inclusion criteria (n = 840)",
                                                                  "Declined to participate (n = 230)", "Other reasons (n = 50)"],
                  randomized=400, allocated={"Intervention": 200, "Control": 200},
                  received={"Intervention": 196, "Control": 199}, not_received={"Intervention": 4, "Control": 1},
                  lost={"Intervention": 6, "Control": 8}, discontinued={"Intervention": 11, "Control": 9},
                  analysed={"Intervention": 200, "Control": 200}, excluded_analysis={"Intervention": 0, "Control": 0})
    fig, ax = pc.consort_diagram(spec, counts)
    return fig


def fig_prisma(spec, out):
    counts = dict(databases=2314, registers=118, duplicates=612, automation_removed=0, other_removed=4,
                  screened=1816, screened_excluded=1650, sought=166, not_retrieved=7, assessed=159,
                  assessed_excluded_reasons=["Wrong population (n = 61)", "Wrong outcome (n = 44)",
                                             "No comparator (n = 23)", "Duplicate cohort (n = 9)"],
                  studies_included=22, reports_included=26)
    fig, ax = pc.prisma2020_diagram(spec, counts)
    return fig


def fig_bars_vs_dots(spec, out):
    fig, axes = pf.subplots(spec, 1, 2)
    methods = ["Ours", "Baseline A", "Baseline B", "Baseline C"]
    auc = np.array([0.912, 0.897, 0.889, 0.874])
    pp.bar_plot(axes[0], methods, auc, errors=[0.006, 0.007, 0.008, 0.009], error_kind="95% CI")
    axes[0].set_ylabel("AUROC")
    pp.dot_plot(axes[1], methods, auc, auc - 0.012, auc + 0.012, highlight="Ours", xlabel="AUROC (95% CI)",
                error_kind="95% CI")
    pf.panel_labels(fig, axes)
    return fig


def fig_heatmap(spec, out):
    fig, ax = pf.subplots(spec)
    M = rng.normal(0, 1, (8, 6))
    M[2, 3] = 2.6
    pp.heatmap(ax, M, [f"Gene {i + 1}" for i in range(8)], [f"S{j + 1}" for j in range(6)], kind="diverging",
               cbar_label="z score", annotate=False)
    return fig


def fig_ml(spec, out):
    fig, axes = pf.subplots(spec, 1, 2, width_ratios=[1, 1.25])
    names = ["Full model", "- memory", "- retrieval", "- verifier", "- all"]
    acc = np.array([71.2, 68.1, 66.4, 63.0, 55.3])
    pp.dot_plot(axes[0], names, acc, acc - 1.1, acc + 1.1, highlight="Full model", xlabel="Accuracy (%)",
                sort=False, error_kind="95% CI")
    steps = np.arange(0, 101, 5)
    for i, (name, rate) in enumerate([("Ours", 0.06), ("Baseline", 0.04)]):
        mean = 70 * (1 - np.exp(-rate * steps))
        pp.line_band(axes[1], steps, mean, mean - 2.5, mean + 2.5, color=pf.CATEGORICAL[i], label=name)
    axes[1].set_xlabel("Training steps (thousands)")
    axes[1].set_ylabel("Validation accuracy (%)")
    axes[1].set_xlim(0, 100)
    pp.direct_labels(axes[1])
    pf.panel_labels(fig, axes)
    return fig


GALLERY = [
    ("estimation_paired", fig_estimation, "double", 0.42),
    ("km_cumulative_incidence", fig_km, "single", 0.95),
    ("forest_subgroups", fig_forest, "double", None),
    ("bland_altman", fig_bland_altman, "single", 0.75),
    ("roc_calibration", fig_roc_cal, "double", 0.45),
    ("consort_flow", fig_consort, "double", None),
    ("prisma2020_flow", fig_prisma, "double", None),
    ("bars_vs_dotplot", fig_bars_vs_dots, "double", 0.38),
    ("heatmap_diverging", fig_heatmap, "single", 0.85),
    ("ml_ablation_training", fig_ml, "double", 0.36),
]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent / "examples" / "gallery"))
    ap.add_argument("--target", default="generic")
    ap.add_argument("--formats", default="pdf,svg,png")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    worst = 0
    for name, builder, column, aspect in GALLERY:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            spec = pf.setup(a.target, column, aspect=aspect)
        try:
            fig = builder(spec, out)
            pf.synthetic_tag(fig)       # every gallery figure is built from simulated data
        except ValueError as exc:  # e.g. a forest table that cannot fit at this preset's type size
            print(f"\n== {name}: SKIPPED at {a.target}: {exc}")
            worst = max(worst, 1)
            continue
        findings = qa.audit_figure(fig)
        rep = pf.save(fig, out / name, formats=a.formats.split(","), quiet=True)
        file_findings = []
        for f in rep["files"]:
            file_findings += qa.audit_file(f, target=a.target, column=column)
        print(f"\n== {name} ({spec.width_mm:.0f} x {fig.get_size_inches()[1] * 25.4:.0f} mm)")
        code = qa.report([f for f in findings + file_findings if f.severity != "INFO"])
        worst = max(worst, code)
        plt.close(fig)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
