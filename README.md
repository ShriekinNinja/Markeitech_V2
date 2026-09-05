<p align="center" style="background: black">
  <img src="docs/assets/markeitech-logo.png" alt="Markeitech" style="max-width: 100%">
</p>

>### **"When you have eliminated the impossible, whatever remains, however improbable, must be the truth."** - Sherlock Holmes

> "No Obstacles; Only Challenges; This is Just a Ride." - Markeitect

> "Build only what the evidence can defend; leave the rest configurable." - Kite

Markeitech is a live-first market-intelligence and trading-discipline system for discretionary
index trading. Its first product is **Sir Loke**, a local private Discord trading companion,
mentor, and configurable advisory governor backed by deterministic market, options, broker, policy,
and audit evidence. The current V2 runtime is the read-only NautilusTrader foundation for that
product.

Sir Loke v1 will recommend qualified SPXW/QQQ 0DTE trades, observe paper-account trades entered
through TWS, monitor their thesis and evidence, challenge the trader firmly, and produce after-trade
reports. That experience is accepted product direction but is not implemented yet. The runtime
does not place orders; automated execution is intentionally absent.

## Project Credits

- **Markeitect** - market architect, founder, trader, product owner, and system designer
- **Kite** - co-builder, architecture and engineering collaborator

### Architects

- **WT** - option-flow architect

## Current State

The implemented foundation includes:

- NautilusTrader `2.0.0rc4` with a guarded Interactive Brokers paper-data connection
  (the upgrade is merged and offline-verified; earlier connected evidence does not automatically
  establish rc4 provider behavior);
- actor-owned system control, static watchlist, and shared native acquisition;
- session/calendar ownership and adaptive evidence-health contracts;
- purpose-specific historical dependency execution;
- substantial deterministic measurement/entity code and historical acceptance evidence, while the
  active V3 profile keeps those owners disabled during the incomplete V3-03 replacement;
- PostgreSQL operational audit, schema recovery, and compact evidence recency profiles;
- optional outbound Discord system-health webhooks, not a two-way Sir Loke bot;
- passive host/process/cache telemetry and sustained resource-health transitions; and
- explicit supervision, bounded queues, deduplication, and failure isolation.

The tracked V3 ES profile currently composes eight calendar, evidence, historical-planning,
acquisition, probe, and persistence actors. V3-03 Slices 1-2 are merged but inactive; Slices 3-9
are unimplemented. Broker trade observation, options intelligence, semantic events, Sir Loke,
the conversational Discord bot, trade episodes, governance, and reports are absent. See
[current status](docs/current-status.md) for the exact surface and
[the Sir Loke v1 product definition](docs/product/sir-loke-v1.md) for the destination.

## Supported Development Environment

The supported local path is:

- macOS;
- Python 3.13 managed by [uv](https://docs.astral.sh/uv/);
- Docker Desktop with Docker Compose;
- PyCharm as an optional convenience over the authoritative terminal CLI;
- TWS or IB Gateway connected to the user's own paper account; and
- the user's own market-data entitlements and Discord webhook.

Node.js is not part of the current runtime setup.

## Quick Start

Clone the repository, then install the locked environment from the repository root:

```bash
uv sync --locked --dev
```

Create local files without replacing an existing machine configuration:

```bash
test -e .env || cp .env.example .env
test -e config/system.local.toml || \
  cp config/system.example.toml config/system.local.toml
```

Edit `.env` with a local PostgreSQL password, matching DSN, and a Discord system-health
webhook. Edit `config/system.local.toml` for the local IB port/client ID, current explicit
futures contracts, entitled instruments, and reviewed runtime policy.

Start Docker Desktop, then run the setup doctor:

```bash
.venv/bin/markeitech environment check
```

Run offline verification:

```bash
.venv/bin/markeitech verify all
```

For the normal connected workflow, start Docker Desktop and run:

```bash
docker compose --env-file .env -f compose.yaml up -d --wait postgres
.venv/bin/markeitech system run \
  --config config/system.local.toml \
  --connect I_UNDERSTAND_THIS_CONNECTS_TO_IB --keep-awake
```

This command connects to IB. Review the [developer setup](docs/operations/developer-setup.md) and
[V2 IB setup](docs/operations/ib-setup.md) before the first connected run.

## Configuration Ownership

- `config/system.example.toml` is the tracked starting template.
- `config/system.local.toml` is the ignored machine/runtime configuration.
- [`config/market-calendars.toml`](config/market-calendars.toml) is the tracked calendar catalog,
  containing reusable exchange-calendar definitions, product phases, and source-cited corrections.
- `.env.example` documents required environment keys.
- `.env` contains ignored local secrets.
- `.idea/` is entirely local; create IDE launchers around the documented command as needed.

Under `[sessions]` in the system TOML, `calendar_catalog = "market-calendars.toml"` selects the
catalog relative to that system file, and `calendar_ids` selects the active definitions. Each
`[[watchlist.members]]` entry binds its instrument to a `calendar_id`; rolling a futures contract
does not require editing the calendar catalog. See [developer setup](docs/operations/developer-setup.md)
for configuration details.

Never commit `.env`, `system.local.toml`, runtime logs, vendor exports, database dumps, or other
files under `data/`.

## Repository Map

- `src/markeitech/` - the sole active runtime package
- `tests/` - runtime and contract tests
- `config/` - tracked configuration templates and calendar definitions
- `compose.yaml`, `pyproject.toml`, and `uv.lock` - root service and Python project definitions
- `docs/` - current authority, architecture, operations, roadmap, research, and notes
- `AGENTS.md` - portable AI-agent entrypoint and mandatory working boundaries
- `markeitech.md` - governing project and engineering charter

The V2 project is rooted directly in the repository; no nested project selector is required. The
[root-promotion plan](docs/roadmap/v2-complete-codebase-migration-plan.md) records the migration and
its recovery boundaries. Run `.venv/bin/markeitech --help` for the authoritative runtime, static-doc,
diagram, verification, and environment-check command hierarchy. The retained `markeitech-system`
entry point is a backward-compatible runtime alias; it delegates to the same behavior owner.

## Making Changes

Every repository change gets a new scoped branch and a GitHub PR, including documentation and
small fixes. Agents implement and verify the requested scope, commit and push the branch, and
open the PR for review. **Markeitect approves and owns the merge; green CI is not merge
permission.** An agent merges only when that specific operation is explicitly delegated.

The integration branch is currently `master`. Do not commit or push changes directly to it,
enable auto-merge, or force-push. Review fixes stay on the same open PR; a new change after merge
gets a new branch. See [CONTRIBUTING](CONTRIBUTING.md) and the
[GitHub workflow](docs/operations/github-workflow.md) for the complete protocol.

## Documentation

Start with the [documentation map](docs/README.md), then read:

- [project charter](markeitech.md)
- [Sir Loke v1 product definition](docs/product/sir-loke-v1.md)
- [current status](docs/current-status.md)
- [development guidelines](docs/development-guidelines.md)
- [developer setup](docs/operations/developer-setup.md)
- [GitHub workflow](docs/operations/github-workflow.md)

API documentation artifacts:
- Repository file source: [docs/api/index.html](docs/api/index.html)
- Hosted site: [https://shriekinninja.github.io/Markeitech_V2/](https://shriekinninja.github.io/Markeitech_V2/)
- Generator and deployment instructions: [docs/operations/v2-api-documentation.md](docs/operations/v2-api-documentation.md)

## License

Copyright (c) 2026 Markeitect. All rights reserved. See [LICENSE](LICENSE).
