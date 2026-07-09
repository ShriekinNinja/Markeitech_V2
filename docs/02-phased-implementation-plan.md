# Phased Implementation Plan

## Stage 0: Repository Bootstrap

Deliver:

- uv Python project
- FastAPI backend shell
- Vite React TypeScript frontend shell
- pytest, ruff, and black configuration
- local setup docs
- architecture docs
- data-only configuration defaults

Stop condition:

- Do not implement Stage 1 domain contracts until Stage 0 is reviewed and approved.

## Stage 1: Core Domain Contracts

Deliver typed, versioned models for contract identity, trade ticks, quote ticks, classified trades, bars, readiness, gaps, health, gateway events, and strategy state events.

Implemented:

- Pydantic v2 domain contracts under `backend/src/markeitech/domain`.
- Generic instrument contract validation with explicit futures support.
- One-active-many-background instrument registry validation.
- NQ convenience contract for the first active instrument.
- UTC timestamp and IANA timezone validation.
- Canonical trade tick, quote tick, classified trade, and one-minute bar models.
- Readiness, gap, source-health, gateway-event, and strategy-state-event models.
- Deterministic trade classification helper.
- Unit tests for contract identity, active/background registry rules, timestamp rules, timezone rules, dedupe keys, quote freshness, classification, bars, readiness, gaps, source health, and event shapes.

## Stage 2: Market Data Foundation

Deliver one authoritative market-data runtime using NautilusTrader IB support where possible and a narrow native IB adapter only for missing capabilities.

Stage 2 starts with NQ as the active tick-by-tick instrument. Every enabled instrument warms up from historical bars, gets multi-timeframe annotations, and then tracks live data according to its role. Background instruments track live 1-minute bars after warmup.

First implementation slice:

- Add a Nautilus `TradingNodeConfig` builder for data-only LiveNode configuration.
- Add an Interactive Brokers data-client config wrapper.
- Keep execution clients, strategies, and actors empty by default.
- Add a deterministic market-data planner that turns the instrument registry into warmup requests and subscription ownership.
- Plan active-instrument tick-by-tick `Last`, tick-by-tick `BidAsk`, and 1-minute bars.
- Plan background-instrument live 1-minute bars after warmup.
- Do not start `TradingNode.run()` or connect to IB in automated tests.

Second implementation slice:

- Load market-data runtime config from local TOML.
- Provide `config/market-data.example.toml`.
- Add `markeitech-market-data-plan` dry-run CLI.
- Print planned warmups, subscriptions, data clients, and execution-client state without connecting to IB.

Third implementation slice:

- Map the deterministic market-data plan into Nautilus-oriented request intents.
- Represent historical bar warmup intents with Nautilus-style bar type strings.
- Represent active trade tick, active quote tick, and 1-minute bar subscription intents.
- Include the request intents in the dry-run CLI output.
- Keep request intents offline-safe; do not call live Nautilus subscription methods yet.

Fourth implementation slice:

- Add guarded Nautilus LiveNode bootstrap helpers.
- Allow LiveNode construction from validated config.
- Refuse LiveNode start unless `run_live_node=true`, `manual_live_node_start=true`, and the caller provides the explicit confirmation token.
- Keep the default example config in dry-run mode.
- Test bootstrap behavior with fake nodes, not live IB connections.

Fifth implementation slice:

- Add `markeitech-market-data-smoke` manual smoke-test CLI.
- Print the validated plan before attempting LiveNode start.
- Refuse smoke startup unless manual config flags and confirmation token are present.
- Keep automated smoke tests on fake nodes only.

## Stage 3: Persistence And Recovery

Deliver Nautilus-compatible Parquet/catalog storage, SQLite metadata, Redis hot runtime coordination, idempotent writes, and restart recovery tests.

Not started.

## Stage 4: WebSocket Gateway

Deliver snapshot-first WebSocket streaming, bounded client queues, resync behavior, readiness, health, and gap events.

Not started.

## Stage 5: Frontend Dashboard

Deliver operational cockpit with active-instrument chart, session context, readiness, source health, gaps, active bar, completed bars, background signal dashboard, and reconnect behavior.

Not started.

## Stage 6: Analytics And Levels

Deliver deterministic derived analytics, levels, zones, and volume profile support.

Not started.

## Stage 7: Signals

Deliver deterministic signal lifecycle, scoring, dedupe, persistence, and dashboard updates.

Not started.

## Stage 8: Strategy Runtime

Deliver isolated strategy worker topology, bounded queues, lag metrics, state restoration, and controlled lifecycle.

Not started.

## Stage 9: Backtesting And Replay

Deliver NautilusTrader-based backtesting and reproducible replay datasets.

Not started.

## Stage 10: Execution And Risk Controls

Deliver explicitly configured paper/live execution with risk checks, auditability, and no accidental live orders.

Not started.
