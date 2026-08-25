# Market Evidence Validation Protocol

Use this protocol for formula reviews, analytical acceptance, reconciliation, or investigation of
a metric discrepancy. Select the checks that can change the downstream-use recommendation; do not
perform a large generic profile in place of testing the material claims.

## 1. Frame The Claim

Record:

- exact metric/output identity, definition version, schema version, and configuration version;
- intended consumer and decision, required fidelity, acceptable health, and abstention behavior;
- instrument, raw symbol, contract, venue, asset class, provider, selector, and entitlement scope;
- session, exchange trade date, timezone, calendar/version, horizon, window, grain, and cadence;
- formula, inputs, units, precision, rounding point, normalization, warmup, nullability, and retained
  state; and
- source, transformation, causation/correlation, and publication lineage.

If these fields cannot be recovered and the omission can change meaning, stop with
`NOT_VERIFIED`.

## 2. Trace The Evidence Chain

Trace at least one accepted observation and every material branch from provider/native input to
the published value. Distinguish:

`provider event time -> local initialization/receive time -> calculation time -> effective/as-of time -> publication time`

For each transformation, identify owner, input and output grain, ordering key, inclusion boundary,
deduplication key, revision/conflict policy, fidelity change, missing-input behavior, and parameter
version. Confirm that lineage survives aggregation rather than becoming a detached scalar.

## 3. Validate Time And Session Meaning

- Keep instants in UTC; use an explicit IANA zone for civil sessions and record the tzdb/calendar
  version when reproducibility depends on it.
- Do not treat a numeric offset or abbreviation as a durable timezone.
- Test DST spring gaps, fall folds, ordinary days, holidays, early closes, overnight sessions,
  exchange trade-date rollover, and windows spanning calendar dates when applicable.
- Establish whether a bar timestamp represents open, close, or provider-specific labeling.
- Establish interval convention, for example `[start, end)`, and test observations exactly before,
  at, and after both boundaries.
- Use event time for market grouping. Treat receive/init/calculation time as operational latency
  evidence unless the metric contract explicitly requires otherwise.
- Cross-instrument comparisons require a shared exact UTC interval plus per-input freshness and
  session applicability; matching local clock labels are insufficient.

## 4. Validate Grain, Aggregation, And Overlap

- State the natural observation grain and candidate key before aggregating.
- Compare row/observation counts, unique keys, time coverage, and source coverage before and after
  joins, resampling, grouping, or source union.
- Detect many-to-many expansion, average-of-averages, denominator drift, mixed complete/partial
  intervals, hidden partial bars, and accidental cross-session aggregation.
- Reconcile exact duplicates separately from same-key/same-value duplicates, revisions, and
  same-key/conflicting-value observations.
- For historical/live convergence, enumerate the overlap interval and keys; prove one deterministic
  owner per accepted observation, exact-duplicate idempotence, conflict visibility, stable results
  under arrival reordering, and no gap at the handoff.
- Treat watermark or lateness thresholds as progress policy, not proof of completeness. Late data
  must be accepted, revised, quarantined, or rejected by explicit contract.

## 5. Validate Formula Correctness

Use evidence independent of the implementation under review, proportionate to the claim: a
hand-calculated exact example, separately implemented calculation, independently sourced comparable
oracle, or defining mathematical/metamorphic invariant. Do not generate expected values with the
code under review or merely restate its formula. External chart or provider parity is additionally
required only when the claim includes parity with that representation.

Check as applicable:

- dimensional consistency and unit conversion;
- hand-calculated minimal examples;
- zero, one-observation, minimum-warmup, empty, all-null, constant, negative, extreme, and
  high-precision inputs;
- denominator zero and near-zero behavior;
- monotonicity, symmetry, translation, scale, conservation, additivity, boundedness, identity, or
  idempotence properties implied by the definition;
- partition/recombination equivalence when the metric is aggregatable;
- invariance to exact-duplicate replay and permitted arrival reorderings;
- sensitivity around thresholds, window boundaries, rounding points, and configuration bounds;
- stable missingness/fidelity behavior under removal of each required input; and
- no future information, look-ahead, survivorship, or post-outcome leakage.

Numerical tolerance must name comparison type, absolute/relative units, precision, rounding stage,
authorized bounds, and rationale. It is typed, bounded, versioned configuration or an explicit
policy candidate, never an unexplained validator constant.

## 6. Establish A Comparable Oracle

Before comparing with an operator chart, provider export, exchange source, or second system,
reconcile:

- exact contract and venue;
- source/provider and reported versus derived status;
- selector such as trades, midpoint, bid, ask, or settlement;
- adjustment, filtering, correction, and revision policy;
- timezone, session, trade date, holidays, and early closes;
- bar boundary/alignment, interval inclusion, grain, precision, and rounding;
- visible/fixed/session range and study parameters; and
- as-of/download time and source version.

A mismatch is a finding to investigate. A match is calibration evidence only until independent
formula and boundary checks also pass.

## 7. Recommend A Disposition

- `RECOMMEND_ADMISSIBLE`: exact reviewed version and scope meet every material gate; residual
  unknowns cannot change the downstream meaning within that scope.
- `RECOMMEND_ADMISSIBLE_WITH_LIMITS`: directionally or conditionally usable only under named
  fidelity, health, session, provider, instrument, or consumer constraints. The downstream
  contract must explicitly support those limits before Kite recommends use.
- `RECOMMEND_REJECTED`: a demonstrated material error, contradiction, fidelity breach, or
  unsupported claim makes the value unsafe for the proposed use.
- `NOT_VERIFIED`: missing source, independent check, specification, configuration, or acceptance
  evidence prevents a defensible conclusion.

These are recommendations to Kite and Markeitect, not runtime authorization, product approval,
review acceptance, or release state. Do not average findings into a confidence score that conceals
a hard gate.

## Evidence Validation Matrix

Produce one row per material requirement:

| Requirement | Exact contract and scope | Evidence inspected | Independent check or invariant | Result | Limits or conflict | Required next evidence |
|---|---|---|---|---|---|---|

Use `PASS`, `FAIL`, `PARTIAL`, or `NOT_RUN` for result. A row is not `PASS` merely because a field
exists, code executes, or a test asserts the implementation's own output.

## Severity

- **Critical:** can recommend fabricated, mis-timed, duplicated, stale, wrong-contract, or
  wrong-fidelity evidence for Sir Loke or systematically reverse/replace market meaning.
- **High:** materially changes a key metric, session, baseline, cross-instrument comparison, or
  downstream state for an in-scope case.
- **Medium:** bounded correctness or observability weakness with a known containment path.
- **Low:** clarity or reproducibility weakness that does not change the current result.

Order the report by decision impact, not file order.
