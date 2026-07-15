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

SQLite stores only the durable commit manifest for each `feature_id`: content hash, instrument, timeframe, `as_of`, feature set, calculation version, configuration hash, commit time, and a monotonic commit sequence. Payload and manifest follow catalog-first ordering. The sequence makes same-timestamp corrected variants deterministic across live operation and restart without selecting one by feature hash. An existing manifest with a different content hash is a hard conflict; a payload that exists without its manifest is a recoverable interrupted commit.

Live feature submission is bounded and asynchronous. Submission returns accepted, queue-full, not-running, or writer-failed status. Writer health exposes pending, accepted, committed, duplicate, rejected, and last-error evidence. A failed batch remains retained in memory and the writer rejects new work; it does not silently skip the damaged feature stream.

The post-commit handoff carries the exact feature payload together with its authoritative SQLite commit time and sequence. Publication is bounded and admits a writer batch atomically: saturation cannot expose only part of a committed multi-instrument batch. Handoff failure leaves the writer failed with its input batch retained, while persistence counters still report any payloads already made durable. Retrying re-verifies those manifests and republishes the same revisions idempotently.

Live composition keeps the newest committed revision per instrument and timeframe ordered by market `as_of` and then durable commit sequence. A corrected variant at the same market timestamp supersedes the earlier revision; an older delayed revision cannot regress state. Only a newly accepted evaluation-timeframe revision creates a point-in-time bundle, and evidence newer than that evaluation timestamp is excluded. Active and background instruments use independent keys and identical rules.

The live signal runtime starts with a UTC watermark and restores only verified open Armed or Triggered signals matching an enabled definition's current algorithm and configuration identity. Committed warmup revisions at or before that watermark rebuild multi-timeframe state but cannot create, replace, or invalidate a signal. Each later evaluation-timeframe revision is applied once and may be composed independently for every enabled definition.

Location episode entry persists Candidate plus Armed transition atomically. A disjoint replacement atomically invalidates the old signal and creates plus arms the new one; confirmed exit applies one terminal transition. Missing, neutral, conflicted, or entry-vetoed Direction preserves an open episode as degraded evidence; only a newly qualified opposite Direction changes the regime. A processing failure retains the unprocessed tail of the drained committed-feature batch and marks the runtime failed instead of silently advancing.

### Signal Contracts

`SignalSnapshot` is the immutable current state of one deterministic setup. Its stable `signal_id` binds schema, setup family, named definition id, algorithm version, configuration hash, setup key, instrument, and direction; lifecycle status, timestamps, evidence, and reasons live under a separate content hash. Recalculating the same setup therefore deduplicates while a definition, algorithm, or configuration revision creates a distinct signal identity.

The initial lifecycle is `candidate -> armed -> triggered`, with invalidated and expired terminal exits. Candidate means Direction evidence exists, Armed adds Location, and Triggered adds Aggression. A transition cannot skip a stage, move time backward, retain the same status, or mutate a terminal signal. Every transition carries the prior content hash, complete current snapshot, appended evidence, reason codes, and its own deterministic transition id.

Evidence is typed by Direction, Location, Aggression, or Follow-through and identifies either a market-context feature or a deterministic market-data window. Direction and Location require feature evidence. Armed state requires available Direction and Location; Triggered state additionally requires available Aggression. Reported, inferred, partial, and unavailable fidelity remain explicit. Unavailable evidence can explain why a setup did not progress but cannot qualify a lifecycle stage.

The setup key is a stable SHA-256 identity derived from family, named definition, instrument, direction, and a caller-supplied deterministic anchor. Presentation text, receipt time, active/background role, Discord routing, and mutable scores do not participate in dedupe identity.

### Direction Definition And Regime Contracts

`SignalDefinitionConfig` gives one named/versioned interpretation of the DLA family explicit timeframe roles. Definitions are enabled independently per instrument. The initial `intraday_context` definition evaluates on completed 1m context, requires agreeing 1h and 15m Direction plus matching 5m confirmation, and treats opposing daily context as degraded rather than vetoed. Other definitions, including a later scalp interpretation, can select different primary and confirmation roles without changing the family or hard-coding those timeframes in the evaluator.

### Live Signal Runtime

`CommittedMarketContextBundle` is one instrument's point-in-time feature set. It permits one feature per timeframe, rejects cross-instrument and future evidence, and requires the evaluation-timeframe feature to be current at the evaluation timestamp. The contract name describes the required upstream guarantee: live composition creates it only from successfully committed feature ids. The pure evaluator does not infer durability from an in-memory object.

Direction qualification fails closed when primary evidence is missing, neutral, or conflicting, or when configured confirmation is insufficient. Context can be ignored, degrade a candidate, or veto it by definition policy. Every considered feature id remains attached as typed Direction evidence with its original fidelity.

`DirectionRegimeTracker` emits at most one candidate while a definition/instrument remains in the same qualified direction. Its setup anchor is the UTC timestamp when that qualified regime began, not each subsequent 1m update. Missing, neutral, conflicting, insufficient-confirmation, and context-veto assessments cannot qualify a new entry, but they preserve an existing regime because loss of strict entry alignment is not proof of reversal. A newly fully qualified opposite direction ends the old regime and starts a distinct candidate. Restart seeds open regimes from verified persisted signals and rejects setup keys inconsistent with their creation timestamp.

For an open signal, soft Direction degradation is exposed as a degraded evidence gap. It preserves the Location episode, resets ordinary exit confirmation, and must block later Trigger progression until Direction is qualified again. It does not append a lifecycle transition. Hard Direction invalidation currently requires the complete named definition to qualify in the opposite direction from newly committed closed-bar evidence; repeated 1m evaluations of unchanged higher-timeframe features cannot manufacture confirmation.

### Location Zone Contracts

Direction is long-lived context; a DLA trade setup is a repeatable entry into a direction-aligned location. `LocationPolicyConfig` declares accepted source kinds, their analytical timeframes, ATR-relative proximity tolerance, and the minimum number of distinct source kinds required. The initial intraday policy includes 15m/5m structural levels and FVGs plus 1m session value-area edges and VWAP. These defaults are versioned signal configuration and may be calibrated without embedding thresholds in evaluator code.

`SignalLocationZone` separates semantic zone identity from its latest observation. Its `zone_id` binds schema, instrument, direction, source and zone kinds, timeframe, and a deterministic origin anchor. Exact feature id, observation timestamp, bounds, fidelity, and reasons remain payload evidence but do not change identity. A developing session VWAP or value edge can therefore move while remaining the same zone; a new swing, FVG, or product session must receive a new origin anchor.

Direction alignment is fail-closed: long zones may be support, bullish FVG, value-area low, or session VWAP; short zones may be resistance, bearish FVG, value-area high, or session VWAP. A zone rejects mismatched source/type pairs, inverted bounds, untrimmed anchors, naive timestamps, and incompatible direction.

`SignalLocationMatch` binds one semantic zone to the exact evaluation feature, observed price and timestamp, calculated distance, applied tolerance, and reason codes. A match cannot predate its zone evidence or exceed tolerance. Edge-triggered entry/exit episodes and attachment to Armed signal state remain subsequent 5C.2 slices.

Location derivation accepts the product-session start explicitly in UTC; it never infers a CME or exchange session from the UTC calendar date. Long evaluation selects nearest support, bullish active FVGs, developing value-area low, and session VWAP. Short evaluation selects nearest resistance, bearish active FVGs, developing value-area high, and session VWAP. Structural and FVG anchors retain their originating observation/detection time and prices, while value-edge and VWAP anchors retain the product-session start.

The current evaluation-timeframe close is matched against every configured zone. Distance is zero inside a zone; otherwise source-timeframe ATR multiplied by the policy fraction defines proximity. Missing ATR prevents an outside-zone proximity claim but does not erase an exact inside-zone match. FVG policy may use zero tolerance to require containment. Match fidelity combines the source-zone and exact evaluation-feature input fidelity without upgrading either.

Qualification requires the configured number of distinct matched source kinds, not merely several levels from one kind. Existing but unmatched sources return `not_at_location`; partial matches below confluence return `insufficient_confluence`; unavailable policy/current-clock evidence returns `missing_evidence`. Missing configured timeframes or source payloads mark the result degraded. Nested level/FVG timestamps newer than their committed feature fail closed as look-ahead evidence.

### Repeatable Location Episodes

`SignalLocationEpisode` binds one repeatable setup opportunity to definition, instrument, Direction, Direction-regime anchor, UTC entry timestamp, and the canonically sorted semantic zone ids matched on entry. Exact entry matches retain their feature revisions, prices, tolerances, fidelity, and reasons but match ordering does not affect episode identity. Every match must use the episode instrument, Direction, and entry timestamp.

`LocationEpisodeObservation` carries one definition/instrument's Direction regime, current evaluation price, and Location qualification at an evaluation timestamp. The tracker emits `entered`, `active`, `favorable_departure`, `departure_unresolved`, `exit_pending`, `exited`, `replaced`, `evidence_gap`, or `no_episode`. Any overlap with an entry zone keeps the existing episode even if other confluence joins or leaves. A qualified set with no entry-zone overlap replaces the old episode immediately because it is a different semantic area.

Departure is measured against the complete original entry-zone geometry and each match's persisted tolerance. A long thesis is adversely breached only below every entry zone's lower tolerated edge; a short thesis only above every upper tolerated edge. Crossing every opposite edge is favorable departure. Price between those boundaries is unresolved displacement, not invalidation. Favorable and unresolved departure preserve the episode and reset adverse confirmation. `exit_confirmation_bars` consecutive completed adverse-breach observations, initially two, are required to exit. `missing_evidence` also preserves the episode and resets confirmation because it cannot claim a breach. A fully qualified opposite Direction regime ends or replaces the episode immediately. After confirmed exit, later entry creates a new id even in the same Direction regime.

Exact retries of the latest observation return the same decision without advancing counters. Different content at the same evaluation timestamp and backward event time fail closed. Direction qualification exposes the active regime anchor on every qualified or missing-evidence decision so composition never reads private tracker state.

### Durable Location Arming

An episode entry creates a deterministic Candidate whose setup key is anchored by the location episode id. The Candidate retains current Direction feature evidence, Direction-regime anchor, and episode id but no Location matches. Its immediate Candidate-to-Armed transition appends deduplicated Location feature references and the complete structured entry matches. Armed and Triggered snapshots require episode identity plus available Location evidence covering every source and evaluation feature used by those matches.

Candidate creation and the initial Armed transition share one SQLite transaction. Exact retries are idempotent. Initial-content, transition, or attached outbox conflicts roll back the Candidate insert, transition history, current snapshot, and notification obligation together. A disjoint-zone replacement similarly invalidates the old Armed signal and creates plus arms the new signal atomically; a conflict in any side leaves the old signal unchanged.

Restart reads continue to verify the initial Candidate hash and complete transition chain before restoring state. The Armed snapshot reconstructs the canonical `SignalLocationEpisode`; its calculated episode id must match the stored id. The Location tracker accepts at most one active episode per definition/instrument, and the Direction tracker restores the canonical UTC regime anchor without assuming the episode-based setup key is a Direction-regime key.

Episode exit or replacement produces an Invalidated transition only when its ended episode id matches the Armed signal. Expiry is not guessed here: the useful Armed observation window depends on Stage 5D Aggression cadence and will be explicit configuration there.

### Aggression Observation Contracts

`AggressionPolicyConfig` selects confirmation methods explicitly by runtime
role. The active instrument initially uses `tick_aggression`; background
instruments use `bar_impulse_proxy`. This is not a failure fallback: expected
tick evidence cannot silently degrade to OHLCV proxy evidence. A role change
must begin a method-consistent window rather than combining evidence modes.

Both methods use a configured one-minute window and a larger Armed expiry
measured in completed definition observations. Wall-clock time does not age an
Armed signal: market closure, a reconnect, or a missing bar cannot impersonate
observed market cadence. Keeping the policy absent preserves the prior
definition configuration hash and leaves Stage 5D behavior disabled.

`evaluate_aggression_window` is currently a pure, unwired policy boundary. It
accepts only complete, non-revision `classified_ticks` bars after the Armed
timestamp. Reported IB OHLCV bars cannot impersonate tick aggression. The
latest consecutive window measures classified-volume coverage, direction-signed
delta, ATR-relative follow-through and adverse excursion, plus optional pace
against a pre-Arm baseline. Quote response remains explicitly unavailable in
this first provider-limited model.

`evaluate_bar_impulse_window` is a separate pure boundary for complete reported
IB bars. It requires directional bar persistence, directional close location,
ATR-relative follow-through, bounded adverse excursion, and volume pace against
a pre-Arm baseline. It never calculates or claims classified delta. Qualified
proxy evidence is always `partial`, uses the source `ib:bar_impulse_proxy`, and
retains order-flow and quote-response unavailability in its reasons.

A qualified window emits deterministic Aggression and Follow-through
market-data-window references sharing one reproducible window id. Full quote-test
classification is `inferred`; accepted tick windows containing unknown volume
are `partial`. The confirmation method participates in window identity and is
also encoded in the evidence source so persistence, logs, and later context
models cannot confuse the two. Expiry retains terminal evidence: an observed
but insufficient window keeps its actual fidelity and failure reasons, while a
missing expected window records `unavailable` evidence. Neither case can
qualify Triggered state.

Runtime collection, post-commit bar handoff, Triggered/Expired persistence, and
restart reconstruction remain subsequent Stage 5D slices. Until those are
wired, configuring a policy changes definition identity but does not activate
live progression.

### Durable Signal State

SQLite stores one current `SignalSnapshot` per signal id plus its immutable initial-candidate content hash. Every accepted `SignalTransitionEvent` is append-only and receives a contiguous per-signal sequence number independent of market timestamps. Restart restoration validates typed row metadata, candidate identity, transition identity, the complete previous-to-current content-hash chain, and agreement between the final transition and current snapshot.

Creating the exact candidate or applying the exact transition again is an idempotent duplicate. A different initial payload under the same signal id is a conflict. A transition must match both the stored prior content hash and source status, so concurrent contenders from one prior state cannot both commit.

An optional pending `NotificationOutboxRecord` may be attached to a transition. The transition event, current snapshot replacement, history append, and outbox enqueue share one SQLite transaction. Outbox identity, dedupe, aggregate signal id, event type, schema, and content conflicts fail the whole transaction. Topic and destination selection remain notification policy rather than signal-domain state.
