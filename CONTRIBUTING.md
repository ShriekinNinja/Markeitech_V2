# Contributing To Markeitech

Markeitech is proprietary. Contributions require prior approval from Markeitect and do not grant
rights to use or distribute the project.

## Before Work

Read, in order:

1. `markeitech.md`
2. `docs/current-status.md`
3. `docs/development-guidelines.md`
4. the accepted architecture and stage plan relevant to the change

Markeitect has final product and trading authority. Architecture and implementation decisions are
discussed before code changes.

## Local Workflow

1. Begin from synchronized `master` on a stage-specific branch without a `codex/` prefix.
2. Explain the intended batch and boundaries before editing.
3. Keep the batch uncommitted for Markeitect's local IDE review.
4. Commit only after explicit approval, with a detailed message.
5. Push and open a detailed pull request.
6. Merge with a merge commit only after all required CI checks pass.

Do not force-push. Do not commit secrets, machine configuration, vendor data, logs, database dumps,
or raw market data.

## Verification

```bash
uv run --project v2 ruff check v2/src v2/tests
uv run --project v2 pytest -q v2/tests -m "not postgres"
```

Connected IB acceptance is manual and operator-owned. Automated tests and CI must never connect to
TWS/IB Gateway, Discord, or a live market-data provider.

See `docs/operations/github-workflow.md` for the full integration policy.
