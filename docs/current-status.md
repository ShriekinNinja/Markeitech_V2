# Current Status

Last reviewed: 2026-08-22

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
membership remains intentionally deferred. Stages 9A through the first Stage 9C runtime family are
live-accepted. A proposed Stage 9C session-measurement extension now precedes Stage 9D so entity
contracts are shaped by proven bar/session inputs rather than assumptions.

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

Stage 9A is complete and accepted at commit `ce9076e`:

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

The corrective Stage 9A/Priority 0 persistence-safety gate is implemented and live-accepted. The
2026-08-17 mega-clean boot recreated PostgreSQL from an empty volume, applied all migrations,
reached `READY`, and shut down cleanly. It stored all 490 accepted records with no retries,
failures, rejections, pending records, sequence gaps, or duplicates. The batch writes PostgreSQL in
bounded transactions, reserves critical audit capacity, validates startup capacity, suppresses
repeated identical persistence-failure logs, and prevents recoverable queue pressure from creating
the invalid `FAILED -> STARTING` transition. Queue admission remains non-blocking and rejected
payloads remain an explicit audit gap.

Evidence recency now supports configurable, persisted adaptive quote profiles keyed by instrument,
feed, selector, provider, session phase, and policy version. Profiles checkpoint compact derived
statistics only; raw observations remain transient. SPX/VIX use cash-session, bar-derived-last
expectations, and Watchlist observation truth now follows each instrument's declared capabilities.
Acquisition retains provider subscription lifetime ownership during shutdown.

The same acceptance run proved profile learning for ES, NQ, YM, and CL. Brief overnight quote
freshness transitions showed that the configurable two-second hard fresh floor is still sensitive
to natural delivery pauses. Transition hysteresis or persistence windows are tracked as Priority 1
calibration; this does not block Stage 9B.

## Stage 9B: Historical Dependency Execution

Stage 9B is complete and live-accepted as of 2026-08-17. One shared provider request served two
independent consumers and produced separate readiness results while unrelated runtime activity
continued. Historical observations remained transient; PostgreSQL stored only request, execution,
and readiness lifecycle records. The accepted timestamp boundary is UTC internally with
instrument-timezone formatting confined to the Nautilus IB adapter request boundary.

## Stage 9C: Baseline Metric Contracts

Stage 9C is complete and live-accepted as of 2026-08-19. The first runtime metric family publishes
three deterministic quote-quality values through native signals at a configured bounded cadence.
Watchlist and metric consumers share one provider subscription per instrument, and the metric
actor obtains evidence-health snapshots without startup sequencing.

The acceptance run received 2,111 quotes, suppressed 1,466 by cadence, executed 645 calculation
cycles, and published exactly 1,935 values. Evidence states reconciled exactly: 981 `HEALTHY`, 24
`DEGRADED`, 924 `DORMANT`, and 6 `STALE`; there were no calculation or publication failures.
PostgreSQL stored 464 operational records and 3 system-health records, matching the persistence
runtime's 467 accepted/stored total with no failures or pending writes. Numerical metric values and
raw quotes remain intentionally transient.

The active extension is the Stage 9C session-measurement work documented in
[`roadmap/v2-stage-9c-session-measurements-plan.md`](roadmap/v2-stage-9c-session-measurements-plan.md).
It closes the completed-bar, session/prior-session, opening-range, gap, power-hour, volatility,
efficiency, and expansion input gap before Stage 9D entity design. Slices 1-2 are enabled and
live-accepted. The acceptance run converged bounded historical and live bars for all 18 configured
instruments, published 1,281 completed-bar values from 183 accepted bars, and reported no actor
calculation failure, duplicate, or conflict. Closed-session recent-history requests degraded
independently without stopping live processing; this confirmed the need for Slice 3's exact,
purpose-specific session windows rather than a universal recent-history warmup.

Slice 3 is accepted at commit `8696acf`. It adds only deterministic active-session,
previous-session, optional overnight, and gap measurements. Historical and live observations
converge at the last interval actually received, and exact open, prior-close, return, and gap
values remain unavailable when their session boundary was not directly observed rather than being
inferred from partial coverage.

Slice 4 is locally accepted. It adds
configuration-owned calendar-relative opening-range families and close-relative power-hour
measurements, including developing/completed truth, coverage, supported-volume isolation, and
early-close handling. The initial acceptance scope configures two opening ranges and one power-hour
window for the CME-equity profile only; expanding profiles requires an explicit session-semantics
review. It does not add entities, semantic events, signals, agent behavior, raw market-data
persistence, or execution.

Slice 5 is live-accepted and committed at `116657b`. It adds three
configuration-owned rolling families over one-, five-, and fifteen-minute completed bars, with 24
active duration candidates and 264 versioned numerical metric definitions. Every candidate reports
range, realized log-return magnitude, average true range, directional efficiency, coverage, and
independently qualified recent and phase-matched expansion baselines. Candidate durations,
reference counts, coverage requirements, selection metadata, and dynamic eligibility all have
explicit configuration envelopes. A bounded 720-observation one-minute warmup can support each
current candidate window, while the 8,000-observation transient ledger can eventually satisfy the
minimum recent baseline for the longest candidate; neither is a universal historical pyramid.
Numerical values and raw bars remain transient, and no semantic regime, compression, trend, signal,
entity, or agent decision is created in this slice.

The extended 2026-08-21 RTH acceptance completed all 63 historical dependencies with zero
degradation and kept all 34 acquisition streams active. Across 32,659 live bars and 18 historical
batches, the measurement actor accepted 10,632 completed bars, identified 13 exact duplicates and
zero conflicts, and published 103,236 completed-bar values, 44,718 session-reference values, 1,779
calendar-window values, and 307,296 rolling values across 2,736 rolling batches. It reported zero
calculation failures. PostgreSQL stored all 32,389 accepted operational events with zero retries,
failures, rejections, or pending writes; Discord delivered all three health messages; shutdown
completed cleanly.

The run also exposed separate hardening concerns which do not invalidate the deterministic
measurement results: evidence-health transitions remain too noisy for some thin instruments, late
evidence callbacks can appear after their actor has entered shutdown, and closed-session calendar
windows were rejected before their future phase began. The first two remain follow-up work. The
closed-session path is now implemented for review as typed, deduplicated deferral with exact
first-completed-boundary retries and session-transition wakeups. Invalid policies still fail hard,
and unrelated acquisition remains active. The optional Observatory ran concurrently during this
acceptance, so its suspected host resource cost is isolated on `v2-stage-observatory` rather than
attributed to Stage 9C.

Stage 9C session measurements are closed. They provide numerical evidence for future entities and
semantic events; they do not themselves classify market state or create opportunities.

## Runtime Resource Hardening

Commit `ba442c4` adds the reviewed passive `RuntimeResourceActor`. The first short connected run
persisted all seven raw samples and showed bounded RSS/cache growth with no sampling failure. At a
configuration-owned cadence the actor publishes process memory, CPU, thread, file-descriptor, host
memory/CPU/swap, disk headroom, and public Nautilus cache-count evidence through the typed
`markeitech.runtime.resource` contract. The existing operational persistence actor records samples
as `runtime.resource`; no raw market data or new database table is introduced.

The current hardening branch adds a separate `RuntimeResourceHealthActor`. It evaluates only
configuration-owned, versioned thresholds with sustained warning/critical/recovery windows and
publishes durable semantic transitions on the non-overlapping `markeitech.runtime.health` signal as
`runtime.resource_health` operational events. Discord remains a read-only
projection: critical transitions may ping; warnings and recoveries do not; raw samples are never
sent. The actor does not mutate Nautilus cache policy, alter global system health, or select Redis.

The 2026-08-22 Observatory-off run collected 20 bounded samples with flat cache counts and no
sampling failures. It also exposed Nautilus prefix-routing overlap between the original raw and
health signal names: one transition re-entered the health actor and reached persistence twice,
rolling back a three-record batch. The health signal now uses a non-overlapping namespace, consumers
guard exact signal names, and the disk critical-percentage threshold is versioned at 2% so the
observed 17.5 GiB / 3.8% state remains warning-level while the 5 GiB absolute critical guard stays
active. Offline verification passes 302 tests with two PostgreSQL-marked tests deselected.

The corrected connected rerun collected 15/15 durable raw samples and one sustained
`NORMAL -> WARNING` disk-headroom transition under policy `2026-08-22-v2`. The health actor reported
zero rejected samples; Discord delivered all four eligible lifecycle/resource messages; global
system health remained `READY` until controlled shutdown; and PostgreSQL reconciled all 726 accepted
records with zero retries, failures, rejections, or pending writes. Process RSS grew only 3.3 MiB,
cache counts remained bounded, and Nautilus returned cleanly. The resource warning path and signal
routing correction are connected-accepted; critical and recovery projection remain controlled
follow-up cases rather than blockers for this hardening batch.
