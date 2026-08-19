# V2 Baseline Metric Contracts

**Status:** Stage 9C is implemented and live-accepted as of 2026-08-19.

## Purpose

Stage 9C turns provider observations and Stage 9B historical batches into reusable deterministic
measurements. This first slice defines the contract boundary before choosing formulas. It prevents
an EMA, opening range, VWAP, volatility measure, or any later analytical value from becoming an
unversioned number whose inputs, settings, health, or meaning cannot be reconstructed.

The contracts are intentionally formula-neutral. The accepted metric candidates remain in the
market-intelligence roadmap, but none enters the runtime until its decision question, formula,
inputs, validation reference, and resource cost are reviewed with Markeitect.

## Non-Negotiable Rules

1. A metric answers a named decision question. Familiarity or popularity is not sufficient reason
   to calculate it.
2. Analytics never call IB or Nautilus acquisition methods. A metric reuses the accepted
   `CapabilityFeedRequirement` and `CapabilityHistoricalRequirement` contracts.
3. Historical observations remain transient inputs. This contract creates no raw-data persistence.
4. Metric identity is `(metric_id, version)`. Formula changes require a new metric version.
5. Parameter identity is the metric identity plus `parameter_version` and `effective_from_ns`.
6. Every parameter is typed, scoped, bounded, sourced, and explicitly static or dynamic.
7. Static means startup-only and operator/config reviewed. It does not mean permanently hard-coded.
8. Dynamic means eligible for a future policy-controlled runtime change inside declared bounds. It
   does not authorize a model or agent to mutate runtime state today.
9. Every output carries event-time and processing-time fields, health, fidelity, parameter version,
   source, evidence lineage, and an explicit missing reason when null.
10. Retained state and update rate are bounded by contract. No implementation may grow state from
    live observations without a declared limit.
11. Numerical updates are not automatically semantic events or PostgreSQL records.
12. One unavailable metric degrades only its own dependents. It does not stop acquisition or
    unrelated capabilities.

## Contract Model

### Metric Definition

`MetricDefinition` is an immutable, versioned description of one analytical meaning.

| Field | Meaning |
|---|---|
| `metric_id`, `version` | Stable identity and formula-contract revision |
| `decision_question` | The bounded market question the value helps answer |
| `implementation_id` | Stable implementation/formula reference |
| `value_kind`, `unit` | Output type and measurement unit |
| `cadence` | Observation, completed bar, timer, session transition, or dependency readiness |
| `horizon` | Human-readable analytical horizon; not an implicit lookback |
| `nullable` | Whether honest missing output is representable |
| `retained_state` | None, latest, rolling window, or current session |
| `fidelity` | Maximum intended output fidelity |
| `failure_behavior` | Emit null, hold a stale prior value, or suppress output |
| `warmup` | Minimum observations/time and dependency-readiness rule |
| `resources` | State, cadence, and output-age bounds |
| `live_inputs` | Existing acquisition feed requirements |
| `historical_inputs` | Existing Stage 9B historical requirements |
| `metric_inputs` | Exact metric identities required upstream |
| `parameters` | Complete typed parameter schema |
| `event_uses` | Reviewed future semantic-event consumers, if any |

A definition must declare at least one direct acquisition input or metric dependency. It cannot
depend on itself. Duplicate logical feeds, dependencies, parameters, and event uses are rejected.

### Acquisition Boundary

`MetricDefinition.acquisition_capability()` converts only direct live and historical inputs into the
existing acquisition `CapabilityDeclaration`. It returns no declaration for a metric built solely
from other metrics.

This preserves one data-ownership path:

```text
Metric definition
    -> capability declaration
    -> DataAcquisitionActor / Stage 9B execution
    -> transient observations or historical batch
    -> future metric runtime
```

The metric layer does not duplicate feed kinds, historical windows, provider selectors, pacing, or
request execution.

### Parameter Definition And Set

`MetricParameterDefinition` declares:

- identity and meaning;
- scalar type and unit;
- documented default and scope;
- source;
- `dynamic` eligibility and mutability class;
- numeric minimum/maximum and optional step; or
- an explicit allowed-value set for text/boolean parameters.

Dynamic numeric parameters require a positive step and policy-controlled runtime mutability.
Static parameters require startup-only mutability. Both remain configurable and validated.

`MetricParameterSet` is the immutable effective configuration for one metric version. It carries a
monotonic parameter version, UTC nanosecond effective time, source, complete values, and optional
superseded version. The registry requires every declared parameter exactly once and rejects
unknown, missing, mistyped, non-finite, or out-of-envelope values.

This is optimization-ready metadata, not an optimization mechanism. A later policy layer must own
authorization, intents, audit, application boundaries, expiry, and rollback.

### Metric Value

`MetricValue` is the provider-neutral output envelope. It includes:

- metric and parameter versions;
- instrument and optional session identity;
- typed scalar value and unit;
- effective, observed, received, calculated, and published UTC nanosecond timestamps;
- health and fidelity;
- source and evidence references;
- explicit missing reasons; and
- revision.

A null value must explain why it is absent, and its definition must permit nulls. Unavailable,
unsupported, and failed values cannot carry a misleading number. The registry validates output type,
unit, nullability, and fidelity compatibility against the exact definition version.

### Registry

`MetricRegistry` is immutable after construction. It:

- rejects duplicate metric identities;
- requires all metric-to-metric dependencies to be registered;
- returns definitions in deterministic identity/version order;
- supports exact version lookup;
- makes latest-version lookup explicit rather than silently upgrading a consumer;
- validates complete parameter sets; and
- validates values against their exact contracts.

The first implementation is in-process because Stage 9C has one runtime. A durable or distributed
registry is not justified yet. PostgreSQL may later audit activated definitions and parameter
versions, but it is not the live registry or message bus.

## Persistence And Publication

This slice adds no PostgreSQL table and no Nautilus message type.

Future runtime behavior must distinguish:

| Information | Default handling |
|---|---|
| Raw quote/trade/bar input | Bounded live memory; never PostgreSQL raw storage |
| Historical response | Transient warmup only |
| Current metric value | Capability-owned bounded memory and native bus update |
| Parameter activation | Operational audit after mutation policy exists |
| Metric readiness/health transition | Operational/semantic audit as approved |
| Compact prior-session summary | Stage 9D persistence decision |
| Every numerical metric update | Not a PostgreSQL event and not a Discord message |

## First Runtime Slice

The first Stage 9C runtime batch implements only the smallest reusable metric family:

1. choose exact decision questions from the accepted catalog;
2. define formula and parameter registry entries;
3. bind direct live and historical requirements;
4. implement an event-driven metric owner with bounded rolling state;
5. publish typed values without semantic-event noise;
6. expose readiness and dimensional health;
7. compare live values with an independent operator reference; and
8. add persistence only for an explicitly approved compact summary.

No trading threshold, instrument preference, or durable numerical storage policy is selected by
this runtime slice.

## First Pure Metric Family: Quote Quality

The first reviewed calculation family establishes formula correctness without changing the live
node. Native Nautilus `QuoteTick` remains quote truth. The metric layer receives only a transient
calculation input and does not create a second durable quote model.

The family contains three version-one definitions:

| Metric | Formula | Unit | Decision question |
|---|---|---|---|
| `quote.midpoint` | `(bid + ask) / 2` | price | What is the center of the current valid two-sided quote? |
| `quote.spread.absolute` | `ask - bid` | price | How wide is the current valid quote in price units? |
| `quote.spread.relative` | `(ask - bid) / midpoint` | ratio | How wide is the quote relative to its midpoint? |

Price arithmetic uses `Decimal`. A relative spread remains a ratio; presentation code may render
it as a percentage later without changing its analytical identity.

### Input And Health Rules

- `HEALTHY` evidence produces `READY` derived values.
- `DEGRADED` evidence may still produce values, but health is `DEGRADED` and fidelity is `PARTIAL`.
- `NOT_EVALUATED`, `DORMANT`, `STALE`, `UNAVAILABLE`, and `UNSUPPORTED` evidence produces explained
  nulls rather than reusing an old quote.
- Missing, non-finite, or non-positive sides and crossed quotes produce `FAILED` explained nulls.
- A locked quote is valid and produces zero absolute and relative spread.
- Event, receive, calculation, and publication ordering is validated.

These are evidence and arithmetic invariants, not trading thresholds. The caller must explicitly
provide `minimum_update_interval_ms` and `maximum_output_age_ms` through
`QuoteMetricCatalogPolicy`; the catalog defines no hidden defaults. Runtime TOML now owns these
policies through `[metrics.quote_quality]`:

- `minimum_update_interval_ms = 250`, bounding publication to at most four metric snapshots per
  second per instrument;
- `maximum_output_age_ms = 15000`, carried in the metric resource contract rather than interpreted
  as a trading threshold;
- explicit parameter version, demand priority, and bounded demand/evidence retry intervals; and
- capability-based scope (`top_of_book`), so instruments are selected from watchlist configuration
  rather than hard-coded in the actor.

Every value remains configurable and versioned. Later optimization may change only parameters
explicitly admitted by an approved mutation policy.

### Runtime Data Flow

1. `QuoteQualityMetricsActor` declares one analyzer-owned quote observation demand per selected
   instrument.
2. `DataAcquisitionActor` validates it and sends it through the existing `DemandReconciler`.
   Identical watchlist and analyzer requirements collapse into one provider subscription.
3. The metric actor consumes native Nautilus `QuoteTick` callbacks; it does not receive republished
   raw quotes through Markeitech signals.
4. The actor requests an explicit current evidence snapshot and also listens for later evidence
   transitions. Bounded retry makes startup order irrelevant.
5. Each eligible quote becomes a minimal transient `QuoteMetricInput`, is calculated with exact
   `Decimal` arithmetic, validated against the immutable registry, and published as `CustomData`
   under `markeitech.metric.value`.
6. The actor retains only current evidence, publication timestamps, and revision counters. It does
   not retain raw quote history.

Analyzer demand is operationally audited. Evidence snapshots are request/reply state transfer and
are deliberately not persisted as semantic transitions. Raw quotes and numerical metric updates
remain outside PostgreSQL and Discord.

The evidence snapshot protocol prevents a late-starting consumer from waiting for a future health
transition. Until evidence is available, quotes produce honest `WARMING` explained nulls rather
than unqualified values. Demand and evidence retries use Nautilus clock timers, not sleeps or actor
start sequencing.

### Current Non-Goals

- no numerical metric-value PostgreSQL rows;
- no logs or Discord output;
- no spread-quality trading threshold; and
- no option-specific interpretation.

## Live Acceptance

The 2026-08-19 live run proved:

- native IB quotes reached both Watchlist and quote-metric consumers through one provider stream
  per instrument;
- 2,111 received quotes minus 1,466 cadence suppressions produced 645 calculation cycles and
  exactly 1,935 metric values across the three configured quote-quality metrics;
- evidence qualification reconciled exactly to those values: 981 `HEALTHY`, 24 `DEGRADED`, 924
  `DORMANT`, and 6 `STALE`, with no unqualified `NOT_EVALUATED` publication;
- closed-session instruments remained honest explained-null observations rather than fabricated
  healthy measurements;
- the metric actor reported zero calculation or publication failures;
- PostgreSQL stored 464 operational records plus 3 system-health records, exactly matching the
  persistence runtime's 467 accepted and stored records; and
- the node, acquisition, historical probes, Discord runtime, metric runtime, and persistence
  runtime all stopped cleanly.

Raw quotes and numerical metric values remain intentionally transient. PostgreSQL contains their
operational lifecycle and system-health audit, not a duplicate market-data store.

Stage 9C is closed. The next product slice is Stage 9D: reviewed session entities, bounded rolling
state, and durable summaries.
