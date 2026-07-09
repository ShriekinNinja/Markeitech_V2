# Data Contracts

Stage 0 does not implement domain contracts. This document defines the constraints that Stage 1 must satisfy.

## Versioning

Every externally visible backend event must include:

- schema version
- event type
- instrument identity
- UTC event timestamp
- UTC ingestion or initialization timestamp where relevant

## Contract Identity

Initial instrument support is explicit-expiry NQ futures only.

Required fields:

- root symbol
- exchange
- expiry
- NautilusTrader instrument id
- IB contract identity fields needed for unambiguous resolution

Continuous futures and silent rollover are prohibited for canonical storage and backend events.

## Timestamp Rules

- Store timestamps in UTC.
- Normalize IB/TWS/Gateway timestamps to UTC.
- Use IANA timezones for session calculations.
- Do not use fixed UTC offsets for London or New York sessions.

## Stage 1 Contract Families

Stage 1 should define:

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

## Persistence Expectations

Raw trade ticks, raw bid/ask quote ticks, and canonical one-minute bars should be persisted to Nautilus-compatible Parquet/catalog storage where practical.

SQLite metadata should carry recovery and checkpoint state.

Writes must be idempotent and restart-safe.
