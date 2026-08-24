# Markeitech V2 Infrastructure Plan

**Status:** Foundation established; all later stages require Markeitect approval.

> **Completed foundation gate record:** This checklist preserves how the V2 foundation was
> accepted. Its early state definitions and unchecked follow-ups are historical gate evidence, not
> a current runtime inventory or progress ledger. Use `docs/current-status.md` for present status.

## Working Agreement

- [x] Markeitect has the final decision on scope and architecture.
- [x] Work proceeds one small, reviewable slice at a time.
- [x] Before each slice, explain its purpose, options, recommendation, and tradeoffs.
- [x] Do not implement an unresolved architecture decision before consultation and approval.
- [x] Commit accepted work before beginning the next change batch.
- [x] Prefer NautilusTrader V2 capabilities when they meet the accepted requirement.
- [x] Keep V2 isolated from the V1 runtime, configuration, environment, and dependencies.
- [x] Preserve useful V1 work for reference; do not silently import its design into V2.
- [x] Treat all previous analytics, indicators, levels, signals, models, and trading assumptions as
      out of scope. V2 analytics will be designed later from a blank page with Markeitect.

## Proven Foundation

- [x] Isolated `v2/` Python project and lockfile.
- [x] NautilusTrader V2 `LiveNode` builds successfully.
- [x] Interactive Brokers connection succeeds through TWS paper trading.
- [x] Configured ES and SPY instrument definitions resolve.
- [x] The runtime publishes a basic `SYSTEM_READY` indication.
- [x] Graceful stop and IB disconnection are verified from live logs.
- [x] V2 owns its TOML configuration and `.env` loading.
- [x] Process environment values take precedence over `v2/.env`.
- [x] Nautilus runtime logs persist to a Git-ignored V2 log file.
- [x] One PyCharm run configuration launches the runtime and keeps macOS awake.
- [x] Focused offline tests and lint checks pass.

## Stage 1: Runtime Message Vocabulary

### Discovery

- [x] Inspect NautilusTrader V2 message-bus APIs, topic behavior, and native event types.
- [x] Identify which lifecycle information Nautilus already publishes.
- [x] Identify the smallest gaps Markeitech must own.
- [x] Document findings without implementing a parallel bus in
      [`v2-runtime-messaging-discovery.md`](../architecture/v2-runtime-messaging-discovery.md).

### Decision Gate 1

- [x] Review the proposed distinction between commands, events, snapshots, and failures.
- [x] Review topic naming and ownership rules.
- [x] Review the minimum common metadata required on Markeitech-owned messages.
- [x] Decide whether custom contracts are needed for the first lifecycle slice.
- [x] Obtain Markeitect approval.

### Implementation

- [x] Implement only the approved minimum message vocabulary.
- [x] Add contract and publication tests.
- [x] Verify publication inside one offline `LiveNode`.
- [x] Review and commit.

## Stage 2: Runtime Control Plane

### Decision Gate 2

- [x] Define the honest initial state set: `STARTING`, `READY`, `FAILED`, and `STOPPING`.
- [x] Defer `DEGRADED`, `RECOVERED`, and `STOPPED` until V2 can observe them truthfully.
- [x] Decide which conditions belong to Nautilus and which belong to Markeitech.
- [x] Define initial readiness as actor operation plus configured instrument availability, not
      live-data activity.
- [x] Make `SystemControlActor` the transition owner and keep consumers read-only.
- [x] Obtain Markeitect approval and record the decision in
      [`v2-runtime-control-plane.md`](../architecture/v2-runtime-control-plane.md).

### Implementation

- [x] Separate state detection from state consumers.
- [x] Publish approved lifecycle transitions through the Nautilus bus.
- [x] Make reasons and evidence visible for every transition.
- [x] Verify transition rules, deduplication, invalid paths, and early actor fault offline.
- [x] Verify startup and normal stop during a user-operated live run.
- [ ] Add connection loss and recovery only after an observable, approved condition exists.
- [x] Review and commit.

## Stage 3: System Health Discord Projection

This is a read-only operational projection. Discord does not determine system state and cannot
become a runtime dependency.

### Approved Initial Scope

- [x] Add Discord immediately after the runtime control plane.
- [x] Subscribe only to approved system-health events.
- [x] Read `MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK` from the V2 environment.
- [x] Format human-readable cards for `STARTING`, `READY`, `DEGRADED`, `RECOVERED`, `FAILED`,
      and `STOPPED` transitions that exist in the approved control-plane contract.
- [x] Do not add analytics, market events, mentions, durable outboxes, or general notification
      routing in the first implementation.
- [x] Discord failure must never block or stop the runtime.
- [x] Record delivery failures in the local runtime log.

### Decision Gate 3

- [x] Inspect the Nautilus V2 actor and async facilities suitable for outbound HTTP.
- [x] Use one actor-owned worker because the RC exposes no actor executor or running Python event
      loop.
- [x] Review the delivery boundary, bounded shutdown, and failure behavior.
- [x] Send readable cards for `STARTING`, `READY`, `FAILED`, and best-effort `STOPPING`.
- [x] Do not send a startup test message; the real `READY` transition proves delivery.
- [x] Obtain Markeitect approval and record the decision in
      [`v2-discord-health.md`](../architecture/v2-discord-health.md).

### Implementation

- [x] Implement one focused Discord health actor.
- [x] Keep webhook secrets out of source control, actor configuration, messages, and logs.
- [x] Prove offline that ordered delivery and rejected requests remain isolated from runtime state.
- [x] Verify readable ordered delivery, including `STOPPING`, during a user-operated live run.
- [x] Review and commit.

## Stage 4: Persistence Boundary

### Requirements Before Technology

- [x] Inventory only the V2 information that must survive restart.
- [x] Classify each item by volume, write pattern, query pattern, retention, and recovery need.
- [x] Separate runtime/control records from future market data.
- [x] Decide what must never be persisted.
- [x] Record findings and the recommendation in
      [`v2-persistence-boundary-discovery.md`](../architecture/v2-persistence-boundary-discovery.md).

### Decision Gate 4

- [x] Compare Nautilus persistence facilities with Markeitech-owned storage.
- [x] Compare suitable local and server-backed database options using the approved requirements.
- [x] Compare suitable market-data storage formats only when market-data requirements exist.
- [x] Decide ownership, schema migration, retention, and backup responsibilities.
- [x] Do not choose SQLite, PostgreSQL, Parquet, Redis, or Docker by default.
- [x] Obtain Markeitect approval: PostgreSQL for operational records; no raw market-data store is
      selected.

### Implementation

- [x] Implement one approved persistence owner.
- [x] Add schema versioning and migrations before storing production records.
- [x] Define idempotency and uniqueness behavior.
- [x] Prove restart reads and duplicate-write handling against PostgreSQL.
- [x] Review and commit.

## Stage 5: Actor Composition And Ownership

Discovery and the proposed decision are recorded in
[`v2-actor-composition-discovery.md`](../architecture/v2-actor-composition-discovery.md).

### Decision Gate 5

- [x] List the actors currently required by approved runtime behavior.
- [x] Give every actor one responsibility and an explicit owner boundary.
- [x] Define configuration-driven enablement and required dependencies.
- [x] Decide how actors announce readiness without relying on startup timing.
- [x] Confirm that actors communicate through approved Nautilus facilities.
- [x] Obtain Markeitect approval.

### Implementation

- [x] Build the approved composition mechanism.
- [x] Reject invalid or incomplete actor configurations before connection.
- [x] Test actors independently and together.
- [x] Review and commit.

## Stage 6: Supervision And Failure Policy

The accepted policy and implementation boundary are recorded in
[`v2-supervision-failure-policy.md`](../architecture/v2-supervision-failure-policy.md).

### Decision Gate 6

- [x] Define which failures are retryable, degradable, fatal, or operator-actionable.
- [x] Define timeout and retry ownership.
- [x] Define queue and backpressure expectations only where queues actually exist.
- [x] Define shutdown and work-draining guarantees.
- [x] Obtain Markeitect approval.

### Implementation

- [x] Add only the approved health and supervision behavior.
- [x] Prevent silent actor failure.
- [x] Expose bounded counters for retries, failures, and dropped work.
- [x] Test failure, recovery-boundary, and shutdown paths.
- [x] Review and commit.

## Stage 7: Provider And Canonical Data Boundary

This stage concerns data transport and identity only. It does not define analytics.

### Decision Gate 7

- [x] Inventory Nautilus native instrument and market-data types available from IB.
- [x] Decide which native types can flow through V2 unchanged.
- [x] Identify provider-specific details that must be preserved.
- [x] Decide whether any Markeitech-owned canonical contracts are actually needed.
- [x] Define timestamps, sessions, instrument identity, source, and fidelity semantics.
- [x] Obtain Markeitect approval and record the decision in
      [`v2-provider-data-boundary-discovery.md`](../architecture/v2-provider-data-boundary-discovery.md).

### Implementation

- [x] Implement the smallest approved provider boundary.
- [x] Pass native source data through unchanged without durable market-data storage or invented
      fidelity.
- [x] Test identity and source configuration while preserving native timestamps by avoiding a
      transformation layer.
- [x] Review and commit.

## Stage 8: Data Acquisition Ownership

The approved direction for a configuration-seeded, runtime-dynamic observation universe and the
core `WatchlistActor` relationship with acquisition is staged in
[`v2-dynamic-watchlist-plan.md`](v2-dynamic-watchlist-plan.md). Its POC closes before historical
acquisition begins.

### Stage 8A: Instrument Definition Ownership

- [x] Make `DataAcquisitionActor` a mandatory core actor.
- [x] Transfer provider-facing instrument-definition requests out of `SystemControlActor`.
- [x] Define a versioned acquisition status and status-request contract.
- [x] Track expected, available, and missing definitions without duplicate requests.
- [x] Make status exchange safe across actor startup order through publish-on-start and a
      post-start status request.
- [x] Keep system health owned exclusively by `SystemControlActor`.
- [x] Add no bars, historical requests, durable market-data storage, pacing policy, or analytics.
- [x] Review and commit Stage 8A.

### Decision Gate 8

- [x] Define live subscription ownership.
- [ ] Define historical-request ownership.
- [ ] Review IB pacing, retry, cancellation, and deduplication requirements.
- [x] Define how feed demand and analytical capability affect transport
      behavior without imposing a fixed active/background hierarchy.
- [ ] Define how approved capabilities declare and derive their own minimum historical evidence.
- [ ] Confirm that reconstructable market data remains transient and is fetched again after
      restart.
- [ ] Obtain Markeitect approval.

Decision draft: [`v2-adaptive-market-data-plane.md`](../architecture/v2-adaptive-market-data-plane.md).

### Stage 8B: Capability And Demand Model

- [x] Define trade universe, observation universe, active capabilities, and temporary focus as
      independent concepts.
- [x] Define provider-neutral feed demand and capability requirement contracts.
- [ ] Define policy-checked intent and observable acquisition lifecycle boundaries.
- [x] Characterize the installed Nautilus subscription surface and avoid relying on opaque
      duplicate-subscription reference counting.
- [ ] Prove native callback distribution and IB unsubscribe behavior in Stage 8C.
- [ ] Define initial resource-budget dimensions without selecting arbitrary limits.
- [x] Obtain Markeitect approval before implementation.

Demand contracts, the logical subscription coordinator, and native call translation are
implemented for review. Focus leases, policy authorization, actor message contracts, resource
budgets, and live Nautilus/IB proof remain pending.

### Stage 8C: Continuous Native-Stream Proof

- [x] Wire configurable native streams for multiple instruments through one logical demand
      owner.
- [x] Prove first-observation state, logical deduplication, final-consumer cancellation, retry, and
      bounded runtime counters offline.
- [x] Use the acquisition actor as one minimal native consumer, not as a trading model.
- [x] Add a temporary bounded native consumer probe without wrappers, persistence, or analytics.
- [x] Live-prove ES/SPY quote and trade observations, IB unsubscribe behavior, and clean shutdown.
- [x] Determine the safe cross-actor native fan-out mechanism without wrapping raw observations or
      allowing independent consumers to cancel provider subscriptions.

### Stage 8D: Capability-Derived Historical Requests

- [ ] Derive bounded historical requirements from approved capability declarations.
- [ ] Prove pacing, ordering, completion, timeout, cancellation, and deduplication.

### Stage 8E: Dynamic Control And Focus

- [ ] Add policy-checked runtime intents for universe, capability, parameter, and focus changes.
- [ ] Prove behavior with deterministic fixtures before an agent receives authority.

### Stage 8F: Failure And Reconnect

- [ ] Define stale observation, connection loss, partial availability, and resubscription.
- [ ] Map truthful acquisition impairment into global health without duplicating Nautilus
      reconnect ownership.

### Explicit Non-Goals

- [x] No raw tick, quote, bar, book, or options-chain persistence.
- [x] No Parquet catalog or market-data tables.
- [x] No replay or backtesting requirements.
- [x] No retention added for hypothetical future consumers.

### Cross-Cutting Operational Audit

- [ ] Treat PostgreSQL as the authoritative audit ledger for every meaningful system intent,
      decision, lifecycle transition, publication, attempt, and outcome added in Stage 8 onward.
- [ ] Give each audited occurrence stable identity, ordering, timestamps, source, correlation,
      causation, schema version, and idempotent write behavior where applicable.
- [ ] Audit market-data control and health facts without persisting raw market-data payloads.
- [ ] Do not mistake ordinary logs, function calls, or native callbacks for durable domain events.

### Remaining Stage 8 Implementation

- [x] Implement approved live-subscription coordination as a provider-neutral core.
- [x] Prevent duplicate live subscriptions and unsafe shared-demand cancellation.
- [x] Make coordinator request and subscription state observable in typed results.
- [ ] Verify connection loss and resubscription behavior.
- [ ] Review and commit.

## Stage 9: Restart And State Recovery

### Decision Gate 9

- [ ] Decide what actors rebuild, restore, request again, or intentionally discard.
- [ ] Define restart ordering through events rather than timing assumptions.
- [ ] Define stale-state and partial-recovery behavior.
- [ ] Obtain Markeitect approval.

### Implementation

- [ ] Implement deterministic recovery for approved state only.
- [ ] Prove clean restart, interrupted restart, and stale-state handling.
- [ ] Review and commit.

## Stage 10: Operational Observability

### Decision Gate 10

- [ ] Decide which logs, health snapshots, and counters are useful to Markeitect.
- [ ] Define log retention and rotation expectations.
- [ ] Decide what belongs in files, durable storage, or console output.
- [ ] Avoid collecting metrics without an operational use.
- [ ] Obtain Markeitect approval.

### Implementation

- [ ] Add the approved structured operational records.
- [ ] Keep high-volume market observations out of general runtime logs.
- [ ] Verify that a failed run can be diagnosed from retained evidence.
- [ ] Review and commit.

## Stage 11: Test And Upgrade Safety

### Decision Gate 11

- [ ] Decide the minimum fake-provider and in-memory-bus support needed.
- [ ] Define which behavior requires live IB acceptance.
- [ ] Define the NautilusTrader RC upgrade review process.
- [ ] Obtain Markeitect approval.

### Implementation

- [ ] Add contract, actor, integration, and failure-path tests as approved.
- [ ] Keep live IB runs operator-controlled.
- [ ] Pin dependencies and review upgrades deliberately.
- [ ] Review and commit.

## Infrastructure Completion Criteria

- [ ] The runtime has explicit, approved ownership boundaries.
- [ ] Actors exchange approved messages through Nautilus facilities.
- [ ] Readiness and failure states have precise meanings and evidence.
- [ ] Required state survives restart through an approved persistence design.
- [ ] Provider data retains identity, timing, source, and fidelity while flowing through the live
      runtime.
- [ ] Acquisition is paced, deduplicated, observable, and recoverable.
- [ ] Shutdown is clean and no required work is silently lost.
- [ ] Discord health reporting is useful but never required for runtime operation.
- [ ] Logs and tests can explain failures without a live debugging session.
- [ ] Markeitect approves the infrastructure as ready for the next product domain.

## Explicitly Deferred

- [ ] Analytics definitions.
- [ ] Indicators, levels, zones, profiles, or technical-analysis policy.
- [ ] Signal and trading models.
- [ ] Machine learning and agents.
- [ ] Options analysis.
- [ ] Discord analytics, market events, signals, mentions, and durable delivery.
- [ ] User interfaces.
- [ ] Execution and automated trading.
- [ ] Additional infrastructure products without a demonstrated requirement.

Deferred items are not rejected. Each begins with a new requirements discussion and its own
approved plan after the infrastructure foundation is accepted.
