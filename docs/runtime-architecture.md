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

Markeitech adds bounded services around NautilusTrader for product-specific contracts, storage metadata, WebSocket presentation, dashboard state, strategy-worker isolation, and operator controls.

The market-data runtime is LiveNode-centered. Markeitech builds validated plans and configuration around NautilusTrader, then uses Nautilus `TradingNodeConfig` and the Interactive Brokers data client as the runtime container for live market data.

Before any live connection, Markeitech builds three deterministic layers:

- validated instrument registry and runtime config
- ownership plan for warmups and subscriptions
- Nautilus-oriented request intents for historical bars, trade ticks, quote ticks, and bars
- ordered LiveNode actions for warmups and live subscriptions

Only the later guarded LiveNode adapter should translate those actions into live Nautilus method calls.

The guarded bootstrap may construct a Nautilus `TradingNode` from validated config, but starting the node requires explicit manual opt-in and a confirmation token because it can connect to IB.

The manual smoke command is the first path allowed to call `TradingNode.run()`. It must print the validated plan and guard state before starting, and it remains outside automated tests.

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
      +--> SQLite metadata
      +--> Redis hot coordination
      +--> WebSocket gateway
                |
                v
              Frontend
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

Redis is only hot runtime coordination. Redis must never be the sole durable source.

### Gateway Boundary

The WebSocket gateway builds snapshots and streams incremental updates from versioned backend events. It must use bounded per-client queues and a policy for slow clients.

The dashboard never connects directly to IB, NautilusTrader internals, persistence, or strategies.

### Strategy Boundary

Strategies eventually consume stable versioned domain interfaces and NautilusTrader strategy lifecycles where practical.

Strategy worker failure must not interrupt ingestion, persistence, or dashboard updates.

## Data-Only Default

Stage 0 configures data-only mode. Execution is off by default and remains out of scope until Stage 10.

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
