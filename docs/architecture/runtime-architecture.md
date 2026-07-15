# Runtime Architecture

## System Boundary

NautilusTrader should be the primary system boundary for trading-domain runtime concerns:

- instruments
- market-data models
- events
- actors
- strategies
- indicators where practical
- message bus
- cache
- data engine
- execution engine
- portfolio and account models
- catalog and persistence facilities
- backtesting and replay
- clocks and lifecycle

Markeitech adds bounded services around NautilusTrader for product-specific contracts, storage metadata, analytics, signals, outbound notifications, later WebSocket presentation and dashboard state, strategy-worker isolation, and operator controls.

This boundary is capability-driven, not framework-driven. Prefer NautilusTrader when it avoids rebuilding mature trading infrastructure such as instrument models, provider connectivity, subscription lifecycle, clocks, replay, strategy lifecycle, execution, portfolio, and account handling. Markeitech retains ownership when behavior is product-specific or when adopting a Nautilus abstraction would weaken data fidelity, recovery guarantees, provider portability, or deterministic testing. New integrations should be judged against that rule rather than added merely for architectural consistency.

The market-data runtime is LiveNode-centered. Markeitech builds validated plans and configuration around NautilusTrader, then uses Nautilus `TradingNodeConfig` and the Interactive Brokers data client as the runtime container for live market data.

Before any live connection, Markeitech builds four deterministic layers:

- validated instrument registry and runtime config
- ownership plan for warmups and subscriptions
- Nautilus-oriented request intents for historical bars, trade ticks, quote ticks, and bars
- ordered LiveNode actions for warmups and live subscriptions

The Markeitech market-data actor translates those actions into Nautilus calls. Historical requests are asynchronous, so an explicit coordinator waits for every request callback, passes the collected bars through the warmup analysis boundary, and only then starts role-based live subscriptions. A warmup or analysis failure leaves the actor unsubscribed.

The prepared-node builder registers the Interactive Brokers data-client factory, attaches the market-data actor, and calls `TradingNode.build()` before the guarded start path can call `TradingNode.run()`.

The guarded bootstrap may construct a Nautilus `TradingNode` from validated config, but starting the node requires explicit manual opt-in and a confirmation token because it can connect to IB.

The manual smoke command is the first path allowed to call `TradingNode.run()`. It must print the validated plan and guard state before starting, and it remains outside automated tests.

Warmup lookbacks currently over-fetch calendar days to cover the configured minimum session count across weekends and common closures. Exact exchange-calendar session resolution remains a later refinement at the session/calendar boundary.

## Runtime Topology

```text
IB Gateway / TWS
      |
      v
NautilusTrader LiveNode + IB data client
      |
      v
Authoritative market-data runtime
      |
      +--> Parquet/catalog storage
      +--> SQLite metadata + durable notification outbox
      +--> Analytics + signals
                |
                +--> Discord webhook delivery
                +--> Future WebSocket gateway --> Frontend
```

Optional Redis coordination may be added beside these services only when a
demonstrated distributed-runtime need appears. It is not part of the current
runtime or a durability boundary.

## Instrument Runtime Model

Markeitech supports multiple configured instruments with one enabled active instrument at a time.

The active instrument receives live tick-by-tick data, real-time trade/quote classification, active bar construction, and operator-first context updates. Explicit-expiry NQ is the first active instrument.

At boot, every enabled instrument is warmed from historical bars, analyzed across configured timeframes, and annotated with market context such as support/resistance zones, EMAs, trend, VWAP, FVGs, session levels, and later additional structures.

Background instruments then track live 1-minute bars through Nautilus where supported. They produce indicators, zones, trend state, context, and signals while another instrument remains active. Examples include ES, SPX, VIX, QQQ, SPY, MAG7 names, and later additional operator-selected instruments.

Switching the active instrument changes runtime stream ownership:

- the old active instrument can downgrade to background monitoring or be disabled by policy
- the new active instrument upgrades to live tick-by-tick ownership
- each instrument keeps separate readiness, gap state, checkpoints, bars, analytics, and signals
- operator-primary projections follow the active instrument
- signal projections may include both active and background instruments

Runtime switching uses a make-before-break handover. The candidate must already be enabled and must have completed the boot warmup. The actor subscribes candidate trade and quote ticks, waits until both stream types have produced data, then changes the logical active instrument and removes the previous active tick streams. All 1-minute bar subscriptions remain unchanged.

Only one instrument is logically active during this process, although the candidate and current active instrument can briefly have overlapping tick subscriptions while readiness is established. A timeout or subscription failure removes the candidate streams and keeps the previous instrument active. The actor exposes the internal switch command; operator-facing command transport belongs to a later surface.

## Live Data Ingestion

The market-data actor normalizes Nautilus `TradeTick`, `QuoteTick`, and external 1-minute `Bar` objects at the runtime boundary. Canonical events retain UTC datetimes, original nanosecond timestamps, decimal prices and quantities, source identity, and venue trade IDs where available. Data for unconfigured instruments is rejected.

Each configured instrument has an isolated runtime snapshot containing event counts and its latest trade, quote, classified trade, external bar, and active tick-built bar. Snapshot role follows the runtime switch coordinator rather than the boot registry, so active ownership changes without replacing instrument state.

Subscribed trades are classified against the latest valid same-instrument quote. The logical active instrument also builds a provisional 1-minute bar from classified ticks. That bar carries classified buy, sell, and unknown volume and becomes complete when the first trade in the next minute arrives. Nautilus/IB external bars are completed bars whose volume remains unknown-side unless a later reconciliation step can prove attribution.

Normalized events flow through an injectable sink. The managed runtime routes supported completed events to bounded persistence and analytics boundaries. Notifications and later WebSocket delivery consume downstream domain projections rather than provider objects.

Interactive Brokers is the only implemented live provider initially. Canonical events remain provider-neutral and retain source identity, source-specific trade or sequence identifiers, original timestamps, and methodology metadata where values are derived. Future providers must enter through adapters at this canonical boundary rather than inherit IB-shaped contracts.

Analytics distinguish reported, inferred, partial, and unavailable evidence. IB top-of-book trades and quotes may support inferred aggressor side, price-level volume, and best-effort delta, but the system must not describe inferred values as authoritative exchange aggressor data or fabricate depth, footprint, or order-flow evidence from bars.

## Live Health And Gaps

Live health requirements follow current runtime ownership. The active instrument requires fresh trade ticks, quote ticks, and completed external 1-minute bars. Background instruments require fresh completed external 1-minute bars. Provisional and completed tick-built bars do not satisfy the external-bar health requirement.

Each required stream is waiting, healthy, stale, or session-paused. Stale thresholds are configurable, and session-open policy is injected so an exchange calendar can suspend expectations outside trading hours. The actor evaluates health once per second and emits a health snapshot only when semantic state changes.

External bar continuity is tracked by interval. Missing 1-minute opens create warning, degraded, or critical gap state based on count. A gap remains open across newer bars and closes only when late data fills every missing interval.

NautilusTrader owns the physical Interactive Brokers connection lifecycle and reconnect behavior. Markeitech does not create a competing reconnect loop; it observes canonical data, reports degradation, and records recovery transitions for later persistence and operator presentation.

## Ownership Boundaries

### Interactive Brokers Boundary

Interactive Brokers connectivity is coordinated through two paths:

- NautilusTrader IB data client inside a LiveNode for supported functionality.
- A narrow native IB API adapter only for capabilities NautilusTrader does not expose.

Both paths must share contract identity, timestamps, sessions, normalization, health, reconnection, persistence, and deduplication rules.

Only one component may own a market-data stream for a contract and data type at a time.

### Backend Domain Boundary

The backend owns versioned domain events that are stable for the dashboard and later strategy workers.

The backend must not duplicate NautilusTrader functionality unless a decision record documents why.

### Persistence Boundary

Parquet/catalog storage is the durable time-series store for raw ticks and bars.

Raw valid trade and quote ticks retain Nautilus native catalog schemas. Completed canonical one-minute bars use a registered custom Arrow record because the canonical contract includes classified volume, source, revision, completion, schema, and dedupe fields that a native OHLCV bar cannot preserve. Decimal fields are encoded as strings and reconstructed as immutable domain values to avoid floating-point precision loss.

One `NautilusParquetTimeSeriesStore` serializes catalog writes because `ParquetDataCatalog` is not thread-safe. It validates an entire bounded batch before writing, returns persistence identities only after the catalog call succeeds, and does not own checkpoints; metadata coordination advances SQLite checkpoints only after successful catalog persistence.

The idempotent coordinator accepts one closed fixed `ts_init` bucket for one stream at a time. It sorts identities deterministically, creates a content-addressed batch manifest, records preparation, writes the exact catalog batch, records catalog success, then atomically commits the compact identity ledger and checkpoint. Exact retries and historical/live overlap are filtered through fixed-size dedupe and logical-identity fingerprints. Receipt-time metadata is excluded so retransmission remains stable, while a matching dedupe fingerprint with different logical metadata fails as corruption. Typed batch, stream, source, and event-time columns support inspection and conservative retention without duplicating full tick payloads in SQLite.

One bounded persistence writer owns all blocking catalog and metadata calls off the market-data callback thread. Submission is non-blocking and returns an explicit result for accepted, full, stopped, failed, unsupported, or provisional input. Its capacity covers every accepted but uncommitted event, including events already moved into open buckets. Native Nautilus trade and quote ticks and completed canonical one-minute bars are grouped by source, instrument, event kind, and fixed `ts_init` bucket; closed buckets are deterministically sorted and split into stable configured-size chunks before coordination. Storage failure fails the writer closed and retains pending work in memory for diagnosis, while graceful shutdown forces a bounded final flush.

Accepted ingress remains a non-durable queue state until the writer appends it to a checksummed, versioned bucket WAL. Native ticks use Nautilus message-pack serialization; canonical bars store only declared versioned fields and regenerate computed properties on recovery. The writer flushes and `fsync`s WAL data before buffering it for catalog persistence, replays all WAL buckets before accepting new live events after restart, and removes a WAL file only after every deterministic chunk commits. A torn final record is truncated to its last valid boundary; a complete checksum mismatch, unknown type, oversized record, or exhausted journal fails closed. File creation and removal also synchronize the journal directory.

Recovery planning uses a provider-neutral session calendar which supplies expected one-minute opens for an instrument and UTC range. Missing bars are calculated only from those expected opens, so weekends, holidays, and maintenance breaks are not gaps. An instrument missing calendar configuration fails planning rather than being mistaken for a closed session. Contiguous missing opens become bounded deterministic historical requests; out-of-lookback bars remain explicitly unavailable. Journaled ticks are exactly replayable. Unjournaled tick gaps are partial when a provider offers best-effort history and unavailable otherwise; neither outcome is represented as complete. Recovery lifecycle records may advance from pending through recovering to a terminal result, but terminal states cannot regress.

Production schedule generation uses a pinned `pandas-market-calendars` adapter behind that protocol. Every instrument contract declares its calendar identifier and whether recovery expects the full, regular, or continuous session. Exchange names and security types never select calendars implicitly: products on the same venue can have different hours, and related indices and futures do not necessarily share a session. Full equity schedules use published premarket and postmarket boundaries when available; regular schedules use market open and close. Published breaks and interruptions split windows before minute generation. A provider-neutral UTC 24/7 implementation remains available for continuous-session contracts, although crypto is not an active product scope. Calendar queries and cached schedules are bounded, and unknown instruments or calendars fail closed. Package rules are local versioned code rather than a live schedule feed, so upgrades require the golden CME, NYSE, DST, holiday, and continuous-session tests plus later comparison against observed IB bars.

The optional LiveNode persistence runtime composes the catalog, SQLite metadata, idempotent coordinator, durable journal, bounded writer, and a narrow actor-facing ingress. It starts and completes journal replay before the LiveNode can start actors or subscriptions. Valid native Nautilus ticks flow directly to the writer; only completed canonical one-minute bars cross the canonical event sink. Callback submission never waits for storage. A rejected tick records known fidelity damage, while a rejected completed bar records an obligation for later historical repair. During shutdown, the LiveNode stops producing events before the writer forces its bounded flush and SQLite closes. Reported and tick-built bars use source-scoped dedupe keys so both observations may coexist for one instrument-minute.

Startup historical ownership remains with one actor-side coordinator. The ordinary multi-timeframe warmup is the first evidence wave for every enabled product instrument, and its one-minute bars enter the same durable writer as live bars. After all coarse requests complete, startup recovery forces a bounded flush and plans gaps from Parquet plus confirmed provider-empty evidence. Exact repair ranges are interleaved round-robin across instruments and issued sequentially. After responses, another bounded flush precedes durable re-verification and independent terminal recovery records. Degraded historical recovery remains visible but does not replace the minimum warmup and analysis gate. If IB repeatedly returns no bar for an expected minute, SQLite counts bounded attempts; only a configured confirmation threshold converts that minute into known provider-empty evidence, preventing endless requests without fabricating market data.

Explicit failure hooks prove every crash boundary. A prepared batch may have no catalog data or may represent the ambiguous window immediately after a physical write; replaying the exact deterministic batch is safe because Nautilus skips the same catalog file. A catalog-written batch can proceed directly to metadata commit. A committed batch is a no-op on retry. Delayed events with newer initialization time but older event time can still be recorded without moving the checkpoint backward.

SQLite stores transactional metadata such as checkpoints, readiness, gap state, recovery state, and durable signal lifecycle state.

SQLite does not govern or replace Parquet market data. Parquet answers which durable market events exist; SQLite answers which ranges have been verified and processed plus the current mutable operational state. Catalog writes must complete before checkpoints advance. A crash may leave a checkpoint behind already-written Parquet data, causing safe overlap on recovery, but a checkpoint must never lead durable catalog data.

The metadata store uses versioned migrations, WAL mode, full synchronous durability, configurable lock timeout, integer nanosecond timestamps, deterministic JSON, and monotonic upserts. Separate worker connections claim outbox work inside `BEGIN IMMEDIATE` transactions, and only the recorded lease owner may finalize a delivery attempt.

Opt-in retention runs at startup before the writer accepts new events. Product calendars resolve cutoffs from completed sessions, then maintenance reads Parquet `ts_event` statistics and deletes only wholly expired files. Mixed-age files pin the metadata cutoff to their oldest event. Each deletion is synchronized to its parent directory before one SQLite transaction removes older compact identities and committed manifests that no longer own identities. WAL presence or incomplete batches suppress the run so recovery always wins. Catalog and identity-ledger stream discovery are combined, allowing a later startup to complete metadata pruning when a crash occurred after deleting the last file. Unmanaged instruments remain untouched and visible in the maintenance report.

Native Nautilus trade and quote schemas do not encode Markeitech's provider source. The current catalog is therefore a single-source IB catalog, and retention assigns native tick files to that same configured runtime source. Before a second native tick provider can share storage, catalog ownership must be partitioned by source or the source must become durable file metadata; changing the runtime source against an existing catalog is not supported.

Every enabled retention attempt is stored as an immutable SQLite audit record, including unsafe skips and failures. Physical SQLite compaction remains an offline operator action: a separate command requires explicit confirmation, rejects ingress WAL or incomplete batches, checkpoints SQLite, obtains exclusive maintenance access, and rewrites only when free pages exceed the configured threshold. Its before/after page evidence is also durable. The LiveNode never runs `VACUUM` automatically.

SQLite also stores a durable notification outbox. Delivery transports consume outbox records idempotently; a Discord outage must not lose signals or block ingestion.

Redis is reserved for optional future hot coordination. It is not used by the current runtime and must never become the sole durable source.

### Notification Boundary

Signal and analytics code emit versioned domain events and never call Discord directly. Notification policy selects, batches, formats, and enqueues delivery records. A Discord incoming-webhook adapter performs one-way delivery with bounded retries, rate-limit handling, deduplication, and explicit sent or failed state.

Discord webhook URLs are secrets and must remain outside source control and durable message payloads. Discord is an initial operator surface, not a source of truth or execution authority. No Discord bot is planned.

### Analytics, ML, And Agent Boundary

Deterministic analytics and versioned feature snapshots are the baseline. Optional ML providers consume those snapshots and emit versioned inference events containing model version, feature schema, input lineage, output semantics, latency, and degraded-input state. Models must pass offline evaluation, replay, and shadow operation before influencing signal ranking or strategy behavior.

The first live baseline is owned by one in-process market-context engine attached to the market-data actor. Warmup coverage and analysis must both succeed before live subscriptions begin. Every enabled instrument receives the same per-timeframe calculations; active status changes data acquisition fidelity, not analytical importance.

Warmup logs are bracketed and phase-labeled so the operator receives one latest context snapshot for every requested instrument/timeframe before subscriptions. The default NQ and ES operational configuration includes 1h warmup; it does not wait for live hourly construction before exposing hourly levels.

The LiveNode separates analytics publication from operator presentation. Every calculated context remains a versioned snapshot and reaches the configured snapshot sink. With DEBUG file logging enabled, each calculation is also retained as a `MARKET_CONTEXT_EVENT` JSONL record. INFO console output is a bounded view: one active-first warmup briefing, then a configurable periodic report only for instruments whose context or active/background role changed. Each reported instrument receives exactly three lines covering top-down direction, levels/session position, and auction context. This reporting layer performs no market calculations.

Durable analytics use a separate Markeitech-owned feature catalog rather than the Nautilus raw-market custom-data path. A feature envelope binds each context payload to an explicit calculation version, configuration fingerprint, and exact input-lineage fingerprints. Feature identity and payload content are hashed separately: revised inputs may coexist at the same `as_of`, while different output from the same deterministic identity is rejected. PyArrow writes immutable, UTC-date-partitioned Parquet batches through file and directory synchronization plus atomic creation. Exact retries are idempotent, and reads validate redundant typed metadata against the stored envelope before returning it.

This separation preserves ownership and revision semantics. Nautilus continues to own runtime connectivity and its native tick/bar catalog behavior; Markeitech owns feature identity and storage. Parquet is durable feature payload truth. SQLite records a feature commit manifest only after the corresponding Parquet payload is durable. If the process stops between those operations, restart finds the existing payload, verifies it, and completes the missing manifest without creating a second feature. A bounded asynchronous writer keeps feature I/O off the actor callback thread, reports accepted, pending, committed, duplicate, rejected, and failed counts, fails closed on storage errors, and receives a bounded shutdown flush. Each manifest also receives a monotonic commit sequence, making same-`as_of` corrections deterministic across process restart. JSONL logs do not substitute for either layer.

The signal-side boundary begins only after the coordinator re-reads and verifies the complete committed batch. Exact committed revisions enter an all-or-nothing bounded handoff; saturation fails the feature writer closed while preserving both the original input batch and truthful durable-commit counters. A point-in-time state index advances independently per instrument/timeframe by `(as_of, commit_sequence)`, ignores stale delivery, and emits bundles only for accepted evaluation-timeframe revisions. The handoff is constructed only when signal definitions are enabled, so persistence-only runs retain their existing path.

The Stage 5C.3b consumer is a dedicated bounded thread owned by the managed LiveNode. Startup order is persistence, verified signal restoration, then Nautilus execution. Shutdown stops and flushes the feature writer, drains and stops signal evaluation while SQLite remains open, then closes the remaining persistence runtime. Warmup commits rebuild feature state behind a startup watermark; only a newer completed evaluation bar may change signal lifecycle. Active and background instruments use the same definition/evaluator/store path.

For each live evaluation, the runtime qualifies Direction, resolves the explicit product-session start from the configured calendar, qualifies Location, advances the repeatable episode tracker, and persists only lifecycle changes. Open state is restored from hash-chain-verified SQLite aggregates matching current definition identity. Calendar, evaluator, callback, or persistence failure marks the runtime failed and returns the unprocessed committed revisions to the handoff. Console projection is intentionally deferred to 5C.3c and is never restart truth.

The live actor publishes each warmup and completed-live context through the same feature sink for active and background instruments. The engine creates the envelope from the exact retained bars at or before that snapshot's `as_of`; higher-timeframe features may include supporting 1m structure lineage but never newer structure evidence. The configuration fingerprint includes history limits, profile bins, composite periods, and per-instrument calendar/session policy. Only a successfully accepted feature envelope may later become signal evidence.

Dashboard recency and analytical history are separate policies. NQ and ES initially request 260 sessions of daily history, 60 of 1h, 20 of 15m, 10 of 5m, and five of 30m/1m history. Warmup context is emitted daily-first. The readiness gate compares observed history with the latest fully closed, session-aware interval and reports freshness independently from EMA history depth.

Completed canonical 1m bars are the only live analytics clock. The active instrument advances from its tick-built bars while background instruments advance from provider bars; the active instrument's parallel provider-bar stream remains available for persistence and recovery without producing a competing context snapshot. Configured higher timeframes align to the product session open, aggregate exact consecutive minute buckets, and are withheld when a minute is missing. At boot, warmup 1m bars seed only each currently forming aggregate bucket; completed buckets remain owned by historical higher-timeframe evidence. This lets the first post-restart boundary complete on schedule without restoring opaque indicator internals or duplicating a closed bar. Context snapshots identify their source and whether the input was provider-reported, tick-inferred, or mixed. Persistence receives each completed canonical bar before analytics runs, so an analytics failure cannot hide an accepted bar from durable recovery.

AI agents may explain persisted evidence, assist research, and compose operator reports. They do not calculate authoritative market state, invent missing evidence, connect directly to IB, mutate durable truth, or control execution. Generated narrative remains distinguishable from deterministic metrics and model inference.

The first named decision-support model is Direction-Location-Aggression: determine auction direction or market condition, identify and refine a relevant location, then observe aggression and follow-through. Direction and location should be deterministic where possible. Aggression starts as evidence-assisted interpretation because its fidelity depends on available IB trades and quotes; automation must be earned through captured data and replay validation.

Its signal lifecycle advances from Candidate with Direction evidence, to Armed with added Location evidence, to Triggered with added Aggression evidence; Invalidated and Expired are terminal exits. Stable signal identity is separate from mutable lifecycle content and notification policy. Every state retains typed evidence ids and fidelity, and every transition carries the previous content hash plus the complete next snapshot so SQLite can later enforce optimistic, restart-safe progression.

SQLite retains the initial candidate hash separately from mutable current content and appends every transition under a contiguous per-signal sequence. Restart reads verify that chain end to end. Applying a transition uses an optimistic previous-content check and may atomically insert a pending notification-outbox record; any state, history, or outbox conflict rolls the complete transaction back. The managed LiveNode signal runtime uses this persistence boundary before any lifecycle change becomes an operator projection.

Direction evaluation is definition-driven rather than tied to the active instrument or one fixed timeframe recipe. The initial `intraday_context` definition uses agreeing 1h and 15m Direction, 5m confirmation, and daily context that can degrade confidence. Definitions are enabled per instrument, so active NQ and background ES can produce independent signals from the same rules while a future `scalp` definition can coexist with different timeframe roles. Cross-instrument confluence remains a later explicit relationship feature; one instrument's evidence is never silently embedded in another instrument's setup identity.

The evaluator consumes a point-in-time bundle of committed feature envelopes and retains every considered feature id as evidence. It creates one candidate per continuous qualified direction regime, preserves that regime across missing or softly degraded entry evidence, and replaces it only when the complete definition qualifies in the opposite direction. Soft degradation preserves the open episode but blocks Trigger progression until Direction requalifies. Restart seeds the regime from verified open signals. The live composition layer remains separate: it observes feature-writer commit completion, selects only evidence available at the evaluation timestamp, persists decisions, and applies identical behavior to active and background instruments.

Location is modeled as an edge-triggered episode inside that Direction context, not as a one-time property of the whole regime. Named definitions configure structural-level, FVG, value-area-edge, and session-VWAP sources independently by timeframe and ATR-relative tolerance. Semantic zone identity is anchored to the originating swing, gap, or product session and remains stable as developing bounds or feature revisions change. Live composition suppresses repeated setup creation while price remains inside the same zone, then permits a fresh DLA setup only after a confirmed exit and re-entry.

The pure location evaluator derives zones only from the configured feature timeframes in one committed point-in-time bundle. Session-scoped sources require the calendar resolver's explicit UTC product-session start; UTC dates are never treated as trading sessions. The evaluation-timeframe close is matched with source-timeframe ATR tolerance, distinct source-kind confluence is enforced, and missing ATR or payloads remain visible as degraded evidence. The evaluator itself has no persistence side effects.

The location episode tracker turns repeated per-bar qualification into edge-triggered state. Entry is immediate. Continued overlap with any entry zone remains one episode; a wholly disjoint qualified zone set replaces it. Once price leaves, the persisted entry zones and their original tolerances classify the move as favorable departure, adverse breach, or unresolved displacement. Favorable and unresolved moves preserve the setup; only configured consecutive adverse-breach observations exit it. Missing evidence resets breach confirmation without claiming an exit. Exact latest-observation retries are idempotent, conflicting same-time observations and backward time fail closed, and a fully qualified opposite Direction regime terminates the old episode immediately. Transient counters remain in memory; the active episode reconstructs from verified durable signal state after restart.

The arming boundary converts an entered episode into an episode-anchored Candidate and immediate Armed transition with complete structured evidence. SQLite commits initial Candidate plus Armed state atomically. Replacing a disjoint episode atomically invalidates the old signal and creates plus arms the new signal, preventing restart from observing two open setups or neither. Verified open snapshots seed Direction and Location trackers before new evaluations. The Stage 5C.3 post-commit feature composer invokes this boundary for every enabled definition and instrument.

The fast-track Direction/Location view combines deterministic trend, VWAP relation, session quartile, profile location, nearby levels, and active FVG location. Current, prior, London, and New York candle-derived profiles use configured price bins and are explicitly inferred. Configured rolling 2-session and 5-session composites add broader auction context only when the exact number of calendar-resolved product sessions is represented; they include explicit observed windows and complete/developing state. The current-session profile remains authoritative for the existing profile-location calculation. Exact tick-price profiles require a separate tick-at-price accumulator and are not claimed by this implementation.

### Gateway Boundary

The WebSocket gateway builds snapshots and streams incremental updates from versioned backend events. It must use bounded per-client queues and a policy for slow clients.

The dashboard never connects directly to IB, NautilusTrader internals, persistence, or strategies.

The gateway and dashboard are intentionally deferred until after persistence, analytics, signals, notification delivery, strategy runtime, and replay are established. Their versioned event boundary remains part of the architecture so Discord-specific formatting cannot leak into domain models.

### Strategy Boundary

Strategies eventually consume stable versioned domain interfaces and NautilusTrader strategy lifecycles where practical.

Strategy worker failure must not interrupt ingestion, persistence, notifications, or later presentation updates.

## Data-Only Default

The runtime operates in data-only mode. Execution is off by default and remains out of scope until a separately approved execution and risk stage.

IB Gateway should be read-only during data phases.

## Operational Invariants

- All timestamps are UTC at storage and event boundaries.
- Session definitions use IANA timezones, never fixed UTC offsets.
- Futures contracts are explicit-expiry contracts.
- NQ is the first active instrument.
- Exactly one enabled instrument is active at a time.
- Every enabled instrument warms up from historical bars before live tracking.
- Background instruments track live 1-minute bars after warmup.
- No silent rollover.
- No duplicate canonical events.
- No duplicated subscriptions.
- No unbounded queues in live data paths.
- No frontend-owned market calculations.
- No signal or analytics code coupled directly to Discord.
- No Discord webhook secret in source control or persisted notification payloads.
- No provider-specific payload leaking beyond the canonical adapter boundary.
- No inferred order-flow metric represented as authoritative source data.
- No ML model or AI agent with direct IB or execution access.
