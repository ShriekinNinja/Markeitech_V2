# Markeitect Model Implementation Plan

Status: Proposed for review

Started: 2026-07-21

Owners: Markeitect and Kite

Branch: `codex/markeitect-model`

Motto: No Obstacles, Only Challenges.

## Objective

Build the Markeitect Model from observable market evidence outward. The first
milestone is not a profitable signal claim. It is a durable observation system
that can recognize aggressive participation, calculate delta/CVD, remember
participant prices, and describe whether effort received price follow-through.

Each stage must preserve timestamp correctness, source fidelity, restart
behavior, bounded runtime operation, and human-readable evidence. Existing
market-data, analytics, persistence, event-bus, and Discord infrastructure are
reused where appropriate. Legacy signal definitions remain present but disabled.

## Stage 0: Clean Model Boundary

- [x] Create `codex/markeitect-model` from the accepted infrastructure commit.
- [x] Retain legacy Fabio/DLA implementation and historical records.
- [x] Disable every legacy signal definition in checked-in live, test, and
  example configurations.
- [x] Prevent construction of the legacy signal handoff, aggression evaluator,
  lifecycle runtime, and signal projection writer when no definition is enabled.
- [x] Verify no pending historical Discord notifications can leak into a new run.
- [x] Add configuration regressions proving definitions remain available but
  NQ and ES enablement is empty.
- [x] Run the complete repository suite.
- [x] Receive review approval and commit the clean boundary.

### Acceptance Gate

- [ ] A normal live/test configuration starts analytics and context without
  starting or logging the legacy signal runtime.
- [ ] No new Fabio/DLA lifecycle or signal Discord event can be produced.
- [ ] No legacy code or history has been deleted.

## Stage 1: Order-Flow Cohort

Separate trading focus from order-flow fidelity. NQ and ES must be observable
simultaneously even when only one instrument is the current trading focus.

### Configuration

- [ ] Define one active trading-focus instrument independently of data mode.
- [ ] Add an explicit order-flow cohort containing NQ and ES.
- [ ] Keep ordinary context instruments on reported 1m bars unless promoted.
- [ ] Validate that every order-flow instrument has contract, entitlement,
  warmup, session, tick-size, and threshold configuration.
- [ ] Keep runtime instrument switching available without discarding the cohort.

### Provider And Runtime

- [ ] Confirm IB/Nautilus can maintain simultaneous NQ and ES trade/quote
  subscriptions under current paper-data entitlements and pacing limits.
- [ ] Subscribe to tick-by-tick trades for both cohort instruments.
- [ ] Subscribe to the quote evidence required by the existing classifier for
  both instruments.
- [ ] Keep per-instrument bounded streams and health counters.
- [ ] Expose missing, stale, delayed, conflicted, and degraded cohort evidence.
- [ ] Preserve analytics/context operation when one cohort member degrades.

### Tests And Acceptance

- [ ] Test independent NQ/ES stream identity and no cross-instrument mixing.
- [ ] Test bounded queues, reconnect, duplicate data, and out-of-order events.
- [ ] Test active-focus switching without subscription loss.
- [ ] Run a short paper session and confirm simultaneous classified flow.

### Acceptance Gate

- [ ] NQ and ES both report defensible classified trades and quotes in one run.
- [ ] Coverage and unknown-volume counters are visible per instrument.
- [ ] No model judgment has been added yet.

## Stage 2: Canonical Flow Measurements

Create reusable facts before detecting setups.

### Delta And CVD

- [ ] Define canonical trade-side and signed-volume contracts.
- [ ] Calculate per-trade signed volume.
- [ ] Calculate completed-bar delta for configured windows.
- [ ] Calculate session CVD with explicit product-session reset identity.
- [ ] Calculate rolling delta and CVD change over configurable windows.
- [ ] Retain CVD slope, acceleration, deceleration, reversal, and extremes as
  decomposed measurements.
- [ ] Retain total, classified, unknown, bid, ask, and inferred volume.
- [ ] Never calculate reported CVD from OHLCV bars.

### Price Response

- [ ] Measure price displacement over time, trade count, volume, ticks, and ATR.
- [ ] Measure maximum favorable and adverse excursion from an observation.
- [ ] Measure price/CVD confirmation and divergence without assigning a trade.
- [ ] Preserve event-time windows and reject look-ahead evidence.
- [ ] Define reset and recovery behavior across reconnect and restart.

### Tests And Acceptance

- [ ] Test buy/sell/unknown classification accounting.
- [ ] Test CVD reset at the configured product-session boundary.
- [ ] Test retries, corrections, gaps, and partial coverage.
- [ ] Test price-up/CVD-up, price-down/CVD-down, and divergent paths.
- [ ] Compare selected calculations with OFS screenshots/recordings.

### Acceptance Gate

- [ ] Markeitect can inspect NQ/ES flow output and recognize the same broad CVD
  path shown by the reference tool.
- [ ] Every measurement identifies its source and fidelity.

## Stage 3: Large Trades And Aggressive Bursts

### Detection

- [ ] Add instrument-specific initial thresholds: NQ 40 and ES 120 contracts.
- [ ] Detect individual classified trades meeting the threshold.
- [ ] Detect repeated same-side activity within configurable time and price
  neighborhoods.
- [ ] Keep individual trades and accumulated bursts semantically distinct.
- [ ] Record side, price band, total size, trade count, start/end time, maximum
  print, classification method, and fidelity.
- [ ] Prevent one trade from being counted in overlapping bursts silently.
- [ ] Retain below-threshold distributions for later calibration.

### Research Comparison

- [ ] Record OFS large-trade settings used in reference streams.
- [ ] Compare IB-derived events with selected OFS and Tradovate examples.
- [ ] Document expected provider and aggregation differences.
- [ ] Avoid asserting that one burst equals one whale or institution.

### Tests And Acceptance

- [ ] Test exact threshold boundaries.
- [ ] Test split prints, repeated bursts, opposite-side overlap, and quiet gaps.
- [ ] Test instrument-specific threshold isolation.
- [ ] Test restart and duplicate idempotency.

### Acceptance Gate

- [ ] Live logs identify the major NQ and ES aggressive events Markeitect sees
  without intolerable noise.
- [ ] Misses and false detections can be explained from source evidence.

## Stage 4: Participant Anchors And Outcome Observation

### Anchor Contract

- [ ] Create immutable participant-anchor identity from instrument, side,
  originating event, price band, and event time.
- [ ] Attach nearby auction locations without making them part of Direction.
- [ ] Retain cumulative same-side and opposing activity around the anchor.
- [ ] Preserve anchors across new levels, bars, and retests.
- [ ] Define bounded retention and explicit terminal/archive reasons.

### Outcome States

- [ ] Implement descriptive states: Pending, Following Through, Absorbed,
  Failing, Trapped, and Recovered.
- [ ] Keep state evidence decomposed rather than using one confidence score.
- [ ] Track price progress obtained per unit of aggression.
- [ ] Track CVD confirmation/non-confirmation and subsequent reversal.
- [ ] Track breaks, holds, reclaims, failed reclaims, and retests.
- [ ] Track favorable/adverse excursion and elapsed observations.
- [ ] Permit recovery after apparent failure when price regains the anchor.
- [ ] Do not call a participant trapped solely because a bubble appeared.

### Durability

- [ ] Persist state changes as immutable events.
- [ ] Commit checkpoints atomically with relevant observation identities.
- [ ] Restore open anchors and pending outcome progress after restart.
- [ ] Reject conflicting retries and backward event time.
- [ ] Keep unchanged observations from creating durable noise.

### Tests And Acceptance

- [ ] Successful buyer at a low remains Following Through, not Trapped.
- [ ] Buyer at a high with no progress becomes Absorbed/Failing only when
  subsequent evidence supports it.
- [ ] Buyer lost below its anchor and failed reclaim can become Trapped.
- [ ] Successful sell initiative after buyer failure remains separately visible.
- [ ] Restart preserves pending failure/recovery evidence.

### Acceptance Gate

- [ ] For selected live examples, Markeitect agrees that the machine described
  who acted, where, and whether they won without issuing a trade signal.

## Stage 5: Auction Map Refinement

### Existing Locations

- [ ] Reuse profiles, POC/VAH/VAL, VWAP, support/resistance, FVGs, session
  ranges, and higher-timeframe structure as evidence inputs.
- [ ] Preserve source, timeframe, maturity, freshness, and fidelity.
- [ ] Consolidate nearby locations without erasing contributors.
- [ ] Stop treating a new nearby location as automatic thesis replacement.

### New/Refined Locations

- [ ] Add explicit HVN and LVN/node contracts with prominence and boundaries.
- [ ] Model low-volume paths and their next acceptance areas.
- [ ] Add untouched gap identity and first-touch state, prioritizing ES/SPX.
- [ ] Add opening-range Fibonacci anchors and extensions.
- [ ] Add gap Fibonacci anchors and completion levels.
- [ ] Preserve prior participant anchors as first-class auction locations.

### Destination Map

- [ ] Produce ordered conditional destinations from the current price.
- [ ] Distinguish reached, broken, accepted, rejected, and still-conditional
  destinations.
- [ ] Avoid language promising that a destination must be reached.
- [ ] Preserve alternate upside and downside paths simultaneously.

### Acceptance Gate

- [ ] The ES 7520/7521 POC example identifies 7516 as the first downside
  destination and 7500 only after the first area breaks/accepts.
- [ ] Markeitect can explain why each reported destination exists.

## Stage 6: Cross-Market State

### NQ/ES Relationship

- [ ] Measure relative displacement, delta/CVD direction, aggression balance,
  and timing between NQ and ES.
- [ ] Describe coherent, divergent, leader, laggard, unresolved, and resolving
  states.
- [ ] Detect two-sided aggression with low directional efficiency.
- [ ] Allow leadership to change during a session.
- [ ] Never convert disagreement directly into a trade direction.

### Context Instruments

- [ ] Retain VIX, CL, SOXL, QQQ/SPX/SPY, and the selected market leader as
  timestamped context.
- [ ] Measure movement relative to recent windows, not only daily percentage.
- [ ] Preserve context freshness and missing/degraded state.
- [ ] Represent relationships as conditional observations, not fixed signs.
- [ ] Record which context changed before, during, and after a thesis event.

### Acceptance Gate

- [ ] The POC retest example describes NQ as two-sided/unresolved while ES leads
  the rejection.
- [ ] Later NQ breakdown changes the relationship to coherent downside.
- [ ] VIX/CL evidence is reported without claiming a universal causal rule.

## Stage 7: Persistent Markeitect Thesis

### Scenario Contract

- [ ] Represent one consequential auction story across multiple observations.
- [ ] Retain preferred and alternate branches.
- [ ] Attach participant anchors, auction locations, context, and destinations.
- [ ] Define Armed as a decision state with known branch-resolution evidence.
- [ ] Permit branch-neutral and directionally biased Armed states explicitly.

### Lifecycle

- [ ] Record initial trigger separately from later confirmation.
- [ ] Record reload/retest opportunities inside the same thesis.
- [ ] Record conviction escalation without translating it into account sizing.
- [ ] Record hold, target reached, continuation, warning, invalidation, recovery,
  and alternate-branch activation.
- [ ] Keep late evidence as context even when no entry remains desirable.
- [ ] Prevent a newly detected level from replacing the thesis automatically.

### Initial Scenario Families

- [ ] Failed buyer -> Short.
- [ ] Failed seller -> Long.
- [ ] Successful buy initiative -> Long continuation.
- [ ] Successful sell initiative -> Short continuation.
- [ ] Failed aggression followed by opposing successful initiative.
- [ ] Break, hold, and failed-reclaim reload.
- [ ] POC/auction-location retest and rejection reload.

### Acceptance Gate

- [ ] The full July 21 ES/NQ sequence appears as one thesis with initial puts,
  POC retest, reload, NQ/ES coherence, 7516 reached, and 7500 conditional.
- [ ] Alternate calls branch remains visible until evidence invalidates it.

## Stage 8: Operator And Discord Experience

### Observation Output

- [ ] Show important large-trade/burst events without flooding every print.
- [ ] Show participant side, anchor, size, current result, CVD response, and
  nearby auction location.
- [ ] Show state changes rather than repeated unchanged snapshots.
- [ ] Keep raw facts separate from inferred interpretation.

### Decision Output

- [ ] Market-events channel receives compact flow and auction state.
- [ ] Alert-stream receives consequential developing battles and retests.
- [ ] Signals channel receives Armed, Triggered, Reload, target, hold, recovery,
  and invalidation narratives only after thesis semantics exist.
- [ ] System-health channel remains limited to runtime/data health.
- [ ] Messages explain who acted, where, what happened, and what resolves next.
- [ ] Never emit "entered" without a location, participant story, and reason.

### Acceptance Gate

- [ ] Markeitect can understand the active thesis without searching console logs.
- [ ] Discord remains useful during live trading rather than becoming telemetry.

## Stage 9: Evidence Review And Calibration

### Reference Set

- [ ] Extend human examples with participant anchors, effort/result notes, CVD,
  cross-market state, entry branch, reload, invalidation, and destinations.
- [ ] Include successful aggression, failed aggression, ambiguous battles, false
  positives, and late-but-useful observations.
- [ ] Preserve screenshots/video timestamps and annotation provenance.

### Measurement

- [ ] Audit observation recall before judging signal profitability.
- [ ] Measure state-transition latency and stability.
- [ ] Measure destination reach, MFE, MAE, and reclaim/retest behavior.
- [ ] Compare early trigger, confirmed trigger, and reload populations.
- [ ] Measure incremental value of NQ/ES coherence and each context instrument.
- [ ] Keep QQQ and SPX expressions separate from underlying thesis outcomes.

### ML/Regression

- [ ] Build timestamp-correct feature rows from raw observations.
- [ ] Establish deterministic baselines before complex models.
- [ ] Optimize large-trade/burst thresholds by instrument and regime.
- [ ] Estimate follow-through, trap, destination, and invalidation probabilities.
- [ ] Use walk-forward/session-separated validation.
- [ ] Prevent label leakage and hindsight mutation.
- [ ] Retain explainable component contributions and model version identity.
- [ ] Keep ML advisory; it cannot execute or silently rewrite model truth.

### Acceptance Gate

- [ ] Calibration claims are supported by out-of-sample evidence, not one trade.
- [ ] Markeitect can inspect why a model ranking changed.

## Stage 10: Options Expression, Deferred

- [ ] Ingest QQQ and SPX option-chain data through a provider boundary.
- [ ] Model spread, volume, open interest, implied volatility, Greeks, moneyness,
  time remaining, and contract multiplier.
- [ ] Map underlying destinations and invalidation to candidate contracts.
- [ ] Separate early, confirmed, reload, and continuation expressions.
- [ ] Measure option outcome independently from underlying thesis outcome.
- [ ] Preserve manual execution and sizing authority.
- [ ] Never encode "full port" as a recommendation or automated action.

## Immediate Next Batch

- [x] Review and commit Stage 0 deactivation plus these model documents.
- [ ] Inspect current subscription contracts and provider limits for simultaneous
  NQ/ES tick and quote flow.
- [ ] Propose the smallest Stage 1 configuration/domain change for approval.
- [ ] Implement only after the Stage 1 boundary is reviewed.
