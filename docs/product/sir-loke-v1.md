# Sir Loke V1 Product Definition

**Status:** Accepted product direction; implementation and connected acceptance remain incomplete

**Accepted by:** Markeitect on 2026-09-05

**Initial user and deployment:** Markeitect only, running locally beside Interactive Brokers
Trader Workstation (TWS) and participating in an allowlisted private Discord context

This document is the canonical product definition for the first useful Markeitech release. The
[project charter](../../markeitech.md) supplies repository-wide invariants, the
[current-status ledger](../current-status.md) says what exists now, and the
[delivery blueprint](../roadmap/v2-market-events-live-agent-plan.md) defines the implementation
path. Detailed stage and architecture documents remain authoritative only for their bounded
technical subjects.

## Product Outcome

Markeitech addresses the mental part of discretionary day trading: fear, greed, FOMO, revenge
trading, attachment to an earlier bias, fighting a trend, bag-holding, and reluctance to admit
that a thesis has failed.

**Sir Loke is the product's first visible experience.** He is a live trading companion, mentor,
and configurable advisory governor backed by Markeitech's deterministic evidence system. The
market-data, measurement, entity, event, options, policy, and audit layers exist to let Sir Loke
recommend, monitor, challenge, explain, and abstain honestly. They are not the user-facing product
by themselves.

The first version succeeds when it helps Markeitect make and maintain a deliberate trading
decision—not merely when it calculates another indicator or sends another health notification.
Profit or one successful trade is useful outcome evidence but is not sufficient product
validation.

## First-Version Scope

### User experience

The first usable Sir Loke is a **live, two-way Discord bot**. It is not an offline prompt demo,
one-way webhook, dashboard, command-line transcript, or manually scripted simulation.

Sir Loke must:

1. receive ordinary conversational messages from Markeitect and respond in context;
2. initiate a conversation when a material opportunity, trade, contradiction, invalidation,
   broker event, risk concern, or evidence failure requires attention;
3. provide concise current-market explanations backed by admitted evidence;
4. recommend a qualified trade when evidence and expression quality support one, or abstain
   explicitly when they do not;
5. detect orders, fills, position changes, and closures reported by the approved broker-observation
   path, whether or not Sir Loke recommended the trade;
6. analyze a trader-originated trade immediately without inventing the trader's thesis;
7. monitor each open trade against its original thesis, declared plan, changing evidence, and
   configured advisory policy;
8. challenge plan drift, invalidated reasoning, unsupported risk, bag-holding, trend fighting,
   FOMO, revenge behavior, and refusal to acknowledge changed evidence;
9. communicate with policy-controlled firmness and request an explicit acknowledgement when
   configured conditions require it;
10. preserve what was known and advised at each point rather than rewriting the historical thesis
    with hindsight; and
11. publish a factual after-trade report containing the plan, evidence, broker-reported execution,
    interventions, trader responses, outcome, and supportable lessons.

### Initial trade and evidence scope

- The first trade-expression products are **SPXW 0DTE** and **QQQ 0DTE** options.
- This pair is an initial delivery boundary, not a permanent whitelist or a configured preference
  for one product over another.
- Evidence instruments are selected for the current decision. ES, NQ, SPX, QQQ, volatility, and
  other approved instruments may supply context without becoming the trade expression.
- SPY options, 1–3 DTE expressions, futures as trade expressions, and other products remain later
  candidates unless Markeitect changes the first-version boundary explicitly.
- Sir Loke can be available whenever the local runtime is operating. Availability does not mean
  every instrument is tradable. Authoritative exchange sessions, maintenance periods, holidays,
  halts, expiration, and last-trade rules govern eligibility and must be stated plainly.

The evidence corridor is intentionally minimum-but-honest. The first version does not need every
planned analytical capability, but it may not use a language model to manufacture missing market,
session, option-contract, liquidity, expiration, settlement, risk, or broker facts.

## The Two Trade-Origination Paths

Both entry paths converge on one canonical trade episode while preserving their different
provenance.

### Sir-Loke-recommended trade

Before the position exists, Sir Loke publishes a versioned recommendation containing:

- target exposure, direction, horizon, and opportunity identity;
- proposed product and exact expression candidate when one is qualified;
- supporting and conflicting evidence;
- trigger and entry conditions;
- invalidation and expiry;
- important missing, stale, or uncertain evidence;
- applicable risk context and policy identity; and
- advisory/no-execution status.

If Markeitect enters the trade, the broker observation may be linked to the recommendation only
when contract, direction, timing, quantity, account, and order/fill evidence support that link.
Ambiguous matches remain ambiguous. Sir Loke must revise or invalidate his own recommendation when
the evidence changes; authorship gives a thesis no permanent authority.

### Trader-originated trade

When a broker-reported trade cannot be attributed safely to a Sir Loke recommendation, the system
opens a trader-originated episode. Sir Loke promptly reports:

- the exact instrument, contract, direction, quantity, entry/fill state, expiry, account
  environment, and exposure it can verify;
- which thesis, invalidation, risk limit, or intended horizon is known and which is unknown;
- supporting, conflicting, missing, stale, or ineligible evidence;
- its provisional safety assessment while deeper analysis is still running;
- its completed assessment and recommended action when sufficient evidence is available; and
- the intervention strength required by the active policy.

Sir Loke may ask Markeitect to state the missing thesis or plan, but it must not delay an urgent
fact-based risk warning while waiting for an explanation.

## Trade Episode And Historical Truth

A trade episode is not one Discord message or one broker order. It may contain multiple orders,
partial fills, cancel/replace activity, scale-in or scale-out actions, fees, position revisions,
and more than one conversation turn.

Every episode preserves:

- stable episode, opportunity, recommendation, account, order, fill, position, contract, policy,
  conversation, and report identities where applicable;
- recommendation-to-execution attribution and its confidence/disposition;
- effective, event, broker-reported, received, evaluated, published, and acknowledged timestamps
  where meaning requires them;
- the original thesis, trigger, invalidation, intended horizon, and risk declaration as immutable
  historical revisions;
- later evidence, interpretations, recommendations, interventions, and trader responses without
  silently replacing earlier records;
- partial, conflicting, duplicated, late, reconciled, and unknown broker state explicitly; and
- paper/live account environment on every admitted broker fact and derived episode record.

A later opportunity must qualify independently. Sir Loke may help restore composure after a loss,
but it must never frame a new trade as a way to win back money, repair confidence, or complete a
recovery sequence.

## Governance And Firmness

First-version governance is forceful but advisory. Firmness is an explicit deterministic policy
state, not merely an aggressive tone generated by the model.

The first policy vocabulary must be able to represent at least:

```text
observing
    -> concern
    -> warning
    -> urgent invalidation
    -> acknowledgement required
    -> noncompliance recorded
    -> Sir-Loke recommendation cooldown
    -> resolved
```

Exact transitions, thresholds, time bounds, risk inputs, acknowledgement rules, and cooldown
behavior remain configuration-owned and require focused approval. A state may recover only from
new evidence or an explicit trader/broker outcome, not because the model changes its tone.

Sir Loke may:

- interrupt and challenge Markeitect;
- state plainly that a thesis is contradicted or invalid;
- refuse to endorse an unsupported position;
- ask for or require an explicit conversational acknowledgement;
- recommend reducing or closing a position;
- record that Markeitect continued despite a warning; and
- withhold new Sir Loke recommendations during a configured cooldown.

Sir Loke v1 cannot:

- prevent Markeitect from trading directly through TWS;
- enforce a broker-side risk limit;
- submit, modify, cancel, replace, or close an order;
- claim that a recommendation was an executed control;
- claim that an attempted or partial fill completed a position change; or
- guarantee that it can prevent an account loss.

Future close authority is a different product and security boundary. If considered later, it
requires separately approved account, portfolio, order, fill, reconciliation, risk, permission,
kill-switch, stale-state, duplicate-action, partial-failure, and recovery semantics. Its possible
future existence does not place an order-action contract or dormant tool in v1.

## Broker Observation

### First acceptance environment

The first connected acceptance uses an **Interactive Brokers paper account through TWS**.

Sir Loke applies the same analytical standards, mentoring behavior, firmness policy, and evidence
requirements to paper and live accounts. Paper mode does not make the analysis casual; live mode
does not manufacture certainty.

Account environment remains mandatory evidence. Broker facts must carry a non-secret stable
account identity or alias and an explicit `paper` or `live` environment so that:

- different accounts cannot be joined accidentally;
- paper outcomes cannot be reported as live performance;
- connection to the wrong TWS instance becomes visible;
- reconnect and reconciliation remain attributable; and
- later live enablement has an explicit acceptance envelope.

A successful paper run does not silently authorize or validate a live-account connection. The
product behavior may be environment-neutral, but connected acceptance is environment-specific.

### Read-only product boundary

Broker observation means receiving and reconciling broker-reported account, order, fill, position,
and closure facts. It does not mean granting Sir Loke execution authority.

The implementation should first evaluate NautilusTrader's native Interactive Brokers execution
client, execution-engine reconciliation, cache, and typed events as the observation foundation.
Markeitech should not introduce a second raw IB connection unless a reviewed proof shows that the
native path cannot preserve the required manual-TWS event fidelity safely.

Nautilus execution facilities are capable of order actions even when Markeitech wants only
observation. The observation boundary therefore requires defense in depth:

- no order-action tool, intent, command schema, Discord route, or agent capability;
- the narrowest internal component allowed to receive native execution state;
- a sanitized typed broker-observation output containing facts, not mutable broker handles;
- static and adversarial tests proving agent and transport surfaces cannot reach order methods;
- explicit TWS/API settings and client identity;
- paper-first connected acceptance; and
- audit of every admitted broker event, reconciliation, omission, conflict, and failure.

Exact visibility of manually entered TWS orders under a safe client-ID and read-only configuration
is not yet verified. It is a required observation-only proof, not an assumption.

## Discord Conversation Boundary

The first interface is an authenticated private Discord bot using an allowlist for the permitted
user, server/channel or direct-message context, and message operations. The existing outbound
webhook health component is not the Sir Loke bot.

The bot transport owns authentication, connection/session handling, inbound/outbound envelopes,
Discord sequence and message identity, ordering, deduplication, retries, rate limits, reconnect,
bounded queues, and delivery results. It does not calculate market truth, broker truth, trade
identity, risk meaning, or agent conclusions.

Conversation state distinguishes:

- a user statement or plan;
- a broker-reported fact;
- deterministic market/risk evidence;
- a Sir Loke interpretation;
- a recommendation or abstention;
- a policy decision or intervention;
- an acknowledgement; and
- a notification delivery outcome.

Discord failure must not stop market-data ingestion, broker reconciliation, deterministic
analysis, or audit. Sir Loke must report dependency degradation after recovery rather than
silently presenting stale conversation state as current.

## Evidence And Reasoning Contract

Sir Loke reads a compact, bounded projection. It does not receive raw ticks, unrestricted market
history, arbitrary Python or SQL, provider credentials, database credentials, Discord secrets,
mutable framework objects, or unrestricted configuration.

Every consequential response distinguishes:

- **verified fact** — authoritative admitted observation or deterministic contract state;
- **measured evidence** — a reproducible calculation with identity, inputs, and units;
- **inference** — a bounded interpretation permitted by the evidence contract;
- **hypothesis** — a possible explanation or scenario still requiring support;
- **recommendation** — advisory action for Markeitect's judgment;
- **policy decision** — deterministic allowed/withheld/escalated behavior; and
- **unknown** — missing, stale, conflicting, unsupported, or unverified information.

The model may synthesize and explain. Deterministic code owns admission, identity, authorization,
policy bounds, evidence freshness, broker reconciliation, state transitions, and the prohibition
on execution. Invalid structured output, unsupported claims, missing citations, tool loops, model
failure, or cost exhaustion must fail into a typed abstention/degradation path.

## First-Version Live Paths

The product requires four independently observable and failure-isolated live paths:

1. **Market and options evidence:** freshness-qualified facts sufficient to recommend or abstain on
   the approved first expressions.
2. **Broker observation:** timely account/order/fill/position/closure facts from the accepted
   paper-through-TWS path.
3. **Sir Loke reasoning and policy:** compact read model, conversation state, typed read-only tools,
   citations, abstention, intervention, and audit.
4. **Discord conversation:** authenticated inbound dialogue and bounded outbound replies/proactive
   messages.

“Runtime connected” is not end-to-end readiness. Sir Loke must report whether each required path is
ready, degraded, stale, unavailable, or outside its accepted scope and must narrow or abstain when
the required path is unusable.

## End-To-End Acceptance

The first usable release is accepted only when deterministic fixtures and separately authorized
connected paper evidence demonstrate all of the following:

1. Sir Loke enters the private Discord context and reports the actual readiness of market,
   options, broker-observation, agent, Discord, and audit dependencies.
2. Markeitect can ask for current context and receives an evidence-qualified response.
3. Sir Loke can proactively publish one genuinely supported SPXW or QQQ 0DTE recommendation—or
   abstain with the exact missing/conflicting reasons.
4. A corresponding manually entered TWS paper trade is detected and linked to the recommendation
   only when its identity supports the link.
5. A separate trader-originated TWS paper trade is detected, acknowledged, analyzed, and monitored
   without an invented thesis.
6. Partial fills, scale changes, cancel/replace behavior, manual closure, duplicate delivery, and
   reconnect/reconciliation preserve the correct trade episode and account environment.
7. A controlled material contradiction or invalidation produces the configured firm warning and
   acknowledgement behavior within its configured timing envelope.
8. Sir Loke preserves the original thesis and later revisions, and it records the trader's
   response or non-response without rewriting history.
9. Closure produces a factual after-trade report and any configured Sir-Loke-side cooldown.
10. No agent, Discord, policy, or observation path can submit, modify, cancel, replace, or close an
    order, and no such action is attempted during acceptance.
11. A failure of Discord, the model, an optional analysis, or one instrument remains contained and
    does not corrupt broker state, market truth, unrelated capabilities, or durable audit.
12. The acceptance record states its exact account environment, contracts, sessions, configuration,
    versions, timestamps, evidence gaps, and unsupported generalizations.

## Explicitly Deferred

- broker-side order prevention or automated closing;
- multi-user or hosted operation;
- a full dashboard or public user interface;
- replay and backtesting;
- unconstrained dynamic instrument or capability expansion;
- model training or autonomous optimization;
- permanent support for every instrument, session, strategy, or trading style;
- raw market-data or full-chain retention merely for hypothetical future use; and
- any claim that v1 is validated for a live-money account.

## Decisions Still Requiring Focused Approval

These decisions do not weaken the accepted product direction. They are explicit gates for their
own implementation batches:

- the safe TWS client-ID, read-only, external-order, reconciliation, and instrument-scope settings;
- exact trade-observation contracts and the component allowed to receive native execution events;
- model provider, model identity, invocation cadence, context and cost budgets, and failure mode;
- Discord bot library/transport and allowlist details;
- precise intervention thresholds, risk inputs, acknowledgement deadlines, and cooldown policy;
- canonical trade-episode, recommendation-linkage, conversation, and report schemas;
- PostgreSQL schema, transaction, retention, recovery, and redaction policy for agent/trade audit;
- minimum sufficient SPXW/QQQ options and cross-instrument evidence; and
- measurable product outcomes such as invalidations noticed in time, plan deviations caught,
  time/exposure beyond invalidation, acknowledgement behavior, and recommendation utility.

No implementation should convert one of these gates into an undocumented default.
