# Source Census And Refresh Policy

This census records sources used to establish the advisor contract on 2026-08-25. Cite the exact
source beside consequential claims. Refresh versioned official documentation when invoked; older
papers remain conceptual authorities but do not prove current library behavior or Markeitech fit.

## Tracked Markeitech Authority

| Source | Role | Constraint carried into the advisor |
|---|---|---|
| `AGENTS.md` | Repository working authority | Markeitect decides; advisors are read-only; evidence classes, side-effect, delegation, and review boundaries apply. |
| `markeitech.md` | Product and engineering charter | Live-first/read-only/advisory; deterministic truth is separate from model output; all variable behavior is typed, bounded, versioned, auditable policy. |
| `docs/current-status.md` | Current implementation truth | ML evaluation and richer intelligence remain future work; raw observations are not a PostgreSQL feature store. |
| `docs/development-guidelines.md` | Engineering guidance | Deterministic features and labels precede training; feature and model identity accompany inference; no silent configuration control. |
| `docs/roadmap/v2-market-events-live-agent-plan.md`, Statistical And ML Models and Stage 9K | Accepted future boundary | Named questions, leakage-safe temporal/regime evaluation, calibration/discrimination/abstention/stability/utility, shadow/rollback, and a mandatory approved data strategy before training. |

## Primary, Official, And Peer-Reviewed Domain Sources

| Source | Type and access | What it supports | Limitation / rejected overreach |
|---|---|---|---|
| [NIST AI RMF 1.0](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf) and [NIST AI RMF Playbook](https://airc.nist.gov/airmf-resources/playbook/) | US government framework; accessed 2026-08-25; RMF 1.0 is under revision | Govern/map/measure/manage lifecycle, documented risk, TEVV, monitoring, human roles, intervention, and accountable go/no-go decisions. | Voluntary, broad guidance; not a Markeitech statistical method, threshold, or regulatory claim. Tailor rather than copy as a checklist. |
| [Federal Reserve SR 11-7, Supervisory Guidance on Model Risk Management](https://www.federalreserve.gov/boarddocs/srletters/2011/sr1107a1.pdf) | Official supervisory guidance, 2011; accessed 2026-08-25 | Conceptual soundness, independent validation, ongoing monitoring, benchmarking, limitations, change control, audit, and use restrictions. | Written for regulated banking organizations. Used as strong governance inspiration, not a claim that Markeitech is regulated by it. |
| S. Kaufman, S. Rosset, C. Perlich, [Leakage in Data Mining: Formulation, Detection, and Avoidance](https://doi.org/10.1145/2020408.2020496), ACM KDD 2011 | Peer-reviewed primary paper; accessed 2026-08-25 | Formalizes illegitimate information and the no-time-machine requirement; motivates explicit as-of contracts and leakage threat modeling. | General data-mining treatment; does not by itself solve revisions, contracts, overlapping labels, or market feedback. |
| H. White, [A Reality Check for Data Snooping](https://doi.org/10.1111/1468-0262.00152), *Econometrica* 68(5), 2000 | Peer-reviewed primary paper; accessed 2026-08-25 | Repeated reuse of one time-series history for specification search can make chance results appear superior; supports explicit search accounting and protected evaluation. | One procedure is not mandated, and its assumptions must be established for the named dataset and decision. |
| D. Politis, J. Romano, [The Stationary Bootstrap](https://doi.org/10.1080/01621459.1994.10476870), *JASA* 89(428), 1994 | Peer-reviewed primary paper; accessed 2026-08-25 | Provides one dependence-aware resampling foundation for standard errors and confidence regions under weakly dependent stationary observations. | It is not a default method; stationarity and dependence assumptions may fail under market shift and must be justified. |
| [scikit-learn Common pitfalls and recommended practices](https://scikit-learn.org/stable/common_pitfalls.html) and [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) | Official versioned docs, displayed 1.9.0; accessed 2026-08-25 | Fit preprocessing only on training subsets; ordinary random CV is inappropriate for ordered deployment; exposes a configurable gap mechanism. | Documentation is current and drift-prone. No dependency is approved or added. `TimeSeriesSplit` does not solve as-of revisions, overlap, grouping, regimes, or feedback. |
| [scikit-learn Probability calibration](https://scikit-learn.org/stable/modules/calibration.html) | Official versioned docs, displayed 1.9.0; accessed 2026-08-25 | Reliability diagrams, calibration procedures, and the warning that an aggregate proper score mixes calibration, resolution, and uncertainty. | Not a mandated library or calibration method; bins and methods are data-dependent policy candidates. |
| C. Guo, G. Pleiss, Y. Sun, K. Weinberger, [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599), ICML 2017 | Peer-reviewed conference paper/preprint; accessed 2026-08-25 | Demonstrates that discrimination and probability calibration differ and post-hoc calibration must be evaluated. | Neural-network/image/text results do not establish a preferred model or calibrator for Markeitech. |
| A. Angelopoulos, S. Bates, [A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification](https://arxiv.org/abs/2107.07511), 2022 revision | Scholarly tutorial/preprint; accessed 2026-08-25 | Makes uncertainty/coverage assumptions and scope explicit; supports distinguishing marginal coverage, shift, and abstention. | Conformal prediction is not prescribed. Exchangeability or sequential assumptions must be justified; coverage is not utility or conditional validity. |
| J. Gama et al., [A Survey on Concept Drift Adaptation](https://doi.org/10.1145/2523813), ACM Computing Surveys 46(4), 2014 | Peer-reviewed survey; accessed 2026-08-25 | Separates evolving streams, drift detection/adaptation strategies, and evaluation concerns. | Drift alarms do not prove cause or grant adaptation authority. Market regimes are not assumed to be stable labeled concepts. |
| A. P. Dawid, [Statistical Theory: The Prequential Approach](https://rss.onlinelibrary.wiley.com/doi/10.2307/2981683), JRSS A 1984 | Peer-reviewed statistical paper; accessed 2026-08-25 | Supports sequential prediction assessment using information available before each outcome. | Prequential evaluation does not waive delayed-label, dependence, feedback, or governance constraints. |
| T. Gebru et al., [Datasheets for Datasets](https://arxiv.org/abs/1803.09010), 2018/2021 publication lineage | Peer-reviewed proposal/preprint; accessed 2026-08-25 | Dataset motivation, composition, collection, intended use, and limitations should be documented. | A datasheet does not create licensing rights, validate labels, or authorize retention. |
| M. Mitchell et al., [Model Cards for Model Reporting](https://arxiv.org/abs/1810.03993), FAT* 2019 | Peer-reviewed proposal/preprint; accessed 2026-08-25 | Intended use, evaluation context, performance slices, and limitations belong with a model identity. | Reporting cannot replace independent validation, monitoring, or policy enforcement. |

## External Agent-Skill Census

External skills were treated as packaging inspiration only. No text was copied.

| Repository and inspected revision | License evidence | Learned | Rejected / not copied |
|---|---|---|---|
| [openai/skills](https://github.com/openai/skills), commit `49f948faa9258a0c61caceaf225e179651397431`; inspected `skills/.system/skill-creator/SKILL.md` | GitHub license endpoint returned no detected repository license on 2026-08-25. | Precise trigger metadata, progressive disclosure, linked references, compact entrypoint, and synchronized `agents/openai.yaml`. | No prose, scripts, templates, or unlicensed material copied. Generic creation/evaluation machinery was unnecessary for this project-scoped advisor. |
| [anthropics/skills](https://github.com/anthropics/skills), commit `3b3fad96af16a10759d930941b4520ba0c40edae`; inspected repository README and template/skill-creator structure | No single machine-detected root license on 2026-08-25. README says many examples are Apache-2.0 while document skills are source-available; licensing is file/folder-specific. | Self-contained `SKILL.md`, frontmatter discoverability, imperative workflows, progressive disclosure, and references for detailed modes. | No source-available document material, wording, scripts, templates, or ambiguous-license content copied. Claude-specific packaging and broad eval loops were not adopted. |
| Existing repository-owned Kite router and Nautilus expert at commit `c6af7a5` | Markeitech proprietary repository material | Project-scoped naming, read-only custom advisor, evidence labels, mandatory context, stop gates, decision artifact, and `agents/openai.yaml` convention. | Nautilus native-capability doctrine was not generalized into statistics. This advisor does not impersonate framework, market, options, provider, security, or human-factors expertise. |

## Source-Fidelity Rules

- Distinguish a peer-reviewed result, official documentation, institutionally credible governance
  guidance, local verified contract, measured Markeitech evidence, and recommendation.
- Record access date and displayed version for mutable documentation. Never turn an example default,
  paper result, or library API into a permanent Markeitech threshold, dependency, or method.
- Verify current APIs before citing exact behavior. Research evidence cannot authorize a package,
  schema, persistence, model, label, live run, or trading semantic.
- Map repeated-search, multiplicity, effective-support, and dependence-aware uncertainty claims to
  a source whose assumptions fit the named dataset; do not invoke a bootstrap or correction by
  vocabulary alone.
- Record unavailable, paywalled, superseded, version-mismatched, or conflicting evidence as unknown.
- Respect source licenses and quotation limits. Prefer paraphrase and attribution; do not vendor
  third-party source into the skill.
