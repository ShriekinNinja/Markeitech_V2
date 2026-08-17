# Markeitech

Markeitech is a live-first market-intelligence and decision-support system for discretionary
index trading, with SPY and QQQ 0DTE options as the initial trade expressions. V2 runs a
NautilusTrader `LiveNode` against Interactive Brokers and is building an adaptive multi-instrument
data plane for deterministic analysis, semantic events, rolling market state, and advisory AI.

The system is data-only and read-only. Trading execution is intentionally not
implemented.

> “When you have eliminated the impossible, whatever remains, however improbable, must be the truth.” --Sherlock Holmes

>  “No Obstacles; Only Challenges; This is Just a Ride.” --Markeitect

## Project Credits

- **Markeitect** - market architect, founder, trader, product owner, and system designer
- **Kite** - co-builder, architecture and engineering collaborator
- **ESS** - angle investor

### Architects

- **WT** - option flow architect



## Current State

Implemented V2 foundations include:

- a clean NautilusTrader `2.0.0rc1` live runtime and IB paper-data connection
- explicit provider and native market-data boundaries
- PostgreSQL operational run and system-health records
- actor-owned system control, Discord health projection, and operational persistence
- dedicated instrument-definition acquisition ownership
- versioned actor contracts with bounded supervision and failure policy

Stage 8 is defining adaptive acquisition: an open-ended observation universe, continuous native
market streams, capability-derived historical requirements, and policy-checked runtime focus.
No V1 analytics or trading model is implicitly active. See
[current status](docs/current-status.md) for the exact implemented boundary.

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- TWS or IB Gateway for live paper-data runs
- Node.js 22.12 or newer only when working on the deferred frontend

## Setup And Checks

```bash
uv sync --project v2
uv run --project v2 pytest -q v2/tests
uv run --project v2 ruff check v2/src v2/tests
```

## Interactive Brokers Runs

Real IB connections require TWS or IB Gateway, the configured environment, and explicit
confirmation. The V2 command is:

```bash
uv run --project v2 markeitech-system v2/config/system.toml \
  --connect I_UNDERSTAND_THIS_CONNECTS_TO_IB
```

Shared PyCharm run configurations are available under `.run/`. Review
[Interactive Brokers setup](docs/operations/ib-setup.md) before connecting.

## Configuration

Use `v2/config/system.toml` for tracked runtime policy and `v2/.env` for local secrets and
machine-specific values that must remain outside Git.

The operating posture requires:

- explicit-expiry futures contracts
- a configured bootstrap instrument universe
- UTC API timestamps and explicit session timezones
- read-only/data-only IB access
- no execution configuration

## Documentation

Start with the [documentation map](docs/README.md). The governing project
principles are in the [project charter](markeitech.md), while
[current status](docs/current-status.md) records what is actually complete and
what comes next.
