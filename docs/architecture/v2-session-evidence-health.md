# V2 Session And Evidence Health

## Purpose

Stage 9A establishes two facts every later metric, event, option candidate, and agent decision must
be able to prove:

1. which exchange session and trade date were active; and
2. whether the required live evidence was usable at that moment.

This stage does not calculate technical analysis, request historical warmup, discover options, rank
opportunities, or place orders.

## Runtime Ownership

`SessionStateActor` is the sole runtime owner of exchange-session state and the only production
component which constructs `CanonicalCalendar` instances. At startup it receives validated,
immutable definitions for the active calendar IDs and creates exactly one evaluator for each. No
consumer receives an evaluator, imports `pandas-market-calendars` for runtime session meaning, or
authors a local calendar fallback.

The actor publishes immutable, definition-identified `CalendarTransition` custom data for initial
state and meaningful phase, exchange-state, or trade-date changes. It also answers bounded typed
projection requests with immutable `CalendarProjection` values. Projection responses account for
every requested calendar exactly once as projected, unavailable, or failed. Ordinary per-calendar
construction failures are contained and returned as sanitized outcomes without suppressing
successful calendars or redefining native publication failure.

Each projection consumer holds at most one outstanding correlated attempt, validates requester,
request ID, source, source epoch, definition digest, calendar set, and coverage, and uses one
bounded Nautilus alert for response timeout or retry wake. Lost responses, `NOT_READY`, and
retryable failures are bounded by configured timeout, fixed backoff, attempt, and total-elapsed
limits. A new run creates a new source epoch; projections are reconstructed from the validated
startup catalog rather than restored as durable state.

`EvidenceHealthActor` is the sole owner of live quote/bar freshness state. It:

- waits for operational persistence readiness;
- observes acquisition subscription outcomes;
- registers its independent native Nautilus handlers during actor startup, outside nested signal
  dispatch;
- records event and receive timestamps in bounded memory;
- evaluates configurable cold-start and adaptive freshness thresholds;
- learns bounded per-instrument receive-cadence profiles for eligible streams; and
- publishes only health-state transitions.

`HistoricalEvidencePlannerActor` is the sole owner of resolving symbolic historical evidence needs
into exact immutable UTC request plans. `DataAcquisitionActor` and the acquisition coordinator
remain the sole owners of provider-facing admission, deduplication, capacity, pacing, queueing,
retry, cancellation, execution, callback handling, and audited lifecycle. Analytical consumers may
publish typed logical demand, but they do not call Interactive Brokers or interpret provider limits.

Each native observation consumer registers its own Nautilus data handler where required; the
DataEngine owns routing and physical subscription sharing. Handler registration failure is
isolated to that consumer and retried under configured policy without delaying unrelated actors.
Consumer actors do not issue provider teardown during shutdown. Acquisition owns logical demand
release and provider cancellation; Nautilus owns local actor-handler cleanup.

## Session Configuration

System schema 21 loads one dedicated
`config/market-calendars.toml` schema-3/catalog-version-4 startup catalog. Inline definitions,
legacy dated overrides, and older system or catalog schemas are rejected. Each system profile
selects its active `calendar_ids`; definitions which are available but unused are validated without
being instantiated. The runtime watchlist is the sole binding authority between exact admitted
instruments and reusable calendar IDs, so futures rollover does not require editing temporal
definitions.

Every immutable calendar definition identifies:

- the `pandas_market_calendars` engine and pinned package version;
- exact provider-calendar name and implementation identity;
- provider-derived exchange timezone and admitted schedule columns;
- break and interruption interpretation;
- normalized, independently timezoned Markeitech product phases;
- source-identified structural corrections and explicit normalization policy;
- definition version, effective time, source configuration identity, and deterministic digest; and
- the catalog identity and digest which admitted it.

The catalog contains five reusable definitions:

- SPXW Cboe Global, Regular, and Curb phases;
- US equities through the NYSE calendar;
- CME equity-index futures;
- CBOT equity-index futures; and
- product-specific CL energy futures.

SPXW phase windows remain explicit configuration because a cash-session calendar alone does not
describe Global and Curb trading. Pinned mcal already supplies the reviewed 2026 CBOE closures and
early closes, so Markeitech maintains no duplicated annual holiday list. Provider schedules own
valid trade dates, holidays, and early closes. An early provider close clamps RTH and prevents the
runtime from inventing a normal Curb session afterward.

Pinned mcal exposes an obsolete regular 15:15-15:30 America/Chicago pause for CME equity
calendars. One source-identified correction removes only that pause for ES, NQ, and YM from trade
date 2021-06-28. Exact provider matches are `APPLIED`, already-conforming rows are
`BASE_ALREADY_CONFORMS`, and unequal provider changes fail as `CONFLICT`. Several early-close rows
encode `break_start == break_end == market_close`; after the structural correction, the evaluator
normalizes only that exact terminal representation into one positive open segment and records the
original endpoints in an immutable normalization outcome. Other partial, inverted, out-of-bounds,
or zero-length break shapes fail closed.

CME/CBOT definitions expose overlapping `GLOBEX`, `ASIA`, `LONDON`, and `NEW_YORK` product phases.
These are descriptive product phases, not exchange-schedule facts or analytical windows. Every
produced instant remains a UTC nanosecond while the exchange and phase IANA timezones remain
explicit for trade-date, civil-clock, and DST meaning.

Phase names are uppercase configured vocabulary. Downstream contracts do not hard-code today's
phase catalog, so a later approved phase can be added without changing the wire schema.

## Historical Planning Boundary

Calendar-relative historical acquisition follows one directional ownership chain:

1. an analytical capability publishes a symbolic, versioned evidence need;
2. `HistoricalEvidencePlannerActor` obtains a digest- and coverage-valid immutable projection;
3. the planner resolves the need into one exact UTC `HistoricalRequestPlan`; and
4. `DataAcquisitionActor` validates and executes that exact plan under provider limits.

The calendar authority supplies temporal facts, the planner owns analytical window resolution, and
acquisition owns provider execution. Acquisition does not decide what a session or product phase
means. The current accepted connected profile retains one outstanding request, one in-flight
request, and one attempt. Increasing concurrency or retries remains blocked until native callback
attribution can distinguish attempts honestly.

## Evidence Health Semantics

The initial states are:

- `DORMANT`: the relevant exchange session is closed, so fresh observations are not expected;
- `NOT_EVALUATED`: session state is not known yet, so absence cannot honestly be classified;
- `HEALTHY`: the latest observation is inside the fresh window;
- `DEGRADED`: a subscription is active but the first observation is pending, or age has crossed
  the preferred fresh window;
- `STALE`: the observation has crossed the configured stale threshold;
- `UNAVAILABLE`: subscription failed/canceled or observation age crossed the unavailable limit;
  and
- `UNSUPPORTED`: reserved for an explicitly unsupported evidence requirement.

An explicit subscription rejection or failure remains `UNAVAILABLE` even while the session is
closed; `DORMANT` suppresses only expected market silence, never infrastructure failure. Session
and observation events may arrive in either order. A transition in either input immediately
re-evaluates affected evidence.

Freshness and fidelity are independent. A reported quote remains `REPORTED` fidelity after it
becomes stale; its health state and age explain that it must not be used. Fidelity is
`UNAVAILABLE` only before any observation exists for the configured stream.

Every transition carries instrument, calendar, feed kind, selector, subscription state, event and
receive timestamps, evaluated age, session phase/trade date/alignment, policy version, source, and
revision. Quote and bar thresholds are startup-configurable and validated in milliseconds.

Quote silence is not treated as a universal fixed heartbeat. Adaptive profiles are isolated by
instrument, feed, selector, provider, session phase, and policy version. Learning occurs only when
the session and subscription are active and the previous evidence state was healthy or degrading;
stale, unavailable, reconnecting, and closed-session intervals do not train the profile. A
configured minimum sample count protects cold start. Effective thresholds are derived from an
exponentially weighted interval mean and variance, then clamped to configured hard minimums and
maximums. Five-second bars retain cadence-based fixed policy in the current configuration.

SPX and VIX cash indexes currently declare bar-derived last only and use cash-session expectations.
The SPXW option session remains separately configured for future option contracts; an extended
option session does not imply that the cash index publishes the same underlying feed overnight.

## Persistence

Calendar, session, and evidence-health transitions use the existing ordered `operational_events`
PostgreSQL ledger:

- typed `CalendarTransition` becomes `calendar.transition`;
- `markeitech.evidence.health` becomes `evidence.health`.
- `markeitech.evidence.recency_profile` becomes `evidence.recency_profile`.

The latest compact learned profile is also upserted into `evidence_recency_profiles` for restart
bootstrap. Checkpoints occur at configured sample intervals and graceful shutdown, never per tick.
The immutable ledger preserves profile-change lineage while the profile table supplies current
state. Calendar projections, provider schedules, raw quotes, bars, and per-update callbacks remain
transient and are not written to PostgreSQL.

## Acceptance And Current Limits

- The canonical-calendar repair is connected-accepted only for the tracked `cme_equity` V3 ES
  profile, its configured 120-day lookback and 14-day lookahead, one historical request and
  attempt, and the observed 2026-08-31 current session.
- The accepted run does not prove a scheduled phase-boundary transition, multi-calendar live
  behavior, connected projection retry/failure behavior, provider cancellation, concurrent
  historical callbacks, or shutdown with provider work in flight.
- `CalendarTransition` plus bounded projection delivery is not a full late-consumer
  current-state/snapshot/reconcile protocol. That remains V3-02 work.
- Completed-bar and `MetricValue` subject identity does not yet carry complete calendar-definition
  identity for cross-epoch conflict detection. That remains a V3-03 prerequisite; it does not
  create a second calendar authority in the accepted V3-01 runtime.
- Global `SYSTEM_HEALTH READY` retains its narrow control-plane meaning: operational persistence
  and configured instrument-definition availability. Calendar-dependent consumers own their local
  bounded projection readiness; adding a global calendar prerequisite requires a separate
  architecture decision.
- The first health owner covers configured native quotes and external five-second bars only.
- Evidence health remains transition-oriented, not a general queryable read model.
- Adaptive recency state restores across runs; it is health policy, not analytical market state.
- Cancellation must be fenced from dispatching queued provider work before shutdown behavior or
  historical concurrency expands.
