# Market Data And Acquisition

**Status:** Consolidated current architecture; active scope and connected evidence remain governed
by [`current-status.md`](../current-status.md)

This document owns the provider-data, observation-universe, watchlist, live-demand, historical-
dependency, and acquisition-control boundaries. It consolidates the still-current decisions from
the former provider-boundary, adaptive-data-plane, historical-execution, and watchlist plans.

## Core Boundary

NautilusTrader and the approved provider adapter own connectivity and native normalized market
objects. Markeitech does not wrap every quote, trade, bar, book, option, or instrument definition
in a parallel raw-data model.

`DataAcquisitionActor` is the sole logical owner of provider-facing live subscriptions and
historical requests. Consumers declare bounded demand. Acquisition resolves instruments,
validates support and policy, reconciles shared requirements, owns pacing/retry/cancellation, and
publishes lifecycle facts. Analytical actors, the watchlist, Discord, and future Sir Loke never
call IB directly.

```text
configuration/operator/future policy intent
    -> watchlist or capability declaration
    -> exact logical live/historical demand
    -> DataAcquisitionActor
    -> Nautilus DataEngine and approved provider adapter
    -> native objects delivered directly to admitted consumers
```

High-volume observations stay on native Nautilus paths. Acquisition lifecycle and evidence-health
facts may use low-volume typed messages and approved operational audit. PostgreSQL is not a raw
market-data archive.

## Four Independent Concepts

The runtime does not use one “active instrument” plus background instruments.

| Concept | Meaning |
|---|---|
| Trade-expression universe | Products eligible to express an approved thesis; SPXW and QQQ 0DTE are the V1 delivery boundary |
| Observation universe | Instruments currently admitted to provide decision evidence; membership may change under policy |
| Active capabilities | Deterministic calculations enabled for an instrument or related group, each with declared dependencies and cost |
| Focus | Temporary expiring priority which may increase depth, breadth, cadence, or reporting without redefining membership or truth |

An observed instrument is not automatically tradable. An expression is not automatically an
evidence source. Several instruments, capabilities, focus leases, opportunities, and trade
episodes may coexist within provider entitlements and configured resource bounds.

## Native Identity, Time, Source, And Fidelity

`InstrumentId` is canonical inside the current Nautilus runtime. It is not assumed to be a
cross-provider master identity. Preserve exact venue, raw symbol, provider metadata, and dated
futures contract identity. A logical future root or continuous symbol is an alias and never the
identity of the contract which produced an observation.

Preserve native `ts_event` and `ts_init` meanings. Do not invent a source timestamp, interpret
historical processing latency as live network latency, or decide a named session from local clock
time. A bar's `BarType`, aggregation source, and timestamp policy are part of its meaning.

Source and fidelity are field-specific:

- provider name is not the same fact as `InstrumentId.venue`;
- reported trades and sizes remain provider-reported, not assumed consolidated;
- aggressor side remains unknown when the source cannot prove it;
- external OHLCV bars are provider aggregates;
- locally aggregated bars are derived;
- order-book depth is not a consolidated full-market book without evidence;
- delayed or frozen data is never labelled real time; and
- unsupported, absent, partial, stale, and unknown are valid outcomes.

The current IB configuration keeps simplified symbology, MIC conversion disabled, quote batching
enabled, quote size-only updates preserved, and revised-bar handling disabled. A change to those
semantics requires explicit configuration, compatibility review, and acceptance.

## Live Demand And Subscription Lifetime

Every live demand identifies consumer, purpose, instrument, native feed kind/selector, source,
priority, optional expiry, correlation/causation, and capability/configuration versions.

The acquisition owner:

1. validates instrument resolution, entitlement/support, and resource bounds;
2. merges compatible consumer claims into one logical provider demand;
3. issues one native subscribe for the shared requirement;
4. distinguishes subscription command success from first usable observation;
5. tracks requested, subscribed, active, stale, failed, canceled, and stopped outcomes; and
6. releases the provider subscription only after the final authorized claim is gone.

Independent consumers register their own native Nautilus handlers after demand admission. They do
not receive a Markeitech fan-out copy of raw observations. The bounded Stage 8C acceptance showed
Nautilus sharing provider subscriptions while two actors received the native stream; this evidence
does not remove acquisition's logical lifetime ownership.

Book and option-chain request shapes require their own bounded contracts. Native type presence is
not evidence that the pinned IB adapter supplies every stream or field.

## Watchlist Ownership

`WatchlistActor` owns current configured observation membership and one bounded latest-state
projection per member. Configuration supplies the durable startup claims. It translates approved
business capabilities such as `top_of_book` or `watchlist_last` into logical demand, observes
native callbacks, and publishes membership/readiness facts—not raw market data.

The active profile remains configuration-seeded. Dynamic membership is deferred and requires a
focused decision covering:

- stable intent and claim owner identity;
- add, update, release, and focus actions;
- exact or policy-resolvable instrument identity;
- requested capabilities, priority, reason, correlation/causation, and expiry;
- deterministic policy disposition and measured provider/resource budgets;
- effective capabilities as the union of all active claims;
- release ordering so one claim cannot tear down another consumer's data;
- idempotent durable intent/lifecycle history and a rebuildable effective-membership projection;
- restart behavior which restores configured and still-valid claims but never resurrects expired
  runtime claims; and
- explicit provider gaps, including whether broad five-second bar-derived last is sufficient.

No operator, news workflow, model, or Sir Loke intent receives direct subscription authority.

## Historical Dependency Planning

Historical observations exist to satisfy declared live evidence needs, not to create replay
storage.

The ownership chain is:

1. a deterministic capability declares a symbolic versioned need;
2. `HistoricalEvidencePlannerActor` obtains canonical session state and resolves exact UTC bounds;
3. `DataAcquisitionActor` validates, deduplicates, budgets, queues, paces, and executes the request;
4. the native provider response is validated against identity, selector, bounds, order, and
   maximum observations;
5. a typed immutable transient batch reaches admitted consumers; and
6. each consumer publishes its own readiness result under its minimum-evidence contract.

Acquisition never defines RTH, GTH, overnight, premarket, opening range, power hour, or another
analytical window. The calendar owner supplies temporal facts; the planner resolves the purpose;
acquisition owns provider execution.

### Request identity and sharing

Provider request identity is content-derived from instrument, feed kind, selector, exact bounds,
limit, source, and immutable parameters. Consumer identity is excluded so compatible requests can
be executed once, while consumer lineage and purpose remain attached.

Historical requests define exact requested/received bounds, observation limits, priority,
deadline, timeout/retry policy, cancellation identity, evidence requirements, and resource cost.
Exact duplicates are idempotent. Unequal same-identity observations are conflicts. Raw batches are
discarded after they no longer contribute to approved calculation state.

### Supported window vocabulary

The implemented bar-history catalog can express previous/current named phases, overnight or
premarket windows, curb where configured, opening range, power hour, named phase slices, previous
sessions, recent completed bars, exact anchored intervals, and synchronized cross-instrument UTC
intervals. Every duration, phase, count, offset, anchor, selector, and maximum is explicit policy;
the resolver invents none.

Historical quotes and trades remain separate future feed kinds. Bars may not counterfeit them.

### Response and readiness

Every response records request/consumer lineage, selector/source/provider, exact bounds,
observation and duplicate/conflict/gap counts, event-time ordering, receive/completion timestamps,
fidelity, missing reasons, and terminal outcome.

Provider completion is not analytical readiness. Each consumer separately reaches `READY`,
`DEGRADED`, `FAILED`, `CANCELED`, or `EXPIRED` according to its own contract. A shared response may
therefore satisfy one consumer and leave another degraded.

The pinned native bar callback does not carry a request identifier sufficient for honest
concurrent attribution. The accepted path therefore runs one active historical request lane. Late
responses after local timeout/cancellation are ignored and audited rather than attached to a
different request. More concurrency remains a stop gate until native attribution is proven.

## Capability And Resource Policy

Each approved capability declares stable identity/version, supported instrument properties, live
feeds, exact history, output contract/cadence/units, bounded retained state, fidelity and
unsupported cases, parameters, resource cost, lifecycle, and health/audit events.

There is no universal base timeframe or warmup matrix. Each measurement independently declares
the smallest dependency which preserves its meaning. Direct provider bars and local aggregation
may be shared or substituted only when source, resolution, bounds, session, price basis, volume,
and fidelity semantics are compatible and equivalence has been validated.

Deterministic policy—not an agent—accepts, modifies, queues, rejects, expires, or cancels intents
according to allowed instruments/capabilities, parameter bounds, entitlements, provider limits,
priority, leases, and provider/CPU/memory budgets.

## Failure, Recovery, And Audit

One instrument or request failure does not stop unrelated feeds. Live and historical queues,
request depth, retries, pacing, timeouts, retained observations, and shutdown work are bounded.
Demand and recovery are event/timer driven.

Persist lifecycle facts such as declaration, admission, queueing, submission, sharing, retry,
first observation, readiness, degradation, failure, cancellation, expiry, and release. Preserve
request, consumer, configuration, policy, provider, and evidence identity. Do not persist raw
quotes, trades, bars, books, chains, or historical response arrays by default.

Open reliability debt includes initial subscription failure recovery, controlled provider
connection-loss/resubscription proof, consumer-detachment ordering, and explicit recovery evidence.
The current connected evidence is bounded to the sessions and profiles recorded in
[`current-status.md`](../current-status.md).

## Explicit Non-Goals And Stop Gates

- no fixed one-active-instrument hierarchy or permanent instrument whitelist;
- no parallel raw-data bus or duplicate provider cache;
- no actor-specific direct IB request path;
- no unbounded option-chain, book, history, or instrument-universe request;
- no assumption that data is consolidated, real time, complete, or supported;
- no persistent raw-data store justified by replay, backtesting, or future convenience;
- no model-authored formula, selector, provider parameter, or resource limit; and
- no order submission, modification, bind-for-control, cancellation, replacement, exercise, or
  close authority.
