# V3 Canonical Calendar Authority Review

**Status:** Architecture and atomic breaking cutover approved 2026-08-30; implementation review
batch complete; disconnected verification passed; first connected acceptance rejected

**Review order:** 1 of 4

## Purpose

Define one canonical temporal foundation for Markeitech before changing actor ownership or
splitting analytical producers.

The decision question is:

> Under one exact calendar definition, what exchange session, trade date, product phase, and UTC
> boundaries apply to a timestamp or trade-date range?

Every completed bar, session reference, analytical window, rolling context, historical request,
metric, entity, and future agent-facing snapshot depends on that answer being stable and
identifiable.

This began as the discovery and design record which separated facts
`pandas-market-calendars` can author from product-specific temporal meaning Markeitech must own.
The later sections record the approved atomic cutover. Sections labelled pre-batch or proposed are
retained as historical decision evidence and do not describe the current implementation state.

## Pre-Batch Verified State (Historical)

### Existing source and configuration

- The active V2 environment contains `pandas-market-calendars` 5.4.0.
- A configured `provider_calendar` selects one mcal calendar implementation for each Markeitech
  calendar.
- Watchlist instruments bind to a Markeitech `calendar_id`.
- Configuration also carries a timezone, schedule-version label, optional product phases, and
  dated overrides.
- All runtime market timestamps and calculated boundaries are represented internally as UTC
  nanoseconds.

### Duplicated semantic authority

Three runtime components independently construct and evaluate the same `SessionCalendar` logic:

- `SessionStateActor` constructs one calendar set to publish current session transitions;
- `DataAcquisitionActor` constructs another set to resolve symbolic historical windows into UTC
  provider-request bounds; and
- `SessionMetricsActor` constructs a third set to classify completed bars and calculate session,
  window, and rolling measurements.

Equivalent immutable startup configuration makes equivalent answers plausible. It does not make
three independently evaluated copies one canonical authority. The current contracts do not carry
a deterministic calendar-definition digest or effective configuration epoch capable of proving
that all three paths used the same temporal meaning.

### Confirmed mcal break omission

The installed mcal `CME_Equity` calendar reports:

- exchange timezone `America/Chicago`;
- an open at 17:00 on the preceding civil date;
- a maintenance break from 15:15 through 15:30;
- a close at 16:00; and
- UTC schedule columns for `market_open`, `break_start`, `break_end`, and `market_close`.

The current empty-phase `SessionCalendar` path consumes only `market_open` and `market_close`.
Consequently, it classifies the CME maintenance break as `OPEN`. Centralizing the existing helper
without first defining admitted schedule columns would centralize an incomplete interpretation.

### Current CME Group mappings and timezone disagreement

The tracked example currently maps the active CME Group futures contracts as follows:

| Exact contract | Venue | Markeitech calendar | Selected mcal calendar |
|---|---|---|---|
| `ESU6.CME` | CME | `cme_equity` | `CME_Equity` |
| `NQU6.CME` | CME | `cme_equity` | `CME_Equity` |
| `YMU6.CBOT` | CBOT | `cme_equity` | `CME_Equity` |
| `CLV6.NYMEX` | NYMEX | `cme_energy` | `CMEGlobex_EnergyAndMetals` |

Disconnected inspection of installed mcal 5.4.0 verifies:

- `CME_Equity` resolves to `CMEEquityExchangeCalendar`, declares
  `America/Chicago`, and supplies `market_open`, `break_start`, `break_end`, and
  `market_close`;
- `CMEGlobex_EnergyAndMetals` resolves to
  `CMEGlobexEnergyAndMetalsExchangeCalendar`, declares `America/Chicago`, and supplies
  `market_open` and `market_close`; and
- both inspected schedules return their dated boundaries in UTC.

The pre-batch tracked general example configured `America/New_York` for both CME definitions,
which disagrees with their installed mcal calendar timezone. The V3 ES review profile already uses
`America/Chicago` for `cme_equity`, but that local correction does not validate the complete CME
Group mapping.

The first implementation must verify, rather than inherit, whether each exact contract belongs to
the selected mcal definition. In particular, the existing `YMU6.CBOT -> CME_Equity` mapping must
be reviewed against the required CBOT schedule semantics. If one selected mcal calendar cannot
truthfully represent all three equity-index contracts, the implementation must create a separate
canonical definition instead of preserving a convenient shared ID.

### Current identity weakness

The configured schedule-version text is not verified against:

- the installed mcal package version;
- the selected provider-calendar implementation;
- admitted market-time columns;
- break/interruption handling;
- normalized product phases and overrides; or
- an effective configuration epoch.

Historical request, completed-bar, and metric contracts therefore cannot prove which exact
calendar definition produced their trade date, phase, or UTC bounds.

## Required Temporal Vocabulary

The following concepts are distinct and must remain independently named.

### Exchange calendar

The selected mcal calendar and the schedule facts it actually provides. Depending on the selected
calendar, those facts can include:

- valid trade dates;
- regular and special opens and closes;
- holidays and early closes;
- exchange timezone and DST conversion;
- named market-time columns;
- breaks or interruptions; and
- other dated schedule facts explicitly exposed by that calendar.

### Exchange session

One dated schedule row compiled from the selected mcal calendar. It identifies the exchange trade
date and its authoritative dated market-time boundaries.

An exchange session is not every period an analyst may want to study.

### Product phase

A versioned Markeitech-defined segment anchored to exchange-schedule facts or to another explicitly
approved temporal source. Examples may include GTH, RTH, Curb, Asia, London, or New York where the
selected product semantics justify those names.

A phase is not attributed to mcal unless the selected mcal calendar actually defines the relevant
market-time boundary. Product phases, inclusion rules, names, and exceptional overrides remain
Markeitech configuration.

### Analytical window

An independently configured analysis interval. It may be:

- relative to one phase boundary;
- contained within one phase;
- spread across multiple phases;
- intentionally aligned to another market's civil clock; or
- eventually composed across calendars where explicitly approved.

Opening ranges, power hour, a London volume profile, or London plus the first thirty minutes of a
New York cash session are analytical windows. They are not automatically exchange sessions or
product phases.

### Rolling context

A moving analytical horizon defined by an exact input series, timeframe, duration or observation
count, update cadence, alignment policy, coverage policy, and retention bound. Rolling contexts do
not become sessions merely because their duration is expressed in time.

## Proposed Authority Boundary

### mcal is authoritative for admitted exchange-schedule facts

For each configured exchange calendar, mcal should author:

- valid exchange trade dates;
- the selected schedule columns actually supplied by the provider calendar;
- holidays, special opens/closes, and early closes represented by those columns;
- the exchange timezone supplied by the calendar; and
- breaks or interruptions included by the reviewed admission policy.

Markeitech must not silently replace an available mcal exchange fact with a duplicated manual
value.

### Markeitech remains authoritative for product semantics

Markeitech configuration should continue to own:

- the mapping from each exact instrument contract to a canonical `calendar_id`;
- selection of the mcal provider calendar;
- which mcal schedule columns are admitted and how breaks are represented;
- versioned product phases not completely supplied by mcal;
- exceptional dated overrides where a reviewed product requirement cannot be represented by the
  selected mcal calendar;
- analytical-window definitions;
- rolling-context definitions; and
- definition identity, effective time, supersession, and audit metadata.

### UTC and timezone have different responsibilities

All produced instants should remain UTC nanoseconds. This does not eliminate timezone identity.

The exchange timezone is required to interpret:

- exchange trade dates;
- local wall-clock schedule rules;
- phases spanning civil dates; and
- DST transitions.

The exchange timezone should be derived from or validated against the selected mcal calendar. If
an analytical window intentionally uses a different civil clock, that analytical clock timezone
must be explicit and separate from the exchange-calendar timezone.

## Proposed Canonical Definition Identity

One immutable calendar definition should identify at least:

- `calendar_id`;
- calendar engine identity, such as `pandas_market_calendars`;
- exact installed engine/package version;
- exact provider-calendar name and implementation identity;
- admitted schedule columns;
- break and interruption policy;
- exchange IANA timezone and timezone-rule source;
- normalized product-phase definitions;
- normalized dated overrides;
- definition version;
- deterministic definition digest;
- source configuration identity;
- `effective_from_ns` and optional `effective_until_ns`; and
- superseded definition identity when applicable.

A schedule-version label alone is insufficient. The digest must be derived from normalized
definition content so that equal names with unequal meaning fail closed.

Runtime calendar/profile mutation should remain disabled initially. An effective epoch is still
required at startup so downstream evidence can identify the definition which produced it.

## Proposed Runtime Shape

### Retain a pure deterministic evaluator

The useful pure `SessionCalendar` behavior should be retained and corrected as the proposed
`CanonicalCalendar` class rather than replaced wholesale. Given one immutable
`CanonicalCalendarDefinition`, it should deterministically produce:

- exchange-session schedule rows;
- trade-date assignment;
- product-phase bounds;
- open, closed, and break/interruption state;
- next transition; and
- immutable bounded schedule projections in UTC.

It should not connect to a provider, submit historical requests, calculate analytical metrics, or
own mutable runtime policy.

### Exact instance ownership and lifecycle

`CanonicalCalendar` is an immutable class, not an actor.

The validated configuration loader supplies immutable `CanonicalCalendarDefinition` values to
`SessionStateActor` through its actor configuration. During `SessionStateActor` construction, the
actor creates exactly one `CanonicalCalendar` instance per configured `calendar_id`.

```text
Validated configuration
        |
        v
CanonicalCalendarDefinition values
        |
        v
SessionStateActor.__init__()
        |
        +--> CanonicalCalendar("cme_equity")
        +--> CanonicalCalendar("cme_energy")
        +--> other configured calendars
```

`SessionStateActor` is the sole runtime owner of those instances. They exist for that actor's
runtime lifetime and are rebuilt from validated immutable definitions for a new actor/run epoch.
No other actor constructs, owns, mutates, or receives a `CanonicalCalendar` instance.

Other components receive only immutable, definition-identified schedule projections, current
state snapshots, or transition events published by `SessionStateActor`. A consumer which needs
additional bounded date coverage requests that projection from `SessionStateActor`; it does not
create another calendar.

### Do not share one mutable Python calendar object across actors

One authority does not require every actor to call one shared mutable object synchronously.
Consumers should receive immutable, versioned calendar definitions and bounded schedule
projections from the canonical boundary.

High-rate completed-bar classification should not require an actor round trip for every bar.
Consumers should normally use an immutable projection covering their accepted timestamps. A typed
request/reply path may extend missing coverage, but it should not become a per-bar hot path.

### Keep query, snapshot, and event semantics separate

#### Point-in-time query or schedule projection

Answers which trade date, exchange session, product phase, and UTC boundaries apply to a supplied
timestamp or trade-date range under one exact definition epoch.

This is required for historical bar classification and historical request planning.

#### Current-state snapshot

Provides a complete immutable current view for late or restarting consumers, including definition
identity, as-of time, current phase/state, per-calendar revision, and explicit unavailable or
conflicting results.

#### Transition event

Records a meaningful change such as definition activation, phase transition, trade-date change,
or admitted dated correction. An event is a transition fact, not a substitute for a complete
snapshot or historical query.

## Historical Request Boundary Consequence

The current acquisition actor resolves symbolic meanings such as previous RTH, current overnight,
or a phase-relative analytical window using its private calendar instance.

The intended later boundary should be:

```text
Analytical capability requirement
        |
        v
Canonical calendar/session facts
        |
        v
HistoricalEvidencePlanner
        |
        v
Exact immutable UTC request plan
        |
        v
DataAcquisitionActor
        |
        v
Provider request execution and lifecycle
```

The calendar authority supplies exchange facts. `HistoricalEvidencePlanner` owns resolution of the
requesting capability's explicit evidence basis, including exact completed-observation count,
exact UTC range, relative civil-time span, completed trading-session count, or trading-calendar
span. `DataAcquisitionActor` owns exact-request validation,
deduplication, provider budgets, pacing, queueing, retries, cancellation, execution, and lifecycle.
It must not decide what an analytical phase or window means.

This ownership move is downstream of the canonical calendar contract. It is not part of the first
shadow-parity batch.

## Superseded First Reviewable Batch Proposal (Historical)

### Name

**Canonical Calendar Contract and Shadow Parity**

### Intended changes

- introduce immutable calendar-definition identity and deterministic digest behavior;
- fully configure every CME Group calendar family currently required by `ESU6.CME`, `NQU6.CME`,
  `YMU6.CBOT`, and `CLV6.NYMEX`;
- verify every exact contract-to-calendar mapping instead of treating the current mapping as
  accepted merely because it loads;
- derive or strictly validate both active CME calendar timezones against the selected installed
  mcal calendars;
- explicitly admit the required mcal schedule columns;
- represent mcal breaks and interruptions honestly;
- distinguish exchange sessions, product phases, analytical windows, and rolling contexts in
  contracts and tests;
- continue emitting all temporal boundaries as UTC nanoseconds;
- build deterministic calendar fixtures; and
- compare the proposed canonical interpretation with each of the three current evaluator paths.

### Original runtime posture

This shadow-only posture was superseded when Markeitect approved one atomic breaking cutover. It is
retained here to explain why the earlier text and fixtures refer to parity. The original proposal
would not:

- alter the canonical session state used by normal runtime operation;
- change provider request bounds;
- change completed-bar admission;
- change metric values;
- issue an IB request;
- require a connected run;
- split an actor;
- change Watchlist behavior; or
- enable runtime calendar mutation.

### Required offline fixtures

- separate fixtures for every accepted CME Group canonical definition used by ES, NQ, YM, and CL;
- exact contract-to-calendar mapping acceptance and rejection;
- rejection of the current `America/New_York` mismatch for mcal calendars which declare
  `America/Chicago`;
- ordinary open and closed periods;
- CME maintenance breaks;
- weekends and exchange holidays;
- early closes;
- DST transitions in both directions;
- phases spanning the prior civil date;
- configured exceptional overrides;
- invalid or mismatched exchange timezone;
- equal version names with unequal definition content;
- stable digest reproduction; and
- parity or explicit divergence across all current calendar consumers.

The current maintenance-break disagreement should be reported as intentional corrective
divergence, not normalized away to make parity appear green.

## Original Non-Goals (Historical)

- no `SessionStateActor` cutover;
- no new analytical window;
- no rolling-metric change;
- no `SessionMetricsActor` split;
- no Watchlist or capability-manager change;
- no provider or adapter change;
- no historical request concurrency or retry change;
- no persistence schema;
- no hot runtime calendar mutation;
- no raw market-data retention;
- no semantic market event, agent behavior, recommendation, or execution; and
- no Nautilus composite-bar or native-indicator cutover.

## Approved Atomic Cutover Implementation State

The review batch now implements one breaking cutover with no shadow or legacy calendar authority:

- system schema 20 loads the dedicated schema-3 `v2/config/market-calendars.toml` catalog and
  rejects inline definitions, old dated overrides, and older system/catalog schemas;
- the loader pins mcal 5.4.0, provider class, provider timezone, admitted columns, product phases,
  source/correction identity, deterministic digests, and bounded default projection requests
  before actor construction;
- the reusable calendar catalog contains no concrete instrument contracts; the runtime watchlist
  is the single startup binding authority, with current bindings `ES/NQ -> cme_equity`,
  `YM -> cbot_equity`, and `CL -> cme_energy`;
- CME/CBOT definitions expose overlapping `GLOBEX`, `ASIA`, `LONDON`, and `NEW_YORK` product phases;
  these phases do not create or constrain analytical windows;
- `SessionStateActor` alone constructs `CanonicalCalendar` instances and publishes typed
  definition-identified `CalendarTransition` and bounded immutable `CalendarProjection` data;
- consumers hold `CalendarProjectionView` values which cannot call mcal or author temporal rules;
- `HistoricalEvidencePlannerActor` resolves symbolic demand into exact UTC
  `HistoricalRequestPlan` data and refreshes projections as calendar transitions occur;
- `DataAcquisitionActor` receives only exact plans and retains concrete provider limits,
  deduplication, queueing, pacing, retry, cancellation, execution, and lifecycle ownership;
- `SessionMetricsActor` classifies completed bars at `interval_end_ns - 1`, resolves historical and
  analytical windows from projections, refreshes those projections on calendar transitions, and
  has no local evaluator fallback;
- `EvidenceHealthActor` consumes typed current transitions and uses a projection only to bootstrap
  current context;
- `OperationalPersistenceActor` stores calendar transitions through the existing operational
  ledger; projections and schedule rows remain transient; and
- the legacy `SessionCalendar`, `SessionStateEvent`, signal, copied calendar payloads, and shadow
  comparison path are removed.

Direct inspection of pinned mcal 5.4.0 confirmed that the inherited CBOE 2026 holiday closures and
early close already come from `CBOE_Index_Options`; no duplicated dated holiday maintenance was
introduced. That provider still does not supply the overnight GTH phase, so GTH/RTH/CURB remain
explicitly provisional, separately timezoned product-phase configuration.

Pinned mcal still exposes the obsolete CME Equity 15:15-15:30 America/Chicago regular pause. The
catalog therefore carries one structural correction sourced to CME's 2021-06-21 notice, effective
trade date 2021-06-28, and scoped to ES, NQ, and YM. Pre-effective rows are unchanged. Exact
matches are removed and recorded as `APPLIED`; a future provider base which already conforms is
recorded as `BASE_ALREADY_CONFORMS`; any unequal provider schedule fails as `CONFLICT`. The source
URL and retrieval status are part of the definition digest. Stable response bytes were unavailable
in this environment, so the catalog records `HASH_UNAVAILABLE` instead of inventing a digest.

Disconnected verification currently consists of the full non-PostgreSQL test suite plus Ruff. It
covers ordinary/closed periods, source-effective CME correction, exchange-state/product-phase
separation, CME/CBOT identity, CL's exact provider calendar, watchlist-owned bindings, regional
phase overlap, weekend, DST, CBOE holiday and early-close behavior, immutable projections, strict
typed contracts, planner/acquisition ownership, persistence conversion, actor composition, and
both tracked system profiles. The first connected IB run on 2026-08-30 rejected the cutover before
historical planning: the default 120-day lookback crossed CME early-close rows represented by
pinned mcal as `break_start == break_end == market_close`, and the projector attempted invalid
zero-duration exchange segments. Projection consumers then retried without receiving a bounded
failure response. No connected IB run has accepted this cutover.

## Remaining Gates

The sole-owner cutover, bounded projections, historical planning boundary, and current consumer
migration are implemented. The following remain separate work:

1. Add the full late-consumer current-state snapshot/buffer/reconcile protocol proposed in the
   SessionState role review; the present transition plus projection contracts do not claim it.
2. Carry canonical calendar definition identity through completed-bar and metric subject identity
   wherever downstream conflict detection requires it.
3. Split the combined metric actor without multiplying calendar authorities.
4. Repeat the bounded connected acceptance owned by Markeitect after correcting the rejected first
   run; do not claim provider-session or live transition acceptance before it passes.
5. Correct zero-duration provider breaks before claiming bounded or arbitrary-range projection
   acceptance. The 2026-08-30 connected run proved the configured default projection is affected:
   its 120-day lookback crossed CME early-close rows whose admitted
   `break_start == break_end == market_close`. The projector attempted zero-length `BREAK` and
   trailing `OPEN` segments and failed closed.
6. Replace the resulting unbounded projection retry loop with an explicit failure response,
   bounded retry policy, and honest system-readiness dependency.

Before increasing historical concurrency or retries, the separate Nautilus/IB callback-correlation
defect must be resolved. Before changing shutdown behavior, cancellation must be fenced so it
cannot dispatch new queued provider work while the actor is stopping. Those issues are recorded
constraints, not reasons to expand this first calendar batch.

## Decision Record

### Accepted scope direction

On 2026-08-30, Markeitect approved the authority direction, full current CME Group scope, dedicated
catalog, explicit product phases, source-composed CME correction, separate historical planner, and
one atomic breaking cutover. The following original questions are retained as the accepted decision
basis:

1. **mcal authority:** Accept mcal as the exchange-schedule source for every fact explicitly
   admitted from the selected calendar, while keeping product phases and analytical windows under
   Markeitech configuration?
2. **Breaks:** Admit mcal-provided breaks and interruptions as canonical closed/non-trading
   intervals rather than treating the entire open-to-close span as continuously open?
3. **Timezone:** Derive or strictly validate the exchange timezone against the selected mcal
   calendar while keeping all output instants in UTC?
4. **Definition identity:** Require exact mcal version, admitted columns, normalized overlays,
   deterministic digest, and startup effective epoch on the canonical definition?
5. **Update policy:** Keep calendar/profile definitions startup-only for now, and treat a future
   mcal package update or definition change as an explicit reviewed definition revision rather
   than silently reinterpreting earlier evidence?
6. **Cutover:** Replace the proposed shadow sequence with one atomic cutover which removes the old
   authority and leaves no legacy fallback?

### Post-implementation catalog correction

On 2026-08-30, Markeitect rejected concrete contract mappings inside the reusable calendar
catalog. The catalog now owns temporal definitions only. `[[watchlist.members]]` owns each runtime
instrument's `calendar_id`; correction product roots remain only as source-bounded applicability
metadata. CME/CBOT calendars now include overlapping `ASIA`, `LONDON`, and `NEW_YORK` phases in
addition to `GLOBEX`. Exact contracts can therefore roll or be added without editing temporal
definitions.

## Advisory Basis

This proposal reconciles read-only consultations from the architecture-boundaries,
data-quality/lineage, event-driven-architecture, and NautilusTrader advisors. All four selected the
calendar authority as the first dependency. NautilusTrader supplies appropriate actor, clock,
typed-data, native bar, cache, and provider-request mechanics, but the installed 2.0.0rc3 runtime
does not supply a general exchange-calendar/session authority which replaces the mcal-backed
Markeitech semantics.

The advisor conclusions are inputs to Markeitect's review. They do not approve this proposal.
