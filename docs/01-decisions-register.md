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

Initial NQ runtime uses explicit individual futures contracts only.

Reason: Continuous futures can roll automatically and would violate the requirement to preserve data under original contract identity.

## DR-0006: Frontend Toolchain

Status: accepted

Use Vite, React, TypeScript, Lightweight Charts, and Zustand for the frontend workspace.

Reason: This supports a dense operational dashboard without coupling presentation to backend internals.

## DR-0007: WebSocket Boundary

Status: accepted

The dashboard receives snapshots and incremental updates from a FastAPI WebSocket gateway. It does not subscribe to IB, NautilusTrader internals, or persistence directly.

Reason: Slow or reconnecting UI clients must not degrade ingestion, analytics, strategies, or persistence.

## DR-0008: Domain Schema Library

Status: proposed for Stage 1

Use Pydantic v2 for external API and backend domain-event schemas while preserving NautilusTrader native models inside the trading runtime where practical.

Reason: Stage 1 needs typed, versioned, JSON-serializable contracts with useful validation and schema generation.
