# Markeitech Specialist Advisor Design

Use this reference only after the coverage check finds a material domain without a suitable
advisor and Markeitect is considering adding one.

## Minimum Contract

A useful specialist advisor must define:

- a narrow, discoverable domain and explicit exclusions;
- the decisions it informs and the decisions it cannot make;
- current primary sources, local executable contracts, tracked Markeitech authority, and raw
  evidence it must inspect;
- how it distinguishes verified facts, measured evidence, inference, hypothesis, recommendation,
  and unknowns;
- freshness, provenance, licensing, timezone, instrument, provider, and fidelity constraints that
  affect meaning;
- a repeatable review or design workflow with concrete stopping conditions;
- the output expected from the advisor and the evidence required before implementation;
- the same repository permissions, approval gates, and side-effect restrictions as Kite.

Each advisor's council-policy entry also declares versioned capability requirements and default,
constraint, and retry profile references under the [allocation contract](resource-allocation.md).
Concrete model/effort mappings belong only to central policy. Do not add `model`,
`model_reasoning_effort`, or invented intent metadata to the Codex role file. Primary Kite makes
and validates the final per-consultation choice. Defaults are preferences, not execution pins;
mandatory restrictions require evidence and belong in the constraint profile.

Prefer one strong advisor per coherent domain over a collection of shallow prompt fragments. Do
not encode a temporary conclusion as permanent expertise. A specialist should improve decisions
by forcing relevant evidence and boundaries into view, not by supplying confident vocabulary.

## Example: Options Flow

An options-flow request should trigger a proposal for an advisor such as
`markeitech-options-flow-expert` when no equivalent skill is available. Its proposed contract would
cover vendor-feed semantics and provenance, OPRA and NBBO limitations, trade classification,
blocks and sweeps, complex orders, 0DTE identity, volume and open-interest timing, Greeks and
underlying context, licensing, and the difference between observed prints and inferred intent.
It must guard against treating a filtered vendor export as consolidated flow or a single print as
proof of directional positioning.

This example illustrates advisor scope; it does not preapprove the skill, its sources, a data
provider, an architecture, or trading semantics.
