# Semantic Events, AI Observer, And Options Intelligence Baseline

**Status:** Historical conceptual research. Its former delivery sequence and “AI observer” product
framing are superseded by the [Sir Loke v1 product definition](../product/sir-loke-v1.md) and
[delivery blueprint](../roadmap/v2-market-events-live-agent-plan.md). Retain its vocabulary only as
informative design input; it is not current product, status, architecture, or implementation
authority.

## Purpose

This document consolidates the current design discussion for Kite / Codex.

It is **not a final architecture or implementation specification**. It is a **strong conceptual baseline**. Before implementation, **Kite and the user should discuss how these concepts integrate into the existing project architecture**, including current actors, NautilusTrader components, event buses, Redis/PostgreSQL usage, market-data pipelines, and execution/risk boundaries.

The goal is a common language and starting point, not a greenfield redesign.

## Current Markeitech V2 Position

This research describes the intended product destination: deterministic market observations become
semantic events, events update multidimensional rolling state, options context joins that state,
and an advisory AI observer produces evidence-based 0DTE suggestions.

At the time of research, it did not change the then-approved V2 sequence:

1. Stages 1 through 9 establish the functional live runtime core.
2. Stages 10 and 11 harden observability, tests, and dependency upgrades.
3. Analytical entities, detectors, semantic events, rolling state, options intelligence, ML, and
   the AI observer follow as separately approved product stages.

The durable constraints from that research were:

- replay and backtesting are out of scope until Markeitect explicitly reopens them;
- raw ticks, quotes, bars, books, and option chains are not durably retained merely for possible
  future use;
- native Nautilus market objects do not receive the semantic-event envelope;
- PostgreSQL currently stores operational run and system-health records only;
- Redis, Parquet, and a generic event-definition registry are unselected ideas, not requirements;
- the proposed envelope, scores, scales, formulas, entities, and lifecycles are hypotheses that
  require concrete domain design and evidence; and
- execution remains absent and AI output remains advisory.

---

## 1. Core event concept

An **event** is an immutable statement that something relevant occurred, is occurring, or is expected to occur.

It is not necessarily a signal, order instruction, strategy decision, or market-state classification.

Examples:

```text
session.opened
session.closed
price.level.near
price.level.breached
price.level.rejected
trend.line.reactivated
zone.fvg.created
zone.fvg.partially_filled
zone.fvg.fully_filled
candle.engulfing
volume.spike
news.scheduled
news.released
```

Strategies, detectors, models, and agents may consume events and derive higher-level events.

---

## 2. Universal event envelope

Every event should share a stable common envelope:

```text
Event
├── identity
├── timing
├── classification
├── market scope
├── direction
├── significance
├── lifecycle
├── relationships
├── evidence/context
└── type-specific payload
```

Suggested fields:

```text
event_id
event_type
event_family
event_layer
schema_version
producer
producer_version

effective_at
observed_at
received_at
started_at
ended_at
scheduled_at
expires_at

scope
instrument_id
symbol
venue
asset_class
contract
timeframe
session

direction
direction_score
severity
confidence
urgency
horizon

lifecycle_stage
subject_id
validity_state
activity_state
completion_state

parent_event_ids
related_event_ids
evidence_group_id

tags
payload
```

Keep the universal envelope stable. Put specialized data in typed payloads.

---

## 3. Event layers

Separate fact from interpretation.

```text
OBSERVATION
INTERPRETATION
COMPOSITE
```

Examples:

```text
OBSERVATION:
    price.crossed_level
    volume.exceeded_baseline
    session.started
    news.released

INTERPRETATION:
    liquidity.sweep_detected
    trend.break_confirmed
    zone.rejection_detected

COMPOSITE:
    setup.long_confluence
    breakout.high_quality
    reversal.probability_increased
```

This keeps the event graph auditable.

---

## 4. Direction and significance

Direction:

```text
BULLISH
BEARISH
NEUTRAL
MIXED
UNKNOWN
```

Optional numeric score:

```text
direction_score: -1.0 to +1.0
```

Do not collapse all importance into one number. Distinguish:

```text
severity
confidence
urgency
relevance
novelty
```

Suggested severity range:

```text
0-19    Informational
20-39   Minor
40-59   Moderate
60-79   Major
80-94   Critical
95-100  Exceptional
```

Confidence and relevance can use `0.0-1.0`; urgency can use `0-100`.

---

## 5. Horizon

Direction without horizon is ambiguous.

```text
MICROSTRUCTURE
INTRABAR
SCALP
INTRADAY
SESSION
MULTI_SESSION
SWING
POSITION
STRUCTURAL
UNKNOWN
```

A bearish 1-minute event may coexist with a bullish daily trend.

---

## 6. Events, state, metrics, and entities

Keep these separate:

```text
Event  = change or occurrence
State  = currently true condition
Metric = continuously measured value
Entity = persistent market object
```

Examples:

```text
Event:
    volatility.regime_changed

State:
    volatility_regime = HIGH

Metric:
    realized_volatility = 0.034

Entity:
    zone_id = Z123
```

Do not emit an event for every metric update unless something meaningful changed.

---

## 7. Persistent entities

Some events describe persistent subjects:

```text
level_id
zone_id
trend_id
session_id
news_id
bar_id
position_id
order_id
instrument_id
```

Example:

```text
FVG entity:
    zone_id = Z123

Events:
    zone.fvg.created
    zone.fvg.entered
    zone.fvg.partially_filled
    zone.fvg.fully_filled
```

All reference the same `zone_id`.

---

## 8. Entity-specific lifecycle

Lifecycle semantics are not identical across all entity types.

Generic states may include:

```text
DETECTED
TENTATIVE
CONFIRMED
ACTIVE
DORMANT
REACTIVATED
RESOLVED
INVALIDATED
EXPIRED
CANCELLED
```

Critical distinction:

```text
DORMANT
    Currently irrelevant, but may become relevant again.

TERMINAL
    Cannot become active again under the same structural meaning.
```

### Trend line

A trend line may remain valid while price is far away for weeks or months.

Possible lifecycle:

```text
CREATED
ACTIVE
DORMANT
REACTIVATED
BROKEN
ROLE_REVERSED
INVALIDATED
EXPIRED
```

Example:

```text
trend.line.created
trend.line.confirmed
trend.line.dormant
trend.line.reactivated
trend.line.touched
trend.line.rejected
```

A reactivated line uses the same `trend_id`.

A broken trend line may later become relevant as reversed support/resistance:

```text
previous_role: SUPPORT
new_role: RESISTANCE
```

Possible event:

```text
trend.line.role_reversed
```

### FVG

An FVG is a finite unfilled imbalance.

```text
CREATED
ACTIVE
PARTIALLY_FILLED
FULLY_FILLED
INVALIDATED
EXPIRED
```

Once:

```text
zone.fvg.fully_filled
```

the FVG is terminal as an active imbalance. It must not later become `zone.fvg.reactivated`.

Price can later react in the same range, but that should be represented as another interpretation/entity.

---

## 9. Lifecycle policy per entity type

Each entity type should define its allowed transitions.

```text
EntityLifecyclePolicy
├── entity_type
├── allowed_states
├── allowed_transitions
├── dormant_states
├── terminal_states
├── reactivation_rules
└── expiration_rules
```

Example trend-line policy:

```text
ACTIVE -> DORMANT
DORMANT -> REACTIVATED
REACTIVATED -> ACTIVE
ACTIVE -> BROKEN
BROKEN -> ROLE_REVERSED
BROKEN -> INVALIDATED

terminal:
    INVALIDATED
    EXPIRED
```

Example FVG policy:

```text
ACTIVE -> PARTIALLY_FILLED
PARTIALLY_FILLED -> ACTIVE
PARTIALLY_FILLED -> FULLY_FILLED
ACTIVE -> FULLY_FILLED
ACTIVE -> INVALIDATED

terminal:
    FULLY_FILLED
    INVALIDATED
    EXPIRED
```

No transition should exist from `FULLY_FILLED` back to `ACTIVE`.

---

## 10. Separate validity, activity, and completion

A single status field is insufficient.

```text
EntityStatus
    lifecycle_state
    validity_state
    activity_state
    completion_state
```

Possible values:

```text
validity_state:
    UNCONFIRMED
    VALID
    DEGRADED
    INVALID

activity_state:
    ACTIVE
    DORMANT
    INACTIVE

completion_state:
    OPEN
    PARTIAL
    COMPLETE
    NOT_APPLICABLE
```

Examples:

```text
Trend line after one month away:
    validity_state: VALID
    activity_state: DORMANT
    completion_state: NOT_APPLICABLE

Trend line approached again:
    validity_state: VALID
    activity_state: ACTIVE
    completion_state: NOT_APPLICABLE

Partially filled FVG:
    validity_state: VALID
    activity_state: ACTIVE
    completion_state: PARTIAL

Fully filled FVG:
    validity_state: VALID
    activity_state: INACTIVE
    completion_state: COMPLETE
```

---

## 11. Typed payloads

### Level interaction

```text
level_id
level_type
level_price
distance_ticks
interaction_type
approach_direction
approach_velocity
penetration_ticks
touch_count
rejection_distance
rejection_duration
close_relative_to_level
```

### Trend line

```text
trend_id
anchor_points
contact_points
contact_count
slope_price_per_second
slope_price_per_bar
projected_price
projection_time
fit_error
line_age
first_contact_at
last_contact_at
break_distance
break_duration
```

Projected price should always include the projection timestamp.

### Zone

```text
zone_id
zone_type
lower_price
upper_price
width_ticks
created_at
origin_timeframe
direction
entry_count
touch_count
fill_percent
remaining_unfilled_ticks
volume_inside
volume_profile
poc_price
value_area_high
value_area_low
strength
invalidating_price
```

Possible zone types:

```text
FVG
ORDER_BLOCK
SUPPLY
DEMAND
VALUE_AREA
LOW_VOLUME_NODE
HIGH_VOLUME_NODE
LIQUIDITY_POOL
GAP
BALANCE_AREA
USER_DEFINED
```

### Candle

```text
bar_id
timeframe
open
high
low
close
volume
range_ticks
body_ticks
upper_wick_ticks
lower_wick_ticks
body_ratio
previous_bar_id
pattern
close_location
relative_range
relative_volume
```

Engulfing should state what was engulfed:

```text
BODY
FULL_RANGE
MULTI_BAR_BODY
MULTI_BAR_RANGE
```

### Volume

```text
observed_volume
baseline_volume
baseline_method
lookback
z_score
percentile
ratio_to_baseline
buy_volume
sell_volume
delta
cumulative_delta
price_response
```

A volume spike should always define its baseline.

### News

```text
news_id
headline
source
event_name
country
currency
scheduled_time
released_time
importance
expected
previous
actual
surprise_value
surprise_normalized
affected_symbols
affected_asset_classes
```

Keep factual release separate from interpretation:

```text
news.released
direction: NEUTRAL

news.market_interpretation
direction: BEARISH
```

---

## 12. Event relationships and double counting

Possible relationships:

```text
DERIVED_FROM
CAUSED_BY
CONFIRMS
CONTRADICTS
INVALIDATES
RESOLVES
PRECEDES
FOLLOWS
OVERLAPS
RETESTS
BELONGS_TO
CORRELATED_WITH
```

Several events may describe the same underlying move:

```text
volume.spike
candle.bullish_engulfing
price.level.reclaimed
composite.breakout_confirmed
```

Useful grouping fields:

```text
evidence_group_id
correlation_group
root_cause_event_ids
```

Do not simply sum correlated evidence. Correlated events may increase confidence more appropriately than severity.

---

## 13. Symbol-level rolling state

Conceptual state:

```text
SymbolEventState
├── bullish_pressure
├── bearish_pressure
├── neutral_risk
├── net_direction
├── gross_activity
├── confidence
├── urgency
└── breakdowns
```

Suggested ranges:

```text
bullish_pressure: 0-100
bearish_pressure: 0-100
neutral_risk: 0-100
net_direction: -100 to +100
gross_activity: 0-100
```

Example:

```text
bullish_pressure: 82
bearish_pressure: 76
net_direction: +6
gross_activity: 94
```

This means highly contested conditions, not mildly bullish calm conditions.

Conceptual contribution:

```text
contribution =
    severity
    x confidence
    x relevance
    x freshness
    x horizon_weight
    x novelty
```

Different events need different decay profiles.

---

## 14. Event definition registry

Each event type can have a declarative definition:

```text
EventDefinition
├── event_type
├── family
├── description
├── allowed_directions
├── default_horizon
├── default_decay
├── required_payload_fields
├── optional_payload_fields
├── severity_semantics
├── confirmation_rules
├── invalidation_rules
├── deduplication_rules
└── aggregation_policy
```

This allows effectively unlimited future event types without redesigning the base model.

---

# Storage Architecture

## 15. PostgreSQL role

PostgreSQL is a good durable semantic-event store, but it should not be the entire live-processing system.

Conceptually:

```text
Market data / detectors
        ↓
Live event bus
        ↓
Consumers / aggregators / strategies
        ↓
PostgreSQL durable event store
```

Use PostgreSQL for:

- immutable event history;
- auditability;
- event relationships;
- event definitions;
- historical state;
- querying/filtering;
- structured + semi-structured payloads.

Do not rely on PostgreSQL as the primary mechanism for:

- ultra-high-frequency fan-out;
- every tick as a semantic event;
- sub-millisecond actor communication;
- constantly mutating rolling state.

---

## 16. Hybrid PostgreSQL schema

Common fields should be real typed columns; event-specific fields can be JSONB.

```text
events
------
event_id
event_type
event_family
event_layer
schema_version

effective_at
observed_at
received_at
expires_at

instrument_id
symbol
venue
timeframe
session

direction
direction_score
severity
confidence
urgency
horizon

lifecycle_stage
subject_id
evidence_group_id

producer
producer_version

payload JSONB
tags TEXT[]
```

Do not place the entire event in one opaque JSON document if fields need indexing, joins, filters, or aggregation.

---

## 17. Append-only event history

Do not mutate:

```text
zone.fvg.created
```

into:

```text
zone.fvg.fully_filled
```

Insert a new event referencing the same subject.

Corrections can use:

```text
supersedes_event_id
invalidates_event_id
```

This preserves auditability and an honest event history.

Persistent entities can have dedicated models/tables such as:

```text
levels
zones
trend_lines
sessions
news_items
instruments
```

---

## 18. Storage classes

Keep these conceptually separate:

```text
1. Raw market data
   ticks, quotes, trades, bars

2. Semantic events
   level rejected, FVG created, volume spike

3. Derived state
   symbol pressure, regime, active zones, active trend lines
```

Practical baseline:

```text
Internal/Nautilus event bus
    live actor communication

Redis
    active entities
    rolling severity
    short-lived state

PostgreSQL
    durable semantic events
    definitions
    relationships
    snapshots

Parquet / time-series storage
    large raw historical tick archives
```

This is a conceptual option only. Markeitech V2 has not selected Redis or raw market-data storage.
PostgreSQL remains operational-only until a later semantic-event persistence requirement is
approved.

---

# Live Agents, ML, and LLM

## 19. Live-listening agent

A live agent is fundamentally an event consumer:

```text
Event bus
   ↓
Agent subscription
   ↓
Agent updates state
   ↓
Agent evaluates
   ↓
Agent emits event / alert / command
```

Conceptual agent:

```text
Agent
├── subscriptions
├── state
├── evaluation logic
├── tools
├── permissions
├── output events
└── health status
```

---

## 20. Deterministic agent vs ML vs LLM

### Deterministic / non-LLM agent

```text
Events -> rules/state machine -> output
```

Best for:

- exact calculations;
- deterministic logic;
- risk rules;
- execution;
- low latency;
- reproducibility;
- repeatable evaluation.

### ML model

```text
features -> trained model -> probability / score / estimate
```

Best for narrow probabilistic questions such as:

```text
Probability this level rejects
Probability this FVG fills within 30 minutes
Probability breakout remains accepted
Expected favorable excursion
Expected adverse excursion
```

### LLM agent

```text
events + state + tools -> LLM reasoning -> structured output
```

Best for:

- combining heterogeneous context;
- explaining contradictions;
- selecting relevant context;
- producing market summaries;
- coordinating tools/models;
- higher-level synthesis.

Poor fit for:

- every raw tick;
- exact numeric calculations without tools;
- hard risk limits;
- unconstrained order execution;
- ultra-low-latency loops.

---

## 21. Replacing in-head calculations and logic

A live agent can replace a large portion of the user's manual reasoning **if the information used by the user is represented in the system**.

Mapping:

```text
Human observations
    -> detectors and metrics

Recurring calculations
    -> deterministic code

Probabilistic judgments
    -> ML models

Contextual synthesis
    -> LLM agent

Hard constraints
    -> deterministic risk controls
```

The LLM is especially suited to:

```text
Given everything happening now:
- what matters?
- what supports the thesis?
- what contradicts it?
- what is missing?
- how does the situation fit together?
```

Subconscious information that is never represented cannot be reliably reproduced.

---

## 22. Recommended first agent

Start with a **Market Observer Agent**, not an autonomous trader.

Responsibilities:

```text
listen to events
maintain live context
group related events
suppress duplicate noise
produce structured summaries
emit composite events
```

Example:

```text
Input:
    price.level.near
    volume.spike
    candle.bullish_engulfing
    price.level.rejected

Output:
    composite.bullish_level_rejection
```

with severity, confidence, and supporting event IDs.

---

## 23. LLM context size

The LLM should receive compact structured snapshots, not the full market history.

Typical narrow packet:

```text
~500-2,500 tokens
```

Richer packet:

```text
~2,000-8,000 tokens
```

A useful packet may include:

```text
current timestamp/session
symbol/timeframe
current price
volatility
target level/zone
recent interaction history
recent relevant events
volume/order-flow state
higher-timeframe structure
cross-market context
upcoming news
position/risk state
ML scores
```

Usually exclude:

- every tick;
- full depth history;
- thousands of old events;
- all symbols;
- full strategy source code;
- complete historical data.

---

## 24. Agent memory

```text
Agent memory != LLM context window
```

### Working memory

```text
active levels
active zones
recent significant events
symbol pressure
current session
positions
regimes
```

Typically in memory/Redis.

### Episodic memory

```text
prior interactions with same level
similar historical setups
earlier session events
```

Typically persisted and retrieved on demand.

### Semantic memory

```text
event definitions
FVG rules
session definitions
severity rules
strategy/risk policies
```

Typically configuration/registries/documentation.

---

## 25. First ML models

Avoid beginning with:

```text
Will price go up or down?
```

Prefer narrow measurable questions:

```text
Given a confirmed level touch,
will price move 20 points away before moving 10 points through it?
```

```text
Given a new FVG,
will it fully fill within 30 minutes?
```

```text
Given a breakout,
will price remain beyond the level for the next five bars?
```

Critical rule:

> Input features may only use information available at the decision timestamp.

Future-derived features create leakage and false performance.

ML output should itself become an event, for example:

```text
ml.level_rejection.scored
```

with:

```text
model_id
model_version
source_event_id
probability
expected_favorable_excursion
expected_adverse_excursion
feature_snapshot_id
```

---

## 26. Suggested development sequence

```text
Stage 1:
    deterministic detectors
    event bus
    persistence
    symbol state

Stage 2:
    deterministic live observer

Stage 3:
    one narrow ML model

Stage 4:
    read-only LLM observer

Stage 5:
    advisory agent

Stage 6:
    constrained automation
```

Execution-critical actions should remain strictly validated and deterministic.

---

# SPY Options, Chain Analytics, and Flow

## 27. What a SPY options-chain agent can conclude

### Deterministic analytics

Examples:

```text
call/put OI concentrations
volume concentrations
unusually active strikes
bid/ask changes
spread widening
IV changes
skew changes
term-structure changes
Greek exposure changes
volume relative to OI
near-the-money liquidity
possible pin areas
high gamma-sensitivity zones
```

### ML/statistical analytics

Examples:

```text
probability SPY remains inside a range
probability a major strike is tested
probability of volatility expansion
probability a breakout persists
probability options activity confirms price
expected 15/30/60-minute move
expected favorable/adverse excursion
```

### LLM synthesis

An LLM can combine:

```text
chain behavior
SPY price action
ES/SPX context
volume
VWAP
market structure
news
volatility
flow events
ML outputs
```

and return:

```text
supporting factors
contradicting factors
scenario probabilities
missing information
confidence
```

---

## 28. Options flow

An options chain is largely a current snapshot:

```text
strike
expiry
bid
ask
volume
open interest
IV
Greeks
```

Options flow is transactional:

```text
timestamp
contract
trade price
trade size
bid/ask context
premium
exchange/conditions when available
repeated prints
block/sweep characteristics
```

Common heuristic:

```text
call at ask -> likely call buyer
call at bid -> likely call seller
put at ask  -> likely put buyer
put at bid  -> likely put seller
```

These are inferences, not proof.

A large call may be:

```text
outright bullish speculation
covered-call selling
one leg of a spread
a hedge
closing activity
part of a complex multi-leg structure
```

Therefore:

```text
call flow != automatically bullish
put flow  != automatically bearish
```

Possible semantic flow events:

```text
options.trade.large
options.trade.ask_side
options.trade.bid_side
options.sweep.detected
options.block.detected
options.repeated_strike_activity
options.volume.exceeds_open_interest
options.flow.cluster_detected
options.flow.price_divergence
options.call_activity.spike
options.put_skew.steepening
options.gamma_concentration.detected
options.liquidity.deteriorating
options.term_structure.inverted
options.pin_risk.increasing
options.volatility_expansion_risk
```

---

## 29. IBKR options-data limitations

IBKR is useful for chain analytics and limited local flow inference, but should not be assumed to equal a dedicated consolidated flow feed.

Useful live fields may include:

```text
bid
ask
bid size
ask size
last price
last size
volume
IV
Greeks
underlying price
```

However, IBKR should not automatically be assumed to provide everything needed to reconstruct professional full-market flow such as:

```text
every consolidated live print
perfect sequencing
complete trade-condition codes
full exchange context
sweep reconstruction
multi-leg strategy identification
complete aggressor classification
opening-vs-closing certainty
```

There is also a scaling issue when subscribing contract-by-contract across the full SPY chain.

A constrained approach may monitor:

```text
SPY
0DTE
next expiry
selected strikes around spot
```

and infer local flow from:

```text
last-price changes
last-size changes
volume deltas
current bid/ask
IV changes
underlying movement
```

These should be labeled as probabilistic flow inference, not authoritative consolidated flow.

---

# High-Level Architecture Baseline

## 30. Conceptual architecture

```text
Market Data
    ↓
Deterministic Detectors
    ↓
Semantic Event Bus
    ├── Durable Event Persistence
    ├── Entity State Manager
    ├── Symbol-State Aggregator
    ├── ML Scoring Services
    ├── Options/Flow Analytics
    └── Live Observer Agents
             ↓
       Composite Events
             ↓
       Dashboard / Alerts / Strategies
             ↓
       Deterministic Risk + Execution
```

For LLM use:

```text
Ticks / quotes / depth
    ↓
Deterministic calculations and detectors
    ↓
Structured semantic events
    ↓
Aggregation / filtering / state
    ↓
LLM agent
```

The LLM should not consume every raw tick.

---

## 31. Responsibility boundaries

```text
Deterministic code:
    facts
    calculations
    event detection
    execution
    risk limits

ML:
    probabilities
    rankings
    estimates

LLM agents:
    context selection
    synthesis
    explanation
    orchestration
    composite interpretation
```

---

# Integration Discussion Required Before Implementation

This document is intentionally conceptual.

Kite should **not immediately implement this as a new architecture**.

Kite and the user should first map it to the current project, including:

```text
current NautilusTrader actors/components
existing event system
existing Redis usage
existing PostgreSQL usage
current market-data pipeline
current tick storage
current indicators/detectors
current strategy interfaces
current dashboard architecture
current IBKR integration
current alerting
current position/risk architecture
```

The discussion should determine:

1. Which concepts already exist under different names.
2. Which pieces should extend existing components rather than create new ones.
3. Where semantic events fit into the current actor/event topology.
4. Which events need durable persistence and which are ephemeral.
5. Which persistent entities need dedicated state models.
6. Whether Redis is needed for each state class or existing in-process state is sufficient.
7. Which live observer should be built first.
8. What the first narrow ML target should be.
9. What SPY/options data IBKR can realistically supply with current subscriptions and architecture.
10. Which conclusions must remain deterministic.
11. Which LLM outputs are advisory only.
12. What permissions any live agent is allowed to have.

---

# Final Baseline Principle

> Keep raw observations, semantic events, persistent entities, derived state, ML scores, LLM interpretations, and execution authority conceptually separate.

And:

> Treat this document as a strong baseline for discussion with Kite, not as a final implementation contract.

The next step is for Kite and the user to map this model onto the existing project and agree on the smallest coherent integration path before implementation.
