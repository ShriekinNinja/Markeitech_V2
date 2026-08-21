# V2 Market-Specialist Requirements Traceability

## Purpose

This file maps the accepted market-analysis specialist brief to the implementation sequence. It is
an audit aid, not a substitute for metric and event contracts. A row marked planned has no runtime
claim behind it yet.

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
| Dynamic cross-market relationships | Relationship state is later evidence, not a fixed causal rule | Planned Stage 9F+ |
| Multiple simultaneous opportunities | Opportunity identity and state are plural | Planned advisory stage |

## Measurement And Event Families

| Specialist family | First implementation location | Required evidence | Current status |
|---|---|---|---|
| Quote quality and liquidity | Stage 9A quote metrics | Native bid/ask plus evidence health | Implemented |
| Completed OHLCV, return, true range | Stage 9C Slices 1-2 | Native/aggregated completed bars and bounded history | Enabled and live-accepted |
| Session range and location | Stage 9C Slice 3 | Session state plus completed bars | Implemented and locally accepted |
| Prior-session references and overnight gap | Stage 9C Slice 3, durable summary in Stage 9D | Purpose-specific calendar-window dependencies | Implemented and locally accepted |
| Opening range and extensions | Stage 9C Slice 4 | Calendar-relative intraday dependency | Implemented for local review |
| Power-hour evidence | Stage 9C Slice 4, durable summary in Stage 9D | Authoritative close-relative window | Implemented for local review |
| VWAP where volume is meaningful | Stage 9C later slice | Intraday price/volume with supported-volume profile | Planned |
| Realized volatility/range | Stage 9C Slice 5 | Purpose-specific completed bars | Planned |
| Directional efficiency and compression | Stage 9C Slice 5 | Bounded returns/ranges | Planned |
| Levels, zones, gaps, profile nodes | Entity stages after trusted measurements | Purpose-specific higher-timeframe/session evidence | Planned |
| Effort versus price response | Richer analytics | Trades/order flow where available; explicitly named proxies otherwise | Planned |
| Cross-instrument leadership, lag, divergence | Cross-instrument state stage | Time-aligned healthy measurements | Planned |
| Options affordability, liquidity, Greeks, expected move | Bounded options-data proof and later options intelligence | Fresh executable option quotes and chain evidence | Planned |
| SPXW GTH underlying-reference quality | Options/cross-instrument stage | Explicit time-aligned ES or other proxy with fidelity | Planned |
| Approach/test/accept/reject/hold/fail/target/invalidate | Semantic event and lifecycle stages | Stable entities plus reviewed measurement transitions | Planned |
| Ranked concurrent 0DTE opportunities | Live advisory agent | Complete evidence graph and policy-authorized option discovery | Planned |

## Slice 2 Gate

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
