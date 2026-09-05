# Sir Loke V1 Delivery Plan

**Status:** Accepted product sequence; implementation beyond the current foundation is not complete

**Product authority:** [`../product/sir-loke-v1.md`](../product/sir-loke-v1.md)

**Implementation authority:** [`../current-status.md`](../current-status.md)

This document turns the first Sir Loke product into ordered delivery gates. It is a plan, not
proof that a capability exists. Each gate requires a separate scoped implementation or acceptance
batch and may advance only when its prerequisite evidence is accepted.

## Product Goal

The first useful Markeitech release is a private, live, two-way Discord companion for Markeitect.
Sir Loke converses in context, proposes genuinely supported SPXW or QQQ 0DTE trades, immediately
analyzes independently entered TWS trades, monitors open trade episodes, challenges contradicted
plans with configurable firmness, and produces evidence-cited reports.

The product is backed by deterministic market, session, broker, policy, identity, and audit
owners. Sir Loke explains, synthesizes, recommends, challenges, and abstains. V1 never submits,
modifies, binds for control, cancels, replaces, exercises, or closes a broker order.

## Immediate Next Action

The next development batch is **Gate 1: Native IB/TWS Observation Proof**. Before any connected
run, inspect the exact pinned NautilusTrader execution-client construction and every startup
request which could download, associate, bind, modify, cancel, or resubmit an order. Produce an
offline safety decision and a bounded paper-account probe plan. The connected probe itself needs
separate explicit authorization.

No trade episode, Discord bot, model, or agent implementation should start until Gate 1 proves a
safe observation foundation or Markeitect approves a different broker-observation boundary.

## Non-Negotiable Boundaries

- Markeitect retains product, trading, architecture, review, and release authority.
- V1 is advisory and has no broker execution capability.
- TWS paper is the first connected acceptance environment; a paper result does not authorize a
  live-money connection.
- Paper and live facts always carry an explicit account environment and stable non-secret account
  identity or alias.
- Native Nautilus objects remain the canonical high-volume provider transport.
- One acquisition owner controls provider-facing market-data and history work.
- One broker-observation owner sanitizes native account, order, fill, and position facts.
- Deterministic code owns identity, admission, evidence health, policy, linkage, and lifecycle.
- Sir Loke uses bounded typed tools with explicit side-effect classes; no arbitrary Python, SQL,
  filesystem, network, credentials, mutable framework objects, or order methods are reachable.
- PostgreSQL stores approved operational and semantic audit, not raw provider observations by
  default.
- Discord and other interfaces are projections, not owners of market, broker, policy, or trade
  truth.
- Missing, stale, conflicting, unsupported, or unverified evidence produces a named limitation or
  abstention, never manufactured certainty.
- Replay, backtesting, model training, autonomous optimization, multi-user hosting, and a full
  dashboard remain outside V1 unless separately reopened.

## Target Topology

```text
TWS paper observations ----> broker observation ----> trade episode --------+
IB market/options data -----> deterministic evidence -> opportunity --------+----> compact read model
trader Discord messages ----> conversation state ---------------------------+             |
deterministic policy -------> intervention/acknowledgement ------------------+             v
                                                                                     Sir Loke
                                                                                         |
                                                                                         v
                                                                               Discord transport

approved lifecycle, evidence references, tool calls, policy decisions, and reports -> PostgreSQL
```

The four live product paths—market/options evidence, broker observation, Sir Loke reasoning and
policy, and Discord conversation—remain independently observable and failure-isolated. A global
`READY` state does not prove all four.

## Reuse Of Existing Foundation

| Existing capability | V1 use | Limit which remains explicit |
|---|---|---|
| CLI composition and system control | Starts and supervises current runtime owners | Current readiness is narrower than product readiness |
| Interactive Brokers market-data adapter | Native definitions and observations | Does not prove manual-order observation |
| Data acquisition and historical planning | Bounded provider demand and warmup | Current correlation/concurrency envelope is narrow |
| Session state and evidence health | Calendar/session truth and freshness | Connected acceptance covers only recorded profiles |
| Measurement/entity work | Deterministic evidence substrate | Active V3 cutover is incomplete; disabled owners are not available |
| PostgreSQL operational audit | Run, health, lifecycle, and compact state evidence | Product schemas need explicit approval |
| Discord health webhook | Failure-isolated outbound projection pattern | It is not an authenticated conversational bot |
| System-diagram/API-doc tools | Static review aids | Generated views are not runtime proof |

The detailed boundaries are consolidated in
[`../architecture/runtime-foundation.md`](../architecture/runtime-foundation.md),
[`../architecture/market-data-and-acquisition.md`](../architecture/market-data-and-acquisition.md),
[`../architecture/session-evidence-health.md`](../architecture/session-evidence-health.md),
[`../architecture/deterministic-evidence-contracts.md`](../architecture/deterministic-evidence-contracts.md),
and [`../architecture/sir-loke-v1-boundaries.md`](../architecture/sir-loke-v1-boundaries.md).

## Gate 0: Product Authority Reset

**Outcome:** one coherent product definition, implementation ledger, delivery plan, architecture
set, and unresolved backlog.

Acceptance requires:

- the Sir Loke product definition records both recommendation-originated and trader-originated
  trade paths;
- paper-through-TWS is the first acceptance environment;
- V1's no-execution boundary and future-close separation are explicit;
- stale plans, research notes, review handoffs, and generated architecture artifacts no longer
  compete with current authority; and
- all surviving links, generated artifacts, and repository checks pass.

This gate completes when the documentation-consolidation PR is approved and merged. Its existence
does not complete any later product gate.

## Gate 1: Native IB/TWS Observation Proof

**Question:** Can the pinned NautilusTrader/IB path observe manually entered TWS paper orders,
fills, positions, changes, and closures without granting Markeitech order control?

### Offline safety decision

Before connecting:

1. inspect the pinned `InteractiveBrokersExecutionClientConfig`, factory, reconciliation/cache
   behavior, external-order settings, and emitted typed events/reports;
2. inspect the exact startup call graph and request methods, including any open-order download,
   auto-open-order, order-binding, reconciliation, modification, cancellation, or resubmission
   behavior;
3. distinguish `reqOpenOrders`, `reqAutoOpenOrders`, `reqAllOpenOrders`, client ID `0`, TWS API
   read-only mode, and Nautilus configuration rather than treating them as interchangeable;
4. define the narrow component which may receive native execution state and the sanitized output
   which downstream owners may see;
5. prove statically that Sir Loke, Discord, policy, and trade-lifecycle surfaces cannot reach
   order-action methods; and
6. define immediate abort criteria for unexpected binding, mutable order ownership, submission,
   modification, cancellation, replacement, or exercise behavior.

The offline review must not infer safety merely because an API setting is named “read-only.”
Binding a manual order can cancel and resubmit it at the exchange and can affect queue priority.

### Separately authorized paper probe

Record the exact TWS build, account environment, non-secret account alias, API settings, client ID,
Nautilus version, configuration digest, timestamps, and logs. Exercise observation of:

- a new manual TWS order;
- partial and complete fills;
- quantity/price change and cancel/replace behavior performed manually in TWS;
- scale-in and scale-out changes;
- manual closure;
- duplicate and late delivery; and
- disconnect, reconnect, and reconciliation.

Acceptance requires complete identity and an explicit proof that Markeitech attempted no order
action and did not bind a manual order for control. If the native path cannot satisfy that contract,
stop and present bounded alternatives; do not add a second raw IB client incidentally.

## Gate 2: Trade Episode, Recommendation Linkage, Policy, And Audit

Implement deterministic product truth before introducing a language model:

- canonical account, order, fill, position, contract, recommendation, opportunity, trade-episode,
  policy, conversation, and report identities;
- a versioned recommendation with evidence, conflicts, trigger, invalidation, expiry, and advisory
  status;
- evidence-based recommendation-to-trade linkage with explicit linked, ambiguous, rejected, and
  trader-originated results;
- immutable historical revisions for thesis, evidence, broker facts, interventions, trader
  responses, and closure;
- deterministic firmness, acknowledgement, noncompliance, and cooldown transitions; and
- approved PostgreSQL schemas, transactions, idempotency, ordering, retention, redaction,
  recovery, and query behavior.

Fixtures must cover partial fills, multiple orders per episode, scale changes, manual closure,
duplicate/late events, reconnect, ambiguous attribution, and unknown trader thesis.

## Gate 3: Authenticated Two-Way Discord Transport

Implement the private conversational transport independently of market reasoning:

- allowlisted user and server/channel or direct-message context;
- inbound/outbound identities, ordering, deduplication, retries, rate limits, reconnect, and
  bounded queues;
- typed user-statement, acknowledgement, delivery-result, and proactive-publication envelopes;
- secret isolation and sanitized logs; and
- graceful degradation which cannot stop broker observation, market evidence, policy, or audit.

The existing webhook remains a separate health projection. It is not reused as proof of bot
authentication, inbound conversation, reconnect, or rate-limit behavior.

## Gate 4: Minimum Honest SPXW/QQQ Evidence Corridor

Admit only the evidence required to make or withhold the first trade recommendation. The corridor
must preserve:

- exact underlying, evidence-instrument, option-product, contract, venue, session, expiration,
  settlement, multiplier, timestamp, provider, and account-environment identity;
- bounded contract discovery and strike/expiry selection;
- bid/ask, age, liquidity, spread, size, Greek/IV source and definition, underlying reference, and
  missing/conflicting evidence;
- independent plural opportunities and expression candidates; and
- deterministic health, eligibility, expiry, invalidation, resource, and lifecycle policy.

No globally preferred trade expression is introduced. Vendor options flow, GEX, additional DTEs,
and richer order-flow sources enter only through separately approved provenance and evidence
contracts.

## Gate 5: Bounded Sir Loke Reasoning

Implement Sir Loke against immutable compact projections and typed bounded tools. Approve the
model provider/identity, invocation triggers, context and token/cost budgets, timeouts, retry and
circuit-breaker behavior, structured output schemas, evidence citation rules, and redaction.

Deterministic validation must reject unsupported facts, invalid identities, missing required
citations, unauthorized tool requests, stale projections, tool loops, and malformed output. Model
failure or budget exhaustion becomes a typed degradation or abstention. The model cannot admit
evidence, change policy, mutate broker state, or decide that a side effect is authorized.

## Gate 6: Integrated Live Sir Loke

Join the independently accepted paths:

- readiness and degradation report on Discord startup;
- ordinary context-aware dialogue;
- proactive supported recommendation or explicit abstention;
- immediate independent-trade detection and analysis;
- open-episode monitoring and evidence-change handling;
- firm deterministic intervention and acknowledgement behavior; and
- factual closure report with immutable historical citations.

Every publication must identify the evidence snapshot and policy/model/configuration versions used.
Failures in Discord, model invocation, one analytical capability, or one instrument stay contained.

## Gate 7: End-To-End Paper Acceptance

Use deterministic fixtures first, then a separately authorized TWS paper session. Three scenarios
are mandatory and distinct:

1. **Qualified evidence:** the fixture/session meets the approved corridor; Sir Loke publishes a
   supported recommendation; a corresponding manual trade is linked only when identity proves it;
   changing evidence drives the configured monitoring and intervention path.
2. **Insufficient or conflicting evidence:** Sir Loke names the gap and abstains; no recommendation
   or recommendation linkage is invented. This proves honest non-action.
3. **Independent trade:** Markeitect enters a trade which Sir Loke did not recommend; it is detected,
   opened as trader-originated, analyzed promptly, monitored, challenged when appropriate, and
   closed/reported without inventing an earlier recommendation or thesis.

A system which always abstains cannot pass the qualified-evidence scenario. A system which always
recommends cannot pass the insufficient-evidence scenario.

Acceptance also covers partial fills, scale changes, cancel/replace, duplicate delivery,
reconnect/reconciliation, manual closure, one controlled contradiction/invalidation, explicit
acknowledgement or recorded noncompliance, and isolated dependency failure. The record states the
exact environment, identities, contracts, sessions, versions, timestamps, evidence gaps, and
unsupported generalizations. Profit is not an acceptance criterion.

## Use-Case-Scoped Reliability Gates

Before a component enters an accepted product path, close or explicitly bound its relevant debt:

| Path | Required evidence before reliance |
|---|---|
| Provider subscriptions | Initial-failure retry and controlled connection-loss/resubscription |
| Historical acquisition | Correlation, cancellation fencing, timeout, duplicate, and shutdown behavior inside the admitted concurrency envelope |
| Session/evidence projections | Late-consumer snapshot/reconcile, timeout/retry, definition identity, and stale-state behavior |
| Deterministic evidence | One producer per canonical series/subject, conflict and revision handling, warmup/restart, health/fidelity propagation |
| Broker observation | Manual-event coverage, reconciliation, identity, duplication, omission, reconnect, and no-control proof |
| Persistence | Atomic required writes, idempotency, restart recovery, redaction, terminal-run truth |
| Discord | Authentication, allowlist, ordering, retry, rate limit, reconnect, bounded shutdown |
| Sir Loke | Citation/claim validation, tool authorization, timeout/cost limits, abstention, audit, and adversarial no-execution tests |

Passing unrelated tests does not close these gates.

## Deferred Design Gates

Focused approval is still required for:

- exact broker-observation configuration and sanitized contracts;
- trade-episode, recommendation, linkage, conversation, policy, and report schemas;
- firmness thresholds, acknowledgement deadlines, risk inputs, and cooldown rules;
- Discord library, intents, allowlist, and deployment details;
- model provider, identity, budgets, invocation cadence, and failure policy;
- minimum SPXW/QQQ evidence and option-expression eligibility;
- product-audit schemas and retention/redaction;
- measurable product outcomes;
- dynamic watchlist membership ownership and lifecycle;
- optional options-flow, GEX, dashboard, richer market structure, ML, and optimization work; and
- any future broker-side prevention or close authority, which is a separate product and security
  program rather than a dormant V1 feature.

Unresolved work is tracked in [`development-backlog.md`](development-backlog.md).
