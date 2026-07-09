# Interactive Brokers Setup

## Stage 0 Posture

Interactive Brokers is documented but not connected in Stage 0.

Market-data startup begins in Stage 2 only after explicit NQ contract configuration and operator approval.

## Supported Connection Paths

Preferred:

- NautilusTrader Interactive Brokers adapter.

Allowed only when needed:

- Narrow native IB API adapter for capabilities NautilusTrader does not expose.

Both paths must use the same contract identity, timestamp, session, health, reconnection, persistence, and deduplication rules.

## Local TWS / IB Gateway Defaults

`.env.example` uses paper TWS defaults:

- host: `127.0.0.1`
- paper TWS port: `7497`
- paper IB Gateway port: `4002`
- live TWS port: `7496`
- live IB Gateway port: `4001`

Use read-only API mode during data stages.

## Required TWS / Gateway Setting

Configure TWS or IB Gateway to return market-data timestamps in UTC before connecting NautilusTrader.

## Contract Configuration

Initial runtime requires an explicit NQ futures contract. Do not configure continuous futures for canonical data capture.

Required values:

- `NQ_SYMBOL=NQ`
- `NQ_EXCHANGE=CME`
- `NQ_CONTRACT_EXPIRY=YYYYMMDD`
- `NQ_INSTRUMENT_ID=<explicit NautilusTrader instrument id>`

The runtime must fail clearly if these values are missing when market-data startup is implemented.

## Execution Safety

Execution is disabled by default:

- `MARKEITECH_MODE=data_only`
- `MARKEITECH_ENABLE_EXECUTION=false`
- `IB_READ_ONLY_API=true`

Do not add account or order-routing requirements during Stage 0.
