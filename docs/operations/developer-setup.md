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

Start a new Codex task after installation so its bundled skills are discovered. The plugin contains
engineering advisors and no runtime code, secrets, external connections, or autonomous authority.
`AGENTS.md` remains the always-on repository authority even when the plugin is not installed.

## 2. Create Local Configuration

The following commands never overwrite existing machine files:

```bash
test -e v2/.env || cp v2/.env.example v2/.env
test -e v2/config/system.local.toml || \
  cp v2/config/system.example.toml v2/config/system.local.toml
```

Both destination files are ignored by Git.

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
4. calendar/profile assignments
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

Configure IB API timestamps for the instrument timezone expected by the pinned Nautilus V2 adapter.
Keep execution unavailable. Each user must supply their own account, permissions, and subscriptions.

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
code. Install the tracked Kite plugin as described above so required specialist consultations are
available on a fresh machine. Git preserves those authorities, plugin sources, notes, and roadmaps;
it does not preserve plugin installation state, private account memory, or prior chat transcripts.
Record any durable decision in the smallest authoritative tracked document rather than relying on
chat history alone.

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
