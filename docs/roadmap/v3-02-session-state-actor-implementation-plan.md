# V3-02 SessionStateActor Current-State Delivery Implementation Plan

**Status:** Decisions accepted; Slice 1 implemented and uncommitted for Markeitect review; Slices
2 through 5 remain unapproved

**Planning branch:** `v3-02-session-state-snapshot-plan`

**Planning baseline:** `3429531` (`docs(v3): close canonical calendar authority stage`)

**Target:** V3-02 late-consumer current-state delivery only

**Depends on:** V3-01 canonical calendar authority, closed with bounded connected acceptance

## Accepted Decision Record

| Decision | Accepted disposition |
|---|---|
| 1. Consumer cutover | Migrate only the active production consumers: `EvidenceHealthActor` and `HistoricalEvidencePlannerActor`. Disable `SessionMetricsActor`, Visual Debug, and dependent Entity Analysis. Add one test-only current-state historical-demand probe. Keep `OperationalPersistenceActor` as a transition audit sink. |
| 2. Snapshot evaluation | For each admitted request, `SessionStateActor` reads its clock once and evaluates every requested calendar at that one owner-clock cut. |
| 3. Producer identity | Do not add a producer-incarnation ID. One `SessionStateActor` construction is permitted per runtime run UUID; same-run replacement is unsupported. |
| 4. Delivery configuration | Add one lean `[sessions.current_state_delivery]` block, separate from schedule-projection retry configuration. |
| 5. Lifecycle | `SessionStateActor` stop is terminal for that runtime. Late callbacks and messages cannot publish, mutate state, or rearm timers. |
| 6. State time | Retain both the exact canonical boundary at which the current state became effective and the owner-clock time at which that state was evaluated. Never substitute evaluation time for an unknown boundary. |

These decisions supersede the earlier draft's three-consumer migration, producer-incarnation ID,
requester-incarnation ID, and large eleven-setting delivery block.

## Authority And Current Baseline

This plan is subordinate to:

1. [`markeitech.md`](../../markeitech.md);
2. [`docs/current-status.md`](../current-status.md);
3. [`docs/development-guidelines.md`](../development-guidelines.md);
4. [`v3-01-canonical-calendar-authority-review.md`](../notes/v3-01-canonical-calendar-authority-review.md);
5. [`v3-02-session-state-actor-role-review.md`](../notes/v3-02-session-state-actor-role-review.md); and
6. [`system-dataflow-maintenance.md`](../architecture/system-dataflow-maintenance.md).

Verified at the planning baseline:

- `SessionStateActor` is the sole runtime owner of the configured `CanonicalCalendar` objects.
- It retains one current `CanonicalSessionSnapshot` and monotonic revision per calendar.
- It publishes `CalendarTransition` v1 and bounded schedule projections.
- It does not offer a current-state request/response contract.
- `EvidenceHealthActor` and `HistoricalEvidencePlannerActor` can start after the last transition
  and therefore need a bounded way to establish current state before applying later transitions.
- `SessionMetricsActor` is configuration-gated but enabled in both tracked runtime templates. Its
  responsibilities are faulty and separately planned for replacement; it is not an implementation
  or acceptance dependency for V3-02.
- The tracked V3 ES profile also enables `visual_debug_capture`, which requires Session Metrics.
- The ignored machine-local profile currently enables Session Metrics and Entity Analysis. It is
  operator-owned and must be aligned manually before it is used again; it is not edited by this
  batch.
- Composition constructs exactly one `SessionStateActor` per runtime run and has no controller or
  same-run actor-replacement path.
- The runtime run UUID already separates revision sequences across normal process restarts.
- `HistoricalWindowResolver` already aligns `recent_completed` requests to the selector interval;
  V3-02 adds regression evidence but does not change historical-window meaning.

The connected V3-01 run remains prior calendar-authority evidence. It is not V3-02 snapshot,
late-consumer, or recovery acceptance.

## Purpose And Completion Claim

V3-02 answers one question:

> How does an active in-process consumer which starts late or becomes temporarily unsynchronized
> establish the complete current state of its configured calendars, reconcile transitions which
> race with that snapshot, and resume live consumption without guessing or creating another
> calendar authority?

V3-02 may be marked implemented only when:

- Session Metrics, Visual Debug, and Session-Metrics-dependent Entity Analysis are absent from the
  active tracked profiles;
- `SessionStateActor` answers bounded current-state requests with complete per-calendar outcomes;
- `EvidenceHealthActor` and `HistoricalEvidencePlannerActor` subscribe before requesting, buffer
  within explicit limits, and install only gap-free reconciled state;
- a test-only actor proves the current-state-to-historical-plan path without becoming runtime
  architecture;
- duplicate, stale, gap, conflict, overflow, timeout, definition, and stop behavior is explicit;
- state-effective time and evaluated-as-of time remain distinct;
- the schedule-projection and historical-planning contracts remain semantically unchanged;
- offline verification passes and architecture/status documents agree; and
- any connected timing acceptance remains pending until separately authorized.

The accepted claim is limited to one statically composed `SessionStateActor` within one runtime
run UUID. It does not claim hot replacement, durable replay, exactly-once delivery, global event
ordering, provider-session correctness, or downstream analytical fitness.

## Scope

### In scope

- disable `SessionMetricsActor` in both tracked runtime profiles;
- disable the V3 ES Visual Debug profile and preserve its existing artifacts as historical only;
- preserve the loader's fail-closed rule that Entity Analysis cannot run without Session Metrics;
- typed current-state request, current-state item, failure, and response contracts;
- one owner-clock cut per admitted request;
- exact canonical state-effective boundary plus evaluated-as-of time;
- one pure bounded subscribe-buffer-snapshot-reconcile state machine;
- bounded retry, deadline, transition buffering, duplicate absorption, gap detection, and stop;
- production adoption by `EvidenceHealthActor` and `HistoricalEvidencePlannerActor` only;
- one test-only actor which synchronizes current state, publishes a symbolic historical demand,
  and observes the real planner's exact output;
- a lean, typed, versioned current-state-delivery configuration block;
- unchanged transition auditing by `OperationalPersistenceActor`;
- focused unit, actor, composition, lifecycle, and disconnected integration evidence; and
- the smallest authoritative documentation and architecture-manifest update.

### Explicitly out of scope

- implementing, fixing, splitting, deleting, or reactivating `SessionMetricsActor`;
- completed bars, metrics, Visual Debug output, Entity Analysis, semantic events, opportunities,
  recommendations, Sir Loke, or execution;
- changing calendar definitions, corrections, phases, mcal evaluation, Watchlist membership, or
  the accepted V3-01 calendar authority;
- changing symbolic historical-demand meaning, historical-window resolution, provider request
  semantics, pacing, retries, limits, or acquisition ownership;
- a new provider call, connected IB run, Discord action, database action, or paid/external action;
- a PostgreSQL migration or persistence of snapshots, watermarks, buffers, retry state, or raw
  schedules;
- same-run actor replacement, controller support, failover, actor save/load, or producer
  incarnation identity;
- new threads, workers, executors, queues, processes, dependencies, lockfiles, or containers;
- replay, backtesting, ML, order routing, recommendation, or execution authority; and
- editing the ignored `v2/config/system.local.toml`.

## Runtime Topology After Deactivation

The V3 ES active path becomes:

```text
SessionStateActor
    |-- current-state snapshot + CalendarTransition --> EvidenceHealthActor
    |-- current-state snapshot + CalendarTransition --> HistoricalEvidencePlannerActor
    `-- CalendarTransition ---------------------------> OperationalPersistenceActor

HistoricalEvidencePlannerActor
    `-- exact HistoricalRequestPlan ------------------> DataAcquisitionActor

Test only:
CurrentStateHistoricalDemandProbeActor
    |-- uses the production current-state reconciler
    |-- publishes one symbolic HistoricalDependencyDemand
    `-- observes the real HistoricalRequestPlan

Disabled:
SessionMetricsActor -> VisualDebugCaptureActor -> visual artifacts
SessionMetricsActor -> Session-Metrics-dependent Entity Analysis
```

`OperationalPersistenceActor` remains a transition audit sink. It does not subscribe to current-
state requests or responses and does not persist synchronization state.

## Ownership And Contract Separation

| Concern | Canonical owner | Consumer responsibility | Durability |
|---|---|---|---|
| Current calendar state | `SessionStateActor` | Install only reconciled immutable state | Transient |
| Calendar transition | `SessionStateActor` | Reconcile by run/calendar/revision identity | Existing operational audit |
| Current-state snapshot | `SessionStateActor` | Correlate, validate, install watermark, reconcile buffer | Transient |
| Historical schedule projection | `SessionStateActor` and `CanonicalCalendar` | Retain bounded immutable schedule view | Transient |
| Exact historical plan | `HistoricalEvidencePlannerActor` | Requester declares need; acquisition executes plan | Existing operational audit only |
| Consumer synchronization state | Each active consumer through one shared pure helper | Bound attempts, time, buffers, and recovery | Transient |
| Delivery policy | Typed startup configuration | Enforce without hidden tunable defaults | Configuration only |

The requesting actor never creates provider timestamps. It declares a symbolic evidence need.
`HistoricalEvidencePlannerActor` alone aligns that need to the approved selector interval,
completion boundary, and canonical schedule before `DataAcquisitionActor` executes it.

## Contract Model

### Type identities

Use distinct typed custom-data contracts:

```text
markeitech.calendar.transition.v2
markeitech.calendar.state.snapshot.request.v1
markeitech.calendar.state.snapshot.response.v1
```

Transition v2 is required only to make state-effective and evaluated-as-of semantics explicit and
consistent with snapshot state. It does not add an incarnation identity.

The canonical revision key remains:

```text
(source, source_epoch, calendar_id, revision)
```

where `source_epoch` is the runtime run UUID. Event identity remains collision-safe under the
accepted one-producer-per-run rule:

```text
calendar:<source_epoch>:<calendar_id>:<revision>
```

There is no dual-canonical transition-v1/v2 publication period.

### CalendarTransition v2

Retain the accepted calendar state and previous-state fields while clarifying time names:

- `definition_effective_from_ns`: when the selected calendar definition became authoritative;
- `state_effective_from_ns`: exact canonical boundary which produced the current state revision;
- `evaluated_as_of_ns`: one owner-clock evaluation cut at which the state was verified;
- `published_ts_ns`: event publication time; and
- `revision` plus `previous_revision`.

Required ordering is:

```text
definition_effective_from_ns <= state_effective_from_ns <= evaluated_as_of_ns <= published_ts_ns
```

`state_effective_from_ns` must come from admitted canonical exchange/phase boundaries. The actor
must not round `evaluated_as_of_ns`, copy it into the boundary field, or invent a boundary. If the
current evaluator cannot supply an exact boundary for every successful state, implementation
stops for a bounded contract review rather than weakening this rule.

Equal revision identity plus equal canonical content is a duplicate. Equal revision identity plus
unequal content is a hard conflict. `schedule_version` remains descriptive; definition digest and
revision identity govern reconciliation.

Operational persistence accepts transition v2 mechanically without a new table or durability
category.

### Snapshot request

`CalendarStateSnapshotRequest` contains:

| Field | Meaning |
|---|---|
| `cycle_id` | Stable identity for one synchronization cycle |
| `request_id` | Unique identity for this attempt |
| `attempt` | Positive attempt number within the configured maximum |
| `requester` | Exact allowed actor ID |
| `expected_source` | `SESSION-STATE` |
| `expected_source_epoch` | Current runtime run UUID |
| `calendar_expectations` | Bounded exact calendar definition identities |
| `requested_as_of_ns` | Earliest acceptable current evaluation; not a historical query |
| `requested_ts_ns` | Attempt creation/publication time |
| `deadline_ts_ns` | Absolute attempt deadline on the same runtime clock |
| `delivery_policy_version` | Exact startup policy version |
| `schema_version` | Strict schema v1 |

Invariants include:

```text
requested_as_of_ns <= requested_ts_ns < deadline_ts_ns
```

Retries keep `cycle_id`, increment `attempt`, and use a new `request_id`. Unknown requesters,
unknown calendars, mismatched definitions, expired attempts, duplicate identity with unequal
content, and over-population fail closed with typed complete outcomes.

### Current-state item

Each successful `CalendarCurrentState` contains:

- calendar, schedule, and exact definition identity;
- trade date, ordered phase memberships, and `OPEN`, `BREAK`, or `CLOSED` state;
- segment bounds and next transition when known;
- positive revision and exact previous revision;
- last transition event ID;
- source and runtime run UUID;
- exact `state_effective_from_ns`;
- common snapshot `evaluated_as_of_ns`; and
- state publication time.

All successful items in one response share the same `evaluated_as_of_ns`. The state-effective
boundary is not used as snapshot freshness, and evaluation time is never used as a candle or
historical-request boundary.

### Failure and response

Each requested calendar receives exactly one success or failure. Minimum stable failure codes are:

- `source_not_ready`;
- `unknown_calendar_id`;
- `definition_identity_conflict`;
- `state_effective_boundary_unavailable`;
- `current_state_evaluation_failed`;
- `request_population_exceeded`;
- `request_deadline_expired`;
- `request_identity_conflict`;
- `requester_not_allowed`; and
- `producer_inactive` where a response can still be safely emitted before stop completes.

The response contains cycle/request/attempt/requester identity, source and run UUID, requested
calendar population, successful states, failures, request/evaluation/publication timestamps,
policy version, derived status, and an optional retry time.

Complete accounting requires:

```text
set(success.calendar_id) union set(failure.calendar_id)
    == set(requested_calendar_ids)
```

with no duplicate, intersecting, or unrequested calendar IDs. Silence is never a valid response.

## Producer Design

### One owner-clock cut

For one admitted request, `SessionStateActor`:

1. reads `cut_ns` once;
2. evaluates every requested calendar at that same instant;
3. derives the exact state-effective boundary from canonical schedule facts;
4. publishes a transition v2 through the normal owner path only if meaningful state changed;
5. freezes each resulting state and revision;
6. returns one success or failure for every requested calendar; and
7. publishes the response only if still active.

The response may be observed before or after its corresponding transition. Consumers reconcile by
revision, not callback order. Periodic evaluation and request evaluation reuse one state-update
primitive so there is only one revision path.

### Bounded admission and duplicates

Composition supplies the exact allowed production requester IDs:

```text
EVIDENCE-HEALTH
HISTORICAL-EVIDENCE-PLANNER
```

Tests construct a separate producer configuration which also allows the test probe. The producer
keeps at most one active cycle per allowed requester and at most `maximum_attempts` immutable
responses for that cycle. Capacity is therefore derived from the allowed requester population and
attempt bound; no speculative requester/cache/rate-limit knobs are added.

Equal attempt identity and content replays the cached immutable response. Unequal content under
the same identity conflicts. A new cycle cannot silently displace an active unexpired cycle.
Terminal or expired cycle state is removed deterministically.

### Lifecycle

`on_start` marks the producer active, subscribes to projection and snapshot requests, completes the
existing persistence-ready handshake, and activates periodic evaluation. Before activation,
valid requests receive `NOT_READY` with bounded retry information.

`on_stop` first marks the producer inactive, then unsubscribes, cancels only owned timers/alerts,
clears transient request state, and reports bounded counters. Every request, callback, evaluation,
publication, and timer-rearm path checks the active flag. Late work is absorbed without mutation
or publication. The same actor object is never restarted.

## Consumer Reconciliation

Add a pure framework-independent module:

```text
v2/src/markeitech/intelligence/session_state_delivery.py
```

It owns synchronization state only. It does not evaluate calendars, calculate evidence, resolve
historical windows, execute requests, persist state, or own actor lifecycle.

Minimum phases are `IDLE`, `WAITING`, `BACKOFF`, `LIVE`, `DEGRADED`, `CONFLICT`, and `STOPPED`.

Each consumer:

1. subscribes to transition v2 and snapshot responses;
2. starts bounded transition buffering before publishing its first request;
3. publishes one cycle/attempt request;
4. buffers matching transitions while waiting;
5. accepts only an exactly correlated and completely accounted response;
6. installs snapshot states as revision watermarks;
7. sorts and reconciles buffered transitions per calendar;
8. enters `LIVE` only after every required calendar is gap-free;
9. schedules the earliest next-boundary watchdog plus delivery grace; and
10. degrades/resynchronizes only the affected calendar where possible.

Rules:

- a revision below the installed watermark is stale;
- equal revision and equal content is a duplicate;
- equal revision and unequal content is a conflict;
- `revision == watermark + 1` applies only when `previous_revision == watermark`;
- out-of-order transitions may converge only when the complete contiguous sequence is present;
- a forward gap, definition mismatch, wrong source/run UUID, or buffer overflow prevents current-
  state use across the affected gap;
- overflow is explicit and starts a bounded resynchronization cycle; and
- `STOPPED` absorbs late responses, transitions, retries, and watchdog alerts.

Delivery is at-least-observable and idempotently reconciled; it is not claimed exactly once.

## Production Consumer Changes

### EvidenceHealthActor

- Replace schedule-projection-as-current-context bootstrap with current-state synchronization.
- Preserve projections only where timestamp coverage is still required.
- Install `_session_by_calendar` only from reconciled state.
- Preserve honest `NOT_EVALUATED` behavior while a calendar is unsynchronized.
- Reevaluate only affected evidence streams after a newly installed revision or recovery.
- Do not change thresholds, recency learning, provider status, health vocabulary, subscriptions, or
  readiness meaning.

### HistoricalEvidencePlannerActor

- Retain schedule projections, symbolic-demand resolution, exact UTC plan generation, deferral,
  retry, and acquisition interaction unchanged.
- Add the current-state synchronization lane.
- Route transition-triggered projection refresh and deferred-demand wakeup through newly installed
  revisions only.
- Keep still-valid projection-only planning available while an unrelated current-state calendar
  is degraded.
- Deduplicate effects by stable demand ID across recovery.

Historical request alignment remains planner-owned. For a `recent_completed` one-minute demand at
`13:36:00.650`, the resolver's existing contract produces the logical half-open interval
`[13:31:00.000, 13:36:00.000)`, encoded by the current inclusive end field as
`13:35:59.999999999`. Neither snapshot evaluation time nor a requesting actor creates those
bounds.

### OperationalPersistenceActor

- Continue recording transition v2 as an operational fact.
- Do not subscribe to or persist snapshot requests, responses, buffers, watermarks, retries, or
  current-state cache entries.
- Add no migration, table, or durability category.

### Disabled Session Metrics surface

- Set `metrics.session_measurements.enabled = false` in both tracked profiles.
- Set `visual_debug_capture.enabled = false` in the V3 ES profile.
- Keep Entity Analysis disabled in both tracked profiles.
- Preserve the loader guards which reject Visual Debug or Entity Analysis when Session Metrics is
  disabled.
- Do not delete actor source, calculation modules, fixtures, or focused unit tests.
- Convert tests which require Session Metrics into explicit test-local enabled configurations;
  active-profile tests must prove it is absent.
- Do not edit the ignored machine-local profile. Record that an operator must disable both Session
  Metrics and Entity Analysis there before launching it.

### Test-only current-state historical-demand probe

Add `CurrentStateHistoricalDemandProbeActor` under
`v2/tests/system/message_actor_fixtures.py`. It never appears in production source, composition,
tracked runtime profiles, or the architecture manifest as a runtime component.

The probe:

1. uses the production synchronization helper;
2. establishes reconciled current state;
3. publishes one stable symbolic `HistoricalDependencyDemandEvent`;
4. observes the real planner's `HistoricalRequestPlan` for its consumer/demand identity; and
5. exposes deterministic success/failure state to the test harness.

It proves producer-before-consumer, consumer-before-producer, transition-before-response,
transition-after-response, duplicate, stale, gap, conflict, timeout, overflow, recovery, plan
deduplication, and terminal-stop cases. It does not substitute for production adoption by Evidence
Health and Historical Planner.

## Configuration

Add this separate lean block to both tracked profiles:

```toml
[sessions.current_state_delivery]
policy_version = 1
response_timeout_ms = 5000
maximum_attempts = 3
retry_backoff_ms = 1000
maximum_elapsed_ms = 60000
maximum_buffered_transitions_per_calendar = 8
maximum_total_buffered_transitions = 32
boundary_delivery_grace_ms = 2000
```

The values are initial bounded implementation defaults, not performance-calibrated market or
provider facts. Focused deterministic tests must establish their arithmetic and safety envelopes;
Markeitect reviews any adjustment in the implementation diff.

Reuse the existing `sessions.maximum_calendars_per_request` bound. Derive producer response-cache
capacity from allowed requester count times maximum attempts. Do not add `minimum_request_interval`,
`maximum_tracked_requesters`, or `maximum_cached_responses` settings in V3-02.

Strict validation includes positive values, maximum attempts inside a small explicit envelope,
elapsed time covering at least one response timeout, total buffer capacity not below the per-
calendar bound, and no unknown or partial block. Advance the system configuration schema exactly
once and update both tracked profiles atomically.

## Implementation Slices

Each slice remains uncommitted until Markeitect reviews it. Stop when a slice exposes a semantic or
authority change outside this plan.

### Slice 1: Deactivate the faulty surface

**Implementation status:** Complete for local review on the planning branch; uncommitted

Files:

- `v2/config/system.example.toml`;
- `v2/config/system.v3-es-minimal.toml`;
- `v2/tests/system/test_config.py`;
- `v2/tests/system/test_composition.py`;
- `v2/tests/system/test_v3_es_minimal_config.py`;
- `v2/tests/system/test_message_delivery.py`; and
- `v2/tests/intelligence/test_session_metric_capture_alignment.py`.

Deliver:

- Session Metrics and Visual Debug absent from active tracked plans;
- dependent Entity Analysis remains disabled;
- explicit test-local enabling where dormant actor behavior is still tested;
- Historical Planner remains active but receives no Session Metrics demands; and
- no actor deletion, provider action, or local-profile edit.

### Slice 2: Contracts and pure synchronization

Files:

- `v2/src/markeitech/intelligence/calendar_messages.py`;
- new `v2/src/markeitech/intelligence/session_state_delivery.py`;
- `v2/src/markeitech/intelligence/__init__.py` only if an existing internal import surface requires
  it;
- `v2/tests/intelligence/test_calendar_messages.py`; and
- new `v2/tests/intelligence/test_session_state_delivery.py`.

Deliver:

- transition v2 without incarnation identity;
- snapshot request/current-state/failure/response v1;
- exact state-effective and evaluated-as-of semantics;
- pure duplicate/stale/gap/conflict/overflow/retry/stop transitions; and
- no actor or domain behavior change.

Do not add the new contracts to the intentional public API registry unless a separately reviewed
public-surface change is required.

### Slice 3: Producer, lifecycle, and lean configuration

Files:

- `v2/src/markeitech/intelligence/actors.py`;
- `v2/src/markeitech/system/config.py`;
- `v2/src/markeitech/system/composition.py`;
- `v2/src/markeitech/system/persistence.py` only for transition-v2 mapping;
- both tracked system TOMLs; and
- focused config, composition, actor, persistence, and node tests.

Deliver:

- one-cut evaluation;
- exact state boundary retention;
- complete response accounting;
- allowed-requester admission and bounded duplicate cache;
- active/inactive lifecycle fence and terminal stop;
- the lean configuration block and one schema advance; and
- no same-run replacement identity or behavior.

### Slice 4: Active consumers and end-to-end fixture

Files:

- `v2/src/markeitech/intelligence/actors.py` for Evidence Health;
- `v2/src/markeitech/system/historical_planner.py`;
- `v2/tests/system/message_actor_fixtures.py`;
- `v2/tests/system/test_message_delivery.py`;
- existing evidence-health and historical-planner regression tests; and
- `v2/tests/acquisition/test_historical_windows.py` for the subsecond alignment regression.

Deliver:

- both active production consumers on one synchronization protocol;
- test-only current-state-to-historical-plan coverage;
- the `13:36:00.650` to five completed one-minute bars alignment assertion;
- no duplicate plan effect after duplicate/recovery inputs; and
- no `SessionMetricsActor` production edit.

### Slice 5: Architecture and closure

Files:

- `docs/architecture/system-dataflow.toml`;
- generated system/data-flow artifacts through the approved generator;
- `docs/current-status.md`;
- `docs/notes/v3-02-session-state-actor-role-review.md`;
- `docs/notes/v3-03-session-metrics-actor-split-review.md`;
- `docs/notes/v3-visual-debug-review-contract.md` and handoff only to mark the mission disabled;
- `docs/roadmap/implementation-history.md` when closure is reviewed; and
- this plan for exact closure evidence.

Deliver:

- active/disabled profile states and snapshot/transition edges agree with composition;
- historical Session Metrics and Visual Debug evidence remains documented without claiming current
  enablement;
- V3-02 is marked implemented only after production consumers and fixture pass; and
- connected timing debt remains explicit.

## Acceptance Matrix

### Contract and producer

- strict immutable schemas and type names;
- one common `evaluated_as_of_ns` across successful states in a response;
- exact canonical `state_effective_from_ns` distinct from evaluation/publication time;
- monotonic revision identity by source/run/calendar;
- complete requested-calendar accounting for success, incomplete, not-ready, rejected, and failed;
- one meaningful transition per changed revision and none for unchanged state;
- bounded duplicate replay and identity conflict;
- unknown requester rejection;
- no response, transition, mutation, or timer rearm after stop; and
- no same-run actor reconstruction support.

### Reconciliation

- consumer-before-producer and producer-before-consumer startup;
- response before/after matching transitions;
- duplicate response and transition absorption;
- stale transition rejection;
- out-of-order contiguous convergence;
- forward-gap, definition-conflict, wrong-run, timeout, and overflow degradation;
- bounded retry and recovery without duplicate domain effect;
- independent per-calendar degradation; and
- stop absorbs all late inputs.

### Consumer and historical path

- Evidence Health never infers a current phase from silence;
- Evidence Health domain thresholds and vocabulary remain unchanged;
- Historical Planner preserves projection and symbolic-demand semantics;
- repeated synchronization does not duplicate a historical plan;
- a subsecond `as_of_ns` is aligned by the planner/resolver, never used raw as a bar boundary;
- the test probe reaches the real planner but never enters production composition; and
- Operational Persistence records only transition audit facts.

### Deactivation and scope

- active tracked plans contain no Session Metrics, Visual Debug, or Entity Analysis actors;
- dormant Session Metrics unit tests remain available through explicit test configuration;
- no new completed-bar, metric, entity, visualization, provider, database, dependency, or external
  behavior;
- ignored local configuration is untouched;
- documentation and architecture manifest match runtime composition; and
- no generated, local, licensed, secret, log, or market-data artifact enters the diff.

## Verification Sequence

Run disconnected verification only:

1. focused contract and pure reconciliation tests;
2. config and composition tests for both tracked profiles;
3. `SessionStateActor` lifecycle and one-cut tests;
4. Evidence Health and Historical Planner regression tests;
5. test-only current-state-to-plan integration tests;
6. historical-window subsecond-alignment regression;
7. persistence mapping tests;
8. full non-PostgreSQL V2 test suite;
9. Ruff or the repository's approved lint target;
10. system/data-flow drift check through the first-party generator;
11. API-doc validation only if the implementation changes an intentional documented/public surface;
12. `git diff --check`; and
13. final status/diff inspection for unrelated or prohibited files.

Passing offline tests do not establish connected timing, provider behavior, PostgreSQL availability,
or market-session correctness.

## Connected Acceptance Gate

No connected run is required to implement the contracts. If Markeitect later authorizes a bounded
connected acceptance, it should establish only:

- the two active consumers recover independently of actor startup order;
- state-effective and evaluated-as-of times reconcile with the canonical calendar log;
- one scheduled boundary produces one revision and one persisted transition;
- no duplicate historical plan appears through synchronization recovery;
- retry and buffer counts remain within configured limits; and
- shutdown produces no post-stop publication or provider work caused by V3-02.

It must not enable Session Metrics, Visual Debug, Entity Analysis, or any connected path merely to
manufacture evidence for this stage.

## Risks And Stop Gates

- **Exact state boundary unavailable:** stop rather than copy evaluation time or broaden calendar
  semantics without review.
- **Same-run producer replacement appears necessary:** stop; V3-02 deliberately has no incarnation
  identity or replacement protocol.
- **Consumer semantic drift:** stop if synchronization changes evidence-health policy or historical-
  planning meaning rather than delivery timing only.
- **Planner alignment defect:** if the new regression reveals behavior inconsistent with the
  accepted `recent_completed` contract, record a separate defect; do not redesign planning inside
  V3-02.
- **Capacity evidence contradicts defaults:** revise the lean block with measured or deterministic
  evidence before continuing; do not add speculative knobs.
- **Persistence expansion:** stop if snapshot correctness appears to require durable snapshot or
  buffer state.
- **Provider or external effect:** stop before any new request, subscription, quota, database, or
  connected action.
- **Dual transition authority:** stop if transition v1 and v2 can both appear canonical.

## Completion Checklist

- [x] Markeitect resolved Decisions 1 through 6.
- [x] V3-01 is closed and the planning branch is based on its accepted commit.
- [x] Session Metrics, Visual Debug, and dependent Entity Analysis are disabled in tracked profiles.
- [ ] Transition v2 and snapshot v1 contracts are strict and immutable.
- [ ] No producer-incarnation or requester-incarnation identity is added.
- [ ] Producer uses one owner-clock cut and retains exact state-effective plus evaluated-as-of time.
- [ ] Pure synchronization state is bounded and framework-independent.
- [ ] Evidence Health and Historical Planner adopt it.
- [ ] The test-only current-state historical-demand probe passes without production composition.
- [ ] Historical schedule projection and request-plan semantics remain unchanged.
- [ ] Operational Persistence remains transition-only; no snapshot durability is added.
- [ ] Configuration schema and both tracked profiles migrate atomically.
- [ ] Alternate-order, late-consumer, gap, conflict, overflow, timeout, failure-isolation, and stop
      evidence passes.
- [ ] Full disconnected suite, lint, diagram drift, and `git diff --check` pass.
- [ ] Final diff contains no unrelated files, secrets, data, logs, local configuration, dependency,
      lockfile, provider, database, or external-service churn.
- [ ] Current status, V3-02 review, V3-03 split review, and visual-debug status agree.
- [ ] Implementation batch remains uncommitted for Markeitect review.
- [ ] Connected acceptance runs only after separate explicit authorization.

## Kite Advisory Basis

The original plan used the smallest sufficient read-only advisor set for Nautilus alignment,
architecture boundaries, event delivery, data quality/lineage, and Python lifecycle. Their current
checkout findings remain useful for typed `CustomData`, actor-owned clocks, bounded reconciliation,
complete accounting, terminal stop, and claim limits.

Markeitect's accepted decisions supersede two earlier advisor recommendations:

- the former three-consumer migration is replaced by two active production consumers plus one
  test-only historical-demand probe because `SessionMetricsActor` is deliberately disabled; and
- the speculative producer-incarnation identity is rejected because current composition permits
  one producer per runtime run UUID and no same-run replacement.

No new advisor consultation was required for this document revision. Advisors remain read-only and
do not approve implementation, architecture, configuration values, connected acceptance, commit,
integration, release, or product/trading decisions. Markeitect retains final authority.
