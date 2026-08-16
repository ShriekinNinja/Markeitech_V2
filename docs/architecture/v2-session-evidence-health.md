# V2 Session And Evidence Health

## Purpose

Stage 9A establishes two facts every later metric, event, option candidate, and agent decision must
be able to prove:

1. which exchange session and trade date were active; and
2. whether the required live evidence was usable at that moment.

This stage does not calculate technical analysis, request historical warmup, discover options, rank
opportunities, or place orders.

## Runtime Ownership

`SessionStateActor` is the sole owner of exchange-session state. It evaluates configured calendar
definitions using `pandas-market-calendars`, publishes an initial state after operational
persistence is ready, and then publishes only phase or trade-date transitions.

`EvidenceHealthActor` is the sole owner of live quote/bar freshness state. It:

- waits for operational persistence readiness;
- observes acquisition subscription outcomes;
- registers its independent native Nautilus handlers during actor startup, outside nested signal
  dispatch;
- records event and receive timestamps in bounded memory;
- evaluates configurable freshness thresholds; and
- publishes only health-state transitions.

`DataAcquisitionActor` and the acquisition coordinator remain the owners of Markeitech logical
demand and its audited provider state. Each consuming actor registers its own native Nautilus data
handler as Nautilus requires; the DataEngine owns routing and physical subscription sharing.
Consumers do not publish additional Markeitech demand. Handler registration failure is isolated to
that consumer and retried under configurable policy without delaying unrelated actors.

## Session Configuration

Each watchlist instrument names a `calendar_id`. Calendar definitions contain:

- provider calendar name;
- exchange timezone;
- explicit schedule version;
- optional named phases; and
- explicit dated overrides for exceptional sessions.

The initial definitions cover:

- SPXW Cboe Global, Regular, and Curb phases;
- US equities through the NYSE calendar;
- CME equity-index futures; and
- CME energy futures.

SPXW phase windows remain explicit configuration because a cash-session calendar alone does not
describe Global and Curb trading. The configured 2026 holiday overrides are versioned startup
policy, not hidden code constants. Provider schedules own valid trade dates, holidays, and early
closes. An early provider close clamps RTH and prevents the runtime from inventing a normal Curb
session afterward.

Phase names are uppercase configured vocabulary. Downstream contracts do not hard-code today's
phase catalog, so a later approved phase can be added without changing the wire schema.

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

## Persistence

Session and evidence-health transitions use the existing ordered `operational_events` PostgreSQL
ledger:

- `markeitech.session.state` becomes `session.state`;
- `markeitech.evidence.health` becomes `evidence.health`.

No new table is required because these are immutable operational facts with versioned payloads.
Raw quotes, bars, and per-update callbacks remain transient and are not written to PostgreSQL.

## Current Limits

- Evaluation uses a configurable periodic cadence; exact transition scheduling can replace it if
  measured timing requirements justify the added mechanism.
- The first health owner covers configured native quotes and external five-second bars only.
- Health state is transition-oriented, not yet a queryable read model.
- Session and health events are durable within a run; durable analytical state and restart
  restoration belong to later stages.
- Real IB acceptance is run by Markeitect. Offline coverage proves DST, holidays, early closes,
  freshness thresholds, wire contracts, composition, and persistence mapping.
