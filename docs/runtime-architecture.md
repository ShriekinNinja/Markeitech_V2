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

## Initial Runtime Topology

```text
IB Gateway / TWS
      |
      v
NautilusTrader IB data client
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

## Ownership Boundaries

### Interactive Brokers Boundary

Interactive Brokers connectivity is coordinated through two paths:

- NautilusTrader IB adapter for supported functionality.
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
- Initial futures contracts are explicit-expiry NQ contracts.
- No silent rollover.
- No duplicate canonical events.
- No duplicated subscriptions.
- No unbounded queues in live data paths.
- No frontend-owned market calculations.
