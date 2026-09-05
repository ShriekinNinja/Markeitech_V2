# Markeitech V2 Backlog

This checklist orders unfinished V2 work by operational consequence. It is a decision aid, not an
automatic implementation queue: Markeitect approves each batch, and priorities may change when new
evidence appears.

The canonical product order is the
[Sir Loke v1 delivery blueprint](v2-market-events-live-agent-plan.md). This backlog records debt and
follow-up work; it does not maintain a second product roadmap.

## Sir Loke V1 Product Gates

- [ ] Consolidate the accepted Sir Loke v1 product direction, current status, and delivery path;
      remove superseded working requirements and the duplicate coding sequence from the active
      documentation tree. Prepared in the current documentation PR; complete only after review and
      merge.
- [ ] Prove the native NautilusTrader/IB read-only TWS observation envelope with offline fixtures
      and one separately authorized paper-account acceptance. No order action.
- [ ] Define canonical broker observation, recommendation linkage, trade episode, trader plan,
      advisory intervention, acknowledgement, cooldown, conversation, and report contracts.
- [ ] Approve the persistence, redaction, retention, restoration, and reconciliation policy for
      the new durable product records.
- [ ] Implement an allowlisted private two-way Discord bot transport with bounded failure and
      reconnection behavior.
- [ ] Complete the minimum V3 measurement, semantic-event, SPXW/QQQ options, and selected
      cross-instrument evidence corridor required for a named recommendation or abstention.
- [ ] Implement the bounded Sir Loke read model, model boundary, read-only tools, citations,
      structured decisions, abstention, monitoring, mentoring, intervention explanation, and
      after-trade reporting.
- [ ] Integrate the four live paths and prove that no Sir Loke/Discord/policy/observation route can
      reach an order method.
- [ ] Complete the separately authorized end-to-end IB paper/TWS acceptance story.

## Completed Priority 0: Historical Runtime Safety Gate

These items could freeze the runtime, corrupt its truth claims, or stop unrelated event-driven
work. They previously blocked Stage 9B and are retained as completed audit history.

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

## Priority 1: Reliability Of Used Sir Loke Paths

These items are not a blanket prerequisite for every Sir Loke implementation step. Each item must
close or receive an explicit bounded acceptance before its exact dependency can contribute to a
live recommendation, intervention, broker observation, or report.

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

- [x] Preserve temporarily unavailable historical session-window demands with typed, deduplicated,
      timer/session-driven retry instead of rejecting closed-session and pre-open work. Connected
      acceptance on 2026-08-22 deferred all six future opening-range demands without rejection while
      unrelated historical acquisition completed.
- [x] Add passive host/process/cache resource measurements plus configurable sustained
      warning/critical/recovery transitions, durable operational audit, and critical-only Discord
      ping policy. Connected warning acceptance on 2026-08-22 reconciled 15 raw samples, one warning
      transition, four Discord deliveries, and all 726 PostgreSQL writes; controlled critical and
      recovery projection remain follow-up cases.
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
- [x] Retire superseded operational documentation through the reviewed root-promotion migration;
      recovery remains available through Git history rather than active-tree copies.

## Options-Flow Evidence Track

The manually downloaded BlackBoxStocks feed is optional vendor-curated context, not a consolidated
options tape, live execution source, or directional signal. Its measured limitations and proposed
contracts are documented in
[`../research/v2-options-flow-specialist-report.md`](../research/v2-options-flow-specialist-report.md).

### Evidence And Provenance Gate

- [ ] Confirm that the active subscription and market-data terms permit internal machine analysis,
      source retention, normalized derivatives, model/agent use, and derived-event projection.
- [ ] Approve whether original exports may be retained outside Git and PostgreSQL, with explicit
      access controls and retention. Until then, `data/OptionsFlow.csv` remains ignored local
      data outside Git.
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

## Gamma-Exposure Evidence Track

Gamma-exposure maps are optional modeled options context, not observed dealer inventory, order
flow, directional probability, or a standalone signal. The interpretation boundary and proposed
provider-neutral contract are documented in
[`../research/gamma-exposure-and-0dte-gex-maps.md`](../research/gamma-exposure-and-0dte-gex-maps.md).

- [ ] Confirm licensed access, internal-analysis rights, retention limits, and authoritative field
      methodology for any GEX provider before runtime ingestion.
- [ ] Define an immutable provider-reported snapshot contract carrying underlying/root/expiration,
      reference instrument and basis, timestamps, session, units, formula/model version, sign
      assumptions, coverage, input age, and evidence-health state.
- [ ] Keep vendor-reported GEX and any future Markeitech chain-derived estimate as separately named
      evidence sources. Never silently substitute one for the other.
- [ ] Normalize SPX/SPY/ES and QQQ/NQ levels through explicit timestamped basis evidence; never
      compare or project index, ETF, and futures levels as if their prices were interchangeable.
- [ ] **Stage 9F:** prove bounded acquisition of the chain, quote, Greek, OI, and reference-price
      inputs required to evaluate gamma claims honestly. Do not retain full raw chains by default.
- [ ] **Stage 9H:** evaluate configurable wall, concentration, flip, balance, straddle, persistence,
      and migration metrics only after their formulas and units are explicit. Join them with
      acceptance/rejection, profile, delta/CVD, volatility, and cross-instrument evidence.
- [ ] **Stage 9I:** expose GEX to the advisory agent only as cited, freshness-qualified evidence
      with supporting, conflicting, and missing inputs visible. A wall, magnet, or flip cannot
      independently create an opportunity or select an option contract.
- [ ] **Stage 9K:** validate and optimize eligible definitions with leakage-safe temporal outcomes,
      source/model version isolation, regime splits, abstention, and level-migration analysis.
- [ ] Keep aggregate dollar GEX, call/put balance, walls, magnets, flips, and straddle fields out of
      PostgreSQL until an approved semantic lifecycle or compact-summary contract exists.
- [ ] Explicitly reject claims of certain dealer positioning, guaranteed pin/support/resistance,
      deterministic hedging flow, or causal market impact from GEX alone.

## Historical Stage Mapping

Stages 9A-9C and runtime-resource hardening preserve completed foundation evidence. Stage 9D and
V3-03 preserve incomplete deterministic entity/measurement replacement work. Stages 9E-9J map
into the minimum evidence, read-model, and opportunity portions of the Sir Loke gates. Stage 9K's
full ML/data program remains later.

These stage labels remain useful technical references but no longer form a second linear product
queue. Follow the canonical roadmap's
[reuse table](v2-market-events-live-agent-plan.md#reuse-of-existing-stage-work) and the
[current-status ledger](../current-status.md) for what is active.

## Documentation Reliability

- [ ] Add CI checks for Markdown links, required authority/status metadata, stale branch-status
      claims, and canonical Stage 9A-9K numbering. Documentation automation reports drift; it does
      not decide product status or rewrite accepted documents.

The canonical product and delivery design remains in
[`../product/sir-loke-v1.md`](../product/sir-loke-v1.md) and
[`v2-market-events-live-agent-plan.md`](v2-market-events-live-agent-plan.md).
