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
- `docs/notes/`
- accepted architecture and operations documents
- roadmaps, research, history, and archives

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
- TWS or IB Gateway configured for a user-owned paper account
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
[system/data-flow maintenance procedure](../architecture/system-dataflow-maintenance.md).

## 1. Clone And Install

```bash
git clone https://github.com/ShriekinNinja/Markeitech_V2.git Markeitech
cd Markeitech
uv sync --project v2 --locked --dev
```

The locked install creates `v2/.venv`. Do not run root `uv sync`; the root project is preserved V1.

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
invoke `$kite:markeitech-advisor-router` to activate Kite for one task and its direct follow-ups;
Kite then selects required advisors by default. The plugin contains engineering advisors and
declares no runtime code, package dependency, credential, MCP server, app connector, or autonomous
authority. Some advisors require approved unauthenticated public documentation for current
evidence. Repository or global Codex configuration is a separate trust surface and is not made safe
by the plugin manifest. `AGENTS.md` remains the always-on repository authority while keeping Kite
dormant unless explicitly invoked.

The council overview and acceptance status are documented in
[`markeitech-advisor-council.md`](../architecture/markeitech-advisor-council.md); that document
links the canonical machine-checkable policy and observed acceptance ledger.
During local plugin development, validate source first, then use the supported cachebuster helper
and reinstall `kite@markeitech` only after that cache mutation is approved. A new task is required
to test discovery. Repository/source validation must not be reported as installed routing proof.

Run the dependency-free source validator from the repository root:

```bash
python3 -B plugins/kite/scripts/validate_advisor_council.py
python3 -B -m unittest plugins/kite/tests/test_validate_advisor_council.py
```

The validator proves structural policy only. It does not prove fresh-task selection, delegated
execution, effective read-only tool isolation, redaction, safe failure, or plugin revocation.

## 2. Create Local Configuration

The following commands never overwrite existing machine files:

```bash
test -e v2/.env || cp v2/.env.example v2/.env
test -e v2/config/system.local.toml || \
  cp v2/config/system.example.toml v2/config/system.local.toml
```

Both destination files are ignored by Git.

Existing local configurations created before schema 21 require a manual migration. Set
`schema_version = 21`, remove the retired `[visual_acceptance]` and `[live_evidence_review]`
sections, and replace inline `[[sessions.calendars]]` definitions with the schema-3
`calendar_catalog = "market-calendars.toml"` reference under `[sessions]`. Also add the bounded
projection settings shown in `system.example.toml`: `projection_lookback_days`,
`projection_lookahead_days`, `maximum_projection_days`, and
`maximum_calendars_per_request`. Add `[sessions.projection_retry]` with the tracked bounded
`response_timeout_ms`, `maximum_attempts`, `retry_backoff_ms`, and `maximum_elapsed_ms` values;
these local actor-delivery controls are independent of IB historical polling and metric-demand
retries. The referenced catalog path is resolved relative to the system
TOML and must exist; the tracked catalog is `v2/config/market-calendars.toml`. Set `calendar_ids`
to the exact catalog definitions this profile needs; unused entries are validated but are not
instantiated. Analytical profiles and windows must use the configured product-phase names, such
as `GLOBEX` for the CME/CBOT equity definitions. Concrete instrument-to-calendar bindings belong
only to `[[watchlist.members]]`; rolling a futures contract does not require editing the calendar
catalog. The CME/CBOT definitions also expose overlapping `ASIA`, `LONDON`, and `NEW_YORK` phases.
Those phase clocks describe market regions and do not create analytical windows by themselves.

The loader rejects older schemas, dead visual sections, inline definitions or overrides,
unavailable provider columns, invalid phase timezones, incomplete source/correction identity,
obsolete catalog-owned instrument mappings, and projection requests which exceed configured
bounds. Do not overwrite
the rest of an existing machine-local profile; compare it with `system.example.toml` and preserve
its reviewed IB, instrument, analytical-profile, persistence, and metric settings.

### Environment file

Set these values in `v2/.env`:

- `MARKEITECH_POSTGRES_PASSWORD`: a local password for the Docker PostgreSQL service
- `MARKEITECH_POSTGRES_DSN`: the same password in the application connection string
- `MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK`: a webhook owned by the current user

The password in the DSN must match `MARKEITECH_POSTGRES_PASSWORD`. Never commit the file or paste
its values into issues, pull requests, logs, or documentation.

### System configuration

Review `v2/config/system.local.toml` before connecting:

1. `[ib].host`, `[ib].port`, and `[ib].client_id`
2. current explicit futures contracts in historical probes, profile bindings, and watchlist members
3. instruments covered by the current user's IB market-data entitlements
4. active `calendar_ids`, calendar/profile assignments, and the dedicated
   `market-calendars.toml` catalog identity
5. Discord, resource-health, persistence, historical, and metric policy

The tracked example contains reviewed defaults, not universally valid contracts or entitlements.
Do not replace explicit futures with continuous futures without a separate architecture decision.

## 3. Configure TWS Or IB Gateway

Use paper trading and enable socket clients in read-only mode. Set the API port in the local system
configuration to the actual TWS/Gateway port. Common defaults are:

- paper TWS: `7497`
- paper IB Gateway: `4002`
- live TWS: `7496`
- live IB Gateway: `4001`

Markeitech's tracked example currently reflects the project's paper Gateway-style port. A custom
TWS port is valid when TWS and `system.local.toml` agree.

Configure TWS or IB Gateway to send instrument-specific API attributes in **instrument timezone**
for the pinned Nautilus `2.0.0rc3` runtime. Its Rust `ibapi 3.3.0` dependency cannot parse IB's
valid dashed UTC `HistoricalDataEnd` metadata. This is a temporary transport compatibility setting:
Nautilus and Markeitech still normalize bar instants to Unix nanoseconds and use UTC internally.
Keep execution unavailable. Each user must supply their own account, permissions, and
subscriptions. A dependency or TWS/Gateway change requires one bounded connected timestamp
calibration before historical-data acceptance.

See [V2 Interactive Brokers setup](ib-setup.md) for the complete checklist.

## 4. Verify The Machine

Start Docker Desktop, then run:

```bash
./scripts/check-env
```

The doctor checks the supported OS, required commands, locked V2 environment, local files,
configuration parsing, required environment values, Docker daemon, and Compose model. It does not
connect to IB. Use `./scripts/check-env --with-ib` only when TWS/Gateway should already be listening.

Run offline verification:

```bash
uv run --project v2 ruff check v2/src v2/tests
uv run --project v2 pytest -q v2/tests -m "not postgres"
```

## 5. Configure PyCharm

1. Open the repository root.
2. Select the existing interpreter at `v2/.venv/bin/python`.
3. Allow PyCharm to create its local module and workspace files.
4. Confirm Docker Desktop and TWS/IB Gateway are running.
5. Create a local Shell run configuration around the command in the next section if desired.

The repository ignores `.idea/` completely. PyCharm launchers, modules, database views, window
layout, and interpreter metadata remain local and cannot affect another machine's checkout.

## 6. Run From The Terminal

```bash
docker compose --env-file v2/.env -f v2/compose.yaml up -d --wait postgres
uv run --project v2 markeitech-system v2/config/system.local.toml \
  --connect I_UNDERSTAND_THIS_CONNECTS_TO_IB --keep-awake
```

The confirmation token is intentional. The command connects to Interactive Brokers but does not
enable execution.

Expected startup behavior:

1. PostgreSQL is reachable and its schema is verified/repaired idempotently.
2. The operational run is opened.
3. Actors start independently and publish readiness through the Nautilus bus.
4. Instrument definitions, acquisition, historical dependencies, and evidence health converge.
5. System control publishes `READY` only when mandatory prerequisites are satisfied.
6. Discord receives eligible system-health transitions.

Runtime logs are written under `v2/data/logs/`. All `v2/data/` content is local and ignored.

## 7. Stop And Inspect

Use the PyCharm stop control or send `SIGINT`. A controlled shutdown records `STOPPING`, drains
bounded persistence work, returns from Nautilus, and closes the run as `STOPPED`.

PostgreSQL remains running after Markeitech stops:

```bash
docker compose --env-file v2/.env -f v2/compose.yaml ps
docker compose --env-file v2/.env -f v2/compose.yaml stop postgres
```

Do not use `docker compose down --volumes` unless the operational history is intentionally being
destroyed.

## Moving To Another Machine

Git alone restores source, tests, project instructions, notes, and the portable AI entrypoint. To
continue with local state, transfer these separately through a secure channel:

- `v2/.env`
- `v2/config/system.local.toml`
- required files under `v2/data/`, such as licensed vendor exports
- an optional PostgreSQL dump when operational history must continue

Create a PostgreSQL backup on the original machine:

```bash
mkdir -p "$HOME/markeitech-backups"
docker compose --env-file v2/.env -f v2/compose.yaml exec -T postgres \
  pg_dump -U markeitech -d markeitech -Fc \
  > "$HOME/markeitech-backups/markeitech-postgres.dump"
```

On the new machine, start PostgreSQL and restore the dump:

```bash
docker compose --env-file v2/.env -f v2/compose.yaml up -d --wait postgres
docker compose --env-file v2/.env -f v2/compose.yaml exec -T postgres \
  pg_restore -U markeitech -d markeitech --clean --if-exists \
  < "$HOME/markeitech-backups/markeitech-postgres.dump"
```

Keep the dump outside Git. `*.dump` is also ignored defensively. PyCharm database connections and
workspace layout may be recreated or transferred separately; they do not affect runtime behavior.

## Continuing With An AI Agent

Open the repository root so the tracked `AGENTS.md` instructions apply. The agent must read the
project charter, current status, development guidelines, and relevant stage plan before changing
code. Normal Codex work does not require Kite. Install the tracked Kite plugin as described above
when its explicit engineering-council mode should be available; invoking Kite then makes its
specialist consultations automatic for that task. Git preserves those authorities, plugin sources,
notes, and roadmaps; it does not preserve plugin installation state, private account memory, or
prior chat transcripts. Record any durable decision in the smallest authoritative tracked document
rather than relying on chat history alone.

## Troubleshooting

### `markeitech-system` is missing

Run `uv sync --project v2 --locked --dev`, then invoke commands through
`uv run --project v2` or `v2/.venv/bin/python`.

### PostgreSQL does not start

Confirm Docker Desktop is running, port `5432` is available, and the password/DSN agree. Inspect:

```bash
docker compose --env-file v2/.env -f v2/compose.yaml ps
docker compose --env-file v2/.env -f v2/compose.yaml logs postgres
```

### IB cannot connect

Confirm TWS/Gateway is logged into paper trading, socket clients are enabled, read-only API is on,
the configured host/port match, the client ID is unused, and the API is allowed from localhost.

### Instruments do not become ready

Check contract expiry, venue/symbology, market-data entitlements, session state, and whether the
requested market is currently publishing. A missing entitlement is not repaired by retrying.

### Discord startup fails

Create a webhook in a channel owned by the current user and place its complete URL only in
`v2/.env`. The tracked example intentionally contains no webhook.
