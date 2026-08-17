# V2 Supervision And Failure Policy

Status: accepted for Stage 6 implementation on 2026-08-05.

## Purpose

Stage 6 makes existing V2 components honest under failure. It does not add market-data,
analytics, monitoring infrastructure, dynamic actors, or a generic plugin framework.

Each component owns its local work and reports structured failures. `SystemControlActor`
remains the sole owner of global runtime health.

## Event-Driven Isolation Invariant

Runtime components must not depend on actor registration order, arbitrary delays, or a prescribed
startup sequence. Each actor registers its own handlers during its Nautilus lifecycle, consumes
immutable state/events idempotently, and converges whenever its dependencies become available.

A component failure may degrade the capability it owns, but must not stop unrelated components or
silently discard future work. The owner keeps failed work bounded and retryable under configurable
policy, publishes failure and recovery facts, and continues accepting work whenever doing so is
safe. Recovery is triggered by dependency/state changes or explicit retry policy, never by an
assumption that another actor "should be ready by now."

Nautilus callbacks must not recursively perform framework mutations which require a second mutable
borrow of actor state. In particular, a signal handler may update local state and publish facts, but
native data-handler registration belongs to actor lifecycle/recovery callbacks outside nested
signal dispatch. Tests must vary event order and duplicate delivery so the same converged state is
reached regardless of which independent component reports first.

## Failure Classes

| Class | Meaning | Runtime response |
| --- | --- | --- |
| Retryable | A bounded local retry may recover the operation. | Retry within the owning component. |
| Degradable | A required capability is impaired after startup, but the runtime can remain observable. | Publish a component failure and transition global health to `DEGRADED`. |
| Fatal | Continuing would make runtime state dishonest. | Transition global health to `FAILED`; runtime shutdown orchestration remains Nautilus-owned. |
| Operator-actionable | Automatic recovery is inappropriate. | Reject startup before connecting to IB with a clear reason. |

## Approved Component Policy

| Component or condition | Startup | Runtime | Shutdown |
| --- | --- | --- | --- |
| PostgreSQL unavailable | Reject before IB; a race-time actor failure is `FAILED`. | Retry individual writes; exhausted retries produce `DEGRADED`. | Drain accepted work within the configured timeout and report any remainder. |
| Persistence queue full or closed | Not applicable after successful preflight. | Produce `DEGRADED`; never grow memory without a bound. | Report rejected and pending work truthfully. |
| System control fault | `FAILED`. | `FAILED`. | Publish `STOPPING` when the actor receives a normal stop. |
| Discord unavailable or slow | Reject before IB only when enabled but misconfigured. | Log and count delivery failure; global health is unchanged. | Best-effort bounded drain; never hold runtime shutdown indefinitely. |
| IB or acquisition failure | Existing Nautilus behavior only in this stage. | Deferred to Stage 8, where the acquisition owner exists. | Existing Nautilus behavior only in this stage. |

## Message Ownership

Workers never decide global health. A worker returns a sanitized result to its actor. The
actor logs the result and, when the policy requires it, publishes a typed component-failure
event. `SystemControlActor` maps that event to the global health state machine.

Malformed component-failure events are rejected, logged, and counted. They do not change
global health. Unknown component identities are treated as fatal programming/configuration
faults because only code-owned actors can publish this internal contract.

## Retry Boundary

Only PostgreSQL health-event writes receive retries in Stage 6. Attempts and backoff are
bounded and configured. The `(run_id, sequence)` uniqueness boundary makes repeated writes
idempotent. Exhausted records are not retained indefinitely in memory.

Discord remains best effort and does not receive a retry loop in this stage.

## Recovery Boundary

Stage 6 does not add `DEGRADED -> READY`. One later successful write is insufficient proof
that a dependency has recovered durably. Recovery evidence and hysteresis require a
separate approved decision.

## Counters

Persistence reports accepted, stored, retry attempts, permanently failed, rejected, and
pending work. Discord reports accepted, delivered, failed, rejected, and pending work.
System control reports component failures received, malformed reports, health transitions,
and suppressed duplicate transitions.

Counters are bounded lifetime observations emitted in component shutdown summaries. This
stage does not add Prometheus, Redis, or a metrics service.

## Shutdown Contract

1. Stop accepting new work and unsubscribe from signals.
2. Place a terminal marker after already accepted FIFO work.
3. Drain within the component's configured timeout.
4. Never wait indefinitely.
5. Log accepted, completed, failed, rejected, and pending work.
6. Preserve the existing CLI responsibility for closing the PostgreSQL runtime-run record.
