## Problem and result

<!-- Explain the problem and the resulting behavior. A concrete before/after example helps. -->

## Scope and tracking

- Stage or task:
- Related issues: <!-- Use "Closes #123" only when this PR completes the issue; otherwise "Refs #123". -->
- Included files and responsibilities:
- Outside this batch:
- Labels: <!-- Apply bug, enhancement, documentation, or question in GitHub; this text does not set labels. -->
- Milestone: <!-- Existing accepted stage, if applicable; otherwise none. -->

## Contracts and behavior

<!-- Describe each effect, or write "none". -->

- Actor, event, provider, and runtime/business behavior:
- Configuration, environment variables, and dependencies:
- Schema, persistence, and data:

## Verification

<!-- Give commands and results. Use "not run" or "not applicable" with a reason, never an implied pass. -->

| Check | Command or evidence | Result |
| --- | --- | --- |
| Focused verification | | |
| Ruff | | |
| Offline V2 tests | | |
| PostgreSQL integration | | |
| Diff and file-scope review | | |

Live acceptance status: `not run` / `run and passed` / `run with findings` / `not applicable`

<!-- If run, identify the authorized run and its bounded evidence. State deferred acceptance explicitly. -->

## Operations and data

- Operational impact and recovery:
- Documentation updated:
- Known debt and follow-up issues:

## Integrity checklist

- [ ] This scoped branch targets `master` and includes only the requested batch.
- [ ] No secrets, webhook URLs, passwords, tokens, local `.env`, or `system.local.toml` were committed.
- [ ] No raw market data, vendor exports, runtime logs, or database dumps were committed.
- [ ] No live IB/TWS, Discord, or execution path was invoked by CI.

## Review and merge gate

- Current PR head and verification evidence:
- Required reviewer: **@ShriekinNinja**.
- Review request status: <!-- Requested / draft / blocked because the author is ShriekinNinja. -->
- Remaining acceptance gates:
- [ ] The three required CI jobs pass on the current PR head; pending/missing/skipped is not pass.
- [ ] @ShriekinNinja has submitted an approving review covering the current head.
- [ ] No direct integration-branch push, force-push, auto-merge, or check bypass was used.

GitHub cannot request or accept an approving self-review. If the author is `ShriekinNinja`, report
the identity blocker and arrange a separately authenticated PR author; do not mark approval above
or substitute a label, assignee, comment, or agent-generated review. Templates and `CODEOWNERS`
do not enforce the merge gate by themselves; see
[the GitHub workflow](https://github.com/ShriekinNinja/Markeitech_V2/blob/master/docs/operations/github-workflow.md).

Approval/merge status: **awaiting Markeitect**. The author must not claim approval on his behalf.
Markeitect approves the current head and owns its merge. An agent may merge only when Markeitect
explicitly delegates that specific operation; CI success or review approval alone is not such
delegation. New commits require renewed approval before merge. Do not delete the branch or
worktree without separate approval.
