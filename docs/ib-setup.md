# Interactive Brokers Setup

## Current Posture

Interactive Brokers is documented but not connected yet.

Market-data startup begins in Stage 2 only after explicit active-instrument configuration and operator approval.

The Stage 2 runtime is centered on a Nautilus `TradingNodeConfig`. Automated tests may build the LiveNode configuration and subscription plan, but they must not start the node or connect to IB.

## Supported Connection Paths

Preferred:

- NautilusTrader Interactive Brokers data client inside a LiveNode.

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

Initial runtime requires an explicit active futures contract. NQ is the first active target. Do not configure continuous futures for canonical data capture.

Initial active NQ values:

- `NQ_SYMBOL=NQ`
- `NQ_EXCHANGE=CME`
- `NQ_CONTRACT_EXPIRY=YYYYMMDD`
- `NQ_INSTRUMENT_ID=<explicit NautilusTrader instrument id>`

The runtime must fail clearly if active instrument values are missing when market-data startup is implemented.

Background instruments may be configured for historical warmup followed by live 1-minute bar tracking. Examples include ES, SPX, VIX, QQQ, SPY, MAG7 symbols, and later additional operator-selected instruments. Background instruments are not tick-by-tick streams unless promoted to active.

## Dry-Run Validation

Before connecting to IB, validate the local runtime plan:

```bash
uv run markeitech-market-data-plan config/market-data.example.toml
```

The command builds the Nautilus `TradingNodeConfig`, validates the market-data registry, and prints planned warmups and subscriptions. It does not start `TradingNode.run()` and does not connect to IB.

The dry-run output includes Nautilus-oriented request intents. These are validation artifacts only; they are not live subscriptions until a later guarded bootstrap translates them into Nautilus calls.

## Guarded LiveNode Bootstrap

Stage 2 can build a Nautilus `TradingNode` object from validated config, but starting it remains manual-only.

LiveNode start requires all of:

- `run_live_node=true`
- `manual_live_node_start=true`
- explicit confirmation token: `I_UNDERSTAND_THIS_CONNECTS_TO_IB`

The checked-in example config keeps both start flags disabled.

## Manual Smoke Command

After the dry-run command succeeds, copy or edit a local config for smoke testing:

```toml
[runtime]
manual_live_node_start = true
run_live_node = true
```

Then run:

```bash
uv run markeitech-market-data-smoke config/market-data.example.toml --confirm I_UNDERSTAND_THIS_CONNECTS_TO_IB
```

The command prints the same plan summary as the dry run and refuses to start unless both config flags and the confirmation token are present. Automated tests use a fake node; they do not connect to IB.

Dry-run output also includes ordered LiveNode actions. These actions are still validation artifacts until a later adapter maps them to real Nautilus calls.

## Execution Safety

Execution is disabled by default:

- `MARKEITECH_MODE=data_only`
- `MARKEITECH_ENABLE_EXECUTION=false`
- `IB_READ_ONLY_API=true`

Do not add account or order-routing requirements during Stage 0.
