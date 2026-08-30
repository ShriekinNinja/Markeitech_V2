# Desired Runtime Architecture Council Review Handoff

**Prepared:** 2026-08-29

**Branch:** `v3-es-progressive-capability-review`

**Starting commit:** `76451f69b5a879dd9e81073414a3174a23e85bcc`

**Status:** Completed historical handoff record; informative only and not an active instruction

The review authorized by this handoff completed on 2026-08-29. Preserve this file as evidence of
the review scope and process. Do not execute it again, treat its requested report structure as a
roadmap, or infer new implementation authority from it unless Markeitect explicitly reopens the
review.

## Objective

Review Markeitect's broad desired-runtime requirements against the current Markeitech V2 runtime,
accepted architecture, and accepted future plans. Identify what is already supported, what can be
reused or extended, what is only planned, what is missing, and which accepted constraints conflict
with or materially weaken the desired runtime. Produce one evidence-backed report for Markeitect's
review before any architecture decision or implementation plan is accepted.

This review is intended to clarify the destination and the smallest coherent path toward it. It is
not an instruction to redesign the whole system, implement code, select trading rules, activate a
provider connection, or approve automated execution.

## Primary Requirement Source

Read [`desired-arch.md`](desired-arch.md) as the working statement of Markeitect's desired runtime.
Its requirements currently cover:

- live market evidence and intelligence for one or more AI agents;
- an initially advisory system which does not preclude separately governed future execution;
- high-priority risk control focused on containing the impact of being wrong;
- initial support for SPX 0DTE options, SPY/QQQ 0-3 DTE options, and ES/NQ futures without making
  those products permanent architectural limits;
- a dynamic runtime observation universe and policy-governed agent requests for instruments,
  data, capabilities, parameters, timeframes, and bounded analytical work;
- top-down, multi-timeframe analysis from broad context to optional order-flow refinement; and
- freshness-aligned, multi-instrument context and relationships without encoding today's examples
  as permanent causal rules.

The document is broad design intent, not accepted implementation authority. Do not fill its open
areas with invented product semantics.

## Authority And Evidence Sources

Read the repository authorities in their required order before consulting advisors or drafting the
report:

1. [`../../markeitech.md`](../../markeitech.md)
2. [`../current-status.md`](../current-status.md)
3. [`../development-guidelines.md`](../development-guidelines.md)
4. [`../README.md`](../README.md)
5. [`../architecture/markeitech-advisor-council.md`](../architecture/markeitech-advisor-council.md)
6. [`../architecture/v2-adaptive-market-data-plane.md`](../architecture/v2-adaptive-market-data-plane.md)
7. [`../roadmap/v2-market-events-live-agent-plan.md`](../roadmap/v2-market-events-live-agent-plan.md)
8. [`desired-arch.md`](desired-arch.md)

Inspect the current implementation and nearby tests where they are needed to distinguish current
behavior from documents, plans, or assumptions. `docs/current-status.md` is the current
implementation ledger; roadmaps and desired architecture are not proof that a capability exists.

## Review Rules

- Preserve the categories `verified fact`, `measured evidence`, `inference`, `hypothesis`,
  `recommendation`, and `unknown`.
- Compare every desired requirement with current implementation, accepted future intent, and
  relevant constraints. Classify support as `SUPPORTED_NOW`, `PARTIAL`, `PLANNED`, `MISSING`,
  `CONFLICTING`, or `UNKNOWN` and cite the evidence for the classification.
- Do not assume that an earlier requirement or constraint is permanently correct merely because it
  is accepted. When it conflicts with the desired runtime, explain its known purpose, the effect of
  retaining it, the risks and benefits of revising or removing it, and the decision Markeitect
  needs to make.
- Do not silently override an accepted requirement. A proposed change remains a proposal for
  Markeitect's decision.
- Make a best effort to reuse accepted runtime capabilities, ownership boundaries, tests,
  integrations, and operational knowledge. Prefer the smallest coherent change set which satisfies
  the desired requirements without preserving a known contradiction.
- Do not force reuse when semantics, authority, fidelity, risk, or structural limits are
  incompatible. Explain why adaptation is insufficient and identify what can still be retained.
- Treat configurability and controlled optimization readiness as system-wide requirements even
  where `desired-arch.md` does not repeat them. Keep truth, authorization, risk, and audit
  invariants deterministic.
- Treat current advisory-only and no-order-routing boundaries as current verified posture. Future
  execution is a separate possible destination requiring explicit risk, account, permission,
  approval, reconciliation, and kill-switch design; this review does not authorize it.
- Do not turn examples such as VIX/CL/SOXL/NQ/ES relationships into fixed trading rules.
- Do not turn minute bars or bar-derived volume into observed order flow.
- Do not perform a connected IB run, consume provider capacity, use PostgreSQL, change services,
  edit code or configuration, install dependencies, mutate external state, commit, or push.

## Kite Activation And Fresh-Task Gate

Explicitly activate Kite through `$kite:markeitech-advisor-router`. Before relying on any council
result, verify that the installed plugin and current task expose policy `2026-08-29-v3` and that all
eight selected custom roles below are configured as `gpt-5.6-sol` with `xhigh` reasoning.

If the fresh task does not expose those exact effective role settings, record the mismatch and stop
before the council review. Repository configuration or installation state alone is not proof of
effective role loading.

The consultation contract is read-only. Current custom-role sandbox declarations are not accepted
as proof of technical tool isolation, so the primary task must also preserve the no-mutation
boundary. If an advisor attempts or requires mutation, authenticated access, secrets, paid
capacity, or a connected runtime, stop the affected conclusion.

## Approved Advisor Set And Exact Questions

Use exactly these eight custom roles for this first broad gap review. Each owns the stated question
and returns evidence and recommendations only.

1. `markeitech_architecture_boundaries_advisor`
   - Which current owners, component boundaries, and accepted plans already support the desired
     runtime; where are authority duplicated, misplaced, over-combined, or structurally limiting;
     and what is the smallest coherent topology change implied by the requirements?
2. `markeitech_nautilus_advisor`
   - For every materially affected framework boundary, what does installed NautilusTrader
     `2.0.0rc3` and current primary documentation provide natively, what current Markeitech use is
     aligned, and where is a custom Markeitech capability actually justified?
   - This advisor must invoke its bundled Nautilus specialist skill and complete the mandatory
     native-capability census and Nautilus Alignment Matrix.
3. `markeitech_data_quality_lineage_advisor`
   - What identity, UTC clock, session, timeframe, historical/live, revision, completeness,
     freshness, alignment, and fidelity contracts are required for honest multi-timeframe and
     cross-instrument intelligence, and which of them are present, partial, absent, or conflicting?
4. `markeitech_market_structure_advisor`
   - Which existing market-structure primitives can support configurable top-down, multi-horizon
     analysis; what broader-timeframe, analytical-window, relationship, or lifecycle semantics are
     missing; and what forbidden interpretations must remain explicit?
5. `markeitech_market_microstructure_order_flow_advisor`
   - What true trade, quote, book, classification, liquidity, delta/CVD, and effort-response
     evidence would be required for optional entry refinement; what can current feeds support
     honestly; and which bar-based or incomplete inputs must remain separately named proxies?
6. `markeitech_event_driven_architecture_advisor`
   - What delivery, ordering, idempotency, admission, backpressure, retry, expiry, recovery, and
     partial-failure contracts are required for dynamic observation, capability activation,
     historical work, focus leases, and agent requests without disturbing unrelated live work?
7. `markeitech_statistical_learning_optimization_advisor`
   - What feature, as-of, label, leakage, calibration, uncertainty, drift, monitoring, and governed
     optimization boundaries must the broad architecture preserve now; which current retention and
     evaluation constraints create future gates; and what should remain explicitly deferred?
8. `markeitech_live_agent_governance_advisor`
   - What typed intent, delegated-authority, approval, evidence-admission, readiness, abstention,
     audit, resource-governance, and no-execution boundaries are required for one or more live
     agents now and for separately authorized execution later?

This exact set was selected and approved for broad architectural coverage. It does not authorize
these roles to decide provider-specific IB limits, option-contract mechanics, portfolio/account
risk, execution mechanics, legal or licensing questions, semantic-event meaning, quantitative
formula validity, final evidence fitness, security controls, persistence mechanics, or visual
presentation. If one of those excluded domains becomes material to a conclusion, identify the
missing coverage and stop or narrow that conclusion honestly; do not silently add an advisor or
substitute general knowledge.

## Consultation Order And Handoffs

Record the selected-role dependency graph before consultation. Use this case-specific order unless
the router identifies an evidence-backed reason to change it:

```text
architecture boundaries
    -> Nautilus alignment
        -> data quality and lineage
        -> event-driven architecture

data quality and lineage
    -> market structure
    -> market microstructure and order flow
    -> statistical learning and optimization

architecture + event delivery + data quality + market domains + statistical governance
    -> live-agent governance
    -> primary Kite synthesis
```

Independent branches may be consulted concurrently after their prerequisites are satisfied. Each
handoff must preserve upstream dispositions without upgrading missing, partial, inferred, or
unverified evidence.

## Required Report

Write the final council synthesis to:

[`desired-arch-council-review-report.md`](desired-arch-council-review-report.md)

The report should be understandable without reading the task transcript and should contain:

1. scope, authority, evidence date, branch/commit, and review limitations;
2. an executive disposition which states whether the desired direction is broadly compatible with
   the current foundation and names the largest blockers without implying approval;
3. a requirement-to-current-state matrix using the required support classifications;
4. a reuse inventory distinguishing implemented-and-verified capabilities, implemented but
   insufficient capabilities, accepted plans, and missing capabilities;
5. the eight advisor dispositions, including their material evidence, disagreements, stop gates,
   and unknowns;
6. a constraint review with `RETAIN`, `REVISE`, `REMOVE`, or `INVESTIGATE` recommendations, the
   original purpose where known, consequences of retaining the constraint, and decision authority;
7. a broad target architecture in words only, with clear ownership and authority boundaries but no
   low-level implementation design;
8. the smallest coherent staged path from current V2 to the desired runtime, identifying reuse,
   prerequisites, explicit decision gates, acceptance evidence, and separately deferred work;
9. risks and missing specialist coverage, especially account/portfolio risk and any future
   execution authority; and
10. a short list of questions requiring Markeitect's decision before a detailed architecture or
    implementation plan can be approved.

Do not post the substantive report into either task transcript. The file is the review artifact.
The task may report only the file path, advisor-execution status, verification performed, and any
blocking limitation.

## Working-Tree Preservation

The fresh task must start from this task's current working tree, not from the repository's default
branch or clean `HEAD`. At handoff preparation time, the worktree intentionally contained:

- uncommitted xhigh profile changes for the eight selected `.codex/agents`;
- uncommitted Kite policy, validator, tests, routing fixture, cachebuster, council architecture,
  and current-status updates for policy `2026-08-29-v3`;
- the untracked [`desired-arch.md`](desired-arch.md);
- user-owned, unrelated or earlier-batch changes in
  [`v3-es-visual-debug-review-handoff.md`](v3-es-visual-debug-review-handoff.md); and
- no council report yet.

Do not clean, reset, revert, reformat, stage, commit, or otherwise absorb unrelated files. The only
authorized repository write in the new task is the required council report file. Leave that report
uncommitted for Markeitect's review.

## Completion And Stop Conditions

The review is complete only when all eight required consultations succeeded at the required model
and reasoning setting, the primary task reconciled their evidence against current repository
authority, and the report exists at the required path with no other new mutation.

Stop the affected conclusion, and state the reason in the report, if:

- a required role, skill, source, installed contract, or current implementation evidence is
  unavailable or stale;
- the source plugin and installed plugin materially disagree;
- an advisor fails, times out, or returns partial evidence material to the conclusion;
- two authorities conflict and Markeitect must decide;
- missing specialist coverage could change the conclusion; or
- completing the conclusion would require implementation, a connected service, secret access,
  paid capacity, external mutation, or an unapproved architecture decision.

Do not mark the desired architecture accepted merely because the report is complete. The next step
is Markeitect's review of the report and explicit decisions on its recommendations and questions.
