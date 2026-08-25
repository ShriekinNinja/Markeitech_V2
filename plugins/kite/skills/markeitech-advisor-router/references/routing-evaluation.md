# Advisor Council Routing Evaluation

**Source design status:** statically reviewed 2026-08-25.

**Installed status:** Kite `0.1.0+codex.20260825140114` was reinstalled from the local `markeitech`
marketplace on 2026-08-25, Codex reported it enabled at that exact version, and the installed cache
matched repository source byte-for-byte. Automatic fresh-task routing and delegated execution for
the changed council remain `PENDING`; static contract resolution and successful installation are
not routing behavior.

Every executed case records:

`Case | Prompt | Expected ordered roles | Actual route | Unnecessary roles | Stop gate | Handoff quality | Overlap/conflict | Result | Evidence date/version`

Use `STATIC_PASS` only for deterministic source checks. Use `INSTALLED_PASS` only after an approved
cachebuster/reinstall and a new task demonstrates actual selection and execution.

| Case | Prompt summary | Expected ordered role(s) | Static contract | Actual installed route | Unnecessary advisors | Stop-gate behavior | Handoff quality | Overlap/conflict | Final result |
|---|---|---|---|---|---|---|---|---|---|
| S1 | Who owns a proposed new canonical state? | architecture boundaries | Exactly one advisor; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| S2 | Does this Python worker cancel and drain safely? | Python runtime | One advisor absent framework/event-policy claim; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| S3 | Is this IB request or entitlement supported? | IB market data | Provider truth only; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| S4 | Is this rolling formula numerically correct? | quantitative metric validation | Formula review only; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| S5 | Is this chart accessible and faithful? | evidence visualization | Projection only; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| M1 | Move an event owner and define retry delivery | architecture -> event-driven | Ownership precedes delivery; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| M2 | Implement IB data through a Nautilus actor | IB -> Nautilus; architecture first only if ownership changes | Separate provider/framework columns; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| M3 | Validate a derived metric for Sir Loke | data quality -> quantitative validation -> evidence fitness -> live-agent governance | Exact dispositions flow forward; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| M4 | Persist a vendor option-flow export | data quality -> licensing -> options flow -> architecture -> PostgreSQL | Identity -> rights -> meaning -> durability -> DB mechanics; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| A1 | “Review the data” without artifact/use | none initially | Clarify or bound assumptions; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| A2 | “Make the chart better” without canonical contract | visualization stop | Request payload/artifact; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| X1 | Design automated order execution | missing execution/risk specialist | Stop and propose coverage; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| X2 | Grant jurisdiction-specific legal approval | licensing -> missing legal coverage | Identify risk then stop; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| B1 | Place a component versus deliver its event | architecture -> event-driven if material | Preserve boundary; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| B2 | Does candle volume prove absorption at a zone? | market structure -> microstructure | Reject counterfeit observed flow; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| B3 | Explain SPXW settlement risk for a supplied candidate | options mechanics -> evidence fitness if material -> candidate risk | Mechanics before risk; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| B4 | Interpret BlackBox sweeps for an SPXW contract | data quality -> licensing -> options mechanics -> options flow | Source and rights precede interpretation; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| B5 | Duplicate/conflict coverage versus rolling formula | data quality -> quantitative validation | Lineage owns observation truth; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| B6 | Metric correctness versus predictive usefulness | quantitative validation -> evidence fitness -> statistical learning | Numerical validity before model evaluation; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| B7 | Define opportunity state versus Sir Loke judgment | semantic lifecycle -> live-agent governance | State is not agent judgment; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| B8 | Canonical evidence versus UI resampling | evidence fitness if needed -> visualization | UI does not recalculate truth; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| B9 | Token handling and vendor redistribution | security -> licensing | Independent dispositions with stable tie-breaker; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| P1 | Fix a prose typo | none | Primary Kite handles it; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| P2 | List advisor files or validate TOML | none | Primary Kite handles administration; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| G1 | Change architecture/dependency/schema/provider owner/runtime policy | applicable advisors -> Markeitect gate | Advice is not approval; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |
| G2 | Connect services or reinstall plugin | applicable analysis -> explicit action approval | No side effect during routing QA; `STATIC_PASS` | `NOT_RUN` | `UNKNOWN` | `NOT_OBSERVED` | `NOT_OBSERVED` | `NOT_OBSERVED` | `PENDING` |

## Exact Role Coverage

This ledger binds each accepted custom-agent identifier to at least one case above. It prevents
short display labels in the matrix from concealing an untested or renamed role.

| Exact custom-agent role | Evaluation case(s) |
|---|---|
| `markeitech_architecture_boundaries_advisor` | S1, M1, M4, B1, G1 |
| `markeitech_nautilus_advisor` | M2 |
| `markeitech_ib_market_data_advisor` | S3, M2 |
| `markeitech_event_driven_architecture_advisor` | M1, B1 |
| `markeitech_python_runtime_advisor` | S2 |
| `markeitech_postgres_persistence_advisor` | M4 |
| `markeitech_data_quality_lineage_advisor` | M3, M4, B4, B5 |
| `markeitech_quantitative_metric_validation_advisor` | S4, M3, B5, B6 |
| `markeitech_evidence_fitness_advisor` | M3, B3, B6, B8 |
| `markeitech_market_structure_advisor` | B2 |
| `markeitech_market_microstructure_order_flow_advisor` | B2 |
| `markeitech_options_0dte_advisor` | B3, B4 |
| `markeitech_options_flow_advisor` | M4, B4 |
| `markeitech_zero_dte_risk_advisor` | B3 |
| `markeitech_statistical_learning_optimization_advisor` | B6 |
| `markeitech_semantic_events_opportunity_lifecycle_advisor` | B7 |
| `markeitech_live_agent_governance_advisor` | M3, B7 |
| `markeitech_evidence_visualization_advisor` | S5, A2, B8 |
| `markeitech_security_tool_boundary_advisor` | B9, G2 |
| `markeitech_vendor_data_licensing_provenance_advisor` | M4, B4, B9, X2 |

Start a fresh task, execute every case without naming the intended advisor, and record actual
selection, order, unnecessary roles, stop gates, handoffs, conflicts, and result. Replace `PENDING`
only with observed evidence.
