# Evaluation And Governance Protocol

Use this reference whenever the task concerns features, labels, datasets, evaluation, calibration,
uncertainty, model monitoring, online learning, adaptive parameters, or optimization.

## 1. Define A Named Decision

Record the consumer, decision timestamp, prediction horizon, eligible population, output meaning,
permitted action, prohibited inference, model-selective abstention behavior, and simplest
deterministic or constant baseline. Separate prediction quality from trading utility and
contract-expression quality. The statistical advisor may test a definition's coherence; Markeitect
and the relevant market-domain advisor own trading meaning.

Reject targets such as `price goes up`, universal opportunity scores, or labels reverse-engineered
from a desired model. A candidate label is not validated merely because it is calculable.

## 2. Feature Validity And The As-Of Ledger

For every feature, require:

- stable feature identity and semantic version;
- formula, units, parameters, scope, source, fidelity, health, missingness, and bounded state;
- provider event time, system receipt time, publication time, revision/effective time, and the
  exact prediction cutoff;
- instrument, venue, session, contract, expiry/roll, and universe-membership identity when they
  affect meaning;
- warmup and availability rules, including restart state;
- deterministic handling of gaps, late arrivals, duplicates, corrections, revisions, and
  unavailable evidence; and
- a reproducible proof that only information knowable at the cutoff contributed.

Formula, units, timestamp/session/grain meaning, source lineage, revision handling, fidelity, and
analytical admissibility remain owned by the market-evidence validation advisor. When any of those
properties materially controls the statistical conclusion, record its exact disposition and
limits in the as-of ledger. Statistical review begins from that accepted or explicitly limited
evidence contract; it does not independently recalculate market truth.

Maintain an as-of ledger for every evaluation row: prediction identity, cutoff, feature-set and
definition versions, exact source revisions, label identity/version, and eventual label-availability
time. Current or corrected state must not be substituted for the state visible at prediction time.

Feature usefulness is measured against a named decision and baseline. Stability, missingness, cost,
and incremental value matter alongside association. Importance scores are diagnostic, not causal
evidence and not permission to retain a feature.

## 3. Label And Outcome Contract

Require a label card with:

- named question, population, anchor event/opportunity, horizon, clock and session semantics;
- exact outcome formula, source, price/quote basis, fees or fill assumptions if relevant, and unit;
- observation start/end, information cutoff, earliest label availability, and revision policy;
- positive/negative/neutral/abstain or continuous semantics;
- censoring, truncation, expiry, early close, halt, missingness, conflicting evidence, and operator
  intervention handling;
- entity and contract identity, overlap rules, and whether multiple rows share one outcome episode;
- provenance, licensing, retention, definition version, and approval owner; and
- prohibited uses and known construct-validity limits.

Operator feedback and trade outcomes are selected and intervention-affected evidence. Do not treat
them as unbiased ground truth without an explicit causal/selection analysis. Screenshots and notes
remain research evidence unless a separately approved, reproducible annotation protocol exists.

## 4. Leakage Threat Model

Audit at least these paths:

- **Future information:** feature timestamps or aggregations cross the prediction cutoff.
- **Revision leakage:** final entity/bar/reference values replace the version then visible.
- **Preprocessing leakage:** imputation, scaling, encoding, feature selection, calibration, or
  missingness rules are fit outside the training fold.
- **Selection leakage:** the same validation or holdout evidence guides feature engineering,
  targets, model families, hyperparameters, thresholds, calibration, or final acceptance.
- **Outcome overlap:** training rows' label windows overlap evaluation rows or cross a fold
  boundary; derive gaps/embargoes from actual information and outcome windows rather than doctrine.
- **Identity leakage:** adjacent contracts, duplicate episodes, revisions, or correlated rows split
  across train and evaluation partitions as if independent.
- **Universe/survivorship leakage:** membership or exclusions use later liquidity, activity,
  availability, or outcome knowledge.
- **Cross-instrument/calendar leakage:** timestamps are aligned by label or completed interval that
  was not simultaneously available across sources.
- **Feedback leakage:** operator/model actions alter later data, labels, or selection probabilities.
- **Proxy leakage:** a field encodes the target, future availability, manual disposition, or
  post-outcome process rather than genuine pre-decision evidence.

Document a negative-control or deliberate leakage test where feasible. Unexpectedly large gains
are a reason to investigate, not validation.

## 5. Evaluation Design

Predeclare before examining final results:

- chronological train/calibration/validation/forward-holdout boundaries and why they match the
  deployment question;
- fold-specific preprocessing and selection; nested evaluation when model or policy search uses
  validation evidence;
- gap/embargo/grouping rules derived from overlap, revision, and shared-episode structure;
- expanding versus bounded rolling windows as configurable candidates, with training-data-only
  selection and regime-sensitivity reporting;
- instrument, contract, session, horizon, evidence-health, volatility/regime, and missingness
  slices justified by the decision—never invented merely to find a winning subgroup;
- constant, historical-frequency, simple deterministic, current-policy, and other credible
  baselines appropriate to the decision;
- metrics for discrimination/ranking, calibration, model-selective abstention/coverage, stability,
  latency/resource cost, and decision utility, kept separate;
- dependence-aware confidence intervals or uncertainty analysis, sample counts, event counts,
  effective support caveats, and multiple-comparison/search accounting; and
- frozen acceptance criteria, including non-inferiority, rejection, and model-selective-abstention
  conditions.

Random shuffles are inappropriate for claims about forward temporal use. A time-series splitter is
only a mechanism: it does not solve revision, overlap, grouping, regime coverage, contract, or
feedback leakage. Do not call an offline chronological study a Markeitech backtest or replay while
those capabilities remain out of scope; if the approved data strategy cannot support evaluation
without reopening those decisions, stop.

## 6. Calibration, Uncertainty, And Model-Selective Abstention

For probabilistic outputs:

- define what probability is estimated, for which population, horizon, and conditioning evidence;
- reserve calibration data that is separate from base-model fitting and protected from final
  evaluation; fit every calibration step inside the selection protocol;
- report reliability by supported probability regions plus a proper score with decomposition or
  complementary discrimination evidence; do not infer calibration from one aggregate score;
- quantify sample support and uncertainty for reliability bins; avoid granular claims unsupported
  by outcomes;
- test temporal, session, instrument, contract, regime, and evidence-health sensitivity;
- state whether uncertainty is aleatoric, epistemic, sampling, model-selection, or distribution-
  shift uncertainty rather than collapsing them into one confidence field; and
- define model-selective abstention and out-of-envelope behavior before promotion.

Model-selective abstention means the evaluated model declines to produce an otherwise eligible
output or action class. It does not define evidence-health, Sir Loke, opportunity, operator-facing,
or tool-policy abstention; those remain with their owning evidence, product, and governance
contracts.

Conformal or other coverage claims apply only under their stated exchangeability, sequential, or
shift assumptions and to the tested population. Marginal coverage is not conditional validity,
trading utility, causal evidence, or immunity to market drift.

## 7. Monitoring And Promotion

Promotion is staged: `offline -> shadow -> advisory -> disabled/retired`, with any later mode
requiring explicit approval. Define:

- model, feature, label, dataset, calibration, policy, and configuration identities;
- training/evaluation windows, intended use, prohibited use, operating envelope, and expiry;
- input schema/quality, missingness, evidence-health, output, calibration, model-selective
  abstention, latency, resource, and error monitoring;
- delayed-label reconciliation and evaluation when outcomes become available;
- comparison to frozen baselines and champion/challenger evidence;
- alert thresholds as bounded configurable policy candidates with support, dwell, hysteresis,
  cooldown, severity, and false-alert review—not magic constants;
- explicit responses: investigate, degrade, model-abstain, disable, rollback, or seek approval; and
- independent review, operator override records, incidents, exceptions, and retirement criteria.

Freeze every shadow or advisory prediction before its outcome matures. The immutable prediction
record must include:

- prediction identity and UTC creation time;
- decision/episode identity and eligibility-contract version;
- model, code, feature, dataset, calibration, configuration, and model-selective-abstention-policy
  versions;
- the as-of information cutoff, immutable feature snapshot identity, and evidence health;
- raw score, probability, interval, or set plus the final model action class and any
  model-selective-abstention reason;
- expected label maturity and current label state;
- final label identity, version, provenance, and availability time when it becomes knowable; and
- monitoring inclusion or exclusion reason.

Preserve test-then-observe ordering: freeze the prediction first, attach the outcome only after it
is knowable, and record the effective training time if that outcome later enters a training set.
Keep unlabeled, delayed, corrected, censored, and excluded predictions visible rather than silently
shrinking the evaluated population.

Monitor these drift families separately:

- **source/availability drift:** missingness, latency, staleness, revisions, provider, or contract
  changes;
- **covariate drift:** feature-distribution change;
- **prediction drift:** score, class, uncertainty, and model-selective-abstention/coverage change;
- **prior/label drift:** outcome prevalence after labels mature;
- **conditional/performance drift:** change in the relationship between inputs, predictions, and
  mature outcomes;
- **calibration drift:** reliability change by time and supported slice; and
- **operational drift:** latency, resource, failure, or version mismatch.

Every monitor needs a versioned reference population/window, current window, statistic, sample
floor, warning/failure threshold, multiple-testing policy where relevant, delayed-label behavior,
owner, and deterministic response. An alarm is diagnostic evidence. It does not identify cause and
never authorizes automatic retraining or live parameter mutation.

## 8. Online Learning And Bounded Optimization

Default to no online update. Consider one only after static/shadow evidence demonstrates a named
need and the approved data strategy supplies sufficiently timely, valid labels.

Every candidate adaptation must declare:

- parameter/model identity, scope, unit, source, current value, approved minimum/maximum, step,
  rate, cadence, effective time, and expiry;
- whether it is startup-only, between-session, runtime-proposable, or frozen;
- objective vector and constraints, never a hidden universal scalar utility;
- minimum fresh sample/event support, evidence-health and regime eligibility, and delayed-label
  behavior;
- exploration budget, multiple-testing/search accounting, resource limits, and maximum cumulative
  change;
- shadow/challenger evidence and human approval required before effect;
- deterministic validation, rejection, audit, rollback, and safe state after restart or uncertainty;
  and
- monitoring for oscillation, feedback loops, boundary pinning, regime overreaction, degraded
  evidence, and objective gaming.

Optimization may propose an in-bounds typed intent; deterministic policy validates it. A model may
not write configuration, redefine labels/features, rewrite history, widen its own envelope, suppress
health, change evidence truth, or execute. Multi-objective tradeoffs remain visible to Markeitect.

## Readiness Outcomes

Use one of these bounded conclusions:

- `BLOCKED`: a material authority, data, label, as-of, leakage, licensing, or safety gate is absent.
- `RESEARCH_ONLY`: coherent hypothesis, but evidence is insufficient for a model or policy candidate.
- `EVALUATION_READY`: approved data/definitions can support the predeclared offline evaluation.
- `SHADOW_CANDIDATE`: evaluation clears frozen criteria; live influence remains prohibited.
- `ADVISORY_CANDIDATE`: shadow evidence clears approved criteria; Markeitect still decides promotion.
- `DEGRADE`, `ROLLBACK`, or `RETIRE`: monitored evidence no longer supports the operating envelope.

Never return `PRODUCTION_READY`, `AUTO_ADAPT`, or an execution authorization.
