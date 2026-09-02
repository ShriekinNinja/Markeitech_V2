# TOML-Driven Markeitech System and Data-Flow Diagram Plan

> Migration note (2026-08-31): this plan still governs the currently implemented diagram tool.
> The API-documentation tool no longer reads the TOML after a one-time component-docstring seed.
> Source documentation is the intended upstream for a future, separately reviewed exporter; this
> TOML-driven plan is not superseded until that exporter exists and is accepted.

**Phase:** Approved staged implementation; Stage 1 authorized
**Report date:** 2026-08-30
**Checkout:** `v3-toml-system-dataflow-diagram` at `c6fe2ad89ae2da077d08c55998cc9ff639c5f0ce`
**Target branch after separate approval:** `v3-es-progressive-capability-review`
**Decision owner:** Markeitect
**Report status:** Approved by Markeitect for staged implementation on 2026-08-30
**Runtime effect:** None. The utility is unrelated to runtime operation and has no runtime consumer.

## Executive conclusion

Proceed with a repository-owned, TOML-driven diagram system under the decisions recorded below. The approved design is a narrow offline documentation-tool project with four deliberately separate truth domains:

1. **Runtime/code truth:** what the reviewed checkout implements and composes.
2. **Architectural-manifest truth:** the reviewed representation used for diagram content and presentation. This is the only hand-edited diagram source.
3. **Generated-artifact truth:** reproducible projections derived only from a successfully validated manifest.
4. **Historical truth:** Git history and accepted architecture records, including removed, rejected, and future boundaries when explicitly represented as such.

“Always aligned” cannot honestly mean that TOML detects every semantic code change by itself. It should mean that the repository requires the same reviewed development batch to update the manifest when architecture changes; bounded static census checks detect mechanically recognizable drift; generation is deterministic at the semantic level; tracked artifacts are regenerated and diff-checked; unsupported source shapes fail closed; and a named human reviewer remains responsible for meaning, authority, omissions, and status honesty.

The system must not import or execute Markeitech runtime code, NautilusTrader, provider adapters, configuration loaders, or `.env` handling. It must not construct a `LiveNode`, start an actor, contact IB, PostgreSQL, Discord, Docker, or any network service, inspect a running process, or read provider data, logs, credentials, or operational storage. Its inputs are restricted to the canonical tracked TOML manifest, explicitly allowlisted tracked source/configuration evidence, and separately approved tracked local assets. Its outputs are documentation only and must never feed runtime configuration or behavior.

Use multiple views from the same stable identities rather than one unreadable everything graph. SVG should be the primary scalable visual, PNG the immediate review image, DOT the structural debugging artifact, and deterministic Markdown the required non-spatial accessibility companion. Every view should carry visible scope, profile, review state, limitations, “generated — do not edit” language, and a clear statement that Markeitech currently submits no orders.

Two material limitations remain:

- The checkout implements a transient persistence-readiness request/response handshake that current accepted documentation says was replaced or removed. Markeitect approved showing the implemented handshake with an explicit unresolved-documentation limitation; runtime/document reconciliation is deferred to a separate task.
- Markeitect declined the optional follow-up PostgreSQL specialist consultation. The persistence view must therefore stop at the verified application write boundary and label database transaction, durability, ambiguous-commit recovery, schema, retention, restore, and run-closure mechanics as unknown.

Continuous implementation is authorized through a runnable, reviewable set of all six offline diagram views. The full batch remains uncommitted for final review. No CI job is approved.

## Markeitect decision record

Markeitect approved the following decisions on 2026-08-30:

- The TOML is consumed only by the offline loader, validator, drift checker, renderer, and generated-documentation workflow. It has no runtime or operational relationship.
- Show the persistence-readiness handshake implemented by current code and expose the accepted-documentation mismatch; defer reconciliation.
- Do not require a PostgreSQL advisor consultation. Stop the persistence representation at the verified application write boundary and mark database internals unknown.
- Generate both a named tracked-profile runtime view and a complete capability inventory.
- Keep implementation, composition, profile enablement, acceptance, and temporal status independent.
- Preserve stable IDs for renames; use new IDs for semantic replacements; retain removed/rejected IDs as tombstones.
- Generate five main views plus a sixth separate future-governed-boundaries view.
- Keep every diagram fact and presentation choice in the TOML, with no Python expressions or runtime logic.
- Require same-batch TOML update, validation, and regeneration for architecture-changing work.
- Use a separately locked documentation-tool environment outside V2 and the preserved root project.
- Evaluate Diagrams with Graphviz using shape-only generic nodes first; defer provider logos/custom icons.
- Generate and track SVG, PNG, DOT, Markdown companions, and an artifact hash/index set.
- Publish artifacts atomically and preserve the prior complete set on failure.
- Add the shared PyCharm configuration named exactly `Generate Sys Diagram` in its later approved batch.
- Do not add a CI diagram job. Enforcement remains local through the generator, PyCharm, staged diffs, and Markeitect review.
- Markeitect is always the final semantic reviewer and sole exception approver.
- Check source paths, symbols, contracts, composition, and configuration without per-symbol source hashes.
- Select exact Python, Diagrams, Graphviz, and font identities only after an offline compatibility/determinism spike.
- Measure readability budgets during implementation and return them to Markeitect for approval.
- Require every drift exception to have exact scope, reason, expiration/removal condition, and Markeitect approval.
- Invoke Graphviz through a fixed approved executable and controlled offline subprocess; the TOML cannot provide commands or executable paths.
- Continue across the implementation stages without intermediate approval pauses; keep the complete result uncommitted for final review.

## Scope and non-negotiable offline boundary

The proposed utility documents the system/data-flow architecture; it is not part of that architecture’s live execution. The implementation must satisfy all of the following as hard boundaries:

- It lives outside the runtime package and remains an isolated offline repository tool.
- It is not a Nautilus actor, plugin, projection actor, service, worker, or runtime CLI subcommand.
- It never imports `markeitech`, `nautilus_trader`, `dotenv`, `psycopg`, HTTP clients, Docker clients, browser/viewer code, or runtime configuration modules.
- It never constructs or starts a `LiveNode`, data client, actor, worker, timer, subscription, historical request, persistence store, or external projection.
- It never reads `.env`, credentials, account identifiers, runtime logs, database contents, provider observations, ignored operator profiles, or host-specific runtime state.
- It performs no network access during validation or generation and never downloads icons, fonts, schemas, documentation, or packages while generating.
- It reads only normalized repository-relative regular files under closed allowlisted roots. Absolute paths, `..`, URLs/URIs, symlinks, devices, sockets, FIFOs, and untracked assets are rejected.
- It writes only a fixed generator-owned output directory through an atomic complete-set publication process.
- It does not affect runtime dependencies, readiness, provider demand, persistence, resource behavior, analytics, shutdown, or product semantics.
- It emits no viewer/browser launch and always uses `show=False` at the Diagrams boundary.

Application controls and tests can demonstrate this boundary for the intended code. They cannot prove that a compromised native Graphviz binary lacks macOS filesystem or network authority. Exact tool provenance, a sanitized subprocess environment, local adversarial tests, and optional OS sandboxing remain distinct defenses. No CI diagram job is approved.

## Required repository authorities and discovery method

The following tracked authorities were read before planning, in the order required by `AGENTS.md`:

- `markeitech.md`
- `docs/current-status.md`
- `docs/development-guidelines.md`
- `docs/README.md`

Relevant accepted architecture, roadmap, operations, source, configuration, and focused tests were then inspected, including:

- `docs/architecture/v2-runtime-control-plane.md`
- `docs/architecture/v2-actor-composition-discovery.md`
- `docs/architecture/v2-provider-data-boundary-discovery.md`
- `docs/architecture/v2-adaptive-market-data-plane.md`
- `docs/architecture/v2-historical-dependency-execution.md`
- `docs/architecture/v2-session-evidence-health.md`
- `docs/architecture/v2-baseline-metric-contracts.md`
- `docs/architecture/v2-supervision-failure-policy.md`
- `docs/architecture/v2-persistence-boundary-discovery.md`
- `docs/roadmap/v2-stage-9d-entities-rolling-state-plan.md`
- `docs/roadmap/v2-market-events-live-agent-plan.md`
- `docs/operations/developer-setup.md`
- `docs/operations/github-workflow.md`
- current composition, node construction, configuration, acquisition, historical, session, health, metric, entity, persistence, Discord, resource, and visual-debug source and nearby tests
- `config/system.v3-es-minimal.toml`
- `pyproject.toml` and `uv.lock`

Discovery was static and read-only. No runtime module was imported, no test suite or service was run, no `.env` or ignored local profile was opened, no provider or database was contacted, and no dependency was installed. Tracked documents establish accepted intent and status; implementation establishes current code behavior; passing tests establish only their exercised scope; previously recorded connected evidence remains bounded to its named run.

The retired runtime data-flow audit described obsolete SQLite/Parquet behavior and was excluded
from automated current-V2 evidence admission before its removal. The intentionally absent
`docs/architecture/current-system-dataflow.png` is neither tracked nor present in this checkout and
was not used.

## Kite council: selected advisors, questions, and status

Kite was activated through the explicitly invoked Markeitech advisor router. Policy `2026-08-29-v3` selected the smallest sufficient set whose answers could change the schema, system census, offline boundary, delivery claims, provider labels, or visual acceptance. Consultations were read-only and advisory.

| Selected role | Exact owned question | Status and effect on this plan |
|---|---|---|
| `markeitech_architecture_boundaries_advisor` | Which topology, canonical-authority, composition, lifecycle/failure-boundary, and drift facts must be modeled so the manifest remains an honest representation rather than competing authority? | Complete. Recommended the four-truth model, independent status axes, named-profile views, stable IDs/tombstones, same-batch updates, fail-closed census checks, and explicit reviewer ownership. It also found the initial detached checkout; the clean worktree was attached to the requested branch at the unchanged commit before this report was written. |
| `markeitech_nautilus_advisor` | Which installed RC3 Nautilus boundaries are native and safe to name, and which lifecycle, bus, adapter, cache, request, callback, readiness, and release semantics remain unknown? | Complete, including its required native-capability gate and Nautilus Alignment Matrix. RC3 is the current pin; refreshed nightly RC4 material is drift context only. The plan must distinguish native mechanics from Markeitech semantics and must not infer order, acknowledgement, cancellation, or provider behavior. |
| `markeitech_event_driven_architecture_advisor` | Which publication, subscription, request, response, callback, readiness, release, persistence, notification, queue, timer, worker, and failure edges are verified, and what delivery/order/idempotency/retry/backpressure/shutdown semantics are known? | Complete. No end-to-end exactly-once or global-order claim is admissible. It found unbounded result queues, no autonomous live-subscription retry, weak historical callback correlation, asynchronous persistence projection, and a code/document persistence-readiness conflict. |
| `markeitech_data_quality_lineage_advisor` | Which source, lineage, clock/session, completeness, duplicate/conflict/revision, freshness, fidelity, schema, retention, and evidence-health facts must be represented, extracted, or left unknown? | Complete with limits. Required completeness vectors, explicit clock domains, historical/live lineage separation, exact duplicate/conflict keys, and limitation records. It identified gaps in historical completeness, metric provenance, conflict audit, selector-specific health, calendar evidence, and snapshot history. |
| `markeitech_security_tool_boundary_advisor` | What is the least-authority offline design for files, dependencies, Graphviz invocation, assets, CI, PyCharm, diagnostics, publication, and revocation? | Complete, conditional. Recommended a separately locked documentation-tool project, closed read/write roots, no runtime imports, a sanitized controlled Graphviz subprocess, shape-only first release, and security/adversarial tests. No security approval was granted. |
| `markeitech_evidence_visualization_advisor` | What view grammar, accessibility artifacts, complexity gates, formats, provenance, and human visual acceptance are required for trustworthy large architecture diagrams? | Complete. Required multiple views, status axes that never rely on color alone, per-view structured companions, no automatic edge reduction, semantic determinism, and measured/approved complexity budgets. |
| `markeitech_ib_market_data_advisor` | Which IB facts about the configured quote/bar/history paths, acknowledgements, callbacks, timestamps, population, revisions, overlap, entitlements, pacing, and failure modes may be admitted from current provider sources? | Complete with limits. Public IB capability and local configuration may be shown separately; exact account entitlement, qualified contract, returned mode, adapter mapping, population completeness, cancellation, and parity remain unknown without narrower evidence. |
| `markeitech_postgres_persistence_advisor` | Which operational-audit storage, queue/worker, transaction, idempotency, retry/recovery, run-lifecycle, retention, and schema facts may be shown without implying unsupported raw or analytical durability? | Not consulted. Markeitect explicitly declined the follow-up consultation and approved a narrower diagram boundary: show only the verified application write path and mark database mechanics unknown. |

Dependency order used by the router was architecture → Nautilus → event delivery; Nautilus → data quality; IB consumed the established Nautilus/data limits; security and visualization were independent but their recommendations were reconciled against the architecture and contract findings. No generalist substituted for PostgreSQL advice and no database-internal claim is admitted.

Additional specialists were intentionally not selected for this planning decision:

- quantitative-metric validation is not needed because the utility validates topology and contract metadata, not formulas or numerical values;
- vendor licensing/provenance is not needed unless provider data or vendor assets are later admitted; no such data is proposed;
- evidence-fitness is not invoked because no named downstream-use acceptance is being granted;
- live-agent governance is not required to show future Sir Loke/execution only as explicitly absent/future, with no authority semantics beyond that limitation;
- Python runtime mechanics and PostgreSQL mechanics would require their specialists before changing runtime designs, but this utility only documents statically observed boundaries and explicit unknowns.

## Verified current-system census

### Current runtime container and native boundary

`src/markeitech/system/node.py` constructs one NautilusTrader `LiveNode` through `LiveNode.builder(...)`, configures one Interactive Brokers data client, builds the node, and registers the code-owned actor plan using `add_actor_from_config(...)`. The project is pinned to NautilusTrader `2.0.0rc3` by `pyproject.toml` and `uv.lock`.

The manifest may identify these current native boundaries:

- the data-only/advisory `LiveNode` container;
- native actor lifecycle, clock/timers, logging, message-bus routing, data engine, and in-process cache;
- native instruments and `InstrumentId`;
- native `QuoteTick`, `TradeTick`, `Bar`, `BarType`, and `InstrumentStatus` observations;
- native `DataType`/`CustomData` routing used by Markeitech custom contracts;
- the Nautilus IB data-client/adapter boundary;
- native subscription/unsubscription and historical `request_bars`/callback surfaces.

The manifest must not imply that native risk, execution, or portfolio infrastructure is a current Markeitech action path. There is no composed strategy, execution client, order submission, replay, backtest, raw-data catalog, Redis, or raw-market persistence flow. Risk/execution framework families should normally be omitted from data-flow views; if context requires them, they must be explicitly labelled “native framework facility — no current Markeitech order path.”

The RC3 public actor surface verifies signals and custom data, but not a current direct Markeitech use of raw message-bus endpoints/request-response. Do not invent physical custom-data topic strings: record the stable `DataType` identity and state that Nautilus derives routing unless exact current-pin evidence later proves a concrete topic.

### Actor composition and ordering

`src/markeitech/system/composition.py` is the code-owned actor-plan authority. Its registration order is:

1. `system_control` — always composed
2. `session_state` — always composed
3. `evidence_health` — always composed
4. `discord_health` — conditional
5. `visual_debug_capture` — conditional
6. `quote_quality_metrics` — conditional
7. `session_metrics` — conditional
8. entity actors, each definition/configuration gated:
   - `session_reference_entities`
   - `market_state_entities`
   - `market_structure_entities`
9. `watchlist` — always composed
10. `data_acquisition` — always composed
11. zero or more `historical_dependency_probe` actors — conditional diagnostics
12. `native_consumer_probe` — conditional diagnostic
13. `runtime_resources` — conditional
14. `runtime_resource_health` — conditional under runtime resources
15. `operational_persistence` — always composed last

Duplicate actor IDs are rejected. Registration order is not startup order, event-delivery order, callback order, readiness order, stop order, or a dependency guarantee. These relationship classes must be independently represented.

The tracked `config/system.v3-es-minimal.toml` profile is schema 18. Static evaluation and the focused profile test establish this eight-actor plan:

1. `SYSTEM-CONTROL`
2. `SESSION-STATE`
3. `EVIDENCE-HEALTH`
4. `VISUAL-DEBUG-CAPTURE`
5. `SESSION-METRICS`
6. `WATCHLIST`
7. `DATA-ACQUISITION`
8. `OPERATIONAL-PERSISTENCE`

This should be called the **tracked V3 progressive-review profile**, not the universally active runtime. The ignored operator profile is unavailable and must not be inspected or inferred.

### Implementation, composition, and profile status

| Component/capability | Implementation | Composition policy | Tracked V3 profile | Canonical responsibility or limitation |
|---|---|---|---|---|
| `SystemControlActor` | Implemented | Always | Enabled | Sole global-health transition owner; `READY` is control-plane startup readiness, not live-evidence or provider readiness. |
| `SessionStateActor` | Implemented | Always | Enabled | Session/calendar-state owner; current schedule/version limitations remain explicit. |
| `EvidenceHealthActor` | Implemented | Always | Enabled | Evidence availability/recency owner; health is not downstream fitness. |
| `WatchlistActor` | Implemented | Always | Enabled | Static configured membership/lifecycle owner and bootstrap-demand producer. Dynamic membership is deferred. |
| `DataAcquisitionActor` and coordinator | Implemented | Always | Enabled | Sole logical provider-demand/request/subscription-lifetime owner; Nautilus/IB own physical mechanics. |
| `OperationalPersistenceActor` | Implemented | Always | Enabled | Sole in-node operational-audit projection/writer; CLI owns process-run opening/terminal closure. Database mechanics remain intentionally unknown beyond the verified application write boundary. |
| `SessionMetricsActor` | Implemented | Conditional | Enabled | Container for completed bars, session references/windows, rolling metrics; only completed-bar foundation is enabled in this profile. |
| `VisualDebugCaptureActor` | Implemented | Conditional | Enabled | Passive diagnostic projection; not evidence, analytical, runtime, or architecture authority. |
| `DiscordHealthActor` | Implemented | Conditional | Disabled | Best-effort external projection only. |
| `QuoteQualityMetricsActor` | Implemented | Conditional | Disabled | Quote-derived metric owner. |
| `RuntimeResourceActor` / `RuntimeResourceHealthActor` | Implemented | Conditional | Disabled | Resource sample and resource-health owners. |
| Entity actors | Implemented | Definition gated | Disabled | Family-specific entity projection owners; snapshots are bounded current state, not history or durability. |
| Historical/native probes | Implemented diagnostics | Conditional | Disabled | Acceptance harnesses, not production capability owners. |
| `VisualAcceptanceActor` / `LiveEvidenceReviewActor` | Removed/rejected | Not composable | Not applicable | Historical tombstones only; never current. |
| Analytical-summary persistence | Accepted future boundary | Not implemented | Not applicable | Future durability distinct from operational audit. |
| Semantic events, options intelligence, opportunities, ML, Sir Loke | Future/deferred | Absent | Not applicable | Future only; no current runtime authority or flow. |
| Order/execution path | Absent | Absent | Absent | No current order submission or execution. |

### Provider-facing ownership and data acquisition

`DataAcquisitionActor` and its coordinator own logical shared demand, request/subscription lifetime, instrument-definition readiness, historical execution policy, consumer fan-out, and release. Consumer actors separately register native handlers so they can receive canonical native data. Multiple actor-level subscription calls must not be diagrammed as multiple canonical provider owners; Nautilus/DataEngine and the adapter may collapse physical subscriptions, with acceptance evidence bounded to the measured path.

The tracked profile declares one Markeitech instrument identity, `ESU6.CME`, simplified IB symbology, realtime requested mode, `use_regular_trading_hours = false`, revised bars disabled, and one historical in-flight lane. This is local configuration intent, not proof of an exact IB `conId`, entitlement, returned market-data mode, or provider acceptance.

The active live requirement is `5-SECOND-LAST-EXTERNAL`; the enabled historical dependency is `5-MINUTE-LAST-EXTERNAL`, `recent_completed`, bounded to two-to-60 observations. Quote acquisition exists as a conditional capability but is not active for this profile, and quote-quality metrics are disabled.

Provider-facing lifecycle states have exact bounded meanings:

- `REQUESTED`: demand registered;
- `ACCEPTED`: local demand accepted/coalesced;
- `SUBSCRIBED`: the native subscription command returned without immediate exception;
- `ACTIVE`: the first matching native observation was seen;
- `COMPLETED`, `FAILED`, `CANCELED`, or `EXPIRED`: separate terminal/failure outcomes.

`SUBSCRIBED` is not provider acknowledgement. `ACTIVE` is not entitlement, completeness, continuity, or analytical usability. The current actor has no autonomous acquisition-owner retry loop for failed live subscriptions; the coordinator can retry only when another reconciliation trigger occurs.

Official IB material verifies provider capabilities such as watchlist data, five-second real-time bars, historical requests, callbacks, market-data modes, entitlements, lines, pacing, and errors. It does not prove how the installed adapter maps this profile. Exact provider method names must therefore not label current runtime edges unless current-pin adapter evidence closes the mapping. Public provider facts, local configuration, installed adapter behavior, and connected measurement must be separate evidence classes.

### Historical request, callback, readiness, and release

The verified current logical flow is:

1. an analytical consumer publishes a versioned historical dependency demand;
2. acquisition compiles a deterministic request identity, deduplicates compatible consumers, applies bounded queue/concurrency/attempt policy, and issues native `request_bars`;
3. the IB/DataEngine boundary returns a sequence through `on_historical_bars(bars)`;
4. the current RC3 callback surface supplies no request or attempt identity, so the actor associates the callback with `active_request_ids[0]`;
5. acquisition validates bounded bar type/order/range/count conditions, publishes an immutable `MarkeitechHistoricalBatch`, execution events, and independent per-consumer readiness;
6. local release/cancellation expires ownership; native cancellation is currently a no-op and late callbacks may be ignored or misattributed.

The active profile’s single in-flight lane narrows but does not eliminate late-attempt correlation risk. `maximum_attempts = 1` means the active profile does not authorize a retry after a submitted request fails or times out. Pending historical scheduling is priority then request ID, not FIFO, and no aging policy is established.

Historical `READY` means only that the configured minimum observation count was reached after the implemented structural validation. It does not establish one bar per expected interval, gap-free market population, field validity, complete session coverage, provider completion/finality, or downstream fitness. A returned count of 60/60 is bounded run evidence, not a general completeness guarantee.

Historical and live bars are distinct lineage sources. IB states that historical data may be filtered, adjusted, compressed, or change between requests, so historical/live equality is not guaranteed. They converge through the `SessionMetricsActor` completed-bar ledger. Equal market/analytical content for the same `(instrument, bar specification, interval end)` is a duplicate; unequal content is a conflict. Transport lineage, timestamps, health/fidelity, evidence references, and revision are excluded from equivalence. First accepted content is retained; conflicts are counted and logged but are not currently published to the operational audit.

### Canonical native and custom data contracts

Native Nautilus observations remain canonical raw runtime data; Markeitech does not create raw wrappers. Current custom routing identities include:

- historical dependency demand, execution, readiness, and `MarkeitechHistoricalBatch`;
- `markeitech.completed_bar.input` (`CompletedBarInput`);
- `markeitech.metric.value` (`MetricValue`);
- `markeitech.entity.revision`, entity snapshot request, snapshot, and response;
- session state, evidence health, evidence snapshot request/response, and adaptive recency profile;
- acquisition status/stream, watchlist membership/lifecycle/demand, analytics demand;
- runtime resource and resource-health contracts;
- system health, component failure, persistence readiness, and acquisition status request.

For every contract, the manifest must distinguish literal signal/data-type identity, semantic owner, authorized publishers/consumers, transport, clocks, lineage, completeness, fidelity/health, reconciliation, retention, and limitations. A signal or `CustomData` carrier establishes in-process transport, not durability, replay, subscriber ordering, or delivery acknowledgement.

`CompletedBarInput` provides strong interval/content identity, historical/live/aggregate source, OHLCV, calendar/profile/trade-date/session/window data, observed/received/normalized clocks, health/fidelity, evidence references, completion/revision, and missing reasons. It has no explicit wire schema-version field. Its duplicate equivalence excludes lineage-related fields and must be documented exactly.

`MetricValue` provides metric/version, parameter version, instrument/session, effective/observed/received/calculated/published clocks, source, health/fidelity, evidence references, and a producer-supplied revision. It does not publish parameter source/effective time, analytical profile, calendar, trade date, schema version, or source-run identity. Full per-value reproducibility must not be claimed.

`EntityRevision` has deterministic identity, definition/profile/instrument/dimensions, parameter/schema versions, positive revision and previous-revision link, typed evidence references, health/fidelity, and bounded state-book conflict/gap behavior. It has no receive time or source-run identity. Entity snapshots are bounded sorted current-state projections, not full histories, complete reconstruction, or durable storage.

### Session, calendar, and evidence health

UTC nanoseconds are internal time; IANA zones and calendar/session/trade-date identity remain explicit. The tracked profile declares `America/Chicago` and `schedule_version = "pmc-5.4"`, but that version is published metadata not verified against the installed calendar definition. Its empty phase set produces one broad provider `OPEN` envelope and does not model the CME maintenance break. Exact date/session coverage therefore requires dated calendar/venue evidence and cannot be inferred from the static profile alone.

Evidence health is receive-time based, session-aware, versioned, and independent of fidelity. It represents source availability/recency, not downstream evidence fitness. The current `on_bar` path maps an instrument’s bar to each configured bar-health key for that instrument regardless of selector, and equal event timestamps refresh receive time. The tracked profile’s single bar selector avoids proving a current collision, but generalized selector-specific health is blocked for profiles with multiple bar selectors until source/test evidence changes.

### Event delivery, queues, workers, projections, and failure isolation

The manifest must model separate milestones rather than generic arrows:

- publication versus owner acceptance;
- native command issued versus provider observation;
- queue admission versus worker processing versus stored result;
- HTTP 2xx versus operator receipt;
- file staging versus atomic publication;
- local component failure versus global health transition versus process/run termination.

No current end-to-end exactly-once or global-order guarantee is established. Current RC3 subscriber ordering, message-bus capacity/backpressure, callback scheduling, adapter reconnect/resubscribe behavior, and native shutdown order remain unknown. Actor registration order must never substitute for these semantics.

Observed in-process boundaries include:

- operational persistence: bounded pending queue with critical reserve, unbounded result queue, worker thread, asynchronous result handling;
- Discord: two independent bounded pending queues/workers and two unbounded result queues; one HTTP attempt, optional and disabled in the tracked profile;
- visual debug: capacity-one job and result boundaries, staged directory publication, passive and enabled;
- historical coordinator: bounded outstanding/in-flight policy, one active lane in the profile, timeout/cancel limitations;
- timers for startup queries, evidence snapshots, demand retry/attachment, health evaluation, resources, and projection quiet/deadline behavior;
- resource actor/health state using bounded configuration/state, disabled in the tracked profile.

Persistence is an asynchronous projection from local signal fan-out. Producers and other consumers do not wait for storage. Queue admission is not storage, and no storage acknowledgement returns to the original producer. Persistence failure can emit a component failure that SystemControl uses for global degradation/failure; Discord and visual-debug failures remain isolated projections. Historical readiness remains per consumer. No generic actor-restart policy or recovery-to-READY contract is implemented.

PostgreSQL currently stores approved operational facts and compact evidence recency, not raw quotes, ticks, bars, historical batches, `CompletedBarInput`, `MetricValue`, `EntityRevision`, or completed-bar conflict records. Static source shows application queue/write/retry paths and conflict clauses. By Markeitect decision, the diagram stops at that verified application write boundary; database transaction, commit ambiguity, durability, schema recovery, retention, and run-closure mechanics remain explicitly unknown.

### Authority conflict: persistence readiness

Current code publishes and consumes `markeitech.persistence.ready.request` and `markeitech.persistence.ready` in system control, acquisition, watchlist, persistence, and entity startup paths. `docs/current-status.md` and accepted `docs/architecture/v2-actor-composition-discovery.md` say immutable preflight prerequisites replaced or removed the transient readiness signal.

The current-runtime diagram must show the implemented handshake because code is runtime truth, but attach a structured `authority_conflict` that cites the contrary accepted documents. It must not silently decide that the documents are stale or that the implementation is wrong. Markeitect must decide the reconciliation in a separately reviewed batch; until then, generated limitations and the accessible companion must expose the conflict.

### Future, removed, rejected, external, and unknown boundaries

The current-runtime view must exclude removed, rejected, disabled-for-profile, and future behavior. The complete inventory may include them in separated status bands. Provider, PostgreSQL, Discord, operator, filesystem, future agents, and future execution are external or separate boundaries, not composed actors.

Future Sir Loke, semantic events, opportunities, options intelligence, ML, richer analytics, analytical persistence, and controlled execution may appear only as explicitly `future`/`not implemented`. Future execution must never connect to current flows with ordinary current styling. A separate future-governed-boundaries view is safer than mixing it into current topology.

## Diagrams and Graphviz capability assessment

### Sources and current identities

Official/upstream material was accessed on 2026-08-30, beginning with the required [Diagrams installation page](https://diagrams.mingrammer.com/docs/getting-started/installation). The assessment also used the current [Diagram](https://diagrams.mingrammer.com/docs/guides/diagram), [Node](https://diagrams.mingrammer.com/docs/guides/node), [Edge](https://diagrams.mingrammer.com/docs/guides/edge), [Cluster](https://diagrams.mingrammer.com/docs/guides/cluster), [Custom node](https://diagrams.mingrammer.com/docs/nodes/custom), [C4](https://diagrams.mingrammer.com/docs/nodes/c4), [generic](https://diagrams.mingrammer.com/docs/nodes/generic), [programming](https://diagrams.mingrammer.com/docs/nodes/programming), [on-premises](https://diagrams.mingrammer.com/docs/nodes/onprem), and [SaaS](https://diagrams.mingrammer.com/docs/nodes/saas) pages; exact `v0.25.1` source and project metadata; Graphviz [documentation](https://graphviz.org/documentation/), [outputs](https://graphviz.org/docs/outputs/), [layout engines](https://graphviz.org/docs/layouts/), [attributes](https://graphviz.org/doc/info/attrs.html), [splines](https://graphviz.org/docs/attrs/splines/), [ordering](https://graphviz.org/docs/attrs/ordering/), [fonts](https://graphviz.org/docs/attrs/fontname/), [source releases](https://graphviz.org/download/source/), and [license](https://graphviz.org/license/).

Current upstream identities observed:

- Diagrams `0.25.1`, released 2025-11-22, MIT-declared.
- Diagrams exact release metadata requires Python `~=3.9` and Python `graphviz >=0.13.2,<0.21.0`, plus Jinja2 and an unexpectedly broad `pre-commit` dependency.
- Current Graphviz source page lists `15.1.1`; Graphviz is EPL-2.0.
- Current Diagrams documentation says Python 3.7+, while the current repository README says 3.9+ and exact `v0.25.1` metadata says `~=3.9`. Exact release metadata governs a pin; the documentation mismatch must be recorded.
- No `dot` executable, Python `diagrams`, or Python `graphviz` package is installed in this worktree environment. No local render, font, plugin, format, layout, or determinism behavior was verified. No installation occurred.

### Diagrams capabilities and limits

Diagrams provides a Python API around Graphviz. A project-owned CLI is required; no general TOML/diagram CLI should be assumed. Relevant capabilities include:

- explicit diagram filenames and `show=False`;
- `png`, `jpg`, `svg`, `pdf`, and `dot` output formats, including multiple formats;
- diagram direction and graph/node/edge attribute maps;
- generic, programming, on-premises, SaaS, C4, provider/resource, and custom nodes;
- local custom icons;
- directed `>>`/`<<`, undirected `-`, labeled, colored, and styled edges;
- grouped/list edge syntax and optional Graphviz edge concentration;
- clusters and nested clusters;
- Graphviz layout and routing controls through attributes.

Important limitations:

- Diagrams is code-first. The proposed TOML translation layer must create explicit objects; it must never evaluate Python expressions from TOML.
- Python operator precedence can change mixed edge expressions. The renderer must create one explicit edge at a time and never generate chained expressions.
- List grouping cannot connect two lists and can obscure identity. It should not define semantics.
- Edge merging/concentration may erase distinct contracts, optionality, direction, or transport. It is forbidden unless an explicit manifest presentation group preserves and lists every member in the accessible companion.
- Clusters support nesting, but unlimited technical depth is not readable. Per-view limits must be measured and approved.
- Exact `v0.25.1` defaults differ from current master/docs: release code defaults to orthogonal curves and restricts accepted curve-style values, while current source/docs expose newer spline behavior. The exact pinned release must be tested.
- Orthogonal routing interacts poorly with ports and edge labels. The implementation spike must measure `dot` plus approved splines on representative views rather than assuming a documentation example will work.
- `Node` defaults to UUID4 IDs. Every node must receive its stable manifest ID as `nodeid`; otherwise DOT and layout diffs are nondeterministic.
- Cluster identity is derived from labels in the release API. The adapter must enforce unique stable cluster labels/names or use an explicitly tested lower-level construction; duplicate visible labels cannot silently collide.
- The `Diagram` context manager renders on exit, and `render()` delegates to Python Graphviz without an explicit sanitized environment boundary. It is unsuitable as the atomic publication/security boundary.
- Packaged provider icons can introduce absolute environment paths into DOT and bring separate trademark/license questions. Shape-only generic nodes are recommended for the first release.
- Large graphs become unreadable and layout-sensitive. View budgets must fail visibly rather than silently shrink, omit, merge, or repartition content.

### Graphviz capabilities and limits

Graphviz `dot` is the natural initial engine for layered directed flows. Relevant controls include `rankdir`, subgraph rank, `ordering`, `splines`, `compound`, edge `constraint`, `concentrate`, node/edge separation, margins, and format-specific rendering.

Use only a closed, code-owned allowlist of engines and attributes. The TOML may choose among approved symbolic presentation values; it must not provide arbitrary Graphviz attributes, executable paths, commands, URLs, HTML labels, `href`, `stylesheet`, `fontpath`, `shapefile`, or uncontrolled image paths.

Output tradeoffs:

| Format | Decision | Strength | Limit |
|---|---|---|---|
| SVG | Required; primary visual | Scalable inspection, selectable text, browser zoom, linkable structure | Layout/font/browser differences; not a complete accessibility tree; must contain no active external reference or host path |
| PNG | Required; review image | Immediate preview and stable snapshot under pinned toolchain | Raster density and platform/font variation; never sole acceptance artifact |
| DOT | Required; structural debug | Inspectable graph identity, nodes, edges, clusters, and attributes | Raw order/coordinates are not architecture authority; must be normalized and free of absolute paths |
| Markdown | Required; accessible companion | Deterministic non-spatial equivalent from the same selected model | Not a visual artifact; must be count/identity-equivalent to the view |
| PDF | Optional, deferred | Print/review convenience | Adds output/plugin/QA surface without being necessary for first acceptance |

Graphviz output formats and render plugins vary by build. Fonts, font substitution, OS libraries, Graphviz version, and browser rendering affect geometry and bytes. The portable hard invariant is **semantic determinism**: identical validated inputs select the same identities, statuses, contracts, and normalized structural model in the same order. Byte-identical DOT/SVG/PNG is a narrower claim only for an exact pinned toolchain/font/platform after repeated measurement.

### Licensing and asset decision

Diagrams is MIT-declared and Graphviz EPL-2.0, but approval is still required for their complete locked dependency/native supply chains and notices. Provider logos, bundled icons, trademarks, fonts, and custom icons have separate terms. The first implementation should use shape-only generic nodes and project-owned text labels. Any later local asset requires:

- tracked regular file under an approved asset root;
- exact source, author/owner, license, permitted-use decision, attribution/notice obligations;
- content hash, approved format and byte/dimension limits;
- non-symlink validation and no external URI;
- accessible text label independent of the icon;
- separate Markeitect approval, with legal/licensing input when appropriate.

No “all bundled icons are covered by the Diagrams license” claim is admissible.

## Recommended authority and alignment model

### Truth domains

| Domain | Owner | What it proves | What it does not prove |
|---|---|---|---|
| Runtime/code truth | Current reviewed checkout, configuration, and bounded runtime evidence | Implemented symbols, composition logic, call sites, profile values, and specifically measured behavior | Architectural correctness, full provider semantics, or that every semantic change is statically discoverable |
| Architectural-manifest truth | Markeitect-approved TOML | Reviewed component/contract/edge/status/evidence representation and all diagram presentation metadata | It does not configure, execute, introspect, or automatically become correct when code changes |
| Generated-artifact truth | Validated manifest plus accepted generator/toolchain | Exact derived view selection and rendering for a recorded input/tool identity | Runtime behavior, manifest semantic correctness, or live currency by generation time alone |
| Historical truth | Git history and accepted dated records | Prior decisions, removed/rejected/future records, bounded connected evidence | Current runtime unless reconciled against current checkout and authority precedence |

The TOML is canonical only for architectural diagram representation. It must declare `not_runtime_configuration = true`. Runtime code/configuration never reads it. The validator never imports runtime code. Generated images never feed the manifest.

### “Always aligned” contract

Alignment is a repository process with layered evidence:

1. The same reviewed batch updates the manifest whenever it changes a component, responsibility, authority, condition, contract, transport, persistence, projection, worker/process/failure boundary, or flow.
2. A static fail-closed census compares supported code/configuration structures and literals to manifest expectations.
3. Architecture-sensitive path changes require a manifest change or a narrow, audited, expiring exception.
4. A clean regeneration must reproduce the complete tracked artifact set with no diff.
5. Reviewers inspect the manifest diff before artifact diffs and remain accountable for semantics and omissions.
6. Rebase/merge changes require revalidation and regeneration.

This can mechanically detect many omissions and stale artifacts. It cannot prove that a responsibility description is correct, that an unseen dynamic path is absent, that a provider delivered, or that a view creates no misleading implication. Those remain reviewer-owned.

## Recommended versioned TOML schema

### Design principles

- One canonical tracked TOML file contains every diagram fact and every presentation choice.
- No Python expressions, imports, commands, environment interpolation, secrets, host paths, runtime values, or duplicated business logic.
- Exact unknowns are valid values; consequential blanks are not.
- Stable IDs are independent of labels and Python class names.
- Status is multi-axis, not one overloaded enum.
- Evidence is typed by class and limitation; a source path is not runtime acceptance.
- View filtering is declarative and validated; the renderer does not infer architecture.
- Closed enums and bounded records replace arbitrary Graphviz attributes.
- Schema changes require explicit version migration and review; unknown keys fail.

### Top-level record families

The initial schema should contain:

- `[manifest]`: schema version, identity, title, description, scope, authority, `not_runtime_configuration`, checkout evidence, owner, review status/effective date, generator contract, default profile, limitations.
- `[[evidence]]`: stable evidence ID, class, repository path, symbol/key/section, commit/blob identity where useful, observed date, what it proves, what it does not prove.
- `[[profiles]]`: named tracked configuration path/hash, schema, purpose, evaluated state, limitations. Never use an unnamed “active” profile.
- `[[boundaries]]`: process/engine/actor/worker/queue/provider/persistence/operator/future boundary hierarchy.
- `[[components]]`: stable identity, labels, kinds, logical areas, responsibilities, authority roles, implementation/composition/profile/temporal/acceptance states, config conditions, lifecycle, cardinality, failure isolation, persistence, style, evidence, limitations.
- `[[capabilities]]`: independently gated responsibilities inside a composed component, such as completed bars versus rolling/session windows.
- `[[contracts]]`: native/custom/signal/request/callback/queue/file/HTTP/database contract identity, schema, owner, producer/consumer, lineage, clocks, quality, reconciliation, retention, evidence.
- `[[delivery_claims]]`, `[[retry_policies]]`, `[[capacity_policies]]`, and `[[lifecycle_claims]]`: reusable bounded semantics referenced by edges.
- `[[edges]]`: stable source/target/category/carried contract/transport/authority/enablement/requiredness/delivery/style/evidence.
- `[[presentation_groups]]`: explicit human-approved edge grouping only; no automatic equivalence.
- `[[views]]`: named selection, profile, status filters, ordering, direction, layout engine, splines, formats, legend, accessibility companion, limitations, and reviewed complexity budgets.
- `[[styles]]`: closed semantic tokens mapped by the generator to code-owned safe Graphviz attributes.
- `[[tombstones]]`: retired stable IDs, status/reason/evidence, replacement link, and prohibition on reuse.
- `[[authority_conflicts]]`: unresolved code/document/record conflict with exact evidence and required decision.
- `[[drift_exceptions]]`: narrow reviewed exceptions with owner, exact rule/items, approval reference, expiry/removal condition, and limitation.

### Status and authority fields

Every component must separate at least:

- `implementation_state = implemented | removed | rejected | future | external | unknown`
- `composition_policy = always | conditional | not_composed | external | unknown`
- per-profile `enablement = enabled | disabled | not_applicable | unknown`
- `acceptance_state = accepted | bounded_evidence | unaccepted | rejected | not_applicable | unknown`
- `temporal_status = current | historical | future | unknown`
- `evidence_certainty = verified_source | measured_bounded | inference | hypothesis | recommendation | unknown`

Ownership must not be one vague “source of truth” string. Require separate nullable references for:

- semantic owner;
- mutation/state-transition owner;
- transport owner;
- persistence owner;
- recovery owner;
- projection owner;
- configuration/policy owner.

Each absent owner must be `not_applicable`, `none_current`, or `unknown`, not silently omitted.

### Contract, lineage, clock, and quality fields

Every consequential contract/stream should record:

- stable contract/stream ID and literal type/signal/callback/request/endpoint identity;
- schema/definition/parameter/configuration versions as separate dimensions;
- canonical instrument and selector/bar-specification identity where applicable;
- provider logical identity and adapter boundary, with runtime-secret/account identity explicitly excluded;
- parent contracts, transformation, evidence references, join key, expected cardinality, fan-out and multiplication risk;
- event, interval-start/end, receive, initialize, calculate, publish, evaluate, availability, and record clocks where present, with unit/source/ordering;
- IANA zone, calendar/version, phase, trade date, overrides, and limitations for session-sensitive data;
- health and fidelity vocabulary and exact meaning;
- completeness vector: request completion, temporal coverage, observation coverage, field validity, contract continuity, lineage completeness, and semantic suitability;
- duplicate/conflict/revision/correction/late/stale keys, excluded fields, first-accepted/supersession policy, and observable outcome;
- transient/durable retention, bound/eviction, destination, and policy authority;
- exact evidence class and claim limitations.

### Delivery and edge fields

Every edge should require:

- stable edge ID, source and target;
- category: `command`, `query`, `response`, `event`, `publication`, `subscription_command`, `native_observation`, `callback`, `readiness`, `release`, `control`, `persistence`, `notification`, `projection`, `timer`, `queue_admission`, `worker_result`, or `failure`;
- contract and transport;
- direction and authority direction;
- producer and authorized consumers;
- message/subject/request/attempt/correlation/causation/revision identity, explicitly allowing verified absence;
- sync/async as `verified_sync`, `verified_async`, `mixed`, `unknown`, or `not_applicable`;
- enablement/profile condition and required/optional state;
- delivery, ordering, retry, cancellation, capacity, lifecycle, and acknowledgement policy references;
- visual style token and optional explicit presentation group;
- evidence and limitations.

For schema version 1, `exactly_once`, `global_order`, `provider_confirmed_cancel`, `durable_before_publish`, and unqualified `delivered` should be forbidden values.

### Representative fragments

These are illustrative schema fragments, not a completed manifest and not approved values.

```toml
[manifest]
schema_version = 1
id = "markeitech-v3-system-dataflow"
title = "Markeitech V3 System and Data Flow"
description = "Offline reviewed architecture representation"
scope = "repository-controlled architecture documentation"
authority = "architecture_representation_only"
not_runtime_configuration = true
checkout_commit = "c6fe2ad89ae2da077d08c55998cc9ff639c5f0ce"
owner = "markeitect"
review_status = "proposed"
architecture_effective_at = "2026-08-30"
generator_contract_version = 1
default_profile = "v3-progressive-review"
limitations = [
  "No current order submission or execution",
  "Generated artifacts are documentation and never runtime input",
]

[[profiles]]
id = "v3-progressive-review"
config_path = "config/system.v3-es-minimal.toml"
config_schema_version = 18
content_sha256 = "<generated-during-approved-reconciliation>"
status = "tracked_profile"
limitations = [
  "Not proof of an ignored operator-local profile",
  "Calendar schedule metadata is not independently verified against current CME truth",
]
```

```toml
[[components]]
id = "actor.session-metrics"
label = "Session Metrics"
kind = "markeitech_actor"
logical_area = "data-processing-intelligence-state"
boundary = "boundary.nautilus-live-node"
implementation_ref = "src/markeitech/system/session_metrics.py:SessionMetricsActor"
actor_id = "SESSION-METRICS"
responsibilities = ["completed-bar admission", "configured metric publication"]
semantic_owner = "actor.session-metrics"
mutation_owner = "actor.session-metrics"
transport_owner = "component.nautilus-message-routing"
persistence_owner = "none_current"
recovery_owner = "actor.session-metrics"
projection_owner = "not_applicable"
policy_owner = "config.session-measurements"
implementation_state = "implemented"
composition_policy = "conditional"
temporal_status = "current"
acceptance_state = "bounded_evidence"
configuration_path = "session_measurements.enabled"
failure_isolation = "actor_local_with_structured_component_failure_when_implemented"
cardinality = "one_per_node"
style = "current-actor"
evidence = ["evidence.composition-source", "evidence.v3-profile-test"]
limitations = ["Component enablement does not enable every contained capability"]

[[components.profile_states]]
profile = "v3-progressive-review"
enablement = "enabled"

[[capabilities]]
id = "capability.session-metrics.rolling"
component = "actor.session-metrics"
label = "Rolling measurements"
implementation_state = "implemented"
composition_policy = "conditional"
configuration_path = "session_measurements.rolling.enabled"
profile = "v3-progressive-review"
enablement = "disabled"
```

```toml
[[contracts]]
id = "contract.completed-bar-input"
transport_kind = "nautilus_custom_data"
type_name = "markeitech.completed_bar.input"
python_symbol = "markeitech.intelligence.completed_bars.CompletedBarInput"
schema_version_kind = "none_explicit"
canonical_owner = "actor.session-metrics"
identity_fields = ["instrument_id", "bar_specification", "interval_end_ns"]
join_key = ["instrument_id", "bar_specification", "interval_end_ns"]
expected_cardinality = "one_accepted_value_per_identity"
event_clock = "interval_end_ns"
availability_clock = "normalized_ts_ns"
clock_unit = "unix_nanoseconds_utc"
source_classes = ["historical_provider", "live_native", "local_aggregate"]
equivalence_excludes = [
  "source", "observed_ts_ns", "received_ts_ns", "normalized_ts_ns",
  "health", "fidelity", "evidence_refs", "revision",
]
correction_policy = "first_accepted_reject_conflict"
retention = "bounded_transient"
limitations = [
  "Historical provider quality is assigned READY/REPORTED without population-coverage proof",
  "Conflicts are counted and logged but are not currently published to operational audit",
]
evidence = ["evidence.completed-bar-contract", "evidence.completed-bar-ledger"]
```

```toml
[[delivery_claims]]
id = "delivery.local-signal-transient-unknown-v1"
scope = "in_process"
transport = "nautilus_signal"
guarantee = "unknown"
replay = "none"
acknowledgement_milestone = "none"
ordering_scope = "unknown"
cross_producer_ordering = "unknown"
duplicate_possible = true
limitations = [
  "Publication is not consumer-effect acknowledgement",
  "Actor registration order is not delivery order",
]

[[edges]]
id = "edge.history-callback-to-acquisition"
source = "boundary.ib-nautilus-historical-callback"
target = "actor.data-acquisition"
category = "callback"
contract = "contract.nautilus-bar-sequence"
transport = "nautilus_data_callback"
correlation = "absent_at_actor_callback"
sync_semantics = "unknown"
delivery_claim = "delivery.provider-callback-unknown-v1"
ordering_claim = "ordering.historical-single-lane-v3-profile"
retry_policy = "retry.historical-v3-profile-one-attempt"
cancellation_policy = "cancel.historical-local-noop-rc3"
required = true
enablement_condition = "session_measurements.completed_bars.enabled"
authority_direction = "provider_observation_to_acquisition_owner"
style = "callback-unknown-correlation"
evidence = ["evidence.acquisition-on-historical-bars", "evidence.rc3-data-actor-stub"]
limitations = ["A late callback can be attributed to a newer active request"]
```

```toml
[[views]]
id = "current-runtime-topology-v3"
label = "Current Runtime Topology — Tracked V3 Progressive-Review Profile"
profile = "v3-progressive-review"
include_temporal_status = ["current"]
include_implementation_state = ["implemented", "external"]
include_profile_enablement = ["enabled", "not_applicable"]
exclude_acceptance_state = ["rejected"]
direction = "left_to_right"
layout_engine = "dot"
splines = "<pending approved render spike>"
formats = ["svg", "png", "dot", "md"]
theme = "markeitech-architecture-v1"
legend = "generated_from_used_tokens"
accessibility_companion_required = true
show_profile = true
show_limitations = true
no_execution_banner = true
max_nodes = "<pending measured and approved budget>"
max_edges = "<pending measured and approved budget>"
max_cluster_depth = "<pending measured and approved budget>"
```

Placeholders in representative fragments are not valid implementation values. The approved schema should require concrete reviewed values before generation.

## Validator and generator architecture

### Package boundary

Create a separate documentation-tool project rather than adding Diagrams to the active V2 runtime environment:

```text
tools/system-diagram/
  pyproject.toml
  uv.lock
  src/markeitech_system_diagram/
```

This project owns only offline parsing, source census, view projection, DOT construction,
controlled rendering, artifact publication, and its tests. It must not depend on the runtime
package.

### Load and normalize

1. Resolve the repository root from a code-owned invocation contract, not from manifest input.
2. Open the fixed canonical TOML path as a tracked regular non-symlink file under the repository.
3. Parse with standard-library `tomllib`.
4. Reject unknown keys, invalid enums, excessive sizes/counts/label lengths, secret-like/URI/absolute-path fields, and unsafe characters.
5. Convert to frozen typed dataclasses/enums and immutable sorted tuples/mapping proxies.
6. Normalize all identities and repository-relative evidence references.
7. Dispatch schema versions explicitly; never guess or silently migrate.

### Structural and semantic validation

Validate before creating a graph:

- unique stable IDs and non-reuse of tombstones;
- no dangling component, capability, boundary, contract, edge, owner, profile, policy, evidence, style, view, replacement, conflict, or exception references;
- acyclic boundary hierarchy and approved maximum nesting;
- exactly one canonical semantic/mutation owner where required, with separate transport/persistence/projection roles;
- legal multi-axis status combinations;
- no current view containing removed, rejected, future, or disabled-for-profile behavior;
- exact literals for type names, signals, callbacks, actor IDs, config keys, and schema versions;
- complete clock/lineage/quality/retention/delivery metadata or explicit typed unknowns;
- no persisted edge unless the approved application persistence mapping and specialist evidence support it;
- no forbidden delivery/order/cancellation/durability wording;
- no arbitrary Graphviz attribute, executable, HTML label, URI, remote font/image, or unapproved asset;
- view complexity and label budgets, failing with exact counts rather than changing the view;
- generated companion/visual identity-set equivalence.

### Static drift census

Use `ast`, `tomllib`, and bounded source text only. Never import or execute source. Initial supported checks should include:

- exact Nautilus pin in `pyproject.toml` and `uv.lock`;
- the whitelisted `LiveNode.builder(...).add_data_client(...).build()` and `add_actor_from_config(...)` shape in `node.py`;
- literal `ActorRegistration` keys, actor IDs, import/config paths, registration order, and explicit enablement conditions in `composition.py`;
- tracked profile schema and values through `tomllib`, evaluated only by closed declarative rules;
- literal signal and custom-data type constants, known publishers/subscribers, request/subscribe/unsubscribe calls, callbacks, timer registrations, and queue declarations;
- frozen dataclass field/enumeration shape for named custom contracts;
- persistence subscription/mapping presence for any claimed operational-audit edge;
- required profile limitations such as the single-selector health assumption and calendar debt.

Fail closed on an unrecognized registry, helper indirection, generated symbol, dynamic import, `getattr`, decorator, loop, or source shape. `NautilusSubscriptionPort` currently uses dynamic `getattr`; the census needs an explicit narrow rule tying literal `FeedKind` mappings to its protocol and tests. “Unsupported census shape” is a hard actionable failure, never a silent omission.

Source call sites prove only structural presence. They do not prove delivery, provider acceptance, timing, ordering, deduplication effects, persistence, or semantic ownership.

### View projection

The view selector operates only on the validated immutable model. It uses declared profile/status filters and explicit IDs/groups. It may order and group records deterministically; it may not infer missing edges, combine owners, upgrade unknowns, automatically partition a view, or reduce semantically distinct edges.

Each projected view produces one normalized semantic record containing the exact selected boundary/component/capability/contract/edge/policy/status/limitation IDs. SVG, PNG, DOT, and Markdown must derive from that same record. Identity/count parity is a hard gate.

### Diagrams adapter and controlled Graphviz boundary

The proposed adapter may use pinned Diagrams node/cluster/edge construction, but it must not use the context manager or `Diagram.render()` as the publication boundary. The implementation spike must establish a supported, tested way to obtain canonical DOT without rendering. It then must:

1. normalize and validate the DOT;
2. reject absolute paths, hyperlinks, external references, host/user data, unsafe attributes, and undeclared IDs;
3. resolve one approved Graphviz executable from code-owned approved locations or an explicitly reviewed CLI/run-configuration argument;
4. reject repository/home/temp executables and unsafe symlinks;
5. verify accepted executable version/identity;
6. invoke with an argument vector, `shell=False`, fixed staging `cwd`, minimal sanitized environment, fixed locale/timezone/hash seed, timeout, and capped/redacted output;
7. render only the code-owned approved formats.

If exact pinned Diagrams cannot expose deterministic DOT without its unsafe render path or host-specific icon paths, implementation must stop and return to Markeitect. Direct safe DOT construction through the Python Graphviz package is the leading alternative, but changing away from Diagrams is a plan revision requiring approval, not an automatic fallback.

### Atomic artifact publication

Generation must never leave a mixed or partial set:

1. create a staging directory beneath the fixed generated-output parent;
2. validate, project, and generate every approved view/format/companion;
3. reopen and validate every output; confirm identity counts, no external references/absolute paths, non-empty render, and expected format;
4. create deterministic `index.json` and `SHA256SUMS` containing only approved non-secret identities and hashes;
5. compare repeated normalized output where required;
6. atomically replace the prior complete generator-owned set only after every gate passes;
7. on failure, discard staging and leave the previous accepted set byte-identical.

Stale cleanup may remove only files named in the previous generator-owned index carrying the correct marker. Never recursively delete an arbitrary path or follow a symlink. Output filenames are derived from bounded stable view IDs, never arbitrary TOML paths.

Metadata should record manifest schema/hash, normalized-model hash, generator source/version hash, reviewed source commit, named profile path/hash, Python version, Diagrams version, Python Graphviz version, native `dot -V` identity, OS/platform and approved font identity, plus artifact hashes. Architecture effective/review time is distinct from generation time. Avoid nondeterministic wall-clock values in rendered content and hash-controlled metadata.

## Generated-view strategy

All views use the same three logical areas, with the third visibly renamed to avoid execution implications:

1. **System and infrastructure**
2. **Data acquisition, processing, metrics, intelligence, and state**
3. **Projections, advisory consumers, and future controlled boundaries**

Every standalone view includes: title, exact profile/scope, reviewed commit/effective date, status legend, limitations, generated marker, and “No current order submission or execution.”

### 1. Current runtime topology

- Named tracked V3 profile only.
- Shows the eight composed actors, `LiveNode`/native engine boundary, IB external boundary, in-process native routing/cache as useful, PostgreSQL operational audit, and enabled passive visual projection.
- Excludes disabled actors, removed/rejected actors, future agents/execution, and inactive capabilities within SessionMetrics.
- Shows registration order only in a separate numbered annotation if needed; never as a lifecycle/data-delivery chain.
- Exposes the persistence-readiness authority conflict.

### 2. Complete component inventory

- Includes implemented/always, implemented/conditional, profile enabled/disabled, diagnostics, removed/rejected tombstones, future/deferred, external, and unknown records.
- Uses separate status bands and status-count reconciliation.
- Uses few or no data-flow edges; inventory adjacency is not runtime flow.
- Shows component sub-capabilities independently from actor composition.

### 3. Provider-to-canonical-data flow

- Separates local demand, native command, external provider boundary, native observation/callback, acquisition lifecycle, historical batch/readiness, and canonical native/custom data.
- Shows provider and adapter facts with distinct evidence classes.
- Preserves historical/live lineage and one-lane callback limitation.
- Does not label exact IB methods, provider acknowledgement, entitlement, returned mode, gap-free completeness, revisions/cancellation, or general parity unless later evidence closes them.

### 4. Metrics, entities, intelligence, and state flow

- Shows accepted completed-bar input, current metric publication, evidence health, session state, and their exact owners/contracts.
- Separates enabled completed-bar foundation from disabled rolling/session-reference/session-window capabilities.
- Segregates disabled entity actors and future semantic events/Sir Loke/opportunities from current data flow.
- Does not turn dependency order into causality, confidence, opportunity ranking, advice, or trading meaning.

### 5. Persistence, operational audit, and external projections

- Shows signal fan-out → persistence actor → bounded pending queue → worker → PostgreSQL → internal result/log/failure as separate milestones.
- Shows the unbounded result queue truthfully and marks database mechanics as specialist-blocked.
- Lists what is not persisted: raw observations, historical batches, completed bars, metric values, entity revisions, and completed-bar conflicts.
- Shows console/logging, enabled visual debug, disabled Discord, operator, and future UI/agent as projections/consumers, never truth calculators.

### Optional 6. Future governed boundaries

Recommended if future Sir Loke and controlled execution must be visible. It must be a separate view with no ordinary current-flow continuation, prominent `FUTURE — NOT IMPLEMENTED`, explicit governance unknowns, and no suggestion of current order submission. If not approved, future execution appears only in the inventory.

### Visual grammar and accessibility

- Logical area: position and light cluster background.
- Component kind: stable shape and text; icons are supplementary or absent.
- Implementation/composition/profile status: explicit uppercase badges plus border/pattern; color is never the only cue.
- External boundary: double boundary plus `EXTERNAL`.
- Historical/removed: separate inventory band with explicit `REMOVED`/`REJECTED`.
- Future: dashed separate enclosure with `FUTURE — NOT CURRENT`.
- Unknown: explicit `UNKNOWN` text/symbol, not a plausible neutral default.
- Edge: arrow direction, exact category prefix (`CMD`, `QUERY`, `RESP`, `PUB`, `SUB CMD`, `CALLBACK`, `PERSIST`, `PROJECT`, `FAIL`), and line pattern; color is tertiary.
- Required/optional: text badge, not thickness alone.
- Canonical authority: explicit owner text/table column, not inferred from position.

WCAG 2.2 is the accessibility baseline. The generated Markdown companion is mandatory because Graphviz SVG geometry does not provide a reliable semantic reading order. Companion and visual must contain the same selected identity set, statuses, limitations, and legend. Human acceptance includes browser inspection, keyboard/screen-reader use of the companion, normal/200%/400% zoom, grayscale and common color-vision simulations, contrast, clipping/overlap/crossing/arrow ambiguity, and readable output dimensions.

Numeric view budgets must be measured with real census fixtures during an approved implementation spike and then approved by Markeitect. Exceeding a budget fails with the view ID and counts; the renderer must not shrink text, remove labels, merge edges, omit nodes, change layout, or create unapproved subviews automatically.

## Drift-detection strategy and honest limits

### Mechanically verifiable

- TOML syntax, exact schema, unknown keys, closed enums, size/count/path limits.
- Duplicate IDs, tombstone reuse, dangling references, owner conflicts, illegal status combinations, boundary cycles.
- Exact source paths/symbols/constants/config keys and supported AST shapes.
- Actor roster, IDs, registration source order, import/config mappings, and evaluated conditions for named tracked profiles.
- Contract dataclass fields/enums/type-name/signal literals and supported publisher/subscriber/callback/request call sites.
- Queue declarations/capacity classifications and timer registrations named by the manifest.
- Copied tracked-profile values and content hashes.
- Current-view exclusion of disabled, removed, rejected, and future records.
- Presence of required lineage/clock/completeness/reconciliation/retention/delivery fields or typed unknowns.
- Prohibition of exactly-once/global-order/provider-ack/durable-before-publish claims.
- Claimed persistence mapping exists in the application source; the diagram makes no database-internal claim beyond that application boundary.
- Changed architecture-sensitive paths are accompanied by a manifest change or audited exception.
- Complete artifact generation, visual/companion identity parity, hashes, no host/external references, and clean regeneration diff.
- Artifact-only manual edits and manifest/artifact hash mismatches.

### Reviewer-owned and not honestly mechanizable

- Whether responsibilities, owners, source-of-truth boundaries, and omissions are semantically correct.
- Whether a source change outside known paths changes architecture.
- Whether dynamic code or provider behavior matches a static call site.
- Runtime delivery, ordering, scheduling, provider acknowledgement, completeness, entitlement, pacing, reconnect, cancellation, and callback semantics.
- Whether a transformation deserves its own component/contract or whether two names conceal duplicate authority.
- Fidelity, health, session, timestamp, revision, conflict, retention, and fitness meaning beyond encoded evidence.
- PostgreSQL durability, recovery, transaction, schema, and retention mechanics remain intentionally unknown by Markeitect decision.
- Whether a projection recalculates truth or a visual edge implies a stronger claim than its metadata.
- Accessibility, legibility, grouping, and whether omitted detail changes the reader’s conclusion.
- Approval of exceptions and unresolved authority conflicts.

### Architecture-sensitive change gate

The future local checker should classify changes to at least:

- actor composition, actor/config classes, `LiveNode` construction, adapters, subscriptions, requests, callbacks;
- configuration schema/default/profile values and conditions;
- signals, custom-data contracts, topics/endpoints if later added;
- acquisition, historical, session, evidence, metrics, entities, persistence, projections, workers, queues, timers, failure/shutdown behavior;
- accepted architecture/current-status documents that change represented meaning;
- diagram assets/styles/toolchain/generator itself.

If a sensitive change occurs, the manifest must change in the same batch. A narrow exception is allowed only as a manifest record with stable ID, exact changed files/items/rules, reason, owner, approval reference, expiry/removal condition, and explicit waived gate. Free-form skip flags, commit-message magic, and permanent blanket exclusions are forbidden.

The checker must not claim source completeness. New unsupported source structures fail closed and require the census rule and manifest to be reviewed together.

## Mandatory repository update procedure

This procedure should become repository authority only after Markeitect approves it and the implementation exists.

### Ownership and timing

- Markeitect retains final architecture and manifest acceptance.
- Each architecture-changing batch names one manifest editor and one semantic reviewer; they may be the same only if Markeitect accepts that review arrangement.
- Classification happens before implementation: does the batch add, change, rename, enable, disable, replace, or remove a component, capability, responsibility, owner, condition, contract, transport, topic/signal/endpoint/callback, request/response path, provider owner, persistence, projection, process/thread/queue/failure boundary, grouping, or flow?
- If yes, the canonical TOML changes in that same reviewed batch before completion.

### Stable identity rules

- Label/class/file rename with unchanged meaning preserves the stable ID and updates implementation/evidence references.
- Responsibility, authority, or semantic replacement creates a new ID and a `replaces` link; it does not quietly reuse the old ID.
- Removal/rejection creates a tombstone with reason, evidence, date/commit, replacement if any, and no current edges.
- Stable IDs are never reused for a different meaning.
- Future-to-current transition changes status only after implementation/current-status evidence and approval; planned existence is not runtime existence.

### Same-batch steps

1. Classify the architecture effect and affected named profiles/views.
2. Update components/capabilities/contracts/edges/policies/statuses/evidence/limitations and exact source/config anchors.
3. Reconcile newly discovered undocumented architecture explicitly; never hide it in a mass regenerated diff.
4. Run manifest syntax/schema/reference/security validation.
5. Run the fail-closed source/config/composition/contract census.
6. Run view selection and complexity validation.
7. Generate the complete artifact set atomically through the locked offline environment.
8. Review manifest diff first, then normalized model/DOT/Markdown, then SVG/PNG.
9. Run focused unit/integration/adversarial tests and deterministic regeneration checks.
10. Confirm the staged diff contains the manifest and expected generated set, with no artifact-only edit, secrets, data, logs, IDE-local state, or unrelated churn.
11. Record unresolved unknowns and any narrowly approved expiring exception.
12. Re-run validation/generation after rebase and after target-branch merge preparation.

### Reviewer responsibilities

The reviewer confirms:

- runtime, manifest, generated, and historical truth remain distinct;
- component/profile/status and future/removed presentation are honest;
- every consequential stream has one canonical owner and correct authority direction;
- registration/dependency/delivery/readiness/shutdown orders are not conflated;
- provider, lineage, persistence, failure, and projection limits are visible;
- current views exclude inactive/future behavior;
- generated images are never edited as authority;
- visual and accessible companions agree and are readable;
- exceptions are narrow, approved, and expiring.

### Local gates; CI excluded

- Local `validate`, `check-drift`, `generate`, and `check-generated` modes.
- The shared PyCharm configuration runs the same local gates with no secrets, database, Docker, `.env`, runtime invocation, network setup, or authenticated session.
- Staged-diff review must include the TOML and complete tracked artifact set.
- `Generate Sys Diagram` must fail on missing, extra, incomplete, or changed output.
- Markeitect review remains mandatory and is not delegated to automation.

### Exceptions, rollback, and regeneration

- An exception never allows unsafe runtime import, network/service access, arbitrary Graphviz attributes/commands, secrets, path traversal, or generated images as authority.
- Roll back runtime change, manifest, and generated artifacts together.
- If generation fails, retain the previous complete set and do not publish staging.
- After dependency/advisory/provenance problems, revoke generation by disabling/removing the run configuration in an approved batch; retain old artifacts only as clearly historical with recorded toolchain identity.
- After rebase/merge, regenerate because source commit/profile hash/tool inputs may change even when semantics do not.

## Proposed file layout

The layout below is the approved target. Stage 1 creates only the standalone project skeleton, schema/model/loader modules, and focused tests; later files remain deferred to their reviewed batches.

```text
docs/architecture/
  system-dataflow.toml
  generated/system-dataflow/
    current-runtime-topology-v3.svg
    current-runtime-topology-v3.png
    current-runtime-topology-v3.dot
    current-runtime-topology-v3.md
    complete-component-inventory.svg
    complete-component-inventory.png
    complete-component-inventory.dot
    complete-component-inventory.md
    provider-to-canonical-data.svg
    provider-to-canonical-data.png
    provider-to-canonical-data.dot
    provider-to-canonical-data.md
    metrics-entities-intelligence.svg
    metrics-entities-intelligence.png
    metrics-entities-intelligence.dot
    metrics-entities-intelligence.md
    persistence-audit-projections.svg
    persistence-audit-projections.png
    persistence-audit-projections.dot
    persistence-audit-projections.md
    index.json
    SHA256SUMS

docs/operations/
  system-dataflow-diagram.md

tools/system-diagram/
  pyproject.toml
  uv.lock
  README.md
  src/markeitech_system_diagram/
    __init__.py
    __main__.py
    cli.py
    models.py
    loader.py
    schema.py
    evidence.py
    source_census.py
    drift.py
    views.py
    diagrams_adapter.py
    graphviz_runner.py
    artifacts.py
    diagnostics.py
  tests/
    fixtures/
    test_*.py

.run/
  Generate Sys Diagram.run.xml
```

The future-governed view is approved as the sixth view. Any asset/license directory still requires separate approval. Exact module granularity may be reduced if the approved implementation remains clear and testable. No CI workflow is part of the approved design.

## Dependency and licensing decision

Recommendation: approve a **separate exact-locked documentation-tool environment**, not a `v2` dependency group and not the preserved root project. This keeps Diagrams, Python Graphviz, Jinja2, `pre-commit`, and native Graphviz outside the live runtime environment and makes prohibited-runtime-import tests meaningful.

The implementation spike verified and adopted Diagrams `0.25.1`, Python Graphviz `0.20.3`, Python `3.13.3`, and native Graphviz `15.1.1` in the separately locked documentation-tool boundary. The exact Python closure is recorded in `tools/system-diagram/uv.lock`; the native Graphviz identity is checked and recorded during each generation. The final uncommitted batch still requires Markeitect's dependency and license review before commit.

- complete lock/transitive review with hashes and current advisory check;
- verification under the project’s approved Python version rather than relying on the missing worktree-local `.venv`;
- native Graphviz executable origin/version/plugin/font review;
- license/notice review for MIT and EPL-2.0 components;
- confirmation that generation works offline after provisioning;
- representative security, determinism, and visual-regression spike;
- a decision on pinning or bundling fonts and supported local macOS environments.

Use shape-only nodes initially. Custom/bundled provider icons and trademarks are deferred until each asset has explicit provenance and permission.

## Deterministic-rendering rules

1. Stable manifest IDs become stable Diagrams/Graphviz node IDs; never accept UUID defaults.
2. Sort boundaries, nodes, ports, edges, policies, legends, limitations, and output index entries by stable declared order then ID.
3. Create explicit edges individually; never use operator chains or source-code list grouping.
4. Use one approved engine, fixed closed attributes, direction, ranks, splines, spacing, margins, DPI, and font identity per theme/view.
5. No automatic merging, concentration, reduction, partitioning, label removal, font shrinking, or layout fallback.
6. No wall-clock timestamp, username, hostname, absolute path, virtualenv path, random ID, environment value, or external resource in DOT/artifacts.
7. Normalize DOT and safe SVG metadata only through reviewed deterministic transforms that preserve semantics.
8. Record exact manifest/model/generator/Python/Diagrams/Python-Graphviz/native-Graphviz/platform/font identities.
9. Repeated generation under the exact accepted environment must match normalized semantic model and canonical DOT; exact artifact-byte claims require measured evidence.
10. Toolchain/font/engine changes intentionally invalidate visual baselines and require renewed review.
11. A binary hash is integrity evidence, not proof of semantic correctness.

## PyCharm `Generate Sys Diagram` design

The approved implementation must add a shareable project-level configuration at `.run/Generate Sys Diagram.run.xml`, named exactly **Generate Sys Diagram**. `.idea/` is ignored and must not be used.

Recommended exact contract:

- type: Python module run configuration;
- working directory: `$PROJECT_DIR$`;
- interpreter: the separately locked `tools/system-diagram` project environment, selected through the project SDK/path without hard-coding the main checkout’s absolute virtualenv;
- module: `markeitech_system_diagram`;
- arguments:

  ```text
  generate --manifest docs/architecture/system-dataflow.toml --output docs/architecture/generated/system-dataflow --check-drift
  ```

- parent environment inheritance disabled (`PARENT_ENVS = false`), with only fixed locale, timezone, hash, bytecode, and repository source-path values supplied;
- no env file, secrets, IB confirmation, Docker/PostgreSQL service, network setup, browser/viewer, runtime build, or before-launch runtime task;
- fixed safe environment only if required, such as `PYTHONDONTWRITEBYTECODE=1`, `PYTHONHASHSEED=0`, `TZ=UTC`, and a fixed locale, after platform verification;
- Graphviz executable identity supplied by code-owned approved configuration, never the TOML;
- exit zero only after validation, drift checks, complete atomic generation, output reopen/verification, and index/hash creation;
- exit non-zero for invalid TOML/schema, drift, unsupported source shape, missing/unsafe asset, missing/wrong Graphviz, timeout/non-zero native result, unsafe DOT/SVG, complexity violation, incomplete output, or publication failure.

The run configuration must operate from repository root and never use `uv run` in a way that silently resolves/downloads packages during generation. Dependency provisioning is a separate explicit development step.

## Tests and acceptance gates

### Unit and schema tests

- valid/invalid TOML, exact schema versions, unknown keys, enums, immutable normalized models;
- duplicates, dangling references, cycles, owner conflicts, status combinations, tombstones, replacements, conflicts, exceptions;
- clock domains/order, lineage/cardinality/fan-out, completeness vectors, reconciliation, retention, delivery policy requirements;
- forbidden delivery/order/durability/cancellation values;
- path traversal, absolute/URI/symlink/special/untracked/oversized files and output escapes;
- arbitrary Graphviz attributes, HTML/URL/image/fontpath/stylesheet/command injection;
- resource and complexity bounds.

### Source-census and drift tests

- actor plan order/conditions/IDs/import/config paths for tracked profiles;
- LiveNode builder/data-client/registration pattern;
- signal/type constants, contract fields/enums, publisher/subscriber/request/callback/timer/queue patterns;
- dynamic `getattr` subscription mapping narrow rule;
- copied profile values/hashes and single-selector limitation;
- persistence mapping required for any claimed durable edge;
- unsupported AST shapes fail closed;
- sensitive-path change requires manifest or audited exception;
- retired runtime audit excluded from current evidence.

### Offline/security tests

- static import graph forbids Markeitech runtime, Nautilus, dotenv, psycopg, HTTP/Docker/browser/viewer modules;
- canary `.env`, DSN, webhook, token, username, hostname, account ID, and absolute paths never appear in output or diagnostics;
- socket/network tripwire and Python audit-hook denial during generation;
- generation succeeds with network/package access disabled after exact provisioning;
- Graphviz path/version/symlink/PATH-hijack, missing executable, non-zero, signal, timeout, excessive output, malformed/incomplete format tests;
- sanitized environment, `shell=False`, fixed cwd, capped/redacted diagnostics;
- no active links/external resources/absolute package paths in DOT/SVG/metadata;
- failure injection at every stage preserves the prior complete output set;
- stale cleanup removes only prior indexed generator-owned files.

### Rendering and artifact tests

- stable node IDs and deterministic explicit-edge ordering;
- one semantic selected model feeds all formats;
- exact component/edge/contract/status/limitation count and ID parity between DOT/SVG/Markdown;
- every used style token appears in the legend;
- current view excludes disabled/removed/rejected/future records;
- complete artifact index/hashes and generated markers;
- repeated canonical model/DOT equality under exact toolchain;
- generated-diff check and artifact-only-edit rejection;
- toolchain change invalidates baseline.

### Behavioral claim fixtures

- `SUBSCRIBED` never renders as provider acknowledgement;
- `READY` never renders as live/analytical/provider readiness;
- historical callback correlation is absent and one-lane limitation visible;
- no active live-subscription retry loop;
- historical minimum-count readiness is not rendered as population completeness;
- first-accepted duplicate/conflict semantics and non-persisted conflict visible;
- persistence is asynchronous after fan-out, not durable-before-publish;
- unbounded result queues represented honestly;
- entity snapshots labelled bounded current state, not history;
- future/removed elements cannot enter current-flow geometry;
- persistence-readiness authority conflict remains visible until resolved.

### Human visual acceptance

For every view:

- inspect SVG and PNG at normal scale; SVG at 200% and 400%;
- no clipped/overlapping labels, titles, legends, nodes, edges, arrowheads, or boundaries;
- no edge through a node and no ambiguous endpoint/crossing;
- statuses and flow categories remain distinguishable in grayscale and common color-vision simulations;
- approved contrast and minimum text size;
- visible scope/profile/review/limitations/no-execution banner;
- Markdown companion keyboard/screen-reader review and exact semantic parity;
- supported macOS browser inspection with OS/browser/font/device-scale/Graphviz/Diagrams identity recorded;
- unexplained baseline changes fail; baselines are never bulk-updated automatically.

### Acceptance levels

1. **Schema acceptance:** typed manifest and fixtures, no rendering dependency required.
2. **Census acceptance:** static reconciliation against the current checkout, fail-closed limits reviewed.
3. **Toolchain acceptance:** exact lock/native Graphviz/security boundary approved.
4. **Render acceptance:** deterministic complete formats and atomic publication.
5. **Semantic acceptance:** Markeitect approves census/authority/status/limitations.
6. **Visual/accessibility acceptance:** every view passes human review.
7. **Repository-process acceptance:** local/PyCharm/update/rollback procedure works.
8. **Merge acceptance:** separately approved only after all above and review of the complete uncommitted batch.

No connected IB, PostgreSQL, Discord, Docker, live runtime, or provider-data run belongs to these gates.

## Staged implementation sequence

The stages remain ordered engineering boundaries, but Markeitect removed intermediate approval pauses. Continue through them without committing and present the complete runnable diagram system for final review.

### Stage 0 — decisions complete

- Markeitect approved the decision record in this report.
- The PostgreSQL specialist consultation was declined; database-internal claims remain unknown.
- The implemented persistence-readiness handshake will be shown with a documentation-conflict limitation; reconciliation is deferred.
- The feature branch and starting state were confirmed before Stage 1.

### Stage 1 — standalone tool skeleton and schema models

- Add separate `tools/system-diagram` project and exact schema/frozen models.
- Add parser, diagnostics, path/security ceilings, representative fixtures, and unit tests.
- No Graphviz/Diagrams rendering yet.

### Stage 2 — source census and drift checks

- Add fail-closed AST/TOML evidence checks for composition, node boundary, profiles, contracts, queues/timers, and persistence mappings.
- Add sensitive-change classification and audited exceptions.
- Validate against fixtures/current source without runtime imports.

### Stage 3 — candidate toolchain and safe render spike

- After explicit dependency/native-tool approval, add exact lock.
- Prove safe DOT extraction from pinned Diagrams, stable IDs, controlled Graphviz invocation, no host paths/network, and deterministic representative output.
- Stop and revise the plan if Diagrams cannot meet the atomic/security boundary.

### Stage 4 — canonical manifest reconciliation

- Build the actual manifest from reviewed current evidence in logical slices.
- Reconcile actor/profile inventory first, then native/provider/contracts, metrics/entities, persistence/projections, removed/future/unknowns.
- Keep every slice reviewable; do not auto-generate semantic truth from code.

### Stage 5 — views, artifacts, and accessibility

- Add declarative view selection, style grammar, legends, Markdown companions, complexity budgets, and complete atomic publication.
- Generate initial SVG/PNG/DOT/Markdown/index/hash set.
- Perform visual/accessibility review and iterate only through TOML/generator changes, never manual artifact edits.

### Stage 6 — repository procedure and PyCharm

- Add operations document, exact `Generate Sys Diagram` run configuration, generated-diff and sensitive-change checks.
- Verify no `.env`, parent environment, runtime task, service, viewer, or network dependency during generation.

### Stage 7 — final offline acceptance and integration review

- Run focused/full offline tests proportional to risk, security/adversarial suite, repeated deterministic generation, artifact diff, visual/accessibility acceptance, and `git diff --check`.
- Inspect final worktree for secrets, data, logs, dependency spillover, IDE-local state, and unrelated churn.
- Leave uncommitted for Markeitect’s final review.
- Commit only after explicit approval; merge to `v3-es-progressive-capability-review` only after separate explicit merge approval; do not delete the feature branch without separate approval.

## Rollback boundary

The complete diagram system is removable without runtime migration because runtime code and configuration never consume it. A rollback batch removes or reverts the standalone tool, manifest, generated artifacts, documentation, and run configuration together while leaving V2 runtime source/configuration untouched.

Within normal architecture batches, roll back the runtime/code change, manifest change, and generated artifacts together. Never retain a diagram that claims a reverted component/flow. Failed generation leaves the previous complete artifact set untouched. Dependency or security revocation disables local generation first; previously generated artifacts may remain only as explicitly historical with their recorded toolchain/manifest identity.

No database migration, provider action, runtime restart, or service rollback is part of this utility.

## Treatment of any existing manual diagram

The original checkout’s untracked `docs/architecture/current-system-dataflow.png` is intentionally absent here and was not evidence. If a copy later appears:

- do not import it into the manifest;
- do not reverse-engineer architecture facts from it;
- do not use it as a visual baseline or source of truth;
- do not overwrite or delete it without a separately reviewed decision;
- classify it as non-authoritative historical/manual material;
- generate the new artifact set under the dedicated generated directory with unmistakable markers.

All future diagram changes occur through reviewed TOML or generator/schema changes. Generated SVG/PNG/DOT/Markdown must never be edited manually.

## Risks, unknowns, alternatives, and unresolved decisions

### Material risks and unknowns

1. **Intentionally bounded persistence representation:** database durability/transaction/recovery/schema/retention/run-closure mechanics remain unknown because Markeitect declined the specialist consultation.
2. **Persistence-readiness authority conflict:** current code and accepted documents disagree.
3. **Toolchain portability:** the accepted local toolchain is measured and exact, but a fresh machine still needs the locked Python environment and approved Graphviz `15.1.1` installed before it can generate.
4. **Diagrams release/docs drift:** Python and curve-style contracts differ between exact release and current docs/master; the implementation therefore pins and validates Diagrams `0.25.1` instead of assuming the current documentation describes another release.
5. **Safe Diagrams integration:** the implementation extracts canonical DOT without using Diagrams' eager rendering context and invokes Graphviz through a constrained subprocess; any future library integration change must repeat the isolation tests.
6. **Native Graphviz supply chain:** binary/plugins/fonts remain outside the Python lock and retain host-level provenance; the exact native version and resolved font limitation are recorded in the artifact index.
7. **Cross-platform determinism:** byte-identical graphics across OS/font/tool versions are unproven; semantic determinism is the honest portable invariant.
8. **Static-census incompleteness:** dynamic code and new source shapes can evade a narrow checker unless it fails closed.
9. **Provider unknowns:** exact IB qualification, entitlement, returned mode, adapter mapping, timestamp provenance, gap/correction/cancellation behavior remain limited.
10. **Historical correlation:** current callback has no request/attempt identity and cancel is no-op.
11. **Delivery unknowns:** no global order, exactly-once, bus capacity, replay, or general recovery guarantee.
12. **Queue/shutdown debt:** unbounded result queues and retry budgets may outlast shutdown budgets.
13. **Lineage gaps:** historical completeness, metric parameter provenance, conflict audit, multi-selector health, calendar identity, and snapshot history are limited.
14. **Visual scale:** actual census may exceed readable budgets; measured subviews may be needed with approval.
15. **Asset rights:** provider icons/trademarks/fonts are not approved.
16. **Operator profile:** ignored local configuration is unavailable; named tracked profiles are not universal runtime truth.
17. **Stale records:** accepted roadmap/document headers may lag current status; evidence precedence/date/commit must remain explicit.

### Alternatives considered

| Alternative | Disposition | Reason |
|---|---|---|
| One everything graph | Reject | Unreadable and collapses profile/status/future distinctions. |
| Hand-edited PNG/SVG/DOT | Reject | Creates a competing source and silent drift. |
| Generate directly from live runtime/introspection | Reject | Violates offline boundary, depends on environment/provider state, risks services/secrets, and confuses observed instance with architecture. |
| Make TOML drive runtime composition | Reject | Inverts authority and duplicates business/configuration logic. |
| Generate all semantics automatically from source | Reject as sole method | Source extraction cannot decide responsibility, canonical authority, provider meaning, omissions, or visual honesty. |
| Diagrams + controlled Graphviz | Recommended candidate | Good node/cluster abstraction and catalogs if safe deterministic DOT extraction is proved. |
| Direct Python Graphviz/DOT generation | Conditional fallback | Smaller/more controllable render boundary, but deviates from the proposed Diagrams approach and requires plan revision/approval. |
| Mermaid | Not recommended for this scope | Easier text diffs but weaker control over large multi-view architecture layout, local render identity, and required node/boundary grammar; still requires renderer/toolchain governance. |
| C4-only model | Not sufficient | Useful component context but cannot by itself express the required stream, contract, lineage, delivery, profile, and persistence detail. |
| Store generated artifacts only in CI | Not recommended initially | Weakens local review and generated-diff evidence; tracked artifacts support repository review when complete and size-bounded. |
| Add Diagrams to V2 dev group | Reject recommendation | Enlarges the live project environment and weakens offline import/supply-chain separation. |

## Final review gates after implementation

The architecture and implementation approach are approved as recorded above. Implementation is complete and uncommitted; these items remain for Markeitect's final local review:

1. Review the complete dependency lock, transitive supply chain, advisories, and license notices with the final uncommitted batch.
2. Review the measured per-view node, edge, cluster-depth, label, contrast, and output-size budgets against the generated results.
3. Approve any local icon/font/trademark asset separately; the initial design remains shape-only.
4. Review the populated canonical manifest and every current/conditional/disabled/removed/future classification.
5. Review the complete tracked SVG/PNG/DOT/Markdown/index/hash artifact set after visual and accessibility verification.
6. Review the final shared PyCharm run configuration after its environment isolation is verified.
7. Approve each narrow drift exception explicitly; none is pre-authorized.
8. Approve final commit and, separately, merge to `v3-es-progressive-capability-review`. Branch deletion remains separately gated.

## Implementation outcome and phase status

Phase 1 discovery and planning completed without runtime or connected action. On 2026-08-30 Markeitect approved the decision record, authorized implementation, and later removed intermediate stage-approval pauses. The uncommitted implementation now includes the canonical manifest, strict typed loader/schema, bounded source/configuration drift census, exact locked documentation environment, controlled Graphviz renderer, atomic complete-set publication, six generated views, ten configuration-gated subcapability records, per-view accessible Markdown companions, measured view budgets, tests, repository maintenance procedure, and the shared **Generate Sys Diagram** PyCharm configuration.

The final implementation uses shape-only Diagrams C4 nodes/boundaries/relationships, Graphviz-native escaped HTML card labels, no custom assets, and the manifest-selected **Markeitech polished dark theme v2**. Its provenance/legend strip, declared nested boundaries, compact status cards, kind-specific shapes, opaque near-black canvas, dark semantic fills, high-contrast text/borders, thicker semantic edges, redundant shapes, explicit status text, and dashed/dotted styles preserve meaning without relying on hue. Automated WCAG contrast and HTML-escaping checks cover every declared text and meaningful graphical pairing; Markdown companions remain viewer-themed semantic records rather than embedding a second CSS authority. Repeated fixture generation is byte-identical under the installed accepted toolchain; the portable guarantee remains semantic determinism with exact tool identities recorded. Visual inspection covered all six PNG outputs and their scalable SVG equivalents. No Markeitech/Nautilus runtime import, `.env`, credential, provider, PostgreSQL, Discord, Docker, network, operational-data, or live-state access occurs.

The report's planned narrow translation layer was retained. The only measured presentation refinements were manifest-owned packing/direction/budget values and deterministic layout-only invisible constraints for the edge-free inventory view. These constraints carry `layout.*` identities in DOT and do not appear as semantic edges or in the accessible companion.

The final offline gate passed 26 focused tests, a clean-parent-environment generation, complete hash verification for all 26 outputs, repeat-generation byte equality under the recorded toolchain, and measured output-size ceilings for every view. Commit, push, PR, merge, and branch deletion remain outside this authorization. Final dependency, manifest, generated-artifact, accessibility, and visual acceptance now belong to Markeitect's local review.
