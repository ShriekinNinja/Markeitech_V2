# Current Status

Last reviewed: 2026-08-16

This page is the source of truth for current implementation progress. Markeitech V2 is the active
system. The preserved V1 status is available in
[`archive/v1-current-status.md`](archive/v1-current-status.md) and does not define V2 behavior.

## Operating Posture

- V2 is a clean runtime foundation on NautilusTrader `2.0.0rc1`.
- Interactive Brokers paper trading is the current provider connection.
- The system provides observation and decision support only; automated execution is absent.
- Components communicate through approved Nautilus actor facilities.
- Each actor owns one responsibility and consumers do not redefine source facts.
- Previous analytics, indicators, levels, signals, models, and trading assumptions are not active
  V2 requirements.
- Markeitect approves architecture decisions before implementation proceeds.

## Live-Accepted Foundation

- Isolated V2 Python project, configuration, environment, dependencies, and runtime logs.
- One PyCharm **Markeitech V2** run configuration with macOS caffeination.
- Nautilus `LiveNode` construction and clean shutdown.
- Interactive Brokers connection through TWS paper trading.
- Configured ES and SPY instrument-definition resolution.
- Versioned system-health signal contract.
- `SystemControlActor` with honest `STARTING`, `READY`, `FAILED`, and `STOPPING` ownership.
- Read-only Discord projection of system-health transitions.
- Discord failure isolation and bounded worker shutdown.

## Stage 4: Operational Persistence

Implementation is complete for review on branch `v2-stage-4-persistence-boundary`:

- PostgreSQL is the accepted operational source of truth.
- Docker Compose owns the local PostgreSQL service and persistent volume.
- The existing PyCharm run configuration starts PostgreSQL and waits for health before Markeitech.
- Versioned migrations run under a PostgreSQL advisory lock before IB startup.
- Every runtime receives a UUID run record.
- `OperationalPersistenceActor` is the sole writer while Nautilus runs.
- System-health events are stored in order with database-enforced idempotency.
- `READY` requires both instrument definitions and operational persistence readiness.
- Mid-run persistence failure produces the first approved `DEGRADED` transition.
- `STOPPING` remains actor-owned; the CLI records `STOPPED` only after `LiveNode.run()` returns
  cleanly.
- A crash, forced kill, or failed terminal write intentionally leaves an incomplete run.
- Restart reads, duplicate handling, migrations, and clean closure pass against real PostgreSQL.

Stage 4 is committed and live-accepted.

## Stage 5: Actor Composition

Implementation is approved and committed on branch `v2-stage-5-actor-composition`:

- A pure actor plan owns the complete static runtime topology.
- System control and operational persistence are mandatory core actors.
- Discord is explicitly enabled or disabled in typed configuration.
- Enabled Discord requires its webhook before IB startup; later delivery failure remains isolated.
- Actor and config import paths are code-owned rather than supplied through TOML.
- Immutable startup prerequisites replace the transient persistence-ready signal.
- Runtime persistence failure remains a separate fact; only system control may transition the
  system to `FAILED` or `DEGRADED`.
- Dynamic plugins, actor removal, and generic readiness infrastructure remain deferred.

Stage 5 is committed and live-accepted.

## Stage 6: Supervision And Failure Policy

Implementation is approved and live-accepted on branch `v2-stage-6-supervision-policy`:

- Component failures use one versioned internal signal contract.
- Workers return sanitized results to their owning actors and never decide global health.
- System control remains the sole owner of global `DEGRADED` and `FAILED` transitions.
- PostgreSQL health-event writes use configured bounded attempts and backoff.
- Exhausted PostgreSQL writes, queue rejection, and shutdown timeout report one structured
  component failure without retaining unbounded work.
- Discord remains optional and best effort; delivery failure never changes global health.
- Persistence, Discord, and system control emit bounded lifetime counters at shutdown.
- Both workers stop accepting work, drain accepted FIFO work within their timeout, and allow a
  later cleanup attempt to finish after an initial timeout.
- Recovery from `DEGRADED` to `READY` remains deliberately deferred until durable recovery
  evidence is defined.

Stage 6 is committed and live-accepted.

## Stage 7: Provider And Canonical Data Boundary

Implementation is approved and committed on branch `v2-stage-7-provider-data-boundary`:

- Native Nautilus instruments and market-data objects remain the runtime transport contracts.
- IB symbology, MIC conversion, quote batching, size-only quote updates, and revised-bar behavior
  are explicit V2 configuration.
- Provider context and request policy remain separate from high-volume native observations.
- Native instrument identity, source fidelity, and timestamps are not rewritten.
- Markeitech-owned market-data contracts remain possible later when a concrete requirement cannot
  be represented safely by native types and acquisition context.
- Preservation means honest live transit, not durable raw market-data retention.

Stage 7 is committed and offline-verified.

## Stage 8: Data Acquisition Ownership

Stage 8A is implemented for review on branch `v2-stage-8-acquisition-ownership`:

- `DataAcquisitionActor` is a mandatory core actor and the sole owner of provider-facing
  instrument-definition requests.
- It discovers definitions already present in the Nautilus cache and requests each missing
  configured definition once.
- A versioned acquisition status reports expected, available, and missing definitions.
- `SystemControlActor` consumes acquisition status and remains the sole owner of global readiness.
- A publish-on-start and post-start request handshake avoids depending on actor registration order.
- This slice adds no live subscriptions, historical bars, persistence, pacing policy, recovery,
  analytics, or trading behavior.

Stage 8A passes offline contract, ownership, deduplication, composition, state-transition, and
Nautilus bus-delivery tests. Live review remains pending.

Stage 8B's architecture direction is approved. It replaces V1's fixed active/background model
with four independent concepts: trade universe, dynamic observation universe, active analytical
capabilities, and temporary focus. The target is a broad continuous native market-data plane
feeding deterministic analysis and semantic state, with a later advisory agent directing
attention through policy-checked intents. No Stage 8B runtime behavior has been implemented.

Stage 8B.1 is committed. Stage 8B.2 and 8B.3 are ready for review:

- reusable analytical capability requirements and instrument-bound feed demand;
- explicit demand ownership, priority, optional expiry, and lifecycle vocabulary;
- pure multi-consumer provider-demand reconciliation;
- one provider-neutral coordinator owning subscribe and unsubscribe lifetime;
- one subscribe for shared demand and one unsubscribe only after the final consumer leaves;
- retryable provider failures which are never reported as active;
- native Nautilus translation for simple instrument, quote, trade, bar, status, and option-Greek
  subscriptions; and
- explicit deferral of richer book and option-chain subscription contracts.

The installed compiled Nautilus core did not expose enough subscription reference-count state for
an honest offline proof of duplicate-actor behavior, so Stage 8C completed that proof against a
live IB connection.

Stage 8C is complete on branch
`v2-stage-8c-continuous-native-stream`:

- standalone configuration schema 3 explicitly declares bootstrap native feeds and the bounded
  probe controls;
- the proof profile requests quotes and trades for configured ES and SPY;
- no feed is inferred merely from observation-universe membership;
- `DataAcquisitionActor` starts streams only after instrument-definition readiness;
- lifecycle facts distinguish `REQUESTED`, `ACCEPTED`, `SUBSCRIBED`, and first-observed `ACTIVE`;
- each demand remains correlated through its stable demand ID;
- raw observations remain native, transient, unwrapped, and unpersisted; and
- shutdown cancels each bootstrap demand while the coordinator protects shared subscriptions.

The live proof registered a temporary `NativeConsumerProbeActor` for those same native quote and
trade streams. Both actors received all four streams. Eight actor-level subscribe commands became
four provider subscriptions. The probe then unsubscribed after 15 seconds with 72 observations,
while `DataAcquisitionActor` continued to 464 observations before shutdown. Provider
unsubscription occurred only during final shutdown. This proves native multi-actor delivery,
provider deduplication, and subscription lifetime safety for this path.

The diagnostic probe remains available behind explicit configuration but is disabled in the normal
runtime profile. It adds no custom market-data envelope, fan-out, persistence, analytics, or
fallback implementation. Offline tests cover configuration, composition, logical deduplication,
lifecycle meaning, first observation, cancellation, retry, and native call mapping.

The subsequent scalable-watchlist POC registered a core `WatchlistActor` for eight instruments.
IB delivered native best-bid/ask updates and external five-second bars to the actor while
`DataAcquisitionActor` anchored the shared provider subscriptions. Broad tick-by-tick `AllLast`
requests reached IB limit `10190`, so tick trades remain a focus-only capability rather than a
baseline watchlist feed. The accepted POC retains bounded readiness transitions and shutdown
summaries; temporary per-update logs were removed after live review.

The actor is now a bounded core state owner with immutable versioned snapshots, native event
timestamps, separate registration and observation state, and out-of-order protection. Versioned
membership and lifecycle contracts are published and persisted through the generic PostgreSQL
audit boundary.
Dynamic membership is explicitly deferred; the accepted stopping point is a live-proven static,
configuration-owned watchlist. The exact handoff is
[`roadmap/v2-static-watchlist-handoff.md`](roadmap/v2-static-watchlist-handoff.md).

The generic PostgreSQL operational ledger and store boundary are implemented. Current acquisition
control events plus static watchlist membership and lifecycle events are wired through the same
ordered bounded persistence worker. A versioned request/ready handshake now gates system control,
data acquisition, and watchlist startup until the in-node persistence worker is subscribed and
its Nautilus startup callback has returned. This replaces the watchlist's timing-based startup
delay and preserves acquisition
`REQUESTED`, `ACCEPTED`, and `SUBSCRIBED` events before the first `ACTIVE` observation. PostgreSQL
preflight reapplies idempotent schema definitions and verifies required tables and columns. A
dropped applied-migration table is therefore recreated before runtime readiness instead of failing
on its first write. No audit event includes raw quote or bar payloads. The startup-audit closure is
implemented for live review on branch
`v2-stage-8e-startup-audit-closure`.

The configuration-ownership slice replaces the root instrument list with typed static
watchlist members. Each member declares its provider instrument ID, permanent owner IDs, and the
capabilities the current watchlist actually provides. System control, instrument-definition
acquisition, the IB provider, actor composition, and membership audit all consume that one member
set. The subsequent static completion removes duplicated bootstrap feeds: Watchlist
capabilities now publish stable demand contracts, Acquisition alone owns provider subscription
lifetime, and each consumer registers its own native Nautilus handlers during actor startup.
Provider subscription outcomes and local consumer readiness converge independently in either
order. Demand, provider outcome, degradation, recovery, and release are operational audit facts;
raw market observations remain memory-only. Session-unaware elapsed-time staleness is deliberately
deferred.
The complete 18-member baseline is now configured through Nautilus IB simplified `load_ids`, with
required startup resolution and explicit September 2026 ES, NQ, YM, and CL contracts. This mapping
is ready for live proof; automatic futures rolling is not implied.

## Explicit Boundaries

- PostgreSQL currently contains runtime runs and system-health transitions. It is the accepted
  durable audit ledger for all future meaningful system intents, decisions, lifecycle changes,
  publications, attempts, and outcomes.
- PostgreSQL does not contain raw ticks, quotes, bars, books, or option-chain payloads. Market-data
  requests, readiness, freshness, gaps, retries, and failures are system events and must be
  audited as their owning components are implemented.
- Ordinary diagnostic logs and individual internal callbacks remain outside PostgreSQL.
- Reconstructable market data will be requested from IB when required by live operation rather
  than retained speculatively.
- Raw market-data persistence, Parquet, replay, and backtesting are outside current scope until
  Markeitect explicitly reopens them.
- Redis, external message streams, actor snapshots, dynamic actor
  composition, analytics, and trading models remain unimplemented.
- V1 remains preserved for reference and reuse, but no V1 runtime behavior is implicitly active.

## Next Accepted Sequence

The static watchlist and live acquisition ownership foundation are complete. Dynamic watchlist
membership remains intentionally deferred. Market intelligence design is now in review on branch
`v2-stage-9-market-intelligence-design`.

The authoritative proposed coding order is:

1. session and calendar ownership;
2. evidence-health contracts;
3. historical dependency execution;
4. baseline metric contracts;
5. entities and rolling state;
6. first semantic events;
7. bounded options-data proof;
8. cross-instrument state;
9. richer analytics; and
10. the live advisory agent.

The agent maintains a plural opportunity set. No instrument is globally preferred, and the
initial SPXW/SPY/QQQ expression universe remains configurable and expandable. All variable market,
analysis, policy, and resource parameters follow the charter's configuration and optimization
principle.

The pre-coding design gate is accepted: opportunities are target-exposure and episode based rather
than source-instrument or contract based, and first-batch parameters are startup-configurable while
carrying explicit future mutability and optimization metadata.

The detailed sequence and gates are maintained in
[`roadmap/v2-first-market-intelligence-coding-sequence.md`](roadmap/v2-first-market-intelligence-coding-sequence.md).

## Stage 9A: Session And Evidence Truth

Stage 9A is implemented for review on branch `v2-stage-9a-session-evidence-health`:

- `pandas-market-calendars` supplies local exchange schedules, holiday rules, DST handling, and
  early-close dates.
- Typed startup configuration maps every watchlist member to one of four versioned calendars and
  defines SPXW GTH/RTH/Curb phases plus explicit exceptional-session overrides.
- `SessionStateActor` owns session/trade-date truth and publishes only initial or changed state.
- `EvidenceHealthActor` consumes acquisition lifecycle facts and independently observes the same
  native Nautilus quote and five-second-bar streams.
- Configured freshness policies distinguish not-yet-evaluated, dormant, healthy, degraded, stale,
  and unavailable evidence without treating a closed market as failed or confusing observation
  age with source fidelity.
- Consumer registration occurs outside nested signal dispatch. Local attachment failures are
  isolated, explicitly unavailable, and retried on configurable cadence; unrelated actors keep
  operating.
- Runtime readiness converges from local registration and acquisition events in either order; it
  does not rely on actor order, sleeps, or a prescribed startup sequence.
- Session and evidence transitions are stored in the existing PostgreSQL operational ledger; raw
  market observations remain memory-only.
- Offline tests cover calendar boundaries, DST, holidays, early closes, freshness transitions,
  strict wire contracts, actor composition, and persistence conversion.

The detailed ownership and semantics are recorded in
[`architecture/v2-session-evidence-health.md`](architecture/v2-session-evidence-health.md).
Live IB acceptance remains Markeitect-owned and has not been run for this batch.
