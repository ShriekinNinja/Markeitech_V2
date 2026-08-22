# Markeitech Documentation

This index separates current authority, implemented architecture, future intent,
operations, working notes, and historical material.

## Authority Order

When documents disagree, use this order:

1. [`markeitech.md`](../markeitech.md) defines current product and engineering
   invariants.
2. [`current-status.md`](current-status.md) records implemented, current, and
   next work plus validation debt.
3. Accepted V2 architecture documents and the
   [V2 infrastructure plan](roadmap/v2-infrastructure-plan.md) govern the active runtime.
4. Accepted V2 architecture documents describe implemented V2 design.
5. The legacy [runtime architecture](architecture/runtime-architecture.md),
   [data contracts](architecture/data-contracts.md),
   [implementation roadmap](roadmap/implementation-roadmap.md), and
   [decisions register](architecture/decisions-register.md) preserve V1 intent and history; they do
   not override accepted V2 decisions.
6. Future roadmaps express future intent and may change through review.
7. Operations documents describe how to run and inspect the system.
8. Notes and archive documents are informative, not normative.

Implementation and tests remain the final evidence when a descriptive document
has not yet been updated. Correct the document rather than preserving an
accidental disagreement.

## Current Guidance

- [Project charter](../markeitech.md)
- [Current status](current-status.md)
- [Development guidelines](development-guidelines.md)
- [Market intelligence request catalog](market-intelligence-request-catalog.md)

## Architecture

- [Decisions register](architecture/decisions-register.md)
- [V2 runtime messaging discovery](architecture/v2-runtime-messaging-discovery.md)
- [V2 runtime control plane](architecture/v2-runtime-control-plane.md)
- [V2 Discord system health](architecture/v2-discord-health.md)
- [V2 persistence boundary discovery](architecture/v2-persistence-boundary-discovery.md)
- [V2 actor composition discovery](architecture/v2-actor-composition-discovery.md)
- [V2 provider and canonical data boundary](architecture/v2-provider-data-boundary-discovery.md)
- [V2 adaptive market-data plane](architecture/v2-adaptive-market-data-plane.md)
- [V2 historical dependency execution](architecture/v2-historical-dependency-execution.md)

Preserved V1 architecture remains available in
[runtime architecture](architecture/runtime-architecture.md),
[data contracts](architecture/data-contracts.md), and the
[legacy decisions register](architecture/decisions-register.md).

## Roadmap And History

- [V2 infrastructure plan](roadmap/v2-infrastructure-plan.md)
- [V2 market events and live-agent requirements](roadmap/v2-market-events-live-agent-plan.md)
- [First market-intelligence coding sequence](roadmap/v2-first-market-intelligence-coding-sequence.md)
- [Active implementation roadmap](roadmap/implementation-roadmap.md)
- [Runtime, market events, and Discord delivery plan](roadmap/runtime-market-events-discord-plan.md)
- [V2 Stage 9C session measurements plan](roadmap/v2-stage-9c-session-measurements-plan.md)
- [Trading quality evidence plan](roadmap/trading-quality-evidence-plan.md)
- [Detailed implementation history](roadmap/implementation-history.md)

The roadmap is intentionally concise. The history retains completed slice detail
for investigation and context, but it does not reopen old stage gates.

## Operations

- [V2 developer setup and machine handoff](operations/developer-setup.md)
- [GitHub workflow](operations/github-workflow.md)
- [V2 runtime resource telemetry](operations/v2-runtime-resource-telemetry.md)
- [V2 operational PostgreSQL](operations/v2-postgresql.md)
- [V2 static watchlist handoff](roadmap/v2-static-watchlist-handoff.md)
- [Interactive Brokers setup](operations/ib-setup.md)
- [Operator context log guide](operations/operator-context-logs.md)
- [Operator signal log guide](operations/operator-signal-logs.md)
- [Persistence maintenance](operations/persistence-maintenance.md)
- [Reference set enrichment](operations/reference-set-enrichment.md)
- [Signal outcome audit](operations/signal-outcome-audit.md)

## Research

- [Market-analysis specialist brief](research/market-analysis-specialist-brief.md)
- [Trading frameworks study](research/trading-frameworks-study.md)
- [Semantic events, AI observer, and options intelligence baseline](research/semantic-events-ai-options-baseline.md)
- [Gamma exposure and 0DTE GEX maps](research/gamma-exposure-and-0dte-gex-maps.md)

Research documents preserve sourced ideas, hypotheses, and unresolved questions.
They are informative and do not define product behavior until an accepted
decision or roadmap item promotes a tested result.

## Notes And Archive

- [Preserved V1 project boundary](../LEGACY.md)
- [Markeitect notes](notes/markeitect-notes.md)
- [Original greenfield brief](archive/initial-greenfield-brief.md)
- [Stage 0 project context](archive/stage-0-project-context.md)
- [Preserved V1 current status](archive/v1-current-status.md)

The archived greenfield brief is preserved as written. It explains the original
direction and stage rationale, but its stage requirements and status statements
do not override the current charter or status page.
