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

Initial instrument support is explicit-expiry NQ futures only.

Required fields:

- root symbol
- exchange
- expiry
- NautilusTrader instrument id
- IB contract identity fields needed for unambiguous resolution

Continuous futures and silent rollover are prohibited for canonical storage and backend events.

Implemented model:

- `NQContractConfig`

Rejected identity examples:

- `NQ.CME`
- `NQ.XCME`
- IB `CONTFUT`

## Timestamp Rules

- Store timestamps in UTC.
- Normalize IB/TWS/Gateway timestamps to UTC.
- Use IANA timezones for session calculations.
- Do not use fixed UTC offsets for London or New York sessions.

Domain models reject naive timestamps and non-UTC aware timestamps at construction time.

## Stage 1 Contract Families

Stage 1 defines:

- explicit NQ contract configuration
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

Writes must be idempotent and restart-safe.
