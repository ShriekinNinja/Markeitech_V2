# Sir Loke V1 Boundaries

**Status:** Accepted future product architecture; not implemented

The canonical user experience is defined in
[`../product/sir-loke-v1.md`](../product/sir-loke-v1.md). This document owns the corresponding
component, authority, request, and side-effect boundaries. The delivery sequence is maintained in
[`../roadmap/sir-loke-v1-delivery-plan.md`](../roadmap/sir-loke-v1-delivery-plan.md), and
[`../current-status.md`](../current-status.md) remains the authority for what exists now.

## Product Topology

Sir Loke is one advisory component inside Markeitech, not a replacement for deterministic market
data, broker reconciliation, policy, persistence, or Discord transport.

```text
market/options observations -> deterministic evidence -> compact read model ----+
broker observations -> canonical trade episode -------------------------------+---> Sir Loke
trader statements -> conversation state --------------------------------------+       |
deterministic advisory policy -------------------------------------------------+       v
                                                                            Discord
```

The four live paths—market/options evidence, broker observation, Sir Loke reasoning/policy, and
Discord conversation—are independently healthy or degraded. One global connected state cannot
stand in for their readiness.

## Ownership

| Responsibility | Canonical owner | Must not own |
|---|---|---|
| Provider connectivity and native market objects | NautilusTrader and approved adapter | Product interpretation |
| Logical live/historical demand, pacing, retries, and cancellation | Data acquisition owner | Session meaning or trade advice |
| Calendar/session truth and evidence health | Deterministic session/evidence owners | Broker state or agent conclusions |
| Measurements, entities, state, and semantic transitions | Bounded deterministic capability owners | Discord rendering or order action |
| Option discovery and expression-quality evidence | Options intelligence owner | Underlying thesis or recommendation authority |
| Account/order/fill/position facts | Read-only broker observation owner | Trader thesis or mutable broker handles downstream |
| Recommendation linkage and complete trade history | Trade episode owner | Conveniently inventing attribution |
| Intervention, acknowledgement, noncompliance, and cooldown | Deterministic advisory policy | Broker enforcement |
| Bounded state supplied to the model | Agent read-model projector | Raw streams, credentials, or arbitrary queries |
| Evidence-cited synthesis and conversation | Sir Loke | Evidence admission, policy transitions, infrastructure, or execution |
| Discord authentication and delivery | Discord bot transport | Market, broker, policy, or trade truth |
| Durable audit | Approved PostgreSQL writers | Raw provider storage or event-bus ownership |

One implementation component may own more than one closely related responsibility only when its
lifecycle, workload, failure, and authority boundaries remain explicit. The table is canonical
ownership, not a mandatory actor-per-row topology.

## Truth And Authority Classes

Every consequential Sir Loke response separates:

- **verified fact:** an admitted authoritative observation or deterministic state;
- **measured evidence:** a reproducible calculation with units, parameters, and lineage;
- **inference:** a bounded interpretation allowed by the evidence contract;
- **hypothesis:** a possible explanation which still needs support;
- **recommendation:** advisory action for Markeitect's judgment;
- **policy decision:** deterministic allowed, withheld, or escalated behavior; and
- **unknown:** missing, stale, conflicting, unsupported, or unverified information.

The model may explain and synthesize these classes. Deterministic code owns source admission,
identity, freshness, broker reconciliation, authorization, policy transitions, and the
no-execution invariant. A model response never promotes an inference into a broker fact or a
hypothesis into an accepted recommendation.

## Request Classes

The system keeps five request classes separate:

1. **Provider request:** acquire a supported native observation, definition, bounded option
   snapshot, or status through the acquisition owner.
2. **Historical-evidence request:** obtain exact bounded past observations needed by one approved
   capability. Raw responses remain transient by default.
3. **Capability request:** activate or reconfigure one registered deterministic calculation inside
   approved parameter and resource bounds.
4. **State query:** inspect an already admitted bounded projection such as health, metrics,
   entities, opportunities, or a trade episode.
5. **Agent intent:** ask deterministic policy to authorize work; it is not direct infrastructure
   or provider access.

An accepted request means only that policy admitted it. `accepted`, `modified`, `queued`, `active`,
`ready`, `degraded`, `rejected`, `failed`, `expired`, `canceled`, and `completed` are distinct
lifecycle results.

### Common envelope

Every executable request identifies, where applicable:

- stable request, schema, requester, authority, purpose, and consumer identity;
- instrument, exact contract, venue, account/environment, session, trade date, horizon,
  resolution, or UTC bounds;
- source/provider and required evidence fidelity;
- requested cadence, depth, maximum observations, and option/strike bounds;
- priority, deadline, lease/expiry, cancellation, and replacement identity;
- parameter, capability, configuration, and policy versions with effective time;
- estimated and admitted provider/CPU/memory/model cost;
- correlation, causation, conversation, opportunity, recommendation, and trade-episode identity;
- side-effect class and exact authorized scope; and
- lifecycle outcome, evidence health, missing/conflicting reasons, and audit identity.

A request never silently implies that data exists, is fresh, has volume, is consolidated, is
reported rather than inferred, or has already completed.

## Tool And Side-Effect Classes

Calling all Sir Loke tools “read-only” is too imprecise. V1 may expose only typed, bounded tools in
these explicit classes:

| Class | Examples | Allowed effect |
|---|---|---|
| Pure state query | Get market state, evidence health, option candidates, opportunity, trade episode | Reads a bounded immutable projection |
| Resource request | Request/release observation, history, capability, focus lease, or option refresh | May change provider/runtime work only after deterministic policy admission |
| Canonical app-state change | Propose/revise/invalidate a recommendation; record an interpretation, trader statement, acknowledgement, or abstention | Appends/revises versioned Markeitech state; never broker state |
| Audit write | Record validated agent/tool/policy lifecycle and decision snapshot | Writes approved durable audit through its owner |
| Outbound publication | Publish a reply, proactive warning, report, or delivery result | Sends only through the authenticated Discord transport |

No class may expose credentials, arbitrary Python or SQL, filesystem/network escape hatches,
mutable framework objects, unrestricted configuration, an execution client, or an order method.
The overarching V1 boundary is **no broker execution**: no submit, modify, bind-for-control,
cancel, replace, exercise, or close action is reachable from Sir Loke, Discord, policy, trade
lifecycle, or broker observation.

## Broker Observation Boundary

The first accepted environment is Markeitect's IB paper account through TWS. Every admitted fact
retains a stable non-secret account identity or alias, explicit `paper` or `live` environment,
broker/source identity, contract, order/fill/position identity, event and receive timestamps,
revision, reconciliation origin, and partial/duplicate/conflict state.

NautilusTrader's native execution/reconciliation facilities are evaluated first because they may
provide the required observations, cache, events, and reports. They also possess order capability,
so a narrow bridge must publish sanitized immutable facts and hide all execution objects and
methods from downstream consumers.

Manual TWS visibility is not assumed. Client ID `0`, `reqOpenOrders`, and `reqAutoOpenOrders` may
bind manual orders for API control; binding a working exchange order can cancel/resubmit it and
affect queue priority. Gate 1 therefore inspects the exact startup calls, request methods,
configuration defaults, and native reconciliation behavior before any connection. The connected
paper probe stops on any unexpected binding, control, resubmission, or order action.

## Trade Episode And Recommendation Linkage

A trade episode can contain a Sir-Loke recommendation or a trader-originated plan, multiple
orders, partial fills, cancel/replace activity, scale changes, commissions, interventions,
acknowledgements, closure, and one after-trade report.

Identity and history rules are:

- preserve opportunity, recommendation, account, order, fill, position, contract, policy,
  conversation, and report identities where applicable;
- preserve original thesis, trigger, invalidation, horizon, and risk declaration as immutable
  revisions;
- append later evidence, interpretation, advice, intervention, and response without hindsight
  rewriting;
- match a broker trade to a recommendation only when contract, direction, account, quantity,
  timing, and order/fill evidence support it;
- keep ambiguous attribution ambiguous; and
- create a trader-originated episode when safe attribution is absent, without inventing intent.

Sir Loke must respond promptly to an independently entered trade with verified broker facts, known
and unknown plan elements, provisional risk concerns, and a completed evidence assessment. It may
ask Markeitect for the missing thesis without delaying an urgent fact-based warning.

## Advisory Governance

Firmness is deterministic policy state, not tone. The first vocabulary supports observation,
concern, warning, urgent invalidation, acknowledgement required, noncompliance recorded,
Sir-Loke recommendation cooldown, and resolution. Exact triggers, risk inputs, time bounds,
acknowledgement rules, recovery, and cooldown are versioned configuration requiring focused
approval.

Sir Loke may interrupt, challenge, refuse endorsement, recommend reducing or closing, request an
acknowledgement, record continued noncompliance, and withhold its own later recommendations. It
cannot prevent a TWS trade, enforce an account limit, or act on an order.

## Option And Opportunity Boundary

Opportunities are plural and identified by target exposure, direction, horizon, episode, evidence,
trigger, invalidation, and lifecycle—not by one leading evidence instrument or chosen contract.
One opportunity may have several SPXW or QQQ 0DTE expression candidates or none.

The options owner bounds expiry and strike discovery, preserves exact product/session/settlement
identity, and evaluates executable bid/ask, spread, quote age/stability, liquidity, moneyness,
time-to-last-trade/expiry, IV/Greeks when valid, and rejection reasons. A fresh executable ask
governs long-option affordability; midpoint ranking requires a valid two-sided quote; last price
alone is insufficient. A good underlying thesis can lack a usable expression, and an attractive
premium cannot create a thesis.

GEX and vendor options-flow remain optional evidence tracks. They require licensed-use,
provenance, formula/source, timestamp, coverage, correction, and inference-rights review. They
cannot establish dealer inventory, opening/closing intent, complete strategy, consolidated flow,
causal hedging impact, or trade direction by themselves.

## Persistence And Redaction

Durable product audit must reconstruct what the system knew, requested, decided, communicated,
observed, and revised. Approved schemas may store broker facts, trade episodes, recommendation
links, interventions, acknowledgements, bounded/redacted conversation envelopes, agent/tool
lifecycle, decision snapshots, delivery results, and reports.

Credentials, raw market streams, unrestricted prompts, mutable broker objects, and secrets never
enter the read model or audit. Exact schemas, transaction boundaries, retention, redaction,
recovery, and deletion policy remain Gate 2 decisions.

## Structural Stop Gates

Stop the implementation batch if it would:

- give Sir Loke or Discord access to an order action or mutable broker object;
- create a second provider subscription owner, calendar owner, trade owner, or policy owner;
- use prose/model output as canonical evidence or policy state;
- collapse paper/live account identity or recommendation/trader provenance;
- treat accepted work as completed evidence;
- make optional GEX/options-flow/model evidence mandatory without approval;
- persist raw provider observations for hypothetical replay/backtesting; or
- hide a missing, partial, stale, conflicting, unsupported, or inferred input.
