# Runtime Foundation

**Status:** Consolidated current architecture; implementation detail and acceptance limits remain
governed by [`current-status.md`](../current-status.md)

This document is the compact authority for Markeitech's implemented runtime foundation. It
consolidates the still-valid decisions from the former messaging, control-plane, supervision,
composition, persistence, and provider-boundary records. Git and pull-request history preserve
the original decision chronology.

## Boundary Summary

Markeitech is one local, event-driven NautilusTrader `LiveNode` with code-owned actor composition,
native market-data delivery, bounded background workers for blocking side effects, and PostgreSQL
operational audit. The runtime is advisory and currently market-data-only. It has no broker
account/order/fill/position observer, conversational Discord bot, model, Sir Loke component, or
order-action path.

The foundation follows five rules:

1. Nautilus owns provider connectivity, normalized market objects, the DataEngine, cache,
   lifecycle, clocks, and native actor delivery where its semantics fit.
2. Markeitech owns product-specific composition, health meaning, provider-demand reconciliation,
   deterministic evidence, bounded operational workers, and approved audit records.
3. One component owns every canonical state transition, provider demand, durable write, and
   external projection responsibility.
4. Components converge from typed facts and current-state recovery; they do not rely on actor
   registration order, sleeps, or another component being ready by a guessed time.
5. An impaired component narrows its own dependents and reports failure without stopping unrelated
   work unless continuing would make system state dishonest.

## Composition

`build_actor_plan` and the code-owned actor registry define the allowed topology. Typed TOML may
select approved optional components and their configuration, but it cannot name arbitrary Python
imports or construct a plugin graph. `node.py` builds the Nautilus clients and registers the
validated plan; it does not redefine component ownership.

The active V3 ES profile is intentionally narrow. Its exact actor roster is maintained in
[`current-status.md`](../current-status.md#active-tracked-v3-profile). Other implemented actors and
pure contracts may be disabled, uncomposed, or retained only as migration evidence. Presence in
source, tests, or the diagram inventory is not evidence that a component is active.

Composition invariants are:

- one `SystemControlActor` owns global system-health transitions;
- one `DataAcquisitionActor` owns provider-facing demand and request lifetime;
- one `OperationalPersistenceActor` owns operational writes while the node is running;
- one `WatchlistActor` owns the effective configured observation membership used by the current
  profile;
- optional projections, probes, resource actors, and intelligence actors are included only when
  their validated configuration enables them;
- duplicate actor IDs and missing mandatory prerequisites fail before provider connection; and
- dynamic actor loading/removal and a generic dependency-injection or plugin system are not part
  of the current runtime.

## Messaging And State Transfer

Markeitech uses Nautilus communication facilities; it does not build a parallel in-process bus.

| Path | Use | Important limit |
|---|---|---|
| Native callbacks and cache | High-volume instruments, quotes, trades, bars, and supported provider objects | Preserve native identity and timestamps; do not republish raw streams for convenience |
| Versioned actor signals | Small operational events and requests | Transient delivery; string payloads require explicit Markeitech validation |
| Typed Nautilus custom data | Structured low-volume state, evidence, and bounded batches | Type and metadata identity must match the payload; not automatically durable |
| Actor-owned bounded queue | PostgreSQL or HTTP work outside the event callback | FIFO/order claims are local to the declared producer and queue |
| PostgreSQL | Approved durable operational facts and explicitly approved semantic state | Not the message bus and not a raw market-data store |

An event is an immutable occurrence. A snapshot or projection represents current state for a
late/recovering consumer. A command or intent requests work and must not be confused with its
acceptance, activation, or completion. A failure is an outcome with evidence, not a separate
transport.

Every consequential channel defines publisher, authorized consumers, identity, ordering scope,
duplicate handling, retry, backpressure, late/stale policy, persistence, and shutdown behavior.
At-least-once delivery with idempotent consumers is the default durable assumption; exactly-once
delivery is never inferred.

## Global And Local Health

`SystemControlActor` is the sole global-health transition owner. Current state vocabulary includes
`STARTING`, `READY`, `DEGRADED`, `FAILED`, and `STOPPING`. Repeating the current state is suppressed;
invalid transitions fail visibly.

Global `READY` remains deliberately narrow: the accepted startup prerequisites and configured
instrument-definition/acquisition conditions are satisfied. It does not prove that every feed is
fresh, a calendar-dependent consumer is synchronized, options are usable, broker state is
reconciled, Discord is connected, or Sir Loke can advise.

Local owners publish dimensional facts for provider demand, session state, evidence freshness,
historical readiness, resources, persistence, and enabled analytical capabilities. A process may
remain running while one instrument is stale or one optional projection is unavailable. Consumers
must evaluate the exact dependencies needed by their decision rather than treating global health
as permission to use all evidence.

Workers report sanitized results to their owning actor. Workers and projections never decide
global health. Unknown internal component identities are programming/configuration failures; a
malformed failure message is rejected and cannot change health.

## Failure, Recovery, And Bounded Work

Every component owns its local work and classifies failure as retryable, degradable, fatal, or
operator-actionable. Retry attempts, backoff, queues, retained state, timers, and shutdown drain
are configuration-bounded.

The runtime must:

- continue accepting unrelated safe work after a local failure;
- trigger recovery from dependency/state changes or explicit timer policy, never arbitrary sleep;
- mark stale or unavailable state rather than silently reuse it;
- keep callback work non-blocking and avoid nested framework mutation from synchronous handlers;
- stop accepting new work before placing a terminal marker behind accepted FIFO work;
- drain only within the configured deadline and report accepted, completed, failed, rejected, and
  pending counts; and
- preserve an honest incomplete durable record if shutdown or terminal persistence fails.

Provider subscription recovery and controlled connection-loss/resubscription acceptance remain
open debt. Recovery evidence is capability-specific; one later successful operation does not by
itself prove durable recovery.

## Canonical Provider Data

Native Nautilus objects are the canonical in-process transport for provider observations. A
Markeitech wrapper is not created merely to copy `InstrumentId`, prices, sizes, bar values, or
timestamps.

Acquisition context is kept beside the native stream or request lifecycle and includes provider
and client identity, resolved instrument, subscription/request identity, data mode, bar selector,
regular-hours policy, exact bounds, completion/cancellation/failure, and observed support. It is
not repeated on every high-volume observation unless a reviewed consumer requires it.

`InstrumentId` is canonical inside the current Nautilus runtime, not a universal cross-provider
identity. Provider-native contract fields, raw symbol, venue meaning, and exact futures expiry
must remain available. A continuous futures root is an alias and never replaces the identity of
the contract which produced an observation.

Preserve native `ts_event` and `ts_init` semantics. Do not invent source timestamps, infer session
from local clock time, or label delayed, provider-aggregated, locally aggregated, partial, or
unknown evidence as higher-fidelity truth. Source and fidelity are field-specific.

The complete acquisition and historical-demand contract is maintained in
[`market-data-and-acquisition.md`](market-data-and-acquisition.md).

## Persistence Ownership

PostgreSQL is the durable audit ledger for approved operational facts. Before provider connection,
the outer CLI performs schema preflight/migration and opens the runtime run. While Nautilus is
active, `OperationalPersistenceActor` owns operational SQL through one bounded worker. After the
node returns cleanly, the CLI records the terminal `STOPPED` outcome because no stopped actor can
truthfully do so.

Implemented durable families include runtime runs, system-health events, generic operational
events, and compact evidence-recency profiles. Each newly approved product record requires its own
schema, identity, transaction, ordering/idempotency, retention, redaction, recovery, and query
decision.

PostgreSQL does not become:

- a duplicate configuration source;
- the in-process event bus;
- a raw quote, trade, bar, book, option-chain, or historical-response warehouse;
- a line-by-line runtime-log copy; or
- speculative storage for replay, backtesting, ML, or future convenience.

Required durable state is committed before dependent lifecycle progress is published. Repeated
writes use stable idempotency boundaries. Schema creation and repair are idempotent; destructive
migration requires separate approval and a recovery plan.

## External Projections

Console, Discord webhooks, visual capture, a future Discord bot, and a future UI are projections.
They render canonical state and delivery outcomes; they do not calculate or mutate market,
broker, policy, or trade truth.

The current [`DiscordHealthActor`](../operations/discord-health-webhook.md) is an optional outbound
webhook projection. It is not Sir Loke. Visual evidence capture is a passive, non-gating review
projection governed by [`visual-evidence-review.md`](../operations/visual-evidence-review.md).

Projection failure must remain bounded and must not stop provider ingestion, deterministic
analysis, broker reconciliation when later added, or required durable audit.

## Acceptance Limits

Offline tests establish only their exercised schemas, calculations, state transitions, and
failure paths. Recorded connected runs establish only their exact provider, account, instrument,
session, configuration, and version envelope. Neither source inventory nor a generated diagram is
proof of runtime composition or live delivery.

Use [`current-status.md`](../current-status.md) for the current acceptance envelope and
[`tools/system-diagram/docs/maintenance.md`](../../tools/system-diagram/docs/maintenance.md) for the
non-authoritative architecture-diagram procedure.
