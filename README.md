# Markeitech

Markeitech is a live-first market-analysis and decision-support system for
discretionary index trading, with options as the primary trade expression. It
runs a NautilusTrader `LiveNode` against Interactive Brokers, warms multiple
underlying instruments across configured timeframes, persists deterministic
market context, and evaluates versioned Direction and Location signal evidence.

The system is data-only and read-only. Trading execution is intentionally not
implemented.

## Project Credits

- **Markeitect** - founder, trader, product owner, and system designer
- **Kite** - co-builder, architecture and engineering collaborator
- **WT** - spiritual guideness
- **ESS** - angle investor

## Current State

Implemented foundations include:

- one runtime-switchable active tick-by-tick instrument
- multiple background instruments receiving live 1-minute bars
- timeframe-specific historical warmup and restart recovery
- canonical market events with explicit contract and source identity
- Parquet time-series persistence with SQLite transactional metadata
- deterministic multi-timeframe context, session levels, FVGs, and profiles
- human-readable active-first operator context logs
- durable, restart-safe signal lifecycle persistence
- live post-commit Direction and Location evaluation for active and background
  instruments

The next product slice wires cadence-bounded Aggression and follow-through into
durable live lifecycle transitions for active and background instruments. See
[current status](docs/current-status.md) for the exact boundary and known
validation debt. Options-chain ingestion and analysis are an explicit future
roadmap track rather than part of the current runtime.

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- TWS or IB Gateway for live paper-data runs
- Node.js 22.12 or newer only when working on the deferred frontend

## Setup And Checks

```bash
uv sync
uv run pytest
uv run ruff check .
uv run black --check .
uv run markeitech-market-data-plan config/market-data.example.toml
```

The API skeleton can be started with:

```bash
uv run fastapi dev backend/src/markeitech/api.py
```

It exposes `GET /health` and `GET /readiness`.

## Interactive Brokers Runs

Real IB connections require a local untracked configuration and explicit
confirmation. The continuous paper-data command is:

```bash
uv run markeitech-market-data-smoke \
  config/market-data.local.toml \
  --confirm I_UNDERSTAND_THIS_CONNECTS_TO_IB
```

Duration-limited acceptance runs use:

```bash
uv run markeitech-market-data-acceptance \
  config/market-data.local.toml \
  --duration 300 \
  --confirm I_UNDERSTAND_THIS_CONNECTS_TO_IB
```

Shared PyCharm run configurations are available under `.run/`. Review
[Interactive Brokers setup](docs/operations/ib-setup.md) before connecting.

## Configuration

Use `config/market-data.example.toml` as the tracked template and keep local
credentials, account identifiers, and machine-specific settings out of Git.

The operating posture requires:

- an explicit active instrument
- explicit-expiry futures contracts
- configured background instruments
- UTC API timestamps and explicit session timezones
- read-only/data-only IB access
- no execution configuration

## Documentation

Start with the [documentation map](docs/README.md). The governing project
principles are in the [project charter](markeitech.md), while
[current status](docs/current-status.md) records what is actually complete and
what comes next.
