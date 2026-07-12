# Markeitech Greenfield Agent Prompt

You are building **Markeitech by Markeitect** from scratch in an empty repository.

This is a greenfield implementation. Do not preserve or recreate any legacy architecture unless explicitly useful. Build a production-grade market-analysis, strategy-research, backtesting, replay, dashboard, and later live-trading platform for discretionary and systematic futures trading.

Initial active focus: **explicit-expiry NQ futures through Interactive Brokers**.

The system must support one runtime-switchable active instrument for live tick-by-tick data and real-time analysis, plus multiple background monitored instruments.

At boot, every enabled instrument must be warmed from historical data, analyzed across configured timeframes, and annotated with market context such as support/resistance zones, EMAs, trend, VWAP, FVGs, session levels, and later additional structures. After warmup, background instruments track live 1-minute bars through Nautilus where supported, while the active instrument tracks live tick-by-tick data.

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

Live market-data runtime must be centered on a NautilusTrader LiveNode. Markeitech may add configuration, validation, planning, and product-specific event boundaries around the LiveNode, but it must not build a parallel live market-data loop when Nautilus can own the runtime concern.

LiveNode startup must remain manual and guarded until IB smoke testing is explicitly approved. Dry-run tooling should validate configuration, plans, and request intents without connecting to IB.

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

- explicit instrument and futures contract configuration
- one active tick-by-tick instrument plus multiple background monitored instruments
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
- Initial active instrument is explicit-expiry NQ futures.
- The architecture must support runtime active-instrument switching.
- Every enabled instrument warms up from historical bars before live tracking.
- Background instruments track live 1-minute bars after warmup.
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

Build one authoritative market-data runtime.

Responsibilities:

- Build a data-only Nautilus LiveNode configuration.
- Resolve the explicit active instrument contract, initially NQ.
- Connect to IB through NautilusTrader.
- Subscribe the active instrument to live tick-by-tick `Last`.
- Subscribe the active instrument to live tick-by-tick `BidAsk`.
- Warm and analyze every enabled instrument from historical bars.
- Monitor configured background instruments through live 1-minute bars.
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
- Runtime starts with NQ as the active instrument.
- Runtime can switch the active instrument without mutating contract identity.
- Runtime can monitor multiple background instruments after historical warmup.
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
   - durable notification outbox and delivery state
   - later signals/levels/strategy metadata

3. Redis only for hot runtime/cache coordination.

Rules:

- Redis must not be the sole durable source.
- Writes must be idempotent.
- Partial writes must be recoverable.
- Gaps must be explicit and observable.
- Notification outbox writes must be transactional with their source metadata where required.
- Pending notification intents must survive restart without storing delivery secrets.
- Interactive Brokers is the only initial live provider, but canonical storage contracts must remain provider-neutral.
- Preserve provider identity, source-specific identifiers, original timestamps, and derivation methodology.
- Distinguish reported, inferred, partial, and unavailable evidence.
- Retain raw ticks for at least five sessions initially.
- Retain 1-minute bars longer.

Acceptance criteria:

- Kill/restart test restores from local storage.
- Missing intervals are detected.
- Only missing intervals are requested.
- Duplicate historical/live overlap is ignored.
- Readiness reports degraded state when data requirements are not met.
- Pending notification intents restore after restart without duplication.

---

# Stage 4 - Analytics And Levels

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

Initial auction-market decision model:

- Direction: determine balance, imbalance, directional pressure, and likely auction destination.
- Location: identify and refine candidate reaction areas using structure, sessions, profiles, POC/VAH/VAL, VWAP, and low-volume nodes.
- Emit versioned, provider-neutral feature snapshots for deterministic signals and later ML consumers.

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
- Versioned analytics, level, and zone events are transport-neutral.
- Direction and Location evidence can be reproduced from the same persisted dataset.

---

# Stage 5 - Signals

Implement initial signals:

- rejection at tracked level/zone
- breakout through tracked level/zone
- proximity to active level/zone
- large trade
- abnormal trade-frequency burst
- FVG-related signal
- Direction-Location-Aggression qualified setup

Direction-Location-Aggression rules:

- Direction alone is context, not an entry signal.
- Location must be explicit, versioned, and tied to supporting structures.
- Aggression may use trade size, inferred aggressor side, price-level volume, trade frequency, quote response, and follow-through when available.
- IB-derived aggression is best-effort evidence and must expose its fidelity and limitations.
- Never fabricate footprint, delta, absorption, or depth evidence from candles.
- Begin as decision support; automation requires captured-data replay and explicit acceptance.

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
- Signal detection must not call Discord, WebSockets, or frontend code directly.
- Optional ML inference may rank or classify setups only after deterministic rules establish a baseline.
- A model score must not silently replace required Direction, Location, or Aggression evidence.

Acceptance criteria:

- Deterministic fixture streams produce deterministic signals.
- Signals do not duplicate after restart.
- Signal lifecycle transitions persist.
- Notification-ready domain events are emitted within the normal 500 ms target.
- The same fixture and feature versions produce the same setup lifecycle before optional model ranking.

---

# Stage 6 - Notifications And Reports

Build a transport-neutral outbound notification pipeline with Discord incoming webhooks as the first delivery adapter.

Initial outputs:

- signal creation and material-strengthening alerts
- signal resolved, invalidated, and expired updates
- readiness, source-health, and gap alerts
- scheduled session analysis reports and context digests
- optional chart or report attachments later

Requirements:

- Consume versioned analytics, signal, readiness, health, and gap events.
- Write notification intents to the durable Stage 3 outbox before delivery.
- Keep Discord formatting and routing outside analytics and signal logic.
- Support severity and purpose-based channel routing.
- Batch or digest low-priority events to control noise.
- Deduplicate deliveries across retries and restarts.
- Respect Discord rate limits and use bounded retries with explicit terminal failure state.
- Sanitize message content and disable unintended mentions by default.
- Keep webhook URLs in secret configuration, never source control or outbox payloads.
- Discord failure must not block ingestion, persistence, analytics, signals, or strategies.
- Do not build a Discord bot or accept inbound Discord commands.

Acceptance criteria:

- A deterministic signal creates one durable notification and one Discord message.
- Repeated processing and restart do not duplicate delivery.
- Material strengthening updates or replaces the existing alert by policy.
- A Discord outage leaves retryable outbox records and does not lose signal transitions.
- Rate limiting delays delivery without unbounded queues or blocking upstream work.
- Scheduled analysis reports can be generated from restored persisted state.
- AI-generated narrative is grounded in persisted structured evidence and remains distinguishable from deterministic metrics and model inference.

---

# Stage 7 - Strategy Runtime

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
- Model-assisted strategies declare model and feature-schema versions and begin in shadow or paper mode.

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

- A crashing strategy does not interrupt ingestion, persistence, or notifications.
- A slow strategy becomes degraded/paused by policy.
- Strategy state restores after worker restart.
- Adding/removing a strategy does not rebuild unrelated pipelines.

---

# Stage 8 - Backtesting And Replay

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
- model version and feature-schema version when inference is used

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
- model training, calibration, shadow comparison, and drift evaluation
- later distributed execution

Acceptance criteria:

- Backtests run independently of live runtime.
- Backtests do not consume live-process resources.
- Same strategy logic can run in backtest and paper/live where practical.
- Results are persisted and comparable.
- Model-assisted results remain reproducible from captured feature snapshots and inference metadata.

---

# Stage 9 - WebSocket Gateway

Build a dedicated FastAPI/WebSocket gateway for future presentation clients.

The dashboard must never connect directly to IB, Nautilus internals, strategies, or persistence.

Gateway requirements:

- Subscribe to versioned backend domain events.
- Build initial snapshots.
- Stream incremental updates.
- Expose readiness, health, gaps, analytics, levels, zones, and signals.
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
- `level.upsert`
- `zone.upsert`
- `signal.upsert`
- `signal.transition`
- `strategy.state`

Later event types:

- `order.execution`

Acceptance criteria:

- New WebSocket client receives snapshot first.
- Live active-bar updates are incremental.
- Completed bars are emitted once.
- Slow client cannot block backend.
- Reconnect restores current state.

---

# Stage 10 - Frontend Dashboard

Build a focused React cockpit after the backend, notification, strategy, and replay foundations are stable.

Initial frontend scope:

- one active instrument
- background monitored instruments and signal stream
- one primary chart
- latest two trading sessions visible
- WebSocket connection state
- readiness state
- source health
- gap state
- active and completed 1-minute bars
- active analytics, levels, and zones

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

- Chart and context load from a snapshot.
- Active bar updates without full reset.
- Completed bars append correctly.
- Reconnect works.
- Readiness, health, analytics, levels, zones, and signals are visible.

---

# Stage 11 - Execution And Risk Controls

Execution is deferred until market data, persistence, analytics, signals, notifications, strategies, backtesting, gateway, and dashboard are stable.

When enabled:

- execution must be explicitly configured
- no accidental live orders
- paper mode before live mode
- risk checks before order submission
- order/execution events persisted
- dashboard exposes execution health
- strategy permissions enforced
- Discord has no direct order-submission authority
- ML models and AI agents have no direct IB or order-submission authority

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
- Discord-coupled analytics or signal logic
- Discord webhook secrets in source control or durable payloads
- Discord commands with execution authority
- provider-specific payloads leaking beyond canonical adapters
- inferred order-flow evidence represented as authoritative source data
- unversioned ML features or inference outputs
- AI-generated narrative treated as durable market truth
- strategy failure stopping ingestion
- fabricated historical delta from histogram data

Normal visible update target:

- notification-ready domain updates within 500 ms under healthy conditions
- later dashboard updates within 500 ms under healthy conditions

Testing expectations:

- unit tests for every domain component
- deterministic fixture tests for event processing
- persistence/restart tests
- WebSocket reconnect tests
- IB manual smoke-test procedure
- backtest reproducibility tests once backtesting is implemented
