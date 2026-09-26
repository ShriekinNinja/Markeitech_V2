<p align="center" style="background: black">
  <img src="docs/assets/markeitech-logo.png" alt="Markeitech" style="max-width: 100%">
</p>

>### **"When you have eliminated the impossible, whatever remains, however improbable, must be the truth."** - Sherlock Holmes

> "No Obstacles; Only Challenges; This is Just a Ride." - Markeitect

> "Build only what the evidence can defend; leave the rest configurable." - Kite

Markeitech is a live trading platform built on NautilusTrader. The immediate priority is a working
execution engine and account monitor, followed by multiple actors, strategies and indicators
operating together in real time. Small issue-defined changes reach live use promptly; actual
operation and Markeitect's feedback drive improvements.

The current runtime supplies market data and operational actors. Execution and account monitoring
are the next development priority, not implemented capabilities. See the
[live foundation plan](docs/roadmap/live-foundation-plan.md).

## Project Credits

- **Markeitect** - market architect, founder, trader, product owner, and system designer
- **Kite** - co-builder, architecture and engineering collaborator

### Architects

- **WT** - option-flow architect

## Current State

The implemented foundation includes NautilusTrader `2.0.0rc5`, guarded Interactive Brokers market
data, actor composition, static watchlist/shared acquisition, session/evidence health, historical
planning, PostgreSQL operational audit, resource monitoring and optional Discord health webhooks.
The tracked example composes ten actors. Shared metric/entity contracts exist; active indicator
production and strategy registration do not. The current node registers a data client and no
execution client.

See [current status](docs/current-status.md) for implementation and known gaps. The project direction
includes execution; a run or order requires explicit account and action authorization.

## Supported Development Environment

The supported local path is:

- macOS;
- Python 3.13 managed by [uv](https://docs.astral.sh/uv/);
- Docker Desktop with Docker Compose;
- PyCharm as an optional convenience over the authoritative terminal CLI;
- TWS or IB Gateway connected to the user's chosen account; and
- the user's own market-data entitlements and Discord webhook.

Node.js is not part of the current runtime setup.

## Quick Start

Clone the repository, then install the locked environment from the repository root:

```bash
uv sync --locked --dev
```

Optionally install the repository command on your user `PATH` using uv's standard tool mechanism:

```bash
uv tool install --editable .
uv tool update-shell
```

The editable tool resolves the command from this checkout. The locked `.venv` remains the
authoritative development and verification environment. The examples below use the PATH command;
prefix them with `.venv/bin/` if you skip the optional tool installation.

Create local files without replacing an existing machine configuration:

```bash
test -e .env || cp .env.example .env
test -e config/runtime.local.toml || \
  cp config/runtime.example.toml config/runtime.local.toml
```

Edit `.env` with a local PostgreSQL password, matching DSN, and a Discord system-health
webhook. Edit `config/runtime.local.toml` for the local IB port/client ID and reviewed runtime
policy. Review its `[watchlist]` table for current explicit futures contracts and entitled
instruments.

Start Docker Desktop, then use the compact disconnected startup to check the selected local
configuration, start PostgreSQL, build without connecting to IB, and exit:

```bash
markeitech system start --config config/runtime.local.toml
```

For development, run tests added or changed for the issue. Broad regression checks run on the PR.

For the normal connected workflow, start Docker Desktop and add the explicit `--ib` flag:

```bash
markeitech system start --config config/runtime.local.toml --ib
```

This command checks the configured IB endpoint and then connects to IB. It does not start TWS or
IB Gateway. Review the [developer setup](docs/operations/developer-setup.md) and
[V2 IB setup](docs/operations/ib-setup.md) before the first connected run.

## Configuration Ownership

- `config/runtime.example.toml` is the tracked starting template.
- `config/runtime.local.toml` is the ignored machine/runtime configuration.
- [`config/system.policy.toml`](config/system.policy.toml) is the tracked runtime limits and
  delivery policy selected by the example and default local profile.
- The `[watchlist]` table in the runtime profile selects exact instruments and requested feeds.
- [`config/system.calendars.toml`](config/system.calendars.toml) is the tracked calendar catalog,
  containing reusable exchange-calendar definitions, product phases, and source-cited corrections.
- `.env.example` documents required environment keys.
- `.env` contains ignored local secrets.
- `.idea/` is entirely local; create IDE launchers around the documented command as needed.

Under `[sessions]` in the policy TOML, `calendar_catalog = "system.calendars.toml"` selects the
catalog relative to the selected runtime profile. Active calendars come from the distinct
`calendar_id` values in `[[watchlist.members]]`; the policy supplies calendars for an empty
watchlist. Rolling a futures contract does not require editing the calendar catalog. See
[developer setup](docs/operations/developer-setup.md) for configuration details.

Never commit `.env`, `runtime.local.toml`, runtime logs, vendor exports, database dumps, or other
files under `data/`.

## Repository Map

- `src/markeitech/` - the sole active runtime package
- `tests/` - runtime and contract tests
- `config/` - tracked configuration templates and calendar definitions
- `compose.yaml`, `pyproject.toml`, and `uv.lock` - root service and Python project definitions
- `docs/` - current product, status, architecture, roadmap, reference, development, operations, and
  generated API documentation
- `AGENTS.md` - portable AI-agent entrypoint and mandatory working boundaries
- `markeitech.md` - governing project and engineering charter

The V2 project is rooted directly in the repository; no nested project selector is required.
Migration history and recovery boundaries remain in Git and the recorded migration tags. Run
`markeitech --help` (or `.venv/bin/markeitech --help` without the optional PATH installation) for
the authoritative runtime, static-doc, diagram, verification, and environment-check command
hierarchy. The retained `markeitech-system` entry point is a backward-compatible runtime alias; it
delegates to the same behavior owner.

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
- [Live trading foundation plan](docs/roadmap/live-foundation-plan.md)
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
