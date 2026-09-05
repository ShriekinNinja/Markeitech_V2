# Deterministic Evidence Contracts

**Status:** Consolidated accepted contracts; active composition and acceptance remain bounded by
[`current-status.md`](../current-status.md)

This document consolidates the stable measurement, completed-bar, entity, state, history, and
evidence-fidelity rules formerly spread across completed Stage 9 plans and architecture notes. It
does not declare every implemented class active. In particular, the active V3 profile keeps the
legacy combined session-measurement and dependent entity surfaces disabled while the replacement
described in [`session-metrics-replacement-plan.md`](../reference/session-metrics-replacement-plan.md)
remains incomplete.

## Evidence Chain

```text
native provider observation
    -> admitted completed-bar or direct deterministic input
    -> versioned measurement
    -> versioned analytical entity and bounded current state
    -> meaningful semantic transition (future minimum Sir Loke corridor)
    -> evidence-cited interpretation or recommendation
```

The layers never collapse:

- an observation is a provider/Nautilus fact with source and timestamp semantics;
- a measurement is a deterministic numerical or typed transformation;
- an entity is a stable analytical subject with identity and lifecycle;
- rolling state is the bounded latest truth about entities;
- an event is an immutable meaningful transition, not every revision;
- an opportunity is an advisory thesis/expression lifecycle; and
- a recommendation remains advisory and cannot become an order instruction.

## Universal Contract Rules

Every cross-component or durable evidence contract defines:

- stable contract name and schema version;
- source, producer, run epoch, subject, instrument, venue, and exact contract identity;
- calendar definition, analytical profile, trade date, session/window, horizon, and resolution
  where they affect meaning;
- event/effective, observed, received, calculated, and published UTC timestamps where applicable;
- sequence and revision scope;
- configuration, definition, formula, parameter, and policy versions with effective time;
- evidence references, source lineage, health, fidelity, coverage, and explicit reason codes;
- duplicate, conflict, late, correction, expiry, and invalidation behavior; and
- bounded typed payload and resource limits.

No identifier is inferred from a display label. Runtime UUIDs and arrival order do not become
analytical identity. A changed formula or payload meaning requires a new version. A later revision
never pretends its evidence existed earlier.

## Historical Evidence

Capabilities declare symbolic, purpose-specific history. `HistoricalEvidencePlannerActor` obtains
canonical calendar state and resolves the declaration into exact UTC bounds.
`DataAcquisitionActor` remains the provider-facing owner for admission, deduplication, pacing,
queueing, retry, cancellation, execution, and callback handling.

History rules are:

- every request has an exact selector, source, bounds, maximum observations, consumer lineage,
  purpose, priority, and immutable parameters;
- identical provider requests are shared while each consumer receives its own readiness result;
- provider response completion is separate from consumer readiness;
- exact duplicates are idempotent; unequal same-identity observations are explicit conflicts;
- one failed, empty, partial, timed-out, canceled, or expired dependency does not block unrelated
  work; and
- raw historical observations are transient and are not persisted merely for replay or future
  convenience.

The current native bar callback does not provide enough identity to correlate concurrent requests
honestly, so the accepted path uses one active provider request lane. Higher concurrency requires
a new attribution proof.

## Completed-Bar Authority

A normalized completed bar carries exact series and observation identity:

- instrument/venue and canonical bar specification;
- interval start/end and timestamp/completion/aggregation/revision policy;
- calendar/profile/configuration identity;
- canonical producer/schema and runtime epoch;
- OHLC values and explicit volume state;
- historical/live input lineage with source stream, selector, provider, correction, and timestamps;
- completion, health, fidelity, missing subintervals, reasons, and evidence references; and
- publication sequence scoped to one series and runtime epoch.

Validation requires positive finite prices, `low <= open/close <= high`, non-negative supported
volume, aligned interval boundaries, and declared completion. Unsupported volume is not zero.

Historical and live inputs converge on semantic interval identity, not arrival order. Equal copies
merge lineage or are counted as duplicates. Unequal same-identity bars never silently overwrite
accepted truth. Under the current `revision_policy = "reject"`, canonical completed bars are final;
accepting revisions requires a separately versioned wire contract and correction design.

Only one foundation owner may admit, aggregate, revise, and publish each canonical completed-bar
series. Numerical owners consume canonical series; they do not republish bars. A composition-time
producer manifest must fail closed on duplicate series or metric-subject claims before provider
demand begins.

## Measurement Definitions And Values

A `MetricDefinition` gives one decision question a stable `(metric_id, version)` and declares:

- implementation/formula and normalization;
- applicability, value kind, canonical unit, cadence, and horizon;
- nullable and failure behavior;
- permitted health/fidelity and known failure modes;
- live, historical, and metric dependencies;
- warmup and bounded retained state/resources;
- parameter definitions; and
- approved future event uses.

Each parameter declares identity, meaning, type, unit, default, scope, source, validation envelope,
step/allowed values, version, effective UTC time, dynamic eligibility, mutability class, rollback,
and audit behavior. `dynamic=true` means only that a future deterministic policy may admit an
in-bounds revision; it grants no present model or actor mutation authority.

A metric value carries exact subject identity, parameter/configuration/producer identity, typed
value and unit, five distinct timestamps, health, fidelity, reasons, evidence references, and a
contiguous per-subject revision chain. Canonical values do not use floating-point wire values.

Health/value invariants include:

- `READY` requires a current non-null value and no reason;
- `DEGRADED` requires a defensible current non-null value plus typed limitation reasons;
- `STALE` carries the last defensible value plus a staleness reason;
- `WARMING`, `UNAVAILABLE`, `UNSUPPORTED`, and `FAILED` carry no value and one or more reasons;
- zero is never substituted for unavailable evidence; and
- a partial input degrades dependents until its mathematical influence leaves their state or a
  reviewed clean reconstruction/reset occurs.

Metric revisions are not completed-bar corrections. An identical repeated revision is a
duplicate; unequal content for the same subject/epoch/revision is rejected while the last accepted
value remains current.

## Resolution And Window Policy

There is no universal base timeframe, mandatory resolution pyramid, or single historical
substrate. Every measurement declares the smallest and cheapest input which preserves its meaning:
provider/source, resolution, price basis, exact lookback/bounds, session scope, volume needs,
fidelity, and allowed direct/aggregation path.

Provider-native and locally aggregated representations may substitute only after equivalence
validation covering interval identity, calendar/session assignment, OHLCV, downstream outputs,
and configured tolerances. Sharing an input is an execution optimization, not an analytical rule.

Analytical sessions and windows are typed/versioned configuration separate from exchange
availability calendars. No code assumes fixed `09:30`, `16:00`, OR5, OR15, or power-hour values.
Opening ranges, prior sessions, overnight/premarket windows, and close-relative windows inherit
authoritative calendar bounds and early closes.

## Accepted Measurement Families

The accepted deterministic catalog includes:

- quote midpoint, absolute spread, and relative spread;
- completed OHLCV, simple return, and true range;
- active-session OHLC, range, location, supported volume, and explicitly bar-derived VWAP estimate;
- immutable previous-session references;
- evolving indicative gap and immutable opening gap as separate meanings;
- configurable opening-range and power-hour numerical families;
- rolling price range, realized log-return magnitude, ATR, directional efficiency, and coverage;
- independent recent and phase-matched equal-duration expansion ratios and empirical midrank
  percentiles; and
- deterministic entity prerequisites for signed direction, EMA/reference geometry, confirmed
  swings, FVG geometry, and explicitly inferred bar-volume allocation.

ATR over `N` measured bars requires the compatible predecessor close as evidence. If it is absent,
the value is unavailable; the first measured bar's high-low cannot replace it. A zero baseline
median makes the expansion ratio unavailable, while an independently valid percentile remains
calculable.

These outputs do not by themselves classify trade direction, acceptance/rejection, order flow,
opportunity, or action. Bar-derived volume allocation remains `INFERRED_FROM_BARS`; OHLCV cannot
be renamed as observed delta, CVD, absorption, or trade-at-price truth.

## Entity Identity And Lifecycle

An `EntityDefinition` owns type/version, decision question, typed payload, identity dimensions,
metric/entity dependencies, permitted health/fidelity, lifecycle, completion, expiry,
invalidation, roll, retention/durability, parameters, and later event uses.

Deterministic entity identity contains only subject-defining dimensions such as type/version,
instrument contract, analytical profile/version, trade date, named session/window/horizon, and an
entity-specific discriminator. It is stable across runs. Runtime IDs, current values, revisions,
and arrival timestamps are not identity.

Each immutable revision carries the stable entity ID, monotonic revision, exact temporal and
profile identity, typed payload, lifecycle, timestamps, dependency versions, evidence references,
health/fidelity/reasons, source, and previous revision. Meaningfully identical projections are
suppressed.

Initial lifecycle vocabulary is:

- `WARMING`: identity exists but required input is insufficient;
- `ACTIVE`: developing with usable evidence;
- `COMPLETE`: the configured subject is complete, not necessarily bullish, accepted, or tradeable;
- `DEGRADED`: usable but incomplete or below the configured evidence contract;
- `STALE`: evidence exceeded its permitted age;
- `INVALIDATED`: identity or required evidence became inconsistent; and
- `EXPIRED`: the retention/relevance boundary passed.

## Accepted Entity Families

Accepted typed families include:

- analytical session, previous-session reference set, opening range, gap, and objective level;
- volatility and compression/expansion state;
- directional, trend/rotation, and moving/anchored reference state;
- confirmed swing, alternating swing leg, bounded per-horizon pivot structure, FVG, and
  constituent-preserving derived zone; and
- explicitly inferred bar-volume distribution with POC/value-area/HVN/LVN candidates where
  supported volume exists.

Support, resistance, target, acceptance, rejection, hold, failure, and trapped-participant meaning
are not permanent properties of objective geometry. They require separately approved interaction
evidence and semantic transitions. Conflicting horizons remain independently visible; no universal
bullish/bearish score erases them.

An `EntityStateBook` keeps the latest revision and bounded indexes by exact identity. Admission,
duplicate suppression, monotonic revision/timestamp checks, roll, invalidation, expiry, snapshots,
and eviction are deterministic. Resource overflow degrades the affected capability; it cannot
silently evict active truth to admit lower-priority history.

## Health, Fidelity, And Missingness

Every output preserves source/feed, exact subject, event/receive/calculation time, age/freshness,
entitlement/subscription state, completeness/coverage, session alignment, warmup, correction or
conflict state, and lineage.

Freshness and fidelity are independent. A stale reported quote remains `REPORTED` but unusable for
fresh decisions. Provider bars are reported aggregates; locally aggregated bars are derived;
incomplete paths may be partial; unsupported or absent values remain unavailable. One unsupported
volume field cannot disable independent price geometry.

The session/evidence vocabulary and current-state reconciliation are maintained in
[`session-evidence-health.md`](session-evidence-health.md).

## Publication, Persistence, And Recovery

Numerical updates and entity revisions use typed Nautilus data paths. They are not automatically
semantic events, Discord messages, or PostgreSQL rows. PostgreSQL records approved demand,
readiness, conflict, resource, lifecycle, and configuration/algorithm identity.

Raw quotes, trades, bars, historical batches, every numerical value, rolling intraday state,
developing candidates, and bar-volume bins remain transient by default. A compact finalized
session summary or selected cross-session entity may be durable only through an approved typed
schema with exact versions, health/fidelity, idempotency, retention, and restart need.

Restored state retains its original effective/finalization/source identity and remains
stale/degraded until catch-up covers the offline interval. Incompatible schema, definition,
formula, or parameter versions are audited and ignored; they are never coerced into current truth.

## Current Replacement Boundary

Earlier Stage 9C/9D profiles supplied bounded connected evidence for these families, but the active
V3 profiles deliberately disabled the combined measurement owner, dependent Entity Analysis, and
Visual Debug during an ownership cutover. V3-03 Slices 1 and 2 provide inactive v2 identities,
validation, producer-manifest foundations, and a disabled completed-bar owner. Slices 3–9 remain
unimplemented.

Therefore:

- accepted formulas and contracts are reusable evidence, not active output claims;
- dormant legacy source is migration evidence, not canonical runtime authority;
- a test-passing inactive owner is not connected or product-ready;
- only one cold-cutover composition may publish each canonical series/metric subject; and
- resuming V3-03 requires a fresh authorized slice tied to a named Sir Loke evidence need.

The full resume instructions and unresolved cutover mechanics remain in the
[`session-metrics replacement plan`](../reference/session-metrics-replacement-plan.md).
