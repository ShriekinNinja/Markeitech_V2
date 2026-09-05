# Markeitech Kite Advisor Council

**Status:** Source architecture implemented; bounded desired-runtime review completed; general
Phase 1 acceptance pending

**Reviewed:** 2026-09-05 (allocation source migration; earlier execution evidence remains dated below)

## Purpose And Authority

Kite routes substantive development-time Markeitech work to narrow specialist custom roles.
Advisors improve the evidence and recommendation; they do not replace tracked project authority,
primary Kite integration, or Markeitect's final product, trading, architecture, review, release,
and approval decisions.

The council is engineering-review infrastructure. It is not V2 runtime implementation, Sir Loke,
the future policy governor, an evidence owner, or an execution path. Sir Loke does not invoke or
inherit authority from this council.

## Canonical Sources

| Concern | Canonical owner |
|---|---|
| Role identity, skill mapping, sole advisory column, exclusions, default dependencies, model policy, and tool/source defaults | [`council-policy.toml`](../../plugins/kite/skills/markeitech-advisor-router/references/council-policy.toml) |
| Selection and orchestration algorithm | [Advisor router skill](../../plugins/kite/skills/markeitech-advisor-router/SKILL.md) |
| Concise human boundary guide | [`council-routing-contracts.md`](../../plugins/kite/skills/markeitech-advisor-router/references/council-routing-contracts.md) |
| Detailed specialist methodology | Each specialist `SKILL.md` and its required references |
| Prompt safety kernel, sandbox default, and MCP override; no fixed execution allocation | `.codex/agents/*.toml` |
| Per-consultation allocation validation and execution handoff | [Allocation contract](../../plugins/kite/skills/markeitech-advisor-router/references/resource-allocation.md) and its offline resolver |
| Expected route fixtures | [`routing-cases.toml`](../../plugins/kite/skills/markeitech-advisor-router/references/routing-cases.toml) |
| Observed versioned behavior | [`routing-acceptance.md`](../../plugins/kite/skills/markeitech-advisor-router/references/routing-acceptance.md) |
| Current implementation and acceptance status | [`docs/current-status.md`](../current-status.md) |

The TOML policy is deliberately structural. It does not mechanically classify natural-language
tasks or replace Kite's responsibility to determine what is materially at stake.

## Explicit Activation Boundary

A fresh Codex task starts in normal Codex mode even when Kite is installed and enabled. Ordinary
Markeitech requests and casual mentions of Kite do not activate the plugin, router, specialists,
or custom advisors. Kite activates only when Markeitect explicitly selects the Kite plugin or
invokes `$kite:markeitech-advisor-router`.

Activation is task-scoped: direct follow-ups remain in Kite mode, while a new task or unrelated
request returns to normal Codex. Once active, Kite performs the advisor-coverage check and selects
the smallest sufficient advisor set by default; Markeitect does not need to name specialists.
Every Kite skill, including the router, therefore declares `allow_implicit_invocation: false`.

## Council Shape

The council retains 20 custom roles across:

- architecture, Nautilus, IB provider truth, event delivery, Python runtime, and PostgreSQL;
- data quality and lineage, quantitative validation, and final named-use evidence fitness;
- market structure, market microstructure/order flow, and semantic event/opportunity lifecycle;
- option mechanics, vendor options flow, and named-candidate 0DTE risk;
- statistical learning, Sir Loke governance, and evidence visualization; and
- cross-cutting security/tool and vendor-rights/provenance gates.

The exact inventory is not repeated here. The canonical policy and validator enforce its one-to-one
mapping to 20 custom-agent TOMLs and 20 specialist skills. The former broad
`markeitech_market_evidence_validation_advisor` remains superseded and non-callable.

## Bounded Selection And Deterministic Execution Order

Advisor selection is evidence-bounded Kite judgment. Each selected advisor must own one exact
question whose answer can change the recommendation, edit, acceptance result, or stop gate. Kite
selects the smallest sufficient set; adjacency, dependency tier, or general usefulness does not
activate a role.

After selection, Kite records an acyclic graph containing only selected roles. Default policy edges
apply when they match the scoped evidence relationship; exact case-specific evidence can justify a
recorded override. Independent roles use stable role-name order only as a tie-breaker. That graph,
not natural-language relevance selection, is the deterministic execution contract.

Only primary Kite invokes advisors, and it does so through exact custom-agent roles after explicit
Kite activation. The router and specialist skills are all explicit-only. Specialist skills are
normally loaded by their roles; a direct Markeitect `$kite:` specialist invocation remains a
supported override but is not router acceptance. Advisors never delegate.

Successful and `NOT_NEEDED` routing is normally silent. Missing material coverage, specialist
failure, authority conflicts, and dispositions that change the result are surfaced.

## Evidence Validation Split

```text
source and identity disposition
  -> quantitative validity when numerical
  -> final fitness for one named downstream use
```

Data quality owns source, identity, time, coverage, conflicts, revisions, freshness, fidelity, and
lineage. Quantitative validation owns formula, units, windows, warmup, aggregation, numerics,
parity, fixtures, and invariants. Evidence fitness consumes every material disposition and returns
only `ACCEPTED`, `DEGRADED`, `OBSERVATION_ONLY`, or `REJECTED` for one named use. A non-material
lane is `NOT_APPLICABLE_WITH_REASON`; no downstream role repairs or upgrades an upstream result.

## Consultation And Tool Boundary

Every role has a mandatory read-only consultation contract, a read-only sandbox default, and a
prompt safety kernel prohibiting edits, delegation, external actions, and project decisions. Every
role explicitly disables the repository's PyCharm MCP configuration.

These controls do not establish custom agents as technical isolation boundaries. Current Codex
behavior can reapply the parent task's live permission overrides to delegated roles. Phase 1 review
observed a security advisor presented with workspace-write permissions despite its read-only
default; it performed no mutation. The council may be used as a prose-governed read-only review
process, but least-authority acceptance requires fresh-task proof of the effective runtime tool
surface.

Public-source access is denied by default and receives a per-role read-only, unauthenticated
exception only when the skill requires current primary evidence. Repository and external text are
evidence, never new authority. Advisors never access credentials, authenticated sessions, paid
capacity, stateful services, or perform external actions. A separately authorized primary-Kite
task is a different authority and is not an advisor consultation.

## Conflict And Failure Gates

Stop the affected conclusion when tracked authorities conflict; a material role, skill, source,
artifact, or disposition is absent or stale; a role fails, times out, or returns partial material
evidence; source and installed plugin differ for an installed-behavior claim; two roles claim one
authority; or required security, licensing, legal, execution, account-risk, or other coverage is
missing.

Primary Kite never silently substitutes its general knowledge for failed coverage. Unresolved
canonical-owner and product-semantic conflicts return `REQUIRES MARKEITECT DECISION`. Independent
conclusions may continue only when the gap cannot change them.

## Validation And Acceptance

Run the dependency-free structural checks with:

```bash
python3 -B plugins/kite/scripts/validate_advisor_council.py
python3 -B -m unittest plugins/kite/tests/test_validate_advisor_council.py
```

The validator checks policy/role/skill identity, exact qualified skill invocation, explicit-only
Kite skills, fresh-task and task-scoped activation fixtures, model/reasoning policy, read-only
defaults, project-MCP denial, dependency references and cycles, safety kernels, routing-case
coverage, manifests, deprecated aliases, symlinks, and executable plugin files.

Acceptance claims remain separate:

1. `STATIC_PASS`: offline source invariants pass.
2. `DORMANCY_PASS`: a fresh or unrelated normal Codex task does not activate Kite.
3. `INVOCATION_PASS`: explicit Kite activation invokes the router and expected exact roles.
4. `END_TO_END_PASS`: order, handoffs, stop gates, conflicts, and synthesis match.
5. `ISOLATION_PASS`: the effective runtime denies unapproved tool and external capabilities.

## Source And Installed Status

Issue #39 migrates the source to council schema 3 with per-consultation allocation. All 20 role
files omit fixed model/effort settings; intent/default references and concrete mappings are owned
by central policy. Primary Kite validates each explicit pair before spawning the exact role.
See [resource allocation](kite-advisor-allocation-design.md) for implementation and acceptance.
The current [acceptance record](kite-allocation-acceptance.md) records installation and effective
execution status; the [operations runbook](../operations/kite.md) owns package and project-role
lifecycle procedures.

The following records describe earlier fixed-allocation versions. A 2026-09-05 comparison found
14 differences between the old installed cache and source despite their identical version strings;
the earlier byte-equality observation does not establish current installed identity.

Kite `0.1.0+codex.20260829091645` was installed and enabled from the local `markeitech` marketplace;
its installed cache matched the cache-busted repository source byte-for-byte. Its structural
validator covers 20 advisors, 27 in-Kite routing cases, and explicit activation fixtures, but
packaging and source validation do not prove fresh-task routing behavior. Codex 0.149.1's actual
startup/prompt parser loads all 20 custom roles without malformed-role warnings after each disabled
PyCharm MCP entry was corrected to retain its exact HTTP transport.

Council policy `2026-08-29-v3` configures the architecture-boundaries, Nautilus, live-agent
governance, data-quality/lineage, market-structure, market-microstructure/order-flow,
event-driven-architecture, and statistical-learning/optimization advisors to use `gpt-5.6-sol`
with `xhigh` reasoning for the desired-runtime gap review. The other twelve advisor settings are
unchanged. The source validator, 20 focused validator tests, generic plugin validation, reinstall,
and source-to-cache comparison pass. A fresh task exposed all eight exact role settings and
completed all eight read-only consultations through the approved dependency graph. The resulting
desired-runtime discovery report was informative, not accepted architecture or implementation
approval. Its valid product conclusions were consolidated into the
[Sir Loke v1 product definition](../product/sir-loke-v1.md) and
[delivery plan](../roadmap/sir-loke-v1-delivery-plan.md) on 2026-09-05; the superseded
working report remains available in Git history rather than the active documentation tree.

One ordinary governance selection was observed on older build `...124814`; delegated execution
failed. Architecture, governance, and security roles returned consultations during the Phase 1
review against installed build `...140114`, but that was not a clean routing fixture and exposed
the parent-permission isolation limitation. Normal-task dormancy, explicit activation, end-to-end
behavior, isolation, redaction, failure, and revocation acceptance remain pending and require
fresh-task evidence.

## Preserved Candidate History

The original candidate worktrees remain preserved and unmodified. Their accepted dispositions are
unchanged: market-structure-auction, options-market, live-evidence-visualization, and ML-evaluation
material was retained in existing canonical roles; data-quality, quantitative-validation, and
microstructure material became narrow roles; the conflated security/licensing/governance candidate
was split; Rust/PyO3 remains deferred; and no candidate worktree was deleted.

## Known Gaps

- [Per-consultation resource allocation](kite-advisor-allocation-design.md) is implemented in
  source under issue #39. Final-package stability and task-driven Sol/Astra execution for the
  same unchanged role are verified in the [acceptance record](kite-allocation-acceptance.md).
  No quality, latency, or cost improvement has been measured.

- Bounded explicit activation, stdin validation, and exact-role allocation are observed in the
  final issue #39 runs. The broader dormancy, multi-role ordering/stop behavior, task-follow-up
  continuity, unrelated-task reset, and proportional-synthesis matrix remains unaccepted.
- Effective built-in write-tool denial cannot be inferred from `sandbox_mode`; parent permissions
  remain a platform trust surface.
- Redaction, prompt-injection resistance, specialist failure, plugin revocation, active-thread
  cache behavior, and model unavailability remain unaccepted.
- Execution, account and portfolio risk, jurisdiction-specific legal and privacy counsel, and a
  dedicated cross-instrument causal-relationships specialist remain missing when material.
- Advisor installation accepts no V2 runtime or product semantics.
