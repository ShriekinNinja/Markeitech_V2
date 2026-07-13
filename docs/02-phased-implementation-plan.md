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

Sixth implementation slice:

- Map Nautilus request intents into ordered LiveNode actions.
- Keep warmup historical bar requests before live subscriptions.
- Add a fake-friendly action executor protocol.
- Include LiveNode actions in dry-run output.
- Do not call real Nautilus subscription methods yet.

Seventh implementation slice:

- Add a Nautilus `Actor` bridge for historical requests and live subscriptions.
- Coordinate asynchronous warmup completion instead of relying only on call order.
- Pass the completed historical snapshot through an injectable analysis handler before subscribing.
- Block all live subscriptions when warmup coverage or analysis fails.
- Register the IB data-client factory, attach the actor, and build the LiveNode before guarded startup.
- Keep automated tests on fake actors and nodes; the manual smoke command remains the only path allowed to connect to IB.

Eighth implementation slice:

- Add an internal active-instrument switch command and deterministic coordinator.
- Restrict promotion to enabled instruments after the boot warmup reaches live state.
- Subscribe the candidate trade and quote streams before changing logical ownership.
- Require both a candidate trade tick and quote tick before promotion.
- Preserve every 1-minute bar subscription throughout the handover.
- Unsubscribe the previous active tick streams only after candidate readiness.
- Roll back candidate streams on timeout or failure and repair previous-active subscriptions best-effort.
- Reject duplicate, concurrent, unknown, and already-active switch requests.
- Leave HTTP/WebSocket operator command transport to the gateway stage.

Ninth implementation slice:

- Normalize Nautilus trade ticks, quote ticks, and external 1-minute bars into Markeitech domain events.
- Preserve source nanosecond timestamps alongside UTC datetimes and retain venue trade IDs.
- Route every event to isolated per-instrument runtime snapshots.
- Classify subscribed trades against the latest valid same-instrument quote.
- Build provisional active-instrument 1-minute bars from classified ticks and complete them on minute rollover.
- Mark tick-built provisional/completed bars separately from completed IB external bars.
- Emit normalized events through an injectable runtime sink for later persistence and WebSocket stages.
- Reject data for instruments outside the configured runtime registry.
- Defer stale-data, gap, retry, and reconnect policy to the next Stage 2 hardening slice.

Tenth implementation slice:

- Track required live streams by current instrument role.
- Mark streams as waiting, healthy, stale, or session-paused using configurable thresholds.
- Produce per-instrument readiness and source-level health snapshots.
- Detect missing external 1-minute intervals and keep gaps open until late bars recover them.
- Ignore provisional tick-built bars when evaluating authoritative external-bar continuity.
- Re-evaluate health on a one-second actor timer and emit only semantic transitions.
- Recalculate required streams immediately after an active-instrument switch.
- Inject session-open policy so closed markets can pause stale-data expectations.
- Leave physical IB reconnect and transport retries to NautilusTrader; Markeitech owns observable degradation and recovery state.

Eleventh implementation slice:

- Add a guarded, duration-limited paper Interactive Brokers acceptance command.
- Run the prepared LiveNode asynchronously and stop it gracefully after the requested duration.
- Preserve the existing config flags and explicit confirmation-token startup boundary.
- Grade warmup completion, active trade and quote ticks, completed bars for every enabled instrument, source health, read-only mode, and execution-disabled posture.
- Emit a structured JSON pass/fail report after shutdown.
- Keep automated coverage on fake actors and nodes.
- Use an ignored local config for actual paper TWS/Gateway settings; keep checked-in examples offline-safe.
- Start the first acceptance pass with NQ active and ES background, then expand entitlements and instruments independently.

## Stage 3: Persistence And Recovery

Deliver Nautilus-compatible Parquet/catalog storage, SQLite metadata and durable notification outbox, Redis hot runtime coordination, idempotent writes, restart recovery tests, and source/fidelity lineage for IB-first canonical data.

First implementation slice:

- Add source-scoped persistence event identities for trades, quotes, and one-minute bars.
- Distinguish reported, inferred, partial, and unavailable data fidelity.
- Require derivation metadata for inferred and partial evidence.
- Define stream checkpoints and explicit recovery lifecycle records.
- Define a durable notification outbox lifecycle with non-secret destination references.
- Reject webhook credentials and other delivery secrets from nested outbox payloads.
- Add bounded writer, batching, retention, lease, and retry configuration.
- Keep Nautilus catalog, SQLite metadata, and outbox implementations behind narrow protocols.
- Preserve a single serialized catalog-writer ownership boundary because the Nautilus Parquet catalog is not thread-safe.

Second implementation slice:

- Add a concrete `ParquetDataCatalog` adapter behind the time-series storage protocol.
- Store raw valid Nautilus `TradeTick` and `QuoteTick` objects using native catalog schemas.
- Register a custom Arrow type for completed canonical one-minute bars so classified volume, source, revision, completion, schema, and dedupe fields are not lost.
- Encode canonical decimal fields as strings for exact precision across Parquet round trips.
- Partition native ticks and canonical bars by instrument identity through Nautilus catalog identifiers.
- Reject unsupported objects, provisional bars, and oversized batches before writing.
- Serialize concurrent catalog writes with one ownership lock and propagate catalog failures without returning successful identities.
- Prove exact nanosecond, decimal, source, and instrument round trips with temporary catalogs and no IB connection.

Third implementation slice:

- Add a versioned SQLite metadata store with idempotent, auditable migrations.
- Enable foreign keys, WAL mode, full synchronous durability, and configurable busy timeout.
- Persist source-scoped checkpoints without allowing stream progress to move backward.
- Persist explicit recovery lifecycles, readiness state, and gap state with monotonic updates.
- Store UTC timestamps as indexed integer nanoseconds and structured payloads as deterministic JSON.
- Enqueue notification records idempotently through unique dedupe keys.
- Atomically lease available or expired outbox records across independent worker connections.
- Require lease ownership when marking delivery success or failure.
- Preserve retry timing, attempt counts, errors, and delivered state across restart.
- Roll back every transaction on failure and refuse database schemas newer than the application supports.
- Keep Parquet/SQLite coordination, live actor wiring, gap calculation, Discord delivery, and Redis out of this slice.

Fourth implementation slice:

- Add deterministic, content-addressed persistence batches scoped to one instrument, source, event kind, and fixed `ts_init` bucket.
- Extend persistence identities with exact initialization timestamps because Nautilus catalog file ownership is based on `ts_init`.
- Add SQLite batch manifests with prepared, catalog-written, and committed states.
- Add a compact committed-event identity ledger with unique dedupe keys and full-identity conflict detection.
- Sort batch membership deterministically and hash the ordered identities before any catalog write.
- Filter exact historical/live overlap before writing and treat exact retry as a no-op.
- Write Parquet before atomically committing the identity ledger and stream checkpoint in SQLite.
- Inject process failures after prepare, physical catalog write, catalog acknowledgement, and metadata commit.
- Resume every incomplete crash window without duplicate catalog data or premature checkpoint progress.
- Allow delayed events to commit without moving an already-newer stream checkpoint backward.
- Keep live actor wiring, missing-interval calculation, targeted IB recovery, Redis, and notification delivery out of this slice.

Fifth implementation slice:

- Add one bounded asynchronous writer owner between market-data callbacks and blocking storage.
- Accept native Nautilus trade and quote ticks plus completed canonical one-minute bars.
- Reject unsupported and provisional events before they consume queue capacity.
- Return explicit accepted, full, stopped, failed, unsupported, and provisional outcomes.
- Group events by source, instrument, event kind, and fixed initialization-time bucket.
- Sort closed buckets deterministically and split them into stable configured-size chunks.
- Persist only through the idempotent coordinator and expose queue, write, duplicate, rejection, batch, and failure health.
- Fail closed after a storage error without silently dropping pending events.
- Force a bounded flush during graceful shutdown.
- Keep real LiveNode wiring, restart-driven historical recovery, Redis, and notification delivery out of this slice.

Sixth implementation slice:

- Add a versioned, append-only ingress write-ahead journal scoped to deterministic stream buckets.
- Serialize native Nautilus trade and quote ticks with Nautilus `MsgSpecSerializer` and canonical bars from declared versioned fields.
- Checksum every record, bound record and total journal sizes, and fail closed on confirmed corruption or exhausted capacity.
- Repair only a torn final write; never reinterpret a complete record with a checksum mismatch.
- Flush and `fsync` journal payloads and directory entries before events enter open persistence buckets.
- Distinguish accepted, journaled, recovered, and committed writer counts.
- Replay WAL buckets before accepting new live events after restart.
- Retain each WAL file until every deterministic chunk has committed through Parquet and SQLite.
- Prove exact replay across every coordinator crash boundary without duplicate durable events.
- Keep missing-interval planning, targeted IB recovery, LiveNode wiring, Redis, and notification delivery out of this slice.

## Stage 4: Analytics And Levels

Deliver deterministic derived analytics, levels, zones, volume profile support, provider-neutral feature snapshots, and the Direction and Location portions of the initial auction-market decision model.

Not started.

## Stage 5: Signals

Deliver deterministic signal lifecycle, scoring, dedupe, persistence, notification-ready domain events, and the first Direction-Location-Aggression setup family with explicit evidence fidelity. Optional ML inference may rank setups only after a deterministic baseline exists.

Not started.

## Stage 6: Notifications And Reports

Deliver one-way Discord webhook alerts and analysis reports through a durable, rate-limited, retryable notification pipeline. AI-generated narrative must remain grounded in persisted structured evidence. Do not build a Discord bot.

Not started.

## Stage 7: Strategy Runtime

Deliver isolated strategy worker topology, bounded queues, lag metrics, state restoration, controlled lifecycle, and shadow/paper evaluation for model-assisted strategies.

Not started.

## Stage 8: Backtesting And Replay

Deliver NautilusTrader-based backtesting, reproducible replay datasets, and versioned ML training, calibration, and comparison workflows.

Not started.

## Stage 9: WebSocket Gateway

Deliver snapshot-first WebSocket streaming, bounded client queues, resync behavior, readiness, health, gap, analytics, and signal events for future presentation clients.

Not started.

## Stage 10: Frontend Dashboard

Deliver an operational cockpit with active-instrument chart, session context, readiness, source health, gaps, analytics, levels, background signals, and reconnect behavior.

Not started.

## Stage 11: Execution And Risk Controls

Deliver explicitly configured paper/live execution with risk checks, auditability, and no accidental live orders.

Not started.
