<p align="center" style="background: black">
  <img src="docs/assets/markeitech-logo.png" alt="Markeitech" style="max-width: 100%">
</p>

>### **"When you have eliminated the impossible, whatever remains, however improbable, must be the truth."** - Sherlock Holmes

> "No Obstacles; Only Challenges; This is Just a Ride." - Markeitect

> "Build only what the evidence can defend; leave the rest configurable." - Kite

Markeitech is a live-first market-intelligence and decision-support system for discretionary
index trading. V2 runs a read-only NautilusTrader `LiveNode` against Interactive Brokers and is
building an adaptive, multi-instrument evidence stream for deterministic measurements, durable
state, semantic market events, options intelligence, and an advisory AI agent.

The runtime does not place orders. Automated execution is intentionally absent.

## Project Credits

- **Markeitect** - market architect, founder, trader, product owner, and system designer
- **Kite** - co-builder, architecture and engineering collaborator

### Architects

- **WT** - option-flow architect

## Current State

The accepted V2 runtime includes:

- NautilusTrader `2.0.0rc3` with a guarded Interactive Brokers paper-data connection;
- actor-owned system control, static watchlist, and shared native acquisition;
- session/calendar ownership and adaptive evidence-health contracts;
- purpose-specific historical dependency execution;
- deterministic quote, completed-bar, session, calendar-window, and rolling measurements;
- PostgreSQL operational audit, schema recovery, and compact evidence recency profiles;
- Discord system-health projection;
- passive host/process/cache telemetry and sustained resource-health transitions; and
- explicit supervision, bounded queues, deduplication, and failure isolation.

V3-03 session metrics is active through merged Slice 2. Connected acceptance debt and the next
review gate are tracked in [current status](docs/current-status.md). Only explicitly admitted V2
analytics and trading semantics are active.

## Supported Development Environment

The supported local path is:

- macOS;
- Python 3.13 managed by [uv](https://docs.astral.sh/uv/);
- Docker Desktop with Docker Compose;
- PyCharm, with terminal commands documented as the portable fallback;
- TWS or IB Gateway connected to the user's own paper account; and
- the user's own market-data entitlements and Discord webhook.

Node.js is not part of the current runtime setup.

## Quick Start

Clone the repository, then install the locked V2 environment:

```bash
uv sync --project v2 --locked --dev
```

Create local files without replacing an existing machine configuration:

```bash
test -e v2/.env || cp v2/.env.example v2/.env
test -e v2/config/system.local.toml || \
  cp v2/config/system.example.toml v2/config/system.local.toml
```

Edit `v2/.env` with a local PostgreSQL password, matching DSN, and a Discord system-health
webhook. Edit `v2/config/system.local.toml` for the local IB port/client ID, current explicit
futures contracts, entitled instruments, and reviewed runtime policy.

Start Docker Desktop, then run the setup doctor:

```bash
./scripts/check-env
```

Run offline verification:

```bash
uv run --project v2 ruff check v2/src v2/tests
uv run --project v2 pytest -q v2/tests -m "not postgres"
```

For the normal connected workflow, start Docker Desktop and run:

```bash
docker compose --env-file v2/.env -f v2/compose.yaml up -d --wait postgres
uv run --project v2 markeitech-system v2/config/system.local.toml \
  --connect I_UNDERSTAND_THIS_CONNECTS_TO_IB --keep-awake
```

This command connects to IB. Review the [developer setup](docs/operations/developer-setup.md) and
[V2 IB setup](docs/operations/ib-setup.md) before the first connected run.

## Configuration Ownership

- `v2/config/system.example.toml` is the tracked starting template.
- `v2/config/system.local.toml` is the ignored machine/runtime configuration.
- `v2/.env.example` documents required environment keys.
- `v2/.env` contains ignored local secrets.
- `.idea/` is entirely local; create IDE launchers around the documented command as needed.

Never commit `.env`, `system.local.toml`, runtime logs, vendor exports, database dumps, or other
files under `v2/data/`.

## Repository Map

- `v2/` - active runtime, tests, configuration template, and Docker service during the
  root-promotion transition
- `docs/` - current authority, architecture, operations, roadmap, research, and notes
- `AGENTS.md` - portable AI-agent entrypoint and mandatory working boundaries
- `markeitech.md` - governing project and engineering charter

During the first root-promotion PR, the sole runtime remains under `v2/`, so use the explicit
`--project v2` commands above. The accepted
[root-promotion plan](docs/roadmap/v2-complete-codebase-migration-plan.md) moves that project to the
repository root in the second PR. The root `scripts/check-env` command remains the active setup
doctor throughout the transition.

## Documentation

Start with the [documentation map](docs/README.md), then read:

- [project charter](markeitech.md)
- [current status](docs/current-status.md)
- [development guidelines](docs/development-guidelines.md)
- [developer setup](docs/operations/developer-setup.md)
- [GitHub workflow](docs/operations/github-workflow.md)

## License

Copyright (c) 2026 Markeitect. All rights reserved. See [LICENSE](LICENSE).
