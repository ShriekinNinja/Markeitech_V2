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

## DR-0021: Discord Webhooks Before Frontend Presentation

Status: accepted

Prioritize persistence, analytics, signals, one-way Discord notifications, strategy runtime, and replay ahead of the WebSocket gateway and frontend dashboard. Use Discord incoming webhooks for initial signal alerts and analysis reports; do not build a Discord bot.

Signal and analytics services emit transport-neutral versioned domain events. Stage 3 provides a durable notification outbox, and the notification stage owns routing policy, formatting, batching, deduplication, rate-limit handling, retries, and delivery state. Discord webhook URLs remain secret configuration and are never stored in outbox payloads or source control.

Reason: One-way webhooks provide a useful human-facing operator surface without making UI delivery an early dependency. The durable outbox prevents Discord availability from affecting ingestion or losing signal transitions, while transport-neutral events preserve the future WebSocket and frontend architecture. A bot adds inbound command, authentication, and operational-authority concerns that are not currently required.

## DR-0022: IB-First And Provider-Ready Data Fidelity

Status: accepted

Implement Interactive Brokers as the sole initial live provider while keeping canonical trades, quotes, bars, and future depth events provider-neutral. Preserve source identity, original timestamps, source identifiers, and derivation methodology. Distinguish reported, inferred, partial, and unavailable evidence in analytics and signals.

Reason: The platform should extract the best defensible information from the available IB feed without delaying delivery for speculative provider integrations. A narrow canonical adapter boundary allows future providers to improve fidelity without forcing analytics, signals, persistence, or strategies into IB-specific contracts. Inferred aggressor side, delta, absorption, footprint, and depth evidence must never be presented as authoritative when the source cannot support that claim.

## DR-0023: Deterministic Core Before ML Or AI Authority

Status: accepted

Build deterministic analytics and versioned feature snapshots before adding ML inference. ML models may classify regimes, detect anomalies, or rank setups through versioned inference events, but must pass offline evaluation, replay, and shadow operation before affecting signals or strategies. AI agents may explain persisted evidence and compose reports, but may not connect directly to IB, mutate durable truth, invent unavailable evidence, or control execution.

Reason: Models and agents can add useful ranking and interpretation without becoming opaque owners of market state. Explicit model, feature-schema, input-lineage, output-semantics, and latency metadata make inference reproducible and auditable. Keeping generated narrative separate from deterministic facts preserves operator trust and allows models to be replaced safely.

## DR-0024: Direction-Location-Aggression Decision Model

Status: accepted

Use Direction-Location-Aggression as the first formal auction-market decision-support model. Stage 4 establishes market condition or direction and identifies/refines locations using deterministic session, structure, and volume-profile evidence. Stage 5 adds aggression and follow-through evidence plus a versioned setup lifecycle. Begin as decision support rather than automated execution.

Reason: The model composes naturally from planned analytics while enforcing patience: direction alone is not an entry, and location requires observed participation. The aggression step is experience-sensitive and depends on data fidelity, so IB-derived trade and top-of-book evidence must be labeled honestly, captured for replay, and validated before automation or ML ranking is trusted.

## DR-0025: Native Tick Catalog And Custom Canonical Bars

Status: accepted

Persist raw valid Nautilus `TradeTick` and `QuoteTick` objects through their native Parquet catalog schemas. Persist completed canonical one-minute bars through a registered custom Arrow record which preserves classified volumes, source, revision, completion, schema version, and dedupe identity. Encode canonical decimals as strings and reconstruct immutable domain bars on read.

Serialize all calls into a catalog instance because Nautilus documents `ParquetDataCatalog` as not thread-safe. Validate bounded batches before writing and return persistence identities only after the catalog write succeeds. SQLite checkpoints remain a later metadata concern and must never advance after a failed catalog call.

Reason: Native tick schemas maximize Nautilus replay compatibility, while flattening canonical bars into native OHLCV bars would silently discard Markeitech-specific evidence. Exact decimal and nanosecond round trips preserve analytical fidelity. A narrow serialized adapter contains Nautilus custom-data implementation details and leaves later queueing, idempotency, and checkpoint transactions outside the catalog itself.

## DR-0026: SQLite As Transactional Metadata Control Plane

Status: accepted

Use versioned local SQLite storage for stream checkpoints, recovery lifecycles, readiness, gap state, and durable notification outbox state. Store timestamps as integer UTC nanoseconds and structured payloads as deterministic JSON. Enable WAL, foreign keys, full synchronous durability, configurable busy timeout, monotonic state updates, and explicit immediate write transactions.

Parquet remains authoritative for market events. A catalog write must succeed before SQLite progress advances. If a process stops after Parquet succeeds but before the checkpoint commits, recovery may safely revisit an overlap; later idempotency removes duplicates. The inverse ordering, where SQLite advances before durable market data exists, is prohibited.

Outbox enqueue uses a unique dedupe key. Claims atomically lease pending, retryable, or expired work across separate connections, and only the active lease owner may mark success or failure. Migration history is auditable and idempotent, and databases with newer unknown schema versions fail closed.

Reason: Mutable operational state needs transactions, uniqueness, conditional updates, and efficient point reads, while high-volume market history needs Nautilus-compatible columnar storage. The hybrid design accepts a recoverable at-least-once overlap window in exchange for keeping each data class in its natural storage engine.

## DR-0027: Deterministic Batches And At-Least-Once Recovery

Status: accepted

Coordinate Parquet and SQLite through content-addressed persistence batches scoped to one instrument, source, event kind, and closed fixed initialization-time bucket. Sort event identities by `ts_init` and dedupe key, hash the ordered identity set, and persist a batch manifest through prepared, catalog-written, and committed states.

Write the exact Parquet batch before atomically committing its full identity ledger and stream checkpoint in SQLite. On retry, compare complete stored identities rather than dedupe keys alone. Exact duplicates are ignored; a reused key with different identity metadata is corruption. Delayed events may commit to the ledger without moving a newer checkpoint backward.

Reason: Parquet and SQLite cannot share an atomic transaction. Deterministic batch membership turns the ambiguous crash window after a catalog write into an exact retry, which Nautilus handles by skipping the same file. The identity ledger handles historical/live overlap and proves checkpoint membership without copying market payloads into SQLite. Failure injection at every boundary demonstrates at-least-once processing without duplicate durable events or false progress.

## DR-0028: Capability-Driven Nautilus Ownership

Status: accepted

Use NautilusTrader where it provides mature trading-runtime capability that Markeitech would otherwise need to rebuild: instrument models, provider connectivity, subscription and reconnect lifecycle, clocks, replay and backtesting, strategy lifecycle, execution, portfolio, and account handling. Keep Markeitech ownership of product-specific canonical contracts, fidelity semantics, persistence coordination, analytics, signals, ML integration, notifications, and presentation boundaries.

Evaluate each new boundary on capability and guarantees rather than framework consistency. Do not adopt a Nautilus abstraction when it would weaken source fidelity, recovery behavior, provider portability, deterministic testing, or clear ownership of product behavior.

Reason: A signals-only application could be simpler without NautilusTrader, but the intended platform includes replay, strategies, execution, risk, and portfolio concerns where replacing a mature runtime would create substantial hidden work and operational risk. Explicit ownership limits preserve that leverage without forcing Markeitech-specific semantics into unsuitable framework abstractions.

## DR-0029: Non-Blocking Bounded Persistence Ingress

Status: accepted

Place one bounded asynchronous writer between live market-data callbacks and the blocking Parquet/SQLite coordinator. Submission never waits for storage and returns an explicit outcome. Queue capacity applies to all accepted but uncommitted events, including events already grouped into open buckets. A full or failed writer is observable and rejects new work; it must not silently discard an event or block the Nautilus callback thread.

Group native Nautilus ticks and completed canonical bars by source, instrument, event kind, and fixed initialization-time bucket. Close buckets by their deterministic time boundary, sort by initialization timestamp and dedupe key, and split oversized buckets into stable configured-size chunks. Force open buckets to flush during graceful shutdown. A storage exception fails the writer closed and retains uncommitted in-memory work for diagnosis.

Reason: Catalog and SQLite latency must not stall market-data handling, while an unbounded handoff would merely hide overload until memory exhaustion. Deterministic bucket membership preserves idempotent crash recovery, and explicit backpressure makes data-loss risk an operational state that later LiveNode wiring can degrade on immediately.

## DR-0030: Durable Bucket Journal Before Catalog Persistence

Status: accepted

Persist accepted native ticks and completed canonical bars to a local versioned, append-only, checksummed WAL before adding them to open persistence buckets. Scope WAL files to the same source, instrument, event-kind, and fixed initialization-time bucket used by the idempotent coordinator. Serialize native ticks with Nautilus `MsgSpecSerializer`; serialize canonical bars from declared versioned fields without computed properties.

Flush and `fsync` WAL payloads before reporting them journaled. Synchronize the containing directory when WAL files are created or removed. On restart, replay WAL buckets before accepting live submissions and remove a WAL only after every deterministic catalog and metadata chunk commits. Repair an incomplete final write by truncating to the last valid record, but fail closed on a complete checksum mismatch, unknown event type, invalid payload, oversized record, or exhausted configured capacity.

Reason: IB cannot reproduce every live quote or trade tick after a process crash, and an in-memory open bucket is therefore not a sufficient recovery source. Per-bucket WAL files preserve the exact payload and batch membership needed to resolve prepared, physically-written, catalog-acknowledged, and metadata-committed crash windows without turning SQLite into a second market-history store. The callback remains non-blocking; accepted and journaled are intentionally distinct operational states.

## DR-0031: Session-Aware And Fidelity-Honest Recovery

Status: accepted

Calculate missing one-minute bars only from a provider-neutral calendar of expected session opens. Exclude weekends, holidays, and maintenance breaks before merging contiguous gaps. Bound provider lookback, intervals per request, and requests per plan. Preserve expected gaps outside provider lookback as unavailable rather than silently clipping them.

Classify journaled tick replay as exact reported evidence. Historical bar backfill may restore reported bar continuity once every expected interval is verified. Any provider-supported historical tick request remains best effort and partial; an unjournaled tick gap with no defensible backfill is unavailable. Tick damage degrades tick-derived aggression, delta, absorption, and similar evidence without invalidating otherwise complete bar-based context. Recovery lifecycle state is durable and terminal states cannot regress.

Reason: Markeitech is a decision-support and later controlled-automation platform, not an HFT recorder. Honest fidelity and reproducible gaps matter more than pretending IB can reconstruct every quote or trade. Session-aware bar repair preserves the analytical history that materially affects the product while allowing isolated tick damage to reduce confidence instead of stopping the system.

## DR-0032: Persistence Owns The LiveNode Lifecycle Boundary

Status: accepted

When persistence is configured, wrap the prepared LiveNode with one persistence runtime. Start the durable writer and complete WAL replay before starting the node, actors, or subscriptions. Stop the node before forcing the writer's bounded final flush and closing SQLite. Send validated native Nautilus trade and quote ticks directly to the writer, and send only completed canonical one-minute bars through the canonical event sink.

Actor callbacks remain non-blocking. Rejected ticks become explicit fidelity gaps; rejected completed bars become historical-recovery obligations. Neither condition may be hidden as successful persistence. Scope canonical bar dedupe keys by source so an external reported bar and a classified-tick bar can coexist for the same instrument and minute.

Reason: Startup ordering prevents new live traffic from overtaking exact journal recovery, and shutdown ordering prevents producers from racing a closing store. A narrow ingress preserves Nautilus-native tick fidelity while keeping Markeitech's canonical event stream extensible. Explicit damage counters let later health and recovery stages distinguish tolerable tick loss from repairable bar continuity without stalling market-data handling.

## DR-0033: Explicit Product Calendars Behind A Provider-Neutral Boundary

Status: accepted

Use pinned `pandas-market-calendars` schedule rules behind Markeitech's `SessionCalendar` protocol. Require each enabled instrument contract to identify its product calendar and choose a full, regular, or continuous session profile. Never infer the calendar solely from exchange, asset class, or a related instrument. Use a native UTC 24/7 calendar for continuous products instead of approximating them with an exchange schedule.

For full equity profiles, include published premarket through postmarket hours when available. For regular profiles, use market open through market close. Split session windows around published breaks and interruptions before generating expected one-minute opens. Normalize output to UTC, bound query ranges and per-runtime schedule caching, and fail closed on unknown policy. Pin the package version because its calendars are shipped rules, not live exchange data; validate upgrades against golden holiday, early-close, maintenance, and DST cases and later reconcile representative schedules with observed IB history.

Reason: Recovery correctness depends on knowing whether a missing minute was actually expected. Explicit product policy handles CME futures, cash indices, equities, and crypto without pretending venue names imply identical sessions. The adapter preserves provider portability, while golden tests and a version pin contain the operational risk of calendar-rule corrections.

## DR-0034: One Fair And Durably Verified Startup Recovery Owner

Status: accepted

Keep ordinary warmup and targeted repair under one actor-side historical coordinator. Treat the existing multi-timeframe warmup as the first recovery evidence wave for every enabled non-crypto instrument. Persist its one-minute bars, force a bounded writer flush, and plan only gaps that remain in Parquet. Convert provider-neutral recovery requests into exact Nautilus historical ranges, interleave them round-robin across instruments, and issue one at a time. Flush and re-query durable bars before completing each instrument's recovery lifecycle.

Do not let one active instrument own recovery correctness for the watchlist. Every configured futures, cash-index, equity, or ETF instrument receives an independent plan and terminal result. A degraded historical result remains explicit but may continue through the existing minimum warmup and analysis gate. Fail startup closed when persistence cannot flush or recovery exceeds bounded request limits.

Treat a returned request with no bar as ambiguous rather than immediate data loss or an invented flat bar. Count that exact interval durably in SQLite and classify it as confirmed provider-empty only after repeated configured observations. Confirmed empties satisfy continuity checks without entering Parquet as market data. Rejected or non-durable returned bars remain persistence damage and cannot be mislabeled provider-empty.

Reason: A second historical requester would race warmup, duplicate IB traffic, and blur readiness ownership. Fair sequential repairs respect pacing across an equally important watchlist, while durable re-verification prevents request completion or in-memory acceptance from being mistaken for stored evidence. Repeated empty confirmation bounds retries without falsifying OHLC history.

## DR-0035: Compact Durable Event Identity Fingerprints

Status: accepted

Store committed per-event dedupe keys and logical persistence identities as fixed-size SHA-256 BLOB fingerprints rather than repeating full dedupe strings and JSON identity documents in SQLite. Keep the owning batch, instrument, event kind, source, event timestamp, and commit timestamp as typed columns so operational inspection and later retention remain deterministic. Exclude local receipt-time metadata from the logical identity fingerprint, preserving the existing rule that a provider retransmission is the same event even when Markeitech receives it again at a different time.

Treat any matching dedupe fingerprint with a different logical identity fingerprint as corruption and fail closed. Continue to store full market payloads in Parquet; the SQLite fingerprint ledger proves idempotency and batch ownership but is not a second market-history store. Migrate populated schema-version-three ledgers transactionally, and leave file-level compaction to controlled maintenance rather than adding an unbounded startup pause.

Reason: Full JSON identities caused SQLite metadata to grow at tick-data scale even though idempotency only requires stable identity evidence. Fixed-size fingerprints preserve duplicate and conflict detection while materially reducing durable metadata. Typed stream and event-time columns retain the information needed for conservative, session-aware retirement without restoring payload duplication.

## DR-0036: Catalog-First Session-Aware Retention

Status: accepted

Run opt-in retention only at a quiescent startup boundary before the persistence writer accepts events. Count completed product sessions through the explicit instrument calendar: keep five completed sessions of native ticks and 250 completed sessions of canonical bars by default, with the current incomplete session retained in addition. Inspect Parquet `ts_event` metadata and delete only a whole file whose maximum event timestamp is older than its stream cutoff. A mixed-age file remains intact, and its minimum event timestamp lowers the corresponding SQLite prune boundary.

Synchronize catalog-directory deletions before pruning compact event identities and empty committed batch manifests in one SQLite transaction. Never prune while ingress WAL files or prepared/catalog-written batches exist. If the process stops after catalog deletion but before metadata pruning, stale fingerprints remain harmless and a later run reconstructs the stream from SQLite to finish cleanup. If deletion fails partway, metadata is not pruned. Instruments without an available calendar policy are retained and reported rather than inferred from venue or symbol; rollover contracts should remain in configuration as disabled entries until their retained history expires.

Reason: Parquet and SQLite cannot share an atomic deletion transaction. Catalog-first ordering makes every interruption conservative: crashes may delay space recovery but cannot remove duplicate protection for retained market data. Whole-file eligibility avoids expensive and failure-prone Parquet rewrites, while completed-session cutoffs respect holidays, weekends, maintenance windows, and partial sessions. Explicit opt-in prevents a software upgrade from silently activating destructive maintenance.

Constraint: Native Nautilus trade and quote files do not contain Markeitech's provider source. Stage 3 treats the catalog as single-source IB storage. A second native tick provider requires source-partitioned catalog ownership or durable source metadata before it may share this retention mechanism.
