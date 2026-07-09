# Project Context

Markeitech by Markeitect is a greenfield trading-system platform for market analysis, strategy research, deterministic replay, dashboarding, backtesting, and later controlled execution.

The initial production target is explicit-expiry NQ futures through Interactive Brokers. The implementation must use NautilusTrader as extensively as practical for trading-domain runtime concerns.

## Primary Goals

- Reliable market-data ingestion from Interactive Brokers.
- Deterministic local persistence and replay.
- A dashboard fed by backend domain events over WebSockets.
- Strategy research and live strategy runtime using the same logic wherever practical.
- Operational safety, observability, restart recovery, and reproducibility.

## Stage 0 Boundaries

Stage 0 creates the repository, project tooling, local setup docs, architecture docs, and minimal health-check code.

Stage 0 does not implement:

- market-data ingestion
- domain event contracts
- delta classification
- replay
- analytics
- strategy execution
- order execution
- live trading

## Design Principles

- NautilusTrader owns trading runtime capabilities wherever practical.
- The backend owns normalized domain events exposed to presentation and later strategy workers.
- The frontend never connects to IB, Nautilus internals, persistence, or strategy processes directly.
- Redis is optional hot runtime infrastructure, not the durable source of truth.
- Execution remains disabled unless a later stage explicitly enables it.
- Every futures contract must be explicit. Continuous futures are not acceptable for initial NQ ingestion.
