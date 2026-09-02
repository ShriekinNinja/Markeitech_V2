## Scope

- What stage or slice does this PR implement?
- Is this a new scoped branch targeting the current integration branch (`master`)?
- What is intentionally out of scope?

## Contracts and behavior

- [ ] Actor, event, persistence, provider, or configuration contracts changed: describe them.
- [ ] No runtime/business behavior changed outside the stated scope.

## Verification

- [ ] Ruff passed.
- [ ] Offline V2 tests passed.
- [ ] PostgreSQL integration tests passed, when applicable.
- [ ] Live acceptance status is stated below.

Live acceptance status: `not run` / `run and passed` / `run with findings` / `not applicable`

## Operations and data

- [ ] PostgreSQL migration impact is described, or `none`.
- [ ] Configuration or environment-variable changes are documented.
- [ ] Documentation was updated, or `none` is explained.

## Integrity checklist

- [ ] No secrets, webhook URLs, passwords, tokens, local `.env`, or `system.local.toml` were committed.
- [ ] No raw market data, vendor exports, runtime logs, or database dumps were committed.
- [ ] No live IB/TWS, Discord, or execution path was invoked by CI.

## Review and merge gate

- Current PR head and verification evidence:
- Known debt, dependencies, and remaining acceptance gates:
- [ ] The three required CI jobs pass on the current PR head; pending/missing/skipped is not pass.
- [ ] No direct integration-branch push, force-push, auto-merge, or check bypass was used.

Approval/merge status: **awaiting Markeitect**. The author must not claim approval on his behalf.
Markeitect approves the current head and owns its merge. An agent may merge only when Markeitect
explicitly delegates that specific operation; CI success or review approval alone is not such
delegation. New commits require renewed approval before merge. Do not delete the branch or
worktree without separate approval.
