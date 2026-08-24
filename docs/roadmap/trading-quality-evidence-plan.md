# Trading Quality Evidence Plan

> **Legacy V1 plan:** Preserved as trading-research and calibration history. It does not activate
> V1 signals or define V2 evidence, analytics, events, models, or acceptance. Use the V2 charter,
> current status, specialist traceability, and Stage 9A-9K blueprint for current authority.

Started: 2026-07-18

Owners: Markeitect and Kite

Motto: No Obstacles, Only Challenges.

This plan moves Markeitech from mechanically correct signal lifecycles toward
measurable trading usefulness. The live architecture is sufficiently stable for
trading-quality work, but no profitable observation, visually convincing alert,
or isolated Trigger is statistical validation.

Markeitect owns setup truth, discretionary acceptance, and the final call. Kite
owns deterministic measurement, analytical contracts, implementation, and
engineering recommendations. ML may rank evidence later; it does not define
truth, alter historical labels, or receive execution authority.

## Current Evidence

The 2026-07-17 live run lasted about four hours and fifty minutes and completed
286 context cycles across ten instruments. Its final signal heartbeat reported
3,796 revisions, 582 evaluations, 247 confirmation evaluations, no stale
revisions, no queue rejection, no projection error, and no open signals.

The signal funnel produced:

- 34 Armed transitions: 17 active NQ and 17 background ES
- 2 Triggered transitions: one NQ tick-aggression confirmation and one ES
  reported-bar proxy confirmation
- 23 Invalidated transitions and 11 Expired transitions
- 18 terminal transitions caused by `location_episode_replaced`

Discord delivered 4,838 durable notifications with no pending or failed record,
but the operator stream was not usable at that volume: 2,860 market briefs and
1,740 approaching-location alerts dominated the output.

These facts separate the present problems:

1. Markeitech may miss valid rejection opportunities before they become
   candidates or Armed signals.
2. Too few Armed signals confirm, but loosening confirmation without measuring
   the funnel may only increase noise.
3. Technical features are deterministic proof-of-concept analytics, not yet
   calibrated trading structure.
4. Rapid replacement of nearby or changing locations may create lifecycle
   churn.
5. Setup direction must remain semantically explicit; rejection and
   break/retest behavior cannot share an ambiguous interpretation.
6. Discord delivery is reliable, while relevance policy remains weak.

## Today's Objective

Build a read-only, deterministic **Signal Outcome Audit** and a versioned
**Markeitect Reference Set** contract. Run both against the 2026-07-17 session
before changing signal thresholds, technical calculations, or notification
policy.

This is one coherent task: establish the evidence needed to determine whether a
setup was missed, rejected by a specific gate, Armed but unconfirmed, Triggered,
or later invalidated, and what price did after each observable decision point.

## Slice 1: Outcome Audit

Create an offline auditor that reads existing persisted signal transitions,
feature snapshots, and canonical one-minute bars without mutating live state or
reimplementing signal logic.

For every Armed and Triggered transition, retain:

- session, instrument, active/background role, setup definition, and algorithm
  version
- event timestamp, direction, observed price, semantic location identity,
  timeframe, bounds, and source family
- Direction, Location, Aggression, and follow-through evidence with fidelity
- confirmation method and the exact reason codes for every later transition
- lifecycle durations from Candidate to Armed, confirmation, and terminal state
- whether a location was replaced, breached, exited, or merely timed out

Measure forward price response independently from lifecycle state at 1, 3, 5,
15, and 30 completed-minute horizons:

- directional return in points, basis points, and ATR units
- maximum favorable excursion and maximum adverse excursion
- time to maximum favorable and adverse excursion
- close-to-close follow-through and excursion path
- whether price remained near, rejected, accepted through, or reclaimed the
  original location when that classification is supported by existing evidence

Armed and Triggered events remain separate populations. An Armed alert that
later anticipated a move is not relabeled as a Trigger. A Triggered signal that
later loses its location is not silently called a successful exit. The report
must preserve what Markeitech knew at each timestamp.

### Outputs

- a versioned machine-readable outcome dataset suitable for later statistical
  analysis and ML
- a concise Markdown session report with funnel counts, outcome distributions,
  confirmation latency, replacement churn, and active/background comparison
- deterministic tests for timestamp boundaries, direction-adjusted excursion,
  missing horizons, session endings, duplicate transitions, and unavailable ATR
- an initial report for the 2026-07-17 live run

## Slice 2: Markeitect Reference Set

Add a versioned human annotation contract stored outside canonical market data.
The first target is at least 30 representative examples, including valid setups
Markeitech missed and convincing-looking setups that should have been rejected.

Each annotation should capture:

- instrument and exact timestamp with timezone
- intended direction and setup family
- decision zone, semantic level type, and relevant timeframe
- why the setup qualified to Markeitect
- confirmation observed from price, volume, profile, or order flow
- invalidation condition and one or more conditional targets
- screenshot or chart reference plus concise notes
- expected lifecycle outcome: ignore, warn, enter location, arm, or trigger

The audit joins annotations to system evidence by instrument and bounded time,
but never overwrites either source. Ambiguous matches remain explicit. Human
labels require provenance and may be revised through a new annotation version,
not destructive editing of research history.

### Funnel Comparison

For each annotated opportunity, classify the first divergence:

```text
Not observed
  -> Direction rejected
  -> Location unavailable or rejected
  -> Candidate suppressed
  -> Armed but confirmation failed
  -> Triggered
  -> Outcome observed
```

This distinguishes low setup recall from strict confirmation. It prevents a
single aggregate Trigger count from hiding whether the failure occurred in
technical feature generation, semantic qualification, lifecycle policy, or
Aggression confirmation.

## Technical Analysis Calibration Track

Do not begin by creating one opaque confidence number. Preserve explainable
component scores and raw inputs so each analytical family can be calibrated,
removed, or replaced independently.

### Structural Levels

- consolidate nearby levels into tick- and ATR-normalized zones
- retain every contributing source and timeframe
- score touches, recency, rejection magnitude, acceptance, persistence, and
  multi-timeframe confluence
- enforce minimum useful width and separation
- suppress stale, weak, nested, and redundant levels without deleting their
  historical evidence

### Fair Value Gaps

- retain displacement, width in ticks and ATR, age, and source timeframe
- model fresh, partially filled, mitigated, inverted, and expired states
- distinguish overlapping gaps and consolidate only through explicit rules
- test whether gap state and quality improve outcomes beyond nearby generic
  support/resistance

### Trend And Regime

- preserve structure, slope, EMA alignment, distance, persistence, and
  volatility regime as separate inputs
- attach strength and confidence to Bullish, Bearish, and Range classifications
- distinguish trend continuation, balance rotation, transition, and failed
  breakout conditions

### Candle-Derived Auction Structure

Reported candles are a primary analytical input, not second-class evidence.
Build profiles from the smallest appropriate available bars and aggregate them
upward while retaining method and fidelity.

- improve within-bar volume allocation beyond a silent uniform-range assumption
- normalize histogram bins by instrument tick size and volatility
- detect HVNs and LVNs through documented smoothing, prominence, separation,
  and adjacent-bin clustering
- retain POC and node migration, persistence, revisits, acceptance, rejection,
  and session/composite anchors
- merge nearby POCs and HVNs into auction zones only through explicit,
  reproducible rules
- distinguish developing, mature, tested, and invalidated nodes
- compare canonical profiles with selected external charts and, if justified,
  supplemental provider histograms without replacing Markeitech methodology

OHLCV can expose anomalous volume bars, participation bursts, and relative
volume. It cannot prove individual large trades, bid/ask delta, CVD, or trapped
participants. Those names remain reserved for trade-level evidence.

### Order Flow

- retain classified coverage, unknown volume, sequence gaps, and reset policy
- evaluate delta versus price response, CVD, acceleration, absorption candidates,
  divergence, large prints, and trapped-participant behavior only where source
  evidence supports those claims
- measure the incremental value of tick evidence over a candle-only baseline
  rather than requiring tick evidence for every useful setup

## Directional Setup Semantics

Rejection and break/retest behavior become separate named setup families:

- support rejection: long candidate only
- resistance rejection: short candidate only
- support break and retest: short candidate only after confirmed acceptance
  below and a failed reclaim
- resistance break and retest: long candidate only after confirmed acceptance
  above and a failed return

A generic Direction change cannot silently reinterpret an existing location.
Target completion cannot reverse a signal automatically. Any future failed-break
or reclaim model requires its own observable state progression and reason codes.

The outcome audit must first verify whether the current implementation actually
produced opposing interpretations for the same semantic location. Perception is
not declared a defect without evidence, but the semantic boundary applies even
if current behavior proves correct.

## ML Research Track

ML work may start once the outcome and annotation datasets are reproducible.
Candle-derived features form the broad historical foundation; tick and order-flow
features are optional enrichment where available.

Initial model families should compare:

1. candle price, volatility, and session context only
2. candle context plus structural levels, FVGs, and auction-profile features
3. candle context plus inferred active-instrument tick/order-flow features
4. the incremental contribution and failure modes of each feature family

Research rules:

- train only from versioned features and labels available at decision time
- use session-aware walk-forward splits; never randomly leak neighboring bars
  or future-derived profile state across train and validation
- begin with transparent statistical and tree-based ranking baselines before
  agents or complex models
- rank candidate quality and estimate calibrated outcome probabilities; do not
  grant lifecycle or execution authority
- report precision, recall, calibration, MFE, MAE, horizon outcomes, regime
  performance, and feature stability
- preserve separate availability and fidelity indicators; absence of tick data
  is a known modality, not fabricated zero order flow

## Discord Relevance Track

Discord noise is acknowledged but does not block today's evidence work. After
the audit identifies useful events, apply a transport-neutral relevance policy:

- active/background cadence separation and watchlist batching
- meaningful-change thresholds for market briefs
- stable semantic-location identity, hysteresis, and cooldown for Approaching
- severity, persistence, and quality gates
- summaries for repeated low-priority events
- no deletion or alteration of underlying durable market and signal truth

The target is not merely fewer messages. It is a concise stream whose omissions
are explainable and recoverable from canonical evidence.

## Today's Acceptance Boundary

Today is complete when:

1. the outcome and annotation contracts are reviewed and versioned
2. the read-only auditor deterministically produces its dataset and report
3. the 2026-07-17 session report explains all 34 Arms, both Triggers, terminal
   outcomes, and replacement churn without hindsight relabeling
4. a sample reference annotation proves the join and first-divergence model
5. focused tests and the full repository suite pass
6. no live runtime, signal threshold, technical calculation, or Discord policy
   changes are bundled into the evidence slice

Markeitect approved one explicit exception before review: split advisory
proximity and Location narrative messages into a dedicated Discord Alert Stream,
while reserving the Signals channel for persisted lifecycle transitions. This
is a destination-routing correction only; it does not change event generation,
signal qualification, lifecycle state, or delivery guarantees.

After review, the audit findings determine the first calibration target. The
likely candidates are location consolidation, directional setup semantics, and
confirmation selectivity, but evidence chooses the order.

## Deliberately Outside Today's Slice

- changing signal thresholds or making Fabio trusted
- implementing all technical-analysis refinements in one batch
- training or deploying a live ML model
- automated execution or options-chain work
- notification throttling before useful-event criteria are measured
- rebuilding live replay infrastructure; the auditor is an offline evidence
  consumer, not a second signal runtime
