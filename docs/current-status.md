# Current Status

**Direction and source inventory reviewed:** 2026-09-24; no new connected run in this batch

**Implementation baseline inspected:** `master` at `417bc3a`

This page is the source of truth for what the active Markeitech checkout implements now. It is
deliberately a current-state ledger, not an implementation diary. Completed design and acceptance
detail remains in the linked architecture, reference, operations, Git history, and pull-request
records.

The [charter](../markeitech.md) and [live foundation plan](roadmap/live-foundation-plan.md)
define direction. Execution and account monitoring are the next priority; changing the plan does
not implement them. Historical verification below is retained with its original scope and dates.

## Status At A Glance

| Area | Current state |
|---|---|
| Runtime | NautilusTrader `2.0.0rc5`, market-data client and code-owned actor composition |
| Provider | Interactive Brokers through TWS/IB Gateway |
| Profiles | Seven-instrument example with ten actors; no separate operational profile |
| Execution and account monitor | Not implemented in the current node; next development priority |
| Strategies and indicators | No strategy registration or active metric-producing actors; shared contracts remain |
| Discord | Optional outbound operational health webhook |
| Persistence | PostgreSQL operational audit and compact evidence-recency profiles |
| CLI | Unified `markeitech` hierarchy, including compact `system start` |

## Current Offline Verification

On 2026-09-05, after aligning documentation and tool relocation with the
unified Python CLI merge at `295cdb7`:

- an offline locked environment sync installed the merged CLI without changing the lockfile;
- `.venv/bin/markeitech verify all` passed Ruff and `700` non-PostgreSQL tests, with `2`
  PostgreSQL-marked tests deselected;
- `.venv/bin/markeitech docs check` documented `261/261` selected public objects and matched all
  `60` committed artifacts;
- `.venv/bin/markeitech diagrams check` passed the manifest/source/configuration drift census,
  generation produced the complete five-view `22`-artifact package, and
  `.venv/bin/markeitech diagrams test` passed all `31` tests;
- all `210` local Markdown link targets across the intended `126` tracked Markdown files resolved;
  and
- `git diff --check` was clean.

These checks establish offline code and documentation consistency only. They do not establish
PostgreSQL integration, provider behavior, a connected rc4 run, broker observation, Discord bot,
model or options acceptance.

Gate 1A subsequently added a focused offline characterization for the pinned native IB execution
path. Its bounded subprocess constructs the genuine client with connection `client_id=1`, a
synthetic explicit account, empty provider loads, and logging bypassed without invoking lifecycle
or report methods. The same seam confirms the pinned client-`0` modulo-1000 constructor rejection.
Tests also verify the exact dependency and installed `RECORD` integrity evidence, measured config
defaults, adversarial construction-only guards, and the current data-only production composition.
See the [Gate 1A evidence reference](reference/ib-observation-gate1.md) for exact artifacts,
commands, source inventory, evidence limits, and verification results.

This evidence proves compiled construction and inspected source only. It does not prove native
startup/wire behavior, network-egress isolation, no-binding/no-order-action behavior, manual TWS
event coverage under the user-reported Master `1` setting, or connected acceptance.

## Operating Posture

- Markeitech is live-first, event-driven and local. The current node is market-data-only;
  execution and account monitoring are active development priorities.
- Markeitect is the only first-version user and retains every trading and product decision.
- The implemented IB client is a NautilusTrader data client. It does not expose broker account,
  order, fill, or position state to Markeitech.
- Connected runs remain manually and explicitly authorized. Automated tests do not connect to IB,
  Discord, or another live provider.
- PostgreSQL stores approved operational facts, not raw quotes, trades, bars, option chains, or
  broker credentials.
- Components continue independently through partial failure where their accepted contracts permit;
  one global `READY` value does not prove that evidence is usable for advice.
- Replay and backtesting remain out of scope.
- Retired source is recoverable through Git history and migration tags but is not current
  authority.

## Tracked Example Profile

[`config/runtime.example.toml`](../config/runtime.example.toml) selects reviewed limits from
[`config/system.policy.toml`](../config/system.policy.toml) and contains seven explicit watchlist
instruments. Its ten actors are System
Control, Session State, Evidence Health, Discord Health, Historical Evidence Planner, Watchlist,
Data Acquisition, Runtime Resources, Runtime Resource Health, and Operational Persistence.

The former `system.v3-es-minimal.toml` review profile has been removed. Single-calendar offline
delivery tests derive a bounded ES fixture from the current template.

## Diagnostic And Inactive Actor Removal

The three runtime diagnostic actors and the private completed-bar foundation implementation are
removed, including their composition, requester admission, configuration, and dedicated tests.
Visual Debug capture, its writer/renderer, configuration, and dedicated tests are also removed.
SessionMetricsActor and its dependent session-reference, market-state, and market-structure
actors are removed, together with their dedicated calculations, configuration, tests, and
replacement plan. QuoteQualityMetricsActor, its midpoint/spread calculations, and its
configuration and dedicated tests are also removed. The current runtime has ten actor classes.
Independent canonical bar/metric and entity contracts remain.

The API registry selects 98 public objects; the diagram source census recognizes ten actor
registrations. Offline checks do not establish connected acceptance.

The tracked runtime example is schema 30: operator choices and watchlist membership are in the
runtime profile, reviewed runtime policy is in `system.policy.toml`, and active calendars are
derived from watchlist members. An empty watchlist uses the policy's `idle_calendar_ids` so the
zero-instrument runtime can still synchronize session state. Complete schema-29 profiles remain
supported. Older local profiles need
their retired `[dashboard]`, `[acquisition]`, `[historical.probe]`,
`[visual_debug_capture]`, and `[metrics]` sections removed before setting schema 29. Retain
`[historical]`, which configures the production acquisition owner. Local files are not migrated
automatically. See [developer setup](operations/developer-setup.md) for the schema-30 split.

## Implemented Foundation

### Runtime and provider boundary

- The package and lockfile pin NautilusTrader `2.0.0rc5`; the earlier rc4 upgrade was merged through PR 17.
- `LiveNode` construction, caller-owned embedded lifecycle tests, guarded production startup,
  controlled shutdown, rotating logs, and explicit IB connection confirmation exist.
- NautilusTrader owns IB market-data connectivity and native normalized observations.
- `DataAcquisitionActor` owns logical provider demand and subscription/request lifetime.
- Static watchlist ownership and native multi-consumer market-data delivery were accepted in the
  predecessor V2 profile.
- Provider-subscription recovery, full connection-loss recovery, and several pacing/cancellation
  semantics remain documented reliability debt.

### Unified operator CLI

- PR 35 added one Python-owned `.venv/bin/markeitech` hierarchy for explicit system build/run,
  static API-documentation and diagram operations, repository verification, and environment
  checks. The legacy `markeitech-system` entry point delegates to the same runtime owner.
- Issue 67 adds the compact `markeitech system start --config CONFIG [--ib]` operator path and an
  optional editable uv tool installation for invoking `markeitech` from the user `PATH`.
  `system start` runs the existing doctor against the selected ignored local profile and starts
  only the existing PostgreSQL Compose service. Without `--ib` it builds disconnected and exits;
  with `--ib` it checks the configured endpoint and delegates to the existing connected runtime
  owner.
- The command hierarchy owns invocation and verification ergonomics; it does not add product
  behavior, a generic task runner, dependency provisioning, arbitrary Docker lifecycle, TWS
  startup, execution authority, GitHub publication, or connected acceptance.
- `markeitech verify all` is offline and excludes the conspicuous `verify postgres` path, which
  requires an explicitly configured disposable local database.
- Connected system execution still requires explicit operator consent
  (`system start --config ... --ib` or the exact lower-level confirmation token) and remains an
  operator-authorized action.

See [developer setup](operations/developer-setup.md) for the complete command contract.

### Calendar, evidence health, and historical acquisition

- `SessionStateActor` owns canonical calendar evaluation and publishes typed transitions and
  bounded current-state projections.
- The tracked calendar catalog contains CBOE SPXW, NYSE, CME equity, CBOT equity, and CME energy
  definitions; only `cme_equity` is active in the V3 ES profile.
- `EvidenceHealthActor` owns source/feed freshness and fidelity state for configured observations.
- `HistoricalEvidencePlannerActor` converts symbolic approved needs into exact UTC request plans;
  `DataAcquisitionActor` executes admitted provider work.
- V3-02 supplies a subscribe-buffer-snapshot-reconcile current-state protocol for late calendar
  consumers. Its connected evidence is bounded to the recorded ES/current-session case.

See [session and evidence health](architecture/session-evidence-health.md) and
[market data and acquisition](architecture/market-data-and-acquisition.md).

### Measurements, entities, and V3 replacement work

The retained implementation includes generic metric/entity contracts and the independent V3-03 Slice 1 completed-bar/metric identities, validation, admission, and
producer-manifest contracts. These contracts do not provide a composed canonical bar or entity
producer. Quote, session, window, rolling, and market-structure calculations and their actors have been
removed. Earlier implementation and connected evidence remain available through Git history.

New analytical production belongs to a selected actor, strategy or indicator issue. Existing
contract tests do not establish active outputs; reach the issue's live scenario promptly.

### Persistence and operational health

- PostgreSQL owns runtime runs, system-health events, generic operational events, and compact
  evidence-recency profiles.
- Schema preflight, idempotent repair, bounded non-blocking admission, batched writes, retry, and
  shutdown reconciliation exist within their recorded acceptance envelope.
- Runtime-resource samples and state transitions exist behind optional configuration; they are
  disabled in the active V3 profile.
- Raw provider observations, historical responses, numerical metric streams, option chains,
  broker order/fill payloads, conversations, and trade episodes are not currently persisted as
  canonical product data.

### Existing Discord projection

`DiscordHealthActor` is an optional outbound projection for health and operational messages.
It has bounded delivery and failure isolation. It remains general operational infrastructure.
It does not receive conversations, calculate market truth or control orders.

### Documentation tooling

- The offline system-diagram utility keeps its manifest, maintenance guide, and generated review
  package under `tools/system-diagram/docs`. It statically reconciles declared sources and
  configuration. Generated diagrams describe their recorded manifest and checkout, not
  automatically the current runtime.
- The isolated API-documentation utility statically validates the versioned public surface and
  generates tracked `docs/api` output. Its GitHub Pages workflow is current at this baseline.
- Neither documentation tool imports the runtime, connects services, or proves live behavior.

### Development collaboration tooling

Kite now supplies focused domain skills for direct use by the primary agent, with optional
independent review. Issue [#63](https://github.com/ShriekinNinja/Markeitech_V2/issues/63) retires the
mandatory advisor roster and allocation/dispatch machinery. The existing explicit router command
remains compatible. See [the library overview](development/kite-advisor-council.md) and
[evaluation record](development/kite-focused-skills-evaluation.md). Source-directed checks do not
establish installed-host discovery, technical isolation, or Markeitect's usefulness verdict.
Development tooling does not activate runtime capabilities.

## Execution And Account Monitoring

The current node configures only a market-data client. There is no production execution client,
account monitor or order-action route. These are implementation gaps to address in the next issue,
not project-wide prohibitions.

The [historical native-client reference](reference/ib-observation-gate1.md) records earlier offline
construction and source inspection. Reuse relevant evidence where current; it is not a mandatory
staged proof gate. The execution issue should reach a small explicitly authorized live scenario
with exact account/client settings, intended actions and limits. See [IB setup](operations/ib-setup.md).

## Connected Acceptance Envelope

Recorded connected acceptance is useful but narrow:

- Earlier V2 profiles established bounded IB market-data subscription, historical request,
  multi-consumer delivery, operational persistence, Discord webhook, resource, measurement, and
  selected entity-projection behavior under the exact recorded sessions and configurations.
- V3-01 accepted the canonical `cme_equity` calendar path for one tracked ES profile and one
  bounded lookback/lookahead envelope.
- V3-02 accepted one late-consumer current-state recovery and five-bar historical request chain.
- The rc5 dependency upgrade passed offline verification. Markeitect reports an online-verified
  rc5 run using the then-named `config/system.example.toml` on 2026-09-17. The exact head, provider responses,
  and sanitized result are not recorded here; [issue #59](https://github.com/ShriekinNinja/Markeitech_V2/issues/59)
  tracks the bounded historical timestamp calibration.
- No connected acceptance establishes SPXW/QQQ options acquisition, a Discord bot, a live model,
  account observation, manual TWS trade detection or trade monitoring.

A connected process start does not establish every runtime capability. A recorded session establishes
only the behavior exercised for its actual account, products, data, and provider conditions.

## Current Gaps And Next Work

- Provider subscription and connection-loss recovery have remaining known gaps.
- Active indicator/metric production and strategy registration need implementation.
- Execution and account/order/fill/position monitoring need implementation and practical live use.

These gaps are not a prerequisite suite for every issue. The [live foundation plan](roadmap/live-foundation-plan.md)
prioritizes execution/account monitoring, then concurrent consumers. Address a gap when selected
or when it directly blocks the issue. Local tests cover added/changed tests and specific CI failures;
PR CI owns broad regression checks. Use live findings to decide subsequent improvements.

## Historical Detail

The active tree intentionally does not retain completed stage logs as competing authority. Stable
decisions are consolidated in the four architecture documents linked from
[`README.md`](README.md). Use Git,
migration tags, and merged pull requests for exact implementation chronology, former research,
review handoffs, and superseded plans.

Historical claims retain only their recorded contract, version, configuration, provider, session,
and acceptance envelope. They do not become current implementation merely because this status page
links to them.
