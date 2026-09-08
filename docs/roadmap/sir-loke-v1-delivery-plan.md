# Sir Loke V1 Delivery Plan

**Direction approved:** 2026-09-08 — deliver Sir Loke through small, reviewable live increments.
**Implementation:** No task below is claimed implemented or live-accepted by this planning change.
**Next task:** SL-01. This plan does not authorize implementation of every listed task.

The [product definition](../product/sir-loke-v1.md) remains the full V1 release contract.
The [current status](../current-status.md) owns implementation evidence, and the
[Sir Loke boundaries](../architecture/sir-loke-v1-boundaries.md) own component and tool authority.
A conversational increment is useful progress toward that product; it is not full V1 acceptance.

## Delivery Rules

- Deliver one observable Sir Loke behavior per task and one coherent PR. Include the minimum
  configuration, integration, audit, and documentation needed to run that behavior. A disabled
  component plus fixtures is not a completed product task.
- Every implementation task ends with a live run performed and reviewed **only by Markeitect**.
  Agents prepare the run; they do not start IB/TWS, Discord, a live model, or connected acceptance,
  inspect private run results unasked, or declare live acceptance on Markeitect's behalf.
- Use the states `planned`, `implementing`, `ready for Markeitect live test`, `changes requested`,
  and `accepted by Markeitect`. Offline checks, CI, publication, or merge alone never mean accepted.
- Present the exact PR head for the live test before merge. Markeitect runs, reviews the results,
  accepts or requests fixes, and owns approval/merge. Fixes remain on the same PR; a changed head
  needs renewed review and a live check of the affected behavior.
- Start dependent implementation only after its prerequisite is live-accepted and merged, unless
  Markeitect explicitly changes that dependency. A blocked broker task does not block an
  independent conversation or market-evidence task whose own dependencies are accepted.
- Tests cover the changed behavior and concrete failure risks. Reuse existing fixtures and run
  required CI; do not create generic proof frameworks, duplicate old acceptance, or expand a task
  into unrelated hardening. Correctness, no execution, identity, freshness, authentication, bounded
  cost, and failure isolation still apply to the behavior being exposed.
- Approve only the unresolved provider/model, dependency, schema, or policy choices required by the
  current task. Keep startup configuration typed, bounded, and versioned; defer optimization and
  dynamic reconfiguration machinery until a named task requires them.
- Infrastructure-only subtasks stay inside their consuming live task. If a task is too large,
  split it into smaller runnable behaviors and give each its own live test. Documentation-only
  maintenance, including this plan change, requires document review rather than a contrived run.

## Required Task Brief And Live Handoff

Before coding, put a short task brief in the issue/PR: task ID, one user-visible outcome, exact
files/responsibilities, accepted dependencies, explicit exclusions, unresolved decisions with a
recommended choice, and focused tests for named risks. Resolve consequential choices with
Markeitect; routine implementation details inside approved boundaries do not need another gate.
Do not write a second architecture document merely to begin a task.

Every implementation PR must provide a runnable handoff containing:

1. Exact commit SHA, setup requirements, local configuration changes for Markeitect to make, and
   which services, paper account, instruments, session, and model budget the test uses.
2. Copy-paste Python-owned start and stop commands, checked against the implemented CLI; never
   invent a future command or require Markeitect to assemble a launch script.
3. A short numbered scenario with the messages/actions Markeitect performs, observable expected
   results, a bounded duration or event count, and immediate stop conditions.
4. One local, sanitized result summary location or clearly identified Discord messages, with
   timestamps, relevant identities, actual/expected outcomes, and gaps. Secrets and raw market
   data do not belong in the PR or committed evidence. No new reporting framework is required.
5. A blank Markeitect verdict: `accepted`, `changes requested`, or `not exercised`, tied to the
   tested head. Agents may help interpret supplied results when asked; Markeitect owns the verdict.

If required market conditions do not occur, the scenario remains not exercised. Fixtures may
cover difficult races but never count as a live market event. Report the remaining case instead
of extending a run without a bound or claiming a pass. No plan entry grants live-money access.

## SL-01 — Talk To Sir Loke In Private Discord

**Depends on:** no broker-observation task.
**Outcome:** ask “What can you see right now?” and receive a real model-generated answer grounded
in the runtime's actual capability/readiness snapshot; exchange a follow-up in the same context.

**Implement:** one allowlisted Discord context, inbound messages and replies, one model provider,
a compact immutable snapshot of current enabled capabilities and instrument identities, bounded
conversation context, citation/claim validation, and the minimum approved sanitized audit.
Unavailable broker, option, and analytical capabilities are stated explicitly. Facts are admitted
by code; the model explains them. Keep order objects, credentials, and arbitrary tools out.

**Touchpoints:** new Sir Loke/Discord modules alongside the existing system composition, config,
CLI, and persistence boundaries; corresponding focused tests. The webhook stays a health transport.
The brief must name the exact new paths after inspection; no general framework or full trade schema.

**Decisions before coding:** propose one Discord library, one model/provider, explicit invocation
and cost limits, allowlist configuration, snapshot/output fields, and minimal audit retention.
Markeitect approves those choices together in this task's short brief; broker proof is not a
prerequisite. The implementation must provide a launch profile that does not activate broker
observation. Live market-data access is optional for this capability-status test.

**Focused checks:** allowlist rejection, unsupported-claim rejection, unavailable-state response,
model timeout/budget handling, bounded context, and no access to execution or secrets.
**Markeitect live test:** start the supplied profile, ask the question and one follow-up, compare
claimed capabilities with the runtime, and request an unavailable trade recommendation. Pass only
if replies are contextual and factual and the missing capability is named without invented advice.

## SL-02 — Ask About Current Market Observations

**Depends on:** SL-01.
**Implement:** expose existing admitted observations, contract, timestamps, session, and freshness
through the read model for one explicitly configured evidence instrument. Reuse acquisition and
health owners; do not activate the unfinished measurement replacement just for a status reply.
**Focused checks:** snapshot identity and stale/missing data admission.
**Markeitect live test:** with paper market data, ask for the latest available observation, compare
it with the same timestamped runtime record, then stop the feed and ask again. A stale observation
must be identified as stale; missing data must not become a current price or trading signal.

## SL-03 — Keep Conversation Failures Contained

**Depends on:** SL-02.
**Implement:** the narrow reconnect, bounded retry, and delivery recovery needed by the working
conversation; keep market ingestion independent. Basic timeouts/isolation already belong in SL-01.
**Focused checks:** duplicate delivery and bounded recovery for the selected transport/model.
**Markeitect live test:** interrupt Discord access and restore it, then exercise the documented
model-unavailable case. Observe continuing ingestion, honest degradation, and recovery without a
burst of duplicate replies. Use reversible local controls specified by the implementation.

## SL-04 — Resolve Native Broker Observation In Paper

**Depends on:** existing Gate 1A evidence; independent of SL-01–03.
**Implement:** a bounded runnable observation probe and outbound-request audit for the pinned native
candidate. Resolve only the source/settings/report concerns needed for its approved test, using the
[broker safety gate](#broker-safety-gate). No production broker owner is activated by this task.
**Focused checks:** permitted request boundary, account identity, and sanitized probe output.
**Markeitect live test:** execute the approved probe against preexisting and new manual paper
orders. Compare TWS facts with captured observations and outbound requests. No binding or order
action is allowed. Missing manual visibility is a finding, not permission to add a second client.
A bounded negative result closes the investigation only when Markeitect accepts it; SL-05 remains
blocked until he approves a viable alternative and its own live proof.

## SL-05 — Sir Loke Notices A Manual Paper Order

**Depends on:** SL-01 and a positive, accepted SL-04 result.
**Implement:** the narrow sanitized broker observer, approved audit, and a proactive Discord
notification for a new manual order, including paper account and exact contract identity.
**Focused checks:** identity, duplicate event suppression, and no mutable broker object downstream.
**Markeitect live test:** place one manual paper order in the admitted scope. Sir Loke reports the
order once and distinguishes an order from a fill or position. Compare the displayed facts with TWS.

## SL-06a — Follow Manual Order Changes

**Depends on:** SL-05.
**Implement:** notifications and audit for manual amendments, cancellation, and replacement,
including preserved original/replacement identity and explicit late/conflicting state.
**Focused checks:** duplicate/late updates and canceled-versus-replaced identity.
**Markeitect live test:** amend and cancel/replace an unfilled paper order using TWS. Compare each
notification with the manual action; Sir Loke must never report an unfilled order as a position.

## SL-06b — Track Fills, Position Changes, And Closure

**Depends on:** SL-06a.
**Implement:** reconcile fills to position quantity for the admitted scope, including partial
fills, scaling, and manual closure. Preserve order/fill/account identities and unknown state.
**Focused checks:** partials, duplicate/late fills, quantity accounting, and closure.
**Markeitect live test:** fill, scale, and close one paper position manually and compare reported
quantities with TWS. Unobserved partial fills remain an explicit unaccepted case; the next task
may depend only on the scope Markeitect accepted, with the missing case retained for SL-18.

## SL-07 — Recover Broker State After Reconnect

**Depends on:** SL-06b.
**Implement:** bounded reconciliation with explicit recovered-versus-live provenance; prevent
recovered events from producing duplicate entry/closure claims. Recheck every recovery request.
**Focused checks:** omission, duplicate reconciliation, and no-control behavior during recovery.
**Markeitect live test:** disconnect the observer around one manual paper state change, reconnect,
and compare the recovered state with TWS. Sir Loke must identify the gap and recovered facts.

## SL-08 — Record The Trader's Thesis

**Depends on:** SL-06b.
**Implement:** one trader-originated episode with a declared thesis, horizon, risk declaration,
and invalidation; ask for unknown fields and append revisions with approved durable audit.
**Focused checks:** original-versus-revised history and separation of trader statements/broker facts.
**Markeitect live test:** enter a paper trade without a recommendation, give Sir Loke a plan, revise
one field, restart, and ask what changed. He must preserve both versions and invent no entry thesis.

## SL-09 — Monitor One Declared Invalidation

**Depends on:** SL-02 and SL-08.
**Implement:** one approved, typed price condition supplied in the trader's plan; deterministic
comparison using an admitted current observation, with missing/stale evidence suspending judgment.
This is monitoring of a declared plan, not an autonomous entry strategy or complete options risk.
**Focused checks:** condition boundary, freshness, and one intervention per transition.
**Markeitect live test:** declare a bounded paper-test condition, observe its live transition, and
verify the warning cites the plan and triggering observation. If no transition occurs, do not pass.

## SL-10 — Request And Record Acknowledgement

**Depends on:** SL-09.
**Implement:** one approved warning/acknowledgement rule with a deadline, correlation to the exact
intervention, and durable response or non-response. Model tone cannot change policy state.
**Focused checks:** timely, late, duplicate, and unrelated acknowledgements.
**Markeitect live test:** acknowledge one warning and leave a separate warning unanswered; check
that Sir Loke records the appropriate result and preserves it after restart.

## SL-11 — Apply Advisory Escalation And Cooldown

**Depends on:** SL-10.
**Implement:** approved concern, warning, urgent invalidation, noncompliance, cooldown, and resolution
transitions only for the admitted condition. Cooldown withholds Sir Loke recommendations; it never
controls TWS. Exact thresholds/times are a task decision, not model output.
**Focused checks:** transition/expiry/recovery rules and recommendation admission during cooldown.
**Markeitect live test:** exercise the bounded policy scenario, inspect state before/after restart,
and verify its expiry/resolution. SL-17 later verifies cooldown against an otherwise qualified
recommendation; this task alone cannot claim that full behavior live-accepted.

## SL-12 — Receive A Factual Closure Report

**Depends on:** SL-07, SL-08, and SL-10.
**Implement:** one report from the admitted episode, preserving plan revisions, broker facts,
interventions, responses, and known outcome. Missing fees or outcomes remain unknown.
**Focused checks:** report reconstruction and duplicate closure/report delivery.
**Markeitect live test:** close a monitored paper trade and compare the report with TWS and the
conversation. Restart and retrieve the same factual history without rewriting the original thesis.

## SL-13 — Inspect One SPXW 0DTE Candidate

**Depends on:** SL-02.
**Implement:** bounded discovery and evidence for one exact SPXW contract: underlying reference,
expiry/last-trade/settlement, multiplier, quote age, bid/ask/size/spread, and valid Greek/IV provenance
where required. Approve source, entitlements, bounds, and missing-data rules in this task.
**Focused checks:** exact contract/session identity and eligibility/rejection rules.
**Markeitect live test:** ask Sir Loke about the selected contract, compare the timestamped facts
with TWS, then check unavailable/stale evidence handling. Candidate inspection is not a recommendation.

## SL-14 — Inspect One QQQ 0DTE Candidate

**Depends on:** SL-13.
**Implement:** QQQ-specific contract, expiration, exercise/settlement, and reference rules using the
accepted candidate path. Preserve SPXW/QQQ separation without a globally preferred expression.
**Focused checks:** product-specific differences and cross-product identity isolation.
**Markeitect live test:** inspect one exact QQQ contract and compare with TWS; query SPXW again and
verify neither product inherits the other's terms. Missing entitlements remain a task blocker.

## SL-15 — Explain One Approved Deterministic Setup

**Depends on:** SL-02; independent of broker tasks.
**Implement:** one explicitly selected setup's necessary measurements and deterministic qualifying,
conflicting, and invalidation evidence, shown by Sir Loke. Reuse existing calculations where valid;
only the required measurement integration enters scope, with one canonical producer.
**Decision before coding:** Markeitect selects the setup; the brief names its exact instruments,
inputs, formula/indicator, parameters, warmup, trigger, and invalidation. This selection is still
open. Do not treat “build market intelligence” as a task or invent a trading rule. If multiple
missing calculations are required, create one named live task per calculation before this task.
The [V3 reference](../reference/session-metrics-replacement-plan.md) supplies reuse constraints,
not a requirement to finish every dormant owner or Visual Debug before this behavior can run.
**Focused checks:** formula/threshold, warmup, missing/conflicting data, and input identity.
**Markeitect live test:** ask why the setup is qualified, contradicted, or unavailable; compare
its inputs and decision with the approved rule during live operation. Unseen states stay unaccepted.

## SL-16 — Recommend Or Abstain On A Qualified Expression

**Depends on:** SL-13, SL-14, and SL-15.
**Implement:** bind an independently qualified opportunity to eligible SPXW/QQQ candidates; publish
versioned evidence, conflicts, entry condition, invalidation, expiry, and approved risk context,
or a named abstention. Support distinct opportunity identities; no fabricated facts or model-only
eligibility. Approve the minimum evidence/risk contract before exposing recommendations.
**Focused checks:** qualified and insufficient/conflicting cases, expiry, and plural candidates.
**Markeitect live test:** ask for an assessment during the bounded session and compare it with the
rule and contract evidence. A real qualified recommendation and a separate honest abstention are
both required for full acceptance; no forced trade or changed threshold to manufacture either.

## SL-17 — Link And Monitor A Recommended Paper Trade

**Depends on:** SL-07, SL-11, and SL-16.
**Implement:** explicit supported/ambiguous/rejected recommendation-to-trade linkage; preserve
independent trades, revise/invalidate recommendations when evidence changes, and apply accepted
monitoring and cooldown to linked episodes. Keep simultaneous opportunities/trades distinct.
**Focused checks:** attribution ambiguity, immutable original thesis, expiry, and cooldown admission.
**Markeitect live test:** manually enter an admitted recommended paper trade and check linkage and
subsequent evidence changes; query again during cooldown. Compare with a separate unlinked trade.
If the required live recommendation/condition is absent, leave that scenario not exercised.

## SL-18 — Complete The Sir Loke V1 Paper Story

**Depends on:** SL-03, SL-07, SL-12, and SL-17, including outstanding live cases from those tasks.
**Implement:** only integration defects found in the existing paths; no new subsystem or wholesale
repetition of accepted offline proofs. Use the product's full
[end-to-end criteria](../product/sir-loke-v1.md#end-to-end-acceptance) as the coverage checklist.
**Markeitect live test:** review three separate bounded scenarios: supported recommendation through
manual entry/monitoring/report; insufficient/conflicting evidence with abstention; independent
manual trade with prompt provisional assessment, completed assessment, monitoring, and report.
Record coverage of partials/scaling/amendments, account identity, original/revised thesis,
acknowledgement/cooldown, concurrent opportunities, restart, failure isolation, and no execution.
Reuse accepted evidence for the same head/behavior where still applicable; test integration changes
and missing cases. Markeitect alone decides whether the complete V1 product is accepted.

## Broker Safety Gate

The former Gate 1 is now a dependency of SL-04 through SL-07 and broker-dependent behavior, not a blanket
prerequisite for Discord or model implementation. Gate 1A remains completed only within its
[recorded offline scope](../reference/ib-observation-gate1.md). Do not repeat unchanged construction
proofs or infer manual-event visibility from them.

The existing [conditional paper protocol](../reference/ib-observation-gate1.md#conditional-gate-1-paper-protocol)
and [IB setup boundary](../operations/ib-setup.md) remain mandatory for broker observation.
Resolve named startup/report/account concerns and audit actual outbound requests before the probe.
Markeitect verifies paper account, TWS settings, client identity, allowed requests, and exact scope,
performs every manual order action, starts/stops the observer, and reviews the evidence.
Unexpected binding, submission, modification, cancellation, replacement, exercise, wrong account,
or loss of the no-control audit stops the run. A negative result does not authorize a workaround.

## Scope Of This Replan

This sequence supersedes the former Gate 1–7 ordering and its prohibition on early bot/model
implementation. It changes delivery dependencies, not the full Sir Loke product, provider ownership,
no-execution rule, raw-data retention policy, or evidence standards. No broker, market, options,
model, Discord, or persistence behavior becomes implemented or accepted by changing this document.
Optional GEX, vendor flow, UI, optimization, and unrelated tooling remain in the
[development backlog](development-backlog.md) until a named product task needs them.
