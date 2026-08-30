# Markeitech Desired Runtime Architecture

**Status:** Informative Markeitect requirements record and council input; not accepted architecture,
a roadmap, an implementation plan, or implementation approval

This working document captures Markeitect's desired runtime behavior and broad architectural
requirements in plain language. It describes what the system should be able to do and the
boundaries it should preserve, without selecting components, implementation details, libraries,
schemas, algorithms, or migration steps. Requirements will be added and structured here as they
emerge. They may inform later stage-specific decisions, but this document does not create or
reorder development stages and does not require action merely because a requirement is recorded.

## Relationship To Existing Requirements And Constraints

This document does not automatically replace, cancel, or weaken previously accepted product,
architecture, engineering, risk, or operational requirements merely because they are not repeated
here. Existing requirements and constraints should be brought into the review, compared with the
desired runtime described here, and reconsidered on their merits rather than silently ignored or
treated as permanently unquestionable.

Configurability remains a system-wide requirement. Anything reasonably variable should remain
explicitly configurable, bounded, and suitable for controlled optimization, even when a later
section describes the desired behavior without repeating that qualification. Optimization must
remain governed and evidence-based; it must not silently change product meaning, evidence truth,
risk authority, or operational safety.

The advisor council should identify when an existing constraint conflicts with, prevents, or
materially weakens the desired runtime. In that situation, an advisor should not merely narrow its
analysis or proposed design until it fits the constraint. It should explain the conflict, the
constraint's original purpose where known, the consequences of retaining it, and the risks and
benefits of revising or removing it. Any such change remains a proposal for Markeitect's decision;
the council does not gain authority to override an accepted requirement by identifying a conflict.

Any later accepted plan should make a best effort to preserve and reuse capabilities that
already exist when they can support the desired runtime correctly. The desired architecture is
not, by itself, a request for a complete rewrite or wholesale replacement of the current system.
Working components, accepted boundaries, integrations, tests, and operational knowledge should be
extended, adapted, or composed where that provides a sound path to the desired behavior.

Reuse should not be forced when an existing capability has incompatible semantics, duplicated or
misplaced authority, unacceptable risk, or a structural limit that would make the desired behavior
misleading or fragile. Any recommendation to replace or substantially redesign an existing part
should identify what can still be retained, explain why incremental change is insufficient, and
compare the cost and risk of adaptation with the cost and risk of replacement. The preferred plan
should be the smallest coherent set of changes that can satisfy the requirements without carrying
forward a known architectural contradiction.

## Purpose And End State

The system exists to collect market evidence and calculate the intelligence and metrics needed by
one or more live-listening AI agents. Those agents may be based on large language models or on
other forms of artificial intelligence.

For every tracked instrument, the runtime should provide the agents with the relevant, timely, and
sufficiently complete information they need to form a prediction, make a trade recommendation, or
abstain when the available evidence is not adequate. Multiple agents may listen to the same live
runtime and may have different analytical responsibilities or perspectives.

The runtime is responsible for producing and supplying trustworthy intelligence. The agents are
responsible for interpreting that intelligence and forming their predictions or recommendations.
The initial system may remain advisory, but the architecture should not prevent future agents from
being granted controlled authority to trade automatically. Any future execution authority must be
introduced explicitly and separately from intelligence access, with defined risk, permission,
oversight, and audit boundaries. Listening to intelligence or producing a recommendation must not
by itself grant permission to execute a trade.

## Risk Management

Risk management is a high-priority responsibility of the system and must remain central to any
future recommendation or automated trading capability. Its purpose is not to avoid every risky
trade or eliminate uncertainty. The system may support trades with substantial risk when that risk
is understood, intentional, and justified by the available evidence.

The purpose of risk management is to control the potential impact of being wrong. Recommendations
and future execution decisions should make their exposure, possible loss, uncertainty, and effect
on the wider account or portfolio explicit. No individual trade, collection of related trades, or
agent should be able to create uncontrolled damage. Risk authority must remain separate from an
agent's analytical confidence or desire to trade.

## Initial Trading Focus And Future Scope

The first trade styles the system should support are:

- zero-days-to-expiration options on SPX;
- options with zero to three days to expiration on SPY and QQQ; and
- NQ and ES futures.

This is the initial product focus, not a permanent limit on the system's instruments, asset
classes, holding periods, or trade styles. The runtime should be able to extend to additional
instruments and forms of trading without treating the initial products as universal assumptions.
Evidence instruments, recommended trade instruments, and instruments eventually authorized for
execution may overlap, but they should remain distinguishable roles.

## Dynamic Observation And Governed Agent Requests

The universe of instruments tracked for data and analysis should be able to change while the
runtime is operating. Authorized agents should be able to request changes such as:

- adding or removing an instrument from the observation watchlist;
- requesting additional data for an instrument;
- running an available analysis on another instrument;
- enabling, disabling, or configuring an indicator or analytical capability; and
- changing the depth, timeframe, or duration of an approved observation or analysis.

An agent request is a proposal, not immediate authority and not evidence that the requested data or
result exists. A separate governing authority should decide whether the request is permitted,
valid, supported, affordable, and safe within the runtime's current resource and provider limits.
It should control the scope, duration, priority, and cumulative impact of agent requests so that no
agent or group of agents can expand observation or calculation without bound.

Every request should have an explicit outcome, including when it is accepted, still preparing,
partially available, rejected, expired, failed, or unsupported. Agents must receive the actual
state and evidence produced by the system and must not fill missing data, assume an analysis ran,
or invent a result when a request could not be satisfied.

## Top-Down Multi-Timeframe Intelligence

Market analysis should support a top-down process that begins with broader timeframes and drills
down through progressively finer timeframes when additional context or entry precision is useful.
The larger timeframes should establish the broader structure, direction, important locations, and
possible objectives. Smaller timeframes should refine that understanding rather than being
interpreted in isolation from the larger context.

The runtime should be able to calculate, track, compare, and relate metrics and intelligence from
multiple timeframes across multiple instruments at the same time. It should preserve which
instrument, timeframe, observation period, and source produced each piece of evidence, while also
making meaningful agreement, disagreement, change, and dependency between them available to the
agents.

Higher-timeframe events may change the relevance or interpretation of lower-timeframe evidence.
For example, if an established daily uptrend is broken, the daily evidence may establish a broad
change in structure while a lower timeframe provides more precise evidence about the next likely
objective, path, or trade opportunity. This is an example of the required cross-timeframe
reasoning, not a fixed rule that every daily trend break has one predetermined target.

The drill-down depth should depend on the decision and its risk. Some trades may require detailed
lower-timeframe or order-flow evidence for a precise entry. Other trades may be acceptable without
that precision when the risk model explicitly permits the resulting uncertainty and exposure.
Order flow should therefore be available as the finest level of refinement where it is relevant,
but it should not be a universal prerequisite for every prediction, recommendation, or future
trade.

## Cross-Instrument Decision Context

Some market decisions depend on the combined state and movement of several instruments rather
than on one instrument viewed alone. The runtime should be able to observe related instruments
together, align their evidence in time, track how their relationships develop, and present the
combined context needed to evaluate a prediction or trade opportunity.

For example, an agent might observe VIX and CL declining sharply while SOXL is rising, use that
combination as context for considering an NQ long, use NQ's own structure to decide whether the
opportunity is more consistent with a scalp or an intraday trade, and continue monitoring ES while
the idea remains active. This illustrates a connected, multi-instrument decision process. It does
not define a permanent instrument set, assume that these relationships are stable, or establish a
fixed rule that the observed combination must produce an NQ-long conclusion.

The relevant instruments, relationships, timeframes, analytical context, and decision horizon
should be defined and revised separately as the system evolves. The runtime should support those
future definitions without embedding today's examples as universal market assumptions. Agents
should be able to distinguish direct observations from calculated relationships and from their own
interpretations, and should be shown when required cross-instrument evidence is missing, stale,
misaligned, conflicting, or no longer supports the original context.
