# Markeitech Greenfield Agent Prompt

You are building **Markeitech by Markeitect** from scratch in an empty repository.

This is a greenfield implementation. Do not preserve or recreate any legacy architecture unless explicitly useful. Build a production-grade market-analysis, strategy-research, backtesting, replay, dashboard, and later live-trading platform for discretionary and systematic futures trading.

Initial focus: **NQ front-month futures through Interactive Brokers**.

Primary design principle: use **NautilusTrader as extensively as practical**. Do not duplicate NautilusTrader capabilities unless there is a documented reason.

## Product Requirements

The platform must support:

1. Reliable live market-data ingestion from Interactive Brokers.
2. Live dashboards through WebSockets.
3. Historical persistence and deterministic replay.
4. Strategy research and backtesting using the same strategy logic as live wherever practical.
5. Safe addition/removal/replacement of live strategies without degrading market-data or dashboard responsiveness.
6. Strong isolation between ingestion, analytics, strategy execution, persistence, and presentation.
7. Operational resilience, observability, restart recovery, and reproducibility.

## Mandatory Architecture Direction

Use NautilusTrader for:

- instruments
- market-data models
- event models
- actors
- strategies
- indicators where practical
- message bus
- cache
- data engine
- execution engine
- portfolio/account models
- persistence/catalog facilities
- backtesting
- replay
- clocks/time handling
- lifecycle management

Interactive Brokers integration must have two coordinated paths:

1. NautilusTrader IB adapter for all supported functionality.
2. Narrow native IB API adapter only for capabilities Nautilus does not expose.

Both IB paths must share contract identity, timestamps, sessions, normalization, health, reconnection, persistence, and deduplication rules.

Do not allow duplicated subscriptions, duplicated events, conflicting stream ownership, or inconsistent contract identity.

---

# Stage 0 - Repository Bootstrap

Create a clean repository with:

- Python 3.12+
- `uv` project setup
- NautilusTrader with IB support
- FastAPI
- SQLite
- Redis support
- Parquet/catalog support
- pytest
- ruff/black or equivalent formatting/linting
- frontend workspace using Vite + React + TypeScript

Suggested top-level structure:

```text
.
├── backend/
│   └── src/markeitech/
├── frontend/
├── docs/
├── tests/
├── data/
├── scripts/
├── pyproject.toml
├── README.md
└── .env.example
```

Create documentation first:

- `docs/00-project-context.md`
- `docs/01-decisions-register.md`
- `docs/02-phased-implementation-plan.md`
- `docs/runtime-architecture.md`
- `docs/data-contracts.md`
- `docs/ib-setup.md`

Do not implement trading execution in this stage.

Acceptance criteria:

- Repo installs cleanly.
- Backend test runner works.
- Frontend dev server works.
- README explains local setup.
- Architecture docs define ownership boundaries.

---

# Stage 1 - Core Domain Contracts

Implement typed, versioned domain models for:

- explicit NQ contract configuration
- canonical trade ticks
- canonical bid/ask quote ticks
- classified trades
- 1-minute bars
- readiness state
- gap state
- source health
- gateway events
- strategy state events
- later level/zone/signal events

Rules:

- All timestamps are UTC.
- Use IANA timezones for sessions.
- Never use fixed UTC offsets for London/New York sessions.
- Initial instrument is explicit-expiry NQ futures.
- Do not silently roll contracts.
- Preserve historical data under original contract identity.

Delta classification:

1. Match trade to most recent valid quote at or before trade timestamp.
2. At or above ask = buy.
3. At or below bid = sell.
4. Inside spread = tick-rule fallback.
5. Otherwise = unknown.

Expose:

- buy volume
- sell volume
- unknown volume
- delta
- classified-volume ratio

Acceptance criteria:

- Unit tests cover contract identity, timestamp rules, session windows, dedupe keys, quote freshness, classification, and readiness transitions.

---

# Stage 2 - Market Data Foundation

Build one authoritative NQ market-data runtime.

Responsibilities:

- Resolve explicit NQ contract.
- Connect to IB through NautilusTrader.
- Subscribe to live tick-by-tick `Last`.
- Subscribe to live tick-by-tick `BidAsk`.
- Normalize events once.
- Deduplicate events once.
- Classify trades once.
- Build canonical 1-minute bars.
- Derive readiness and gap state.
- Publish versioned backend domain events.

Historical bootstrap:

- First startup requests enough historical 1-minute bars for five complete Globex sessions.
- Normal restart loads local persisted data first.
- Request only missing bars or bounded tick gaps.
- Deduplicate historical/live overlap.
- Live tick streams are authoritative from healthy connection onward.

Do not use IB histogram data as a trade stream.

Do not use `reqHistoricalTicks` as routine startup bootstrap.

Acceptance criteria:

- Startup fails clearly when explicit contract config is missing.
- Runtime starts NQ-only.
- No execution client initializes by default.
- Live trade and quote streams are both active.
- 1-minute bars are produced from canonical trade events.
- Restart does not duplicate events or bars.

---

# Stage 3 - Persistence And Recovery

Implement hybrid persistence:

1. Nautilus-compatible Parquet/catalog storage for:
   - raw trade ticks
   - raw bid/ask quote ticks
   - canonical 1-minute bars

2. SQLite transactional metadata for:
   - checkpoints
   - readiness state
   - gap state
   - recovery metadata
   - later signals/levels/strategy metadata

3. Redis only for hot runtime/cache coordination.

Rules:

- Redis must not be the sole durable source.
- Writes must be idempotent.
- Partial writes must be recoverable.
- Gaps must be explicit and observable.
- Retain raw ticks for at least five sessions initially.
- Retain 1-minute bars longer.

Acceptance criteria:

- Kill/restart test restores from local storage.
- Missing intervals are detected.
- Only missing intervals are requested.
- Duplicate historical/live overlap is ignored.
- Readiness reports degraded state when data requirements are not met.

---

# Stage 4 - WebSocket Gateway

Build a dedicated FastAPI/WebSocket gateway.

The dashboard must never connect directly to IB, Nautilus internals, strategies, or persistence.

Gateway requirements:

- Subscribe to versioned backend domain events.
- Build initial snapshots.
- Stream incremental updates.
- Expose readiness and health.
- Use bounded client queues.
- Drop or resync slow clients.
- Support reconnect/resubscription.
- Include schema versioning.
- Prevent slow clients from blocking backend processing.

Initial event types:

- `snapshot`
- `bar.active`
- `bar.completed`
- `readiness.update`
- `health.update`
- `gap.update`

Later event types:

- `level.upsert`
- `zone.upsert`
- `signal.upsert`
- `signal.transition`
- `strategy.state`
- `order.execution`

Acceptance criteria:

- New WebSocket client receives snapshot first.
- Live active-bar updates are incremental.
- Completed bars are emitted once.
- Slow client cannot block backend.
- Reconnect restores current state.

---

# Stage 5 - Frontend Dashboard

Build a focused React cockpit.

Initial frontend scope:

- one active instrument
- one primary chart
- latest two trading sessions visible
- WebSocket connection state
- readiness state
- source health
- gap state
- active 1-minute bar
- completed 1-minute bars

Preferred stack:

- Vite
- React
- TypeScript
- Lightweight Charts
- Zustand or equivalent small state store

Rules:

- Use incremental chart updates, not full-series replacement on every tick.
- Do not include replay controls in normal live UI.
- Do not connect directly to IB or backend internals.
- UI should be operational, dense, and useful, not a marketing page.

Acceptance criteria:

- Chart loads from snapshot.
- Active bar updates without full reset.
- Completed bars append correctly.
- Reconnect works.
- Readiness/health are visible.

---

# Stage 6 - Analytics And Levels

Add derived analytics:

Timeframes:

- base: 1m
- derived: 5m, 15m, 30m

Indicators/structures:

- EMA 9/20/50/200 on 1m, 5m, 15m
- session VWAP
- prior Globex high/low
- London high/low
- New York high/low
- London 15m and 30m ORB
- New York 15m and 30m ORB
- session volume profiles
- POC/VAH/VAL
- FVG on 1m, 5m, 15m

Sessions:

- Full CME Globex coverage
- London: `08:00-11:30 Europe/London`
- New York: `09:30-16:00 America/New_York`

Volume profile defaults:

- 5-point NQ bins
- 70% value area
- current Globex
- previous Globex
- London
- New York

Acceptance criteria:

- Analytics rebuild deterministically after restart.
- Derived bars are built from 1m bars.
- Levels persist and restore.
- Frontend renders active levels/zones.

---

# Stage 7 - Signals

Implement initial signals:

- rejection at tracked level/zone
- breakout through tracked level/zone
- proximity to active level/zone
- large trade
- abnormal trade-frequency burst
- FVG-related signal

Signal lifecycle:

- active
- expired
- invalidated
- resolved

Signal scoring:

- severity: info, low, medium, high, critical
- strength: 0-100
- confidence only if justified
- mandatory reason codes and supporting metrics

Deduplication key:

- instrument
- signal type
- direction
- timeframe
- reference level/zone
- analysis session

Rules:

- Repeated detection updates existing signal.
- Emit new alert only on creation or material strengthening.
- Persist every transition.
- Restore current and previous Globex-session signals on restart.

Acceptance criteria:

- Deterministic fixture streams produce deterministic signals.
- Signals do not duplicate after restart.
- Signal lifecycle transitions persist.
- WebSocket sidebar receives updates within normal 500 ms target.

---

# Stage 8 - Strategy Runtime

Design strategy support as a primary architecture concern.

Requirements:

- Strategies consume stable versioned domain interfaces.
- Strategy logic must not depend on dashboard code, raw IB callbacks, or persistence internals.
- Backtest and live should use the same event models and lifecycle wherever practical.
- Strategy config is externalized and versioned.
- Strategy state is isolated per strategy instance, instrument, account, and deployment.
- Strategy failure must not stop market-data ingestion.
- Slow strategies must not block the market-data path.
- Strategies declare subscriptions, timeframes, indicators, warm-up, and execution permissions.

Preferred live topology:

- isolated strategy worker processes
- bounded event queues
- explicit backpressure policy
- observable lag metrics
- process restart with state restoration
- no unsafe in-process hot reload

Lifecycle states:

- registered
- loading
- warming_up
- paper
- live
- paused
- stopping
- failed
- retired

Acceptance criteria:

- A crashing strategy does not interrupt ingestion or dashboard.
- A slow strategy becomes degraded/paused by policy.
- Strategy state restores after worker restart.
- Adding/removing a strategy does not rebuild unrelated pipelines.

---

# Stage 9 - Backtesting And Replay

Backtesting is mandatory from the beginning, but implement after the data foundation is stable.

Use NautilusTrader backtesting wherever practical.

Every backtest must capture:

- strategy version
- strategy config
- contract/instrument version
- dataset snapshot id
- data fidelity requirements
- commission model
- fee model
- slippage model
- latency assumptions
- order-fill simulation rules
- session model
- result metadata

Data fidelity rules:

- Bar-based strategies may use historical bars.
- Profile-based strategies may use validated histogram or bar-derived profile data.
- Tick/delta/quote/sequence-dependent strategies require locally captured ticks/quotes or another validated historical provider.
- IB histogram data is not a substitute for time-ordered trade/quote data.

Support:

- single-run backtests
- batch experiments
- walk-forward testing
- regression backtests
- later distributed execution

Acceptance criteria:

- Backtests run independently of live runtime.
- Backtests do not consume live-process resources.
- Same strategy logic can run in backtest and paper/live where practical.
- Results are persisted and comparable.

---

# Stage 10 - Execution And Risk Controls

Execution is deferred until market data, persistence, dashboard, analytics, strategies, and backtesting are stable.

When enabled:

- execution must be explicitly configured
- no accidental live orders
- paper mode before live mode
- risk checks before order submission
- order/execution events persisted
- dashboard exposes execution health
- strategy permissions enforced

Acceptance criteria:

- Data-only mode remains default.
- Live execution cannot start accidentally.
- Paper/live behavior is observable and auditable.

---

# Global Acceptance Standards

The system is not HFT. Prioritize:

- correctness
- determinism
- resilience
- maintainability
- reproducibility

Unacceptable:

- unbounded queues
- blocking I/O in live data path
- silent contract rollover
- duplicated subscriptions
- duplicated canonical events
- dashboard-owned market calculations
- Redis-only durable state
- frontend direct IB access
- strategy failure stopping ingestion
- fabricated historical delta from histogram data

Normal visible update target:

- dashboard updates within 500 ms under healthy conditions

Testing expectations:

- unit tests for every domain component
- deterministic fixture tests for event processing
- persistence/restart tests
- WebSocket reconnect tests
- IB manual smoke-test procedure
- backtest reproducibility tests once backtesting is implemented
