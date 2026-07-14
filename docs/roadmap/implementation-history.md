# Detailed Implementation History

This document preserves the reviewed slices, stop conditions, and implementation
outcomes that brought Markeitech to its current boundary. It includes historical
phrasing such as “deferred” and earlier stage ownership; those statements record
the sequence at that time rather than reopening completed gates.

Use [current status](../current-status.md) for actual completion and the
[implementation roadmap](implementation-roadmap.md) for future intent. BTC and
crypto references below record an early continuous-market test and calendar
coverage; they are not active product scope.

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

Original target: deliver Nautilus-compatible Parquet/catalog storage, SQLite metadata and durable notification outbox, optional hot runtime coordination, idempotent writes, restart recovery tests, and source/fidelity lineage for IB-first canonical data. Redis was deliberately deferred because no demonstrated coordination requirement justified it.

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

Seventh implementation slice:

- Add a provider-neutral session-calendar protocol which returns expected one-minute opens.
- Provide an explicit session-window implementation for deterministic tests and later calendar adapters.
- Exclude weekends, holidays, and maintenance breaks before classifying missing bar intervals.
- Normalize and merge only contiguous expected missing minutes.
- Bound recovery lookback, intervals per request, and requests per plan.
- Split deterministic historical bar requests without spanning expected session closures.
- Classify journal replay as exact, historical bar repair as reported, optional historical tick repair as partial, and unavailable tick gaps honestly.
- Preserve out-of-lookback bar damage as unavailable rather than silently clipping it.
- Persist pending, recovering, complete, and degraded recovery lifecycles without terminal-state regression.
- Keep provider calendar selection, actual IB requests, LiveNode wiring, Redis, and notification delivery out of this slice.

Eighth implementation slice:

- Add an optional persistence section to the market-data runtime configuration.
- Compose the Parquet catalog, SQLite metadata store, idempotent coordinator, durable journal, bounded writer, and actor-facing ingress as one persistence runtime.
- Start the persistence writer and finish exact journal replay before the LiveNode starts actors or subscriptions.
- Route validated native Nautilus trade and quote ticks to persistence without converting away their native schemas.
- Route only completed canonical one-minute bars to persistence; ignore provisional tick-built bars and unrelated canonical events.
- Keep market-data callbacks non-blocking and expose accepted, rejected, tick-gap, and bar-recovery-required ingress health.
- Treat rejected ticks as known fidelity damage and rejected completed bars as historical-recovery obligations.
- Stop the LiveNode before forcing the bounded persistence flush and closing SQLite metadata.
- Scope one-minute-bar dedupe identity by source so reported and tick-built bars for the same instrument and minute can coexist.
- Keep provider calendar selection, actual historical recovery requests, Redis, and notification delivery out of this slice.

Ninth implementation slice:

- Pin `pandas-market-calendars` behind the existing provider-neutral session-calendar protocol.
- Require every instrument contract to declare an explicit calendar identifier and session profile rather than inferring hours from exchange or security type.
- Support full, regular, and continuous session profiles; use a native 24/7 calendar for continuous instruments.
- Interpret full equity sessions as published premarket through postmarket hours and regular sessions as market open through market close.
- Split expected minute windows around published breaks and interruptions.
- Normalize all generated expectations to UTC while preserving exchange DST, holidays, and early closes.
- Bound query ranges and maintain a thread-safe, per-runtime LRU of generated schedules.
- Map NQ and ES to `CME_Equity`, SPX to the US regular cash session, and BTC to native 24/7 behavior in checked-in configuration.
- Add golden tests for CME halts and early closes, NYSE holidays and DST transitions, equity extended hours, and weekend crypto operation.
- Keep actual IB historical recovery requests, provider schedule reconciliation, Redis, and notification delivery out of this slice.

Tenth implementation slice:

- Use the ordinary multi-timeframe historical warmup as the first recovery evidence wave for every enabled product instrument.
- Normalize and durably persist returned one-minute warmup bars without routing them into live counters.
- Force a bounded writer flush before recovery planning and verify observed opens from Parquet rather than trusting accepted queue submissions.
- Plan only unresolved calendar-aware one-minute gaps after the coarse warmup response.
- Map deterministic recovery requests to exact Nautilus historical bar ranges.
- Interleave requests fairly across instruments and execute one repair at a time so one instrument cannot consume the recovery queue.
- Flush again after targeted responses, re-query durable bars, and persist independent complete or degraded recovery outcomes per instrument.
- Keep unrepaired historical gaps explicit without blocking otherwise valid minimum warmup analysis or live subscriptions.
- Persist repeated provider-empty evidence and stop retrying an interval only after the configured confirmation threshold; never synthesize an OHLC bar.
- Bound both per-instrument and aggregate request counts and fail closed when startup persistence cannot flush or verify.
- Include per-instrument recovery requests, before/after damage, provider-empty confirmations, and reason codes in paper acceptance reports.
- Cover CME futures, a US ETF, and a cash index through the same generic execution path.
- Keep historical tick backfill, Redis, notification delivery, and provider-specific schedule overrides out of this slice.

Eleventh implementation slice, part A:

- Replace the unbounded per-event JSON identity ledger with fixed-size SHA-256 fingerprints stored as raw SQLite BLOBs.
- Preserve the existing logical identity boundary: provider event metadata participates in the fingerprint, while local receipt timestamps do not make a retransmission distinct.
- Retain exact instrument, event-kind, source, event timestamp, batch, and commit columns beside each fingerprint so later retention can prune metadata by durable stream and event time.
- Fail closed when a dedupe fingerprint resolves to a different logical identity fingerprint.
- Migrate populated schema-version-three databases transactionally without losing committed dedupe evidence.
- Validate the migration against a copy of the Stage 3 live database before applying retention policy to production data.
- Defer physical database compaction to explicit maintenance; schema migration must not introduce an unbounded startup `VACUUM`.
- Keep session-aware catalog retirement, metadata pruning, maintenance scheduling, and storage-budget enforcement in the next reviewable part of this slice.

Eleventh implementation slice, part B:

- Add opt-in retention maintenance at the quiescent startup boundary before the persistence writer accepts new events.
- Derive tick and bar cutoffs from completed product sessions rather than elapsed days; an in-progress session does not consume one retained session.
- Inspect typed Parquet `ts_event` statistics and retire only whole files whose newest event is older than the applicable cutoff.
- Keep mixed-age files intact and pin SQLite pruning to their oldest retained event so every retained row keeps its dedupe protection.
- Delete and directory-sync catalog files before transactionally pruning compact identities and now-empty committed batch manifests.
- Skip maintenance when ingress WAL files or incomplete persistence batches require recovery, and repeat safely on a later startup.
- Reconstruct streams from both Parquet and SQLite so a restart can finish metadata pruning after a crash that deleted the final catalog file.
- Retain unmanaged instruments and report them explicitly; expired rollover contracts must remain configured as disabled instruments until their data ages out.
- Keep maintenance disabled by default until an operator explicitly enables deletion, and report inspected, deleted, and retained bytes without deleting recent evidence to meet an arbitrary disk quota.
- Keep controlled SQLite file compaction and persisted maintenance history in the next reviewable part of this slice.

Eleventh implementation slice, part C:

- Persist immutable audit records for every enabled retention attempt, including completed, no-op, unsafe-skipped, and failed outcomes.
- Persist manual SQLite compaction reports with before/after page counts, free pages, and reclaimed bytes.
- Keep SQLite compaction outside LiveNode startup and require an explicit offline command and confirmation token.
- Refuse compaction while ingress WAL files, incomplete persistence batches, or an active SQLite client prevent exclusive maintenance.
- Skip the rewrite when reclaimable free pages remain below a configurable threshold, defaulting to 16 MiB.
- Provide a checked-in PyCharm offline compaction runner and machine-readable JSON output.
- Keep automatic scheduling of database rewrites out of the runtime; ordinary retention can create free pages without imposing an unbounded startup pause.

## Stage 4: Analytics And Levels

Deliver deterministic derived analytics, levels, zones, volume profile support, provider-neutral feature snapshots, and the Direction and Location portions of the initial auction-market decision model.

In progress.

### Stage 4A: Baseline Live Market Context

- Build versioned per-instrument, per-timeframe context after the all-instrument warmup gate.
- Calculate EMA 20/50/200 and ATR 14 with Nautilus indicators, plus session VWAP, session range position, confirmed swing support/resistance, and an explicit trend state.
- Aggregate configured 5m, 15m, 30m, and 1h contexts only from complete consecutive canonical 1m bars; never fabricate a higher-timeframe bar across a missing minute.
- Label provider-reported, tick-inferred, and mixed analytics inputs explicitly.
- Update active and background instruments equally from completed live 1m bars, while the active instrument retains its tick-by-tick data path.
- Expose structured context logs and include the latest snapshots in the duration-limited paper acceptance report.

Stage 4A baseline implementation is complete. Feature persistence, aggression, signals, ML, Discord delivery, and UI remain later slices.

### Stage 4D/4E Fast-Track Operator Context

Implemented on the dedicated usable-context branch ahead of the normal persistence sequence:

- Emit a clearly bounded warmup context block before live subscriptions, including configured 1h history.
- Calculate previous product-session high/low from 1m history.
- Calculate DST-aware London and New York developing ranges plus 15m and 30m opening ranges.
- Detect confirmed, still-unfilled three-bar FVGs independently on each context timeframe.
- Build current, prior, London, and New York 70% value-area profiles using per-instrument price bins.
- Label candle-derived profiles as inferred with methodology `bar_range_uniform_volume`; do not describe them as footprint or authoritative trade-at-price data.
- Emit deterministic Direction/Location context from EMA trend, session VWAP, session quartile, profile location, nearby support/resistance, and active FVG location.

This fast-track work remains subject to later persisted-data replay and value-integrity comparison before signals or automation depend on it.

### Stage 4B: Live Analytics Operationalization

Proceed live-first. Keep contracts, timestamps, lineage, fidelity, and deterministic calculations replay-compatible, but defer construction of the replay runtime while live operation is the product priority.

- Prove every requested warmup timeframe reaches a bounded freshness threshold near boot time.
- Publish explicit analytics readiness, freshness, history-depth, and degraded-input evidence.
- Refine profile granularity and combinations without overstating candle-derived precision.
- Replace high-volume diagnostic logs with bounded periodic operator context reports.
- Define restart restoration and derived-state ownership for the continuous LiveNode path.
- Preserve stable replay inputs and pure deterministic calculation boundaries for the later replay stage.

Implemented slices:

- Timeframe-specific history requirements, daily-first warmup context, session-aware freshness, independent indicator-depth classification, bounded readiness logs, subscription gating, and acceptance evidence. Exactly one stale 1m interval is tolerated as degraded startup evidence so a sequential warmup crossing a minute boundary cannot create an endless restart race; larger 1m lag still blocks.
- Restart-safe sequential IB warmup with bounded retries, followed by an active-first operator briefing and change-aware periodic context reports capped at three lines per changed instrument. Full context snapshots continue through the structured callback boundary and DEBUG JSONL evidence path.
- Instrument-specific profile refinement with explicit rolling 2-session and 5-session composites, observed-window lineage, developing state, exact-session-count gating, and finer NQ/ES bins. Existing current-session profile-location semantics remain unchanged.
- Restart-continuous higher-timeframe aggregation by seeding only currently forming session-aligned buckets from warmup 1m bars, preserving mixed provider/tick lineage, rejecting missing minutes, and avoiding duplicate completed-bucket emissions.

Canonical bars and versioned configuration own restart truth; mutable derived internals are rebuilt rather than restored. All candle-derived profiles remain inferred. Persisted feature audit history and later live-versus-replay comparison remain before signals can depend on composites.

### Stage 4C: Durable Feature Snapshots

Persist deterministic analytics independently from human-readable logs before signals depend on them.

First implementation slice:

- Add a versioned market-context feature envelope containing calculation version, configuration fingerprint, exact input-stream lineage, and the complete provider-neutral context snapshot.
- Derive feature identity from calculation/configuration identity plus sorted input-lineage fingerprints, instrument, timeframe, `as_of`, source, and fidelity.
- Hash output content independently so the same deterministic identity producing different values fails as nondeterminism instead of silently overwriting history.
- Store immutable feature payloads in Markeitech-owned PyArrow Parquet partitions by feature set, instrument, timeframe, and UTC date.
- Use deterministic batch files, `fsync`, and atomic creation; collapse exact retries while retaining legitimate revised-input variants at the same `as_of`.
- Query ordered feature history and every latest-as-of variant without selecting an arbitrary revision.
- Keep SQLite feature commit manifests, bounded asynchronous actor wiring, operational counters, and live acceptance evidence in the next reviewable slice.

Feature Parquet is separate from the Nautilus raw-market catalog. SQLite proves feature commit state after catalog durability and may later accelerate broader identity lookup, but Parquet remains the feature payload truth. Signals remain out of scope until the live feature writer and restart audit path are complete.

Narrowed Stage 4C.2 delivery for the first live signal path:

- Add catalog-first SQLite feature commit manifests and conflict detection.
- Build exact feature lineage from the analytical bars actually consumed by each context snapshot.
- Add a bounded asynchronous feature writer and wire warmup/live snapshots through the existing actor sink.
- Expose accepted, committed, duplicate, rejected, pending, and failed writer evidence and force a bounded shutdown flush.
- Prove live-node composition, restart idempotency, and active/background feature persistence.

Deferred explicitly, not removed: feature retention policy, SQLite lookup optimization and pruning, a standalone feature inspection CLI, broad historical feature backfill, and full live-versus-replay value comparison. Those return after the first deterministic signal candidate lifecycle; signals may consume only successfully submitted versioned feature envelopes and must retain their feature ids.

## Stage 5: Signals

Deliver deterministic signal lifecycle, scoring, dedupe, persistence, notification-ready domain events, and the first Direction-Location-Aggression setup family with explicit evidence fidelity. Optional ML inference may rank setups only after a deterministic baseline exists.

Stage 5 is split into reviewable slices:

- **5A - Contracts and lifecycle:** immutable signal snapshots, deterministic setup/signal/transition identity, typed evidence references, explicit fidelity, and fail-closed lifecycle transitions.
- **5B - Durable signal state:** SQLite signal snapshots and append-only transitions, optimistic conflict detection, restart restoration, and atomic notification-outbox enqueue where policy requires delivery.
- **5C - Direction/Location candidates:** deterministic candidate qualification from committed market-context feature ids, stable setup anchors, scoring configuration, invalidation, expiry, and active/background parity.
- **5D - Aggression and follow-through:** bounded IB trade/top-of-book evidence windows, honest inferred/partial/unavailable semantics, arming and triggering rules, and tick-gap degradation.
- **5E - Live operationalization:** actor/runtime wiring, human-readable signal logs, notification-ready events, restart and saturation evidence, and a live shadow acceptance run before Discord delivery.

Stage 5A is complete. A candidate is decision support, not an order instruction. Direction and Location require market-context feature evidence; Aggression may later use a deterministic market-data window. No lifecycle state may skip required evidence, move backward, or mutate after invalidation/expiry.

Stage 5B is complete. SQLite retains the immutable initial-candidate hash, current snapshot, and append-only sequenced transition events. Candidate and transition retries are idempotent; optimistic prior-content checks reject competing progression. Restart reads verify the complete transition hash chain reaches current state. A transition and its optional pending notification-outbox record commit or roll back together, without embedding destination policy in signal logic.

Stage 5C is divided further so market semantics remain reviewable:

- **5C.1 - Named Direction definitions:** versioned per-instrument definition enablement, committed multi-timeframe feature bundles, configurable Direction qualification, stable regime anchors, and restart seeding. The first definition uses 1h+15m Direction, 5m confirmation, and degrading daily context. A later scalp definition may use 15m+5m/1m without changing the signal family.
- **5C.2 - Location and candidate progression:** define deterministic location qualification, arm candidates at actionable auction locations, and invalidate or expire stale setups.
- **5C.3 - Live composition:** build point-in-time bundles only from durably committed features, persist evaluator decisions, restore open regimes, and apply the same definitions to active and background instruments.

Stage 5C.3 is split at the asynchronous durability boundary:

- **5C.3a - Committed feature handoff:** assign restart-stable commit sequence, publish exact verified revisions through an atomic bounded queue, and maintain deterministic per-instrument point-in-time feature state.
- **5C.3b - Live signal runtime:** consume committed revisions, restore open Direction/Location state, evaluate enabled definitions, and persist episode/arming decisions for active and background instruments.
- **5C.3c - Console projection:** expose change-aware human-readable signal and runtime-health logs without making presentation output a source of truth.

Stage 5C.3a is complete. Stage 5C.3b now owns a bounded consumer thread under the managed LiveNode lifecycle. It restores verified open Armed/Triggered episodes, rebuilds point-in-time state from committed warmup revisions without emitting historical setups, evaluates every enabled definition from the first post-start evaluation bar, and atomically persists episode entry, replacement, and exit. Stage 5C.3c remains presentation-only console projection and operational acceptance evidence.

Stage 5C.1 is complete. It remains a pure decision boundary; the Stage 5C.3 runtime now consumes it without moving live concerns into the evaluator.

Stage 5C.2 uses repeatable location episodes rather than one trade setup for an entire Direction regime:

- **5C.2a - Location contracts and policy:** canonical zone identity, exact feature revisions, structured price matches, and source-specific timeframe/tolerance configuration.
- **5C.2b - Zone derivation and matching:** derive direction-aligned structural, FVG, value-edge, and VWAP zones from committed features and match price without look-ahead.
- **5C.2c - Repeatable episodes:** suppress duplicates while price remains in one semantic zone and allow a new setup only after exit and re-entry.
- **5C.2d - Armed lifecycle:** persist Candidate and Candidate-to-Armed progression, invalidation, expiry, and restart restoration.

Stage 5C.2a is complete. It does not itself derive zones or change signal lifecycle state.

Stage 5C.2b is complete. It derives only direction-aligned zones from configured committed features, requires an explicit product-session start for session-scoped identity, applies source-specific ATR proximity, and returns qualified, not-at-location, missing-evidence, or insufficient-confluence outcomes. It does not create location episodes or arm signals.

Stage 5C.2c is complete. It converts point-in-time qualification into idempotent enter, active, exit-pending, exited, replaced, and evidence-gap decisions. Same-zone overlap remains one episode, disjoint qualified zones replace immediately, ordinary exit requires a configurable number of consecutive observed bars, and missing evidence preserves the episode while breaking that sequence.

Stage 5C.2d is complete. Episode entry deterministically creates a Candidate and Armed transition carrying the Direction regime, episode id, structured entry matches, and complete Direction/Location feature evidence. Initial creation and replacement commit atomically in SQLite; conflicts roll back all affected signal and outbox state. Verified open Armed/Triggered snapshots reconstruct both trackers after restart. Episode exit/replacement invalidates Armed state. Time-based Armed expiry remains coupled to the Stage 5D aggression observation policy rather than using an arbitrary pre-aggression timeout here.

Future stages previously listed here now live only in the active
[implementation roadmap](implementation-roadmap.md). Keeping unstarted work out
of the history prevents an old sequence from becoming an accidental requirement.
