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

## Initial Runtime Topology

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
      +--> Redis hot coordination
      +--> Analytics + signals
                |
                +--> Discord webhook delivery
                +--> Future WebSocket gateway --> Frontend
```

## Instrument Runtime Model

Markeitech supports multiple configured instruments with one enabled active instrument at a time.

The active instrument receives live tick-by-tick data, real-time trade/quote classification, active bar construction, dashboard primary chart updates, and later strategy eligibility. Stage 2 starts with explicit-expiry NQ as the first active instrument.

At boot, every enabled instrument is warmed from historical bars, analyzed across configured timeframes, and annotated with market context such as support/resistance zones, EMAs, trend, VWAP, FVGs, session levels, and later additional structures.

Background instruments then track live 1-minute bars through Nautilus where supported. They can produce indicators, zones, trend state, context, and dashboard signals while another instrument remains active. Examples include ES, SPX, VIX, QQQ, SPY, MAG7 names, and later additional operator-selected instruments.

Switching the active instrument changes runtime stream ownership:

- the old active instrument can downgrade to background monitoring or be disabled by policy
- the new active instrument upgrades to live tick-by-tick ownership
- each instrument keeps separate readiness, gap state, checkpoints, bars, analytics, and signals
- dashboard primary views follow the active instrument
- signal views may include both active and background instruments

Runtime switching uses a make-before-break handover. The candidate must already be enabled and must have completed the boot warmup. The actor subscribes candidate trade and quote ticks, waits until both stream types have produced data, then changes the logical active instrument and removes the previous active tick streams. All 1-minute bar subscriptions remain unchanged.

Only one instrument is logically active during this process, although the candidate and current active instrument can briefly have overlapping tick subscriptions while readiness is established. A timeout or subscription failure removes the candidate streams and keeps the previous instrument active. The Stage 2 actor exposes the internal switch command; operator-facing command transport belongs to the later gateway stage.

## Live Data Ingestion

The market-data actor normalizes Nautilus `TradeTick`, `QuoteTick`, and external 1-minute `Bar` objects at the runtime boundary. Canonical events retain UTC datetimes, original nanosecond timestamps, decimal prices and quantities, source identity, and venue trade IDs where available. Data for unconfigured instruments is rejected.

Each configured instrument has an isolated runtime snapshot containing event counts and its latest trade, quote, classified trade, external bar, and active tick-built bar. Snapshot role follows the runtime switch coordinator rather than the boot registry, so active ownership changes without replacing instrument state.

Subscribed trades are classified against the latest valid same-instrument quote. The logical active instrument also builds a provisional 1-minute bar from classified ticks. That bar carries classified buy, sell, and unknown volume and becomes complete when the first trade in the next minute arrives. Nautilus/IB external bars are completed bars whose volume remains unknown-side unless a later reconciliation step can prove attribution.

Normalized events flow through an injectable sink. Stage 2 does not persist or broadcast them yet; persistence, analytics, notifications, and later WebSocket delivery consume this boundary in later stages.

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

One `NautilusParquetTimeSeriesStore` serializes catalog writes because `ParquetDataCatalog` is not thread-safe. It validates an entire bounded batch before writing, returns persistence identities only after the catalog call succeeds, and does not own checkpoints; Stage 3 metadata coordination will advance SQLite checkpoints only after successful catalog persistence.

The idempotent coordinator accepts one closed fixed `ts_init` bucket for one stream at a time. It sorts identities deterministically, creates a content-addressed batch manifest, records preparation, writes the exact catalog batch, records catalog success, then atomically commits the compact identity ledger and checkpoint. Exact retries and historical/live overlap are filtered through fixed-size dedupe and logical-identity fingerprints. Receipt-time metadata is excluded so retransmission remains stable, while a matching dedupe fingerprint with different logical metadata fails as corruption. Typed batch, stream, source, and event-time columns support inspection and conservative retention without duplicating full tick payloads in SQLite.

One bounded persistence writer owns all blocking catalog and metadata calls off the market-data callback thread. Submission is non-blocking and returns an explicit result for accepted, full, stopped, failed, unsupported, or provisional input. Its capacity covers every accepted but uncommitted event, including events already moved into open buckets. Native Nautilus trade and quote ticks and completed canonical one-minute bars are grouped by source, instrument, event kind, and fixed `ts_init` bucket; closed buckets are deterministically sorted and split into stable configured-size chunks before coordination. Storage failure fails the writer closed and retains pending work in memory for diagnosis, while graceful shutdown forces a bounded final flush.

Accepted ingress remains a non-durable queue state until the writer appends it to a checksummed, versioned bucket WAL. Native ticks use Nautilus message-pack serialization; canonical bars store only declared versioned fields and regenerate computed properties on recovery. The writer flushes and `fsync`s WAL data before buffering it for catalog persistence, replays all WAL buckets before accepting new live events after restart, and removes a WAL file only after every deterministic chunk commits. A torn final record is truncated to its last valid boundary; a complete checksum mismatch, unknown type, oversized record, or exhausted journal fails closed. File creation and removal also synchronize the journal directory.

Recovery planning uses a provider-neutral session calendar which supplies expected one-minute opens for an instrument and UTC range. Missing bars are calculated only from those expected opens, so weekends, holidays, and maintenance breaks are not gaps. An instrument missing calendar configuration fails planning rather than being mistaken for a closed session. Contiguous missing opens become bounded deterministic historical requests; out-of-lookback bars remain explicitly unavailable. Journaled ticks are exactly replayable. Unjournaled tick gaps are partial when a provider offers best-effort history and unavailable otherwise; neither outcome is represented as complete. Recovery lifecycle records may advance from pending through recovering to a terminal result, but terminal states cannot regress.

Production schedule generation uses a pinned `pandas-market-calendars` adapter behind that protocol. Every instrument contract declares its calendar identifier and whether recovery expects the full, regular, or continuous session. Exchange names and security types never select calendars implicitly: products on the same venue can have different hours, and related indices and futures do not necessarily share a session. Full equity schedules use published premarket and postmarket boundaries when available; regular schedules use market open and close. Published breaks and interruptions split windows before minute generation. Continuous instruments use a native UTC 24/7 implementation. Calendar queries and cached schedules are bounded, and unknown instruments or calendars fail closed. Package rules are local versioned code rather than a live schedule feed, so upgrades require the golden CME, NYSE, DST, holiday, and crypto tests plus later comparison against observed IB bars.

The optional LiveNode persistence runtime composes the catalog, SQLite metadata, idempotent coordinator, durable journal, bounded writer, and a narrow actor-facing ingress. It starts and completes journal replay before the LiveNode can start actors or subscriptions. Valid native Nautilus ticks flow directly to the writer; only completed canonical one-minute bars cross the canonical event sink. Callback submission never waits for storage. A rejected tick records known fidelity damage, while a rejected completed bar records an obligation for later historical repair. During shutdown, the LiveNode stops producing events before the writer forces its bounded flush and SQLite closes. Reported and tick-built bars use source-scoped dedupe keys so both observations may coexist for one instrument-minute.

Startup historical ownership remains with one actor-side coordinator. The ordinary multi-timeframe warmup is the first evidence wave for every enabled non-crypto instrument, and its one-minute bars enter the same durable writer as live bars. After all coarse requests complete, startup recovery forces a bounded flush and plans gaps from Parquet plus confirmed provider-empty evidence. Exact repair ranges are interleaved round-robin across instruments and issued sequentially. After responses, another bounded flush precedes durable re-verification and independent terminal recovery records. Degraded historical recovery remains visible but does not replace the minimum warmup and analysis gate. If IB repeatedly returns no bar for an expected minute, SQLite counts bounded attempts; only a configured confirmation threshold converts that minute into known provider-empty evidence, preventing endless requests without fabricating market data.

Explicit failure hooks prove every crash boundary. A prepared batch may have no catalog data or may represent the ambiguous window immediately after a physical write; replaying the exact deterministic batch is safe because Nautilus skips the same catalog file. A catalog-written batch can proceed directly to metadata commit. A committed batch is a no-op on retry. Delayed events with newer initialization time but older event time can still be recorded without moving the checkpoint backward.

SQLite stores transactional metadata such as checkpoints, readiness, gap state, recovery state, and later signal metadata.

SQLite does not govern or replace Parquet market data. Parquet answers which durable market events exist; SQLite answers which ranges have been verified and processed plus the current mutable operational state. Catalog writes must complete before checkpoints advance. A crash may leave a checkpoint behind already-written Parquet data, causing safe overlap on recovery, but a checkpoint must never lead durable catalog data.

The metadata store uses versioned migrations, WAL mode, full synchronous durability, configurable lock timeout, integer nanosecond timestamps, deterministic JSON, and monotonic upserts. Separate worker connections claim outbox work inside `BEGIN IMMEDIATE` transactions, and only the recorded lease owner may finalize a delivery attempt.

Opt-in retention runs at startup before the writer accepts new events. Product calendars resolve cutoffs from completed sessions, then maintenance reads Parquet `ts_event` statistics and deletes only wholly expired files. Mixed-age files pin the metadata cutoff to their oldest event. Each deletion is synchronized to its parent directory before one SQLite transaction removes older compact identities and committed manifests that no longer own identities. WAL presence or incomplete batches suppress the run so recovery always wins. Catalog and identity-ledger stream discovery are combined, allowing a later startup to complete metadata pruning when a crash occurred after deleting the last file. Unmanaged instruments remain untouched and visible in the maintenance report.

Native Nautilus trade and quote schemas do not encode Markeitech's provider source. The Stage 3 catalog is therefore a single-source IB catalog, and retention assigns native tick files to that same configured runtime source. Before a second native tick provider can share storage, catalog ownership must be partitioned by source or the source must become durable file metadata; changing the runtime source against an existing catalog is not supported.

Every enabled retention attempt is stored as an immutable SQLite audit record, including unsafe skips and failures. Physical SQLite compaction remains an offline operator action: a separate command requires explicit confirmation, rejects ingress WAL or incomplete batches, checkpoints SQLite, obtains exclusive maintenance access, and rewrites only when free pages exceed the configured threshold. Its before/after page evidence is also durable. The LiveNode never runs `VACUUM` automatically.

SQLite also stores a durable notification outbox. Delivery transports consume outbox records idempotently; a Discord outage must not lose signals or block ingestion.

Redis is only hot runtime coordination. Redis must never be the sole durable source.

### Notification Boundary

Signal and analytics code emit versioned domain events and never call Discord directly. Notification policy selects, batches, formats, and enqueues delivery records. A Discord incoming-webhook adapter performs one-way delivery with bounded retries, rate-limit handling, deduplication, and explicit sent or failed state.

Discord webhook URLs are secrets and must remain outside source control and durable message payloads. Discord is an initial operator surface, not a source of truth or execution authority. No Discord bot is planned.

### Analytics, ML, And Agent Boundary

Deterministic analytics and versioned feature snapshots are the baseline. Optional ML providers consume those snapshots and emit versioned inference events containing model version, feature schema, input lineage, output semantics, latency, and degraded-input state. Models must pass offline evaluation, replay, and shadow operation before influencing signal ranking or strategy behavior.

AI agents may explain persisted evidence, assist research, and compose operator reports. They do not calculate authoritative market state, invent missing evidence, connect directly to IB, mutate durable truth, or control execution. Generated narrative remains distinguishable from deterministic metrics and model inference.

The first named decision-support model is Direction-Location-Aggression: determine auction direction or market condition, identify and refine a relevant location, then observe aggression and follow-through. Direction and location should be deterministic where possible. Aggression starts as evidence-assisted interpretation because its fidelity depends on available IB trades and quotes; automation must be earned through captured data and replay validation.

### Gateway Boundary

The WebSocket gateway builds snapshots and streams incremental updates from versioned backend events. It must use bounded per-client queues and a policy for slow clients.

The dashboard never connects directly to IB, NautilusTrader internals, persistence, or strategies.

The gateway and dashboard are intentionally deferred until after persistence, analytics, signals, notification delivery, strategy runtime, and replay are established. Their versioned event boundary remains part of the architecture so Discord-specific formatting cannot leak into domain models.

### Strategy Boundary

Strategies eventually consume stable versioned domain interfaces and NautilusTrader strategy lifecycles where practical.

Strategy worker failure must not interrupt ingestion, persistence, notifications, or later presentation updates.

## Data-Only Default

Stage 0 configures data-only mode. Execution is off by default and remains out of scope until Stage 11.

IB Gateway should be read-only during data phases.

## Operational Invariants

- All timestamps are UTC at storage and event boundaries.
- Session definitions use IANA timezones, never fixed UTC offsets.
- Futures contracts are explicit-expiry contracts.
- Stage 2 starts with NQ as the first active instrument.
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
