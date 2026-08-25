# Markeitech Kite Advisor Council

**Status:** Repository advisor architecture implemented and installed; fresh-task routing acceptance
remains pending

**Reviewed:** 2026-08-25

## Purpose And Authority

Kite routes substantive Markeitech questions to narrow read-only specialists. Advisors improve the
evidence and recommendation; they do not replace tracked authority, primary Kite integration, or
Markeitect's final product, trading, architecture, review, release and approval decisions.

The router is `plugins/kite/skills/markeitech-advisor-router/`. Its route registry is the canonical
manager contract. Custom roles live in `.codex/agents/`. Skills live only in the repository Kite
plugin and use the `markeitech-` prefix.

No advisor creation changes V2 runtime implementation. In particular, semantic events, Sir Loke,
options intelligence and opportunity lifecycle remain future runtime stages as stated in
`docs/current-status.md`.

## Canonical Inventory

| Tier/domain | Custom role | Repository skill | Reasoning |
|---|---|---|---|
| Architecture | `markeitech_architecture_boundaries_advisor` | `markeitech-architecture-boundaries-expert` | medium |
| Framework | `markeitech_nautilus_advisor` | `markeitech-nautilus-v2-expert` | high |
| Provider | `markeitech_ib_market_data_advisor` | `markeitech-ib-market-data-expert` | high |
| Event delivery | `markeitech_event_driven_architecture_advisor` | `markeitech-event-driven-architecture-expert` | high |
| Python runtime | `markeitech_python_runtime_advisor` | `markeitech-python-runtime-expert` | medium |
| PostgreSQL | `markeitech_postgres_persistence_advisor` | `markeitech-postgres-persistence-expert` | medium |
| Data quality/lineage | `markeitech_data_quality_lineage_advisor` | `markeitech-data-quality-lineage-expert` | high |
| Quantitative validation | `markeitech_quantitative_metric_validation_advisor` | `markeitech-quantitative-metric-validation-expert` | high |
| Evidence fitness | `markeitech_evidence_fitness_advisor` | `markeitech-evidence-fitness-expert` | high |
| Market structure | `markeitech_market_structure_advisor` | `markeitech-market-structure-expert` | medium |
| Microstructure/order flow | `markeitech_market_microstructure_order_flow_advisor` | `markeitech-market-microstructure-order-flow-expert` | high |
| Semantic events/opportunities | `markeitech_semantic_events_opportunity_lifecycle_advisor` | `markeitech-semantic-events-opportunity-lifecycle-expert` | medium |
| Options mechanics/0DTE | `markeitech_options_0dte_advisor` | `markeitech-options-0dte-expert` | high |
| Vendor options flow | `markeitech_options_flow_advisor` | `markeitech-options-flow-expert` | high |
| Named-candidate risk | `markeitech_zero_dte_risk_advisor` | `markeitech-zero-dte-risk-expert` | high |
| Statistical learning | `markeitech_statistical_learning_optimization_advisor` | `markeitech-statistical-learning-optimization-expert` | high |
| Live-agent governance | `markeitech_live_agent_governance_advisor` | `markeitech-live-agent-governance-expert` | medium |
| Evidence visualization | `markeitech_evidence_visualization_advisor` | `markeitech-evidence-visualization-expert` | medium |
| Security/tool boundary | `markeitech_security_tool_boundary_advisor` | `markeitech-security-tool-boundary-expert` | high |
| Vendor licensing/provenance | `markeitech_vendor_data_licensing_provenance_advisor` | `markeitech-vendor-data-licensing-provenance-expert` | high |

There are 20 callable specialist roles. The former broad
`markeitech_market_evidence_validation_advisor` and its skill are superseded and are not callable
aliases.

## Deterministic Routing

Default dependency order, applied only when a domain is material:

1. architecture and authority ownership;
2. framework/provider contracts;
3. delivery and Python concurrency;
4. persistence and data quality;
5. quantitative validity and evidence fitness;
6. market semantics and derived semantic lifecycle;
7. option mechanics and vendor flow;
8. candidate risk;
9. statistical learning/optimization;
10. live-agent governance; and
11. evidence visualization.

Security is a precondition wherever secrets, permissions, tools, dependencies, credentials,
network surfaces or redaction change. Licensing is a precondition after exact vendor identity and
before acquisition, external processing, retention, redistribution, display, derived-data or
agent/model use. These gates are not postponed merely because they are cross-cutting.

Only primary Kite invokes advisors. Advisors return exact handoffs and never delegate. Primary Kite
records the selected roles, dependency edges and dispositions, invokes one role once per scoped
question, and joins only compatible columns. A bounded second consultation requires materially new
evidence. Stable role-name order is only a tie-breaker for independent consultations.

## Evidence Validation Split

```text
provider and domain contracts
  -> data-quality and lineage disposition
exact metric plus quality disposition
  -> quantitative-validity disposition
every material disposition plus one named use
  -> evidence-fitness result
```

Data quality owns source, identity, time, coverage, conflicts, revisions, freshness, fidelity and
lineage. Quantitative validation owns formula, units, windows, warmup, aggregation, numerics,
parity, fixtures and invariants. Evidence fitness consumes an exact disposition from every material
upstream owner and returns only `ACCEPTED`, `DEGRADED`, `OBSERVATION_ONLY` or `REJECTED` for one
named use. A non-material lane must be recorded as `NOT_APPLICABLE_WITH_REASON`; quantitative
validation is not mandatory for categorical, operational, provider-reported, or other non-metric
evidence when its irrelevance is explicit. Evidence fitness cannot recalculate, average failures,
or upgrade an unknown. Its final matrix preserves consumer-specific severity, permitted and
prohibited uses, validity, expiry/revalidation, and any required consumer acceptance.

## Conflict And Stop Gates

Stop the affected consequential conclusion when tracked authorities conflict; a required role,
skill, source or artifact is unavailable/stale; an upstream disposition is absent or material
`UNKNOWN`; two roles claim one authority; provider documentation conflicts with measured behavior;
source and installed plugin differ for an installed claim; security/licensing/legal/execution/risk
coverage is missing; or an advisor exceeds read-only authority.

Unresolved canonical-owner, product-semantic or competing-authority conflicts are
`REQUIRES MARKEITECT DECISION`. A downstream advisor cannot cure an upstream conflict.

## Candidate Worktree Reconciliation

Candidate worktrees remain preserved and unmodified.

| Candidate | Disposition | Adopted, rejected or deferred material |
|---|---|---|
| `market-structure-auction` | Duplicative; not installed | Auction/profile geometry, TPO versus observed trade-at-price versus inferred bar volume, value-area configuration and acceptance/rejection guardrails were already present in the canonical market-structure advisor and remain there. A second authority was rejected. |
| `options-market` | Duplicative; not installed | Compatible contract/chain/quote/Greek/exercise/settlement mechanics remain in the canonical 0DTE options advisor. Vendor-flow interpretation was explicitly separated. |
| `live-evidence-visualization` | Duplicative; not installed | Canonical-projection-only, visual acceptance, accessibility and browser-performance material remains in the evidence-visualization advisor. |
| `ml-evaluation` | Duplicative; not installed | As-of ledgers, label maturity/censoring, forward evaluation, calibration, monitoring and bounded optimization remain in the statistical-learning advisor. |
| `data-quality-lineage` | Adopted as source material | Identity/time/coverage/reconciliation/fidelity material forms the new narrow role; formula and final-fitness authority were excluded. |
| `quant-metric-validation` | Adopted as source material | Formula/window/warmup/numerical/fixture material forms the new narrow role; provider truth, model utility and final fitness were excluded. |
| `market-microstructure-order-flow` | Completed as canonical role | Evidence ladder, trade/quote/book contracts, classifier coverage, delta/CVD, effort-response and participant-intent limits were adopted. |
| `security-licensing-governance` | Rejected as conflated and empty | Replaced with separate security/tool-boundary and vendor-licensing/provenance roles. |
| `rust-pyo3` | Deferred and uninstalled | Current accepted architecture has no native-extension requirement. Installing it would create premature authority and maintenance. |
| Empty/superseded candidates | Preserved | No worktree was deleted or normalized during this batch. |

## Model And Reasoning Policy

All roles use the existing `gpt-5.6-sol` model; no model was changed for cosmetic uniformity.

`high` is assigned where a mistake depends on versioned framework/provider contracts, delivery
semantics, evidence validity, market microstructure, options interpretation, statistical validity,
security, licensing or expiry risk. `medium` is assigned to bounded ownership inventory, routine
Python/PostgreSQL mechanics, market-structure contract review, semantic lifecycle coordination,
agent governance and evidence projection. PostgreSQL remains medium because logical durability and
authority are settled upstream; escalate the consultation rather than silently changing the role's
permanent profile when ambiguity or consequence is exceptional.

Reasoning effort is not authority. A high-effort advisor remains narrow and read-only.

## Source And License Discipline

Every new domain records tracked authority and external primary or institutional sources in its
skill references. Sources are linked and paraphrased. No third-party skill, proprietary manual,
vendor schema, licensed data or undocumented claim is copied. Research cut dates are not proof of
current behavior; drift-prone sources must be refreshed for consequential consultations.

## Installation And Acceptance

Source validation proves packaging and internal references only. Kite
`0.1.0+codex.20260825140114` was cache-busted and reinstalled from the local `markeitech`
marketplace on 2026-08-25. The installed cache matched the repository plugin byte-for-byte, and
Codex reported that exact version installed and enabled. This proves installation and source/cache
identity, not automatic routing or delegated advisor execution.

The routing matrix at
`plugins/kite/skills/markeitech-advisor-router/references/routing-evaluation.md` records static
results separately from installed results. Changed-council fresh-task rows remain `PENDING` until
a new task records selected roles, order, unnecessary roles, stop gates, handoffs, conflicts and
final result.

## Known Gaps

- Fresh-task changed-council discovery, automatic routing, and delegated execution are pending.
- No runtime product semantics are accepted by advisor installation.
- Execution, account/portfolio risk, jurisdiction-specific legal counsel, privacy counsel and a
  dedicated cross-instrument causal-relationships specialist remain missing when those decisions
  are material.
- Candidate research worktrees remain separate historical source material and may drift.
