# V3 SessionStateActor Role Review

**Status:** Calendar-owner, typed-transition, bounded-projection, and boundary-timer subset approved,
committed, and connected-accepted with V3-01; full late-consumer snapshot protocol remains proposed

**Review order:** 2 of 4

**Dependency:** The canonical calendar authority in
[`v3-01-canonical-calendar-authority-review.md`](v3-01-canonical-calendar-authority-review.md) is
implemented, committed, and connected-accepted.

## Purpose

Define a narrow, durable responsibility for `SessionStateActor` after one canonical mcal-backed
calendar definition exists.

The actor should answer one current-state question:

> For each configured canonical calendar, what exchange session, product phase, trade date, and
> phase bounds are in effect now under the active calendar-definition epoch?

It should publish current truth and meaningful transitions. It should not become the universal
owner of every period an analytical capability may use.

## Implemented Subset

`SessionStateActor` now solely owns one `CanonicalCalendar` per active definition. It publishes
typed, source-epoch-scoped `CalendarTransition` custom data whenever a consumed current-state field
changes and answers bounded typed projection requests with immutable, definition-identified
schedule coverage. It uses both a configurable periodic reconciliation timer and the next known
boundary alert. Other actors no longer instantiate mcal or a copied evaluator.

The transition contract includes current and previous trade date, phase memberships and exchange
state, segment bounds, next transition, definition/effective identity, source epoch, revision, and
effective/evaluated/published timestamps. The existing operational ledger stores those transitions.

The full late-consumer current-state snapshot request/response and subscribe-buffer-reconcile
protocol described below is not implemented and must not be inferred from projection support.

## Pre-Cutover Verified State (Historical)

`SessionStateActor` currently:

- constructs its own `SessionCalendar` objects from copied startup configuration;
- waits for operational-persistence readiness;
- periodically evaluates the current clock time;
- publishes an initial state and later changes to `(trade_date, phase)`;
- carries phase open/close and next-transition timestamps in the event;
- uses one in-memory revision counter per calendar; and
- publishes operational transition facts through the existing persistence boundary.

The actor currently does not:

- publish an immutable current-state snapshot in response to a late consumer;
- provide a bounded point-in-time schedule projection for historical timestamps;
- carry a deterministic calendar-definition digest or effective epoch;
- identify a producer/run epoch for its revision sequence;
- publish a change when phase boundaries change but `(trade_date, phase)` stays equal;
- expose explicit unavailable or conflicting calendar state; or
- prevent acquisition and analytical actors from independently evaluating copied calendars.

The current transition event is useful but insufficient as the sole session-state interface. A
consumer which starts after the initial event may wait indefinitely for the next transition, and a
current transition cannot classify historical bars.

## Proposed Responsibility

`SessionStateActor` should be the sole runtime publisher of current exchange-session and product-
phase state under one active canonical calendar-definition epoch.

### It owns

- activating the approved immutable startup calendar-definition set;
- current trade-date assignment per calendar;
- current exchange-session state;
- current product-phase state;
- open, close, break/interruption, and next-transition boundaries relevant to current state;
- current-state revision per calendar within one producer/run epoch;
- initial state publication;
- meaningful transition publication;
- immutable current-state snapshots for late or restarting consumers;
- typed unavailable/conflict outcomes when current state cannot be established; and
- bounded, observable timer lifecycle for current-state reevaluation.

### It may project, but does not author

- the immutable canonical calendar definition;
- bounded schedule coverage generated from that definition; and
- product-phase definitions supplied by approved versioned configuration.

The actor is the runtime state owner, not the source of arbitrary phase names or exchange-calendar
rules.

### It must not own

- analytical-window definitions;
- opening-range, power-hour, London, New York, or other analytical calculations;
- rolling contexts;
- bar normalization or aggregation;
- historical request execution, budgets, queueing, or provider pacing;
- analytical capability activation;
- Watchlist membership;
- evidence freshness;
- metric or entity calculation;
- raw market-data persistence;
- semantic market events; or
- agent interpretation or trading behavior.

## Proposed Contracts

The actor needs distinct transition and snapshot contracts. Historical point-in-time schedule
coverage remains a canonical-calendar contract rather than a current-state event.

### Session state transition

A transition should identify at least:

- immutable event ID;
- source actor identity;
- source/run epoch;
- calendar ID;
- canonical calendar-definition version and digest;
- calendar effective epoch;
- exchange-session/trade-date identity;
- previous and current product phase;
- open/closed/break state;
- effective transition timestamp;
- phase open and close UTC nanoseconds;
- next transition UTC nanoseconds;
- evaluated-as-of and published timestamps;
- per-calendar revision and previous revision;
- reason; and
- schema version.

The ordering boundary is per source/run epoch and calendar revision. Consumers must not infer a
global order relative to bars, historical batches, metric publications, or other actors from
arrival time.

An identical event ID or identical `(source epoch, calendar, revision)` with equal content is an
idempotent duplicate. Equal identity with unequal content is a hard conflict.

### Session state snapshot request

A request should include:

- stable request and requester identity;
- requested calendar IDs;
- requested as-of time;
- optional minimum definition epoch; and
- bounded response/deadline policy.

### Session state snapshot response

A response should include:

- request identity;
- source actor and source/run epoch;
- generated-at and as-of timestamps;
- complete requested-calendar accounting;
- active calendar-definition identities;
- current state and revision for every requested calendar;
- explicit unavailable/conflict outcome per missing calendar;
- response completeness; and
- schema version.

Snapshot rate limits or suppression must return a typed rejection or retry time. Silence cannot be
treated as an empty or healthy response.

### Calendar schedule coverage

Historical bar classification and historical request planning need point-in-time schedule facts,
not only the actor's current state. The approved calendar boundary should provide a bounded
immutable projection covering requested timestamps or trade dates.

Consumers should hold that immutable projection locally. A synchronous request for every incoming
bar is rejected as a hot-path design.

## Late-Consumer Startup Protocol

The minimum safe protocol is:

1. subscribe to session-state transition events;
2. request a source-scoped current-state snapshot;
3. buffer transitions until the snapshot response arrives;
4. reconcile snapshot and buffered transitions by source epoch, calendar ID, and revision;
5. enter live consumption only after the requested calendar set is completely accounted for; and
6. expose a typed degraded/unavailable outcome on timeout, incomplete response, conflict, or epoch
   change.

This removes actor-registration-order assumptions without inventing durable replay.

## Evaluation And Transition Policy

The initial implementation may retain a bounded periodic evaluation cadence. The cadence remains
typed, versioned startup configuration.

The actor should also use known next-transition boundaries where the native clock safely supports
them, but exact scheduling should not introduce hidden unbounded timers or make current state
dependent on one timer surviving a restart.

A transition should be published when any meaningfully consumed current-state field changes,
including:

- definition epoch;
- trade date;
- phase;
- open/closed/break state;
- authoritative current-phase bounds; or
- an unavailable/conflict condition.

Merely refreshing the same immutable current state should not create event noise.

## Persistence Boundary

Current session transitions are already approved operational audit facts. Strengthening their
identity can reuse that boundary.

This review does not approve:

- a new PostgreSQL table;
- durable schedule projections;
- raw calendar query logging;
- durable per-timer state; or
- durable analytical-window state.

If restart requirements later demand persistence of definition activation, snapshot watermarks, or
calendar corrections beyond the existing operational event, that placement requires separate
persistence review.

## Superseded Staged Migration Direction (Historical)

The approved implementation used one atomic cutover instead of the following shadow stages. The
stages remain useful as a record of the safety concerns which informed the final batch.

### Stage A: consume the accepted canonical definition in shadow

- retain current canonical session-state events;
- construct the new definition identity and schedule projection without changing consumers;
- compare current and proposed session results over deterministic fixtures;
- report the known CME-break divergence explicitly; and
- fail closed on equal definition version with unequal digest.

### Stage B: strengthen event identity and add snapshots

- add source/run epoch and calendar-definition identity;
- introduce current-state snapshot request/response;
- preserve current event fields needed by accepted consumers during migration;
- prove subscribe/snapshot/buffer/reconcile startup behavior; and
- keep all consumers on the current canonical event until compatibility passes.

### Stage C: cut over calendar consumers

- make `SessionStateActor` the sole current-state publisher under the accepted definition;
- remove local current-session fallbacks from analytical consumers;
- supply bounded canonical schedule coverage for historical classification;
- move semantic historical-window planning outside acquisition in a separately reviewed batch;
- remove copied calendar evaluation only after parity and complete consumer migration; and
- fence old and new publishers so they are never both canonical for the same definition epoch.

Runtime calendar mutation remains out of scope through all three stages.

## Acceptance Evidence

### Offline contract and actor evidence

- initial state for every configured calendar;
- transition-only publication under unchanged state;
- publication when bounds or definition epoch change without a phase-name change;
- current open, closed, and maintenance-break states;
- weekend, holiday, early-close, DST, and configured-override behavior;
- deterministic calendar-definition identity;
- late consumer subscribe/snapshot/buffer/reconcile flow;
- snapshot timeout, typed rejection, incomplete response, and epoch-change handling;
- duplicate and conflicting transition handling;
- actor startup in alternate composition orders;
- bounded snapshot request and response populations;
- timer cancellation and no publication after stop;
- independent consumer failure isolation; and
- no new provider request or raw-data persistence.

### Cutover evidence

Before removing copied calendar evaluation, parity must cover every current consumer:

- `EvidenceHealthActor` current session expectations;
- historical window planning;
- completed-bar trade-date and phase classification;
- session-reference metrics;
- analytical-window metrics;
- phase-matched rolling baselines; and
- entity consumers which retain session identity.

A connected run may later confirm live transition timing and operational audit, but it is not
needed to review the initial actor contract and offline snapshot behavior.

## Explicit Non-Goals

- no analytical-window management;
- no historical provider execution;
- no metric or entity computation;
- no dynamic calendar mutation;
- no dynamic actor loading;
- no global event ordering;
- no raw schedule persistence;
- no Watchlist expansion;
- no agent control; and
- no execution authority.

## Remaining Decisions

Sole ownership, typed transitions, bounded projections, meaningful-boundary publication, startup-
only definitions, and removal of copied consumer evaluators are decided and implemented. The
remaining decision is the exact late-consumer snapshot and reconciliation protocol.

1. Define and approve the source-scoped current-state snapshot request/response contract, complete
   calendar accounting, retry/timeout outcomes, and bounded request population.
2. Define and prove the late-consumer subscribe, buffer, snapshot, reconcile, and epoch-change
   protocol before claiming restart-safe current-state delivery.
3. Run bounded connected acceptance before claiming live transition timing or operational-audit
   acceptance for the new contract.

## Advisory Basis

Architecture, data-quality/lineage, event-driven-architecture, and NautilusTrader consultations
agree that the current actor should be narrowed and strengthened rather than replaced by a
nonexistent native Nautilus calendar component. Nautilus `DataActor`, clock/timer, typed custom
data, signal, and lifecycle facilities remain appropriate transport and runtime mechanics. The
session semantics remain mcal-backed Markeitech responsibility.

The advisor conclusions are inputs to Markeitect's review. They do not approve this proposal.
