# Architecture And Implementation

Use this reference for architecture questions, design reviews, implementation plans, and requested code changes after completing the native capability gate.

## Frame The Decision

State the outcome, current stage, system boundary, decision owner, current implementation, proposed target, and excluded work. Identify whether each concern belongs to Nautilus core, an adapter, a provider, Markeitech product semantics, or an external projection.

Investigate locally before asking questions. Ask Markeitect when the unresolved choice changes architecture, dependencies, infrastructure, persistence, schemas, provider ownership, runtime policy, or product meaning.

## Trace The End-To-End Contract

For each flow, make these relationships explicit:

1. **Source and fidelity:** provider, venue, instrument, contract, observation, timestamp, lineage, and known gaps.
2. **Demand and ownership:** requester, subscriber, reconciler, retry owner, release owner, readiness proof, and one provider-facing owner per canonical stream.
3. **Native mechanics:** exact Nautilus types, actor facilities, cache behavior, indicator registration, bus route, request/response, adapter call, or persistence facility.
4. **Product semantics:** any Markeitech-owned definition, evidence health, entity, semantic event, policy, or audit fact added above native mechanics.
5. **State:** identity, revisions, ordering, deduplication, warmup, invalidation, expiry, restart, and bounded retention.
6. **Failure:** isolation, retry, backpressure, late callbacks, degradation, recovery evidence, and shutdown.
7. **Persistence and projection:** durable versus transient data, owner, schema, retention, idempotency, and read-only consumers.

Console, Discord, dashboards, and future agents consume canonical state. They do not calculate or mutate market truth.

## Indicator Architecture

When indicators are involved, separate:

- native numerical primitive and registration lifecycle;
- configured input stream and warmup dependency;
- Markeitech product interpretation or entity;
- semantic transitions and evidence health;
- projection to logs, Discord, UI, or Sir Loke.

Prefer registered native indicators for calculations they own. Extend or compose them when additional deterministic product meaning is required. Never label bar geometry as observed order flow.

## Persistence Architecture

Show the complete persistence topology, even when the decision is to persist nothing. Distinguish cache backing, actor state, raw market-data catalog, operational event history, approved semantic state, and external message projection. Explain why each store exists and why adjacent native facilities were accepted or rejected.

PostgreSQL is not automatically the answer because it already exists. Nautilus persistence is not automatically the answer because it is native. Ownership follows the approved data meaning, recovery requirement, and evidence contract.

## Runtime Semantics

Verify the pinned behavior for actor lifecycle, callback thread affinity, registration order, cache-before-publication, request correlation, historical/live topics, custom data, adapter reconnect, timers, shutdown, and background workers.

Keep synchronous callbacks bounded and non-blocking. Necessary I/O or expensive work belongs behind a bounded worker owned by the responsible actor, with typed and observable results. Do not invent thread-safety or async guarantees from naming.

## Configuration And Resources

Variable thresholds, periods, windows, cadences, selectors, horizons, limits, retention, retries, and resource budgets are typed, bounded, versioned configuration with units, scope, defaults, mutability, source, effective time, and audit behavior.

State cost across instruments, subscriptions, provider pacing, callbacks, history, CPU, memory, queues, persistence, latency, and external quotas. Preserve unrelated capabilities through partial failure.

## Implementation-Ready Output

Include, proportionally to risk:

- completed Nautilus Alignment Matrix;
- decision and rejected alternatives;
- ownership and end-to-end flow;
- exact current-pin imports and APIs;
- proposed modules, types, configuration, and interfaces;
- lifecycle, state transitions, invariants, and failure behavior;
- persistence, migration, resource, and operational effects;
- observability and operator projections;
- focused tests, broader offline regression, and Markeitect-owned connected acceptance;
- documentation updates, staged rollout, rollback boundary, unknowns, and gates.

For implementation, inspect the worktree and nearby tests, explain the batch before editing, preserve user changes, avoid incidental cleanup, run proportional offline verification, inspect the final diff, run `git diff --check`, and leave the batch uncommitted until Markeitect approves it.
