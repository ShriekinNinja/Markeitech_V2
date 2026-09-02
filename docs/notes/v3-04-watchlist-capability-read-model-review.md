# V3 Watchlist, Capability, And Intelligence Read-Model Review

**Status:** Proposed review record; not accepted architecture, an implementation plan, or
implementation approval

**Review order:** 4 of 4

**Dependencies:** Canonical calendar/session identity is implemented in the uncommitted calendar
cutover. Canonical completed-bar ownership, complete metric subject identity, and explicit
analytical producer ownership remain prerequisites before a symbol-level intelligence snapshot can
claim completeness.

## Purpose

Decide whether `WatchlistActor` should become:

1. a read-only snapshot of every metric and piece of intelligence known about a symbol; or
2. the manager of the analytical metrics required for each symbol.

The proposed answer is **neither**. Both desired capabilities are useful, but each represents a
different authority from watchlist membership and operational observation readiness.

This review separates three responsibilities:

- observation-universe membership and baseline observation readiness;
- analytical capability activation and dependency management; and
- read-only instrument intelligence projection.

## Current Verified State

`WatchlistActor` is not currently empty. It owns meaningful static operational behavior.

It currently:

- receives the configuration-owned watchlist membership;
- publishes versioned static membership and lifecycle facts;
- expresses baseline `top_of_book` and `watchlist_last` demand;
- waits for and interprets acquisition subscription outcomes;
- registers independent native Nautilus quote and bar consumers;
- retries failed local consumer attachment;
- retains the latest bid, ask, and five-second-bar-derived last value;
- retains native event timestamps;
- protects latest state from out-of-order replacement;
- tracks bounded observation and out-of-order counters;
- distinguishes consumer registration from observation completion;
- reports whether each configured member produced its required baseline observations; and
- releases its static demand during controlled shutdown.

Its internal immutable `WatchlistSnapshot` is used by the actor's own lifecycle and logging paths
and by tests. Repository inspection found no public runtime request/reply consumer for that
snapshot.

`WatchlistActor` does not currently:

- consume `MetricValue`;
- possess the metric definition registry;
- know which analytical profiles or timeframes are enabled;
- expand analytical metrics into historical requirements;
- calculate indicators or session measurements;
- maintain entities or semantic events;
- serve an agent-facing intelligence read model; or
- authorize dynamic analytical changes.

## Why The Two Proposed Options Should Be Separated

### Option A: Watchlist as an all-metrics symbol snapshot

The desired read-only view is valuable, but it is not watchlist truth.

An honest snapshot of “everything the system knows about ES” must distinguish:

- enabled from disabled capabilities;
- unconfigured from requested-but-warming capabilities;
- missing from failed or unavailable outputs;
- one-minute from five-minute, fifteen-minute, hourly, daily, or other timeframe values;
- one analytical profile, phase, or window from another;
- active from stale or superseded parameter and configuration epochs;
- independent producer source epochs and revisions;
- a coherent as-of cohort from values observed at materially different times;
- expected values from unexpected extra or duplicate producers; and
- canonical evidence from inferred evidence and agent interpretation.

The current generic `MetricValue` identity and producer population cannot answer all of those
questions. Adding metrics to `WatchlistActor` now would create a second latest-value selection and
staleness authority without a defensible completeness contract.

**Disposition:** retain the requirement, but implement it later as a dedicated read-only
instrument-intelligence projection.

### Option B: Watchlist as required-metric manager

Managing required metrics means owning:

- capability identity and version;
- activation and deactivation;
- instrument/group applicability;
- analytical profiles, timeframes, and windows;
- dependency expansion;
- live feed and historical evidence requirements;
- expected output population;
- provider and runtime resource budgets;
- priority, leases, expiry, and release;
- parameter activation and allowed mutation;
- lifecycle, failures, and recovery; and
- future operator or agent authorization.

That responsibility is materially different from deciding which instruments belong to the
observation universe.

Combining them would recreate a super-actor and collapse two concepts the accepted adaptive data
plane deliberately keeps separate: observation-universe membership and active analytical
capabilities.

**Disposition:** reject capability-management authority inside `WatchlistActor`. Preserve it as a
separate future analytical capability manager.

## Proposed Responsibility Boundaries

### WatchlistActor: observation universe and operational readiness

`WatchlistActor` should own:

- configured bootstrap membership;
- future approved runtime membership claims, when dynamic membership is reopened;
- exact instrument/calendar binding;
- owner/claim identity and membership lifecycle;
- protected baseline versus optional membership;
- the baseline observation capabilities required to establish operational visibility;
- acquisition demand for those baseline observation capabilities;
- local native consumer attachment state;
- acquisition outcome and first-observation state;
- latest observation timestamps and bounded operational counters;
- immutable membership and operational-readiness snapshots; and
- release of its own claims without canceling another consumer's shared provider demand.

It must not own:

- analytical formulas or metric definitions;
- analytical capability authorization;
- session, window, or rolling calculation;
- canonical completed bars;
- analytical parameter mutation;
- historical semantic-window resolution;
- provider pacing or execution;
- all-metrics latest-state selection;
- market interpretation;
- agent policy; or
- trade recommendation or execution.

The current latest bid/ask/bar-derived-last retention may be retained provisionally as an
operational observation proof. Whether those values remain useful after evidence health and
canonical metric/read-model paths are complete should be reviewed separately. They should not be
removed incidentally during the capability or metric split.

### Analytical capability manager: active analysis requirements

A separate stable responsibility should eventually own:

- the catalog of approved analytical capabilities and versions;
- static startup activation per instrument or group;
- exact analytical profile, timeframe, period, window, and parameter binding;
- dependency expansion into canonical bars, session projections, live feeds, and historical
  evidence;
- expected output identities and producer ownership;
- activation lifecycle: requested, accepted, preparing, active, partial, failed, disabled,
  released, expired, or unsupported;
- resource and provider-cost estimates;
- configuration and future policy bounds; and
- reconciliation between desired and observed capability state.

It must not:

- connect to IB;
- execute provider requests;
- calculate the metrics it activates;
- rewrite canonical evidence;
- decide Watchlist membership implicitly; or
- grant an agent arbitrary configuration authority.

Initially, this responsibility should consume reviewed startup configuration only. Dynamic
operator and agent intents remain a later governance stage with explicit authorization, budgets,
leases, audit, expiry, and rollback.

### Instrument intelligence read model: what the system knows

A separate read-only projector should eventually consume canonical:

- Watchlist membership and operational readiness;
- session state and calendar definition identity;
- evidence health;
- completed-bar state or references where required;
- `MetricValue` streams;
- entity revisions;
- future semantic events;
- capability activation lifecycle; and
- producer health and source watermarks.

It should answer bounded questions such as:

> What canonical evidence and intelligence is available for ES at as-of time T under configuration
> epoch C, and which expected capabilities are disabled, warming, partial, stale, failed,
> unavailable, or conflicted?

It owns projection and completeness accounting only. It must not:

- recalculate metrics;
- infer missing values;
- activate capabilities;
- request provider data;
- mutate Watchlist membership;
- convert an interpretation into canonical truth;
- hide missing or stale producers; or
- treat snapshot construction as an agent decision.

## Proposed Instrument Intelligence Snapshot Contract

Before implementation, the snapshot needs an explicit named consumer question and expected
population.

It should carry at least:

- stable snapshot and request identity;
- projector identity and version;
- generated-at and requested as-of timestamps;
- Watchlist membership revision;
- exact instrument contract and venue;
- requested capability/profile/timeframe/window scope;
- active configuration and calendar-definition epochs;
- expected producer and output manifest;
- values and entities with complete canonical subject identity;
- disabled, unconfigured, warming, missing, stale, partial, failed, unavailable, and conflicted
  entries;
- source owner, source epoch, source revision, and watermark for every included value;
- evidence health, fidelity, and age;
- maximum observed cross-value temporal skew;
- response completeness and truncation;
- explicit unavailable owner responses; and
- schema version.

The projector must know which owners are expected. Waiting a fixed duration and counting whatever
responses arrive is not a completeness contract.

## Proposed Control Flow

### Static startup posture

```text
Checked-in startup configuration
        |
        +--> WatchlistActor: bootstrap membership and baseline observation demand
        |
        +--> Analytical capability manager: reviewed active analytical capabilities
                                      |
                                      v
                         Canonical dependency declarations
                                      |
                                      v
                      Calendar planner / DataAcquisitionActor
                                      |
                                      v
                         Independent analytical producers
                                      |
                                      v
                       Instrument intelligence read model
```

The two configuration consumers have distinct meanings. Watchlist membership does not imply every
analysis is enabled, and activating an analysis does not automatically authorize adding an
unapproved instrument to the observation universe.

### Future governed runtime posture

A later operator or advisory agent may propose:

- adding or removing an optional observed instrument;
- activating or reconfiguring an approved capability;
- requesting bounded additional historical evidence; or
- applying temporary focus.

Those proposals require a separate deterministic governor. The governor may accept, modify, queue,
reject, expire, or revoke them according to authorization, entitlements, configuration envelopes,
provider limits, and aggregate resource budgets.

Neither Watchlist nor the agent may bypass that policy by publishing raw acquisition or metric
commands directly.

## Relationship To DataAcquisitionActor

The boundaries remain:

- Watchlist expresses approved baseline observation demand;
- capability management expresses approved analytical dependencies;
- historical planning resolves temporal semantics into exact UTC plans;
- `DataAcquisitionActor` validates, deduplicates, budgets, paces, queues, executes, and reports
  provider lifecycle; and
- native Nautilus paths deliver observations directly to approved consumers.

Shared logical demand should continue to collapse into one provider subscription or request where
the complete provider request is equal. Releasing one Watchlist or analytical claim must not cancel
another owner's data.

## Migration Direction

### Stage A: freeze the current Watchlist boundary

- preserve current static membership and baseline observation behavior;
- document its actual runtime consumers and internal-only snapshot;
- make no dynamic membership change;
- make no analytical capability change; and
- do not remove latest observation state during unrelated refactoring.

### Stage B: complete analytical producer identity

- accept canonical calendar/session identity;
- accept canonical completed-bar ownership;
- split metric responsibilities;
- complete metric subject identity;
- establish global producer and expected-output manifests; and
- prove source-scoped recovery and partial failure.

### Stage C: introduce startup-static capability management

- move active analytical capability selection into one explicit validated responsibility;
- preserve existing provider demand and analytical calculations;
- expose desired versus observed activation state;
- maintain startup-only mutability; and
- leave operator/agent runtime control disabled.

### Stage D: introduce the read-only instrument intelligence projection

- consume canonical values rather than private actor state;
- account for the complete expected population;
- expose partial, stale, unavailable, and conflict outcomes honestly;
- prove bounded as-of snapshot behavior; and
- leave all calculations and provider control in their canonical owners.

### Stage E: revisit dynamic membership and capability intents

Only after governance, resource budgets, durability, restart, expiry, and revocation are accepted:

- reopen dynamic Watchlist membership;
- enable operator intents first;
- prove lease and shared-claim behavior;
- add agent requests only after authority and abstention gates; and
- preserve protected bootstrap membership independently from optional runtime claims.

## Acceptance Evidence

### Watchlist boundary

- complete configured membership identity;
- membership snapshot and lifecycle accounting;
- baseline demand and local consumer readiness remain separate;
- first-observed, degraded, recovered, and released states;
- shared subscription safety;
- out-of-order observation protection;
- bounded state and counters;
- quiet or closed markets do not become false acquisition failures; and
- no analytical metric or read-model calculation inside Watchlist.

### Capability management

- one active owner per capability identity and scope;
- exact dependency expansion;
- enabled, disabled, preparing, active, partial, failed, unsupported, and released accounting;
- invalid instrument/profile/timeframe/parameter combinations fail closed;
- duplicate desired-state intents are idempotent;
- aggregate provider and runtime budgets are enforced before retaining work;
- no direct provider call; and
- static configuration behavior before any runtime mutability.

### Intelligence read model

- exact expected producer/output manifest;
- no timeframe, profile, window, calendar, or parameter-epoch collision;
- late owner startup and source snapshot reconciliation;
- missing owner versus empty owner versus lost/suppressed response distinction;
- coherent as-of and maximum-skew reporting;
- disabled, warming, stale, partial, unavailable, conflict, and truncated results;
- bounded snapshot state and request rate;
- no metric recomputation or fallback invention; and
- one named downstream use reviewed separately for final evidence fitness.

## Explicit Non-Goals

- no dynamic membership in the current data-processing foundation batch;
- no agent or model control;
- no arbitrary runtime configuration access;
- no metric calculation inside Watchlist or the read model;
- no direct IB access outside acquisition;
- no raw market-data persistence;
- no new database or message broker;
- no semantic event, opportunity, recommendation, or execution behavior; and
- no claim that a read-only snapshot is fit for trading merely because it is structurally
  complete.

## Decisions For Markeitect Review

1. Reject both proposed Watchlist expansions as combined responsibilities?
2. Preserve `WatchlistActor` as observation-universe membership, baseline demand, local consumer
   attachment, and operational observation-readiness owner?
3. Review the current latest bid/ask/bar-derived-last state later rather than deleting or elevating
   it during the metric split?
4. Create a separate analytical capability manager, initially startup-static, after metric
   producer identity is accepted?
5. Create a separate read-only instrument intelligence projector after expected metric population
   and complete subject identity exist?
6. Keep dynamic Watchlist/capability intents deferred until a separate policy, resource,
   authorization, expiry, audit, and recovery stage?
7. Require an explicit expected-owner/output manifest rather than treating whatever arrives before
   a timeout as “all intelligence”?

## Advisory Basis

Architecture, data-quality/lineage, event-driven-architecture, and NautilusTrader consultations
agree that the two proposed Watchlist options represent separate responsibilities. They recommend
retaining Watchlist as the operational universe/readiness owner, assigning analytical activation
to a separate capability-management boundary, and assigning symbol-level canonical intelligence
to a separate read-only projector after producer identities stabilize.

The advisor conclusions are inputs to Markeitect's review. They do not approve this proposal.
