# Current Status

**Last reviewed:** 2026-09-05

**Implementation baseline inspected:** `master` at `06a675e`

This page is the source of truth for what the active Markeitech checkout implements now. It is
deliberately a current-state ledger, not an implementation diary. Completed design and acceptance
detail remains in the linked architecture, stage, operations, Git history, and pull-request
records.

The [project charter](../markeitech.md) defines product and engineering invariants. The canonical
[Sir Loke v1 product definition](product/sir-loke-v1.md) defines the first useful user experience.
The [delivery blueprint](roadmap/v2-market-events-live-agent-plan.md) defines future sequence.
None of those future documents proves implementation.

## Status At A Glance

| Area | Current state |
|---|---|
| Product runtime | Active V2 source at repository root, built on NautilusTrader `2.0.0rc4` |
| First visible product | Sir Loke v1 is accepted product direction but unimplemented |
| Provider | Interactive Brokers paper connection through TWS/IB Gateway for market data only |
| Active tracked profile | One-instrument V3 ES operational/historical probe profile |
| Trade observation | Unimplemented; no execution client, account/order/fill/position owner, or trade lifecycle |
| Discord | Outbound webhook health projection exists; inbound conversational bot does not |
| Agent/model | Unimplemented; no live model, Sir Loke read model, conversation state, or agent tools |
| Execution | Absent; no submit, modify, cancel, replace, or close path |
| Persistence | PostgreSQL operational audit and compact evidence-recency profiles; no raw market-data store |
| Current implementation focus | Product direction has moved to the shortest honest Sir Loke v1 path; each code batch still needs focused approval |

## Current Offline Verification

On 2026-09-05, while preparing the documentation authority reset against the implementation
baseline above:

- `uv run --locked --offline ruff check src tests scripts/sir-kite-pr.py` passed;
- the focused V3 profile contract passed `2/2` tests;
- the full non-PostgreSQL suite passed `649` tests with `2` PostgreSQL-marked tests deselected;
- every local Markdown link target in current docs/plugin references resolved; and
- `git diff --check` was clean.

This verifies the offline code baseline and documentation consistency only. It does not establish
PostgreSQL integration, provider behavior, a connected rc4 run, broker observation, Discord bot,
model, Sir Loke, options, or live-money acceptance.

## Operating Posture

- Markeitech is live-first, event-driven, local, advisory, and currently read-only.
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

## Active Tracked V3 Profile

[`config/system.v3-es-minimal.toml`](../config/system.v3-es-minimal.toml) is the narrow progressive
profile used by the most recent V3 acceptance work. Its actor plan contains exactly:

1. `SystemControlActor`;
2. `SessionStateActor`;
3. `EvidenceHealthActor`;
4. `HistoricalEvidencePlannerActor`;
5. `WatchlistActor`;
6. `DataAcquisitionActor`;
7. the temporary `CurrentStateHistoricalProbeActor`; and
8. `OperationalPersistenceActor`.

The profile is limited to `ESU6.CME`, the `cme_equity` calendar, a `watchlist_last` bar capability,
and a temporary five-observation current-state-gated historical probe. It does not compose a
completed-bar foundation, metric owner, entity owner, semantic event detector, options owner,
Discord actor, runtime-resource actor, broker-observation owner, trade lifecycle, or Sir Loke.

The profile contains disabled configuration sections retained for schema compatibility and review
history. Values in disabled sections are not active analytical defaults or accepted product
behavior.

## Implemented Foundation

### Runtime and provider boundary

- The package and lockfile pin NautilusTrader `2.0.0rc4`; the upgrade was merged through PR 17.
- `LiveNode` construction, caller-owned embedded lifecycle tests, guarded production startup,
  controlled shutdown, rotating logs, and explicit IB connection confirmation exist.
- NautilusTrader owns IB market-data connectivity and native normalized observations.
- `DataAcquisitionActor` owns logical provider demand and subscription/request lifetime.
- Static watchlist ownership and native multi-consumer market-data delivery were accepted in the
  predecessor V2 profile.
- Provider-subscription recovery, full connection-loss recovery, and several pacing/cancellation
  semantics remain documented reliability debt.

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

See [session and evidence health](architecture/v2-session-evidence-health.md) and
[historical dependency execution](architecture/v2-historical-dependency-execution.md).

### Measurements, entities, and V3 replacement work

Substantial deterministic measurement and entity code exists, but active and historical surfaces
must not be conflated:

- Earlier Stage 9C profiles implemented and connected-tested completed-bar, session-reference,
  analytical-window, and rolling numerical measurements.
- Earlier Stage 9D work implemented pure entity/state contracts and owners for session references,
  volatility state, confirmed swings, pivot relationships, FVGs, and derived zones. Some optional
  actor paths received bounded connected acceptance.
- V3-02 disabled the combined `SessionMetricsActor`, dependent Entity Analysis, and Visual Debug
  in both tracked runtime profiles because those responsibilities require replacement and an
  atomic wire cutover.
- V3-03 Slice 1 is merged at `4631df5` and supplies inactive v2 completed-bar/metric contracts,
  validation, admission, and producer-manifest foundations.
- V3-03 Slice 2 is merged through `e8f49e3` and supplies a private disabled multi-series
  completed-bar foundation plus deterministic fixtures. It is not composed or connected-accepted.
- V3-03 Slices 3–9 are unimplemented. The separate rc4 prerequisite is already merged, so the old
  “awaiting rc4 PR” resume text is stale. Any resumed V3-03 work needs a newly approved batch and
  must be reconciled with the accepted Sir Loke v1 delivery priority.

The detailed replacement boundary remains in the
[V3-03 plan](roadmap/v3-03-session-metrics-actor-split-implementation-plan.md). Passing tests for
inactive owners do not make them current live outputs.

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

`DiscordHealthActor` is an optional outbound webhook projection for system-health and operational
messages. It has bounded delivery work and failure isolation, but it does not:

- connect through the Discord Gateway as a bot;
- receive messages;
- authenticate Markeitect as the allowed conversational user;
- maintain conversation state;
- route questions or commands to an agent; or
- provide Sir Loke recommendations, mentoring, trade monitoring, or reports.

Enabling the webhook actor cannot turn it into Sir Loke.

### Documentation tooling

- The offline system-diagram utility statically reconciles the canonical architecture TOML and
  generates the tracked diagram set. Generated diagrams describe their recorded manifest and
  checkout, not automatically the current runtime.
- The isolated API-documentation utility statically validates the versioned public surface and
  generates tracked `docs/api` output. Its GitHub Pages workflow is current at this baseline.
- Neither documentation tool imports the runtime, connects services, or proves live behavior.

## Sir Loke V1 Gap

The product direction is accepted; the implementation is not present.

| Required first-version capability | Current evidence | Status |
|---|---|---|
| Live private two-way Discord conversation | Outbound webhooks only | **Absent** |
| Model-backed Sir Loke reasoning | No model provider, invocation, structured output, or read model | **Absent** |
| Evidence-cited recommendations and abstention | Deterministic foundations exist; no recommendation owner | **Absent** |
| SPXW and QQQ 0DTE contract discovery/quality | Future design intent only | **Absent** |
| Broker account/order/fill/position observation | IB data client only | **Absent** |
| Detection of manually entered TWS trades | No observation path; native behavior unproven | **Absent / unknown provider behavior** |
| Recommendation-to-execution attribution | No trade episode or linkage contract | **Absent** |
| Open-trade thesis monitoring | No canonical trade plan, thesis, invalidation, or position join | **Absent** |
| Firm policy-controlled mentoring/governance | No intervention, acknowledgement, noncompliance, or cooldown owner | **Absent** |
| After-trade report | Operational audit only; no product report contract | **Absent** |
| Order actions | No execution client or order command | **Intentionally absent in v1** |

## Broker Observation Status

The first planned connected acceptance uses an Interactive Brokers paper account through TWS.
Sir Loke's behavior is intended to be the same for paper and live observations, while every broker
fact retains account identity and environment.

NautilusTrader `2.0.0rc4` exposes an Interactive Brokers execution client, live execution-engine
reconciliation, cache access to accounts/orders/positions, typed strategy callbacks, and native
reports. Markeitech has not configured or accepted those facilities. Exact delivery of manually
entered TWS orders under a safe client-ID and read-only configuration remains unknown.

No connected order-observation probe has run. No order has been placed, modified, canceled,
replaced, or closed by Markeitech. The first observation design must prove the native path before
considering custom IB access and must expose no order action to Sir Loke.

See the [Sir Loke v1 product definition](product/sir-loke-v1.md#broker-observation) and
[IB setup boundary](operations/ib-setup.md).

## Connected Acceptance Envelope

Recorded connected acceptance is useful but narrow:

- Earlier V2 profiles established bounded IB paper market-data subscription, historical request,
  multi-consumer delivery, operational persistence, Discord webhook, resource, measurement, and
  selected entity-projection behavior under the exact recorded sessions and configurations.
- V3-01 accepted the canonical `cme_equity` calendar path for one tracked ES profile and one
  bounded lookback/lookahead envelope.
- V3-02 accepted one late-consumer current-state recovery and five-bar historical request chain.
- Existing connected evidence predates the rc4 upgrade unless a record explicitly says otherwise;
  the rc4 upgrade itself was offline-verified.
- No connected acceptance establishes SPXW/QQQ options acquisition, a Discord bot, a live model,
  Sir Loke advice, account observation, manual TWS trade detection, trade monitoring, or live-money
  behavior.

A connected process start is not end-to-end Sir Loke readiness. Passing one paper session cannot
be generalized across accounts, products, sessions, provider conditions, or live money.

## Current Validation Debt And Stop Gates

- Provider subscription failure and connection-loss recovery are not accepted end to end.
- The V3 completed-bar and metric replacement has not reached composition, cold cutover, legacy
  retirement, or connected acceptance.
- Manual TWS order visibility, external-order claiming/binding, and read-only API behavior require
  a bounded observation-only paper proof.
- Canonical trade episode, recommendation linkage, intervention, conversation, and report schemas
  are undecided.
- Minimum sufficient SPXW/QQQ option, liquidity, expiration, settlement, and reference evidence is
  unimplemented.
- Agent provider/model, cost, context, output validation, prompt/security, and outage behavior are
  undecided.
- Discord bot authentication, intents, allowlist, reconnection, rate limits, and secret boundary
  are undecided.
- Persistence admission, retention, redaction, recovery, and audit reconstruction for broker,
  conversation, agent, and trade records require explicit schema review.
- No order-execution work may begin under the Sir Loke v1 authority.

## Next Product Sequence

After this documentation authority reset is reviewed and merged, the accepted high-level path is:

1. prove the native IB/TWS read-only observation boundary offline and through one separately
   authorized paper-account probe;
2. define canonical trade-episode, recommendation-linkage, advisory-policy, and audit contracts;
3. implement an authenticated, failure-isolated two-way Discord bot transport;
4. complete the minimum honest market/options evidence corridor for SPXW and QQQ 0DTE;
5. implement Sir Loke's bounded read model, reasoning, recommendations, abstention, monitoring,
   mentoring, and reports;
6. integrate the paths without adding an order-action surface; and
7. run the complete paper-through-TWS acceptance story.

This sequence establishes direction, not blanket implementation approval. Each consequential
architecture, configuration, schema, dependency, connected run, and implementation batch still
uses its focused review and PR.

The detailed gates and reuse mapping are maintained in the
[canonical delivery blueprint](roadmap/v2-market-events-live-agent-plan.md).

## Historical Detail

The active tree intentionally does not repeat every former stage log here. Use:

- [V2 infrastructure foundation](roadmap/v2-infrastructure-plan.md) for completed early-runtime
  gates;
- [Stage 9C session measurements](roadmap/v2-stage-9c-session-measurements-plan.md) for the
  predecessor measurement implementation and connected evidence;
- [Stage 9D entities and rolling state](roadmap/v2-stage-9d-entities-rolling-state-plan.md) for
  entity/state design and bounded acceptance;
- [V3-01/V3-02 architecture](architecture/v2-session-evidence-health.md) and the
  [V3-02 plan](roadmap/v3-02-session-state-actor-implementation-plan.md) for current calendar-state
  delivery;
- the [V3-03 replacement plan](roadmap/v3-03-session-metrics-actor-split-implementation-plan.md)
  for incomplete cutover work; and
- Git and pull-request history for exact implementation chronology.

Historical claims retain only their recorded contract, version, configuration, provider, session,
and acceptance envelope. They do not become current implementation merely because this status page
links to them.
