# V3 SessionMetricsActor Split Review

**Status:** Split remains a proposal; `SessionMetricsActor`, Session-Metrics-dependent Entity
Analysis, and Visual Debug are disabled and ignored in tracked runtime profiles pending this work

**Review order:** 3 of 4

**Dependencies:** The V3-01 canonical calendar authority, V3-02 late-consumer current-state
delivery, narrowed `SessionStateActor` ownership, and historical planner/acquisition boundary are
implemented and bounded connected-accepted. Canonical completed-bar and metric subject identity
still require approval before multiple analytical producers become canonical.

## Purpose

Replace the current overloaded `SessionMetricsActor` responsibility with a small set of explicit,
independently configurable analytical owners while preserving one canonical completed-bar stream,
existing evidence lineage, provider-demand ownership, and partial-failure isolation.

This is a reuse-first split. It does not discard the accepted pure calculation modules, bar
admission ledger, historical/live convergence, metric registry, or existing tests. It reorganizes
ownership around the state machines which already exist.

## Implemented Prerequisites

`SessionMetricsActor` no longer constructs or receives a calendar evaluator. It consumes immutable
definition-identified projections from `SessionStateActor`, classifies each completed bar at
`interval_end_ns - 1`, and refreshes projections when a typed calendar transition arrives. There
is no local fallback calendar.

V3-02 adds the bounded current-state snapshot and subscribe-buffer-snapshot-reconcile protocol
needed by independently starting consumers. `EvidenceHealthActor` and
`HistoricalEvidencePlannerActor` use it now. It is an available delivery prerequisite for future
split owners, not authorization to reactivate or migrate the faulty combined actor.

Analytical actors still declare symbolic historical evidence needs. The new
`HistoricalEvidencePlannerActor` alone resolves those needs through canonical projections and
publishes exact UTC plans. `DataAcquisitionActor` no longer interprets sessions or windows; it
enforces concrete provider resource limits and owns queueing, pacing, retries, cancellation,
execution, and lifecycle. This prerequisite does not split any of the metric responsibilities
listed below.

## Current Verified State

`SessionMetricsActor` is not part of either tracked active actor plan. Its dependent Entity
Analysis and Visual Debug surfaces are also disabled. The existing class, pure calculations, and
tests are retained as recovery and migration evidence; their presence does not make the actor a
current producer or an accepted analytical authority.

The dormant `SessionMetricsActor` implementation combines all of these responsibilities in one
actor and one configuration object:

- live analytical feed demand;
- historical dependency demand;
- native consumer attachment and retry;
- immutable canonical calendar projection consumption and refresh;
- provider-bar timestamp interpretation;
- smaller-to-larger bar aggregation;
- historical/live convergence;
- completed-bar duplicate and conflict admission;
- canonical `CompletedBarInput` publication;
- completed-bar OHLCV, compatible-predecessor return, and true-range metrics;
- active-session, previous-session, overnight, and gap measurements;
- analytical-window measurements such as opening range and power hour;
- rolling range, realized return magnitude, ATR, efficiency, coverage, and expansion baselines;
- derived five- and fifteen-minute completed bars;
- session state, evidence state, historical readiness, and acquisition lifecycle observation;
- demand, evidence, and deferred-window retry timers; and
- one combined shutdown summary and failure counter set.

Its completed-bar foundation is singular:

- one live selector;
- one historical selector;
- one historical window;
- one calculation interval;
- one timestamp policy; and
- one retained-observation limit.

The current runtime therefore cannot configure a second independent canonical completed-bar
foundation alongside the first, even though Nautilus `BarType` and historical demand contracts can
represent other timeframes.

## Why The Split Cannot Be First

Splitting the actor before correcting its inputs would multiply existing ambiguity.

The following must be settled first:

1. one canonical calendar-definition identity and session/phase projection;
2. exact completed-bar series and writer identity;
3. complete metric subject identity across timeframes, profiles, windows, and configuration
   epochs;
4. one authoritative producer per canonical output identity;
5. late-consumer snapshot or bounded recovery semantics for independently starting analytical
   owners; and
6. safe historical planning and acquisition boundaries.

Without those controls, two new actors could publish the same metric ID for different timeframes
or classify the same bar under different session definitions without a detectable conflict.

V3-01 and V3-02 close prerequisites 1, 5, and 6 for the accepted one-producer-per-run topology.
Completed-bar series identity, complete metric subject identity, and canonical producer uniqueness
across the proposed split remain unresolved gates. No owner below is approved for implementation
merely because session-state delivery is now available.

## Proposed Logical Owners

### 1. Completed-bar foundation owner

This is the only canonical writer of normalized `CompletedBarInput` observations for each exact
completed-bar series identity.

It owns:

- normalized candidate creation from accepted native and historical bars;
- exact bar-series identity;
- interval start/end and timestamp interpretation policy;
- completion policy;
- aggregation until a separately accepted native composite path replaces it;
- historical/live overlap and convergence;
- duplicate, conflict, revision, and correction admission policy;
- one bounded canonical ledger per exact series;
- canonical completed-bar publication;
- bounded source-scoped snapshots or watermarks for late/restarting consumers;
- explicit gap and partial-coverage evidence; and
- completed-bar producer health and failure isolation.

It must not own:

- session references;
- analytical-window definitions or values;
- rolling contexts;
- market-state classification;
- semantic interpretation;
- provider pacing or request execution;
- Watchlist membership; or
- agent-facing intelligence snapshots.

### 2. Completed-bar numerical metrics owner

This owner consumes canonical completed bars and publishes direct numerical measurements.

It owns:

- open, high, low, close, and supported volume projections where useful as metric values;
- compatible-predecessor simple or log return according to the exact accepted definition;
- true range using explicit predecessor lineage;
- direct signed displacement or other approved immediate bar measurements;
- formula, unit, warmup, missing-reason, parameter, and output-age policy; and
- per-series bounded predecessor state.

It must not admit, aggregate, revise, or rewrite canonical bars.

Separating this owner from bar admission keeps canonical observation truth distinct from derived
numerical evidence. If later measurement shows that one physical actor is required for runtime
cost, the two logical responsibilities must still retain separate contracts and producer
identities.

### 3. Session-reference metrics owner

This owner consumes canonical completed bars plus authoritative canonical session projections.

It owns:

- active-session open, high, low, close, range, and supported-volume measurements;
- previous-session references;
- optional overnight references;
- opening or indicative gap measurements;
- session-specific coverage, missing, health, and fidelity semantics;
- reference-specific historical dependency declarations; and
- bounded session-reference state.

It must not:

- independently instantiate or evaluate mcal;
- publish canonical completed bars;
- define arbitrary analytical windows;
- calculate rolling contexts; or
- execute historical requests.

### 4. Analytical-window metrics owner

This owner consumes canonical completed bars plus canonical temporal anchors.

It owns zero or more independently named, versioned analytical windows, including:

- opening ranges;
- power-hour or close-relative windows;
- London or New York analytical windows;
- phase-spanning windows;
- eventually approved cross-calendar windows;
- developing versus complete lifecycle;
- window-specific coverage, volume support, health, and fidelity;
- window-specific historical dependency declarations; and
- bounded per-window state and revision.

Analytical windows remain independent from product phases. The session authority supplies
temporal anchor facts; this owner decides which analytical windows exist and what they calculate.

### 5. Rolling-measurements owner

This owner consumes canonical completed bars by exact series identity.

It owns:

- any number of independently configured rolling families;
- explicit input bar specification/timeframe per family;
- candidate durations or observation counts;
- update cadence and alignment;
- range and return-based numerical measurements;
- ATR and efficiency calculations under explicit formula versions;
- coverage requirements;
- recent and phase-matched comparison baselines;
- parameter bounds, mutability metadata, and dynamic eligibility;
- bounded per-family retained state; and
- rolling producer health and revision.

It must not inherit one global selector or one global calculation interval from a generic session
metrics configuration.

Rolling numerical evidence remains measurement. It does not become trend, regime, compression,
signal, opportunity, recommendation, or order meaning by being moved to a separate owner.

## Shared Contracts Without Shared Authority

### Global metric definition and producer manifest

The current actor's one local `MetricRegistry` prevents duplicate definitions inside that actor.
After the split, composition must validate a global producer manifest.

The manifest should fail closed on duplicate canonical producers for the same complete subject:

- metric ID and version;
- parameter version and effective time;
- instrument or applicable instrument set;
- exact bar specification/timeframe;
- calendar definition epoch;
- analytical profile;
- session or analytical window identity;
- configuration epoch; and
- producer/output schema version.

An actor-local registry remains useful for formula validation. It cannot be the only uniqueness
check after multiple producers exist.

### Canonical completed-bar subject identity

Before cutover, completed-bar identity must carry enough information to distinguish:

- exact instrument contract and venue;
- provider and adapter/source stream;
- full source selector and bar specification;
- interval start and end;
- timestamp interpretation policy;
- historical, live, aggregate, restored, or revised source class;
- calendar definition and effective epoch;
- trade date and product phase;
- analytical profile where applicable;
- configuration epoch;
- evidence references;
- completeness and real gaps;
- health and fidelity; and
- producer and subject revision.

There must be one canonical writer for each complete identity.

### Metric subject identity

`MetricValue` must become self-describing enough that an independent consumer can distinguish the
same formula across timeframes, profiles, sessions, windows, and parameter epochs without relying
on actor-local knowledge or an opaque `session_id`.

### Historical dependency planning

Each analytical owner declares its own evidence requirement. A separate accepted planner resolves
the requirement into exact UTC bounds. `DataAcquisitionActor` remains the only provider executor
and may share identical requests across owners.

No analytical owner calls IB or directly owns provider pacing.

## Proposed Data Flow

```text
Nautilus native bars + transient HistoricalBatch
                    |
                    v
        Completed-bar foundation owner
          - normalize and aggregate
          - converge history and live
          - admit duplicate/conflict truth
                    |
                    v
         Canonical CompletedBarInput stream
          + source snapshot/watermark recovery
                    |
        +-----------+-------------+----------------+
        |                         |                |
        v                         v                v
Completed-bar metrics   Session-reference   Analytical-window
        |                    metrics             metrics
        |                         |                |
        +-------------------------+----------------+
                                  |
                                  v
                       Rolling-measurements owner
                   where its exact input series applies
                                  |
                                  v
                     Canonical MetricValue streams
                                  |
                                  v
                  Entity owners and future read model
```

The exact delivery graph may allow rolling measurements to consume completed bars directly rather
than other numerical outputs. Dependencies must be explicit per metric definition; this diagram
does not create an implicit total order among owners.

## Delivery, Recovery, And Failure Rules

### No global arrival-order assumption

Consumers correlate by complete identities, source epochs, revisions, watermarks, and evidence
references. They must not assume a session transition, completed bar, historical result, and metric
arrive in one global order.

### Late or restarted consumers

Before an analytical owner may independently start or restart, it needs a bounded recovery path:

1. subscribe to the canonical source;
2. request a source-scoped bounded snapshot;
3. buffer later source events;
4. reconcile snapshot and buffered events by source epoch and watermark;
5. enter live calculation only after continuity is proven; and
6. publish explicit partial/unavailable health if retained history cannot cover the gap.

No raw-data persistence or replay system is implied. If required warmup exceeds the canonical
owner's bounded retention, the owner declares a normal historical dependency through the planner
and acquisition boundary.

### Slow-consumer isolation

One expensive or failed analytical family must not block canonical bar admission or unrelated
families. Every owner requires bounded work and retained state.

If a consumer falls behind, the system must expose a gap/degraded state and use the bounded
snapshot or historical repair path. Immutable bars must not be silently coalesced or dropped while
claiming continuous rolling state.

The concrete queue, callback, thread, and restart mechanics require a later Python-runtime review
after contracts and ownership are accepted.

### Shutdown

Each owner should:

- reject new work after entering `STOPPING`;
- cancel timers;
- stop admitting new demands;
- drain only already accepted bounded work to a configured deadline;
- report pending/incomplete counts; and
- isolate its stop failure from unrelated owners according to approved composition policy.

The existing historical coordinator currently can dispatch new queued work while sequential
cancellation is running, and a late provider callback cannot be reliably attributed after a retry.
Keep one in-flight historical request and one attempt until those separate provider-execution
defects are fixed and accepted.

## Nautilus Native Capability Disposition

Nautilus 2.0.0rc3 provides useful native facilities:

- `DataActor` lifecycle and native bar callbacks;
- `Clock` timers and alerts;
- native `Bar` and `BarType`;
- typed `CustomData`;
- signals;
- cache access;
- composite bar types; and
- registered native indicators.

Those facilities do not replace Markeitech's evidence envelope, calendar/profile identity,
historical/live convergence, conflict policy, health, fidelity, missing reasons, or analytical
window semantics.

Native composite bars and indicators remain separate shadow/parity candidates. They must not be
adopted as canonical replacements in the actor-split batch merely because their classes exist.

For every proposed native replacement, parity must cover exact interval boundaries, timestamp
policy, partial first bars, no-update intervals, OHLCV, volume, history/live overlap, revisions,
warmup, formula semantics, and complete Markeitech evidence identity.

## Migration And Cutover

The dormant `SessionMetricsActor` retains the historical combined implementation identity but is
not an active canonical producer in either tracked profile. No replacement responsibility may
become canonical until it is independently proven and explicitly enabled through the reviewed
cutover below.

### Phase 1: complete identities and manifests

- strengthen calendar, completed-bar, metric, and producer identities;
- establish global producer uniqueness validation;
- add source-scoped recovery contracts; and
- preserve current canonical outputs.

### Phase 2: shadow completed-bar foundation

- new foundation owner consumes the same approved inputs;
- publishes only to a noncanonical shadow namespace;
- compares exact accepted, duplicate, conflict, gap, and output populations;
- introduces no new provider request; and
- leaves the old actor as sole canonical writer.

### Phase 3: shadow numerical owners

- new numerical owners consume the current canonical completed-bar stream;
- publish noncanonical shadow metrics;
- compare formulas, warmup, missing values, health, fidelity, revision, and lineage;
- exercise alternate history-first/live-first and session-transition ordering; and
- prove one family can fail without stopping the others.

### Phase 4: explicit single-writer cutover

- select one exact completed interval/configuration/calendar boundary;
- record old and new source epochs and watermarks;
- fence the old canonical writer before admitting the new writer;
- transfer bounded current state through the approved snapshot/warmup path;
- prevent any dual canonical publication; and
- keep rollback capable of fencing the new writer before the old writer resumes.

### Phase 5: retire the old combined actor

- remove old configuration only after every enabled responsibility has an accepted owner;
- reconcile all downstream consumers;
- preserve historical review documentation;
- update current status and authoritative architecture; and
- retain rollback evidence until Markeitect accepts retirement.

## One-By-One Review And Acceptance

Each resulting family should be reviewed independently over ES before broad activation:

1. canonical completed-bar series identity and exact OHLCV;
2. predecessor-dependent return and true range;
3. active-session and previous-session references;
4. optional overnight and gap metrics;
5. each analytical window separately;
6. each rolling family, timeframe, and candidate duration separately; and
7. every enabled entity consumer after its required metrics are accepted.

The passive visual-debug capture may represent the canonical runtime outputs for this review. It
must not select, request, calculate, mutate, retain, or lifecycle-manage the analytical work it
displays.

A screenshot is review evidence, not formula or runtime acceptance by itself. Logs, manifests,
canonical records, input/output accounting, lineage, and deterministic fixtures remain required.

## Explicit Non-Goals

- no new metric formula merely to justify the split;
- no native composite-bar or indicator cutover;
- no provider connection or extra IB demand in shadow phases;
- no raw market-data persistence;
- no replay or backtesting;
- no dynamic actor loading;
- no analytical capability manager in this batch;
- no Watchlist intelligence store;
- no semantic events, opportunities, agent behavior, advice, or execution; and
- no claim that code separation alone proves runtime isolation or performance.

## Decisions For Markeitect Review

1. Accept the five logical owners above as the target responsibility split?
2. Require one canonical completed-bar writer and separate direct numerical metric ownership?
3. Keep analytical windows separate from product phases and session-reference calculations?
4. Let every rolling family declare its exact input timeframe and duration independently rather
   than inherit one global session-metrics selector?
5. Require a composition-time global metric-producer manifest before multiple producers are
   enabled?
6. Use shadow parity and an explicit interval-boundary writer fence instead of replacing the old
   actor in one step?
7. Review and accept each family independently on ES before broader activation?
8. Keep native composites and indicators as separately reviewed parity candidates rather than
   mixing their adoption into this split?

## Advisory Basis

Architecture, data-quality/lineage, event-driven-architecture, and NautilusTrader consultations
agree that the combined actor is a structural bottleneck and that a reuse-first split is warranted
only after calendar and subject identity are fixed. They also agree that one canonical
completed-bar writer, independent analytical families, bounded source recovery, global producer
uniqueness, and a fenced parity cutover are required.

The advisor conclusions are inputs to Markeitect's review. They do not approve this proposal.
