# Markeitech Documentation

This index separates product authority, current implementation, accepted delivery direction,
implemented architecture, operations, research, and historical technical records. Superseded
working requirements and duplicate roadmaps are removed rather than left beside current authority.

## Authority Order

When documents disagree, use this order:

1. [`markeitech.md`](../markeitech.md) defines current product and engineering invariants.
2. [`product/sir-loke-v1.md`](product/sir-loke-v1.md) defines the accepted first useful product.
3. [`current-status.md`](current-status.md) records implemented behavior, current work, and
   validation debt.
4. The canonical [Sir Loke delivery blueprint](roadmap/v2-market-events-live-agent-plan.md) governs
   the product delivery sequence and maps reusable Stage 9/V3 work into it.
5. Accepted architecture and stage documents govern their bounded technical subjects; they do not
   override the product contract or claim that planned behavior is implemented.
6. The [V2 infrastructure plan](roadmap/v2-infrastructure-plan.md) preserves completed foundation
   gates; it is not the current progress ledger.
7. Future roadmaps express future intent and may change through review.
8. Operations documents describe how to run and inspect the system.
9. Research, notes, drafts, and historical decision records are informative, not normative.

Implementation and tests remain the final evidence when a descriptive document has not yet been
updated. Correct the document rather than preserving an accidental disagreement.

## Current Guidance

- [Project charter](../markeitech.md)
- [Sir Loke v1 product definition](product/sir-loke-v1.md)
- [Current status](current-status.md)
- [Development guidelines](development-guidelines.md)
- [Market intelligence request catalog](market-intelligence-request-catalog.md)

## Architecture

- [V2 runtime messaging discovery](architecture/v2-runtime-messaging-discovery.md)
- [V2 runtime control plane](architecture/v2-runtime-control-plane.md)
- [V2 Discord system health](architecture/v2-discord-health.md)
- [V2 supervision and failure policy](architecture/v2-supervision-failure-policy.md)
- [V2 persistence boundary discovery](architecture/v2-persistence-boundary-discovery.md)
- [V2 actor composition discovery](architecture/v2-actor-composition-discovery.md)
- [V2 provider and canonical data boundary](architecture/v2-provider-data-boundary-discovery.md)
- [V2 adaptive market-data plane](architecture/v2-adaptive-market-data-plane.md)
- [V2 historical dependency execution](architecture/v2-historical-dependency-execution.md)
- [V2 session and evidence health](architecture/v2-session-evidence-health.md)
- [V2 baseline metric contracts](architecture/v2-baseline-metric-contracts.md)
- [Kite advisor council](architecture/markeitech-advisor-council.md)
- [System/data-flow manifest maintenance](architecture/system-dataflow-maintenance.md)
- [System/data-flow implementation plan](architecture/toml-driven-system-dataflow-plan.md)
- [Generated system/data-flow inventory](architecture/generated/system-dataflow/complete-inventory.md)

## Roadmaps And Plans

- [V2 infrastructure foundation](roadmap/v2-infrastructure-plan.md)
- [Sir Loke v1 delivery blueprint and reusable market-evidence plan](roadmap/v2-market-events-live-agent-plan.md)
- [Market-specialist requirements traceability](roadmap/v2-market-specialist-requirements-traceability.md)
- [Stage 9C session measurements](roadmap/v2-stage-9c-session-measurements-plan.md)
- [Stage 9D entities and rolling state](roadmap/v2-stage-9d-entities-rolling-state-plan.md)
- [V3-02 session-state actor](roadmap/v3-02-session-state-actor-implementation-plan.md)
- [V3-03 session-metrics actor split](roadmap/v3-03-session-metrics-actor-split-implementation-plan.md)
- [V2 static watchlist handoff](roadmap/v2-static-watchlist-handoff.md)
- [V2 dynamic watchlist](roadmap/v2-dynamic-watchlist-plan.md)
- [V2 API documentation](roadmap/v2-api-documentation-plan.md)
- [V2 live dashboard draft](roadmap/v2-live-dashboard-plan-draft.md) — deferred projection design,
  not part of Sir Loke v1
- [V2 backlog](roadmap/v2-backlog.md)
- [V2 root promotion and V1 retirement](roadmap/v2-complete-codebase-migration-plan.md)

## Operations

- [Developer setup and machine handoff](operations/developer-setup.md)
- [Static API documentation](operations/v2-api-documentation.md)
- [Generated API reference (`docs/api/index.html`)](../docs/api/index.html)
- [Hosted API reference (GitHub Pages)](https://shriekinninja.github.io/Markeitech_V2/)
- [GitHub workflow](operations/github-workflow.md)
- [Runtime resource telemetry](operations/v2-runtime-resource-telemetry.md)
- [Operational PostgreSQL](operations/v2-postgresql.md)
- [Futures rollover](operations/v2-futures-rollover.md)
- [Interactive Brokers setup](operations/ib-setup.md)
- [Interactive Brokers market-data subscriptions](operations/ib-market-data-subscriptions.md)

## Research

- [Market-analysis specialist brief](research/market-analysis-specialist-brief.md)
- [Semantic events, AI observer, and options intelligence baseline](research/semantic-events-ai-options-baseline.md)
- [Gamma exposure and 0DTE GEX maps](research/gamma-exposure-and-0dte-gex-maps.md)
- [Options-flow specialist report](research/v2-options-flow-specialist-report.md)
- [Bokeh live-system visualization assessment](research/bokeh-live-system-visualization-shallow-assessment.md)
- [TOML/code reconciliation assessment](research/toml-code-reconciliation-shallow-assessment.md)

Research documents preserve sourced ideas, hypotheses, and unresolved questions. They are
informative and do not define product behavior until an accepted decision or roadmap item promotes
a tested result.

## Historical Technical Review Records

Working product requirements, the desired-runtime council handoff/report, and the duplicate first
market-intelligence sequence were consolidated into the Sir Loke product definition, current
status, and canonical delivery blueprint on 2026-09-05, then removed from the active tree. Their
original text remains recoverable through Git history.

- [V3-01 canonical calendar authority review](notes/v3-01-canonical-calendar-authority-review.md)
- [V3-02 session-state actor role review](notes/v3-02-session-state-actor-role-review.md)
- [V3-03 session-metrics actor split review](notes/v3-03-session-metrics-actor-split-review.md)
- [V3-04 watchlist/capability read-model review](notes/v3-04-watchlist-capability-read-model-review.md)
- [V3 visual-debug review contract](notes/v3-visual-debug-review-contract.md)
- [V3 ES visual-debug handoff](notes/v3-es-visual-debug-review-handoff.md)

These V3 records preserve bounded design/review evidence; current status and accepted stage plans
still determine whether their conclusions remain active. Historical tracked source removed from
the active tree remains recoverable through Git history and the annotated migration tags. It is
not current documentation authority.
