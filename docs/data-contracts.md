# Data Contracts

Stage 1 implements domain contracts under `backend/src/markeitech/domain`.

These contracts are intentionally pure backend schemas and deterministic helpers. They do not connect to Interactive Brokers, NautilusTrader live nodes, persistence, WebSockets, frontend code, or strategy workers.

## Versioning

Every externally visible backend event includes or derives:

- schema version
- event type
- instrument identity
- UTC event timestamp
- UTC ingestion or initialization timestamp where relevant

Current schema version: `1.0`.

## Contract Identity

Initial active instrument support is explicit-expiry NQ futures. The contract layer supports multiple configured instruments so the runtime can keep one active tick-by-tick instrument while monitoring many background instruments.

Required fields:

- root symbol
- exchange
- expiry for futures
- NautilusTrader instrument id
- IB contract identity fields needed for unambiguous resolution

Continuous futures and silent rollover are prohibited for canonical storage and backend events.

Implemented models:

- `InstrumentContractConfig`
- `FuturesContractConfig`
- `EquityLikeContractConfig`
- `InstrumentRuntimeConfig`
- `InstrumentRegistryConfig`
- `NQContractConfig`

Rejected identity examples:

- `NQ.CME`
- `NQ.XCME`
- `ES.CME`
- IB `CONTFUT`

## Active And Background Instruments

The runtime model separates configured instruments from active instruments.

Roles:

- `active`: exactly one enabled instrument. It receives live tick-by-tick data, real-time classification, real-time active bar construction, primary chart updates, and later strategy eligibility.
- `background`: many enabled instruments. They warm up from historical bars, are annotated across configured timeframes, and then track live 1m bars for indicators, zones, trends, context, and signal dashboard events.

An active-instrument switch request identifies an enabled target, request ID, UTC request timestamp, and reason. Runtime switch state exposes the current active instrument, optional candidate, candidate trade/quote readiness, deadline, and last failure. A successful promotion emits `ActiveInstrumentChangedEvent`; failed attempts do not change logical active ownership.

Canonical instrument events may include `event_ts_ns` and `ts_init_ns` alongside UTC datetimes. The integer nanosecond fields preserve source identity; when present, they must match their datetime fields at Python's microsecond precision. Canonical trades also retain the venue/source trade ID.

One-minute bars identify their source and completion state. IB external bars are completed and initially assign all volume to unknown-side volume. Active tick-built bars are provisional until minute rollover and carry buy, sell, and unknown volume derived only from the configured trade-classification rules.

Market-data stream health identifies trade-tick, quote-tick, or external 1-minute-bar streams and reports `waiting`, `healthy`, `stale`, or `paused`. Instrument health combines the streams required by its current runtime role with external-bar gap state. Source health aggregates instrument degradation without taking ownership of the underlying Nautilus reconnect lifecycle.
- `disabled`: configured but not monitored.

Data modes:

- `tick_by_tick`: required for the active instrument.
- `live_1m_bars`: required for background instruments after historical warmup.
- `historical_warmup_only`: reserved for configured instruments that should be analyzed from history without live tracking.
- `disabled`: required for disabled instruments.

Warmup:

- Every enabled instrument requires warmup configuration.
- Warmup defines lookback sessions and derived analysis timeframes.
- Initial annotations include support/resistance, EMAs, trend, VWAP, and FVGs.

Switching the active instrument changes runtime ownership. It must not mutate instrument identity or silently roll any futures contract.

## Timestamp Rules

- Store timestamps in UTC.
- Normalize IB/TWS/Gateway timestamps to UTC.
- Use IANA timezones for session calculations.
- Do not use fixed UTC offsets for London or New York sessions.

Domain models reject naive timestamps and non-UTC aware timestamps at construction time.

## Stage 1 Contract Families

Stage 1 defines:

- explicit instrument and futures contract configuration
- one-active-many-background registry configuration
- canonical trade ticks
- canonical bid/ask quote ticks
- classified trades
- one-minute bars
- readiness state
- gap state
- source health
- gateway events
- strategy state events
- extension points for levels, zones, and signals

The event catalog includes `active.instrument.changed` for future runtime switches.

Current modules:

- `markeitech.domain.instruments`
- `markeitech.domain.market_data`
- `markeitech.domain.classification`
- `markeitech.domain.state`
- `markeitech.domain.events`

## Delta Classification Contract

Trade classification rules:

1. Match trade to the most recent valid quote at or before the trade timestamp.
2. At or above ask means buy.
3. At or below bid means sell.
4. Inside spread uses tick-rule fallback.
5. Otherwise classification is unknown.

Exposed outputs:

- buy volume
- sell volume
- unknown volume
- delta
- classified-volume ratio

Implemented helper:

- `classify_trade(trade, quote, previous_trade=None, max_quote_age=...)`

The default quote freshness window is two seconds. Stage 2 may tune this by configuration when real IB data characteristics are observed.

## Persistence Expectations

Raw trade ticks, raw bid/ask quote ticks, and canonical one-minute bars should be persisted to Nautilus-compatible Parquet/catalog storage where practical.

SQLite metadata should carry recovery and checkpoint state.

Committed event idempotency is represented in SQLite by raw SHA-256 fingerprints of the dedupe key and logical persistence identity, plus typed batch, instrument, event-kind, source, event-time, and commit-time columns. Local receipt timestamps are excluded from the logical fingerprint so a provider retransmission remains the same event. A matching dedupe fingerprint with different logical metadata is corruption and must fail closed. Full market payloads remain in Parquet rather than being duplicated into the metadata store.

Retention is defined in completed product sessions. A Parquet file is eligible only when its maximum typed `ts_event` is older than the stream cutoff. A retained mixed-age file protects all of its rows by lowering the metadata prune boundary to its minimum `ts_event`. Catalog deletion must be durable before compact identities and empty committed batch manifests may be pruned; WAL or incomplete batch state prohibits pruning.

Retention and SQLite compaction reports are immutable operational evidence. They carry a unique run identity, UTC maintenance timestamp, terminal status, bounded reason or error data, and exact file, byte, identity, batch, or page counters appropriate to the operation.

Writes must be idempotent and restart-safe.

Stage 3 persistence contracts live under `markeitech.persistence`. They add source-scoped event identities, stream checkpoints, recovery lifecycle records, durable notification outbox records, bounded persistence configuration, and storage protocols without coupling the Stage 1 domain models to a specific database.

Persistence fidelity is explicit:

- `reported`: received from the provider without a derived methodology
- `inferred`: calculated from provider data and accompanied by a derivation method
- `partial`: calculated from incomplete inputs and accompanied by a derivation method
- `unavailable`: the required evidence cannot be represented from current inputs

Outbox records contain a non-secret destination key. Webhook URLs, tokens, and secrets are prohibited from payloads, including nested payload fields.

## Baseline Analytics Contracts

Stage 4 analytics contracts live under `markeitech.analytics`. `AnalysisBar` normalizes native warmup bars and completed canonical 1m bars with an explicit timeframe, source, and input fidelity. `MarketContextSnapshot` is a versioned, provider-neutral point-in-time view containing indicator values, session location, trend state with reason codes, and nearest confirmed support and resistance.

Analytics input fidelity is explicit:

- `reported`: the context's latest bar was reported by the provider
- `inferred`: the context's latest bar was constructed from classified live ticks
- `mixed`: a derived bar combines inputs with different fidelity

An absent indicator remains `null`; insufficient history is represented as `insufficient_data` with reason codes. A missing minute prevents publication of the affected higher-timeframe bar. These contracts do not contain Discord formatting, model inference, or UI state.

Usable-context extensions remain part of the same versioned snapshot:

- prior product-session high and low
- DST-aware London and New York ranges and 15m/30m opening ranges
- confirmed active three-bar fair value gaps with timeframe and bounds
- current, prior, London, and New York volume-profile snapshots
- rolling multi-session composite profiles with requested session count, observed UTC window, and complete/developing state
- profile location plus deterministic Direction/Location score and reason codes

`volume_profile_bin_size` is configured per instrument. Candle-based profiles distribute each completed 1m bar's volume uniformly across every configured price bin intersecting its high-low range, conserve the bar's total volume exactly, and use a contiguous 70% expansion around POC. They are always marked `inferred` with methodology `bar_range_uniform_volume`. They are not exchange aggressor data, market depth, footprints, or exact historical trade-at-price distributions.

`volume_profile_composite_sessions` declares rolling product-session counts per instrument. A composite is emitted only when that many distinct calendar-resolved sessions are represented. Its window includes the current session and is therefore marked developing until that session closes. The current-session profile remains the sole profile used by `profile_location` and the deterministic Direction/Location score; composites are additional evidence and do not silently change existing signal semantics.

### Analytics Readiness

Warmup history requirements are configured per timeframe. The legacy instrument-level `lookback_sessions` remains a compatibility fallback only; `lookback_sessions_by_timeframe` owns explicit analytical depth.

`AnalyticsReadinessSnapshot` contains one `TimeframeAnalyticsReadiness` result for every required instrument/timeframe. Each result records the request lookback, expected and observed latest completed bar, lag intervals, bar count, freshness, indicator depth, and reason codes.

- Freshness: `current`, `stale`, or `unavailable`
- Depth: `full` at 200+ bars, `partial` at 50-199 bars, or `insufficient` below 50 bars
- Instrument/runtime status: `ready`, `degraded`, or `blocked`

The currently forming interval is never required. Unavailable required history or 1m evidence stale by more than one completed interval blocks subscriptions. Exactly one stale 1m interval is retained as explicit degraded startup evidence to tolerate a sequential warmup crossing a minute boundary. Stale higher timeframes and incomplete indicator depth are also degraded evidence and do not prevent live operation.

On restart, completed canonical 1m warmup bars seed only the currently forming session-aligned 5m, 15m, 30m, and 1h buckets. A seeded bucket must still contain every exact minute before it can emit. A bucket complete at the warmup cutoff is not seeded because historical higher-timeframe evidence already owns it. Aggregates spanning provider warmup and tick-built live inputs carry source `mixed` and fidelity `mixed`.

### Durable Feature Contracts

`FeatureInputLineage` identifies each exact input stream used by a feature calculation with instrument, timeframe, source, fidelity, observed UTC window, event count, and a SHA-256 identity fingerprint. A lineage window cannot extend beyond the resulting snapshot, must include the snapshot's own timeframe, and cannot cross instruments.

`MarketContextFeatureSnapshot` wraps one complete `MarketContextSnapshot` with a feature-set name, calculation version, SHA-256 configuration fingerprint, and one or more input-lineage entries. Its deterministic `feature_id` includes the envelope schema, algorithm/configuration identity, instrument, timeframe, `as_of`, output source/fidelity, and canonically sorted input lineage. Its independent `content_hash` covers the complete context payload.

The separation is intentional:

- A retry from the same inputs, calculation, and configuration has the same feature id and content hash and is a duplicate.
- A corrected input fingerprint produces a new feature id even at the same instrument/timeframe/`as_of`; both variants remain auditable.
- The same feature id with a different content hash indicates nondeterministic calculation or corruption and fails closed.
- Lineage order does not change identity.

Feature payloads are immutable Parquet records partitioned by feature set, instrument, timeframe, and UTC date. Query APIs return all latest-as-of variants instead of choosing an arbitrary revision. Human-readable operator logs are projections of context and are never feature persistence.
