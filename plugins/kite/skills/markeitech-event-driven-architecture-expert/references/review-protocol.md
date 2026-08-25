# Event-Driven Architecture Review Protocol

Use this protocol for consequential design, review, or failure analysis. Adapt its depth to the
risk, but do not omit a boundary whose failure could invalidate the recommendation.

## 1. Frame The Requirement

State:

- the fact, state, request, or effect that must be communicated;
- why it exists and which accepted product requirement needs it;
- the accepted source of truth and owner allowed to change it; if placement or authority is absent
  or conflicting, hand that question to architecture boundaries rather than assigning it here;
- latency, loss, duplication, ordering, staleness, and recovery tolerance;
- whether the boundary is local, cross-thread, cross-process, durable, provider-facing, or
  externally projected; and
- what must continue operating when this path fails.

Do not begin with a preferred broker, actor count, topic layout, retry library, or pattern name.

## 2. Classify The Message

Use one primary meaning:

| Kind | Meaning | Key question |
|---|---|---|
| Event | Immutable fact that occurred | Who is authoritative for the occurrence? |
| Snapshot | Current state for synchronization or recovery | What version and as-of boundary does it represent? |
| Command or intent | Request for an owner to act | How is acceptance distinguished from completion? |
| Query or snapshot request | Request for information | What consistency and timeout contract applies? |
| Acknowledgement | Evidence of a named processing milestone | Send, enqueue, receipt, validation, durable effect, or business completion? |
| Failure outcome | Observable result of attempted work | Is it retryable, terminal, canceled, expired, or superseded? |

A mutable snapshot is not an event log. A command is not proof of state. A transport
acknowledgement is not proof of a business effect.

## 3. Build The Event-Driven Architecture Matrix

Produce one row per material channel, callback, queue, request lane, durable boundary, or external
projection.

| Requirement | Authoritative owner | Producer and authorized consumers | Contract and identity | Delivery and ordering boundary | Idempotency and conflict behavior | Retry, timeout, cancellation | Capacity and overload outcome | Startup, shutdown, recovery | Evidence and decision |
|---|---|---|---|---|---|---|---|---|---|

For each row, distinguish current verified behavior from proposed policy. If a field is unknown,
write `Unknown` and identify the smallest proof rather than filling it with convention.

## 4. Contract Census

Inspect the exact current contract for:

- message/event ID, subject ID, source/owner, schema and semantic version;
- event/effective time, observation/receive time, publication time, and timezone meaning;
- run, instrument/contract, provider/venue, session, configuration, and evidence lineage where
  meaning depends on them;
- correlation, causation, attempt, revision, sequence, and deduplication identity;
- allowed producers, consumers, routing key/topic/data type, and compatibility behavior;
- payload bounds, optional fields, unsupported fidelity, and validation failure;
- delivery, ordering, duplication, late/out-of-order, replay, and conflict rules;
- retention/persistence, privacy/licensing, observability, and audit; and
- startup handshake, late-consumer synchronization, cancellation, expiry, and shutdown.

Keep transport identity separate from evidence meaning. This advisor owns message, attempt,
correlation, causation, acknowledgement, delivery, and deduplication behavior. The market-evidence
validation specialist owns the meaning of provider/instrument identity, revisions, observation
timestamps, sessions, staleness, conflicts, lineage, and fidelity; consume that meaning rather than
redefining it here.

Prefer a narrow typed contract over a general envelope that hides ownership or semantic meaning.
Do not wrap high-volume native observations merely to make the architecture appear uniform.

## 5. Idempotency And Retry Analysis

For every retrying operation, answer:

1. Which failures are transient and retryable?
2. What deadline, maximum attempts, backoff, jitter, pacing, and cancellation policy applies?
3. What stable operation key survives retries and restart?
4. Where is duplicate detection performed, for how long, and with what bounded memory or durable
   state?
5. What happens when the same identity arrives with different content?
6. Is the effect itself idempotent, or only the enqueue/send API?
7. What proves completion, and can its acknowledgement be lost?
8. What is the observable exhausted, expired, canceled, or dead-letter outcome?

At-least-once delivery implies possible duplicates. At-most-once delivery implies possible loss.
Use `effectively-once` only when a named scope, stable identity, durable or otherwise sufficient
deduplication state, and conflict policy are proven. Use `exactly-once` only when every boundary
through the final required effect is proven under the stated failure model.

## 6. Capacity, Backpressure, And Overload

Map production rate, service rate, burst tolerance, and every buffer. For each boundary name its
mechanism and semantic outcome:

- demand/admission control;
- bounded queue or concurrency lane;
- coalescing to the latest state;
- deferral with a bounded pending set;
- priority and reserved capacity;
- rejection or shedding;
- safe drop with explicit loss evidence;
- producer slowdown where the source supports it; or
- failure/escalation when the item cannot be lost.

Never recommend an unbounded queue as reliability. A queue capacity alone is incomplete without a
full/closed behavior, observability, recovery policy, and shutdown treatment. Coalescing is valid
only for replaceable state, not distinct immutable facts. Dropping is valid only when the lost
meaning and downstream degradation are explicit.

## 7. Lifecycle, Supervision, And Recovery

Walk these scenarios independently:

- producer starts before consumer; consumer starts before producer; late dynamic consumer;
- duplicate subscription/registration; partial registration; owner restart;
- dependency absent, stale, slow, malformed, unauthorized, or unavailable;
- callback exception, mailbox/queue full, slow consumer, timeout, and retry exhaustion;
- duplicate, conflicting, late, out-of-order, or post-cancellation response;
- provider disconnect/reconnect and desired-versus-observed reconciliation;
- required persistence unavailable before dependent publication;
- clean stop, forced stop, drain timeout, unfinished work, and restart after either; and
- one component repeatedly failing while unrelated components continue.

Supervision policy must define shared fate rather than assume it. Restart intensity, window,
strategy, backoff, and escalation are bounded policy candidates. Restarting without clearing or
reconciling invalid state may repeat corruption faster.

Prefer event-driven handshakes, current-state snapshots, or reconciliation over sleeps and assumed
actor registration order. Restore only compatible, still-valid state; otherwise return honestly to
warming, partial, degraded, unavailable, or another accepted lifecycle state.

## 8. Failure-Injection Evidence

Recommend the smallest deterministic evidence proportional to the risk. Candidate tests include:

- duplicate and conflicting identity;
- loss or missing acknowledgement;
- retry after side effect but before acknowledgement;
- late callback after timeout, cancellation, or shutdown;
- out-of-order and cross-producer interleaving;
- full queue, reserved-capacity exhaustion, slow consumer, and overload recovery;
- startup-order permutations and late snapshot synchronization;
- repeated crash/restart until bounded escalation;
- persistence failure at each side of publish/write ordering; and
- proof that unrelated actors and capabilities continue.

Passing a fixture proves only its modeled failure and transport. Connected provider behavior,
durability, process crashes, performance, and operator-visible recovery require their own evidence.

## 9. Decision Test

Recommend the smallest design that satisfies required meaning and failure tolerance while
preserving accepted ownership and native framework contracts. Compare alternatives by semantic
fit, failure isolation, evidence fidelity, bounded resources, recovery complexity, operability,
and migration effect.

Stop before implementation if the winning option requires an unapproved architecture, ownership,
topology, persistence, provider, schema, infrastructure, dependency, runtime-policy, or
product-semantic change. Present the owning-advisor analysis and decision gate to Markeitect; do
not accept or implement it here.
