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
   - `AVAILABLE`: name and invoke the applicable specialist before substantive planning or edits.
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
