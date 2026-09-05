# Advisor Council Routing Guide

The machine-checkable [council policy](council-policy.toml) is the canonical registry for role
identity, skill mapping, ownership, exclusions, default dependencies, model policy, and tool/source
defaults. This document is a concise human guide. The validator checks that it lists every role,
but it does not compare prose semantics; if the guide drifts, the TOML policy governs.

Every custom role is a bounded consultation. “May recommend” never means it may edit, approve, or
perform the action. Primary Kite selects the smallest sufficient set and assigns one exact owned
question to every selected role.

Primary Kite also owns each consultation's model/effort choice. Follow
[resource allocation](resource-allocation.md) and run the resolver before exact-role dispatch.
Advisor entries declare intent/default references; role files do not force execution settings.
Allocation never changes the selected-role set, dependency ordering, or evidence/permission contract.

## Activation Boundary

Kite is explicit-only. A fresh Codex task, an ordinary Markeitech request, and a casual mention of
Kite remain normal Codex and do not invoke the router or advisors. Explicitly selecting Kite or
invoking `$kite:markeitech-advisor-router` activates Kite for that task and its direct follow-ups.
A new or unrelated task returns to normal Codex. Once active, Kite performs the coverage check and
uses the smallest sufficient advisor set by default; Markeitect never needs to name specialists.

## Ownership Guide

| Exact custom role | Sole advisory column | Important exclusion |
|---|---|---|
| `markeitech_architecture_boundaries_advisor` | Topology, canonical authority, owner placement, duplication, durability ownership, change cost | Event, Python, database, or market mechanics |
| `markeitech_nautilus_advisor` | Installed/current Nautilus capability and framework alignment | IB provider truth and product meaning |
| `markeitech_ib_market_data_advisor` | IB requests, entitlements, pacing, sessions, fields, delivery, provider failure | Nautilus adapter behavior and market meaning |
| `markeitech_event_driven_architecture_advisor` | Delivery, ordering, idempotency, retry, backpressure, recovery, partial failure | Component placement, Python implementation, event meaning |
| `markeitech_python_runtime_advisor` | Python concurrency, cancellation, shutdown/restart, typing/packages, measured resources | Nautilus guarantees and event policy |
| `markeitech_postgres_persistence_advisor` | Approved PostgreSQL schema, migration, transaction, recovery, retention, observability mechanics | Logical durability and raw-retention approval |
| `markeitech_data_quality_lineage_advisor` | Identity, lineage, clocks, sessions, completeness, revisions, freshness, fidelity | Formula validity, licensing permission, final fitness |
| `markeitech_quantitative_metric_validation_advisor` | Formula, units, windows, warmup, aggregation, numerics, parity, fixtures | Provider truth, market meaning, final fitness |
| `markeitech_evidence_fitness_advisor` | Fitness of identified evidence for one named use | Recalculation, repair, market meaning, model evaluation |
| `markeitech_market_structure_advisor` | Swings, pivots, legs, objective levels, FVGs, zones, profiles, auction geometry | Observed flow, semantic interactions, options |
| `markeitech_market_microstructure_order_flow_advisor` | Trades, quotes, BBO/NBBO, classification, delta/CVD, books, effort-response | Bar geometry, participant intent, options mechanics |
| `markeitech_semantic_events_opportunity_lifecycle_advisor` | Derived-event and plural-opportunity identity, transitions, time, conflict, revision, non-admission | Sir Loke judgment or abstention, option selection, execution |
| `markeitech_options_0dte_advisor` | Option identity, chain, quotes/Greeks, expiry, exercise, settlement, bounded discovery | Vendor-flow interpretation, candidate risk acceptance |
| `markeitech_options_flow_advisor` | Vendor-flow schemas, prints, classifications, premium, OI timing, filters, provenance | General options mechanics, positioning claims, trade advice |
| `markeitech_zero_dte_risk_advisor` | Risk synthesis for an already named long single-leg 0DTE candidate | Candidate selection, validation, sizing, portfolio risk |
| `markeitech_statistical_learning_optimization_advisor` | Feature/label validity, leakage-safe evaluation, calibration, monitoring, bounded optimization | Model building, training, metric calculation, trading semantics |
| `markeitech_live_agent_governance_advisor` | Sir Loke intent schemas, authority, approval lifecycle, evidence admission, abstention, audit, no execution | Security mechanics, delivery, persistence, market meaning |
| `markeitech_evidence_visualization_advisor` | Projection integrity, financial presentation, accessibility, browser acceptance, visual QA | Canonical analytics, delivery protocol, agent meaning |
| `markeitech_security_tool_boundary_advisor` | Secrets, authentication, permissions, MCP/tools, redaction, supply chain, external surfaces, safe failure | Sir Loke approval taxonomy, component placement, legal approval |
| `markeitech_vendor_data_licensing_provenance_advisor` | Terms, permitted use, retention, display/redistribution, derived data, provenance, legal escalation | Engineering truth, market meaning, legal approval |

## Evidence Validation Chain

```text
source and identity disposition
  -> quantitative validity when the evidence is numerical
  -> final fitness for one named downstream use
```

Data quality owns observation truth. Quantitative validation owns mathematical truth. Evidence
fitness consumes all material dispositions and cannot repair or upgrade them. A non-numerical lane
may be `NOT_APPLICABLE_WITH_REASON`; it is never silently skipped.

## Boundary Examples

- Component placement precedes delivery mechanics when ownership is unsettled.
- IB capability does not prove Nautilus adapter delivery.
- Bars may support price geometry; they do not become observed order flow.
- Opportunity lifecycle state is not Sir Loke judgment or abstention.
- Sir Loke governance owns approval meaning; security owns permission and tool enforcement.
- A visually attractive projection cannot repair rejected evidence.

Conflicts remain explicit. A downstream advisor cannot cure an upstream `UNKNOWN`, rejection,
missing authority, or competing owner. Primary Kite returns unresolved product or ownership choices
to Markeitect.
