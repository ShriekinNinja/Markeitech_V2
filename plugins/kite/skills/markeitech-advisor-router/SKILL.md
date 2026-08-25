---
name: markeitech-advisor-router
description: Route substantive Markeitech work to the repository advisor council with explicit domain ownership, dependency ordering, stop gates, and conflict handling. Use before domain-specific planning, design, implementation, review, analysis, or research; do not delegate trivial repository operations or ordinary conversation.
---

# Markeitech Advisor Router

Kite owns advisor selection and orchestration. Markeitect describes the real task normally and
never needs to name this router or a specialist. Advisors supply read-only analysis; they do not
accept architecture, product, trading, review, release, or implementation decisions.

## Mandatory Routing Contract

Before substantive domain work:

1. Read current repository authority, inspect the branch/worktree, and identify the decision,
   consequence, required evidence, material domains, and unknowns.
2. Read [references/council-routing-contracts.md](references/council-routing-contracts.md). Select
   only materially relevant advisors and build dependency edges from its route contracts.
3. Classify each material domain `AVAILABLE`, `MISSING`, or `NOT_NEEDED`. A similarly named skill
   is coverage only when its contract owns the exact decision and it can inspect the required
   evidence.
4. Delegate every `AVAILABLE` domain through its exact project custom-agent role. Do not use a
   generic direct-skill fallback when a custom role exists.
5. Execute the dependency graph deterministically. Preserve each advisor's evidence labels and
   exact disposition; never let a downstream advisor upgrade an upstream `UNKNOWN`, rejection, or
   stop gate.
6. Reconcile the columns as primary Kite. Specialists never delegate, accept another specialist's
   decision, or claim canonical authority outside their route.

Use [references/routing-evaluation.md](references/routing-evaluation.md) only for router QA. Its
designed cases and static results are not installed fresh-task evidence.

## Default Dependency Order

Apply only the relevant tiers:

1. architecture and authority ownership;
2. framework and provider contracts;
3. runtime delivery and concurrency;
4. persistence and data-quality boundaries;
5. quantitative validity and final evidence fitness;
6. market semantics, including structure, microstructure, and accepted semantic lifecycle;
7. options mechanics and vendor options-flow interpretation;
8. named-candidate risk;
9. statistical learning and bounded optimization;
10. live-agent governance; and
11. evidence projection and visualization.

Within one tier, explicit evidence dependency wins. Genuinely independent consultations may run
concurrently; stable custom-role name is only a deterministic tie-breaker and does not create
semantic precedence.

Security and licensing are cross-cutting preconditions:

- consult `markeitech_security_tool_boundary_advisor` before a consequential recommendation that
  introduces or changes secrets, permissions, tools, dependencies, credentials, network surfaces,
  external services, logging/redaction, or safe-failure behavior;
- consult `markeitech_vendor_data_licensing_provenance_advisor` after exact source/vendor identity
  is established and before recommending acquisition, external processing, retention,
  redistribution, display, derived-data use, or agent/model use.

## No Cycles Or Duplicate Authority

- Only primary Kite invokes advisors.
- Advisors return `REQUIRED_HANDOFF` with the exact question and evidence; they never invoke one
  another.
- Record selected role IDs, dependency edges, required inputs, completion state, and dispositions.
- Invoke a role once per scoped question. A bounded follow-up is allowed only when new evidence
  materially changes the question and the router records why it is not recursive delegation.
- No two advisors may fill the same canonical semantic column. Preserve a conflict and stop rather
  than averaging or choosing the convenient answer.
- Architecture may census ownership first. A second architecture consultation is justified only
  when specialist evidence leaves materially different owner candidates.

## Stop And Escalation Gates

Stop the affected consequential conclusion when:

- tracked authorities materially conflict;
- a required custom role, bundled skill, current primary source, exact contract, or raw artifact
  is unavailable or stale;
- a required upstream disposition is absent, conflicting, or `UNKNOWN` and can change the result;
- two advisors claim the same scoped authority or authorized writer;
- source plugin and installed cache differ for a claim about installed routing;
- provider documentation and measured behavior materially conflict;
- security, licensing, legal, execution, account-risk, or another required specialist is missing;
  or
- an advisor recommends action outside its read-only authority.

Unresolved canonical-owner, product-semantic, or competing-authority conflicts return
`REQUIRES MARKEITECT DECISION`. Name the smallest evidence or decision that could release the
gate. Continue only independent portions whose conclusions cannot be changed by the gap.

For missing coverage, return:

```text
Advisor check: MISSING
Domain: <subject>
Proposed advisor: markeitech-<domain>-expert
Why: <consequential decision or failure mode>
Gate: Awaiting Markeitect approval to create it or proceed without it.
```

Do not create or broaden coverage without approval. Consultation never grants permission to edit,
commit, push, connect services, consume paid data, mutate persistence, or make a product decision.

Read [references/advisor-design.md](references/advisor-design.md) only when Markeitect approves a
new or materially changed specialist.
