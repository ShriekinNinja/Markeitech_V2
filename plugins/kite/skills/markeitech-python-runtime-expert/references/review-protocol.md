# Python Runtime Review Protocol

Select only the relevant modes. This is a decision framework, not authority to redesign or edit.

## Common Intake

1. Restate the required behavior, non-goals, side effects, latency/resource sensitivity, and
   acceptance evidence.
2. Identify owners for mutable state, tasks, threads/processes, queues, connections, timers,
   retries, shutdown, and emitted truth.
3. Map execution contexts: actor callback, event-loop task, worker thread, process, synchronous
   caller, and test harness. Mark every crossing.
4. Trace normal and adverse lifecycle paths, including partial construction, repeated calls,
   overload, exception, cancellation, timeout, late result, stop-before-start, and restart.
5. Inspect current code and focused tests before proposing abstractions.

## Concurrency And Asyncio Mode

Check:

- whether work is I/O-bound, Python-CPU-bound, or performed in native code;
- event-loop/thread affinity and thread-safe handoff mechanisms;
- shared state, atomicity assumptions, lock ordering, callback reentrancy, and blocking calls;
- task ownership, strong references, exception observation, structured concurrency, and whether
  sibling cancellation matches the product's partial-failure requirement;
- propagation of `CancelledError`, timeout scope, cleanup in `finally`, and the semantic effect of
  `shield`, eager task execution, or executor shutdown;
- queue admission, backpressure, priority/reserved capacity, completion reporting, and accepted-work
  semantics;
- bounded drain, join, cancellation, abandoned/late completion, idempotent cleanup, and restart.

Do not prescribe `TaskGroup`, `gather`, threads, processes, or executors without matching their
failure and cancellation semantics to the requirement. Related child tasks may benefit from
structured concurrency; unrelated capabilities may require separate supervision so one failure
does not cancel healthy work.

For actor callbacks, require a Nautilus-advisor consultation before asserting framework thread,
lifecycle, callback, or bus guarantees. The Python advisor may still identify generic blocking,
shared-state, cleanup, and exception-observation risks.

## Typing And Package Mode

Check:

- the configured Python target and actual static checker, if any;
- public versus private boundaries, import direction, cycles, side effects at import time, and
  stable package entry points;
- whether dataclasses, protocols, typed dictionaries, generics, or narrower value objects improve a
  real boundary without disguising runtime validation;
- `Any`, casts, ignores, untyped third-party boundaries, covariance/invariance, and optional-state
  modeling;
- serialization/runtime validation separately from static assignability;
- build metadata, source layout, included packages, lockfile consistency, and versioned public
  contracts.

A new checker, plugin, packaging tool, runtime validator, or dependency is an approval-gated
dependency decision. Prefer proving gaps with existing tools first.

## Failure-Isolation And Lifecycle Mode

Build an ownership table with:

`Resource/work | Owner | Starts when | Success signal | Failure signal | Retry owner | Stop rule | Late-result handling | Evidence`

Reject designs that:

- publish success before durable or required work completes;
- allow a worker to redefine canonical or global health;
- let optional output failure stop ingestion or independent capabilities;
- retry forever without bounded resources, observable state, expiry, or an owner;
- swallow exceptions/cancellation, lose accepted work silently, or leave orphaned tasks/threads;
- assume daemon-thread exit is graceful cleanup;
- make stop non-idempotent or allow callbacks to mutate stopped ownership state.

Treat retry count, delays, jitter, concurrency, queue sizes, timeouts, drain policy, retained history,
and failure escalation as typed, bounded, versioned configuration candidates when they may vary.

## Performance And Resource Mode

First form a falsifiable question, such as whether queue wait dominates end-to-end latency or
whether retained Python allocations explain RSS growth. Then choose the narrowest measurement:

- timers/counters and queue-depth histories for lifecycle and workload attribution;
- `cProfile`/`pstats` for Python call cost, with overhead acknowledged;
- `tracemalloc` snapshot differences for traced Python allocations;
- process/OS metrics for RSS, CPU, threads, descriptors, page faults, and host pressure;
- native-aware tooling only when approved and required to distinguish extension work.

Require comparable before/after runs and correctness checks. Optimization must not weaken evidence
fidelity, determinism, isolation, or shutdown. Avoid caching, batching, pooling, slots, alternative
interpreters, free-threaded builds, or native rewrites until a measured bottleneck and owner exist.

## Code Review Mode

Review defect-first and continue beyond the first issue. Prioritize correctness, lost work, deadlock,
event-loop blocking, orphaned work, state races, shutdown/restart faults, unbounded growth, exception
loss, type-boundary unsoundness, then maintainability and optimization. Each finding needs:

`Severity | Claim label | File/line | Trigger | Consequence | Evidence | Smallest safe correction | Verification`

Do not report style preferences as defects. If a suspected issue depends on undocumented
NautilusTrader behavior, classify it as unknown and route it instead of asserting a defect.

## Completion Check

- Required behavior and owner are explicit.
- Normal, failure, overload, cancellation, stop, late-result, and restart paths are accounted for.
- Variable controls are bounded policy candidates with units and scopes.
- Findings distinguish local proof, measurement, inference, hypothesis, recommendation, and unknown.
- Offline verification is proportional to risk and its limits are stated.
- Cross-advisor, approval, connected-run, persistence, resource, migration, and operational effects
  are explicit.
