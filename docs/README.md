# Markeitech Documentation

The repository documents current authority, accepted future direction, operations, and generated
API output. Completed stage plans, research snapshots, and review handoffs live in Git and merged
pull requests rather than competing with current documents.

## Authority Order

When sources disagree, use this order and stop for Markeitect's decision on a material conflict:

1. [`../markeitech.md`](../markeitech.md) — durable product and engineering charter.
2. [`product/sir-loke-v1.md`](product/sir-loke-v1.md) — first useful product outcome.
3. [`current-status.md`](current-status.md) — what is implemented and accepted now.
4. [`roadmap/sir-loke-v1-delivery-plan.md`](roadmap/sir-loke-v1-delivery-plan.md) — ordered future
   gates; [Gate 1](roadmap/sir-loke-v1-delivery-plan.md#gate-1-native-ibtws-observation-proof) is the
   next product batch.
5. [`development-guidelines.md`](development-guidelines.md) — implementation and review rules.
6. The smallest accepted architecture or operations document governing the exact subject.

A plan, generated diagram, test result, historical note, or remembered conversation is not proof
of current implementation.

## Product And Status

- [Sir Loke V1 product definition](product/sir-loke-v1.md)
- [Current status](current-status.md)
- [Sir Loke V1 delivery plan](roadmap/sir-loke-v1-delivery-plan.md)
- [Unresolved development backlog](roadmap/development-backlog.md)

## Architecture

- [Runtime foundation](architecture/runtime-foundation.md)
- [Market data and acquisition](architecture/market-data-and-acquisition.md)
- [Session and evidence health](architecture/session-evidence-health.md)
- [Deterministic evidence contracts](architecture/deterministic-evidence-contracts.md)
- [Sir Loke V1 boundaries](architecture/sir-loke-v1-boundaries.md)

These five documents consolidate the active architecture. The system-diagram manifest and its
generated review artifacts now live with the isolated tool under
[`../tools/system-diagram/docs/`](../tools/system-diagram/docs/).

## Detailed Reference And Development Collaboration

- [Session-metrics replacement plan](reference/session-metrics-replacement-plan.md) — detailed
  active V3 replacement work; not proof that disabled owners are available.
- [Kite advisor council](development/kite-advisor-council.md) — development-time consultation,
  separate from Sir Loke runtime behavior.
- [Kite resource allocation](development/kite-advisor-allocation-design.md) — per-consultation
  model/effort selection, with bounded execution evidence and remaining acceptance gates.

## Operations

- [Developer setup](operations/developer-setup.md)
- [Kite installation and operations](operations/kite.md)
- [GitHub workflow](operations/github-workflow.md)
- [Interactive Brokers setup and broker-observation gate](operations/ib-setup.md)
- [IB market-data subscriptions](operations/ib-market-data-subscriptions.md)
- [Futures rollover](operations/v2-futures-rollover.md)
- [PostgreSQL](operations/v2-postgresql.md)
- [Runtime resource telemetry](operations/v2-runtime-resource-telemetry.md)
- [Discord health webhook](operations/discord-health-webhook.md)
- [Visual evidence review](operations/visual-evidence-review.md)
- [V2 API documentation](operations/v2-api-documentation.md)

## Generated API Documentation

[`api/`](api/) is tracked generated output. Its source-analysis tool, registries, templates, and
tests live under [`../tools/api-docs/`](../tools/api-docs/). Do not edit generated API pages by
hand or run bare MkDocs commands; use the first-party wrapper described in the operations guide.

## History

Retired V1 source and superseded V2 plans remain recoverable through Git history, migration tags,
and merged pull requests. They are not current product or architecture authority and must not be
reintroduced without a separately reviewed admission into current V2 contracts.
