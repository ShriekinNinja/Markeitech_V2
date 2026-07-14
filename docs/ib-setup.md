# Interactive Brokers Setup

## Current Posture

Interactive Brokers connectivity is implemented behind a manual-only smoke command. No live connection is made by automated tests or the default configuration.

Market-data startup begins in Stage 2 only after explicit active-instrument configuration and operator approval.

The Stage 2 runtime is centered on a Nautilus `TradingNodeConfig` and a Markeitech market-data actor. Automated tests build configuration, action plans, coordinators, and fake nodes, but they must not start a real node or connect to IB.

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

Stage 2 can prepare a Nautilus `TradingNode` from validated config by registering the IB data-client factory, attaching the market-data actor, and building the node clients. Starting it remains manual-only.

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

The command prints the same plan summary as the dry run and refuses to start unless both config flags and the confirmation token are present. After startup, the actor requests every configured historical warmup, waits for all asynchronous completions, validates historical coverage, and only then submits active and background live subscriptions. Automated tests use fake actors and nodes; they do not connect to IB.

The PyCharm `Market Data - Continuous Live Context` run configuration invokes this guarded command with `config/market-data.local.toml`. Unlike the acceptance command, it has no duration limit and runs until stopped. Context is emitted as one human-scannable `MARKET_CONTEXT` line per updated instrument and timeframe while the full LiveNode and persistence lifecycle remains active.

The local runtime enables Nautilus JSONL file logging at `data/logs/markeitech-live.jsonl`. It captures IB, LiveNode, persistence, readiness, context, and structure messages from the same kernel logger while the console remains human-readable. Files rotate at 25 MiB with ten backups and are ignored by Git. Share or inspect this file when diagnosing a live run; do not commit it because broker/runtime metadata may be present.

The runtime monitors required-stream freshness and external 1-minute bar continuity. Every instrument contract must declare `calendar_id` and `session_profile`; recovery uses the pinned product-calendar adapter to exclude holidays, early closes, breaks, and other expected closures. Use `full` when IB bars are expected across published extended hours, `regular` for market-open through market-close expectations, and `continuous` only with the native `24/7` calendar. These package-shipped rules are not a live exchange-hours feed, so representative schedules must be reconciled with observed IB bars before production use. NautilusTrader remains responsible for physical IB reconnect and transport retry behavior.

With persistence enabled, the initial warmup bars are flushed before exact one-minute repair requests begin. Repairs are issued sequentially and fairly across configured non-crypto instruments. The acceptance report records each instrument's recovery request count, missing intervals before and after repair, confirmed provider-empty intervals, and remaining reason codes. A degraded recovery is observable but does not by itself invalidate otherwise sufficient warmup analysis; storage failure or an unbounded recovery plan does fail startup.

Dry-run output also includes ordered LiveNode actions. The manual smoke path maps those actions to real Nautilus actor calls after the startup guards pass.

## Duration-Limited Paper Acceptance

Create `config/market-data.local.toml` from the checked-in example and keep it local. Set the actual paper socket port plus both manual startup flags. The repository ignores this filename.

Run the offline plan first:

```bash
uv run markeitech-market-data-plan config/market-data.local.toml
```

Then run the bounded acceptance command:

```bash
uv run markeitech-market-data-acceptance config/market-data.local.toml \
  --duration 90 \
  --confirm I_UNDERSTAND_THIS_CONNECTS_TO_IB
```

The command starts the real prepared LiveNode, observes it for the requested duration, stops it gracefully, and prints a JSON report. It passes only when warmup completes, the active instrument receives trade and quote ticks, every enabled instrument receives completed external 1-minute bars, source health is healthy, IB is read-only, and execution remains disabled.

For the first paper run, prefer NQ active plus ES background. Add SPX and other independently entitled feeds after the CME path passes so entitlement failures remain easy to isolate.

## Execution Safety

Execution is disabled by default:

- `MARKEITECH_MODE=data_only`
- `MARKEITECH_ENABLE_EXECUTION=false`
- `IB_READ_ONLY_API=true`

Do not add account or order-routing requirements during Stage 0.
