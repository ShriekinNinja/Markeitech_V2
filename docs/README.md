# Markeitech Documentation

The repository documents current authority, accepted future direction, operations, and generated
API output. Completed stage plans, research snapshots, and review handoffs live in Git and merged
pull requests rather than competing with current documents.

## Authority Order

1. [`../markeitech.md`](../markeitech.md) — durable direction and engineering principles.
2. [`current-status.md`](current-status.md) — implemented state and known limitations.
3. The selected issue and approved plan — actual task scope and acceptance.
4. [`development-guidelines.md`](development-guidelines.md) and the smallest relevant architecture
   or operations contract — implementation guidance.

[`roadmap/live-foundation-plan.md`](roadmap/live-foundation-plan.md) records direction;
[`roadmap/development-backlog.md`](roadmap/development-backlog.md) records candidates. Neither expands
an active issue. Plans, generated diagrams and historical notes do not establish implementation.

## Architecture

- [Runtime foundation](architecture/runtime-foundation.md)
- [Market data and acquisition](architecture/market-data-and-acquisition.md)
- [Session and evidence health](architecture/session-evidence-health.md)
- [Deterministic evidence contracts](architecture/deterministic-evidence-contracts.md)

These four documents consolidate the active architecture. The system-diagram manifest and its
generated review artifacts now live with the isolated tool under
[`../tools/system-diagram/docs/`](../tools/system-diagram/docs/).

## Detailed Reference And Development Collaboration

- [Kite focused skills](development/kite-advisor-council.md) — direct domain guidance and optional
  independent review for the selected development task.

## Operations

- [Developer setup](operations/developer-setup.md)
- [Kite installation and operations](operations/kite.md)
- [GitHub workflow](operations/github-workflow.md)
- [Interactive Brokers setup and execution development](operations/ib-setup.md)
- [IB market-data subscriptions](operations/ib-market-data-subscriptions.md)
- [Futures rollover](operations/v2-futures-rollover.md)
- [PostgreSQL](operations/v2-postgresql.md)
- [Runtime resource telemetry](operations/v2-runtime-resource-telemetry.md)
- [Discord health webhook](operations/discord-health-webhook.md)
- [V2 API documentation](operations/v2-api-documentation.md)

## Generated API Documentation

[`api/`](api/) is tracked generated output. Its source-analysis tool, registries, templates, and
tests live under [`../tools/api-docs/`](../tools/api-docs/). Do not edit generated API pages by
hand or run bare MkDocs commands; use the first-party wrapper described in the operations guide.

## History

Retired V1 source and superseded V2 plans remain recoverable through Git history, migration tags,
and merged pull requests. They are not current product or architecture authority and must not be
reintroduced without a separately reviewed admission into current V2 contracts.
