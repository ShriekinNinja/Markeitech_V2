# V2 Stage 9C Session Measurements Plan

**Status:** Slices 1-3 accepted; Slice 4 implemented for local review

**Branch:** `v2-stage-9c-session-windows`

## Purpose

Stage 9D needs proven measurements before it can define honest session entities and durable
summaries. The accepted Stage 9C runtime currently publishes quote midpoint and spread quality.
It does not yet publish the completed-bar, session, prior-session, opening-range, gap, volatility,
efficiency, or compression measurements required by the first entity family.

This extension closes that dependency. It does not create entities or semantic market events.

## Product Boundary

This stage will:

- normalize completed bars into deterministic metric inputs;
- converge transient historical warmup and live completed bars without startup sequencing;
- calculate versioned session and prior-session measurements;
- calculate configurable opening-range and power-hour measurements;
- calculate numerical volatility, directional-efficiency, and compression/expansion inputs;
- publish typed `MetricValue` objects through the existing native data boundary;
- retain only bounded in-memory calculation state; and
- persist operational request/readiness/failure lifecycle only.

This stage will not:

- create session, opening-range, gap, level, zone, or opportunity entities;
- classify acceptance, rejection, trend, regime, compression, or expansion semantically;
- publish Discord market messages;
- store raw bars, historical batches, or every numerical metric value in PostgreSQL;
- infer order flow, CVD, buying, selling, absorption, or trapped participants from OHLCV bars;
- select a preferred instrument, option, direction, or trade; or
- implement replay, backtesting, ML, or agent behavior.

## Trading Calendar Versus Analytical Session

The existing calendar answers when an instrument or product is expected to trade and which trade
date owns an observation. It does not, by itself, define every analytical window Markeitect uses.

Analytical session profiles must therefore be explicit, typed, versioned, and configurable. A
profile may define:

- the primary session used for prior-session references;
- an overnight or premarket interval;
- one or more opening ranges;
- a power-hour interval relative to the primary-session close;
- whether volume-derived measurements are supported; and
- which parameters are eligible for later policy-controlled optimization.

No code may assume `09:30`, `16:00`, five minutes, fifteen minutes, or sixty minutes. Configuration
may initially select those values, but the implementation consumes named windows and validated
parameters.

## Recommended Architecture

```text
SessionStateActor
    -> authoritative trade date, phase, and phase boundaries

SessionMetricsActor
    -> declares historical dependencies through DataAcquisitionActor
    -> consumes transient HistoricalBatch data
    -> declares one shared live bar demand per selected instrument
    -> consumes native completed bars from Nautilus
    -> normalizes and reconciles historical/live observations
    -> calculates pure versioned metrics
    -> publishes MetricValue CustomData

DataAcquisitionActor
    -> remains the only provider-demand and historical-request owner

OperationalPersistenceActor
    -> stores demand, execution, readiness, conflict, and failure lifecycle
    -> does not store raw bars or numerical metric updates
```

The actor owns one analytical family only. Pure formulas, validation, window aggregation, and
historical/live reconciliation remain framework-independent modules with deterministic tests.

Runtime composition remains event-driven:

- session state, evidence snapshots, historical batches, live bars, and readiness may arrive in
  any order;
- no actor start order, sleeps, or arbitrary startup delays are allowed;
- missing inputs produce explicit warming/degraded values or bounded suppression according to the
  metric contract;
- failed requests remain retryable and observable; and
- unrelated acquisition, Watchlist, quote metrics, persistence, and Discord health continue.

## Configuration Model

The concrete TOML shape will be reviewed with the implementation, but it must express these
concepts without symbol-specific code.

### Family policy

- enabled state;
- required Watchlist capability used to select instruments;
- per-measurement live and historical dependency declarations;
- source, resolution, lookback, session scope, price basis, and required fidelity for each
  dependency;
- optional normalization or aggregation policy where the requested measurement requires it;
- parameter and algorithm versions;
- demand priority and retry cadence;
- evidence snapshot retry cadence;
- maximum retained bars per instrument/session;
- maximum output age and late-data tolerance;
- historical/live overlap policy;
- maximum active/completed sessions retained; and
- resource limits for instruments, historical observations, and publications.

### Analytical session profile

- stable profile ID and version;
- owning calendar ID;
- primary phase or calendar-relative named window;
- overnight/premarket window definition;
- opening-range definitions;
- power-hour offsets relative to the authoritative close;
- volume support policy;
- valid instrument classes or explicit capability scope; and
- exceptional-session behavior.

### Profile binding

Every instrument selected by an enabled measurement family must resolve to exactly one configured
analytical profile. Stage 9C uses explicit instrument bindings; it does not infer analytical meaning
from an exchange name or silently fall back to a calendar-day boundary.

Validation precedence and future extension are:

1. exact instrument binding;
2. a later explicitly configured group binding;
3. a later explicitly configured instrument-class binding; and
4. no match is a rejected capability, never a guessed profile.

The current startup configuration uses the first form. A future dynamic Watchlist-add intent must
include or policy-resolve an approved profile before session measurements may admit that instrument.
The instrument calendar and profile calendar must match. Separate profiles may share one calendar
when their analytical semantics differ; the initial configuration uses this to keep US equity/ETF
volume support separate from SPX/VIX index volume non-support.

### Parameter metadata

Every variable parameter must declare:

- ID, meaning, type, and unit;
- selected value and validation envelope;
- scope and source;
- parameter version and effective time;
- `dynamic` eligibility;
- startup-only or policy-controlled mutability; and
- rollback/audit identity.

`dynamic=true` means a later approved optimizer may propose a value inside policy limits. It does
not grant the current runtime permission to mutate configuration.

## Resolution-Selection Policy

There is no universal canonical timeframe, historical substrate, or timeframe pyramid. Each
measurement independently declares the smallest and cheapest dependency that preserves its
meaning:

- provider/source and price basis;
- exact resolution;
- bounded lookback or explicit time bounds;
- analytical-session scope and RTH/extended-hours policy;
- required volume and fidelity semantics; and
- whether direct provider bars, runtime aggregation, or validated fallback aggregation is allowed.

Examples are illustrative, not hard-coded policy:

| Measurement | Likely dependency | Reason |
|---|---|---|
| Previous-day OHLC | Direct daily bar when its provider/session semantics match the requested day | Intraday reconstruction adds no value |
| Opening range | Intraday bars precise enough for the configured boundary | The window cannot be recovered honestly from a daily bar |
| One-hour EMA | Direct hourly bars | The metric is defined on hourly observations |
| Weekly OHLC or structure | Direct weekly bars, or daily-to-weekly aggregation when explicit week/session control is required | Six months of one-minute history is unnecessary and operationally wasteful |
| Session VWAP estimate | Intraday price/volume bars meeting the approved fidelity contract | Daily OHLCV cannot reconstruct the path-dependent estimate |

One measurement does not automatically consume or derive from the timeframe below it. The
executor may share an already requested dependency only when source, resolution, bounds, session
scope, price basis, and fidelity are genuinely compatible. This is a resource optimization, never
an analytical assumption.

For the first **intraday session-measurement** implementation, a configurable one-minute
calculation interval remains the recommended input for measurements that need minute-level window
precision. Existing live five-second IB bars may be aggregated to that interval, and matching
historical one-minute bars may satisfy the same declared dependency. Both paths produce the same
internal `CompletedBarInput` contract. This choice does not require prior-day, daily, weekly, or
other measurements to use one-minute history.

The first aggregation boundary policy is explicitly `utc_fixed_intraday`. It permits only fixed
intraday intervals which divide a UTC day exactly and is intended for paths such as five-second to
one-minute aggregation. It is not valid for daily, weekly, RTH, Globex, exchange-local, or
session-anchored aggregation. Those measurements must declare a provider-native dependency or a
separate reviewed boundary policy.

Whenever direct provider bars and locally aggregated bars can represent the same requested
measurement, acceptance requires an equivalence fixture comparing interval identity, session
assignment, OHLCV, and resulting metric/entity output within configured tolerances. A mismatch is
reported as a fidelity difference; one representation never silently substitutes for the other.

## Completed-Bar Contract

Every normalized completed bar must carry:

- instrument and exact bar specification;
- calendar, analytical profile, trade date, and session/window identity;
- interval start and end in UTC nanoseconds;
- open, high, low, close, and volume;
- source path: historical provider bar or live aggregate;
- observed, received, and normalized timestamps;
- evidence health and fidelity;
- source observation references;
- completion status;
- revision/correction identity; and
- missing or conflict reasons.

Validation requires finite positive prices, `low <= open/close <= high`, non-negative volume,
aligned interval boundaries, and a completed interval. Unsupported volume is distinct from zero
volume.

## Historical And Live Convergence

The actor declares bounded history through the accepted Stage 9B protocol. It never calls IB
directly.

Recommended initial request strategy:

1. expand each approved measurement into its exact bounded dependency contract;
2. request direct provider bars at the declared resolution when their source/session semantics
   satisfy that contract;
3. aggregate only where the declaration explicitly permits it;
4. share requests only when selectors, resolutions, price basis, fidelity, session scope, and
   resolved bounds are compatible; and
5. retain no raw history after the approved measurement state has been built.

This may produce a direct daily request for previous-day OHLC, minute-level requests for an
opening range or session VWAP estimate, and a different bounded resolution for rolling numerical
inputs. The actor does not widen a fine-grained request merely to make it a common source for
unrelated measurements.

Observations are keyed by instrument, declared dependency/bar specification, and interval end.

- Exact duplicates are idempotent.
- A live bar may arrive before warmup and is retained within the configured bound.
- Warmup completion merges by event time, not arrival order.
- A conflicting observation for the same key is never silently overwritten.
- The recommended first conflict policy is `reject_conflict`: preserve the accepted
  observation, degrade affected output, and emit an operational conflict record.
- Other policies may be admitted later only as explicit configured/versioned choices.
- Late observations inside the retained window may produce a new metric revision.
- Observations outside the retained/revision window are rejected operationally.
- A later revision never pretends it was available earlier.

## Measurement Catalog

All outputs use the existing `MetricDefinition`, `MetricParameterSet`, `MetricValue`, registry,
health, fidelity, evidence-reference, and revision contracts. Metric IDs below describe proposed
stable meanings; exact names and formulas are reviewed before implementation.

### 9C-S1: Completed-Bar Foundation

| Measurement | Decision question | Recommended definition |
|---|---|---|
| Completed OHLCV | What did the completed calculation interval report? | Separate open/high/low/close/volume values sharing one evidence group |
| Simple return | How far did close move from the preceding compatible close? | `close / prior_close - 1` |
| True range | What span did this interval realize including a prior-close gap? | `max(high-low, abs(high-prior_close), abs(low-prior_close))` |

The first bar has a null return and gap-aware range when no valid prior close exists. Missing or
unsupported volume produces an explained null; it is never replaced with zero.

### 9C-S2: Active-Session Measurements

| Measurement | Meaning |
|---|---|
| Session open/high/low/latest close | Running values for the configured analytical session |
| Session range | `high - low` |
| Session location | `(latest_close - low) / (high - low)`, null for zero range |
| Session volume | Sum of supported completed-bar volume |
| Session bar-VWAP estimate | Configured bar-price basis weighted by supported bar volume |

The VWAP output must be named and documented as a bar-derived estimate unless the selected input
provides an authoritative reported WAP. It cannot be presented as trade-level VWAP.

### 9C-S3: Previous-Session References

After the configured primary session is complete, publish immutable measurements for:

- open, high, low, close, range, and supported volume;
- bar-VWAP estimate where supported;
- session return; and
- source completeness, coverage, and fidelity.

Identity includes instrument, analytical profile, trade date, metric/parameter versions, and exact
session bounds. A changed formula creates a new metric version rather than rewriting history.

### 9C-S4: Overnight And Gap Measurements

Keep two concepts separate:

- **Indicative gap:** latest valid overnight/premarket reference minus previous primary-session
  close. It evolves before the primary open.
- **Opening gap:** primary-session open minus previous primary-session close. It becomes immutable
  after the opening observation is accepted.

Publish each in price units and ratio form. Also publish overnight open/high/low/latest close and
range when the profile defines an eligible window. Gap fill, hold, acceptance, or rejection are
entity/event semantics and remain outside this stage.

### 9C-S5: Opening Ranges

For every configured opening-range definition, publish:

- start/end and completion state;
- running then final high, low, and range;
- latest distance above the high and below the low in price units and ratio form; and
- coverage/fidelity.

An opening range is a parameterized family, not hard-coded OR5/OR15 logic. Before completion its
measurements are explicitly developing. Stage 9D will decide entity lifecycle; Stage 9E will decide
which transitions deserve events.

### 9C-S6: Power-Hour Measurements

For the configured close-relative interval, publish a compact numerical set:

- open, high, low, close, range, and return;
- supported volume and bar-VWAP estimate;
- directional efficiency; and
- completeness/coverage.

These are OHLCV-derived measurements. They do not claim aggressive buying/selling, delta, CVD,
absorption, or trapped participants.

### 9C-S7: Volatility, Efficiency, And Compression Inputs

| Measurement | Recommended numerical definition |
|---|---|
| Realized log-return magnitude | Unannualized `sqrt(sum(log_return^2))` over a configured completed-bar window |
| Average true range | Mean true range over a configured completed-bar window |
| Directional efficiency | `abs(last_close-first_close) / sum(abs(close_change))`, null when denominator is zero |
| Rolling price range | Highest high minus lowest low over one configured candidate window |
| Range expansion ratio | Candidate rolling price range divided by a comparable configured trailing baseline |
| Range percentile | Candidate rolling price range rank within a bounded trailing reference distribution |

The stage publishes numerical inputs only. Labels such as `TRENDING`, `ROTATING`, `COMPRESSED`, or
`EXPANDING` require separately reviewed state/entity/event policy.

#### Reviewed Multi-Horizon Policy

Context, expansion detection, state interpretation, and any later trade action answer different
questions. They must not inherit one universal horizon merely because they consume the same bar
stream. In particular, a consolidating market benefits from broader context that suppresses chop,
while a shorter expansion detector may remain active to notice a genuine break. Once movement is
established, a later directional selector may tighten around recent evidence so stale balance data
does not dilute the move.

Stage 9C therefore calculates a bounded, configuration-owned bank of candidate horizons. It does
not choose one authoritative horizon, mutate subscriptions from an unreviewed heuristic, or publish
an action. The initial reviewed candidate envelopes are:

| Family | Context candidates | Expansion candidates |
|---|---|---|
| Fast, one-minute inputs | 20m, 30m, 45m, 60m | 10m, 15m, 23m, 30m |
| Tactical, five-minute inputs | 2h, 3h, 4h, 6h | 1h, 90m, 2h, 3h |
| Structural intraday, fifteen-minute inputs | 4h, 6h, 8h, 12h | 2h, 3h, 4h, 6h |

The operator-selected defaults remain 45 minutes of one-minute inputs, four hours of five-minute
inputs, and eight hours of fifteen-minute inputs. These defaults are not permanent preferences.
Candidate activation, resolution, duration, bounds, step, historical selector, minimum evidence,
and dynamic eligibility are versioned configuration. Historical dependencies remain
purpose-specific; no universal base timeframe or automatic resolution pyramid is introduced.

Every candidate publishes independently with exact window identity, session/phase composition,
coverage, fidelity, and lineage. A current rolling price range and its baseline must use equal
durations; a shorter expansion candidate may coexist with broader context, but it must not be
divided by a longer-duration baseline. Baseline observations exclude the current window and any
evidence prohibited by the eventual comparison policy.

#### Later Adaptive Selection

A separately reviewed bounded selector may later identify an effective context or detection
horizon for a specific action. Its first candidate policy may combine:

- normalized EMA slope, expressed relative to volatility and elapsed bars rather than raw price;
- directional efficiency and volatility/range expansion;
- agreement or instability between neighboring candidate horizons;
- evidence coverage, health, and session composition; and
- persistence, hysteresis, minimum dwell time, and hard horizon bounds.

The intended behavior is action-dependent: broader context while consolidation would make a tight
window easy to chop, and tighter recent evidence while an established move would make old balance
data misleading. Expansion detection remains independently selectable and need not use the context
horizon or a fixed fraction of it.

EMA slope is evidence, not sole authority. Raw slope is not comparable across instruments or
volatility regimes, and an EMA-only selector can lag transitions or chatter. A later competing
policy may use bounded change-point detection: expand while the observed return/range distribution
is stable, contract after a meaningful distribution change, and grow again as the new condition
stabilizes. Both policies must be replayable from cited evidence, versioned, independently
evaluated, and permitted to abstain.

Adaptive selection belongs to a later reviewed state/policy stage. Stage 9C's responsibility ends
at trustworthy candidate measurements and the evidence required to compare selection policies.

#### Reviewed Range Baselines And Percentiles

Range expansion has two distinct comparison questions. Recent-regime comparison asks whether price
is expanding relative to its immediate behavior. Phase-matched comparison asks whether that range
is unusual for the same authoritative session phase and offset. Neither reference can replace the
other, and Stage 9C must not blend them into one score.

For every active range candidate, publish the observed rolling price range plus independently
healthy recent and phase-matched comparisons:

- `rolling_price_range` is the highest high minus the lowest low over the candidate window;
- `expansion_ratio_recent` divides that range by the median of eligible recent windows;
- `expansion_ratio_phase` divides it by the median of eligible phase-matched windows;
- `range_percentile_recent` ranks it inside the recent reference distribution; and
- `range_percentile_phase` ranks it inside the phase-matched reference distribution.

The recent baseline uses prior completed, non-overlapping windows with the same input resolution
and duration. It adapts to the immediately preceding regime. The phase-matched baseline uses the
equivalent duration anchored at the same offset inside the same authoritative session phase across
prior valid sessions. It preserves time-of-day/session seasonality and never silently substitutes
another phase. Early-close or interrupted-session windows that do not provide the required interval
are excluded with an explained evidence reason.

An eligible reference sample must:

- use the same input resolution and exact duration as the current candidate;
- exclude the current window and avoid overlap with another sample in that baseline;
- satisfy the configured coverage, evidence-health, and fidelity requirements;
- retain its calendar, trade date, phase, phase offset, and boundary-crossing lineage; and
- remain independent of samples rejected for missing, conflicting, or prohibited evidence.

The initial recent reference count is 20, configurable from 8 through 64. The initial phase-matched
session count is 10, configurable from 5 through 30. Counts, bounds, steps, dynamic eligibility,
minimum valid samples, and parameter version/effective UTC time are configuration. If one baseline
lacks its minimum evidence, only that comparison remains `WARMING` or `UNAVAILABLE`; the rolling
range and the other comparison continue independently. A zero median produces an explained null
ratio, never infinity.

Both percentiles use an empirical midrank definition:

```text
(count(reference < current) + 0.5 * count(reference == current)) / reference_count
```

Every percentile publishes its eligible reference count and baseline identity. Repeated equal
ranges therefore receive a neutral tie treatment, while a small sample cannot masquerade as a
well-supported distribution. Numerical ratios and percentiles remain evidence inputs; Stage 9C
does not assign compressed, expanding, ordinary, exceptional, or trade-action labels.

## Health, Fidelity, And Null Behavior

Every output states exact health, fidelity, evidence references, coverage, missing reasons, and
session alignment.

- Historical warmup pending: `WARMING`, with explained null where history is required.
- Current bars healthy but prior session missing: active-session values may be `READY` while gap
  values remain unavailable.
- Index volume unsupported: price metrics remain valid while volume/VWAP metrics are explicitly
  unsupported or null.
- Missing bars inside a cumulative window: output is `DEGRADED` with coverage, not silently
  complete.
- Closed market with a completed immutable prior-session reference: the reference remains valid;
  live measurements follow their own dormant/stale contract.

Metric health is per output. One unavailable volume input must not disable unrelated price
measurements or another instrument.

## Bounded State

Per selected instrument/profile, retain only:

- configured dependency observations needed by approved measurements and windows;
- current and immediately previous session accumulators;
- configured opening-range accumulators;
- the previous-session reference needed for gap calculations;
- bounded rolling return/range samples; and
- deduplication, revision, evidence, and publication timestamps.

All cardinality, time, and observation bounds are validated at startup. Raw history is discarded
after it no longer contributes to an approved active calculation.

## Persistence Boundary

PostgreSQL records analytical demand, historical execution/readiness, capability readiness/failure,
overlap conflicts, rejected corrections, resource failures, and configuration/algorithm identity.

PostgreSQL does not yet record raw bars, every completed-bar metric, every running session update,
or the prior-session/power-hour durable summary. The compact summary belongs to Stage 9D after its
identity, lifecycle, commit-before-publication, and restart contract is approved.

### Accepted Slice 2 Preflight Policies

- Completed-bar foundation warmup requests two observations and may request at most four. This is
  the real request envelope, not a placeholder budget.
- Historical and live observations share one semantic interval identity.
- The first accepted completed interval is preserved. An unequal later copy is rejected as a
  conflict, degrades affected evidence, and produces an operational audit event.
- Provider bar revisions are unsupported in this stage and are rejected; the IB adapter remains
  configured with revised-bar handling disabled.
- Metric definitions carry formula, normalization, applicability, known failure modes, priority,
  expected fidelity, and allowed runtime fidelities.
- Parameter source, version, and explicit UTC effective time are configuration-owned and must be
  copied into future `MetricParameterSet` and `MetricValue` publication.
- Native provider bars may honestly produce `REPORTED` values; validated local aggregation produces
  `DERIVED`; incomplete/degraded paths may produce only declared `PARTIAL` or `UNAVAILABLE` values.
- Provider timestamps are interpreted only through the configured `timestamp_policy`; the initial
  IB external-bar profile declares `interval_start`, and changing that boundary is a reviewed
  configuration decision rather than an adapter assumption.

## Failure Isolation And Recovery

- One instrument's invalid bar or failed warmup cannot stop another instrument.
- One unavailable measurement cannot stop unrelated metric families.
- Provider disconnect preserves bounded state but marks outputs through evidence health.
- Reconnect reconciles demand through the existing acquisition owner.
- Historical timeout/retry uses Stage 9B policy independently of live processing.
- Actor exceptions are supervised without blocking acquisition.
- Restart rebuilds transient state from bounded history; no replay store is required.
- Shutdown releases demand, cancels timers, drains publication work, and reports exact counters.

## Delivery Slices

### Slice 1: Contracts And Pure Bar Normalization

- Add completed-bar input and analytical-session profile contracts.
- Add config parsing/validation and metric registry entries.
- Implement pure validation, configured aggregation, deduplication, and conflict detection.
- Test UTC/session alignment, duplicates, conflicts, late data, and resource bounds.

**Gate:** deterministic inputs and identities are approved and implemented.

### Slice 2: Historical/Live Runtime Convergence

- Add the session-metrics actor.
- Declare shared live bar and bounded historical demands.
- Consume historical batches, readiness, session state, evidence snapshots, and native live bars.
- Publish completed-bar foundation metrics with exact lineage.

**Gate:** history and live bars converge in either arrival order without duplicate intervals or
provider ownership leakage.

**Implementation status:** the actor, demand wiring, timestamp policy, bounded aggregation,
foundation metric publication, and live-first recalculation path are enabled and live-accepted.
The acceptance run covered all 18 configured instruments, converged history and live bars in the
same actor, published 1,281 values from 183 accepted bars, and reported no calculation failure,
duplicate, or conflict. Closed-session `recent_completed` dependencies degraded independently and
did not block unrelated work.

### Slice 3: Session, Previous-Session, Overnight, And Gap Metrics

- Implement active-session accumulators.
- Implement immutable prior-session references.
- Implement indicative and opening gaps.
- Prove unsupported-volume isolation.

**Gate:** session references match an independent chart across restart and rollover.

**Accepted implementation policy:**

- Keep the completed-bar foundation intact and project session references through a separate,
  bounded state component owned by the same actor.
- Request each historical purpose through its exact calendar-aware window. Active-session warmup
  uses session-to-date, previous-session evidence uses one completed configured primary phase,
  and overnight evidence is requested only for profiles that explicitly enable an eligible phase.
- Use a separately configured historical selector for these references; it need not match the
  one-minute completed-bar foundation selector.
- Merge live completed bars from the end of the last historical interval actually accepted, not
  from the request's later as-of timestamp, so history-first and live-first arrival produce the
  same state without either double-counting overlap or dropping a valid live tail.
- Require direct boundary evidence for anchor semantics. A mid-session first observation is not a
  session open, and an incomplete prior-session tail is not a prior close; dependent return and gap
  values remain explicitly unavailable until those anchors are observed.
- Calculate coverage from represented time, carry source health and fidelity per output, and let
  active-session, previous-session, overnight, and gap families degrade independently.
- Publish prior-session and opening-gap values as immutable once their complete inputs are
  accepted. Indicative gap remains developing while its overnight reference changes.
- Profiles without an approved overnight phase publish explained unavailable overnight and
  indicative-gap values; they never reinterpret a primary session as overnight evidence.
- Numerical values remain transient. PostgreSQL receives dependency demand, execution, readiness,
  rejection, conflict, and resource lifecycle facts only; durable analytical summaries wait for
  Stage 9D.

### Slice 4: Opening Range And Power Hour

- Implement configurable opening-range families.
- Implement configurable close-relative power-hour measurements.
- Preserve developing versus complete measurement truth.

**Gate:** windows match authoritative calendar boundaries, including early closes.

**Implementation status:** implemented for local review. Each analytical profile may declare zero
or more independently named calendar-relative windows with its own purpose, anchor phase/boundary,
offset, duration envelope, dynamic eligibility, historical selector, and bounded observation
envelope. The family policy separately owns price basis, coverage envelope, retention, and output
age. Metric identity includes profile and window IDs, so multiple concurrent opening ranges do not
collide.

The initial runtime configuration deliberately enables two opening ranges and one close-relative
power-hour window only for the CME-equity analytical profile. This is an acceptance scope, not a
hard-coded instrument rule; other profiles remain explicit empty sets until their desired session
semantics are reviewed. Opening-range bounds freeze after completion while distance measurements
continue from the latest accepted close. Power-hour history falls back to the latest started
close-relative window, allowing prior-session evidence before the current window begins. Early
closes are inherited from the authoritative calendar rather than fixed clock times.

Opening-range outputs do not depend on volume or directional efficiency. Power-hour volume and
bar-VWAP remain independently unsupported where the profile lacks volume while its OHLC, return,
range, coverage, and efficiency outputs remain available. All numerical state stays bounded and
transient; PostgreSQL continues to receive only dependency and runtime lifecycle facts.

### Slice 5: Volatility, Efficiency, And Compression Inputs

- Implement approved rolling numerical formulas.
- Validate bounded memory and parameter envelopes.
- Keep semantic classifications out.

**Gate:** outputs match independent fixtures and remain stable under missing/late data.

### Slice 6: Live Acceptance And Stage Closure

- Run offline, PostgreSQL integration, and resource-bound tests.
- Markeitect runs connected IB acceptance.
- Reconcile input, suppression, history, metric, evidence, conflict, and shutdown counters.
- Compare selected instruments against independent chart values.
- Update status and merge through a detailed PR after local review.

**Gate:** the complete baseline session-measurement family is trustworthy enough to shape Stage 9D.

## Test Matrix

Offline tests cover strict schemas, DST/holidays/early closes, futures/equities/indices,
unsupported volume, five-second aggregation, one-minute historical normalization, direct
coarser-resolution dependencies, provider-native versus locally aggregated equivalence fixtures,
every arrival ordering, duplicates/conflicts/late/missing data, opening-range and power-hour
boundaries, zero-range arithmetic, versions/dynamic eligibility, bounded resources,
failures/recovery, actor independence, and clean shutdown.

PostgreSQL integration verifies operational lifecycle only and proves raw/numerical data is absent.

## Live Acceptance Evidence

The connected run must demonstrate:

- one provider stream per unique live requirement despite multiple consumers;
- bounded historical requests inside IB/resource policy;
- correct session and trade-date assignment;
- exact historical/live overlap accounting;
- completed-bar, session, prior-session, opening-range, gap, and power-hour values matching an
  independent operator reference for selected futures, ETF/equity, and index cases;
- honest volume/VWAP unsupported behavior for indices;
- no values published with unavailable prerequisites;
- unrelated runtime components continuing through a degraded measurement case;
- no raw bars or numerical metric churn in PostgreSQL;
- complete operational persistence reconciliation; and
- clean shutdown with zero unexplained pending work.

## Decisions Requested From Markeitect

The recommended first implementation assumes:

1. per-measurement resolution declarations, with a configurable one-minute calculation interval
   only for the initial intraday measurements that require it; existing five-second live bars may
   be aggregated and matching one-minute historical bars may satisfy that exact dependency;
2. `reject_conflict` as the initial historical/live overlap policy;
3. explicit analytical session profiles separate from availability calendars;
4. indicative pre-open gap and immutable opening gap as distinct metrics;
5. bar-derived VWAP/participation fields named as estimates or proxies, never order flow; and
6. all seven measurement families complete through the six delivery slices before Stage 9D entity
   implementation begins.

No runtime code begins until these decisions and the metric scope are reviewed.
