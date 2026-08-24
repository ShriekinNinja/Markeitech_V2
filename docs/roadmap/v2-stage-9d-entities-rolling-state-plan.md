# V2 Stage 9D Entities And Rolling State Plan

**Status:** Slices 9D.1 through 9D.4C approved, committed, and connected-accepted; 9D.5A approved
and committed; 9D.5B implemented locally for review; narrow 9D.3 window-boundary acceptance
deferred

**Branch:** `v2-stage-9d-entities-rolling-state`

**Acceptance branch:** `v2-stage-9d-connected-acceptance`

**9D.5 branch:** `v2-stage-9d5-market-structure`

**Next gate:** Review 9D.5B, then implement 9D.5C FVG and constituent-preserving zone projection.
The unobserved 9D.3 opening-range developing-to-complete transition is explicitly deferred until a
run crosses that configured boundary and does not block 9D.5.

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
- Which confirmed pivots form the current bounded structure on one exact horizon, how are its
  alternating legs related, and where does that structure remain mixed or insufficient?
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
- implement confirmed swing, swing-leg, per-horizon pivot-structure, FVG, and derived-zone
  entities with explicit confirmation, relationship, fill, invalidation, and expiry semantics;
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

### Group 4: Swings, Pivot Structure, FVGs, And Derived Zones

#### Swing Entity

A swing entity represents confirmed market geometry under one configured detector. Its identity
includes detector/version, horizon, instrument/profile, pivot timestamp, and swing kind. Payload
includes pivot price, confirmation time, left/right evidence span, prominence/displacement
evidence, age, health, fidelity, and invalidation/expiry status.

Age is query-relative evidence derived from the immutable confirmation timestamp and the query's
UTC timestamp. It is not stored as a changing payload field and cannot create time-only revisions.

The detector's left/right span, minimum prominence, normalization, confirmation delay, source
resolution, horizon, tie handling, and retention are configuration. Developing candidates may be
tracked internally, but they cannot be published as confirmed swings without the required future
evidence.

Swing detection and swing interpretation remain separate. A confirmed swing records objective
geometry; it does not by itself claim higher-high, lower-low, support, resistance, trend, reversal,
or trade direction. Different configured detectors may expose tactical and structural pivots from
the same source timeframe, and different source horizons remain independently identifiable. A
lower-horizon pivot may be displayed beside a higher-horizon pivot, but it never inherits the
higher horizon's identity.

#### Swing Leg Entity

A swing leg relates two compatible, alternating confirmed pivots under one configured chain
policy. Its identity includes the chain definition/version and both endpoint entity IDs. Payload
includes exact origin and destination revisions, price and percentage displacement, elapsed bars
and UTC duration, raw and volatility-normalized slope, available path-efficiency and displacement
evidence, optional volume context, health, fidelity, and complete lineage.

The leg does not predict continuation or reversal. Volume is optional confirming context rather
than a universal geometry requirement so instruments without meaningful volume can retain honest
price structure.

#### Pivot Structure State Entity

A pivot-structure state owns the bounded current relationship among confirmed pivots for one exact
instrument, analytical profile, detector, source horizon, and structure definition. It preserves
the selected pivot chain, current structural bounds, high-to-high and low-to-low comparisons,
successive-leg expansion or compression, unresolved conflicts, evidence age, and health. Initial
relationship labels are descriptive: `HIGHER`, `LOWER`, `EQUAL`, `MIXED`, and `INSUFFICIENT` on
their explicit axes. A derived geometry state may be `UPWARD`, `DOWNWARD`, `ROTATIONAL`, `MIXED`,
or `INSUFFICIENT` only under its named versioned policy.

All confirmed swings remain independently queryable. Consecutive same-kind pivots are never
deleted or silently rewritten: the configured chain policy may replace the current terminal pivot,
retain the pivots in separate compatible chains, or leave the chain unresolved until an opposite
pivot confirms. Only the current relationship projection revises.

Pivot structure is narrower than Group 3 direction/trend state. It describes confirmed swing
relationships only. Later composites may combine independently queryable horizons with EMA,
efficiency, volatility, volume, cross-instrument, options, and other evidence through explicit,
decomposable, configuration-owned weights. Stage 9D.5 does not create that cross-horizon composite
or a universal direction score.

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
- `MarketStructureEntityActor`: confirmed swings, swing legs, per-horizon pivot structure, FVGs,
  and derived zones; and
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
- swing-chain compatibility, alternating-leg construction, same-kind terminal-pivot policy,
  equal-high/low tolerance, minimum leg displacement, scale mixing, revision, and retention;
- swing-leg displacement, duration, slope normalization, path-efficiency, and optional volume
  context;
- pivot-structure relationship labels, bounds, expansion/compression, conflict handling, health,
  and expiry;
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

**Implementation evidence:** tracked configuration schema 16 now owns a disabled, bounded catalog
envelope for all five groups. Definitions carry exact analytical applicability, dependency and
parameter versions, lifecycle rules, durability, health/fidelity permissions, complete typed
parameter envelopes and effective sets, optimization eligibility, and resource limits. Enabled
catalogs must cover all groups and fail closed on identity/version conflicts, unknown profile or
instrument bindings, unsupported volume applicability, missing parameter values, invalid
mutability, and out-of-range or off-step values. `system.example.toml` remains disabled and empty;
the ignored schema-15 local configuration is deliberately untouched pending operator-reviewed
migration before any connected run.

Thirteen version-one prerequisite metrics are registered over exact completed-bar dependencies:
signed displacement, simple return, signed path efficiency, EMA value/slope/separation, swing pivot
price/prominence, FVG lower/upper/width/fill, and inferred allocated bar volume. Pure calculations
use explicit configurable policies and real warmup contracts; reject mixed, overlapping, or
incomplete bar identity; preserve missing/partial/unsupported evidence; confirm swings only after
the right span; conserve allocated candle volume exactly; and converge numerically for equivalent
historical and live completed bars. Bar allocation is explicitly inferred geometry, never observed
trade-at-price evidence. Eight prerequisite tests, 25 configuration tests, the 105-test
intelligence suite, and the 327-test non-PostgreSQL suite pass. No actor, database schema, Discord
projection, or connected run is introduced by 9D.2.

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

**Implementation evidence:** the upstream session-reference metric catalog now publishes exact
active/previous-session `start_ns`, `end_ns`, and `complete` values. Opening-range metrics now
publish open, close, and optional supported volume in addition to existing geometry; unsupported
volume stays explicit and field-local instead of degrading price evidence. The reviewed enabled
test catalog defines analytical session, previous-session reference, configured opening range,
opening gap, previous-session high/low, and opening-range high/low entities with exact dependency,
application, identity, health, fidelity, and parameter versions. The tracked runtime example stays
disabled and empty.

`SessionReferenceEntityActor` consumes typed `MetricValue` custom data only. Its pure bounded owner
indexes exact subject evidence, converges under arrival-order changes, emits `WARMING` identities
until required evidence exists, advances monotonic meaningful revisions, enforces profile and
session-phase applicability, rejects parameter-version mismatches, suppresses exact
duplicates/stale/conflicting inputs, bounds retained metric values and entity state, and queues
publication overflow rather than silently dropping an admitted revision. Per-type bounds are
correctly scoped by instrument. Composition fails closed when a Group 1 dependency has no
configured metric producer. Immutable typed snapshot request/response contracts expose filtered
current state to later actors.

Offline evidence covers order-independent convergence, warming-to-active lifecycle, optional
volume, direction-neutral objective levels, phase filtering, bounded retention, overflow recovery,
duplicate/conflict behavior, per-instrument/type limits, actor composition, and a native Nautilus
typed-CustomData delivery proof. A connected missing-evidence case exposed a timestamp fallback
defect; the corrected path now publishes a payload-free `WARMING` revision and is protected by a
focused regression test. The complete offline V2 suite passes 337 tests with two PostgreSQL-marked
tests deselected.

The accepted 2026-08-23 closed-market run reached system `READY` with 18/18 configured instrument
definitions. IB completed 39 historical dependencies; 21 were ready and 18 degraded honestly when
the closed-market one-minute interval returned no observations. Session measurement emitted 18
reference batches with 900 values and three window batches with 39 values, with zero failures. The
Group 1 actor accepted 42 metrics, published 45 revisions, suppressed nine duplicate revisions,
rejected none, and stopped with no pending publication. PostgreSQL stored 682/682 accepted
operational events, Discord delivered 3/3 health messages, runtime resource health remained normal,
and shutdown completed cleanly. Live-bar updates were later exercised, but an opening-range
developing-to-complete transition still requires a run which crosses the configured window
boundary. Markeitect explicitly deferred that narrow proof; it remains recorded acceptance debt
without blocking 9D.5.

This slice adds no provider request, raw-data persistence, analytical PostgreSQL table, Discord
market projection, semantic interaction event, opportunity, option selection, or Sir Loke behavior.

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

#### 9D.4A: Pure State Policy And Payload Contracts

This first 9D.4 batch implements the actor-independent contract and classification layer only. It
adds typed immutable payloads for volatility, compression/expansion, directional,
trend/rotation, and moving/anchored-reference state. A common pure classifier accepts one exact
named numerical measure and a versioned policy containing configuration-owned category labels and
contiguous bands, hysteresis, consecutive-confirmation count, minimum coverage, maximum evidence
age, and permitted health/fidelity. The policy also carries definition, parameter, source, and UTC
effective-time identity so later runtime composition does not manufacture hidden defaults.

The classifier uses lower-inclusive and upper-exclusive category boundaries, preserves a current
confirmed category while a new candidate accumulates, resets interrupted candidates, requires a
configured hysteresis crossing before a transition candidate begins, ignores non-monotonic input
without mutating accepted memory, and returns `UNAVAILABLE` under stale or insufficient evidence.
The exact unavailable label is policy owned. Family projectors retain their complete numerical
inputs, horizon identity, evidence lineage, candidate/confirmation state, independent reference
slope and separation axes, and explicit cross-horizon conflicts. No horizon is collapsed into a
universal direction or trend score.

Seven focused tests prove policy-envelope rejection, exact category boundaries, initial and
transition confirmation, hysteresis, interrupted candidates, stale and late evidence, coverage
and fidelity requirements, policy-version re-warm, independent reference axes, numerical payload
retention, and explicit cross-horizon conflicts. The 144-test intelligence/configuration scope and
complete 344-test
non-PostgreSQL suite pass with two PostgreSQL-marked tests deselected.

9D.4A deliberately adds no Nautilus actor or request, runtime configuration binding, entity
revision publication, state-book ownership, PostgreSQL schema, Discord projection, semantic
transition event, opportunity selection, option selection, or Sir Loke behavior. Those runtime
concerns require the next separately reviewed 9D.4 batch.

#### 9D.4B: Bounded Metric-Driven State Ownership

This second 9D.4 batch binds the 9D.4A policies to typed entity definitions, exact metric roles,
parameter-set identity, analytical-profile applications, session phases, and horizons. A new pure
`MarketStateProjectionOwner` accepts `MetricValue` revisions, retains only a configured maximum,
projects through the shared `EntityRegistry` and `EntityStateBook`, queues only admitted revisions
under a configured per-cycle publication limit, and serves immutable filtered snapshots. It adds
no Nautilus actor or runtime subscription.

The owner currently covers the metric-driven families that can be represented honestly from
scalar evidence:

- volatility state with explicit normalization and complete optional numerical context;
- compression/expansion state with explicit recent/phase baseline counts and duration;
- signed directional state for one exact horizon; and
- configured moving/anchored reference state with independent slope and separation policies.

Each classification axis binds one required measure role and one required coverage role. The
binding validates that the policy measure, entity parameter version, metric dependency, payload
type, policy axes, and family-specific roles agree before any input is accepted. Classification
memory is isolated by deterministic entity identity and policy axis. A metric correction at the
same effective timestamp re-evaluates from a clean policy memory rather than masquerading as a new
chronological observation.

Metric duplicates, same-revision conflicts, stale revisions, parameter-version mismatches,
unsupported instruments, session-phase mismatches, and unrelated metrics are contained without
mutating accepted state. `reconcile(now_ns)` can publish a `STALE` revision without waiting for a
new metric. Publication overflow is deferred rather than discarded. Per-entity projection and
classification caches are removed when the shared state book rejects or evicts their identity, so
the pure owner remains bounded with the entity and metric limits it advertises.

Eight focused tests prove role-order convergence, confirmation, duplicate/conflict/stale input
containment, parameter isolation, timer-driven staleness, exact-horizon snapshot queries,
independent reference axes, compression baseline retention, deferred publication, and bounded
metric retention. The combined intelligence/configuration scope passes 152 tests in the locked V2
environment, and the complete non-PostgreSQL V2 suite passes 352 tests with two PostgreSQL-marked
tests deselected.

`TrendRotationStatePayload` remains available from 9D.4A, but 9D.4B intentionally refuses to bind
`trend_rotation_state`. That family needs typed directional, compression/expansion, and reference
entity inputs plus explicit conflicting-horizon evidence. Encoding those facts as ad hoc scalar
strings would violate the evidence and structured-data rules. Cross-entity reconciliation, raw
runtime configuration translation, the Nautilus actor, and live publication therefore remain the
next separately reviewed 9D.4 work. PostgreSQL, Discord, semantic events, opportunities, options,
and Sir Loke remain unchanged.

#### 9D.4C: Configured Runtime Projection

This third 9D.4 batch translates approved metric-driven state definitions into validated runtime
configuration and a dedicated Nautilus actor. Entity-analysis catalog version 2 may attach an
optional `market_state` block to a Group 2 or Group 3 definition. The binding selects one exact
effective parameter set and declares one or more independently named policy axes. Every axis names
its required measure and coverage roles, category bands, unavailable category, and the parameter
IDs supplying boundaries, hysteresis, confirmation count, minimum coverage, and maximum evidence
age. The parser rejects missing or mismatched parameter sets, parameter-version disagreement,
unknown or incorrectly typed parameter references, optional policy evidence, duplicate axes or
policy identities, non-contiguous bands, and legacy catalog versions.

The actor receives only typed `MetricValue` custom data. It does not subscribe to bars, calculate
source measurements, request provider data, or embed classification logic. It delegates ingestion,
deduplication, conflict handling, bounded metric retention, classification memory, entity admission,
publication deferral, snapshots, and staleness revision generation to the 9D.4B pure owner. The
actor owns the Nautilus subscriptions, typed `EntityRevision` publication, configured reconciliation
timer, persistence-ready handshake, snapshot throttling, failure isolation, and bounded lifetime
counters.

Composition activates only enabled Group 2 or Group 3 definitions which carry an explicit runtime
binding. It derives the available rolling metric/version identities from enabled configured
families and candidates, then refuses startup if any bound dependency lacks a producer. Definitions
without a runtime binding remain catalog-only and are not silently interpreted. This lets the
entity catalog describe the accepted future capability set without pretending every family already
has runtime evidence.

The first producer-backed binding is deliberately narrow: `volatility_state` for the configured
fast horizon uses `rolling.fast.context_45m.range_percentile_recent` as its normalized measure and
the matching coverage ratio, with optional ATR, realized range, and realized return magnitude as
numerical context. Initial values in the test catalog are offline fixture parameters, not trading
calibration. The tracked runtime example remains disabled with no definitions.

The following families remain deferred honestly:

- compression/expansion requires the approved phase-duration observation metric in addition to
  existing expansion and baseline evidence;
- direction requires signed displacement, signed return, and signed path-efficiency producers;
- moving/anchored reference state requires reference value, slope, separation, and coverage
  producers; and
- trend/rotation requires typed cross-entity inputs and explicit conflicting-horizon evidence.

Focused tests cover catalog-version and parameter-reference rejection, explicit runtime resource
limits, producer availability, selective composition, sandboxed native bus delivery, and projection
of rolling metric evidence into a typed confirmed volatility-state revision. The combined
intelligence/configuration/composition/message scope passes 173 tests, and the complete
non-PostgreSQL V2 suite passes 358 tests with two PostgreSQL-marked tests deselected. The batch adds
no provider request, analytical PostgreSQL persistence, Discord output, semantic transition,
ranking, opportunity, option selection, or Sir Loke behavior. Connected acceptance is separate and
must prove actual rolling evidence, revisions, staleness, resource behavior, and clean shutdown.
Any liquid session which supplies the configured rolling inputs is valid evidence; US RTH is not a
9D.4C requirement. Session- or window-specific transitions remain accepted only when the run
actually crosses their configured boundaries.

### 9D.5: Swing, Pivot-Structure, FVG, And Zone Projection

#### 9D.5A: Confirmed Swing Entities

- implement confirmed swing payload, identity, lifecycle, and pure projection;
- contain developing candidates internally and publish only after the configured right-span and
  confirmation evidence is complete;
- preserve exact detector, source horizon, pivot/confirmation time, prominence, displacement,
  optional volume context, evidence bars, health, and fidelity; and
- prove strict no-look-ahead behavior, tied-pivot policy, deterministic deduplication, late evidence
  handling, and bounded candidate/confirmed retention.

**Exit:** independently queryable tactical and structural pivots are truthful, horizon-specific
entities rather than inferred chart labels.

**Implementation evidence:** a framework-independent confirmed-swing payload, detector application
contract, and bounded projection owner consume only `CompletedBarInput` evidence. The owner keeps a
bounded first-accepted ledger per exact detector/application/instrument/bar-specification subject,
splits evidence at every non-contiguous interval, and invokes the reviewed strict-pivot geometry
only within contiguous runs. It publishes immutable `COMPLETE` revisions only after the configured
right span exists. A late bar may complete a previously gapped window, while exact historical/live
duplicates and conflicting observations cannot republish or rewrite accepted truth.

Entity identity preserves definition, detector and version, source bar specification, horizon,
pivot timestamp, swing kind, instrument, and analytical profile. Payload preserves pivot price,
strict prominence, confirmation close and displacement from the pivot, optional pivot-bar volume,
configured left/right spans, and exact source-bar references. Health and fidelity are inherited
from the complete evidence window. The shared registry validates the required pivot-price and
prominence metric contracts, and the shared state book provides deterministic admission, snapshot,
terminal eviction, and global/per-instrument/per-type bounds. Multiple tactical and structural
detector applications remain independently identifiable; no relationship label or directional
meaning is introduced.

Seven focused tests prove no-look-ahead confirmation, tied-pivot rejection, transport-independent
deduplication, late contiguous evidence, detector/horizon identity isolation, degraded/partial and
missing-volume honesty, and bounded candidate/confirmed retention. Together with prerequisite
coverage, 15 focused tests pass, the complete intelligence suite passes 134 tests, and the full
non-PostgreSQL suite passes 365 tests with two PostgreSQL-marked tests deselected. This slice adds
no Nautilus actor, runtime configuration binding, PostgreSQL table, Discord output, semantic event,
chart renderer, connected run, swing leg, pivot relationship, FVG, or zone.

#### 9D.5B: Swing Legs And Per-Horizon Pivot Structure

- implement deterministic alternating swing legs from compatible confirmed pivots;
- implement explicit consecutive same-kind pivot handling without deleting confirmed swing truth;
- implement high-to-high, low-to-low, structural-bound, leg-expansion/compression, and
  insufficient/mixed relationship projection for one exact horizon;
- preserve complete endpoint revisions, chain-policy identity, raw and normalized geometry,
  optional volume context, health, fidelity, and conflicts; and
- prove deterministic chain construction, equality-tolerance boundaries, terminal-chain revision,
  arrival-order convergence, horizon isolation, and bounded retention.

**Exit:** later consumers receive one canonical, inspectable pivot relationship state per configured
horizon instead of reconstructing HH/HL/LH/LL and swing legs independently.

**Implementation evidence:** a separate pure relationship owner consumes immutable complete
confirmed-swing revisions without changing or deleting confirmed-swing truth. Exact application,
instrument, analytical profile/version, detector/version, horizon, source-bar specification, and
chain-policy/version define each bounded subject. The policy explicitly owns source interval,
same-kind terminal handling, resolved-run selection, equality tolerance, minimum leg displacement,
leg expansion/compression tolerance, pivot/bar/normalization retention, and selected-chain bounds.
Each numerical market threshold declares its current value, floor, ceiling, step, and dynamic
eligibility under the versioned policy. Equal-price selection within a same-kind run uses an
explicit earliest/latest tie-break policy.

Alternating compatible pivots produce revisable swing-leg entities with exact endpoint entity and
revision lineage. Each leg records signed price and percentage change, UTC duration, elapsed bars,
price slope per bar and hour, optional volatility-normalized displacement and slope, available path
efficiency, favorable/adverse excursion, optional path volume, exact completed-bar references,
health, fidelity, and explicit missing context. Supporting completed bars and normalization
evidence are retained independently before or after the first swing so callback order cannot erase
available context. No configured normalization is fabricated when its metric evidence is absent.

One active pivot-structure entity revises per exact subject. It preserves the bounded selected
alternating chain, every selected leg revision, explicit same-kind predecessor comparisons for all
retained confirmed pivots, structural bounds, consecutive-leg scale comparisons, superseded
confirmed pivots, unresolved pivots, and minimum-displacement conflicts. Comparison records own
price and percentage change, elapsed bars, UTC duration, and slope. Geometry labels are
limited to the named policy's descriptive `UPWARD`, `DOWNWARD`, `ROTATIONAL`, `MIXED`, and
`INSUFFICIENT` relationships; they are not a trend score, prediction, support/resistance claim, or
cross-horizon composite.

Every retained confirmed pivot after the first of its kind owns an explicit comparison to that
same-kind predecessor, including pivots which the current alternating chain supersedes. Only
comparisons whose endpoints remain selected may influence the current geometry label. The baseline
supports more-extreme terminal replacement, latest-terminal selection, and
unresolved-until-opposite behavior. Equal-price boundaries are inclusive of configured tolerance.
Late swings are sorted by immutable pivot identity and converge to the same current payload as
chronological arrival. Eleven focused tests cover policy-envelope rejection, complete leg geometry
and lineage, equality-boundary comparisons, explicit same-kind replacement and tie-breaking,
unresolved-run resolution, late path/normalization enrichment, minimum displacement, leg scale and
geometry labels, arrival-order convergence, detector/horizon isolation, and bounded pivot
retention. This slice adds no Nautilus actor, runtime configuration binding, PostgreSQL table,
Discord output, semantic event, chart renderer, connected run, FVG, zone, cross-horizon weighting,
trendline, Fibonacci, or trading meaning.
Together with prerequisite coverage, 18 focused market-structure tests pass, the complete
intelligence suite passes 145 tests, and the full non-PostgreSQL suite passes 376 tests with two
PostgreSQL-marked tests deselected.

#### 9D.5C: FVG And Constituent-Preserving Zone Projection

- implement FVG formation, fill, invalidation, expiry, and revision behavior;
- implement derived zones with complete constituent lineage and explicit source/horizon
  compatibility;
- prove deterministic overlap, merge, split, maximum-width, minimum-constituent, late-evidence,
  revision, and bounded-retention behavior; and
- keep support/resistance, revisit expectation, interaction meaning, confidence, and opportunity
  scoring out of FVG and zone payloads.

**Exit:** FVG and zone geometry remains useful and inspectable without turning every pattern into a
market claim or repeating V1's noisy annotation behavior.

#### 9D.5D: Runtime, Snapshot, Visual, And Connected Acceptance

- compose the optional bounded `MarketStructureEntityActor` only for enabled reviewed definitions;
- publish changed revisions through typed Nautilus custom data and serve immutable filtered
  snapshots;
- reconcile actor/entity/publication/resource counters and prove independent failure and clean
  shutdown behavior;
- project the same entity snapshots into a non-authoritative visual acceptance view without
  calculating or mutating analytical truth in the renderer; and
- compare selected pivots, relationships, FVGs, and zones with timestamped independent operator
  references while treating visual agreement as calibration evidence rather than general proof.

**Exit:** reusable market geometry and per-horizon pivot structure are available through the live
runtime as truthful entities without pretending they are a trade setup or cross-horizon decision.

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
- deterministic swing-leg and pivot-chain construction, including consecutive same-kind pivots;
- equal-high/low tolerance boundaries and same-kind terminal-pivot revision without rewriting
  confirmed swing entities;
- strict separation among detector identity, source horizon, pivot scale, pivot structure, and
  broader directional/trend state;
- deterministic raw and normalized leg displacement, duration, slope, and optional volume context;
- deterministic zone construction and complete constituent lineage;
- bar-volume conservation, binning, value-area/node calculation, and unsupported-volume behavior;
- fidelity separation between inferred bar-volume distribution and future observed profiles;
- actor failure isolation and event-loop non-blocking behavior; and
- no raw market observations in PostgreSQL.

Connected acceptance must prove only what the live run observes. It should reconcile publication
and persistence counters, inspect memory/resource behavior with the Observatory off, verify clean
shutdown, and record any market-session coverage which could not be exercised. London/ETH futures
data may close 9D.4C when the configured rolling inputs flow and the optional actor is active; it
cannot by itself close an opening-range lifecycle transition whose boundary occurred before the
run.

The connected-acceptance configuration initially declared only `READY`, `DEGRADED`, and `WARMING`
for the volatility entity while its classifier can also truthfully emit `STALE` and `UNAVAILABLE`.
The runtime correctly rejected that incomplete health envelope during actor construction. The local
acceptance definition now includes all five outcomes, and offline construction of the complete
`MarketStateEntityActor` succeeds. This was a configuration correction only: thresholds, bands,
confirmation, staleness policy, actor ownership, and publication behavior were unchanged.

Connected acceptance closed on 2026-08-24 using liquid London/ETH futures data. The optional actor
consumed 645 rolling metrics and published 645 valid revisions with zero metric conflicts, stale
inputs, rejected revisions, deferred or pending publications, projection failures, or snapshot
failures. Its configured timer completed 2,560 reconciliation cycles; no evidence crossed the
staleness boundary during the run, so `staleness_revisions=0` is the observed result rather than a
claim that the transition was exercised. The surrounding session runtime produced 64,064 rolling
values with zero calculation failures. Process and cache resources remained bounded, PostgreSQL
stored all 2,261 accepted operational events without retry or rejection, Discord delivered all four
health messages, and controlled shutdown disconnected IB cleanly. One resource warning correctly
reported host disk headroom below its configured threshold. `^SPX.CBOE` was unobserved in this
session, accounting for 17/18 watchlist instruments and 33/34 active streams; that unrelated
session-specific absence does not weaken the futures-backed rolling-state evidence. This closes
9D.4C without closing the separately deferred 9D.3 opening-range boundary transition.

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
4. The first structure baseline uses configurable confirmed-pivot swing detectors with explicit
   scale and source-horizon identity; deterministic compatible alternating swing legs; bounded
   per-horizon pivot-structure state with explicit same-kind, equality, conflict, revision, and
   retention policy; configurable three-bar wick-gap FVG geometry; deterministic
   constituent-preserving derived zones; and a deterministic uniform candle-volume allocation
   across intersected price bins. Confirmed swing truth is never deleted to simplify a current
   chain. Cross-horizon weighting, trendlines, channels, Fibonacci projections, support/resistance,
   order blocks, and supply/demand semantics remain deferred until their own contracts are
   reviewed.
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
