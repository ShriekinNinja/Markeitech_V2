# Connected Operational Boot With Zero Instruments

Status: implemented for review; **ready for Markeitect live test**, not live-accepted.

## Outcome And Scope

`config/system.operational.toml` starts the native Nautilus IB data client and exactly ten
operational actors: System Control, Session State, Evidence Health, Historical Evidence Planner,
Data Acquisition, Discord Health, Runtime Resources, Runtime Resource Health, Operational
Persistence, and Dashboard. The loopback dashboard starts with an empty watchlist. The watchlist is disabled and empty. There are no instrument loads, market-data
subscriptions, historical requests, analytical actors, visual capture, diagnostic probes, execution
clients, or model calls. Configured calendars remain active independently of instruments.

This is a connected operational baseline. It does not implement runtime instrument addition,
market-evidence readiness, broker account observation, or the conversational Sir Loke bot. Discord
uses the existing two outbound webhooks. Adding instruments currently requires a validated profile
and a restart; this task does not introduce a dynamic universe controller.

## Configuration And Contracts

The profile uses system schema 27. For older local profiles, remove the complete `[acquisition]`
and `[historical.probe]` sections, plus `[visual_debug_capture]`,
the entire `[metrics]` tree (including quote quality, session measurements, and entity analysis) if
present, and update
`schema_version` to 27. Add `[ib_execution]` and `[risk_engine]` from the tracked example,
leaving execution disabled for this operational profile. Keep `[historical]` and its
production request limits. The loader rejects older schemas and retired sections.

`watchlist.enabled` defaults to true; a disabled watchlist must have `members = []`. Enabling the
watchlist requires at least one member. Metric-producing actors and their configuration have
been removed.

The acquisition-status payload retains its version-1 shape and now accepts an empty expected set.
Its readiness means that the configured instrument-definition work is complete, including explicitly
zero work. System Control requires the acquisition owner's matching status before releasing empty
startup readiness. Acquisition subscribes to its normal control/demand contracts but does not run
its historical polling timer when the instrument scope is empty.

The zero-instrument Discord operational card is enabled explicitly by composition. It does not
infer an empty workload from missing watchlist or demand events. It reports only persistence and
acquisition initialization, and states that connectivity, calendars, telemetry, and delivery need
separate evidence. Ordinary instrument profiles retain their existing readiness join.

The native IB connection and exact CLI confirmation remain unchanged. There is no dependency,
database-schema, retention-policy, execution-authority, or provider-ownership change. Resource
samples use the existing operational-events ledger, at six samples per minute with this profile.
The resource thresholds are reviewable baseline values, identified by `operational-boot-v1`;
critical Discord mentions are disabled in this profile.

## Setup And Commands — Markeitect Only

Use the PR head reported in the handoff and verify it with `git rev-parse HEAD`. Run from the
repository root. Keep the existing `.env` and local profiles intact. The existing locked `.venv`
must be provisioned as described in [developer setup](developer-setup.md).

Create a separate ignored local copy, without overwriting an existing one:

```bash
cp -n config/system.operational.toml config/system.operational.local.toml
```

Review that copy before running. Set the correct TWS/IB Gateway host, port, and a free nonzero client
ID. The template uses `127.0.0.1:4002`, client `20`; these values do not select or identify an account
mode. Keep TWS API read-only enabled. Keep `watchlist.enabled = false`, `members = []`, the ten-actor
roster, and analytics disabled. Review the resource thresholds for this machine.

Have PostgreSQL running using the existing [PostgreSQL operations](v2-postgresql.md). The existing
ignored `.env` must supply:

- `MARKEITECH_POSTGRES_DSN`;
- `MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK`;
- `MARKEITECH_DISCORD_OPERATIONAL_EVENTS_WEBHOOK`.

An offline construction check is available; it does not validate connections or database readiness:

```bash
.venv/bin/markeitech system build --config config/system.operational.local.toml
```

Start the connected run:

```bash
.venv/bin/markeitech system run --config config/system.operational.local.toml --connect I_UNDERSTAND_THIS_CONNECTS_TO_IB
```

This command initializes/repairs the existing operational schema, opens a runtime-run record,
connects the native IB data client, posts Discord notifications, samples the host and native cache,
and writes operational audit records. No execution client or market-data demand is configured.
It does not launch TWS, start Docker, or invoke a model.

Stop by pressing **Ctrl+C once in the launching terminal**. Wait for native shutdown and the normal
return. Do not force-kill a healthy draining run. If shutdown has not completed within 60 seconds,
record the outstanding workers/client state and request investigation; do not claim clean closure.

## Three-Minute Live Scenario And Evidence

Observe the runtime for three minutes after initialization, then stop it. Use the run ID printed
in `SYSTEM_RUN_START` to correlate the terminal, log file, and PostgreSQL rows. With the default
relative log directory, output is under `data/logs`, with the `markeitech-operational` file name.
Do not change the default CLI profile or PyCharm configuration for this test.

| Condition | Evidence required for acceptance |
| --- | --- |
| IB connected | Native IB client connection-success output and the matching client/session in TWS; node construction or global READY alone is insufficient |
| Operational actors started | Native actor-start output for the exact ten actors, with no faults |
| Persistence ready | `SYSTEM_HEALTH` reaches READY after persistence/acquisition startup, and matching run/health/resource records are actually in PostgreSQL |
| Calendars initialized | `CALENDAR_TRANSITION` for every configured calendar, plus `EVIDENCE_SESSION_STATE_SYNC` and `HISTORICAL_PLAN_SESSION_STATE_SYNC` reaching LIVE |
| Discord available | Health and zero-instrument operational cards visible; matching `DISCORD_HEALTH_DELIVERED` and `DISCORD_OPERATIONAL_DELIVERED` success results |
| Runtime measured | Repeated `RUNTIME_RESOURCE` samples; cache observation successful with zero instruments, quotes, trades, bar types and bars |
| Resource health evaluated | `RUNTIME_RESOURCE_HEALTH_SUMMARY` reports samples evaluated and zero rejected samples; check any sustained WARNING/CRITICAL transitions against actual measurements |
| Zero market-data work | `DATA_ACQUISITION_SUMMARY` has zero instrument requests/receipts and no streams; historical planner has zero planned demands; no instrument probe runs |
| Clean stop | Persistence and Discord worker summaries reconcile accepted work with stored/delivered work, zero failed/rejected/pending, no worker timeout, and the matching runtime run closes as STOPPED |

A resource evaluator starts with an internal NORMAL state; its existence alone is not measurement.
Require nonzero evaluated samples. A three-minute run does not exercise the full 90-sample RSS
growth window, long outages, provider reconnect, entitlements, market-data delivery, or analytical
usefulness. Mark those conditions not exercised.

Stop and record a failed test for unexpected instrument requests/subscriptions, actor faults,
calendar conflicts or exhausted synchronization retries, missing telemetry, failed/rejected audit
writes, failed webhook delivery, critical resource pressure, or an IB startup failure. A process
that remains alive with those failures has not passed this scenario. Existing global health does
not aggregate every optional projection or resource condition.

Write a sanitized result to `data/operational-boot-review.md` containing the tested SHA, run ID,
start/stop UTC timestamps, actual actor roster, outcomes for each row above, resource summary,
worker reconciliation, observed limits, and Markeitect's verdict: accepted / changes requested /
not exercised. Never include DSNs, webhook URLs, credentials, raw market data, or database dumps.
Do not commit the local result or runtime logs.

## Offline Evidence And Remaining Limits

The focused test drives all nine real actors through the native rc4 lifecycle, with SQL and HTTP
I/O and host resource samples replaced by deterministic test boundaries. Native cache observation,
actor signals, calendar synchronization, worker queues, and shutdown are exercised. Separate checks
cover the exact roster, empty native provider loads, configuration rejection, acquisition payload
round trips, and explicit zero-work Discord rendering. This proves only the exercised offline
behavior, not IB/Discord/PostgreSQL connectivity or host measurements.

Existing provider recovery and operational persistence debts remain. In particular, a failed native
run may remain open as crash evidence, and the existing CLI terminal-write/shutdown reconciliation
is not a new end-to-end durability guarantee. The live scenario above must verify its own closure.

The implementation remains on a scoped PR for Markeitect review, live test, and merge. Roll back by
stopping this run and selecting the previously accepted profile at its reviewed head. No destructive
migration or data purge is required.
