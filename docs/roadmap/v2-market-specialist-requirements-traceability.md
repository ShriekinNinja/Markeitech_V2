# V2 Market-Specialist Requirements Traceability

## Purpose

This historical trace maps the accepted market-analysis specialist brief to its Stage 9
implementation scopes. It is an audit aid, not the current product sequence or a substitute for
metric and event contracts. Use the [current-status ledger](../current-status.md) for active
runtime behavior and the [Sir Loke blueprint](v2-market-events-live-agent-plan.md) for current
delivery priority.

## Cross-Cutting Requirements

| Requirement | Contract or enforcement | Status |
|---|---|---|
| No configured preferred trade instrument | Opportunity universe remains concurrent; no preference field exists | Enforced by plan |
| Exact inputs and bounded warmup | Capability live/historical requirements | Implemented foundation |
| Formula and normalization are explicit | `MetricDefinition.formula` and `.normalization` | Implemented foundation |
| Instrument applicability is explicit | `MetricDefinition.applicability` plus analytical profile binding | Implemented foundation |
| Honest variable fidelity | Expected and allowed fidelities; evidence/missing reasons | Implemented foundation |
| Known failure modes are declared | `MetricDefinition.failure_modes` | Implemented foundation |
| Parameters are configurable and optimization-ready | Typed envelopes, mutability, source, version, UTC effective time | Implemented foundation |
| No counterfeit index volume | Volume-supported and volume-unsupported profiles are distinct | Implemented configuration |
| No raw market-data persistence | Native observations and historical responses remain transient | Enforced architecture |
| No universal score | Dimensions remain separate through measurements and rolling state | Enforced by plan |
| Dynamic cross-market relationships | Relationship state is later evidence, not a fixed causal rule | Planned Stage 9G |
| Multiple simultaneous opportunities | Opportunity identity and state are plural | Planned advisory stage |

## Measurement And Event Families

| Specialist family | First implementation location | Required evidence | Evidence disposition at 2026-09-05 |
|---|---|---|---|
| Quote quality and liquidity | Stage 9A quote metrics | Native bid/ask plus evidence health | Code and historical acceptance exist; disabled in active V3 profile |
| Completed OHLCV, return, true range | Stage 9C Slices 1-2 | Native/aggregated completed bars and bounded history | Predecessor accepted then disabled; V3 replacement incomplete and inactive |
| Session range and location | Stage 9C Slice 3 | Session state plus completed bars | Predecessor accepted then disabled; V3 replacement incomplete |
| Prior-session references and overnight gap | Stage 9C Slice 3, durable summary in Stage 9D | Purpose-specific calendar-window dependencies | Predecessor accepted then disabled; durability remains incomplete |
| Opening range and extensions | Stage 9C Slice 4 | Calendar-relative intraday dependency | Predecessor accepted then disabled; V3 replacement incomplete |
| Power-hour evidence | Stage 9C Slice 4, durable summary in Stage 9D | Authoritative close-relative window | Predecessor accepted then disabled; durability remains incomplete |
| VWAP where volume is meaningful | Stage 9D Group 1 prerequisite/reference state | Intraday price/volume with supported-volume profile | Planned in approved Stage 9D scope |
| Realized volatility/range | Stage 9C Slice 5 | Purpose-specific completed bars | Predecessor numerical inputs accepted; active V3 replacement incomplete |
| Directional efficiency and compression | Stage 9C Slice 5 inputs; Stage 9D Groups 2-3 state | Bounded returns/ranges plus signed directional prerequisites | Pure code/evidence exists; disabled in active V3 profile |
| Objective session/reference levels and gaps | Stage 9D Group 1 | Purpose-specific session/window evidence | Pure/runtime code and historical evidence exist; disabled in active V3 profile |
| Direction, trend, rotation, volatility, compression, expansion | Stage 9D Groups 2-3 | Versioned multi-horizon numerical evidence | Partial pure/runtime implementation; disabled in active V3 profile |
| Swings, FVGs, and derived zones | Stage 9D Group 4 | Purpose-specific completed-bar geometry | Pure/runtime code exists; disabled in active V3 profile |
| Inferred bar-volume distribution, POC/value area, HVN/LVN | Stage 9D Group 5 | Completed OHLCV where volume is supported | Approved with explicit `INFERRED_FROM_BARS` fidelity |
| Observed trade-at-price profile nodes | Richer analytics after an approved trade-at-price source | Observed trades at price | Deferred; must remain separate from bar inference |
| Effort versus price response | Richer analytics | Trades/order flow where available; explicitly named proxies otherwise | Planned |
| Cross-instrument leadership, lag, divergence | Cross-instrument state stage | Time-aligned healthy measurements | Planned |
| Options affordability, liquidity, Greeks, expected move | Bounded options-data proof and later options intelligence | Fresh executable option quotes and chain evidence | Planned |
| SPXW GTH underlying-reference quality | Options/cross-instrument stage | Explicit time-aligned ES or other proxy with fidelity | Planned |
| Approach/test/accept/reject/hold/fail/target/invalidate | Semantic event and lifecycle stages | Stable entities plus reviewed measurement transitions | Planned |
| Ranked concurrent 0DTE opportunities | Sir Loke | Complete evidence graph and policy-authorized option discovery | Accepted product requirement; unimplemented |

## Historical Stage 9C Slice 2 Gate

Slice 2 may publish only completed-bar foundation metrics. It does not claim session structure,
levels, trends, order flow, options intelligence, or trading signals. It passes only when:

- every selected instrument has exactly one compatible analytical profile;
- historical and live arrival order produces the same accepted interval set;
- warmup remains inside the configured two-to-four-observation envelope;
- aggregation uses only the declared UTC-fixed intraday policy;
- conflicts and rejected revisions are visible and isolated per instrument;
- output fidelity follows the actual data path;
- parameter source/version/effective time and evidence lineage are preserved; and
- unrelated actors continue through missing, stale, conflicting, or unsupported evidence.
