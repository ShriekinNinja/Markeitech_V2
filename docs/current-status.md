# Current Status

Last reviewed: 2026-09-02

This page is the source of truth for current implementation progress. Markeitech V2 is the sole
active system. Retired source remains recoverable through Git history but does not define current
behavior.

## Operating Posture

- V2 is a clean runtime foundation on NautilusTrader `2.0.0rc3`.
- Interactive Brokers paper trading is the current provider connection.
- The system provides observation and decision support only; automated execution is absent.
- Components communicate through approved Nautilus actor facilities.
- Each actor owns one responsibility and consumers do not redefine source facts.
- Previous analytics, indicators, levels, signals, models, and trading assumptions are not active
  V2 requirements.
- Markeitect approves architecture decisions before implementation proceeds.

## Current Snapshot

- The V1 retirement PR is merged, and the active V2 Python project has been promoted from the
  former nested `v2/` directory to the repository root. Source, tests, configuration templates,
  Compose, package metadata, the lockfile, CI, operations commands, and static documentation tools
  now share that root. The `markeitech-v2` distribution name and all product/runtime semantics are
  unchanged. Ignored secrets, local configuration, data, IDE state, and pre-existing virtual
  environments remain outside the tracked migration and require deliberate operator selection.
- The active audit-and-alignment branch upgrades NautilusTrader from `2.0.0rc1` to `2.0.0rc3`.
  RC3 removed the generic Python network helpers and embedded `LiveNode.start()` lifecycle used by
  Markeitech's Discord transport and integration-test harness. Discord now uses one isolated
  standard-library HTTPS boundary, while embedded node tests use the public caller-owned
  `run_async()` and `LiveNodeHandle` lifecycle. Production remains on hosted `LiveNode.run()`.
  The migration passes all 409 offline tests. Markeitect's operator-owned connected run on
  2026-08-25 confirmed RC3 startup and controlled shutdown, complete operational persistence
  reconciliation, and successful Discord lifecycle delivery through the replacement transport.
- Stages 1 through 9C and the runtime-resource hardening gate are implemented and connected-
  accepted within the evidence recorded below.
- Stage 9D is active. Slices 9D.1 through 9D.5C are approved and committed. The market-structure
  runtime portion of Slice 9D.5D is implemented. Together they provide typed
  analytical entity contracts, a bounded state book, a configuration-owned entity catalog,
  deterministic numerical prerequisites, pure rolling market-state projection, an optional
  `MarketStateEntityActor` runtime boundary, pure confirmed-swing entity projection, and pure
  per-horizon swing-leg and pivot-structure relationship projection.
- Stage 9D.3 still carries narrow opening-range developing-to-complete acceptance debt. Markeitect
  explicitly deferred that window-boundary proof until a run crosses the configured boundary; it
  does not block 9D.5. Stage 9D.4C connected acceptance closed on 2026-08-24 against liquid
  London/ETH futures data with its optional runtime projection enabled.
- The accepted run projected 645 rolling metrics into 645 valid market-state revisions with zero
  conflicts, rejections, deferrals, or projection failures. Its staleness timer completed 2,560
  reconciliation cycles without observing evidence old enough to require a stale revision.
  Session metrics produced 64,064 rolling values with zero calculation failures; resources stayed
  bounded; PostgreSQL stored all 2,261 accepted operational events; Discord delivered 4/4 health
  messages; and shutdown was clean. The acceptance configuration declares `STALE` and
  `UNAVAILABLE` as valid volatility-entity health outcomes, correcting the earlier actor-
  construction rejection without changing classification policy. Stage 9D.5A now projects only
  fully confirmed strict pivots with detector/horizon identity, contiguous completed-bar lineage,
  bounded evidence and entity retention, and no market interpretation. Stage 9D.5B now relates
  compatible alternating pivots through exact endpoint revisions and owns explicit price,
  percentage, time, bar-count, slope, optional path/volume, and optional volatility-normalized
  evidence. Its revisable per-horizon structure preserves same-kind comparisons, bounds,
  leg-scale relationships, superseded/unresolved pivots, and conflicts without rewriting confirmed
  swings or producing a trend score. The three numerical relationship thresholds carry explicit
  versioned floors, ceilings, steps, and dynamic eligibility. Stage 9D.5C now adds pure bounded
  FVG lifecycle and constituent-preserving zone projection. FVGs retain independent formation
  identity, exact completed-bar lineage, fill state, remaining interval, optional normalization,
  and configurable complete/invalidate/expire outcomes. Zones preserve exact source revisions and
  deterministic horizon, distance, padding, width, constituent-count, age, partition, weighting,
  and retention policy without support/resistance or trading meaning. The new optional
  `MarketStructureEntityActor` receives only accepted completed bars through typed Nautilus custom
  data. Rolling calculation exposes its exact accepted one-, five-, and fifteen-minute completed
  inputs, and `SessionMetricActor` publishes newly accepted derived bars without changing their
  source lineage. The structure actor resolves every application against one explicit named set,
  and coordinates the reviewed confirmed-swing, pivot-relationship, FVG, and derived-zone owners.
  Changed revisions are published as typed entity data and logged with instrument, type, lifecycle,
  revision, and entity identity. Consumers may request immutable snapshots filtered by instrument,
  entity type, analytical profile, and lifecycle. Projection failures are isolated per owner and
  reconciled through bounded runtime counters. The tracked acceptance catalog now declares five
  explicit 5-minute market-structure contracts; its numerical values are offline fixtures, not
  trading calibration. Offline actor evidence proves completed-bar transport, all five entity
  revision types, local fan-out, exact parameter-set selection, rejection of unavailable sets and
  incomplete or scope-incompatible companion definitions, and filtered snapshots. Owner invariant
  failures remain isolated to the affected projection and are counted rather than escaping the
  Nautilus callback. The rejected `VisualAcceptanceActor` and `LiveEvidenceReviewActor` were
  subsequently retired from runtime composition, typed configuration, source, and tests. Their
  exclusive Kaleido and Pillow dependencies were also removed. Configuration schema 21 no longer
  accepts either dead section. The progressive `VisualDebugCaptureActor` remains a separate,
  passive observer and was not changed by that removal. Historical ignored artifacts and local
  configurations remain outside Git as recovery evidence; they are not runnable current profiles.
- The approved V3 canonical-calendar cutover is implemented and connected-accepted for the exact
  tracked V3 ES profile.
  `SessionStateActor` is the sole mcal-backed evaluator owner, publishes typed transitions
  and bounded immutable projections, and has no shadow/legacy counterpart. A separate historical
  planner turns symbolic evidence needs into exact UTC plans; acquisition executes those plans and
  retains provider limits without interpreting sessions. At V3-01 closure, system schema 21 and
  calendar-catalog schema 3/catalog version 4 configured five reusable calendar identities without
  concrete instrument contracts.
  The runtime watchlist alone binds admitted instruments to calendars. CME/CBOT definitions carry
  overlapping `GLOBEX`, `ASIA`, `LONDON`, and `NEW_YORK` product phases, deterministic lineage,
  and one source-cited CME equity-hours correction. The full disconnected suite passes. The first
  connected acceptance run on 2026-08-30 was rejected before historical planning because pinned
  mcal represents several CME early closes with `break_start == break_end == market_close`; the
  projector attempted zero-duration exchange segments and consumers retried without a bounded
  failure response. The committed repair normalizes only that exact terminal provider
  representation after source-cited corrections, records an immutable normalization outcome,
  emits per-calendar response-v2 failures for ordinary projection exceptions, and gives each of
  the three consumers one correlated, bounded, one-shot retry lifecycle. CME/CBOT definition
  versions are now 4. Offline verification passes. Markeitect accepted the repaired 2026-08-31
  connected run using the tracked schema-21 V3 ES profile and catalog version 4: the canonical
  owner served five projection requests with zero rejection or construction failure; all three
  consumers completed with zero projection timeout or terminal outcome; the planner produced one
  exact plan with no deferral or rejection; IB returned 60/60 requested bars; persistence
  reconciled 36/36 accepted records; and shutdown was clean. This acceptance is bounded to
  `cme_equity`, the configured 120-day lookback/14-day lookahead, one historical request and
  attempt, and the observed current session. It does not accept multi-calendar live behavior,
  phase-boundary delivery, late-consumer recovery, connected retry/failure paths, concurrent
  historical callbacks, or cancellation with provider work in flight. The broader metric-actor
  split remains deferred.
- V3-02 current-state delivery is implemented and committed on
  `v3-02-session-state-snapshot-plan`. System schema 23 retains one statically composed
  `SessionStateActor` per runtime run UUID and adds strict transition-v2 plus current-state
  snapshot-v1 contracts. The producer evaluates every requested calendar at one owner-clock cut
  while preserving the exact state-effective boundary separately from evaluated-as-of and
  publication time. `EvidenceHealthActor` and `HistoricalEvidencePlannerActor` now use one bounded
  subscribe-buffer-snapshot-reconcile protocol with explicit definition, source/run, revision,
  duplicate, stale, gap, conflict, overflow, timeout, retry, failure-isolation, and terminal-stop
  behavior. `OperationalPersistenceActor` remains a transition-only audit sink; snapshots,
  watermarks, retry state, buffers, projections, and raw schedules remain transient.
  `SessionMetricsActor`, Session-Metrics-dependent Entity Analysis, and Visual Debug remain present
  as dormant code or review material but are disabled and ignored in both tracked runtime profiles
  pending the separately reviewed Session Metrics replacement. Markeitect explicitly retained the
  temporary `CURRENT-STATE-HISTORICAL-PROBE` in the tracked V3 ES profile for additional bounded
  live checks. It owns no provider API, persistence, analytical output, or production capability.
  In the accepted 2026-08-31 connected run, the probe deliberately omitted snapshot attempt 1,
  recovered on attempt 2, observed `GLOBEX+NEW_YORK`, and caused the existing planner to resolve
  five completed one-minute bars from `13:51:00Z` through `13:55:59.999999999Z`. Acquisition
  submitted one IB request, accepted and delivered `5/5` bars, published `READY`, reported zero
  historical degradation and late callbacks, and shut down cleanly. Session State rejected no
  snapshot request; persistence stored `31/31` accepted operational facts. One non-terminal
  planner projection timeout was observed during startup before successful recovery. This single
  run accepts only the exact late-consumer recovery and historical-request chain; it does not
  establish multi-calendar behavior, phase-boundary delivery, repeated provider reliability,
  performance, value parity, or general market-session correctness.
- V3-03 Slice 1 is merged at `4631df5`. It supplies the public immutable completed-bar and
  MetricValue v2 contracts plus private pure validation, admission, producer-manifest, readiness,
  and legacy-compatibility helpers. Its contract checks cover exact wire shapes and primitive
  types, canonical decimal strings, complete subject dependencies, exact missing-slot geometry,
  bounded historical requests and producer claims, and revision-chain
  duplicate/conflict/stale/gap handling. Existing enabled MetricValue publishers and consumers
  remain together on one private legacy v1 wire until a later atomic v2 cutover; there is no dual
  publication.
- V3-03 Slice 2 is approved and committed at `eb3995b`, then merged into the stage branch at
  `e8f49e3`. It corrects canonical completed-bar
  identity by keeping provider/adapter/source-path dimensions in the new public
  `CompletedBarInputIdentity` carried by each lineage entry, not in
  `CompletedBarSeriesIdentity`. It adds a private, disabled multi-series foundation actor and
  configuration/state model for the exact ES five-second-live to one-minute-canonical path,
  independently gated per-series readiness using the foundation receipt clock, the versioned
  bounded close-grace policy, owned and correlated projection/current-state request cycles,
  bounded calendar timeout/retry and transition-gap reconciliation, canonical-bootstrap
  history/live convergence, exact five-second slot admission, atomic publication, final
  complete/partial/empty outcomes, bounded admission, and exact metadata routing. Parsed native
  `BarType` values and the live subscription client bind configured route identity. An immutable
  authority snapshot taken from the actual historical execution port now fails provider, adapter,
  stream, or schema contradictions before foundation actor construction or demand and remains the
  source identity carried by each batch. A transition received while a projection request is
  waiting no longer republishes that request; its refresh intent starts exactly one new correlated
  generation after completion. The production lifecycle fixture now uses pinned-rc3
  `Clock.new_test`, native `Bar` values through `on_bar`, and the actual deterministic cutoff
  callback, including exact-cutoff admission checks on both sides of timer firing.
  No actor is composed or enabled; no tracked profile, provider request/subscription behavior, or
  demand implementation has changed; the existing historical execution port now exposes its
  read-only source identity on each transient batch. No connected acceptance is claimed. Evidence
  for this slice remains disconnected only: the 105-test focused correction set,
  including 88 intelligence-contract tests, and all 616 non-PostgreSQL V2 tests pass. The full V2
  Ruff gate is clean, all 31 API-documentation utility tests pass, and the locked API-documentation
  validator selects and documents all 261 registered entries with no missing docstrings.
- PostgreSQL currently stores runtime runs, system-health events, generic operational events, and
  compact evidence-recency profiles. Raw provider observations and transient numerical metric
  values remain outside PostgreSQL.
- The 18-member configuration-owned static watchlist is live-accepted. Dynamic membership remains
  explicitly deferred.
- Semantic interaction events, the bounded options proof, cross-instrument state, richer analytics,
  Sir Loke, opportunity lifecycle, ML evaluation, replay, backtesting, and execution remain future
  work.
- A separate offline documentation utility now validates one versioned TOML architecture manifest,
  reconciles its supported actor/contract/profile anchors against repository source, and generates
  six tracked SVG/PNG/DOT/Markdown views plus an artifact index and hashes. It is not imported or
  composed by V2, reads no runtime state or secrets, and changes no runtime behavior. The shared
  PyCharm **Generate Sys Diagram** configuration runs only this locked documentation environment.
- The pre-retirement system-diagram census debt is resolved without changing the active metric
  wire identity: `METRIC_VALUE_TYPE_NAME` now declares the same `markeitech.metric.value` value as
  a literal string, as required by static architecture reconciliation. Root-promotion validation
  includes the complete locked diagram-tool test, generation, and drift-check boundary.
- A separate locked API-documentation utility now statically analyzes the curated V2 Python public
  surface and produces an untracked MkDocs site at `docs/api` plus sanitized metadata and artifact
  indexes. Its
  versioned denominator currently selects 260 package exports plus one explicit operator entry
  point, 261 objects in total; all 261 selected objects have source docstrings and none are
  reported as missing. Static analysis and rendering deny target imports, dynamic
  inspection, external inventories, network access, and child processes; the wrapper first uses
  bounded read-only Git queries for source identity. It verifies source stability and publishes
  complete artifact sets atomically. Attribute-registry version 2 approves five bounded
  `architecture.component.*` fields for implementation-backed class documentation.
  Caller/callee and architecture-flow examples remain unapproved future discovery
  concepts rather than inferred runtime semantics. The first architecture-component docstrings are
  seeded for all 20 exact implementation-referenced records in the current system/data-flow TOML.
  Seven substantive responsibility sets are preserved exactly; 13 generic placeholders remain
  explicit documentation debt rather than being promoted as meaningful responsibilities. The
  API-doc build then reads source declarations only. The existing system-diagram tool still
  consumes the TOML during this migration interval; the future source-to-TOML/diagram exporter is
  not implemented or accepted yet. The generated local site uses a full-width dark presentation
  with contained horizontal scrolling for wide tables and signatures.
- The repository-owned Kite plugin defines a 20-role advisor council for development-time
  engineering consultation, not V2 runtime implementation or Sir Loke behavior. Kite
  `0.1.0+codex.20260829091645` is installed and enabled from the local `markeitech` marketplace;
  its installed cache matched the cache-busted repository source byte-for-byte. This build adds
  one canonical council policy, bounded
  selection with deterministic selected-role dependency execution, explicit-only Kite activation
  and specialist skills, explicit advisor denial of the project PyCharm MCP, and a dependency-free
  structural validator. A fresh or unrelated Codex task remains normal Codex; explicitly invoking
  Kite activates its router for that task and direct follow-ups, after which Kite uses the smallest
  sufficient advisor set by default. One ordinary governance selection was observed on older build
  `...124814`, but its
  delegated execution failed. Architecture, governance, and security roles returned consultations
  during the 2026-08-26 Phase 1 review, but that was not a clean routing fixture; the security role
  was presented a workspace-write parent permission surface despite its read-only default.
  Therefore read-only is a mandatory consultation contract and custom-agent default, not an
  accepted runtime isolation boundary. Fresh-task dormancy, explicit activation, task-scoped
  continuity/reset, end-to-end order and stop behavior, isolation, redaction, failure, and
  revocation acceptance remain pending. Policy version `2026-08-29-v3` fixes the eight advisors
  selected for the desired-runtime gap review at `gpt-5.6-sol` with `xhigh` reasoning; the other
  twelve role settings are unchanged. Source validation, 20 focused validator tests, generic
  plugin validation, installation, and source-to-cache comparison pass. A fresh task exposed all
  eight exact role settings and completed the approved read-only desired-runtime consultations.
  Their [desired-runtime report](notes/desired-arch-council-review-report.md) is an informative
  council discovery record and proposal source; it is not accepted architecture, a roadmap, an
  authoritative debt ledger, or implementation approval. General council acceptance remains
  pending as described above.

The remainder of this page is the chronological implementation record supporting this snapshot.
When an older section describes a former review state, the snapshot above governs current status;
the older wording is retained only as implementation history.

## Chronological Implementation Record

### Live-Accepted Foundation

- Isolated V2 Python project, configuration, environment, dependencies, and runtime logs.
- One PyCharm **Markeitech V2** run configuration with macOS caffeination.
- Nautilus `LiveNode` construction and clean shutdown.
- Interactive Brokers connection through TWS paper trading.
- Configured ES and SPY instrument-definition resolution.
- Versioned system-health signal contract.
- `SystemControlActor` with honest `STARTING`, `READY`, `FAILED`, and `STOPPING` ownership.
- Read-only Discord projection of system-health transitions and one-shot startup operational
  readiness from existing watchlist and historical evidence.
- Discord failure isolation and bounded worker shutdown.

## Stage 4: Operational Persistence

Implementation is complete for review on branch `v2-stage-4-persistence-boundary`:

- PostgreSQL is the accepted operational source of truth.
- Docker Compose owns the local PostgreSQL service and persistent volume.
- The existing PyCharm run configuration starts PostgreSQL and waits for health before Markeitech.
- Versioned migrations run under a PostgreSQL advisory lock before IB startup.
- Every runtime receives a UUID run record.
- `OperationalPersistenceActor` is the sole writer while Nautilus runs.
- System-health events are stored in order with database-enforced idempotency.
- `READY` requires both instrument definitions and operational persistence readiness.
- Mid-run persistence failure produces the first approved `DEGRADED` transition.
- `STOPPING` remains actor-owned; the CLI records `STOPPED` only after `LiveNode.run()` returns
  cleanly.
- A crash, forced kill, or failed terminal write intentionally leaves an incomplete run.
- Restart reads, duplicate handling, migrations, and clean closure pass against real PostgreSQL.

Stage 4 is committed and live-accepted.

## Stage 5: Actor Composition

Implementation is approved and committed on branch `v2-stage-5-actor-composition`:

- A pure actor plan owns the complete static runtime topology.
- System control and operational persistence are mandatory core actors.
- Discord is explicitly enabled or disabled in typed configuration.
- Enabled Discord requires its system-health and operational-events webhooks before IB startup;
  later delivery failure remains isolated.
- Actor and config import paths are code-owned rather than supplied through TOML.
- Immutable startup prerequisites replace the transient persistence-ready signal.
- Runtime persistence failure remains a separate fact; only system control may transition the
  system to `FAILED` or `DEGRADED`.
- Dynamic plugins, actor removal, and generic readiness infrastructure remain deferred.

Stage 5 is committed and live-accepted.

## Stage 6: Supervision And Failure Policy

Implementation is approved and live-accepted on branch `v2-stage-6-supervision-policy`:

- Component failures use one versioned internal signal contract.
- Workers return sanitized results to their owning actors and never decide global health.
- System control remains the sole owner of global `DEGRADED` and `FAILED` transitions.
- PostgreSQL health-event writes use configured bounded attempts and backoff.
- Exhausted PostgreSQL writes, queue rejection, and shutdown timeout report one structured
  component failure without retaining unbounded work.
- Discord remains optional and best effort; delivery failure never changes global health.
- Persistence, Discord, and system control emit bounded lifetime counters at shutdown.
- Both workers stop accepting work, drain accepted FIFO work within their timeout, and allow a
  later cleanup attempt to finish after an initial timeout.
- Recovery from `DEGRADED` to `READY` remains deliberately deferred until durable recovery
  evidence is defined.

Stage 6 is committed and live-accepted.

## Stage 7: Provider And Canonical Data Boundary

Implementation is approved and committed on branch `v2-stage-7-provider-data-boundary`:

- Native Nautilus instruments and market-data objects remain the runtime transport contracts.
- IB symbology, MIC conversion, quote batching, size-only quote updates, and revised-bar behavior
  are explicit V2 configuration.
- Provider context and request policy remain separate from high-volume native observations.
- Native instrument identity, source fidelity, and timestamps are not rewritten.
- Markeitech-owned market-data contracts remain possible later when a concrete requirement cannot
  be represented safely by native types and acquisition context.
- Preservation means honest live transit, not durable raw market-data retention.

Stage 7 is committed and offline-verified.

## Stage 8: Data Acquisition Ownership

Stage 8A is implemented for review on branch `v2-stage-8-acquisition-ownership`:

- `DataAcquisitionActor` is a mandatory core actor and the sole owner of provider-facing
  instrument-definition requests.
- It discovers definitions already present in the Nautilus cache and requests each missing
  configured definition once.
- A versioned acquisition status reports expected, available, and missing definitions.
- `SystemControlActor` consumes acquisition status and remains the sole owner of global readiness.
- A publish-on-start and post-start request handshake avoids depending on actor registration order.
- This slice adds no live subscriptions, historical bars, persistence, pacing policy, recovery,
  analytics, or trading behavior.

Stage 8A passes offline contract, ownership, deduplication, composition, state-transition, and
Nautilus bus-delivery tests. Live review remains pending.

Stage 8B's architecture direction is approved. It replaces the fixed active/background model
with four independent concepts: trade universe, dynamic observation universe, active analytical
capabilities, and temporary focus. The target is a broad continuous native market-data plane
feeding deterministic analysis and semantic state, with a later advisory agent directing
attention through policy-checked intents. No Stage 8B runtime behavior has been implemented.

Stages 8B.1 through 8B.3 were completed before the Stage 8C connected proof:

- reusable analytical capability requirements and instrument-bound feed demand;
- explicit demand ownership, priority, optional expiry, and lifecycle vocabulary;
- pure multi-consumer provider-demand reconciliation;
- one provider-neutral coordinator owning subscribe and unsubscribe lifetime;
- one subscribe for shared demand and one unsubscribe only after the final consumer leaves;
- retryable provider failures which are never reported as active;
- native Nautilus translation for simple instrument, quote, trade, bar, status, and option-Greek
  subscriptions; and
- explicit deferral of richer book and option-chain subscription contracts.

The installed compiled Nautilus core did not expose enough subscription reference-count state for
an honest offline proof of duplicate-actor behavior, so Stage 8C completed that proof against a
live IB connection.

Stage 8C is complete on branch
`v2-stage-8c-continuous-native-stream`:

- standalone configuration schema 3 explicitly declares bootstrap native feeds and the bounded
  probe controls;
- the proof profile requests quotes and trades for configured ES and SPY;
- no feed is inferred merely from observation-universe membership;
- `DataAcquisitionActor` starts streams only after instrument-definition readiness;
- lifecycle facts distinguish `REQUESTED`, `ACCEPTED`, `SUBSCRIBED`, and first-observed `ACTIVE`;
- each demand remains correlated through its stable demand ID;
- raw observations remain native, transient, unwrapped, and unpersisted; and
- shutdown cancels each bootstrap demand while the coordinator protects shared subscriptions.

The live proof registered a temporary `NativeConsumerProbeActor` for those same native quote and
trade streams. Both actors received all four streams. Eight actor-level subscribe commands became
four provider subscriptions. The probe then unsubscribed after 15 seconds with 72 observations,
while `DataAcquisitionActor` continued to 464 observations before shutdown. Provider
unsubscription occurred only during final shutdown. This proves native multi-actor delivery,
provider deduplication, and subscription lifetime safety for this path.

The diagnostic probe remains available behind explicit configuration but is disabled in the normal
runtime profile. It adds no custom market-data envelope, fan-out, persistence, analytics, or
fallback implementation. Offline tests cover configuration, composition, logical deduplication,
lifecycle meaning, first observation, cancellation, retry, and native call mapping.

The subsequent scalable-watchlist POC registered a core `WatchlistActor` for eight instruments.
IB delivered native best-bid/ask updates and external five-second bars to the actor while
`DataAcquisitionActor` anchored the shared provider subscriptions. Broad tick-by-tick `AllLast`
requests reached IB limit `10190`, so tick trades remain a focus-only capability rather than a
baseline watchlist feed. The accepted POC retains bounded readiness transitions and shutdown
summaries; temporary per-update logs were removed after live review.

The actor is now a bounded core state owner with immutable versioned snapshots, native event
timestamps, separate registration and observation state, and out-of-order protection. Versioned
membership and lifecycle contracts are published and persisted through the generic PostgreSQL
audit boundary.
Dynamic membership is explicitly deferred; the accepted stopping point is a live-proven static,
configuration-owned watchlist. The exact handoff is
[`roadmap/v2-static-watchlist-handoff.md`](roadmap/v2-static-watchlist-handoff.md).

The generic PostgreSQL operational ledger and store boundary are implemented. Current acquisition
control events plus static watchlist membership and lifecycle events are wired through the same
ordered bounded persistence worker. A versioned request/ready handshake now gates system control,
data acquisition, and watchlist startup until the in-node persistence worker is subscribed and
its Nautilus startup callback has returned. This replaces the watchlist's timing-based startup
delay and preserves acquisition
`REQUESTED`, `ACCEPTED`, and `SUBSCRIBED` events before the first `ACTIVE` observation. PostgreSQL
preflight reapplies idempotent schema definitions and verifies required tables and columns. A
dropped applied-migration table is therefore recreated before runtime readiness instead of failing
on its first write. No audit event includes raw quote or bar payloads. The startup-audit closure is
implemented for live review on branch
`v2-stage-8e-startup-audit-closure`.

The configuration-ownership slice replaces the root instrument list with typed static
watchlist members. Each member declares its provider instrument ID, permanent owner IDs, and the
capabilities the current watchlist actually provides. System control, instrument-definition
acquisition, the IB provider, actor composition, and membership audit all consume that one member
set. The subsequent static completion removes duplicated bootstrap feeds: Watchlist
capabilities now publish stable demand contracts, Acquisition alone owns provider subscription
lifetime, and each consumer registers its own native Nautilus handlers during actor startup.
Provider subscription outcomes and local consumer readiness converge independently in either
order. Demand, provider outcome, degradation, recovery, and release are operational audit facts;
raw market observations remain memory-only. Session-unaware elapsed-time staleness is deliberately
deferred.
The complete 18-member baseline is now configured through Nautilus IB simplified `load_ids`, with
required startup resolution and explicit September 2026 ES, NQ, and YM contracts plus the October
2026 CL contract. This mapping is live-accepted; automatic futures rolling is not implied. The
manual procedure is documented in
[`operations/v2-futures-rollover.md`](operations/v2-futures-rollover.md).

## Explicit Boundaries

- PostgreSQL currently contains runtime runs, system-health events, generic operational events,
  and compact evidence-recency profiles. It is the accepted durable audit ledger for future
  meaningful system intents, decisions, lifecycle changes, publications, attempts, and outcomes
  only after their schemas and retention are explicitly approved.
- PostgreSQL does not contain raw ticks, quotes, bars, books, or option-chain payloads. Market-data
  requests, readiness, freshness, gaps, retries, and failures are system events and must be
  audited as their owning components are implemented.
- Ordinary diagnostic logs and individual internal callbacks remain outside PostgreSQL.
- Reconstructable market data will be requested from IB when required by live operation rather
  than retained speculatively.
- Raw market-data persistence, Parquet, replay, and backtesting are outside current scope until
  Markeitect explicitly reopens them.
- Redis, external message streams, dynamic actor composition, semantic interaction events,
  options intelligence, advisory models, and trading models remain unimplemented. Deterministic
  measurements and the approved Stage 9D entity/state foundation are implemented as described
  below.
- Retired implementations are not active and can enter V2 only through a new, explicitly reviewed
  requirement and current contract.

## Next Accepted Sequence

The static watchlist and live acquisition ownership foundation are complete. Dynamic watchlist
membership remains intentionally deferred. Stages 9A through 9C are live-accepted. Stage 9D is
active through connected-accepted Slice 9D.4C. The narrow deferred 9D.3 opening-range boundary
proof remains stated in the current snapshot and does not block 9D.5.

The canonical Stage 9 coding order is:

1. 9A session/calendar ownership and evidence-health truth;
2. 9B historical dependency execution;
3. 9C baseline metric contracts and runtime;
4. 9D entities and rolling state;
5. 9E first semantic events;
6. 9F bounded options-data proof;
7. 9G cross-instrument state;
8. 9H richer analytics;
9. 9I agent read model, policy, and tools;
10. 9J concurrent advisory opportunities; and
11. 9K evaluation and ML readiness.

The agent maintains a plural opportunity set. No instrument is globally preferred, and the
initial SPXW/SPY/QQQ expression universe remains configurable and expandable. All variable market,
analysis, policy, and resource parameters follow the charter's configuration and optimization
principle.

The pre-coding design gate is accepted: opportunities are target-exposure and episode based rather
than source-instrument or contract based, and first-batch parameters are startup-configurable while
carrying explicit future mutability and optimization metadata.

The canonical sequence is maintained in
[`roadmap/v2-market-events-live-agent-plan.md`](roadmap/v2-market-events-live-agent-plan.md); the
first focused implementation sequence remains available in
[`roadmap/v2-first-market-intelligence-coding-sequence.md`](roadmap/v2-first-market-intelligence-coding-sequence.md).

## Stage 9A: Session And Evidence Truth

Stage 9A is complete and accepted at commit `ce9076e`:

- `pandas-market-calendars` supplies local exchange schedules, holiday rules, DST handling, and
  early-close dates.
- Typed startup configuration maps every watchlist member to one of five versioned calendars and
  defines provisional SPXW GTH/RTH/Curb product phases. mcal remains the sole source for CBOE
  holidays and early closes; the catalog carries no duplicated dated holiday overrides.
- `SessionStateActor` owns session/trade-date truth and publishes only initial or changed state.
- `EvidenceHealthActor` consumes acquisition lifecycle facts and independently observes the same
  native Nautilus quote and five-second-bar streams.
- Configured freshness policies distinguish not-yet-evaluated, dormant, healthy, degraded, stale,
  and unavailable evidence without treating a closed market as failed or confusing observation
  age with source fidelity.
- Consumer registration occurs outside nested signal dispatch. Local attachment failures are
  isolated, explicitly unavailable, and retried on configurable cadence; unrelated actors keep
  operating.
- Runtime readiness converges from local registration and acquisition events in either order; it
  does not rely on actor order, sleeps, or a prescribed startup sequence.
- Session and evidence transitions are stored in the existing PostgreSQL operational ledger; raw
  market observations remain memory-only.
- Offline tests cover calendar boundaries, DST, holidays, early closes, freshness transitions,
  strict wire contracts, actor composition, and persistence conversion.

The approved V3 canonical-calendar cutover is implemented and connected-accepted for the exact
tracked V3 ES profile. System
schema 21 loads `config/market-calendars.toml` schema 3/catalog version 4 as one dedicated
startup catalog;
inline definitions, old overrides, and older schemas are rejected. Each system profile selects
its active `calendar_ids`; available but unused definitions are validated without being
instantiated. The loader pins installed `pandas-market-calendars` 5.4.0, provider implementation,
provider-derived exchange timezone, admitted columns, product phases, definition/effective
identity, source-cited structural corrections, and deterministic definition/catalog digests. It
also proves that the configured default projection span and selected calendar count fit their
runtime bounds. The catalog defines CBOE SPXW, NYSE, CME equity, CBOT equity, and product-specific
CL identities, but contains no concrete instrument contracts. The watchlist is the single startup
binding authority: its current bindings include `ES/NQ -> cme_equity`, `YM -> cbot_equity`, and
`CL -> cme_energy`. Futures rollover therefore changes runtime instrument configuration without
changing the reusable calendar catalog.

The inherited 2026 CBOE GTH holiday overrides were removed after direct inspection of pinned mcal
5.4.0 confirmed that it already supplies those holiday closures and the following-day early-close
schedule. Markeitech no longer maintains a duplicated annual holiday list. The
`CBOE_Index_Options` provider does not supply the overnight GTH phase itself; that custom phase
clock remains provisional and explicitly identified as Markeitech-defined.

`SessionStateActor` is the sole runtime owner of exactly one immutable `CanonicalCalendar` per
active calendar ID. It publishes definition-identified typed `CalendarTransition` custom data and
bounded immutable calendar projections. It schedules both periodic reconciliation and the next
known temporal boundary. Consumers never receive or instantiate mcal evaluators: evidence health
uses typed current transitions; session measurements classify bars and resolve analytical windows
from immutable projections; and a separate `HistoricalEvidencePlannerActor` resolves symbolic
historical demand into exact UTC plans. `DataAcquisitionActor` receives only exact plans and retains
provider-facing admission limits, queueing, pacing, retries, cancellation, execution, and lifecycle
ownership. The old `SessionCalendar`, legacy `SessionStateEvent`, shadow comparison, and local
calendar fallbacks are removed. Calendar transitions continue through the existing bounded
operational-event persistence path; projections and raw schedules are not persisted.

The installed mcal CME equity calendars still expose an obsolete regular 15:15-15:30
America/Chicago pause. One source-identified, effective-dated structural correction removes that
pause for ES, NQ, and YM from trade date 2021-06-28. Pre-effective rows remain unchanged; exact
provider matches are recorded as `APPLIED`, already-correct base rows as
`BASE_ALREADY_CONFORMS`, and unequal provider changes fail as `CONFLICT`. Product `GLOBEX` phase
membership remains distinct from exchange `OPEN/BREAK/CLOSED` state. The CME/CBOT definitions also
declare overlapping, DST-aware `ASIA`, `LONDON`, and `NEW_YORK` phases. These are descriptive
product phases, not analytical windows; analytical capabilities still choose their own windows and
candle sizes independently. The first connected run on 2026-08-30 rejected the cutover when the
configured projection crossed mcal's terminal zero-length early-close break representation. The
committed repair normalizes only that exact provider shape and bounds projection delivery with
typed per-calendar outcomes and correlated consumer retries. Markeitect accepted the repaired
2026-08-31 run: `SessionStateActor` served five projection requests with zero rejection or
construction failure; Evidence Health, Session Metrics, and Historical Planning reported zero
projection timeout or terminal outcome; the planner produced one exact plan with no deferral or
rejection; IB returned 60/60 requested bars; operational persistence reconciled 36/36 records; and
shutdown was clean. The run used the tracked 120-day lookback/14-day lookahead `cme_equity`
profile. This bounded acceptance does not generalize to all five calendars, a scheduled phase
boundary, late-consumer recovery, connected failure/retry paths, concurrent historical requests,
or shutdown with provider work in flight. The wider `SessionMetricsActor` responsibility split
remains deferred.

The detailed ownership and semantics are recorded in
[`architecture/v2-session-evidence-health.md`](architecture/v2-session-evidence-health.md).

The corrective Stage 9A/Priority 0 persistence-safety gate is implemented and live-accepted. The
2026-08-17 mega-clean boot recreated PostgreSQL from an empty volume, applied all migrations,
reached `READY`, and shut down cleanly. It stored all 490 accepted records with no retries,
failures, rejections, pending records, sequence gaps, or duplicates. The batch writes PostgreSQL in
bounded transactions, reserves critical audit capacity, validates startup capacity, suppresses
repeated identical persistence-failure logs, and prevents recoverable queue pressure from creating
the invalid `FAILED -> STARTING` transition. Queue admission remains non-blocking and rejected
payloads remain an explicit audit gap.

Evidence recency now supports configurable, persisted adaptive quote profiles keyed by instrument,
feed, selector, provider, session phase, and policy version. Profiles checkpoint compact derived
statistics only; raw observations remain transient. SPX/VIX use cash-session, bar-derived-last
expectations, and Watchlist observation truth now follows each instrument's declared capabilities.
Acquisition retains provider subscription lifetime ownership during shutdown.

The same acceptance run proved profile learning for ES, NQ, YM, and CL. Brief overnight quote
freshness transitions showed that the configurable two-second hard fresh floor is still sensitive
to natural delivery pauses. Transition hysteresis or persistence windows are tracked as Priority 1
calibration; this does not block Stage 9B.

## Stage 9B: Historical Dependency Execution

Stage 9B is complete and live-accepted as of 2026-08-17. One shared provider request served two
independent consumers and produced separate readiness results while unrelated runtime activity
continued. Historical observations remained transient; PostgreSQL stored only request, execution,
and readiness lifecycle records. UTC remains the internal timestamp boundary. Installed Nautilus
`2.0.0rc3` sends intraday historical bounds in UTC, but its pinned Rust `ibapi 3.3.0` rejects IB's
valid dashed UTC `HistoricalDataEnd` form. TWS/Gateway therefore temporarily remains in instrument-
timezone mode so the dependency can parse response metadata; Nautilus still normalizes resulting
bar instants to Unix nanoseconds. A bounded connected calibration also exposed and reproduced an
inclusive-to-exclusive native request-end defect as 4/5 returned one-minute bars. After the narrow
port correction, one ES request returned five consecutive completed one-minute bars, READY 5/5,
no forming bar, no retry or late callback, an independently active live stream, and fully
reconciled operational persistence. This acceptance is limited to that exact recent-completed path.
Daily and coarser provider bars remain date-semantic and are not accepted as exchange-session
boundary truth.

## Stage 9C: Baseline Metric Contracts

Stage 9C is complete and live-accepted as of 2026-08-19. The first runtime metric family publishes
three deterministic quote-quality values through native signals at a configured bounded cadence.
Watchlist and metric consumers share one provider subscription per instrument, and the metric
actor obtains evidence-health snapshots without startup sequencing.

The acceptance run received 2,111 quotes, suppressed 1,466 by cadence, executed 645 calculation
cycles, and published exactly 1,935 values. Evidence states reconciled exactly: 981 `HEALTHY`, 24
`DEGRADED`, 924 `DORMANT`, and 6 `STALE`; there were no calculation or publication failures.
PostgreSQL stored 464 operational records and 3 system-health records, matching the persistence
runtime's 467 accepted/stored total with no failures or pending writes. Numerical metric values and
raw quotes remain intentionally transient.

The completed extension is the Stage 9C session-measurement work documented in
[`roadmap/v2-stage-9c-session-measurements-plan.md`](roadmap/v2-stage-9c-session-measurements-plan.md).
It closes the completed-bar, session/prior-session, opening-range, gap, power-hour, volatility,
efficiency, and expansion input gap before Stage 9D entity design. Slices 1-2 are enabled and
live-accepted. The acceptance run converged bounded historical and live bars for all 18 configured
instruments, published 1,281 completed-bar values from 183 accepted bars, and reported no actor
calculation failure, duplicate, or conflict. Closed-session recent-history requests degraded
independently without stopping live processing; this confirmed the need for Slice 3's exact,
purpose-specific session windows rather than a universal recent-history warmup.

The former temporary V3 ES debug baseline selected a bounded historical-only review of 60 direct
five-minute `ESU6.CME` completed bars. It fixes the producer interval at 300 seconds, keeps the
normal five-second live input operating, uses close-timestamped native bars through
`timestamp_policy = "interval_end"`, requires two observations for prior-close metrics, and rejects
unequal same-interval observations. The normal producer independently requests up to 60 historical
observations. The visual observer targets those 60 historical bars and zero live-source bars for
display; those projection targets do not set provider request size, retention, or runtime duration.
The nominal selected span is five hours before any real gaps. Markeitect accepted the coordinated
configuration changes as a usable baseline for continuing the debug, while explicitly recording
that the number of coupled settings is not an accepted configuration interface. This is test
authorization, not an accepted IB limit, general history policy, other-timeframe provider
acceptance, or derived-metric value acceptance. The bounded 2026-08-28 connected run is accepted
for its direct five-minute source/series gate: IB returned 60/60 requested bars, SessionMetrics
accepted 60 historical completed bars with zero duplicates, conflicts, or calculation failures,
and the passive artifact selected the same 60 historical bars and zero live bars with no declared
gap. That layout was a provisional debug baseline; repeated per-bar historical-source markers
remain recorded visual cleanup debt. Parameter effective time remains stored
but unenforced and unpublished; the 1,000-observation retention remains provisionally coupled to a
disabled rolling placeholder; and maximum output age remains metadata rather than enforced expiry.

The committed correction made `visual_debug_capture` a strictly passive observer. It
does not reuse either rejected visual component and it does not request a producer snapshot.
Capture on/off composition differs only by the observer; SessionMetrics configuration, startup
history, live demand, calculation, retention, persistence, and lifecycle remain identical. The
observer selects already-published canonical bars and metrics into historical-only, live-only, or
mixed projections. Real gaps, short populations, missing readiness, and incomplete metric cohorts
produce prominently partial diagnostic artifacts. Unequal same-identity records remain terminal
integrity failures. A capacity-one worker writes one self-contained Plotly HTML plus manifest
through atomic directory publication. The artifact is a bounded observer receive cut, not globally
final truth, review acceptance, raw-data persistence, restart state, or provider completeness.

V3-02 subsequently disabled Session Metrics and the dependent Visual Debug and Entity Analysis
surfaces in both tracked profiles. The actor code, historical acceptance evidence, and review
contract remain available for the separately reviewed replacement; they are not current runtime
outputs.

The first connected capture attempt did not publish an artifact and is rejected as visual
acceptance, but it supplied useful runtime evidence. History returned exactly five bars ending at
13:53 UTC. The run then began inside the 13:53-13:54 live aggregation bucket, so that partial minute
could never supply all twelve five-second constituents. The first possible complete live aggregate
therefore began at 13:54, leaving a one-minute gap after the historical cohort. The projection
correctly refused that non-contiguous `HHHHHLLLLL` sequence and expired its 15-minute deadline at
14:08:21 UTC. The run processed 279 live five-second bars; session metrics reported one historical
batch, 27 accepted completed bars, 189 completed-bar values, and zero duplicate, conflict, or
calculation failures. Persistence reconciled 35 accepted/stored records with zero retry, failure,
rejection, or pending write, and SIGINT shutdown completed cleanly. These observations refute the
earlier timer-stall hypothesis: the deadline and live processing both progressed, but their log
records were not visible in the file until shutdown.

The rejected Option 1 capture-alignment behavior is removed. SessionMetrics publishes its normal
startup foundation-history demand whether capture is enabled or disabled. The visual observer
never calls IB, emits demand, chooses an upstream boundary, or publishes canonical truth. A natural
mid-bucket startup gap is now useful debug evidence and remains `UNCLASSIFIED_TEMPORAL_GAP` until a
stronger canonical schedule fact explains it.

The 2-second quiet period, 15-minute completion deadline, and 30-second output drain remain
provisional projection settings. The activation identity is an operator label, not a configuration
digest. The capture schema and renderer policy are versioned separately; `MetricValue`
still lacks bar specification/profile/trade-date/window identity; parameter effective time remains
unenforced; prior-close metrics omit predecessor lineage and do not yet define health, contiguity,
or session-transition compatibility completely. File logging also has measured live-observability
debt: consequential READY, live-progress, and deadline records from the first capture attempt were
buffered and appeared only during shutdown, so tailing the configured log file cannot currently be
treated as reliable evidence that the runtime is stalled or progressing. Browser acceptance,
formula-parity acceptance, accessibility acceptance, provider licensing decision, and final
evidence-fitness decision remain incomplete for this component.

The five-minute completed-bar source/series gate was accepted for that bounded run. At that review
point, the intended next walkthrough was the completed-bar configuration followed by one-by-one
OHLCV and derived-metric review. V3-02 stopped that sequence and disabled the faulty combined
actor. The dormant `SessionMetricsActor` implementation groups completed-bar foundation, session
reference, calendar-window, and rolling-measurement responsibilities in one configuration object.
Its completed-bar foundation configuration is singular: one live selector, one
historical selector, and one calculation interval. This does not impose a system-wide historical
timeframe; other capabilities can declare independent selectors such as fifteen-minute bars.
However, the temporary profile permits only one outstanding historical request, and a second
parallel canonical completed-bar foundation cannot currently be configured. Both restrictions are
explicit architecture/configuration debt, not accepted production policy; no redesign is selected.

Slice 3 is accepted at commit `8696acf`. It adds only deterministic active-session,
previous-session, optional overnight, and gap measurements. Historical and live observations
converge at the last interval actually received, and exact open, prior-close, return, and gap
values remain unavailable when their session boundary was not directly observed rather than being
inferred from partial coverage.

Slice 4 is accepted. It adds
configuration-owned calendar-relative opening-range families and close-relative power-hour
measurements, including developing/completed truth, coverage, supported-volume isolation, and
early-close handling. The initial acceptance scope configures two opening ranges and one power-hour
window for the CME-equity profile only; expanding profiles requires an explicit session-semantics
review. It does not add entities, semantic events, signals, agent behavior, raw market-data
persistence, or execution.

Slice 5 is live-accepted and committed at `116657b`. It adds three
configuration-owned rolling families over one-, five-, and fifteen-minute completed bars, with 24
active duration candidates and 264 versioned numerical metric definitions. Every candidate reports
range, realized log-return magnitude, average true range, directional efficiency, coverage, and
independently qualified recent and phase-matched expansion baselines. Candidate durations,
reference counts, coverage requirements, selection metadata, and dynamic eligibility all have
explicit configuration envelopes. A bounded 720-observation one-minute warmup can support each
current candidate window, while the 8,000-observation transient ledger can eventually satisfy the
minimum recent baseline for the longest candidate; neither is a universal historical pyramid.
Numerical values and raw bars remain transient, and no semantic regime, compression, trend, signal,
entity, or agent decision is created in this slice.

The extended 2026-08-21 RTH acceptance completed all 63 historical dependencies with zero
degradation and kept all 34 acquisition streams active. Across 32,659 live bars and 18 historical
batches, the measurement actor accepted 10,632 completed bars, identified 13 exact duplicates and
zero conflicts, and published 103,236 completed-bar values, 44,718 session-reference values, 1,779
calendar-window values, and 307,296 rolling values across 2,736 rolling batches. It reported zero
calculation failures. PostgreSQL stored all 32,389 accepted operational events with zero retries,
failures, rejections, or pending writes; Discord delivered all three health messages; shutdown
completed cleanly.

The run also exposed separate hardening concerns which do not invalidate the deterministic
measurement results: evidence-health transitions remain too noisy for some thin instruments, late
evidence callbacks can appear after their actor has entered shutdown, and closed-session calendar
windows were rejected before their future phase began. The first two remain follow-up work. The
closed-session path is now implemented for review as typed, deduplicated deferral with exact
first-completed-boundary retries and session-transition wakeups. Invalid policies still fail hard,
and unrelated acquisition remains active. The optional Observatory ran concurrently during this
acceptance, so its suspected host resource cost is isolated on `v2-stage-observatory` rather than
attributed to Stage 9C.

Stage 9C session measurements are closed. They provide numerical evidence for future entities and
semantic events; they do not themselves classify market state or create opportunities.

## Runtime Resource Hardening

Commit `ba442c4` adds the reviewed passive `RuntimeResourceActor`. The first short connected run
persisted all seven raw samples and showed bounded RSS/cache growth with no sampling failure. At a
configuration-owned cadence the actor publishes process memory, CPU, thread, file-descriptor, host
memory/CPU/swap, disk headroom, and public Nautilus cache-count evidence through the typed
`markeitech.runtime.resource` contract. The existing operational persistence actor records samples
as `runtime.resource`; no raw market data or new database table is introduced.

Commit `248a999` adds a separate `RuntimeResourceHealthActor`. It evaluates only
configuration-owned, versioned thresholds with sustained warning/critical/recovery windows and
publishes durable semantic transitions on the non-overlapping `markeitech.runtime.health` signal as
`runtime.resource_health` operational events. Discord remains a read-only
projection: critical transitions may ping; warnings and recoveries do not; raw samples are never
sent. The actor does not mutate Nautilus cache policy, alter global system health, or select Redis.

The 2026-08-22 Observatory-off run collected 20 bounded samples with flat cache counts and no
sampling failures. It also exposed Nautilus prefix-routing overlap between the original raw and
health signal names: one transition re-entered the health actor and reached persistence twice,
rolling back a three-record batch. The health signal now uses a non-overlapping namespace, consumers
guard exact signal names, and the disk critical-percentage threshold is versioned at 2% so the
observed 17.5 GiB / 3.8% state remains warning-level while the 5 GiB absolute critical guard stays
active. Offline verification passes 302 tests with two PostgreSQL-marked tests deselected.

The corrected connected rerun collected 15/15 durable raw samples and one sustained
`NORMAL -> WARNING` disk-headroom transition under policy `2026-08-22-v2`. The health actor reported
zero rejected samples; Discord delivered all four eligible lifecycle/resource messages; global
system health remained `READY` until controlled shutdown; and PostgreSQL reconciled all 726 accepted
records with zero retries, failures, rejections, or pending writes. Process RSS grew only 3.3 MiB,
cache counts remained bounded, and Nautilus returned cleanly. The resource warning path and signal
routing correction are connected-accepted; critical and recovery projection remain controlled
follow-up cases rather than blockers for this hardening batch. The runtime-resource evidence gate
closed before Stage 9D began.

## Stage 9D: Entities And Rolling State

Stage 9D is active. Slices 9D.1 through 9D.4C are approved and committed; the stage gives
accepted Stage 9C measurements stable entity identity, bounded current-state projection, explicit
revision/expiry/invalidation semantics, and an approved compact completed-session recovery
boundary. Its approved scope now includes complete first deterministic implementations for
objective session/reference/level entities; volatility and compression/expansion state;
horizon-specific direction, trend, rotation, and range state; moving/anchored references; and
confirmed swings, deterministic swing legs, per-horizon pivot structure, FVGs, and derived zones.
It also includes a separately named bar-volume-distribution baseline with explicit
`INFERRED_FROM_BARS` fidelity; observed trade-at-price profiles remain deferred.

Stage 9D does not introduce semantic interaction events such as approach, acceptance, rejection,
breakout, or failure; options intelligence; Discord market alerts; ML; Sir Loke; raw market-data
persistence; replay; or execution. All variable formulae, thresholds, horizons, detectors,
windows, lifecycle policies, and resource bounds must be typed, bounded, versioned configuration
with optimization metadata. Initial parameter values are not presented as trading calibration.

The detailed plan is available in
[`roadmap/v2-stage-9d-entities-rolling-state-plan.md`](roadmap/v2-stage-9d-entities-rolling-state-plan.md).
The initial Stage 9D capability bindings, bounded actor split, EMA/reference baseline, first
swing/FVG/zone/bar-volume definitions, three-class durability policy, dedicated analytical
persistence ownership, and restoration/retention policy are approved.

Slice 9D.1 is implemented. It introduces framework-independent, immutable
entity definition, identity, parameter, evidence, revision, lifecycle, durability, snapshot, and
admission contracts plus a pure bounded state book. Entity IDs are deterministic; registry
dependencies and payload/evidence compatibility are validated; revision gaps, stale writes,
conflicts, and meaningless updates are rejected; only terminal state may be evicted or pruned; and
cross-session restoration is forced to remain stale/degraded until later catch-up evidence. The
state book supports bounded snapshots by instrument, entity type, analytical profile, identity
dimensions, and lifecycle. Nine focused entity tests and the 312-test non-PostgreSQL suite pass.

Slice 9D.2 is approved and committed. Tracked configuration schema 16 adds a disabled,
bounded entity-analysis catalog capable of representing all five approved groups with exact
profile/instrument/session/horizon applicability; metric and entity dependency versions; permitted
health/fidelity; lifecycle rules; durability; complete parameter schemas and effective parameter
sets; optimization eligibility; and global/per-instrument resource limits. Enabled catalogs must
represent all five groups and reject unknown applicability, unsupported volume use, duplicate
identity/version, missing parameter values, invalid mutability, and values outside or off their
declared optimization envelope. The tracked example remains disabled with no definitions so this
schema change does not activate unreviewed market semantics.

Stage 9D.2 also adds version-one metric-registry definitions and pure deterministic calculations
for signed displacement, signed simple return, signed path efficiency, configurable EMA value,
slope and price separation, confirmed strict-pivot swing geometry, three-bar wick FVG geometry and
fill, and uniform-intersection candle-volume price-bin estimates. Their real warmup, units,
formulae, dependencies, health, fidelity, failure modes, bounds, and mutability are explicit.
Bar-volume output is always `INFERRED`; unsupported or partial volume remains honest. Eight focused
prerequisite tests, 25 configuration tests, the 105-test intelligence suite, and the 327-test
non-PostgreSQL suite pass with two PostgreSQL-marked tests deselected.

Slice 9D.5A is approved and committed at `666b972`. It adds a framework-independent confirmed-swing
payload, detector application contract, and bounded projection owner over completed bars. A swing
is published as an immutable `COMPLETE` entity only after its configured right span exists in one
contiguous evidence run. Identity preserves definition, detector/version, source bar specification,
horizon, pivot timestamp, swing kind, instrument, and analytical profile. Payload preserves exact
pivot and confirmation geometry, strict prominence, confirmation displacement, optional pivot-bar
volume, configured spans, and source-bar references. Health and fidelity remain inherited from the
full evidence window. Age stays query-relative from the confirmation timestamp instead of creating
time-only entity revisions.

The owner uses the shared entity registry/state book, rejects conflicting bar observations,
suppresses historical/live duplicates, permits late bars to complete a previously gapped evidence
window, requires contiguous bars, bounds retained candidate evidence and confirmed entities, and
supports independent tactical and structural detector identities without interpreting either as
trend, support, resistance, reversal, or direction. Seven focused tests plus the prerequisite tests
pass 15/15; the complete intelligence suite passes 134 tests, and the full non-PostgreSQL suite
passes 365 tests with two PostgreSQL-marked tests deselected. No actor, runtime composition,
configuration migration, PostgreSQL schema, Discord projection, semantic event, connected run,
or visual annotation is included.

Slice 9D.5B is approved and committed at `4d2cee9`. A separate pure relationship owner consumes
immutable complete confirmed-swing revisions and projects deterministic alternating swing legs and
one revisable pivot-structure state per exact instrument/profile/detector/horizon/chain-policy
subject. Legs preserve endpoint revisions, price and percentage displacement, bar and UTC duration,
raw slope, optional normalized slope, path efficiency, excursion, volume context, completed-bar
lineage, health, fidelity, and missing context. The structure payload preserves selected pivots,
same-kind predecessor comparisons, structural bounds, leg-scale comparisons, superseded and
unresolved pivots, and conflicts without changing confirmed swing truth or creating a universal
direction score. Eighteen focused market-structure tests, 145 intelligence tests, and 376
non-PostgreSQL tests passed for that reviewed batch.

Slice 9D.5C is implemented locally for review. A pure bounded FVG owner applies the reviewed
three-completed-bar wick-gap detector to contiguous evidence only. It projects stable formation
identity, exact bounds and source bars, optional explicit width normalization, fill ratio,
remaining interval, lifecycle bars, and configurable full-fill and completed-bar-age terminal
outcomes. Exact duplicates and conflicts cannot rewrite accepted bar truth; late bars and
normalization evidence reproject deterministically; retained bars, normalizations, entities, and
publication work are bounded. FVG entities remain independent. The first baseline does not merge
or reinterpret their identities.

A separate pure derived-zone owner consumes approved objective-level, confirmed-swing, and active
FVG revisions. Its versioned policy explicitly owns source types and horizons, lifecycle and
developing eligibility, same-horizon or mixed-horizon compatibility, merge distance, padding,
maximum width, minimum constituents, constituent age, deterministic ordered partitioning, equal
weighting, withdrawal outcome, and source retention. Merge and split create inspectable zone
lifecycle revisions while every zone payload and evidence reference preserves the exact source
entity IDs and revisions. Zones carry geometry only: no support/resistance label, revisit claim,
confidence, opportunity score, direction, alert, or execution meaning is introduced.

Sixteen focused 9D.5C tests prove no-look-ahead formation, partial/full fill, configured
completion/invalidation, expiry, late evidence, normalization, bounded retention, source and
horizon eligibility, exact lineage, maximum-width splitting, merge/split history, reactivation,
and arrival-order convergence. The complete intelligence suite passes 161 tests and the full
non-PostgreSQL V2 suite passes 392 tests with two PostgreSQL-marked tests deselected. The slice adds
no actor, runtime/configuration migration, PostgreSQL schema, Discord output, semantic event,
renderer, connected run, or trading interpretation.

The ignored local runtime configuration was operator-reviewed and migrated to schema 16 for the
connected Group 1 acceptance run. It remains local and untracked; the tracked example remains
disabled and empty.

Slice 9D.3 is approved, committed, and closed-market connected-accepted.
`SessionReferenceEntityActor` consumes only typed
`MetricValue` custom data and projects analytical-session, previous-session-reference,
opening-range, opening-gap, and direction-neutral objective-level revisions through native
Nautilus custom data. The actor does not consume bars, request provider data, calculate semantic
interactions, choose direction, notify Discord, or write analytical state to PostgreSQL. Exact
application profile, instrument, session-phase, metric/version, parameter-version, health, and
fidelity contracts remain configuration owned.

The upstream metric contracts now expose exact active/previous-session bounds and completion plus
opening-range open, close, and supported volume. Unsupported volume remains optional field-level
evidence and does not degrade otherwise valid price geometry. The bounded owner converges under
out-of-order metric arrival, suppresses duplicates and conflicts, retains overflow publications
instead of discarding them, scopes per-type limits by instrument, and serves immutable typed
snapshot requests/responses. Enabled Group 1 composition also fails closed when a definition names
a metric/version that the configured session-reference or opening-range producers cannot emit. The
enabled test catalog contains the complete Group 1 definitions; the tracked runtime example remains
disabled and empty.

The accepted 2026-08-23 closed-market run reached `READY` with all 18 configured instrument
definitions. Acquisition completed 39 historical dependencies: 21 were ready and 18 degraded
honestly after IB returned no one-minute observations for the closed-market interval. Session
measurement produced 18 reference batches with 900 values and three window batches with 39 values,
with zero failures. Group 1 accepted 42 metric values and published 45 entity revisions, with nine
duplicate revisions, zero rejected revisions, and no pending publications. A missing-evidence
timestamp defect found during the first connected run was corrected so the same path now emits a
payload-free `WARMING` revision instead of escaping the actor callback. The complete offline V2
suite passes 337 tests with two PostgreSQL-marked tests deselected. PostgreSQL stored all 682
accepted operational events, Discord delivered all three health messages, resource health remained
normal, and shutdown was clean.

RTH live-bar updates, developing-to-complete session transitions, and rolling-input behavior remain
explicit connected-acceptance debt. No Stage 9D analytical-state schema, Discord market projection,
or semantic interaction event has been introduced.

Slice 9D.4A is approved and committed. It adds immutable typed payload
contracts for volatility, compression/expansion, horizon-specific direction, trend/rotation, and
configured reference state plus one pure scalar state-classification primitive. Category labels and
contiguous bands, definition and parameter identity, evidence measure, health/fidelity envelope,
minimum coverage, hysteresis, consecutive confirmation, and maximum evidence age are supplied by
validated versioned policy rather than hidden constants. The classifier handles exact boundaries,
candidate interruption, stale or late evidence, and unavailable state deterministically.

The family projectors retain their exact numerical inputs, horizon, evidence references, candidate
and confirmed state, reference axes, and explicit cross-horizon conflicts. They do not create a
universal direction or trend score and do not infer transitions or trading meaning. Seven focused
market-state tests, the 144-test intelligence/configuration scope, and the complete 344-test
non-PostgreSQL suite pass with two PostgreSQL-marked tests deselected. Stage 9D.4A adds no actor,
provider request, runtime configuration binding, entity revision publication, PostgreSQL schema,
Discord output, semantic event, opportunity selection, option selection, or Sir Loke behavior.

Slice 9D.4B is approved and committed at `3b815eb`. It adds typed market-state
definition, application, and policy-axis bindings plus one bounded pure projection owner for
metric-driven volatility, compression/expansion, exact-horizon direction, and independent
reference slope/separation state. The owner contains stale, duplicate, conflicting, mismatched,
out-of-scope, and out-of-order input; retains metrics under a configured limit; uses the shared
entity registry/state book; defers publication overflow; serves filtered snapshots; and can publish
staleness revisions from explicit reconciliation without new market input. Per-entity classifier
memory is removed if the state book rejects or evicts that identity.

Trend/rotation runtime ownership is deliberately deferred because it requires typed cross-entity
inputs and explicit conflicting-horizon evidence. Stage 9D.4B does not counterfeit that evidence
as scalar text. Eight focused owner tests and the combined 152-test intelligence/configuration
scope pass in the locked V2 environment. The complete non-PostgreSQL V2 suite passes 352 tests with
two PostgreSQL-marked tests deselected. The batch adds no Nautilus actor, provider request, runtime
TOML translation, PostgreSQL schema, Discord output, semantic event, opportunity, option selection,
or Sir Loke behavior.

Slice 9D.4C is approved and committed at `662fa0f`. It adds strict optional
market-state policy bindings to entity-analysis catalog version 2 and a bounded
`MarketStateEntityActor` which consumes typed `MetricValue`, delegates all classification and
revision ownership to the 9D.4B pure owner, publishes typed `EntityRevision`, serves the existing
snapshot contract, and performs configured periodic staleness reconciliation. Category bands,
boundary values, hysteresis, confirmation, minimum coverage, maximum evidence age, parameter-set
identity, resource limits, and reconciliation cadence remain explicit validated configuration.

Runtime composition admits only enabled Group 2 or Group 3 definitions with an explicit
`market_state` binding and fails closed if any declared metric/version lacks an active configured
producer. The current offline test catalog therefore activates only `volatility_state`, bound to
the configured fast `context_45m` recent-range percentile and coverage metrics. The catalog-only
dynamic EMA definition remains inactive. Compression/expansion still lacks its required phase
duration metric; direction and reference state still lack their signed-direction and EMA-reference
producers; trend/rotation still requires typed cross-entity reconciliation. None is manufactured
from substitute evidence.

Focused configuration, composition, and native in-process bus tests prove strict policy validation,
producer-contract rejection, selective actor registration, and rolling metrics projecting into a
typed active volatility-state revision. The combined intelligence/configuration/composition/message
scope passes 173 tests. The complete non-PostgreSQL V2 suite passes 358 tests with two
PostgreSQL-marked tests deselected. The tracked runtime example remains disabled and empty, so this
batch does not activate new market semantics in a normal run. It adds no provider request,
PostgreSQL schema, Discord projection, semantic event, opportunity, option selection, or Sir Loke
behavior.

Connected acceptance closed on 2026-08-24 using the ignored local acceptance configuration and
liquid London/ETH futures data. The actor consumed 645 metrics, published 645 valid revisions,
completed 2,560 staleness-reconciliation cycles, retained 15 current metrics, and stopped with zero
conflicts, rejected revisions, deferred or pending publications, projection failures, or snapshot
failures. No evidence crossed its staleness boundary during the run, so no stale revision was
observed. The surrounding runtime produced 64,064 rolling values without calculation failure,
stored 2,261/2,261 operational events without retry or rejection, delivered 4/4 Discord health
messages, remained resource-bounded, and disconnected cleanly. This closes 9D.4C without claiming
the separately deferred 9D.3 opening-range boundary transition.
