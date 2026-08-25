# Native Capability Gate

Use this gate before custom design or implementation. Its purpose is to prevent accidental reinvention and framework bypass while preserving legitimate Markeitech product semantics.

## 1. Define The Requirement Before The Mechanism

State:

- product meaning and decision consumer;
- required source, instrument, venue, contract, timestamp, and evidence fidelity;
- historical, live, restored, derived, or inferred lineage;
- update cadence, warmup, readiness, invalidation, expiry, and restart semantics;
- resource, provider, persistence, and failure constraints;
- what is deliberately out of scope.

Do not name a custom actor, table, model, or algorithm until the requirement is independent of its implementation.

## 2. Breadth Before Depth

Survey every relevant Nautilus family before searching exact symbols:

- actor and strategy lifecycle;
- clocks, timers, and scheduling;
- message bus pub/sub, request/response, endpoints, signals, and custom data;
- cache, cache database, and state restoration;
- data engine, aggregation, requests, subscriptions, and catalog access;
- native instruments and market-data models;
- indicator catalog, registration, initialization, and update paths;
- live node, engines, adapters, reconnect, and readiness behavior;
- persistence, catalogs, writers, serialization, and external stream backing;
- configuration, identifiers, resources, and observability.

Record candidates even when they appear only partially relevant. Narrow the list only after examining semantics.

## 3. Verify The Installed Contract

For each candidate, verify the installed distribution rather than relying on memory or nightly documentation alone:

- import path and public export;
- constructor and configuration fields;
- methods, callbacks, properties, enums, and exceptions;
- actor or engine ownership;
- update and initialization lifecycle;
- serialization or persistence support;
- local usage and focused tests;
- release-candidate or migration differences.

Compiled symbols may require public stubs, API docs, focused construction probes, or existing tests when introspection is incomplete.

## 4. Separate Adapter Delivery

A core type or method does not prove the Interactive Brokers adapter supplies it. Verify:

- request or subscription path;
- contract resolution and symbology;
- provider pacing and limits;
- historical versus live behavior;
- timestamps, revisions, and missing-data behavior;
- reconnect and unsubscribe behavior;
- connected acceptance evidence when required.

Label untested adapter behavior as provider-documented, inferred, or unknown.

## 5. Indicator Gate

Before writing or retaining a custom indicator calculation, answer:

1. Does the installed native indicator catalog contain the calculation or a composable primitive?
2. Can `DataActor` registration update it from the required quote, trade, or bar stream?
3. What exact input price and update semantics does it use?
4. How is warmup supplied, and what proves `initialized` readiness?
5. Does it support the required reset or session anchoring semantics?
6. What happens with partial history, revised bars, duplicates, missing observations, and restart?
7. Can Markeitech compose or wrap the native indicator while keeping product semantics separate?
8. How will results be compared with the native implementation and an independent reference?

A custom calculation is allowed only when the native facility is absent, adapter-incompatible, semantically mismatched, operationally unsafe, or incapable of preserving an approved product contract. Record the exact reason.

Native examples to inspect when relevant include EMA, ATR, efficiency ratio, swings, VWAP, moving averages, volatility, momentum, and volume indicators. This is a navigation hint, not an exhaustive or fixed indicator list.

## 6. Persistence Gate

Classify the data before choosing storage:

| Data class | Typical meaning | Native facilities to inspect first |
|---|---|---|
| Ephemeral runtime state | Fast current projection | Nautilus cache and bounded histories |
| Restartable actor state | Minimal state needed after restart | actor or strategy save/load and supported cache backing |
| Refetchable raw market data | Provider observations | cache policy, catalog, streaming writer; retain only with approved live need |
| Durable operational fact | What the system attempted or experienced | native event facilities plus approved Markeitech operational audit |
| Approved semantic state | Versioned market meaning consumed later | native serialization where fitting, otherwise Markeitech schema with lineage |
| External projection | Discord, UI, downstream observation | message-bus external backing or project-owned projection; never market truth |

Inspect cache database support, `ParquetDataCatalog`, stream writers, actor state, message-bus backing, and event-store semantics before proposing another store. Do not use cache backing as a complete historical event archive. Do not retain refetchable market data for hypothetical replay, backtesting, ML, or convenience.

For every persisted class, state owner, schema identity, idempotency, ordering, retention, migration, recovery, failure isolation, and why native or Markeitech ownership is correct.

## 7. Decision Order

Use this preference order:

1. native facility directly;
2. native facilities composed;
3. narrow Markeitech wrapper or extension around native mechanics;
4. custom Markeitech implementation with an explicit rejection record.

Valid rejection or extension reasons are:

- absent from the installed version;
- adapter/provider cannot deliver the needed contract;
- documented semantic mismatch;
- ownership, isolation, fidelity, or deterministic testability requires a narrow boundary;
- explicitly approved product semantics are outside Nautilus's responsibility.

Invalid reasons include familiarity, convenience, existing custom code, aesthetic preference, or an assumption that custom code will be easier to optimize.

## 8. Nautilus Alignment Matrix

Use one row per requirement:

| Requirement | Native candidate | Installed-version evidence | Adapter/provider evidence | Semantic fit | Proposed owner | Decision | Rejection or extension rationale | Acceptance evidence |
|---|---|---|---|---|---|---|---|---|

Allowed decisions: `USE_NATIVE`, `COMPOSE_NATIVE`, `WRAP_NATIVE`, `CUSTOM_RECOMMENDED`, `CUSTOM_APPROVED`, `DEFER`, `UNKNOWN`.

Use `CUSTOM_RECOMMENDED` when evidence supports custom ownership but Markeitect has not approved that exact boundary. Use `CUSTOM_APPROVED` only when current repository authority or an explicit Markeitect decision already approves it, and cite that authority. `UNKNOWN` remains a visible gate, not a prompt to guess.
