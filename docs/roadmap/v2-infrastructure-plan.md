# Markeitech V2 Infrastructure Plan

**Status:** Foundation established; all later stages require Markeitect approval.

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

- [ ] Review the proposed distinction between commands, events, snapshots, and failures.
- [ ] Review topic naming and ownership rules.
- [ ] Review the minimum common metadata required on Markeitech-owned messages.
- [ ] Decide whether custom contracts are needed for the first lifecycle slice.
- [ ] Obtain Markeitect approval.

### Implementation

- [ ] Implement only the approved minimum message vocabulary.
- [ ] Add contract and publication tests.
- [ ] Verify publication inside one live `LiveNode`.
- [ ] Review and commit.

## Stage 2: Runtime Control Plane

### Decision Gate 2

- [ ] Define exactly what `STARTING`, `READY`, `DEGRADED`, `FAILED`, `STOPPING`, and `STOPPED`
      mean.
- [ ] Decide which conditions belong to Nautilus and which belong to Markeitech.
- [ ] Decide whether readiness means connection only, instrument availability, live-data activity,
      or another approved combination.
- [ ] Decide who publishes each transition and who consumes it.
- [ ] Obtain Markeitect approval.

### Implementation

- [ ] Separate state detection from state consumers.
- [ ] Publish approved lifecycle transitions through the Nautilus bus.
- [ ] Make reasons and evidence visible for non-ready states.
- [ ] Verify startup, normal stop, connection loss, and recovery behavior.
- [ ] Review and commit.

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

- [ ] Inspect the Nautilus V2 actor and async facilities suitable for outbound HTTP.
- [ ] Review the proposed delivery boundary and failure behavior.
- [ ] Review the first card format and confirm which approved health transitions are sent.
- [ ] Decide whether a startup test message is useful.
- [ ] Obtain Markeitect approval.

### Implementation

- [ ] Implement one focused Discord health actor.
- [ ] Keep webhook secrets out of source control, configuration files, messages, and logs.
- [ ] Prove that unavailable or rejected Discord requests do not affect system readiness.
- [ ] Verify readable delivery during a user-operated live run.
- [ ] Review and commit.

## Stage 4: Persistence Boundary

### Requirements Before Technology

- [ ] Inventory only the V2 information that must survive restart.
- [ ] Classify each item by volume, write pattern, query pattern, retention, and recovery need.
- [ ] Separate runtime/control records from future market data.
- [ ] Decide what must never be persisted.

### Decision Gate 4

- [ ] Compare Nautilus persistence facilities with Markeitech-owned storage.
- [ ] Compare suitable local and server-backed database options using the approved requirements.
- [ ] Compare suitable market-data storage formats only when market-data requirements exist.
- [ ] Decide ownership, schema migration, retention, and backup responsibilities.
- [ ] Do not choose SQLite, PostgreSQL, Parquet, Redis, or Docker by default.
- [ ] Obtain Markeitect approval.

### Implementation

- [ ] Implement one approved persistence owner.
- [ ] Add schema versioning and migrations before storing production records.
- [ ] Define idempotency and uniqueness behavior.
- [ ] Prove restart reads and duplicate-write handling.
- [ ] Review and commit.

## Stage 5: Actor Composition And Ownership

### Decision Gate 5

- [ ] List the actors currently required by approved runtime behavior.
- [ ] Give every actor one responsibility and an explicit owner boundary.
- [ ] Define configuration-driven enablement and required dependencies.
- [ ] Decide how actors announce readiness without relying on startup timing.
- [ ] Confirm that actors communicate through approved Nautilus facilities.
- [ ] Obtain Markeitect approval.

### Implementation

- [ ] Build the approved composition mechanism.
- [ ] Reject invalid or incomplete actor configurations before connection.
- [ ] Test actors independently and together.
- [ ] Review and commit.

## Stage 6: Supervision And Failure Policy

### Decision Gate 6

- [ ] Define which failures are retryable, degradable, fatal, or operator-actionable.
- [ ] Define timeout and retry ownership.
- [ ] Define queue and backpressure expectations only where queues actually exist.
- [ ] Define shutdown and work-draining guarantees.
- [ ] Obtain Markeitect approval.

### Implementation

- [ ] Add only the approved health and supervision behavior.
- [ ] Prevent silent actor failure.
- [ ] Expose bounded counters for retries, failures, and dropped work.
- [ ] Test failure, recovery, and shutdown paths.
- [ ] Review and commit.

## Stage 7: Provider And Canonical Data Boundary

This stage concerns data transport and identity only. It does not define analytics.

### Decision Gate 7

- [ ] Inventory Nautilus native instrument and market-data types available from IB.
- [ ] Decide which native types can flow through V2 unchanged.
- [ ] Identify provider-specific details that must be preserved.
- [ ] Decide whether any Markeitech-owned canonical contracts are actually needed.
- [ ] Define timestamps, sessions, instrument identity, source, and fidelity semantics.
- [ ] Obtain Markeitect approval.

### Implementation

- [ ] Implement the smallest approved provider boundary.
- [ ] Preserve source data without inventing unavailable fidelity.
- [ ] Test identity, timestamp, and source preservation.
- [ ] Review and commit.

## Stage 8: Data Acquisition Ownership

### Decision Gate 8

- [ ] Define live subscription ownership.
- [ ] Define historical-request ownership.
- [ ] Review IB pacing, retry, cancellation, and deduplication requirements.
- [ ] Decide whether active and background instruments require different transport behavior.
- [ ] Obtain Markeitect approval.

### Implementation

- [ ] Implement only approved acquisition coordination.
- [ ] Prevent duplicate subscriptions and historical requests.
- [ ] Make request and subscription state observable.
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
- [ ] Provider data retains identity, timing, source, and fidelity.
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
