# Markeitech Documentation

This index separates current authority, implemented architecture, future intent,
operations, working notes, and historical material.

## Authority Order

When documents disagree, use this order:

1. [`markeitech.md`](../markeitech.md) defines current product and engineering
   invariants.
2. [`current-status.md`](current-status.md) records implemented, current, and
   next work plus validation debt.
3. The [decisions register](architecture/decisions-register.md) records accepted
   architectural decisions and their rationale.
4. [Runtime architecture](architecture/runtime-architecture.md) and
   [data contracts](architecture/data-contracts.md) describe implemented design.
5. The [implementation roadmap](roadmap/implementation-roadmap.md) expresses
   future intent and may change through review.
6. Operations documents describe how to run and inspect the system.
7. Notes and archive documents are informative, not normative.

Implementation and tests remain the final evidence when a descriptive document
has not yet been updated. Correct the document rather than preserving an
accidental disagreement.

## Current Guidance

- [Project charter](../markeitech.md)
- [Current status](current-status.md)
- [Development guidelines](development-guidelines.md)

## Architecture

- [Decisions register](architecture/decisions-register.md)
- [Runtime architecture](architecture/runtime-architecture.md)
- [Data contracts](architecture/data-contracts.md)
- [V2 runtime messaging discovery](architecture/v2-runtime-messaging-discovery.md)
- [V2 runtime control plane](architecture/v2-runtime-control-plane.md)
- [V2 Discord system health](architecture/v2-discord-health.md)
- [V2 persistence boundary discovery](architecture/v2-persistence-boundary-discovery.md)

## Roadmap And History

- [V2 infrastructure plan](roadmap/v2-infrastructure-plan.md)
- [Active implementation roadmap](roadmap/implementation-roadmap.md)
- [Runtime, market events, and Discord delivery plan](roadmap/runtime-market-events-discord-plan.md)
- [Trading quality evidence plan](roadmap/trading-quality-evidence-plan.md)
- [Detailed implementation history](roadmap/implementation-history.md)

The roadmap is intentionally concise. The history retains completed slice detail
for investigation and context, but it does not reopen old stage gates.

## Operations

- [Interactive Brokers setup](operations/ib-setup.md)
- [Operator context log guide](operations/operator-context-logs.md)
- [Operator signal log guide](operations/operator-signal-logs.md)
- [Persistence maintenance](operations/persistence-maintenance.md)
- [Reference set enrichment](operations/reference-set-enrichment.md)
- [Signal outcome audit](operations/signal-outcome-audit.md)

## Research

- [Trading frameworks study](research/trading-frameworks-study.md)

Research documents preserve sourced ideas, hypotheses, and unresolved questions.
They are informative and do not define product behavior until an accepted
decision or roadmap item promotes a tested result.

## Notes And Archive

- [Markeitect notes](notes/markeitect-notes.md)
- [Original greenfield brief](archive/initial-greenfield-brief.md)
- [Stage 0 project context](archive/stage-0-project-context.md)

The archived greenfield brief is preserved as written. It explains the original
direction and stage rationale, but its stage requirements and status statements
do not override the current charter or status page.
