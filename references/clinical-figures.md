# Clinical figures

Survival curves, forest plots, participant flow, agreement, diagnostic accuracy, prediction, individual response, and the summary graphics journals now request (central illustration, visual or graphical abstract). Journal rules quoted here come from `assets/journal-specs/journal_specs_clinical.json` (retrieved 2026-11-14); recheck before submission.

## Contents
1. Time to event: Kaplan-Meier, cumulative incidence, competing risks
2. Forest plots
3. Participant flow (CONSORT 2025, PRISMA 2020, STROBE)
4. Method agreement (Bland-Altman)
5. Discrimination and calibration (ROC, PR, calibration)
6. Continuous outcomes and individual response
7. Central illustration, visual abstract, graphical abstract
8. Journal chart rules at a glance
9. Clinical images and privacy

## 1. Time to event

Evidence: Pocock, Clayton and Altman (Lancet 2002) recommend plotting survival curves going up (cumulative incidence) rather than down, limiting how far in time the plot extends, showing the extent of follow-up, displaying uncertainty, and caution in reading curve shape. KMunicate (Morris et al, BMJ Open 2019; 1174 stakeholders) favored an extended table under the plot with numbers at risk, censored, and events at regular times, plus a confidence interval around each curve. Guyot et al (2012) found reconstructed hazard ratios were reasonably accurate only when numbers at risk or total events were reported, so always report both. Underwood et al (Br J Surg 1984) set the vascular-surgery convention: step curves, numbers remaining at intervals, and a strict rule on how far a curve is claimed to hold.

Build:
```python
fig, ax, rax, res = pc.km_figure(spec, time, event, arm, order=["Intervention", "Control"],
                                 failure=True, at_times=[0, 1, 2, 3, 4], xmax=4,
                                 xlabel="Years since randomization",
                                 ylabel="Cumulative incidence of MACE (%)", ylim=(0, 40),
                                 annotation="HR, 0.68 (95% CI, 0.50-0.92)",   # from the user's Cox model
                                 show_logrank=False, risk_extended=False)
```
- Step function, never a smoothed line. When the extended table already tabulates censored counts, censoring ticks add little and can be omitted (`censor_marks=False`); keep them when no table is shown.
- Numbers at risk under the x axis at each labeled time (`risk_ax`); `risk_extended=True` prints "at risk (events) [censored]".
- Upward cumulative incidence (`failure=True`) when event rates are low; choose a y-axis range that does not exaggerate small differences and state the range in the legend. Several vascular journals require the y axis to start at 0 (EJVES).
- Stop the curve where it stops being reliable. Journal rules differ, so follow the target: JVS truncates or dots the curve when the standard error exceeds 10%; EJVES truncates when numbers at risk are small (for example below 10), when SE exceeds 10%, or beyond median follow-up, and requires the truncation to be predefined, declared in the legend, and justified in the methods; JEVT accepts Kaplan-Meier only while SE < 10% and at least 10 patients remain at risk in all groups, wants Greenwood SEs per interval, and says not to plot 95% CIs.
- `km_plot(truncate="auto")` applies the target preset's rule (JVS `{"max_se": 0.10}`, EJVES `{"min_at_risk": 10}`, JEVT both); pass a dict for a protocol rule or `None` to switch it off (the QA then warns for those journals). Each arm ends at its own last follow-up or truncation time and is never extended to a common end. The JVS dotted-continuation alternative is not automated; truncation is. `res["ends"]` gives the plotted end of each arm for the legend.
- Missing or non-finite times, events, or groups raise an error in `kaplan_meier`, `logrank_test`, and `cumulative_incidence`; resolve them in the source data and state exclusions in the legend. When the last patients at risk all have the event, S(t) = 0 and the Greenwood SE is undefined (`KMTable.se` is NaN, as in R `survfit`); the SE rule treats that point as exceeding the limit and stops the curve before it.
- The SE is Greenwood's: SE(S(t)) = S(t) × √Σ dᵢ / (nᵢ(nᵢ − dᵢ)) over event times up to t (`KMTable.se`). It is an absolute SE, so once S(t) is low it can stay under 10% with very few patients left (and in large trials it may never trigger); pair it with an at-risk floor when follow-up is long, and report which rule was used.
- Uncertainty display: `ci_style="band"` (default; translucent where arms overlap), `"bars"` (95% CI vertical lines at the labeled times, the JVS alternative: "adding vertical lines to the survival curve at relevant time-points"), or `"none"`; `"auto"` chooses none for JEVT. The QA warns (`KM_CI_CLIPPED`) when the y-axis limit cuts a CI, a common way to make an uncertain tail look precise.
- Competing risks: when death from other causes precludes the event, plot Aalen-Johansen cumulative incidence (`pc.cumulative_incidence`), not 1 minus Kaplan-Meier, which overstates incidence. NEJM instructions say Kaplan-Meier is replaced by cumulative incidence when competing risks are present.
- Hazard ratios and adjusted estimates come from the user's model; print them as supplied. The log-rank P is a transparent unadjusted test and may be shown when it was the planned analysis.
- Two arms: intervention blue solid, control dark gray dashed (`pf.ARMS`), labeled directly at the curve ends.

## 2. Forest plots

Lewis and Clarke (BMJ 2001): squares for estimates sized by weight, lines for intervals, a diamond for the pooled or overall estimate. Schriger et al (Int J Epidemiol 2010) found forest plots often sparse, alphabetized, or missing key information. Kiran, Crespillo and Rahimi (Heart 2017) recommend tabulated statistics including heterogeneity alongside the plot.

```python
fig, axd = pc.forest_plot(spec, rows, col_titles=("Intervention\nevents/n", "Control\nevents/n"),
                          est_title="HR (95% CI)", p_title="P for interaction",
                          xticks=[0.5, 0.75, 1, 1.5], xlim=(0.45, 1.6),
                          favours=("Favors intervention", "Favors control"))
```
- Ratios on a log axis with the null at 1 (JAMA requires ratio measures on a log scale with actual, not log-transformed, values; NEJM computes ratio CIs on the log scale).
- Raw numerators and denominators in the margins (Annals requires them); estimates and P values in their own columns, never on top of markers.
- Order rows by a prespecified structure (overall, then subgroup families), not alphabetically.
- Subgroup interaction P values only when the multiplicity plan covers them (NEJM).
- Mark an interval that runs off the axis with an arrow or widen the axis; the builder warns.
- The Lancet prints forest plots and trial profiles in black and white: check the grayscale preview.

Survival curve and forest plot in one figure. Give each part its own subfigure: panels stacked in one gridspec column share left and right margins under constrained layout, so a forest plot placed under a survival panel inherits the survival panel's y-label and direct-label margins (about 30 mm lost at 127 mm width), and side-by-side panels in one gridspec row inherit the forest header's top margin.
```python
spec = pf.setup("jvs", "double", height_mm=215)
fig = pf.figure(spec)
top, bottom = fig.subfigures(2, 1, height_ratios=[3.75, 3.4])   # side by side: fig.subfigures(1, 2, width_ratios=[1, 2.1])
gs = top.add_gridspec(2, 1, height_ratios=[3.0, 0.75])
ax, rax = top.add_subplot(gs[0]), top.add_subplot(gs[1])
rax.sharex(ax)
res = pc.km_plot(ax, time, event, arm, order=["Intervention", "Control"], risk_ax=rax, failure=True,
                 at_times=[0, 1, 2, 3, 4], xlabel="Years since randomization", annotation=hr_text)
_, fx = pc.forest_plot(spec, rows, col_titles=("Intervention\nevents/n", "Control\nevents/n"),
                       favours=("Favors intervention", "Favors control"), fig=bottom)
pf.panel_labels(fig, [ax, fx["host"]])
pf.save(fig, "final_figures/Fig2")
```
`forest_plot(..., fig=fig, subplotspec=gs[0, 1])` places it in one gridspec cell instead. The builder raises an error naming the region width when the columns leave less than 25 mm for the plot, and warns with the height needed when rows would crowd; widen the region or stack the panels rather than shrinking type.

## 3. Participant flow

- CONSORT 2025 (Hopewell et al, BMJ 2025;389:e081123 and JAMA 2025;333:1998-2005) keeps a participant flow diagram with the 30-item checklist. `pc.consort_diagram(spec, counts)` draws enrollment, allocation, follow-up, and analysis for a two-arm parallel trial and warns when counts do not add up (assessed minus excluded must equal randomized; arms must sum to randomized).
- PRISMA 2020 (Page et al, BMJ 2021): `pc.prisma2020_diagram(spec, counts)` for databases and registers.
- STROBE or registry cohorts: `pc.flow_diagram(spec, boxes, edges, stages=...)` with side boxes for exclusions at each step (JACC and AHA instructions both suggest a flow chart with exclusions at each phase).
- Text stays live and editable; widths follow the preset; check arithmetic before drawing.

## 4. Method agreement

Bland and Altman (Lancet 1986): correlation does not measure agreement. Plot the difference against the mean with the mean bias and 95% limits of agreement (bias ± 1.96 SD).
```python
res = pc.bland_altman(ax, invasive, cuff, unit="mmHg", label_a="Invasive", label_b="Cuff")
```
- Shaded bands give approximate 95% CIs for the bias (t-based) and for each limit (SE ≈ sqrt(3 s²/n), from the 1986 paper).
- `percent=True` when error scales with magnitude; the result reports a regression slope of difference on mean as a proportional-bias check.
- State in the legend whether clinically acceptable limits were prespecified.

## 5. Discrimination and calibration

- `pc.roc_plot` draws empirical ROC curves with AUC and DeLong 95% CIs (validated against scikit-learn and a 3,000-resample bootstrap). Square axes, chance diagonal. The default interval is Wald (AUC ± z × SE, clipped to 0 and 1), the form R pROC reports for `ci.auc(method="delong")`, so the figure reproduces an analyst's pROC output; `ci="logit"` gives the logit-transformed interval, which stays inside (0, 1) and differs visibly at high AUC or small n. Name the method in the legend ("95% CI by the DeLong method, Wald interval"). With perfect separation the DeLong SE is 0 and the interval collapses to 1.00; report that as a small-sample artifact.
- `pc.precision_recall` with the prevalence baseline when outcomes are rare.
- `pc.calibration_plot`: binned observed proportions with Wilson CIs against predicted risk, the ideal line, calibration-in-the-large, and the recalibration slope. Discrimination without calibration is half a validation.
- TRIPOD distinguishes development, internal validation, and external validation; label which one the figure shows. A renamed subset of the development cohort is not external validation.

## 6. Continuous outcomes and individual response

Weissgerber et al (Circulation 2019) found 47.7% of papers in top peripheral vascular disease journals used bar graphs for continuous data; Riedel et al (2022) found the practice persisting across fields; Wullschleger et al (2014) found 64% of articles in three cardiovascular journals misused the SEM. AHA, JACC, Heart, and Annals instructions all discourage bar graphs except for counts and proportions.

- Group comparisons: `pp.estimation_plot` (every observation plus mean with 95% CI, or median with bootstrap CI) or `pp.raincloud` for larger groups.
- Paired measurements (before and after, left and right limb): `pp.paired_plot`.
- Repeated measures: `pc.spaghetti_plot` (individual trajectories plus group mean with pointwise CI; inference needs a longitudinal model).
- Individual change ranked (for example percent change in ankle-brachial index): `pc.waterfall_plot`, one bar per patient, response thresholds as reference lines.
- AHA asks for error bars in both directions and the number of subjects per group in every figure; JAMA asks for point estimates as markers with two-sided error bars.

## 7. Central illustration, visual abstract, graphical abstract

These are summary graphics, built with the schematic path (`references/diagrams-and-icons.md`) at the venue's canvas. What the instructions state:
- JACC: Central Illustration encouraged (optional) at JACC; legend listed last.
- JACC: Cardiovascular Interventions: Central Illustration required for original research and state-of-the-art reviews; one original image (not an existing figure); boxed text header at the top; title of 10 words or fewer.
- JACC: Advances: Central Illustration required (original research, state-of-the-art reviews); AI/EPS/SVG/PDF preferred; title at top, brief patient population, synopsis of main findings toward the bottom; no logos; labeled "Central Illustration".
- JACC: Basic to Translational Science: Visual Abstract required for original research (may be hand-drawn; redrawn in house).
- JACC: Case Reports: Visual Summary required (case timeline or summary figure).
- Circulation: Cardiovascular Interventions: Graphic Abstract required for original investigations and reviews, with title and legend inside the graphic. Hypertension and ATVB graphic abstracts at most 15 × 15 cm, 12 pt sans serif, JPG; Stroke at most 18 cm square.
- European Heart Journal: Structured Graphical Abstract required for clinical research, translational science, and meta-analysis: graphic 11.0 cm high × 18.0 cm wide, landscape, at least 300 ppi, sans serif 10 to 12 pt (never below 8 pt), graphs as vector; text element of up to 40 words each for Key Question, Key Finding, Take-home Message.
- EuroIntervention: Central Illustration mandatory for main article types; highlights the key result; explicitly not a visual abstract; must not duplicate another figure.
- JVS: optional visual abstract on the journal PowerPoint template (slide 13.33 × 7.5 in, measured from the template). JEVT: visual abstract required on its PowerPoint template.
- Catheterization and Cardiovascular Interventions: central figure strongly encouraged.
- Elsevier generic graphical abstract: at least 1328 × 531 px at 300 dpi, displayed in a 500 × 200 px window.
- Cell: graphical abstract 1200 × 1200 px at 300 dpi, Arial 8 to 12 pt.

Design rules for all of them: one finding, readable at thumbnail size, population and intervention named, outcome with its effect size and uncertainty, no logos, no unreadable mini-charts. Chapman et al (Br J Surg 2019) found visual abstracts drew more engagement than plain-English abstracts on social media; engagement is not a substitute for accuracy, so numbers on the abstract must match the paper exactly.

## 8. Journal chart rules at a glance

Encoded in the presets' `rules`, so `audit_figure` flags violations:
- JAMA Network: no pie charts, 3-D graphs, or stacked bars; bars only for frequencies with an unbroken axis from 0; ratio measures on log scale; Kaplan-Meier as step function with numbers at risk; at most 4 panels.
- JACC family: avoid bar graphs except counts and proportions; JACC: Advances and Basic to Translational Science reject dynamite plots; JACC: CI wants charts in black and white rather than gray; legends titled in 10 words or fewer, 150 words maximum, abbreviations defined alphabetically at the end.
- AHA journals: avoid bar graphs except counts and proportions; show all data points where possible; error bars in both directions; n per group in every figure; uppercase panel letters top left; at most 6 panels; no headings on the figure.
- EHJ: at most 6 panels; legends give n and the test; exact P preferred; alt text required under each caption; do not truncate axes to inflate differences.
- Heart: avoid bar or column graphs (use box plots or distributions); label lines directly; no chart decoration.
- Annals: avoid pie charts and 3-D; avoid bars without variability; raw numbers in forest-plot margins; numbers at risk under survival plots.
- The Lancet: numbers at risk required with Kaplan-Meier, censored numbers encouraged; 3-D converted to 2-D; consistent axes across serial graphs.
- EJVES and JVS: survival-curve truncation and numbers at risk as in section 1; EJVES portrait figures only.

## 9. Clinical images and privacy

- Strip burned-in identifiers (name, MRN, date of birth, study date, accession number, institution) from angiography, echo, CT, MR, and ultrasound captures. Use `image_panels.py` masks and keep the masking in the audit; do not blur identifiers you could crop.
- Several journals forbid black bars over eyes as anonymization (JAMA, Lancet, Heart, The BMJ): identifiable photographs need written consent on the journal's form instead.
- Anonymized radiographs, ultrasound, and pathology may be used without separate consent at The BMJ and BMJ journals when identifying marks are removed; consent rules differ by journal, so read the target's policy.
- Keep the original DICOM or raw capture; derived panels must be traceable to it.
