# V2 Stage 9D Entities And Rolling State Plan

**Status:** Slice 9D.1 implemented; pending Markeitect review

**Branch:** `v2-stage-9d-entities-rolling-state`

## Purpose

Stage 9C produces deterministic numerical `MetricValue` evidence. Stage 9D gives related values a
stable analytical identity and a bounded current-state projection so later semantic detectors,
options intelligence, Discord projections, and Sir Loke can refer to the same subject without
reconstructing its meaning independently.

The stage answers questions such as:

- Which exact ES primary session does this set of values describe?
- Which previous-session reference set is valid for the current trade date?
- Which configured opening range is developing or complete?
- Which indicative or opening gap is represented, and what evidence produced it?
- Which objective price levels and zones currently exist, on which horizon, and from which exact
  evidence?
- Is the current horizon directional, rotational, volatile, compressed, or expanding under a
  named configuration?
- Which swings and FVGs are developing, confirmed, filled, invalidated, or expired?
- What price/volume concentrations can be inferred honestly from completed bars?
- Which revision is current, what changed, and is the entity still usable?
- Which compact evidence from the completed session must survive restart?

Stage 9D may classify deterministic current analytical state when the classification is the
declared entity itself: for example `DIRECTIONAL`, `ROTATIONAL`, `COMPRESSED`, or `EXPANDING` under
an exact versioned definition. It does not publish semantic transition events such as approach,
test, acceptance, rejection, breakout, failure, or trapped participation; rank opportunities;
select an option; notify Discord about market meaning; or execute a trade. Those are later stages.

The approved scope is a complete first deterministic implementation, not a claim of permanent
trading calibration. Formulae, thresholds, windows, horizons, and lifecycle policies remain
reviewable and optimization-ready.

## Position In The Evidence Chain

```text
Native Nautilus observations
    -> Stage 9C MetricValue evidence
    -> Stage 9D typed entities and bounded rolling state
    -> Stage 9E meaningful semantic transitions
    -> later options, relationship, analytics, and Sir Loke read models
```

The boundaries are strict:

- an observation is provider or Nautilus market data;
- a measurement is a deterministic value calculated from declared evidence;
- an entity is a stable analytical subject with identity and lifecycle;
- rolling state is the bounded latest truth about entities;
- an event is an immutable meaningful transition; and
- an opportunity is a later advisory thesis and expression lifecycle.

An entity revision is not automatically a semantic event. Numerical changes may revise current
state without creating operator or agent noise.

## Stage Scope

This stage will:

- define versioned entity identity, definition, revision, lineage, health, and lifecycle contracts;
- project existing metric values into a bounded latest-state store;
- publish typed entity revisions through Nautilus without wrapping raw market data;
- provide a typed snapshot request/response boundary for later consumers;
- implement session, previous-session reference, opening-range, gap, and objective level entities;
- implement rolling volatility, compression/expansion, direction, trend, rotation, and range-state
  entities across explicitly configured horizons;
- implement configurable moving or anchored references required by the first trend-state contract;
- implement confirmed swing, FVG, and derived-zone entities with explicit developing,
  confirmation, fill, invalidation, and expiry semantics;
- implement a separately named bar-volume-distribution entity with inferred POC, value area,
  HVN/LVN candidates, balance areas, and distribution shape where volume is supported;
- retain explicit parameter, metric, calendar, analytical-profile, session, source, and fidelity
  identity;
- preserve event-driven convergence when metrics and session state arrive in any order;
- define expiry, invalidation, roll, and restart semantics without inventing missing evidence;
- persist only an approved compact completed-session summary; and
- audit meaningful entity and persistence lifecycle facts in PostgreSQL.

This stage will not:

- store raw quotes, bars, trades, books, chains, or every metric update;
- reactivate V1 levels, zones, profiles, signals, thresholds, or one-active-instrument behavior;
- classify approach, test, acceptance, rejection, hold, breakout, failure, target interaction, or
  trapped participation;
- label candle-distributed volume as observed trade-at-price volume or order flow;
- implement an observed trade-at-price volume profile until an approved source supplies that
  evidence;
- collapse rolling dimensions into a universal bullish/bearish score;
- create Discord market alerts;
- implement option discovery, Greeks, cross-instrument relationships, ML, or Sir Loke;
- add replay or backtesting support; or
- let analytical actors call Interactive Brokers directly.

## Existing Inputs And Ownership

Stage 9D consumes only accepted V2 contracts:

- `MetricValue` custom data from quote and session measurement actors;
- `SessionStateEvent` signals from `SessionStateActor`;
- evidence health already carried by metric values and session state;
- analytical profile, calendar, window, and parameter configuration from the validated runtime
  configuration; and
- persistence readiness through the existing startup handshake.

`SessionMetricsActor` and `RollingMetricsActor` remain owners of their accepted measurements.
`SessionStateActor` remains the calendar/session truth owner. `DataAcquisitionActor` remains the
only provider-demand owner. Stage 9D may add narrowly scoped deterministic measurement producers
only for numerical prerequisites which Stage 9C does not yet provide, such as signed displacement,
reference slope/separation, swing geometry, FVG geometry, and bar-volume price-bin estimates.
Those producers publish versioned `MetricValue` evidence before an entity projector consumes it;
an entity actor must not hide new numerical calculations inside an opaque payload or request IB
data directly.

## Contract Model

### Entity Definition

An `EntityDefinition` declares stable semantics rather than runtime values:

- `entity_type` and positive `entity_version`;
- decision question and implementation identity;
- typed payload contract;
- identity dimensions;
- required and optional metric dependencies with versions;
- permitted metric health and fidelity;
- lifecycle and completion rules;
- expiry, invalidation, roll, and revision policy;
- retention and durability class;
- parameter definitions and version requirements; and
- intended later event uses.

Definitions live in a registry with duplicate-key and dependency validation. A changed meaning or
payload shape requires a new entity version.

### Entity Identity

Entity identity is deterministic and independent of runtime arrival order. The canonical identity
contains only dimensions which define the subject, for example:

```text
entity type/version
instrument contract
analytical profile/version
trade date
session or named window
entity-specific discriminator such as gap kind
```

The resulting `entity_id` is stable across restarts and runs. A runtime UUID, actor ID, revision,
current value, metric timestamp, or source-run ID must not form part of analytical identity.

### Entity Revision

Each published revision carries:

- stable `entity_id`, type, and version;
- monotonic positive revision;
- instrument, calendar, profile, trade date, session, and window identity;
- typed entity payload;
- lifecycle status;
- effective, observed, calculated, and published UTC timestamps;
- metric IDs, metric versions, parameter versions, and evidence references;
- aggregate health and fidelity plus explicit missing/conflicting reasons;
- source actor and schema version; and
- previous revision reference when one exists.

Publication requires deterministic equality. The actor suppresses an update when the complete
meaningful signature is unchanged. A changed revision records what is currently known; it never
pretends that revised evidence was available earlier.

### Lifecycle Vocabulary

The initial lifecycle vocabulary is analytical availability, not market interpretation:

- `WARMING`: identity exists but required inputs are not yet sufficient;
- `ACTIVE`: the subject is developing with usable current evidence;
- `COMPLETE`: the configured subject is complete and no longer developing;
- `DEGRADED`: some evidence exists but quality or completeness is below the configured contract;
- `STALE`: the latest evidence exceeded its allowed age;
- `INVALIDATED`: the entity can no longer be used because identity or required evidence became
  inconsistent;
- `EXPIRED`: the configured retention or relevance boundary passed.

`COMPLETE` does not mean accepted, rejected, bullish, bearish, successful, or tradeable.

### Typed Payloads

Use a common envelope with entity-specific immutable payload dataclasses. Do not place unrelated
entity values into an unvalidated generic dictionary. Persistence may serialize the validated
payload to JSONB, but runtime type safety remains code owned.

## Approved Baseline Capability Groups

The first four groups are complete baseline implementations for Stage 9D. Complete means each
approved entity has typed contracts, deterministic identity, configuration, lifecycle, lineage,
bounded rolling state, failure isolation, and verification. It does not mean its initial parameter
values are trading-calibrated or frozen.

The fifth group is intentionally partial in evidence fidelity, not incomplete in engineering. Its
bar-derived result is implemented and verified fully under an explicit inferred contract. A future
observed trade-at-price profile will be a separate capability and entity family.

### Group 1: Objective Sessions, References, And Levels

#### Analytical Session Entity

Identity:

- instrument;
- analytical profile and version;
- trade date; and
- configured session/window definition ID and version.

Payload begins with session bounds, current phase, open/high/low/latest close, range, location,
supported volume and bar-VWAP estimate where applicable, coverage, completion, and fidelity. It
links to the authoritative calendar event and source metric revisions.

This entity is not a replacement for `SessionStateEvent`: the event owns exchange-calendar phase
truth, while the entity owns instrument/profile-specific analytical session state.

#### Previous-Session Reference Set

Identity:

- instrument;
- analytical profile and version; and
- completed session definition and trade date.

Payload contains only approved completed-session references such as OHLC, range, return, supported
volume, bar-VWAP estimate, coverage, exact bounds, and source fidelity. It becomes `COMPLETE` only
when the configured completion and coverage contract is satisfied. Partial data remains explicit
and must not be promoted into an exact reference set.

#### Opening Range Entity

Identity:

- instrument;
- analytical profile and version;
- trade date; and
- configured opening-range definition ID and version.

Payload contains configured bounds, developing/completed status, open/high/low/close, range,
coverage, supported volume, and source evidence. An opening-range definition is not hard-coded to
OR5 or OR15: duration, session anchor, extension formulae, source resolution, completion, and
applicability are typed configuration.

#### Gap Entity

Identity:

- instrument;
- analytical profile and version;
- target session definition and trade date; and
- configured gap definition ID and version.

Payload includes the named prior reference, current reference or session open, absolute and ratio
gap, source timestamps, health, and fidelity. Gap kinds are registry/configuration owned rather
than limited in code to one market-open convention. Fill, hold, and failure semantics remain Stage
9E work.

#### Objective Level Entity

One common envelope represents an exact price or narrow derived band produced by an approved
level definition. Initial level sources may include session/previous-session OHLC, opening-range
bounds/extensions, gap references, and approved moving or anchored references. Identity includes
the level definition/version, horizon, source subject, trade date or anchor identity, and exact
instrument/profile.

Payload includes price or bounded interval, source kind, horizon, direction-neutral role,
developing/completed state, age, coverage, health, fidelity, and evidence links. Support,
resistance, target, approach, acceptance, and rejection are not permanent properties of an
objective level; those roles require later price-interaction evidence.

### Group 2: Volatility, Compression, And Expansion State

The first rolling market-state entities convert accepted Stage 9C numerical evidence into named,
horizon-specific current state without producing a trade score.

#### Volatility State Entity

Payload may include realized-range/return measures, ATR, normalized percentile or z-score where a
valid baseline exists, current category, baseline coverage, and confidence/health. Category edges,
baseline choice, normalization, minimum coverage, hysteresis, confirmation, and staleness are
configuration, never hidden constants.

#### Compression/Expansion State Entity

Payload may include recent and phase-matched expansion ratios, range percentile, current phase,
duration, and evidence sufficiency. The baseline vocabulary may include `COMPRESSED`, `BALANCED`,
`EXPANDING`, and `UNAVAILABLE`; exact labels and boundaries are versioned definitions. Transition
events are Stage 9E output, not Stage 9D entity revisions.

### Group 3: Direction, Trend, Rotation, And Range State

Stage 9C currently provides unsigned directional efficiency, which is insufficient for an honest
directional entity by itself. Stage 9D therefore adds the smallest reviewed numerical
prerequisites before projecting state:

- signed displacement or return over each configured horizon;
- path efficiency with explicit sign retained separately;
- configurable moving or anchored reference values where requested;
- reference slope, price/reference separation, and optional alignment evidence; and
- coverage, recency, and conflicting-horizon evidence.

The baseline entity families are:

- `DirectionalStateEntity`: signed directional evidence for one exact horizon;
- `TrendRotationStateEntity`: directional, rotational, ranging, mixed, or unavailable state under
  one named definition; and
- `ReferenceStateEntity`: configured moving/anchored reference value, slope, separation, and
  health, without claiming that the reference held or failed.

No universal trend score is created. Each horizon remains independently queryable, conflicting
horizons remain visible, and a later consumer may not erase them behind one bullish/bearish value.
EMA is one configurable reference formula, not a mandatory or privileged implementation. Period,
source, resolution, anchor, smoothing formula, warmup, applicability, and dynamic eligibility are
all definition owned.

### Group 4: Swings, FVGs, And Derived Zones

#### Swing Entity

A swing entity represents confirmed market geometry under one configured detector. Its identity
includes detector/version, horizon, instrument/profile, pivot timestamp, and swing kind. Payload
includes pivot price, confirmation time, left/right evidence span, prominence/displacement
evidence, age, health, fidelity, and invalidation/expiry status.

The detector's left/right span, minimum prominence, normalization, confirmation delay, source
resolution, horizon, tie handling, and retention are configuration. Developing candidates may be
tracked internally, but they cannot be published as confirmed swings without the required future
evidence.

#### FVG Entity

An FVG entity represents a configured multi-bar price imbalance geometry. Payload includes exact
bounds, direction, formation timestamps, source horizon/resolution, width and normalized width,
fill percentage, remaining interval, age, health, and lifecycle. Pattern length, wick/body choice,
minimum width, normalization, confirmation, fill method, invalidation, merge, and expiry are
configuration.

The entity describes geometry only. It does not claim that price will revisit the interval or that
the interval is support/resistance.

#### Derived Zone Entity

A derived zone groups compatible approved entities under a named zone-building policy. Initial
inputs may include nearby objective levels, confirmed swings, and FVGs. Payload records every
constituent entity/revision, exact construction method, bounds, horizon mix, age, health, fidelity,
and invalidation state.

Merge distance, width/padding, minimum constituents, allowed source types/horizons, weighting,
maximum width, aging, and split/merge behavior are configuration. Confluence is represented by
its components; Stage 9D does not turn it into an opportunity score.

### Group 5: Inferred Bar-Volume Distribution

`BarVolumeDistributionEntity` estimates price/volume concentration from completed OHLCV bars only
where the analytical profile declares meaningful volume. It may expose:

- configured price bins and estimated volume per bin;
- inferred POC and value-area bounds;
- inferred HVN/LVN candidates;
- balance areas and distribution-shape descriptors; and
- coverage, contributing-bar count, interval bounds, health, and fidelity.

The allocation method inside each bar, bin width/count, tick rounding, value-area percentage,
HVN/LVN detector, smoothing, minimum volume/coverage, window/session, source resolution, update
cadence, and retention are typed configuration. The default method must be documented and
deterministic; no method may imply observed trade placement inside a candle.

The payload and human-readable name must carry `INFERRED_FROM_BARS`. It must not publish observed
aggressive volume, delta, CVD, large trades, absorption, trapped participants, or an observed
trade-at-price profile. A future `TradeAtPriceProfileEntity` will use separate evidence,
definition, identity, and fidelity and will not overwrite this entity.

### Compact Completed-Session Summary

The first durable summary is a derived projection, not raw market data. It should include only the
reviewed values needed by a later live startup:

- completed previous-session reference set;
- completed configured calendar windows such as power hour;
- approved finalized objective levels and entity references when cheaper and equally honest than
  re-requesting them;
- exact instrument/profile/session identity;
- metric, parameter, entity, and schema versions;
- source completeness, health, fidelity, and evidence references; and
- finalization and persistence timestamps.

Rolling intraday values, developing swings/FVGs/zones, bar-volume bins, raw bars, every entity
revision, and speculative future ML features are not retained by default. Each additional durable
field requires an explicit decision-question and restart-cost justification.

## Rolling State Projection

The initial pure `EntityStateBook` owns:

- latest revision by `entity_id`;
- bounded indexes by instrument, type, profile, trade date, and lifecycle status;
- deterministic admission and duplicate suppression;
- monotonic revision and timestamp validation;
- expiry/invalidation/roll processing; and
- immutable snapshots for readers.

Bounds must be explicit configuration:

- maximum entities globally and per instrument/type;
- active and completed trade-date retention;
- maximum tolerated input age;
- snapshot publication cadence or minimum update interval;
- maximum publications per calculation cycle; and
- startup-only versus later policy-controlled mutability.

Eviction is deterministic and observable. Active entities cannot be silently evicted to admit
lower-priority completed history. Exceeding a hard resource bound degrades the affected capability
without blocking unrelated actors.

## Runtime Actors And Messaging

One universal technical-analysis actor is rejected. The recommended bounded ownership is:

- `SessionReferenceEntityActor`: analytical session, previous-session reference, opening range,
  gap, and directly derived objective levels;
- `MarketStateEntityActor`: volatility, compression/expansion, direction, trend/rotation, and
  moving/anchored reference state;
- `MarketStructureEntityActor`: confirmed swings, FVGs, and derived zones; and
- `BarVolumeDistributionActor`: inferred bar-volume distributions and profile-node candidates.

The exact names are reviewable, but the responsibility split is architectural: one actor may fail,
degrade, warm, or restart without stopping unrelated entity families. All actors use the same
entity envelope, registry, and pure `EntityStateBook` primitives rather than inventing local
identity or revision rules.

Each actor will:

1. subscribe to persistence readiness and only the session/metric/entity evidence it owns;
2. accept inputs in any order without depending on actor startup sequence;
3. index the latest compatible revisions by exact identity;
4. calculate any approved numerical prerequisite through a pure named projector;
5. project entities through pure functions and a bounded state book;
6. publish changed revisions as typed Nautilus `CustomData`;
7. answer typed snapshot requests for later detectors and read models;
8. emit operational lifecycle/failure facts without persisting numerical churn; and
9. stop independently without changing acquisition or upstream metric ownership.

No nested signal handler may call provider, database, Discord, or blocking work. Any durable write
is queued through a reviewed persistence boundary. Timers may evaluate expiry/staleness, but they
must not impose startup sequencing; new evidence always triggers immediate reconciliation.

## Persistence Decision Gate

PostgreSQL currently owns operational facts and learned evidence-recency profiles. Stage 9D is the
first proposal to store approved analytical state. No schema or writer change will be implemented
until Markeitect approves this boundary.

### Recommended Boundary

Use a dedicated analytical-summary table and typed persistence command rather than disguising the
summary as an operational event. Keep operational entity lifecycle facts in `operational_events`.

Recommended table behavior:

- one deterministic row identity per instrument/profile/completed trade date/summary version;
- validated identity columns for exact lookup plus a versioned JSONB payload;
- immutable finalized revisions, with idempotent duplicate acceptance;
- explicit source run, entity/metric/parameter/schema versions, health, fidelity, and timestamps;
- no raw bars, ticks, quotes, chains, or unbounded revision history; and
- idempotent migration creation and required-column verification on every boot.

### Writer Ownership To Approve

Two viable options remain open:

1. extend `OperationalPersistenceActor` with a distinct typed analytical-summary command; or
2. add a dedicated bounded analytical-summary persistence actor sharing only low-level PostgreSQL
   utilities and migration ownership.

The recommendation is option 2 because operational audit and analytical state are different
responsibilities. The cost is another bounded worker and readiness/failure contract. This decision
must be reviewed before the persistence slice.

## Restart And Recovery Semantics

On startup:

- completed durable summaries may be loaded and published as restored `COMPLETE` entities;
- restored evidence retains original effective/finalization timestamps and source run;
- currently developing entities are rebuilt from current transient evidence;
- rolling intraday state is not fabricated from a summary;
- missing warmup returns `WARMING`, `DEGRADED`, or unavailable evidence as appropriate;
- formula/parameter/schema incompatibility prevents silent restoration; and
- unrelated runtime capabilities continue while one entity family warms or fails.

The stage does not add raw-data replay. A summary is sufficient only for explicitly declared
next-session decision questions.

## Configuration

All variable behavior follows the charter's configuration and optimization principle. A formula,
threshold, timeframe, window, lookback, detector policy, or lifecycle choice may not be hidden in
an actor constant merely because the first release uses one value. The first configuration must
declare:

- enabled entity families and selected watchlist capability;
- profile/entity bindings and versions;
- required metric IDs and versions;
- source resolution, horizon, history requirement, warmup, and calculation cadence;
- permitted health/fidelity and minimum coverage;
- formula implementation and version;
- moving/anchored reference kinds, price sources, periods, anchors, slopes, and separation units;
- volatility baseline, normalization, category boundaries, hysteresis, and confirmation;
- compression/expansion baseline, ratios/percentiles, boundaries, hysteresis, and confirmation;
- directional/trend/rotation inputs, conflict policy, boundaries, hysteresis, and confirmation;
- swing geometry, confirmation, normalization, tie handling, invalidation, and expiry;
- FVG geometry, minimum width, fill, merge, invalidation, and expiry;
- zone source eligibility, merge/split, width, weighting, age, and constituent requirements;
- bar-volume allocation, binning, value-area, node detection, smoothing, update, and retention;
- completion, expiry, retention, and publication policy;
- global/per-instrument resource bounds;
- summary fields and durability policy;
- startup-only or policy-controlled mutability metadata;
- source, version, and UTC effective time; and
- persistence retry, queue, and shutdown budgets if a dedicated writer is approved.

Every variable parameter carries:

- stable parameter identity and semantic description;
- unit, type, default, minimum/maximum or allowed values, and validation rules;
- scope by instrument class, instrument, session, horizon, profile, and capability;
- `dynamic` eligibility and mutability class;
- source, version, UTC effective time, and rollback/audit metadata; and
- optimization eligibility and safety bounds.

`dynamic=true` means a future policy or model may propose a typed in-bounds revision. It does not
authorize an actor or model to mutate configuration directly. `dynamic=false` freezes that
parameter for optimization under the current definition, but it remains explicitly configurable
through a reviewed version change. Runtime mutation, policy approval, and optimization are not
implemented by Stage 9D.

Entity identity dimensions, evidence honesty, schema/type validation, and the prohibition on raw
market-data persistence are code invariants, not tunable settings. Likewise, inferred bar-volume
evidence can never be configured into observed trade-at-price fidelity.

## Delivery Slices

### 9D.1: Contracts And Pure State Book

- define entity definition, identity, revision, lifecycle, health/fidelity, and typed payload
  contracts;
- implement registry and deterministic ID construction;
- implement bounded `EntityStateBook` admission, deduplication, revision, snapshot, roll, expiry,
  and invalidation behavior; and
- add pure contract/state tests.

No actor, configuration, database, migration, Discord, or connected run is introduced.

**Exit:** entity identity and rolling-state behavior are reviewable without framework side effects.

**Implementation evidence:** immutable typed contracts, deterministic identity, dependency and
evidence validation, revision ordering, meaningful-change suppression, bounded admission,
terminal-only eviction/pruning, restoration fidelity guards, and filtered immutable snapshots are
implemented. Nine focused tests pass, the complete intelligence suite passes 97 tests, and the
full non-PostgreSQL suite passes 312 tests with two PostgreSQL-marked tests deselected. No actor,
configuration loader, persistence schema, Discord projection, or connected run was added.

### 9D.2: Configuration And Numerical Prerequisites

- define and validate the complete configuration envelope for Groups 1-5;
- bind every entity definition to exact metric, session, horizon, fidelity, and parameter versions;
- add only missing deterministic numerical prerequisites such as signed displacement, reference
  slope/separation, swing/FVG geometry, and bar-volume price-bin estimates;
- keep each new numerical output in the metric registry with declared inputs, formula, units,
  normalization, warmup, applicability, health, fidelity, and failure modes; and
- prove configuration bounds, version separation, unsupported applicability, missing evidence,
  and historical/live convergence offline.

**Exit:** every entity input is available as explicit versioned evidence; no entity projector
hides an unreviewed calculation or constant.

### 9D.3: Session, Reference, And Objective-Level Projection

- add reviewed configuration and composition;
- implement pure projections for analytical session, previous-session reference, opening range,
  gap, and their approved objective levels;
- add the bounded session/reference owner and typed CustomData publication;
- add snapshot request/response; and
- prove out-of-order convergence, bounded memory, duplicate suppression, actor isolation, and clean
  shutdown offline.

**Exit:** stable objective market subjects are shared through Nautilus without interaction or
trading semantics.

### 9D.4: Rolling Market-State Projection

- implement volatility state;
- implement compression/expansion state;
- implement horizon-specific direction and trend/rotation state;
- implement configured moving/anchored reference state;
- preserve conflicting horizons and unavailable evidence rather than collapsing them; and
- prove threshold boundaries, hysteresis, confirmation, revisions, staleness, and bounded state
  offline.

**Exit:** consumers can query current numerical market state by exact horizon and definition
without deriving it independently or receiving semantic transition noise.

### 9D.5: Swing, FVG, And Zone Projection

- implement confirmed swing entities and developing-candidate containment;
- implement FVG formation, fill, invalidation, expiry, and revision behavior;
- implement derived zones with complete constituent lineage;
- prove no look-ahead publication, deterministic overlap/merge behavior, late evidence handling,
  and bounded retention; and
- keep support/resistance and interaction meaning out of the entity payload.

**Exit:** reusable market geometry is available as truthful entities without pretending it is a
trade setup.

### 9D.6: Inferred Bar-Volume Distribution

- implement deterministic bar-volume allocation and configurable price binning;
- derive inferred POC, value area, HVN/LVN candidates, balance areas, and shape descriptors;
- reject volume-unsupported instruments/profiles honestly;
- carry `INFERRED_FROM_BARS` through runtime contracts, snapshots, logs, and human-readable names;
- prove volume conservation under the selected allocation method, deterministic bin boundaries,
  revision behavior, and resource bounds; and
- prohibit order-flow, delta, CVD, aggressive-side, or observed trade-at-price claims.

**Exit:** Markeitech has a useful candle-derived price/volume map without counterfeit profile or
order-flow fidelity.

### 9D.7: Durable Summary Persistence

- resolve the persistence-owner decision gate;
- add the reviewed migration and boot-time verification;
- persist only finalized approved session/power-hour summaries;
- preserve idempotency, retry, queue bounds, failure isolation, and source/version lineage; and
- keep lifecycle audit separate from stored analytical state.

**Exit:** the next premarket restart can recover yesterday's approved summary without raw history.

### 9D.8: Recovery And Connected Acceptance

- hydrate compatible summaries;
- prove incomplete or incompatible summaries do not become current truth;
- run Markeitect-owned connected acceptance;
- reconcile every entity-family, summary, persistence, resource, and shutdown counter;
- compare selected objective levels, states, swings, FVGs/zones, and inferred profile values with
  independent operator references; and
- record unexercised session/horizon/market conditions as acceptance debt rather than passing them
  by assumption.

**Exit:** Stage 9D is ready to support quiet Stage 9E detectors.

## Verification Plan

Offline verification must cover:

- strict serialization and malformed/unknown-schema rejection;
- stable identity across runs and arrival order;
- entity-version separation;
- monotonic revisions and unchanged-signature suppression;
- metric/parameter/fidelity lineage preservation;
- warming, partial, degraded, stale, invalidated, complete, and expired behavior;
- out-of-order session state and metric delivery;
- exact duplicate, conflicting revision, and late-input behavior;
- deterministic bounds and eviction protection;
- snapshot immutability and filtering;
- persistence idempotency, schema repair, retries, queue pressure, and restart compatibility;
- exact threshold, hysteresis, confirmation, source-resolution, and horizon behavior;
- no look-ahead swing or FVG confirmation;
- deterministic zone construction and complete constituent lineage;
- bar-volume conservation, binning, value-area/node calculation, and unsupported-volume behavior;
- fidelity separation between inferred bar-volume distribution and future observed profiles;
- actor failure isolation and event-loop non-blocking behavior; and
- no raw market observations in PostgreSQL.

Connected acceptance must prove only what the live run observes. It should reconcile publication
and persistence counters, inspect memory/resource behavior with the Observatory off, verify clean
shutdown, and record any market-session coverage which could not be exercised.

## Stage Exit Criteria

Stage 9D closes only when:

- every approved Group 1-4 entity has one stable, versioned identity and typed payload;
- Group 5 is fully implemented under the explicit `INFERRED_FROM_BARS` contract and never
  represented as observed trade-at-price evidence;
- all entity revisions cite compatible accepted metric evidence and parameter versions;
- any added numerical prerequisite is registry-defined, independently testable, and carries exact
  formula, units, warmup, health, and fidelity;
- rolling state is bounded, deterministic, snapshot-readable, and actor-order independent;
- developing, complete, stale, degraded, invalidated, and expired states remain honest;
- completed-session summaries persist and restore idempotently without raw market data;
- PostgreSQL analytical state and operational audit reconcile;
- unrelated runtime capabilities continue through entity or summary failure;
- offline verification passes and connected acceptance debt is stated precisely; and
- current status, roadmap, implementation, and tests agree.

## Approved Decisions

Markeitect approved the following decisions before implementation began:

1. Capability applicability is bound through configuration by analytical profile, instrument or
   instrument class, session, and horizon. The initial baseline uses one-minute evidence for
   session/opening-range/proximity and fast state; five- and fifteen-minute evidence for intraday
   state and structure; direct one-hour and one-day evidence for higher-timeframe state and
   structure; and direct weekly evidence only for configured structural references. No universal
   resolution pyramid, preferred instrument, or all-capabilities-on-all-instruments rule exists.
2. Runtime ownership is split among bounded session/reference, market-state, market-structure, and
   bar-volume-distribution actors sharing common entity contracts and pure state-book primitives.
3. The first moving/anchored reference baseline contains the existing session bar-VWAP estimate,
   configured EMA 20/50/200 references, and one dynamic-eligible EMA initially set to 10 with a
   bounded 5-34 integer envelope. EMA is a registry formula, not privileged code; additional
   reference families require an explicit decision question.
4. The first structure baseline uses a configurable confirmed-pivot swing detector; configurable
   three-bar wick-gap FVG geometry; deterministic constituent-preserving derived zones; and a
   deterministic uniform candle-volume allocation across intersected price bins. Order blocks and
   supply/demand semantics remain deferred until precisely defined.
5. Durability has three explicit classes. Finalized session facts are persisted. The latest
   revision of explicitly configured cross-session entities may be checkpointed, including
   confirmed higher-timeframe swings, still-relevant FVGs/zones/levels, and compact finalized
   inferred profile references. Rolling state, developing candidates, volume bins, per-update
   revisions, and raw market observations remain transient. Restored cross-session checkpoints
   remain stale/degraded until catch-up evidence covers the offline interval.
6. A dedicated analytical-summary persistence actor and table own approved analytical durability;
   operational audit remains separate. Analytical recovery failure degrades that capability and
   does not stop unrelated runtime actors.
7. Initial completed-summary retention is two sessions per instrument/profile with a fourteen-day
   maximum age. Every entity family retains independent typed/versioned bounds. Restoration
   requires exact schema, entity, metric, formula, and parameter compatibility; incompatible state
   is audited, ignored, and re-warmed.

All numerical defaults above remain configuration values with identity, type, bounds, source,
version, UTC effective time, mutability, and optimization metadata. Approval establishes the
first baseline, not permanent trading calibration.
