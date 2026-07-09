# Decisions Register

This register records architecture decisions that should not drift silently.

## DR-0001: Python Version

Status: accepted

Use Python 3.13 for Stage 0.

Reason: NautilusTrader currently supports Python 3.12 through 3.14. The local workspace has Python 3.13 available, and pinning avoids ambiguous "3.12+" behavior.

## DR-0002: Dependency Manager

Status: accepted

Use uv with a root `pyproject.toml` and checked-in `uv.lock` once dependencies are resolved.

Reason: uv is recommended by NautilusTrader docs and gives reproducible local installs.

## DR-0003: NautilusTrader Dependency

Status: accepted

Declare `nautilus_trader[ib,docker]` for the backend.

Reason: The IB integration and Dockerized IB Gateway support are optional NautilusTrader extras. The platform depends on both for the intended IB path and local automation.

## DR-0004: Data-Only Default

Status: accepted

Stage 0 and later market-data stages default to data-only mode. Execution is disabled unless a later stage explicitly configures and verifies it.

Reason: The first build phase must not make accidental live orders possible.

## DR-0005: Explicit Futures Only

Status: accepted

Futures runtime uses explicit individual futures contracts only.

Reason: Continuous futures can roll automatically and would violate the requirement to preserve data under original contract identity. NQ is the first active futures target, but the rule applies to all futures roots.

## DR-0006: Frontend Toolchain

Status: accepted

Use Vite, React, TypeScript, Lightweight Charts, and Zustand for the frontend workspace.

Reason: This supports a dense operational dashboard without coupling presentation to backend internals.

## DR-0007: WebSocket Boundary

Status: accepted

The dashboard receives snapshots and incremental updates from a FastAPI WebSocket gateway. It does not subscribe to IB, NautilusTrader internals, or persistence directly.

Reason: Slow or reconnecting UI clients must not degrade ingestion, analytics, strategies, or persistence.

## DR-0008: Domain Schema Library

Status: accepted

Use Pydantic v2 for external API and backend domain-event schemas while preserving NautilusTrader native models inside the trading runtime where practical.

Reason: Stage 1 needs typed, versioned, JSON-serializable contracts with useful validation and schema generation.

## DR-0009: Stage 1 Domain Contract Boundary

Status: accepted

Implement Stage 1 contracts as pure Pydantic models and deterministic Python functions under `markeitech.domain`.

Reason: Domain contracts must be testable before IB connectivity, persistence, WebSockets, or strategy runtime exist. NautilusTrader integration remains a runtime boundary for later stages rather than a dependency inside these external backend event schemas.

## DR-0010: Active And Background Instrument Roles

Status: accepted

Support exactly one enabled active instrument and multiple enabled background instruments.

Reason: The operator needs one runtime-switchable instrument for live tick-by-tick data and real-time analysis, while other instruments can still contribute historical-bar-based context, indicators, zones, trends, and dashboard signals.

Every enabled instrument must warm up from historical bars and receive multi-timeframe annotations before live tracking. The active instrument must use tick-by-tick data. Background instruments track live 1-minute bars after warmup. Switching the active instrument changes stream ownership but must not mutate instrument identity.

## DR-0011: LiveNode-Centered Market Data Runtime

Status: accepted

Stage 2 market-data runtime configuration is centered on NautilusTrader `TradingNodeConfig` and the Interactive Brokers data client.

Reason: The final runtime should run inside Nautilus LiveNode instead of a separate homegrown market-data loop. Markeitech owns validation, planning, product-specific contracts, and event boundaries around that LiveNode. Automated tests build configuration and plans but do not start the node or connect to IB.
