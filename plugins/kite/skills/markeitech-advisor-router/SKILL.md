---
name: markeitech-advisor-router
description: Automatically assess specialist-advisor coverage before substantive Markeitech domain work, invoke an available advisor, or briefly identify missing specialist coverage for Markeitect's approval. Kite must use this proactively for planning, design, implementation, review, analysis, or research that depends on subject-specific expertise; Markeitect never needs to mention or invoke the router. Do not use for trivial repository operations or ordinary conversation.
---

# Markeitech Advisor Router

Run an advisor-coverage check automatically before substantive domain work. The purpose is to
expose missing expertise before general engineering judgment hardens into a product, market,
provider, data, or framework decision. Advisor selection is Kite's internal responsibility:
Markeitect must be able to describe the real task normally and must never be asked to name or invoke
this router.

## Coverage Check

1. Identify the material subject domains, decision stakes, required evidence, and important
   unknowns in the request.
2. Inspect the currently available Kite skills and other applicable specialist skills. Prefer the
   known plugin skill catalog and targeted scope checks; do not perform broad filesystem, memory,
   or network searches merely to prove that an advisor is absent. A similarly named skill is
   coverage only when its stated scope includes the current decision and it can inspect the
   required authority and evidence.
3. For each material domain, classify coverage as:
   - `AVAILABLE`: name and consult the applicable specialist before substantive planning or edits,
     using its project custom-agent role when one is defined.
   - `MISSING`: recommend a specialist advisor and stop before a consequential domain decision or
     edit until Markeitect approves creating it or explicitly chooses to proceed without it.
   - `NOT_NEEDED`: reserve this for trivial, administrative, or genuinely domain-neutral work and
     state why specialist judgment cannot materially change the outcome.
4. When several domains apply, identify all of them and prioritize consultation by risk. One
   advisor must not impersonate expertise outside its contract.

Routine routing is silent. Do not print a coverage banner for `AVAILABLE` or `NOT_NEEDED` unless the
consultation materially changes the recommendation, reveals a risk, or provides evidence useful to
Markeitect. For `MISSING`, stop with only this compact gate:

```text
Advisor check: MISSING
Domain: <subject>
Proposed advisor: <skill name>
Why: <one sentence naming the consequential decision or failure mode>
Gate: Awaiting Markeitect approval to create it or proceed without it.
```

## Delegated Specialist Consultation

For available NautilusTrader coverage, delegate one narrow, read-only consultation to the
project-scoped `markeitech_nautilus_advisor` custom agent and wait for its result before substantive
planning or edits. The delegated prompt must state the real task, the bounded decision or review
question, the relevant repository scope, and the evidence expected. Do not prescribe the desired
answer or ask the advisor to make changes.

For available Interactive Brokers market-data provider-truth coverage, delegate one narrow,
read-only consultation to the project-scoped `markeitech_ib_market_data_advisor` custom agent and
wait for its result before making the affected provider recommendation. That advisor owns IB
contract identity, entitlements, delivery modes, request semantics, provider limits, sessions, and
provider failures. It does not own Nautilus adapter or Markeitech runtime behavior.

For consequential PostgreSQL schema objects, migrations, constraints, indexes, queries, database
transactions, retention mechanics, backup, restore, or database-observability work, delegate one
narrow, read-only consultation to the project-scoped `markeitech_postgres_persistence_advisor`
custom agent and wait for its result before making the affected PostgreSQL recommendation. The
logical durability requirement, canonical component owner, semantic meaning, and end-to-end event
or runtime execution contract remain with their applicable authorities and specialists.

For available statistical-learning coverage, delegate a narrow, read-only consultation to the
project-scoped `markeitech_statistical_learning_optimization_advisor` custom agent before a
consequential feature/label, leakage, evaluation, calibration, model-monitoring, or bounded-
optimization recommendation. If analytical feature correctness is unresolved, consult the
market-evidence validation advisor first and provide its exact disposition to the statistical
advisor without upgrading the evidence class.

The custom agent owns invocation of the bundled `$kite:markeitech-nautilus-v2-expert` skill and its
native-capability and alignment gates. Kite remains responsible for checking the returned evidence
against tracked authority and the current checkout. Do not duplicate the specialist consultation in
the primary thread merely to obtain a preferred conclusion.

The IB custom agent owns invocation of the bundled `$kite:markeitech-ib-market-data-expert` skill
and its provider-truth and handoff matrices. When a request combines IB capability with Nautilus
adapter or runtime use, consult both advisors in bounded scopes. Only the Nautilus advisor may fill
adapter evidence authoritatively; the primary Kite agent reconciles the results and remains
responsible for the recommendation.

The PostgreSQL custom agent owns invocation of the bundled
`$kite:markeitech-postgres-persistence-expert` skill and its database evidence and decision matrix.
When a request combines PostgreSQL with Nautilus ownership, component boundaries, semantic-evidence
meaning, event delivery, or Python runtime execution, consult each applicable advisor in a bounded
scope. The primary Kite agent reconciles the results without allowing one advisor to fill another's
evidence column.

If the custom role cannot be spawned, cannot load its required skill, or cannot inspect a required
source, report that limitation and stop before the consequential NautilusTrader decision or edit.
Apply the same gate to the affected IB provider decision when the IB custom role cannot be spawned,
cannot load its required skill, or cannot inspect a required current provider or venue source.
Apply the same gate to the affected PostgreSQL recommendation or edit when its custom role cannot be
spawned, cannot load its required skill, or cannot inspect the current schema, migration history,
driver/server contract required by the question, or relevant current primary source.
Apply it to the affected statistical-learning conclusion when that custom role cannot be spawned,
cannot load its skill, or cannot inspect the approved data strategy and evidence it requires.

For another available specialist without a defined custom-agent role, invoke its skill directly
until Markeitect approves a corresponding delegated role.

## Missing Advisor Proposal

Internally define a proposed name such as `markeitech-<domain>-expert`. Do not emit a full advisor
specification during routine routing. Expand the following contract only when Markeitect asks for
details or approves creating the advisor:

- the exact questions and decisions it owns;
- the tracked project authority, installed contracts, primary documentation, and domain evidence
  it must inspect;
- evidence-freshness and source-fidelity requirements;
- likely failure modes, overclaims, and boundary violations it must guard;
- its expected output and when an independent audit is warranted.

Do not create, install, or broaden a skill without Markeitect's approval. Do not let consultation
grant permission to edit, connect services, consume paid data, mutate persistence, commit, push, or
make a product decision. Advisors recommend; Markeitect decides; Kite remains responsible for
reviewing the evidence and integrated work.

Read [references/advisor-design.md](references/advisor-design.md) when proposing or creating a new
specialist.
