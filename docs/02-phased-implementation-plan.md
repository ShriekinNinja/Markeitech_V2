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

Not started.

## Stage 2: Market Data Foundation

Deliver one authoritative NQ market-data runtime using NautilusTrader IB support where possible and a narrow native IB adapter only for missing capabilities.

Not started.

## Stage 3: Persistence And Recovery

Deliver Nautilus-compatible Parquet/catalog storage, SQLite metadata, Redis hot runtime coordination, idempotent writes, and restart recovery tests.

Not started.

## Stage 4: WebSocket Gateway

Deliver snapshot-first WebSocket streaming, bounded client queues, resync behavior, readiness, health, and gap events.

Not started.

## Stage 5: Frontend Dashboard

Deliver operational NQ cockpit with chart, session context, readiness, source health, gaps, active bar, completed bars, and reconnect behavior.

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
