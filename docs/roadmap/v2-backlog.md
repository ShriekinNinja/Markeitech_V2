# Markeitech V2 Backlog

This checklist orders unfinished V2 work by operational consequence. It is a decision aid, not an
automatic implementation queue: Markeitect approves each batch, and priorities may change when new
evidence appears.

## Priority 0: Critical Runtime Safety

These items can freeze the runtime, corrupt its truth claims, or stop unrelated event-driven work.
They block Stage 9B.

- [x] Make operational-persistence admission non-blocking so PostgreSQL latency or a saturated
      bounded queue cannot freeze the Nautilus event loop.
- [x] Reject unaccepted persistence work explicitly, report the affected sequence and bounded
      counters, and degrade through the existing component-failure path.
- [x] Preserve FIFO processing and retry behavior for every record accepted by the worker.
- [x] Batch accepted records into bounded PostgreSQL transactions instead of opening one
      connection and transaction per event.
- [x] Reserve configured queue capacity for system-health and component-failure records.
- [x] Validate configured normal capacity against the deterministic startup event envelope.
- [x] Prevent admission pressure from producing an invalid terminal-to-starting health transition.
- [x] Review and live-accept the non-blocking persistence behavior before Stage 9B. The
      2026-08-17 mega-clean boot stored all 490 accepted records with zero retries, failures,
      rejections, pending records, sequence gaps, or duplicates.

## Priority 1: Reliability Before Unattended Intelligence

These items do not block the first deterministic market-intelligence slices, but they must close
before an unattended advisory agent can be trusted.

- [ ] Add provider-subscription retry and recovery ownership after an initial acquisition failure;
      retries must be event/timer driven and must not block unrelated streams.
- [ ] Publish explicit component-recovery evidence and permit system health to recover from
      `DEGRADED` to `READY` when current evidence proves the
      failed dependency has recovered.
- [ ] Replace the single lifetime persistence-failure latch with bounded transition/deduplication
      semantics so a later distinct failure remains observable without creating an event storm.
- [ ] Decide whether rejected operational records require a local durable overflow spool. Until
      then, rejection is explicit but the rejected payload is not durable in PostgreSQL.
- [ ] Add direct actor lifecycle and retry tests for persistence, acquisition, watchlist, session,
      and evidence-health actors.
- [ ] Verify connection loss, provider recovery, and resubscription behavior in a controlled live
      acceptance run.
- [ ] Decide whether learned evidence-recency profiles need age-based prior decay in addition to
      policy-version isolation and exponentially weighted live updates.
- [ ] Add configurable evidence-health transition hysteresis or persistence windows. The
      2026-08-17 clean run learned valid quote cadences, but the configured two-second hard fresh
      floor still produced 13 brief `HEALTHY -> DEGRADED` transitions on naturally intermittent
      overnight ES, YM, and CL quotes; all recovered automatically. Keep thresholds, confirmation
      duration, and recovery behavior configurable and optimization-ready.

## Priority 2: Runtime Hardening

- [ ] Make native-probe composition request only feed kinds the selected probe supports.
- [ ] Cache or precompute session schedules so steady-state evaluation does not rebuild exchange
      calendars every second.
- [ ] Treat observations for unexpected instruments as explicit rejected input instead of raising
      from a live callback.
- [ ] Execute only unapplied database migrations and distinguish missing-schema repair from normal
      migration startup.
- [ ] Reconcile interrupted runtime-run records on startup with an explicit terminal reason.
- [ ] Verify operational event identity and deduplication across restart and repeated delivery.

## Priority 3: Maintainability And Scale

- [ ] Add CI gates for V2 tests, lint, migration checks, and configuration validation.
- [ ] Define PostgreSQL connection lifecycle, pooling, circuit breaking, and capacity evidence when
      measured load justifies changing the current single-worker design.
- [ ] Add bounded observability for queue occupancy, rejection rate, write latency, and recovery
      without persisting raw market observations.
- [ ] Define retention, backup, and restore acceptance for operational records before production
      deployment.
- [ ] Archive remaining V1-only operational documentation clearly without deleting preserved work.

## Options-Flow Evidence Track

The manually downloaded BlackBoxStocks feed is optional vendor-curated context, not a consolidated
options tape, live execution source, or directional signal. Its measured limitations and proposed
contracts are documented in
[`../research/v2-options-flow-specialist-report.md`](../research/v2-options-flow-specialist-report.md).

### Evidence And Provenance Gate

- [ ] Confirm that the active subscription and market-data terms permit internal machine analysis,
      source retention, normalized derivatives, model/agent use, and derived-event projection.
- [ ] Approve whether original exports may be retained outside Git and PostgreSQL, with explicit
      access controls and retention. Until then, `v2/data/OptionsFlow.csv` remains untracked.
- [ ] Capture the export timezone, download timestamp, schema/version identity, and complete active
      BlackBox filter profile with every future artifact.
- [ ] Decide whether to pursue a supported licensed API or richer source containing stable trade/
      correction identity, NBBO-at-print, venue, condition, strategy linkage, and precise time.

### Isolated Source Contract

- [ ] Define immutable source-artifact, source-row, and provider-neutral normalized-observation
      contracts without presenting a manually imported file as live evidence.
- [ ] Preserve decimal/raw source values, partial contract identity, unknown-timezone state,
      sentinel/correction states, exact-date 0DTE derivation, and explicit fidelity.
- [ ] Add deterministic artifact/row/equivalence identities, same-artifact idempotency, overlap
      detection, and honest ambiguity where cross-file deduplication is impossible.
- [ ] Implement a pure bounded BlackBox CSV adapter and quality summary with fixtures for schema
      drift, duplicate-looking prints, orange/red rows, missing side, zero spot/IV, and the audited
      20,271-row sample.
- [ ] Keep raw rows out of PostgreSQL. Audit artifact lifecycle and quality summaries only after
      the source contract is accepted.

### Product Integration Gates

- [ ] **Stage 9F:** join normalized flow only with canonical option identity, fresh NBBO/quotes,
      chain/Greeks/OI, named underlying reference, session state, and quote-quality evidence before
      making moneyness, affordability, liquidity, or expression-quality claims.
- [ ] **Stage 9H:** add reviewed rolling concentration, repeated-contract activity, relative
      premium/size, surface/time/session cohorts, and flow-versus-underlying-response analytics.
      Keep calls/puts, ask/above-ask, sweep/block, late/cancel, 0DTE, contract, and underlying
      dimensions separate; do not collapse them into a folklore bullish/bearish score.
- [ ] **Stage 9I:** expose options-flow evidence to the advisory agent only after source freshness,
      completeness, filter bias, missing fields, and conflicting evidence remain visible. The feed
      stays optional and can never be a mandatory readiness dependency.
- [ ] **Stage 9K:** evaluate and optimize eligible thresholds only with leakage-safe temporal data,
      explicit outcomes, versioned parameters, and policy bounds. Two sessions are insufficient.

### Explicit Non-Goals

- [ ] Do not build a live actor, raw-row PostgreSQL table, full-chain subscription, Discord stream,
      agent tool, or directional score in the first source-contract slice.
- [ ] Do not infer opening/closing intent, customer/dealer identity, complete strategy, consolidated
      volume, executable price, or market-wide sentiment from the current export.
- [ ] Do not let options-flow work reorder or weaken the accepted Stage 9 product sequence.

## Product Sequence

- [x] **Stage 9A:** session/calendar ownership and evidence-health truth.
- [x] **Critical hardening gate:** live-accept Priority 0 persistence behavior.
- [x] **Stage 9B:** historical dependency execution. Live-accepted 2026-08-17 with one shared
      provider request, two independent consumers/readiness results, continuing unrelated runtime
      activity, and lifecycle-only PostgreSQL persistence.
- [ ] **Stage 9C:** baseline deterministic metric contracts.
- [ ] **Stage 9D:** session entities, rolling state, and durable summaries.
- [ ] **Stage 9E:** first quiet semantic market events.
- [ ] **Stage 9F:** bounded 0DTE options-data proof.
- [ ] **Stage 9G:** cross-instrument relationship state.
- [ ] **Stage 9H:** richer approved analytics.
- [ ] **Stage 9I:** live advisory agent and plural opportunity set.

The detailed product design remains in
[`v2-first-market-intelligence-coding-sequence.md`](v2-first-market-intelligence-coding-sequence.md)
and [`v2-market-events-live-agent-plan.md`](v2-market-events-live-agent-plan.md).
