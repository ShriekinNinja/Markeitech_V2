# Sir Loke V1 Delivery Plan

**Direction approved:** 2026-09-08 — build analytical competence through small live increments;
guardian behavior follows demonstrated trading value.
**Implementation:** No task below is claimed implemented or live-accepted by this planning change.
**Next task:** SL-01. This plan does not authorize implementation of every listed task.

The [product definition](../product/sir-loke-v1.md) remains the full V1 release contract.
The [current status](../current-status.md) owns implementation evidence, and the
[Sir Loke boundaries](../architecture/sir-loke-v1-boundaries.md) own component and tool authority.
A conversational increment is useful progress toward that product; it is not full V1 acceptance.

## Product Progression And Next Task

Build a trading intelligence companion with greater sustained observation, computation, memory,
and simultaneous scenario coverage than one operator can maintain. The bot is the first working
surface. Strong analytical observation, useful trade assessment, and earned guardian behavior
are the development direction. A current-price narrator or repeated confirmation prompt is not
that outcome. See the product's [analytical standard](../product/sir-loke-v1.md#analytical-competence-before-guardianship).

| Priority | Work | Result Markeitect evaluates live |
|---|---|---|
| 1 | SL-01, then SL-02 | Talk to the real bot about actual current observations |
| 2 | IN-01 first; then IN-02 through IN-08 and newly justified intelligence tasks | Increasingly capable, continuous market understanding |
| 3 | SL-15, SL-13, SL-14, SL-16, according to their dependencies | Evidence-backed setups, expression suitability, and useful trade assessments |
| 4 | SL-04 through SL-08, and SL-07 recovery, when broker awareness becomes the current need | Facts about actual paper trades and the trader's plan |
| 5 | Analytical trust decision, then SL-09 through SL-12 and SL-17 | Informed monitoring, challenge, and reporting grounded in accepted intelligence |
| 6 | SL-18 | Complete paper product acceptance |

SL-03 is available when conversation recovery blocks useful live observation; basic failure
isolation is part of every affected task. A broker fact notification remains factual observation;
it does not qualify Sir Loke to judge a trade. Broker work does not displace intelligence by default.

For “implement the next task,” inspect accepted results and the selected next task from the last
review. The initial queue is SL-01, SL-02, IN-01, then IN-02. After each intelligence run, the agent
recommends the next concrete capability or assessment task from observed gaps and available inputs;
Markeitect decides on material priority changes. If no selection is recorded, propose the next
eligible IN card in listed order with a specific reason. Research belongs inside that task.

The table establishes focus, not a requirement to finish an entire intelligence catalogue. Once
a setup's required evidence is accepted, SL-15 and the relevant options/assessment tasks may run;
intelligence development continues afterward. The catalogue is deliberately open-ended. Task
numbers preserve identity, not a global serial dependency. Agents must not jump from SL-03 to
broker/acknowledgement work merely because the old SL numbers appear sequential.

## Intelligence Development Loop

IN-01 through IN-08 are concrete starting capabilities, not a claim that the complete intelligence
set is known or that these calculations establish an edge. The backlog must evolve with live use.

1. **Choose a market question.** Use Markeitect's latest review, a missed observation, a misleading
   explanation, or a named limitation. The agent proposes the capability and its expected added
   value; do not ask Markeitect to design an indicator list or supply the implementation recipe.
2. **Resolve only that task's uncertainty.** Inspect reusable code and source availability; research
   the relevant native/provider contract or analytical method when needed. Propose exact inputs,
   definitions, settings, interpretation limits, and a runnable scope in the short brief. An
   indicator or new feed needs a named question it will answer. There is no general research gate.
3. **Build and expose it in Sir Loke.** Include the calculation, current state/change detection,
   explanation, and minimal audit needed by the chosen behavior. Facts and deterministic transitions
   remain code-owned; interpretations and alternative hypotheses remain labeled. A candidate
   interpretation can be evaluated live without being admitted as trade advice.
4. **Markeitect runs and judges it.** In addition to factual correctness, he judges whether the
   observation was useful, timely, redundant, misleading, or missing something material. Agents
   provide a short before/after example, not a test-count claim. No result is marked useful for him.
5. **Select the next improvement.** With results he supplies, the agent proposes one concrete task:
   add a missing capability, improve an existing one, investigate a misleading conclusion, or retire
   a noisy one. Record the chosen task and dependency in the plan/issue. New intelligence work is
   normal product development, not automatically deferred until the guardian is complete.

For each selected new task, use `IN-09` onward with a specific question/title, exact implementation
scope, dependencies, named checks, and Markeitect's live scenario. Do not create a generic “develop
intelligence” issue or an offline-only research task with no consuming live behavior. If evidence
shows a proposed capability is unavailable, report that blocker and a concrete alternative; do not
fake a live result. Changing data sources, formulas, policy, or retention still requires approval
for that task, not speculative approval of every future capability.

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

## IN-01 — Put Price In Its Session Context

**Depends on:** SL-02.
**Question:** Where are we trading relative to this session and the last completed session?
**Implement:** current-session open/high/low, previous-session high/low/close, and price location
relative to those references for one evidence instrument. The brief proposes exact session and
history coverage. Reuse `session_references.py` calculations where valid and integrate only the
required completed-bar/reference path; full V3 owner replacement is not a prerequisite.
**Focused checks:** session boundary, incomplete history, and exact reference/source identity.
**Markeitect live test:** ask “Where are we in today's session?” Compare the cited levels with the
same-session chart and ask again after a range change. Sir Loke must explain the changed location,
not list numbers without context. Review whether the reference map helps orient the trading day.

## IN-02 — Describe The Developing Price Structure

**Depends on:** IN-01.
**Question:** What structural progression is actually established, and what is still forming?
**Implement:** confirmed swings and their relationships on one chosen timeframe, using reviewed
confirmation rules. Reuse valid `market_structure_entities.py` logic; keep developing observations
separate from confirmed structure and preserve when confirmation became knowable.
**Focused checks:** confirmation delay, equal pivots, gaps, and chronological availability.
**Markeitect live test:** ask for the latest structural progression and its counterevidence. Review
marked levels/times against the chart as it develops; a later pivot must not rewrite earlier advice.
Judge whether the explanation identifies something material beyond the latest price direction.

## IN-03 — Distinguish Directional Progress From Range Expansion

**Depends on:** IN-01.
**Question:** Is price making sustained directional progress, rotating, or simply moving farther?
**Implement:** one bounded range/volatility comparison and one directional-progress measurement;
propose formulas, lookbacks, and a compatible baseline in the brief. Reuse valid rolling logic,
fixing relevant known defects only. Keep measurements distinct from provisional regime labels.
**Focused checks:** predecessor dependence, baseline sufficiency, units, and missing data.
**Markeitect live test:** ask what changed in movement character during a bounded live window.
Compare the cited changes with the same bars and assess usefulness; do not equate larger bars with
trend strength or publish a regime conclusion when the selected evidence does not establish it.

## IN-04 — Follow One Interaction With An Important Level

**Depends on:** IN-01 and IN-02.
**Question:** What happened after price reached a session or structural reference?
**Implement:** a time-ordered account of approach, crossing, and subsequent behavior at one
identified level. Propose a single bounded hold/reclaim/failure interpretation rule; distinguish
observed crossings from that interpretation. Continue watching the same event rather than emit a
new unrelated narrative on every update.
**Focused checks:** event identity, transition timing, expiry, and repeated-touch handling.
**Markeitect live test:** select a nearby admitted level before interaction, watch its live sequence,
and compare Sir Loke's updates with it. Judge whether the updates notice a meaningful change in time.
An interaction that never occurs remains not exercised; it is not manufactured by moving the level.

## IN-05 — Compare Two Timeframes Without Collapsing Them

**Depends on:** IN-02 and IN-03.
**Question:** Is the short-term move consistent with, or opposed to, the broader structure?
**Implement:** compare the existing analysis on two explicitly chosen horizons for the same
instrument. Preserve each horizon's confirmation time and uncertainty; add only the second series
and comparisons needed. No single directional score may conceal disagreement.
**Focused checks:** alignment, incomplete coarser bars, and independent warmup.
**Markeitect live test:** ask how the near-term move fits the broader context, then ask what would
change that assessment. Check both cited horizons and judge whether the distinction improves it.

## IN-06 — Watch Two Related Markets Together

**Depends on:** IN-03 and IN-05.
**Question:** Does a second relevant market support or contradict the observed move?
**Implement:** one explicitly selected evidence-instrument pair, matched observation horizons, and
one reviewed comparison of relative movement or structure. Approve feeds and comparison units;
use existing acquisition ownership. A relationship is evidence of agreement/divergence, not proof
of leadership, causation, or an automatic trading signal.
**Focused checks:** time/session alignment, unequal units, and one stale leg.
**Markeitect live test:** ask what the second market adds while both are observed continuously.
Compare each side and a subsequent update. Judge whether Sir Loke catches relevant disagreement
that would require switching attention manually; mark the limits of the sampled pair/session.

## IN-07 — Remember How The Session's Assessment Changed

**Depends on:** IN-04 and IN-05.
**Question:** What changed since the earlier assessment, and which earlier assumption stopped fitting?
**Implement:** a bounded chronological account of admitted observations, analytical events, and
Sir Loke's hypotheses/revisions. Approve the minimal semantic audit and retention needed; raw-feed
storage and backtesting remain out of scope. Distinguish “we expected” from “we observed.”
**Focused checks:** as-of ordering, immutable original assessment, revision references, and recovery.
**Markeitect live test:** ask for an assessment, revisit it after new live evidence, then restart
and ask what changed. Review the original and revised explanations; hindsight must remain visible.

## IN-08 — Track Competing Scenarios And Surface Material Changes

**Depends on:** IN-04, IN-06, and IN-07.
**Question:** Which explanations still fit, what contradicts each, and what should we watch next?
**Implement:** two simultaneous, evidence-cited market hypotheses with named confirmation,
contradiction, and expiry conditions. Add one bounded proactive update on a material transition,
with an explanation of what changed and why it matters. Preserve unresolved alternatives and
independent opportunities. The brief defines significance and alert limits; no order advice yet.
**Focused checks:** contradictory evidence, separate scenario identity, stale inputs, and alert churn.
**Markeitect live test:** record both scenarios before the outcome, continue a bounded live session,
and inspect updates and expiries. Judge incremental insight, timeliness, missed evidence, and noise.
Persuasive hindsight or a stream of generic caution does not pass the usefulness review.

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

## SL-09 — Explain And Monitor A Thesis Invalidation

**Depends on:** SL-02, SL-08, SL-16, and Markeitect's analytical trust decision.
**Implement:** monitor one approved thesis-invalidation condition from the accepted setup/analysis
against the trader's declared plan and current evidence. Explain supporting and opposing evidence,
what materially changed, and the justified advisory response. A price threshold may be one input;
a threshold reminder by itself does not establish analytical supervision. Missing/stale evidence
suspends the affected judgment and must be stated.
**Focused checks:** condition boundary, freshness, and one intervention per transition.
**Markeitect live test:** observe a bounded paper-test thesis transition and inspect why the
assessment changed, its evidence, and the timely proposed response. Generic “are you sure?” prompts
or repetition of the declared stop do not pass. If no relevant transition occurs, do not pass.

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

## SL-15 — Develop One Evidence-Backed Setup Assessment

**Depends on:** IN-04 and the specific accepted intelligence needed by the selected setup.
IN-08 is required when the setup uses competing scenarios; unrelated IN cards do not block it.
**Implement:** qualifying, conflicting, trigger, invalidation, and expiry evidence for one concrete
setup, exposed through Sir Loke. The agent proposes that setup from available evidence and the
observed analytical gaps, explains its limitations, and owns the technical decomposition.
Markeitect decides on the proposal; he is not expected to design the strategy or indicator list.
Any missing analytical capability becomes a named IN task with its own live output and review.
Selection of a setup is permission to evaluate that definition, not a claim of trading edge.
**Focused checks:** rule boundaries, prospective evidence availability, and honest non-qualification.
**Markeitect live test:** review a setup assessment before the outcome and compare its trigger,
counterevidence, and invalidation with subsequent events. Include unsuccessful and non-qualifying
cases in the bounded review; record what Sir Loke added and where his assessment was wrong or late.

## SL-16 — Recommend Or Abstain On A Qualified Expression

**Depends on:** SL-13, SL-14, and SL-15.
**Implement:** bind an independently qualified opportunity to eligible SPXW/QQQ candidates; publish
versioned evidence, conflicts, entry condition, invalidation, expiry, and approved risk context,
or a named abstention. Support distinct opportunity identities; no fabricated facts or model-only
eligibility. Approve the minimum evidence/risk contract before exposing recommendations.
**Focused checks:** qualified and insufficient/conflicting cases, expiry, and plural candidates.
**Markeitect live test:** record the assessment before its outcome, compare it with Markeitect's
contemporaneous judgment when he chooses to record one, and review subsequent evidence. A real
qualified recommendation and a separate honest abstention are both required for full acceptance;
no forced trade or changed threshold to manufacture either. Record benefit, misses, and false
confidence, not just whether the fields were populated. The analytical trust decision below uses
these prospective observations; it is a separate Markeitect verdict, not automatic on task completion.

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

## Analytical Trust Decision

Before SL-09 through SL-11 guardian behavior, Markeitect must explicitly accept that Sir Loke's
live analytical/trade assessments add enough value to justify supervising his decisions in a
named scope. This is a product-usefulness decision from actual runs, not another offline proof
program. Conversation delivery, a correct indicator, account visibility, or a firm tone cannot
satisfy it. Factual broker notifications may work before it; guardian judgments may not.

From the intelligence tasks onward, preserve a small prospective review record: what Sir Loke
said before the outcome, its cited evidence and horizon, what later happened, what he missed or
misread, and Markeitect's judgment of its incremental value. Compare useful discoveries,
contradictions caught, timeliness, simultaneous coverage, uncertainty, and needless interruptions.
Include failures and quiet/missed cases as well as successes; avoid selecting only convincing
examples. Agree the bounded live review window and useful criteria in the task brief, then let
Markeitect judge the results. Do not fabricate a universal score or a statistical superiority claim.

The ambition is to surpass Markeitect's unaided trading judgment through capabilities that one
human cannot sustain simultaneously. That ambition must be earned in live use. If the evidence
is insufficient, continue the intelligence loop with a concrete improvement task; do not substitute
acknowledgement and cooldown machinery for missing analytical competence. Acceptance is scoped
and can be withdrawn if live behavior stops supporting it. No execution authority follows from it.

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
implementation. It retains the full Sir Loke experience and requires demonstrated analytical
usefulness before guardian behavior. Provider ownership, the no-execution rule, raw-data retention
policy, and evidence standards remain intact. No broker, market, options, model, Discord, or
persistence behavior becomes implemented or accepted by changing this document.
Additional intelligence methods and sources remain in the
[development backlog](development-backlog.md) as candidates to promote through the intelligence
loop, not capabilities deferred until after guardianship. UI, optimization, and unrelated tooling
still require a concrete product need. No particular indicator list is the definition of intelligence.
