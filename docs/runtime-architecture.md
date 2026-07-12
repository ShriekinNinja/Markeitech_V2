# Runtime Architecture

## System Boundary

NautilusTrader should be the primary system boundary for trading-domain runtime concerns:

- instruments
- market-data models
- events
- actors
- strategies
- indicators where practical
- message bus
- cache
- data engine
- execution engine
- portfolio and account models
- catalog and persistence facilities
- backtesting and replay
- clocks and lifecycle

Markeitech adds bounded services around NautilusTrader for product-specific contracts, storage metadata, analytics, signals, outbound notifications, later WebSocket presentation and dashboard state, strategy-worker isolation, and operator controls.

The market-data runtime is LiveNode-centered. Markeitech builds validated plans and configuration around NautilusTrader, then uses Nautilus `TradingNodeConfig` and the Interactive Brokers data client as the runtime container for live market data.

Before any live connection, Markeitech builds four deterministic layers:

- validated instrument registry and runtime config
- ownership plan for warmups and subscriptions
- Nautilus-oriented request intents for historical bars, trade ticks, quote ticks, and bars
- ordered LiveNode actions for warmups and live subscriptions

The Markeitech market-data actor translates those actions into Nautilus calls. Historical requests are asynchronous, so an explicit coordinator waits for every request callback, passes the collected bars through the warmup analysis boundary, and only then starts role-based live subscriptions. A warmup or analysis failure leaves the actor unsubscribed.

The prepared-node builder registers the Interactive Brokers data-client factory, attaches the market-data actor, and calls `TradingNode.build()` before the guarded start path can call `TradingNode.run()`.

The guarded bootstrap may construct a Nautilus `TradingNode` from validated config, but starting the node requires explicit manual opt-in and a confirmation token because it can connect to IB.

The manual smoke command is the first path allowed to call `TradingNode.run()`. It must print the validated plan and guard state before starting, and it remains outside automated tests.

Warmup lookbacks currently over-fetch calendar days to cover the configured minimum session count across weekends and common closures. Exact exchange-calendar session resolution remains a later refinement at the session/calendar boundary.

## Initial Runtime Topology

```text
IB Gateway / TWS
      |
      v
NautilusTrader LiveNode + IB data client
      |
      v
Authoritative market-data runtime
      |
      +--> Parquet/catalog storage
      +--> SQLite metadata + durable notification outbox
      +--> Redis hot coordination
      +--> Analytics + signals
                |
                +--> Discord webhook delivery
                +--> Future WebSocket gateway --> Frontend
```

## Instrument Runtime Model

Markeitech supports multiple configured instruments with one enabled active instrument at a time.

The active instrument receives live tick-by-tick data, real-time trade/quote classification, active bar construction, dashboard primary chart updates, and later strategy eligibility. Stage 2 starts with explicit-expiry NQ as the first active instrument.

At boot, every enabled instrument is warmed from historical bars, analyzed across configured timeframes, and annotated with market context such as support/resistance zones, EMAs, trend, VWAP, FVGs, session levels, and later additional structures.

Background instruments then track live 1-minute bars through Nautilus where supported. They can produce indicators, zones, trend state, context, and dashboard signals while another instrument remains active. Examples include ES, SPX, VIX, QQQ, SPY, MAG7 names, and later additional operator-selected instruments.

Switching the active instrument changes runtime stream ownership:

- the old active instrument can downgrade to background monitoring or be disabled by policy
- the new active instrument upgrades to live tick-by-tick ownership
- each instrument keeps separate readiness, gap state, checkpoints, bars, analytics, and signals
- dashboard primary views follow the active instrument
- signal views may include both active and background instruments

Runtime switching uses a make-before-break handover. The candidate must already be enabled and must have completed the boot warmup. The actor subscribes candidate trade and quote ticks, waits until both stream types have produced data, then changes the logical active instrument and removes the previous active tick streams. All 1-minute bar subscriptions remain unchanged.

Only one instrument is logically active during this process, although the candidate and current active instrument can briefly have overlapping tick subscriptions while readiness is established. A timeout or subscription failure removes the candidate streams and keeps the previous instrument active. The Stage 2 actor exposes the internal switch command; operator-facing command transport belongs to the later gateway stage.

## Live Data Ingestion

The market-data actor normalizes Nautilus `TradeTick`, `QuoteTick`, and external 1-minute `Bar` objects at the runtime boundary. Canonical events retain UTC datetimes, original nanosecond timestamps, decimal prices and quantities, source identity, and venue trade IDs where available. Data for unconfigured instruments is rejected.

Each configured instrument has an isolated runtime snapshot containing event counts and its latest trade, quote, classified trade, external bar, and active tick-built bar. Snapshot role follows the runtime switch coordinator rather than the boot registry, so active ownership changes without replacing instrument state.

Subscribed trades are classified against the latest valid same-instrument quote. The logical active instrument also builds a provisional 1-minute bar from classified ticks. That bar carries classified buy, sell, and unknown volume and becomes complete when the first trade in the next minute arrives. Nautilus/IB external bars are completed bars whose volume remains unknown-side unless a later reconciliation step can prove attribution.

Normalized events flow through an injectable sink. Stage 2 does not persist or broadcast them yet; persistence, analytics, notifications, and later WebSocket delivery consume this boundary in later stages.

Interactive Brokers is the only implemented live provider initially. Canonical events remain provider-neutral and retain source identity, source-specific trade or sequence identifiers, original timestamps, and methodology metadata where values are derived. Future providers must enter through adapters at this canonical boundary rather than inherit IB-shaped contracts.

Analytics distinguish reported, inferred, partial, and unavailable evidence. IB top-of-book trades and quotes may support inferred aggressor side, price-level volume, and best-effort delta, but the system must not describe inferred values as authoritative exchange aggressor data or fabricate depth, footprint, or order-flow evidence from bars.

## Live Health And Gaps

Live health requirements follow current runtime ownership. The active instrument requires fresh trade ticks, quote ticks, and completed external 1-minute bars. Background instruments require fresh completed external 1-minute bars. Provisional and completed tick-built bars do not satisfy the external-bar health requirement.

Each required stream is waiting, healthy, stale, or session-paused. Stale thresholds are configurable, and session-open policy is injected so an exchange calendar can suspend expectations outside trading hours. The actor evaluates health once per second and emits a health snapshot only when semantic state changes.

External bar continuity is tracked by interval. Missing 1-minute opens create warning, degraded, or critical gap state based on count. A gap remains open across newer bars and closes only when late data fills every missing interval.

NautilusTrader owns the physical Interactive Brokers connection lifecycle and reconnect behavior. Markeitech does not create a competing reconnect loop; it observes canonical data, reports degradation, and records recovery transitions for later persistence and operator presentation.

## Ownership Boundaries

### Interactive Brokers Boundary

Interactive Brokers connectivity is coordinated through two paths:

- NautilusTrader IB data client inside a LiveNode for supported functionality.
- A narrow native IB API adapter only for capabilities NautilusTrader does not expose.

Both paths must share contract identity, timestamps, sessions, normalization, health, reconnection, persistence, and deduplication rules.

Only one component may own a market-data stream for a contract and data type at a time.

### Backend Domain Boundary

The backend owns versioned domain events that are stable for the dashboard and later strategy workers.

The backend must not duplicate NautilusTrader functionality unless a decision record documents why.

### Persistence Boundary

Parquet/catalog storage is the durable time-series store for raw ticks and bars.

SQLite stores transactional metadata such as checkpoints, readiness, gap state, recovery state, and later signal metadata.

SQLite also stores a durable notification outbox. Delivery transports consume outbox records idempotently; a Discord outage must not lose signals or block ingestion.

Redis is only hot runtime coordination. Redis must never be the sole durable source.

### Notification Boundary

Signal and analytics code emit versioned domain events and never call Discord directly. Notification policy selects, batches, formats, and enqueues delivery records. A Discord incoming-webhook adapter performs one-way delivery with bounded retries, rate-limit handling, deduplication, and explicit sent or failed state.

Discord webhook URLs are secrets and must remain outside source control and durable message payloads. Discord is an initial operator surface, not a source of truth or execution authority. No Discord bot is planned.

### Analytics, ML, And Agent Boundary

Deterministic analytics and versioned feature snapshots are the baseline. Optional ML providers consume those snapshots and emit versioned inference events containing model version, feature schema, input lineage, output semantics, latency, and degraded-input state. Models must pass offline evaluation, replay, and shadow operation before influencing signal ranking or strategy behavior.

AI agents may explain persisted evidence, assist research, and compose operator reports. They do not calculate authoritative market state, invent missing evidence, connect directly to IB, mutate durable truth, or control execution. Generated narrative remains distinguishable from deterministic metrics and model inference.

The first named decision-support model is Direction-Location-Aggression: determine auction direction or market condition, identify and refine a relevant location, then observe aggression and follow-through. Direction and location should be deterministic where possible. Aggression starts as evidence-assisted interpretation because its fidelity depends on available IB trades and quotes; automation must be earned through captured data and replay validation.

### Gateway Boundary

The WebSocket gateway builds snapshots and streams incremental updates from versioned backend events. It must use bounded per-client queues and a policy for slow clients.

The dashboard never connects directly to IB, NautilusTrader internals, persistence, or strategies.

The gateway and dashboard are intentionally deferred until after persistence, analytics, signals, notification delivery, strategy runtime, and replay are established. Their versioned event boundary remains part of the architecture so Discord-specific formatting cannot leak into domain models.

### Strategy Boundary

Strategies eventually consume stable versioned domain interfaces and NautilusTrader strategy lifecycles where practical.

Strategy worker failure must not interrupt ingestion, persistence, notifications, or later presentation updates.

## Data-Only Default

Stage 0 configures data-only mode. Execution is off by default and remains out of scope until Stage 11.

IB Gateway should be read-only during data phases.

## Operational Invariants

- All timestamps are UTC at storage and event boundaries.
- Session definitions use IANA timezones, never fixed UTC offsets.
- Futures contracts are explicit-expiry contracts.
- Stage 2 starts with NQ as the first active instrument.
- Exactly one enabled instrument is active at a time.
- Every enabled instrument warms up from historical bars before live tracking.
- Background instruments track live 1-minute bars after warmup.
- No silent rollover.
- No duplicate canonical events.
- No duplicated subscriptions.
- No unbounded queues in live data paths.
- No frontend-owned market calculations.
- No signal or analytics code coupled directly to Discord.
- No Discord webhook secret in source control or persisted notification payloads.
- No provider-specific payload leaking beyond the canonical adapter boundary.
- No inferred order-flow metric represented as authoritative source data.
- No ML model or AI agent with direct IB or execution access.
