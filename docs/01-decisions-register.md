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

## DR-0012: Offline Request Intents Before Live Subscriptions

Status: accepted

Map market-data plans into Nautilus-oriented request intents before implementing live subscription calls.

Reason: Historical warmups, active tick subscriptions, background bar subscriptions, and ownership rules can be validated deterministically without connecting to IB. A later guarded bootstrap should be the only layer that translates these intents into live Nautilus method calls.

## DR-0013: Manual Confirmation For LiveNode Start

Status: accepted

Building a Nautilus `TradingNode` is allowed from validated config, but starting it requires `run_live_node=true`, `manual_live_node_start=true`, and the confirmation token `I_UNDERSTAND_THIS_CONNECTS_TO_IB`.

Reason: Starting the LiveNode can connect to Interactive Brokers. The default development path must remain offline-safe and data-only, while still allowing an explicit manual smoke-test path later.

## DR-0014: Manual Smoke Command Before Live Subscriptions

Status: accepted

Add a separate `markeitech-market-data-smoke` command for manual IB smoke testing.

Reason: The normal dry-run CLI should remain harmless. Any command that may start the Nautilus LiveNode must be visually distinct, print the validated plan first, require explicit config flags, and require the confirmation token. Automated tests must use fake nodes rather than IB.

## DR-0015: Ordered LiveNode Actions Before Real Calls

Status: accepted

Translate Nautilus request intents into ordered LiveNode actions before wiring real Nautilus method calls.

Reason: Warmup requests must happen before live subscriptions, active/background ownership must stay deterministic, and duplicate actions must be caught before any IB connection. A fake-friendly action executor keeps this layer testable without TWS or IB Gateway.

## DR-0016: Actor-Owned Asynchronous Warmup Gate

Status: accepted

Execute market-data actions through a Nautilus `Actor` and require all historical request callbacks plus a successful warmup analysis handler before any live subscription is submitted.

Reason: Nautilus historical requests are asynchronous, so request call order alone cannot guarantee that instruments are analyzed and annotated before live tracking. The coordinator makes readiness explicit, blocks subscriptions on missing history or analysis failure, and gives the later analytics engine a stable historical snapshot boundary.

## DR-0017: Make-Before-Break Active Instrument Switching

Status: accepted

Promote only enabled, warmed background instruments. Subscribe candidate trade and quote ticks and require data from both streams before atomically changing logical active ownership and removing the previous active tick subscriptions. Keep 1-minute bars subscribed for every monitored instrument throughout the handover.

Reason: Waiting for candidate data avoids a blind interval during an operator switch. A short overlap in physical tick subscriptions is acceptable because exactly one instrument remains logically active. Timeout and failure rollback preserve the previous active instrument and prevent a partially ready candidate from taking ownership.

## DR-0018: Canonical Normalization At The Actor Boundary

Status: accepted

Normalize Nautilus ticks and bars immediately inside the market-data actor, preserve original nanosecond timestamps and decimal values, and route canonical events into isolated per-instrument snapshots before persistence or presentation.

Reason: Nautilus remains the live runtime authority while Markeitech needs stable, versioned contracts for analytics, storage, and the dashboard. Preserving raw timestamp precision prevents tick identity loss. External IB bars retain unknown-side volume, while active tick-built bars expose only classification that can be supported by observed trades and quotes.

## DR-0019: Observe Health Without Duplicating Reconnect Ownership

Status: accepted

Track role-based stream freshness and external-bar continuity inside Markeitech, while leaving the physical Interactive Brokers reconnect and retry lifecycle to NautilusTrader.

Reason: The product needs explicit waiting, stale, gap, degraded, and recovered states for persistence and operator visibility. A second connection-recovery loop would compete with Nautilus and risk duplicate subscriptions. Session-open policy remains injectable so stale thresholds are evaluated only when data is expected.

## DR-0020: Duration-Limited Paper IB Acceptance Gate

Status: accepted

Complete Stage 2 with a manually confirmed, duration-limited paper Interactive Brokers run which starts the real prepared LiveNode, captures observable runtime state, stops gracefully, and emits a structured acceptance report.

Reason: Offline tests cannot prove contract resolution, entitlements, historical response behavior, live tick delivery, or IB bar timing. A bounded command is safer and more diagnosable than an indefinite smoke process, while the existing read-only, data-only, no-execution, and confirmation-token guards remain mandatory.

The first paper connection revealed that the IB instrument provider must preload every enabled registry instrument. The TradingNode config therefore supplies those IDs through `InteractiveBrokersInstrumentProviderConfig.load_ids` before any actor warmup request is submitted.

A closed-market paper run also revealed that IB can emit sentinel quote values such as `-1/-1` immediately after subscription. These values are recorded as dropped normalization events and do not enter canonical state, satisfy switch readiness, or escape into the Nautilus data queue as exceptions.
