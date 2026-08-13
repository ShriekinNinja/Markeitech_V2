# Current Status

Last reviewed: 2026-08-12

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

## Explicit Boundaries

- PostgreSQL does not contain market data, Discord deliveries, configuration, logs, or IB
  instrument definitions.
- Reconstructable market data will be requested from IB when required by live operation rather
  than retained speculatively.
- Raw market-data persistence, Parquet, replay, and backtesting are outside current scope until
  Markeitect explicitly reopens them.
- Redis, external message streams, actor snapshots, dynamic actor
  composition, analytics, and trading models remain unimplemented.
- V1 remains preserved for reference and reuse, but no V1 runtime behavior is implicitly active.

## Next Accepted Sequence

Stage 8A now owns instrument-definition acquisition. Remaining Stage 8 decisions still define
live and historical acquisition behavior; none are implied by this slice. Stages 1 through 9 form
the functional live runtime core; Stages 10 and 11 harden observability, tests, and upgrades.
Market intelligence begins afterward with separately approved analytical entities, semantic
events, rolling state, options context, ML, and an advisory AI observer.

The complete gated sequence is maintained in
[`roadmap/v2-infrastructure-plan.md`](roadmap/v2-infrastructure-plan.md).
