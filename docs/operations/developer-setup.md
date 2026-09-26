# V2 Developer Setup And Machine Handoff

This is the authoritative fresh-machine path for Markeitech V2. It supports continuing the same
project on another macOS machine without sharing secrets through Git or contacting the original
machine during routine setup.

## What Git Preserves

A normal clone includes the active V2 source and tests plus the tracked project authority:

- `AGENTS.md`
- `markeitech.md`
- `docs/development-guidelines.md`
- `docs/current-status.md`
- the accepted product, architecture, roadmap, reference, development, and operations documents
- the isolated tools and their tracked documentation artifacts

These files preserve project rules, limits, decisions, handoffs, and implementation state. Local
Codex/AI chat history, account memory, IDE workspace state, secrets, vendor data, runtime logs, and
Docker volumes are outside Git. `AGENTS.md` provides the portable AI entrypoint to the tracked
authority; transfer the required local items explicitly as described below.

## Supported Environment

- macOS
- Docker Desktop with Docker Compose
- PyCharm
- `uv`
- Python 3.13
- TWS or IB Gateway configured for the user-selected account
- user-owned market-data entitlements
- user-owned Discord webhook

The terminal workflow is fully supported. PyCharm is a convenience layer over the same commands.

The project also contains a separately locked, offline architecture-documentation environment at
`tools/system-diagram`. Provision it only when generating diagrams:

```bash
uv sync --project tools/system-diagram --locked
```

The shared PyCharm configuration **Generate Sys Diagram** then validates the canonical TOML,
checks supported source/configuration drift, and atomically regenerates the tracked documentation
artifacts. It does not use the V2 runtime environment, `.env`, IB, Docker, PostgreSQL, Discord, or
the network. See the
[system/data-flow maintenance procedure](../../tools/system-diagram/docs/maintenance.md).

After provisioning, use the root Python-owned CLI for supported operations:

```bash
.venv/bin/markeitech --help
.venv/bin/markeitech docs --help
.venv/bin/markeitech diagrams --help
```

For a user-PATH command bound to this checkout, use uv's editable tool installation:

```bash
uv tool install --editable .
uv tool update-shell
```

Restart the shell if uv changes its `PATH` configuration. The editable tool is an operator
convenience; use the locked root `.venv` for development and repository verification.

Invoke the already-provisioned entry point directly. Do not put `uv run` in front of routine CLI
operations: `uv run` may create or synchronize the root environment before the CLI can enforce its
own offline and isolation checks. Dependency installation remains the separate, explicit
`uv sync --locked --dev` step above. `.venv/bin/python -m markeitech` is the equivalent module
entry point when an installed script is inconvenient.

The closed hierarchy and its side-effect class are:

| Command | Class | Owned behavior |
| --- | --- | --- |
| `system build` | disconnected | Builds the configured Nautilus node without running or connecting it. |
| `system run` | connected | Requires the exact IB token, then delegates to the existing runtime owner. |
| `system start` | local service or connected | Checks the selected ignored local profile, starts PostgreSQL, builds disconnected by default, or checks the IB endpoint and runs connected when `--ib` is supplied. |
| `docs validate` / `check` / `test` | offline read-only | Uses the locked API-doc interpreter; `check` compares a fresh build with tracked output. |
| `docs generate` | offline write | Atomically regenerates the complete tracked `docs/api` artifact set. |
| `diagrams validate` / `check` / `test` | offline read-only | Uses the locked diagram interpreter; `check` includes the drift census. |
| `diagrams generate` | offline write | Regenerates the canonical complete diagram artifact set with drift checking. |
| `verify lint` / `test` / `all` | offline read-only | Uses the active root interpreter; `all` runs lint then non-PostgreSQL tests and fails fast. |
| `verify postgres` | local service | Runs only PostgreSQL-marked tests against the explicitly configured test database. |
| `environment check` | local diagnostic | Reads local setup/configuration and checks Docker without starting a service; `--with-ib` opts into a TCP-listener check. |

All fixed child-process commands run from the repository root in an owned process group and return
their child exit code. Parent `SIGINT`, `SIGTERM`, and `SIGHUP` are forwarded to the complete child
group. The first signal permits two seconds for cleanup; a repeated signal or expired deadline
kills the group, including descendants. A cancellation returns the shell-compatible status
`128 + signal` (`130`, `143`, or `129`, respectively), and no owned child remains able to publish
after the wrapper returns. The isolated docs and diagram launcher passes only deterministic
Python/locale controls and the caller's executable `PATH`; runtime, provider, database, Discord,
GitHub, proxy, cloud, and other caller variables are not inherited. The CLI has no command registry,
shell interpolation, arbitrary-command escape hatch, or automatic dependency provisioning.

## 1. Clone And Install

```bash
git clone https://github.com/ShriekinNinja/Markeitech_V2.git Markeitech
cd Markeitech
uv sync --locked --dev
```

The locked install creates the root `.venv` used by the runtime, tests, and normal PyCharm project
interpreter.

### Install The Kite Advisor Plugin

The repository includes the Kite source under `plugins/kite/` and a local Markeitech marketplace
manifest under `.agents/plugins/`. Register the cloned repository as a marketplace, then install
Kite:

```bash
codex plugin marketplace add .
codex plugin add kite@markeitech
```

Start a new Codex task after installation so its bundled skills are discovered. A new task remains
normal Codex: installing or enabling Kite makes it available, not active. Explicitly select Kite or
invoke `$kite:markeitech-advisor-router` for a task and direct follow-ups. Kite selects relevant
skills for the primary agent; no project advisor roles or council dispatch are required.
The package adds no runtime code, dependency, credential, MCP server, or app connector.

See [Kite focused skills](../development/kite-advisor-council.md) for the workflow and
[Kite operations](kite.md) for authorized installation, versioning, identity, fresh-task checks,
and rollback. Source validation is not installed-behavior proof.

```bash
python3 -B plugins/kite/scripts/validate_skill_library.py
python3 -B -m unittest discover -s plugins/kite/tests
```

## 2. Create Local Configuration

The following commands never overwrite existing machine files:

```bash
test -e .env || cp .env.example .env
test -e config/system.local.toml || \
  cp config/system.example.toml config/system.local.toml
```

Both destination files are ignored by Git. The example and local system profiles reference the
tracked `config/system.watchlist.toml`; its `[watchlist]` table owns membership and retry settings.
The `watchlist_file` path is resolved relative to the system TOML. To keep a machine-specific
watchlist, copy it to `config/system.watchlist.local.toml` and point the local system profile there.
Existing inline `[watchlist]` profiles still load, but a profile must use exactly one source.

The current loader accepts only system schema **29**. To migrate a schema-23/24 local profile:

1. Remove the complete `[acquisition]` section, which contained only native-consumer diagnostic settings.
2. Remove the complete `[historical.probe]` section; keep `[historical]` and its production limits.
3. Remove `[visual_debug_capture]` if present; the capture actor and renderer have been removed.
4. Remove the entire `[metrics]` tree, including quote quality, session measurements, entity analysis, and all child tables.
5. Remove the entire `[dashboard]` section if present. Set `schema_version = 29` and compare the result with the corresponding tracked profile.

For a schema-25/26/27/28 profile, remove the entire `[dashboard]` section if present, then set
`schema_version = 29`. Keep the production `[historical]` section.

Preserve machine-specific IB settings, paths, thresholds, and secret environment references.
Local files are not migrated automatically. For profiles older than schema 23, also apply the
calendar and current-state changes below; a version-number edit alone is insufficient.

For pre-calendar-cutover profiles, remove the retired `[visual_acceptance]` and
`[live_evidence_review]` sections and replace inline `[[sessions.calendars]]` definitions with the
schema-3 `calendar_catalog = "market-calendars.toml"` reference under `[sessions]`. Add the bounded
projection settings shown in `system.example.toml`: `projection_lookback_days`,
`projection_lookahead_days`, `maximum_projection_days`, and
`maximum_calendars_per_request`. Add `[sessions.projection_retry]` with the tracked bounded
`response_timeout_ms`, `maximum_attempts`, `retry_backoff_ms`, and `maximum_elapsed_ms` values;
these local actor-delivery controls are independent of IB historical polling and metric-demand
retries. The referenced catalog path is resolved relative to the system
TOML and must exist; the tracked catalog is `config/market-calendars.toml`. Set `calendar_ids`
to the exact catalog definitions this profile needs; unused entries are validated but are not
instantiated. Concrete instrument-to-calendar bindings belong only to `[[watchlist.members]]` in
the selected watchlist file; rolling a futures contract does not require editing the calendar
catalog. The CME/CBOT definitions also expose overlapping `ASIA`, `LONDON`, and `NEW_YORK` phases.
Those phase clocks describe market regions and do not create analytical windows by themselves.

Include the complete `[sessions.current_state_delivery]` section from the current example:
versioned response timeout, attempts/backoff/elapsed bounds, per-calendar and total transition
buffers, and boundary-delivery grace. Remove the entire `[metrics]` tree; its quote-quality,
session-measurement, and entity-analysis actors and configuration have been removed.

The loader rejects older schemas, dead visual sections, inline definitions or overrides,
unavailable provider columns, invalid phase timezones, incomplete source/correction identity,
obsolete catalog-owned instrument mappings, and projection requests which exceed configured
bounds. Do not overwrite
the rest of an existing machine-local profile; compare it with `system.example.toml` and preserve
its reviewed IB, instrument, and persistence settings.

### Environment file

Set these values in `.env`:

- `MARKEITECH_POSTGRES_PASSWORD`: a local password for the Docker PostgreSQL service
- `MARKEITECH_POSTGRES_DSN`: the same password in the application connection string
- `MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK`: a webhook owned by the current user

The password in the DSN must match `MARKEITECH_POSTGRES_PASSWORD`. Never commit the file or paste
its values into issues, pull requests, logs, or documentation.

### System configuration

Review `config/system.local.toml` and its selected watchlist file before connecting:

1. `[ib].host`, `[ib].port`, and `[ib].client_id`
2. current explicit futures contracts in profile bindings and watchlist members
3. instruments covered by the current user's IB market-data entitlements
4. active `calendar_ids`, calendar/profile assignments, and the dedicated
   `market-calendars.toml` catalog identity
5. Discord, resource-health, persistence, historical, and metric policy

The tracked example contains reviewed defaults, not universally valid contracts or entitlements.
Do not replace explicit futures with continuous futures without a separate architecture decision.

## 3. Configure TWS Or IB Gateway

Log into the account/session selected by the trader and enable socket clients in read-only mode.
Set the API port in local system configuration to the port actually configured in TWS/Gateway.
The tracked example's `4002` value is only an example endpoint; replace it with the selected
session's port when needed. Product behavior and acceptance do not depend on account mode.

Configure TWS or IB Gateway to send instrument-specific API attributes in **instrument timezone**
for the pinned Nautilus `2.0.0rc5` runtime. The dashed UTC `HistoricalDataEnd` parsing limitation
was established under rc3 and remained open under rc4; rc5 connected timestamp calibration is
pending. Retain this temporary transport compatibility setting until that calibration:
Nautilus and Markeitech still normalize bar instants to Unix nanoseconds and use UTC internally.
Keep execution unavailable. Each user must supply their own account, permissions, and
subscriptions. A dependency or TWS/Gateway change requires one bounded connected timestamp
calibration before historical-data acceptance.
Record the rc5 result in [issue #59](https://github.com/ShriekinNinja/Markeitech_V2/issues/59).

See [V2 Interactive Brokers setup](ib-setup.md) for the complete checklist.

## 4. Verify The Machine

Start Docker Desktop, then run:

```bash
.venv/bin/markeitech environment check
```

The doctor checks the supported OS, required commands, locked V2 environment, local files,
configuration parsing, required environment values, Docker daemon, and Compose model. It does not
connect to IB. Use `.venv/bin/markeitech environment check --with-ib` only when TWS/Gateway should
already be listening.

For development, run tests added or changed for the issue. Broad regression checks run on the PR.

## 5. Configure PyCharm

1. Open the repository root.
2. Select the existing interpreter at `.venv/bin/python`.
3. Allow PyCharm to create its local module and workspace files.
4. Confirm Docker Desktop and TWS/IB Gateway are running.
5. Create a local Shell run configuration around the command in the next section if desired.

The repository ignores `.idea/` completely. PyCharm launchers, modules, database views, window
layout, and interpreter metadata remain local and cannot affect another machine's checkout.

## 6. Run From The Terminal

To construct the configured node without provider or service connection:

```bash
.venv/bin/markeitech system build --config config/system.local.toml
```

The compact disconnected path checks the environment, starts PostgreSQL, builds the selected
configuration without connecting to IB, and exits:

```bash
.venv/bin/markeitech system start --config config/system.local.toml
```

With the optional PATH installation, the equivalent command is:

```bash
markeitech system start --config config/system.local.toml
```

Add `--ib` only for a connected runtime:

```bash
.venv/bin/markeitech system start --config config/system.local.toml --ib
```

With the optional PATH installation, the equivalent connected command is:

```bash
markeitech system start --config config/system.local.toml --ib
```

The flag is explicit connection consent. The command checks that the configured TWS/IB Gateway
endpoint is listening before it starts PostgreSQL and delegates to the existing connected runtime.
It connects to Interactive Brokers but does not start TWS/IB Gateway or enable execution. The
lower-level `system run --connect I_UNDERSTAND_THIS_CONNECTS_TO_IB` command remains available.

Expected startup behavior:

1. PostgreSQL is reachable and its schema is verified/repaired idempotently.
2. The operational run is opened.
3. Actors start independently and publish readiness through the Nautilus bus.
4. Instrument definitions, acquisition, historical dependencies, and evidence health converge.
5. System control publishes `READY` only when mandatory prerequisites are satisfied.
6. Discord receives eligible system-health transitions.

Runtime logs are written under `data/logs/`. All `data/` content is local and ignored.

## 7. Stop And Inspect

Use the PyCharm stop control or send `SIGINT`. A controlled shutdown records `STOPPING`, drains
bounded persistence work, returns from Nautilus, and closes the run as `STOPPED`.

PostgreSQL remains running after Markeitech stops:

```bash
docker compose --env-file .env -f compose.yaml ps
docker compose --env-file .env -f compose.yaml stop postgres
```

Do not use `docker compose down --volumes` unless the operational history is intentionally being
destroyed.

## Moving To Another Machine

Git alone restores source, tests, project instructions, notes, and the portable AI entrypoint. To
continue with local state, transfer these separately through a secure channel:

- `.env`
- `config/system.local.toml`
- `config/system.watchlist.local.toml`, if the local profile references a machine-specific copy
- required files under `data/`, such as licensed vendor exports
- an optional PostgreSQL dump when operational history must continue

Create a PostgreSQL backup on the original machine:

```bash
mkdir -p "$HOME/markeitech-backups"
docker compose --env-file .env -f compose.yaml exec -T postgres \
  pg_dump -U markeitech -d markeitech -Fc \
  > "$HOME/markeitech-backups/markeitech-postgres.dump"
```

On the new machine, start PostgreSQL and restore the dump:

```bash
docker compose --env-file .env -f compose.yaml up -d --wait postgres
docker compose --env-file .env -f compose.yaml exec -T postgres \
  pg_restore -U markeitech -d markeitech --clean --if-exists \
  < "$HOME/markeitech-backups/markeitech-postgres.dump"
```

Keep the dump outside Git. `*.dump` is also ignored defensively. PyCharm database connections and
workspace layout may be recreated or transferred separately; they do not affect runtime behavior.

## Continuing With An AI Agent

Start with the development resume point at the top of
[`current-status.md`](../current-status.md); it links to the accepted stage's execution progress,
next slice, exact code/test entrypoints, verification commands, and explicit deferred work. Do not
use an old implementation worktree or the historical planning baseline as the current starting
point without reconciling it with `master` and preserving local changes.

Open the repository root so the tracked `AGENTS.md` instructions apply. The agent must read the
project charter, current status, development guidelines, and relevant stage plan before changing
code. Normal Codex work does not require Kite. Install the tracked Kite plugin as described above
when its explicit engineering-council mode should be available; invoking Kite then makes its
specialist consultations automatic for that task. Git preserves those authorities, plugin sources,
notes, and roadmaps; it does not preserve plugin installation state, private account memory, or
prior chat transcripts. Record any durable decision in the smallest authoritative tracked document
rather than relying on chat history alone.

## Troubleshooting

### `markeitech` is missing

Run `uv sync --locked --dev`, then invoke commands through `uv run` or `.venv/bin/python`.
The retained `markeitech-system` entry point is a compatibility alias for the original runtime
surface; new terminal and CI workflows use `markeitech`.

## Commands Intentionally Outside The Unified CLI

The repository command census keeps the following operations explicit and separate because they
have different authority, prerequisites, or side effects:

- `uv sync` provisions locked root or tool environments; the CLI diagnoses missing environments
  but never installs or updates them.
- `start` may run the fixed `docker compose ... up -d --wait postgres` operation. Other Compose
  services, inspection, stopping, backup, restore, and destructive lifecycle operations remain
  explicit operator commands.
- `verify postgres` is a conspicuous local-service test command and is excluded from `verify all`.
- `scripts/sir-kite-pr.py` and Git commands own authenticated publication and source-control
  workflow; the CLI provides no GitHub or arbitrary-command executor.
- the repository-owned Kite validator and plugin install/cachebuster commands remain development-
  time plugin maintenance, not V2 runtime or repository verification.
- backup, restore, connected acceptance, browser review, and other operator procedures remain
  explicit operations under their dedicated guides.

The shell implementation at `scripts/check-env` remains the single setup-doctor behavior owner
behind `markeitech environment check`; it is not a second command-definition surface.

### PostgreSQL does not start

Confirm Docker Desktop is running, port `5432` is available, and the password/DSN agree. Inspect:

```bash
docker compose --env-file .env -f compose.yaml ps
docker compose --env-file .env -f compose.yaml logs postgres
```

### IB cannot connect

Confirm TWS/Gateway is logged into the selected account, socket clients are enabled, read-only API is on,
the configured host/port match, the client ID is unused, and the API is allowed from localhost.

### Instruments do not become ready

Check contract expiry, venue/symbology, market-data entitlements, session state, and whether the
requested market is currently publishing. A missing entitlement is not repaired by retrying.

### Discord startup fails

Create a webhook in a channel owned by the current user and place its complete URL only in
`.env`. The tracked example intentionally contains no webhook.
