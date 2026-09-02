# V2 Adaptive Market-Data Plane

**Status:** Stage 8C is complete, including live native multi-actor delivery and subscription
lifetime proof against IB.

**Scope:** The intended live market-data and analysis control model. This document defines the
destination and ownership boundaries before subscription code is added. It does not approve a
fixed instrument list, warmup plan, analytical model, options strategy, or automated execution.

## Product Destination

Markeitech is intended to observe an open-ended market universe, turn native market observations
into deterministic measurements and semantic events, maintain rolling system-wide market state,
and let an advisory agent direct attention toward a ranked set of concurrent SPXW, SPY, and QQQ
0DTE opportunities.

SPY, QQQ, SPX, ES, and NQ are initial examples, not an architectural whitelist. Other equities,
indexes, futures, volatility products, sectors, rates, commodities, options, or later providers
may become useful evidence sources.

The target loop is:

```text
Provider market data
        |
        v
Nautilus DataEngine and native market objects
        |
        v
Deterministic analysis capabilities
        |
        v
Semantic event stream and rolling state
        |
        v
Advisory decision agent
        |
        v
Policy-checked observation and analysis intents
        |
        +----> acquisition, options, and analysis owners
        |
        v
Concurrent 0DTE opportunity set for operator review
```

The agent directs the machinery. It does not replace deterministic analysis, subscribe directly
to IB, call provider APIs, invent indicators, or bypass resource and risk policy.

## Four Independent Concepts

The former binary distinction between one active instrument and background instruments is too
narrow. Replace it with four independent concepts.

### Trade universe

Products through which a thesis may be expressed. The initial configurable seed is SPXW, SPY, and
QQQ 0DTE options. It is not an architectural whitelist, and no product is globally preferred.
Several opportunities and expression candidates may coexist. This does not imply that an option's
underlying must always be the highest-fidelity observation source.

### Observation universe

Any instruments currently available to inform decisions. Membership is dynamic and may originate
from configuration, discovery, an approved scanner, operator input, or an agent intent.

An observed instrument is not necessarily tradable. There is no architectural maximum beyond
provider entitlements, pacing, runtime capacity, and approved budgets.

### Active capabilities

The deterministic measurements currently enabled for each instrument or related group. A
capability declares its required native inputs, warmup requirement, live cadence, supported
instrument properties, outputs, and resource cost.

Examples are illustrative only:

```text
Capability: session_volume_profile
Inputs: externally reported bars with volume
Warmup: declared session history
Live cadence: completed bars
Output: versioned profile facts and semantic changes
```

```text
Capability: trade_response
Inputs: native trades and quotes
Warmup: bounded rolling window, if required
Live cadence: every accepted observation
Output: deterministic effort-versus-response measurements
```

The capability owner, not the agent, translates a high-level activation into exact feed and
historical requirements.

### Focus

A temporary priority applied to part of the observation universe. Focus may increase data depth,
analysis breadth, update frequency, option-chain coverage, or reporting priority. It does not make
other instruments analytically unimportant and does not imply that only one instrument may receive
granular data.

Focus should be represented by an expiring lease rather than mutable global identity. Multiple
focus leases may coexist when provider and system budgets allow it.

## Data Plane

The market-data plane must support continuous native streams for as many approved instruments as
the provider and runtime can sustain. Candidate feed classes include:

- trades;
- quotes;
- external or internally aggregated bars;
- order-book data when useful and supported;
- instrument status and closes;
- option Greeks and chain slices when verified for the IB adapter; and
- narrow provider-specific data only when Nautilus cannot expose the required capability.

Native Nautilus objects remain the high-volume transport contracts. They flow through the
DataEngine, cache, and actor handlers without Markeitech raw-data wrappers. Raw observations are
not copied onto the semantic event stream and are not sent directly to an LLM.

Provider subscriptions are owned by one logical acquisition coordinator. A consumer expresses
demand to that owner and never independently cancels a provider feed. The coordinator collapses
shared demand into one native subscribe call and performs one native unsubscribe only after the
last consumer leaves.

The installed NautilusTrader `2.0.0rc1` actor surface exposes paired native subscribe and
unsubscribe methods for instruments, quotes, trades, bars, instrument status, option Greeks,
books, and option chains. Its compiled Python boundary does not expose provider subscription
reference counts or enough internal state to prove how duplicate actor subscriptions and
independent unsubscriptions reach the IB adapter. Markeitech therefore does not rely on implicit
provider deduplication. Stage 8C must still prove how independently implemented consumers receive
the same native stream without wrapping raw observations.

## Analysis Plane

Analysis components are organized by responsibility, not one actor per instrument. One component
may maintain bounded state keyed by many instruments when that gives clear ownership and efficient
processing.

Each approved capability must declare:

- capability and version identity;
- accepted instrument characteristics;
- required native live inputs;
- historical inputs and minimum depth, if any;
- output contract and cadence;
- fidelity constraints and unsupported cases;
- configurable parameters and allowed ranges;
- estimated provider and runtime cost;
- activation, reconfiguration, and shutdown behavior; and
- health and stale-data evidence.

Capability dependencies form the warmup plan. Warmup is therefore not one static global list and
not arbitrary agent prose. The agent selects an approved capability for an instrument; the system
derives, validates, schedules, and observes the exact historical requests required to initialize
it.

## Agent Control Plane

The advisory agent consumes semantic events and rolling state, then publishes structured intents.
It may eventually request:

- observation-universe additions or removals;
- activation, deactivation, or reconfiguration of approved capabilities;
- temporary focus leases;
- bounded historical evidence;
- quote, trade, bar, book, Greek, or option-chain attention;
- option-chain snapshots around selected expirations and strikes; and
- a refreshed system-state synthesis before proposing a trade.

Every intent must include identity, purpose, priority, expiry, correlation or causation context,
and the requested capability. A deterministic policy component accepts, modifies, queues, rejects,
or expires the intent according to approved instruments, capabilities, parameter ranges,
entitlements, pacing, and resource budgets.

The executing actor publishes an observable lifecycle such as requested, accepted, active,
completed, rejected, failed, canceled, or expired. The agent reasons from these results; it cannot
mistake an intention for flowing data or completed analysis.

## Bootstrap Without A Static Strategy

The runtime still needs a deterministic cold start:

1. Connect to IB and resolve the configured bootstrap universe.
2. Publish runtime health, provider capability, entitlement, session, and resource facts that are
   actually known.
3. Activate only the minimal approved baseline needed to make the agent operational.
4. Let the agent propose an initial observation and analysis plan.
5. Validate and execute accepted intents through their owning actors.
6. Feed resulting measurements, semantic events, capability health, and rolling state back to the
   agent.

The bootstrap universe is a reliable starting point, not the permanent observation universe.
Likewise, configuration supplies allowed defaults and limits; it must not become the only way to
change attention at runtime.

## Ownership

| Responsibility | Owner |
|---|---|
| Native provider connectivity and normalized market objects | Nautilus and the IB adapter |
| Logical demand, provider requests, deduplication, pacing, and cancellation | `DataAcquisitionActor` or later approved acquisition coordinator |
| Deterministic measurement | Capability-specific analysis actor |
| Capability registry and dependency expansion | Markeitech policy/configuration boundary |
| Semantic event meaning and rolling state | Later approved intelligence components |
| Attention and analysis intents | Advisory agent or operator |
| Intent authorization and resource limits | Deterministic policy component |
| Option-chain acquisition and interpretation | Later approved options components |
| Concurrent opportunity ranking and trade proposals | Advisory agent using typed evidence |
| Order execution | Absent until separately designed and approved |

## Resource And Safety Rules

- No actor, analyzer, model, or agent may connect directly to IB outside the acquisition boundary.
- One logical owner reconciles aggregate demand into provider-facing subscriptions and requests.
- Adding a consumer must not silently duplicate provider traffic.
- Unsubscribing one consumer must not remove data still required by another.
- Historical requests and option snapshots are bounded, prioritized, deduplicated, and paced.
- Focus and optional observation use leases with explicit expiry.
- Requested, active, first-observed, stale, failed, and canceled are different states.
- Provider absence, unknown fidelity, or missing entitlement remains explicit.
- High-volume raw data stays on native paths; semantic events represent meaningful derived changes.
- The agent receives tools and approved parameters, not arbitrary Python or unbounded provider APIs.
- No market-data retention is introduced solely for replay, backtesting, or unspecified future use.

## Stage 8 Sequence

### Stage 8B: Capability and demand model

Define typed, provider-neutral concepts for observation demand, feed requirements, capability
requirements, focus leases, resource budgets, and lifecycle facts. Verify installed Nautilus and
IB subscription behavior before selecting the exact fan-out mechanism.

The implemented Stage 8B batches now provide:

- instrument-bound native feed requirements;
- reusable, instrument-neutral capability feed and historical requirements;
- bootstrap, operator, analyzer, and future-agent demand ownership;
- bounded priority and optional UTC expiry;
- pure reconciliation of multiple consumers into one logical provider demand;
- safe removal and expiration while shared demand remains active; and
- explicit acquisition lifecycle vocabulary without pretending runtime transitions exist yet;
- one logical coordinator which reconciles demand into provider subscription lifetimes;
- exactly one subscribe for shared logical demand and one unsubscribe after its final consumer;
- retryable, observable provider subscribe and unsubscribe failures;
- native Nautilus translation for instruments, quotes, trades, bars, instrument status, and
  per-contract option Greeks; and
- explicit rejection of books and option chains until their richer native contracts are defined.

It does not yet provide focus leases, policy authorization, resource budgets, actor message
contracts, actor wiring, live provider evidence, first-observation evidence, or historical
execution.

### Stage 8C: Continuous native-stream proof

Run configurable continuous native market data for multiple instruments through one acquisition
owner and one minimal deterministic consumer. Prove demand deduplication, first observation,
independent consumers, unsubscribe safety, and bounded state. This is architecture proof, not a
trading model.

The first Stage 8C batch now:

- declares bootstrap feeds explicitly in configuration rather than deriving them from instrument
  membership;
- activates those feeds only after every configured instrument definition is available;
- routes native subscribe and unsubscribe commands exclusively through `DataAcquisitionActor`;
- uses that actor as the first minimal native consumer without wrapping or persisting observations;
- distinguishes a successful subscription command (`SUBSCRIBED`) from first native data
  (`ACTIVE`);
- publishes versioned, demand-correlated lifecycle facts and bounded shutdown counters; and
- configures quote and trade proof streams for ES and SPY without treating that list as a permanent
  observation universe.

The live experiment proved the native path. A temporary `NativeConsumerProbeActor` and
`DataAcquisitionActor` both received ES/SPY quote and trade callbacks. Nautilus collapsed eight
actor-level subscribe commands into four provider subscriptions. When the probe unsubscribed,
acquisition continued receiving native observations and the provider feeds remained active until
final shutdown. Independent analysis actors may therefore consume native Nautilus callbacks
without a Markeitech market-data wrapper or custom fan-out. Logical demand authorization and the
provider-lifetime anchor remain owned by acquisition. The diagnostic probe is disabled in the
normal runtime profile but preserved for explicit verification.

### Stage 8D: Capability-derived historical requests

Add bounded historical request planning from approved capability declarations. Prove ordering,
completion, timeout, cancellation, deduplication, and IB pacing without defining one universal
warmup.

### Stage 8E: Dynamic control and focus

Add policy-checked runtime intents for universe changes, capability activation, parameter changes,
and focus leases. Start with deterministic fixtures before any agent controls them.

### Stage 8F: Failure and reconnect behavior

Define stale observation, connection loss, resubscription, partial availability, and honest global
health effects. Only then is adaptive acquisition complete enough for intelligence components.

## Open Decisions Before Stage 8B Code

1. Whether the first demand contract represents raw feed requirements only or capabilities that
   expand into feed requirements. Recommendation: define both and keep them separate.
2. Resolved in Stage 8C: analysis consumers register for native callbacks while acquisition anchors
   provider lifetime. Do not relay raw ticks through semantic signals or introduce wrappers.
3. Which minimal bootstrap feeds make the future agent operational. This must be decided with the
   first actual intelligence consumer, not guessed from a retired implementation.
4. The initial resource-budget dimensions: provider subscriptions, historical pacing, option-chain
   breadth, analyzer cost, and event-rate limits.
5. The first minimal deterministic consumer used to prove the data plane. It must test plumbing
   without smuggling in an analytical strategy.

## Explicit Non-Goals

- No fixed active/background instrument hierarchy.
- No assumption that ES, SPY, QQQ, SPX, or NQ is the complete universe.
- No analytics or indicators selected in this decision.
- No raw-tick LLM ingestion.
- No agent direct access to IB, PostgreSQL, or order submission.
- No automated execution.
- No replay, backtesting, Parquet, or speculative raw-data storage.

## References

- [Nautilus actors](https://nautilustrader.io/docs/latest/concepts/actors/)
- [Nautilus data](https://nautilustrader.io/docs/latest/concepts/data/)
- [Nautilus adapters](https://nautilustrader.io/docs/latest/concepts/adapters/)
- [Nautilus options](https://nautilustrader.io/docs/latest/concepts/options/)
