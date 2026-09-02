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

## Branch And PR Workflow

Every repository change, including a documentation edit or small fix, follows this protocol.

1. Begin from the current integration branch (`master`) on a **new** stage/task-specific branch
   without a `codex/` prefix. Preserve unrelated local work; use a separate worktree when needed.
2. Explain the intended batch and boundaries before editing.
3. Implement the authorized scope, update its documentation, and run proportional verification.
4. Commit the scoped files with a detailed message, push the change branch, and open a detailed
   PR into `master`. Use a draft if unfinished; an implementation-ready handoff includes a PR URL.
5. Address requested review fixes through ordinary commits on that same open PR and rerun the
   affected checks. Do not combine unrelated work or reuse the branch after merge.
6. **Stop before merge.** Markeitect approves the current head and merges it after all three
   required CI checks pass. An agent may perform only a specifically delegated merge, using a
   merge commit and the approved head. Any later commit requires renewed approval.
7. After the merge is verified, start the next change from refreshed `master` on another new
   branch. Do not delete branches or worktrees without approval.

The authorized change request includes commits, branch pushes, and PR publication; it does not
authorize merge. Read-only requests authorize no edits; plan-only work stays limited to the
requested planning artifact. Explicit no-commit or no-push instructions still limit publication.
Never commit or push directly to `master`, enable auto-merge, bypass checks, or force-push. Local
IDE review is available on request but is not the default delivery gate.

Do not commit secrets, machine configuration, vendor data, logs, database dumps, or raw market data.

## Verification

```bash
uv run ruff check src tests
uv run pytest -q tests -m "not postgres"
```

Connected IB acceptance is manual and operator-owned. Automated tests and CI must never connect to
TWS/IB Gateway, Discord, or a live market-data provider.

See `docs/operations/github-workflow.md` for the full integration policy.
