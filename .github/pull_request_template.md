## Problem and result

<!-- Explain the problem and the resulting behavior. A concrete before/after example helps. -->

## Scope and tracking

- Stage or task:
- Related issue: <!-- Link the tracking issue. Use "Closes #123" only when this PR completes its accepted checklist; otherwise "Refs #123". -->
- Approved plan comment and approval record: <!-- Link both issue comments. -->
- Included files and responsibilities:
- Outside this batch:
- Labels: <!-- Apply bug, enhancement, documentation, or question in GitHub; this text does not set labels. -->
- Milestone: <!-- Existing accepted stage, if applicable; otherwise none. -->

### Approved milestone checklist

<!-- Copy the approved issue plan here, including each milestone's outcome/scope, human and agent
     time estimates, suggested model/reasoning effort, and Spark suitability. Update checkboxes and
     exact-head evidence as work lands. Milestone approval is explicit; link its issue comment or
     PR comment and record any PR-side decision on the issue before continuing. -->

- [ ] M1 — <!-- Approved scope; human/agent estimate; model/effort; Spark suitability. -->
  Approval to proceed: <!-- Link the approval record, or write pending. -->
- [ ] M2 — <!-- Add or remove rows to match the approved issue plan. -->
  Approval to proceed: <!-- Link the approval record, or write pending. -->

Issue communication record: <!-- Link substantive decisions, revisions, blockers, and milestone
handoffs recorded in follow-up issue comments. -->

## Contracts and behavior

<!-- Describe each effect, or write "none". -->

- Actor, event, provider, and runtime/business behavior:
- Configuration, environment variables, and dependencies:
- Schema, persistence, and data:

## Verification and live feedback

- Tests added/changed and local result:
- Specific CI failure reproduced, if any:
- Changed document/package checks or artifact generation:
- PR CI status: <!-- Broad root/PostgreSQL/lint/Kite/API-doc checks run on the PR. -->
- Diff and file-scope review:

Do not routinely rerun full suites locally. Simple changes do not require a new test solely for
process. Record actual results without implying unexercised behavior passed.

For runtime work, include a short practical live handoff. Documentation-only work: not applicable.

- Exact revision and setup/commands:
- Account/instruments, intended actions and run authorization:
- Steps, expected result and stop condition:
- Result location, Markeitect's feedback and remaining unexercised cases:

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
- [ ] The four required CI jobs (V2 Ruff, V2 Offline Tests, V2 PostgreSQL Integration, and API
      docs verification) pass on the final current PR head; pending/missing/skipped is not pass.
- [ ] Every approved milestone is complete and has explicit Markeitect approval recorded on the
      issue before the next milestone began.
- [ ] @ShriekinNinja has submitted an approving review covering the current head.
- [ ] No direct integration-branch push, force-push, auto-merge, or check bypass was used.

Contributors and their agents publish through their own authorized GitHub identities and request
`@ShriekinNinja` as reviewer. Sir Kite is Markeitect's local publishing setup for his agents;
other contributors do not need its credentials. GitHub cannot request or accept an approving
self-review: Markeitect's agents use Sir Kite so `ShriekinNinja` can approve their PRs. If that
local setup is unavailable, report the identity blocker. Do not mark approval above or substitute
a label, assignee, mention, comment, or agent-generated review. Templates and `CODEOWNERS`
do not enforce the merge gate by themselves; see
[the GitHub workflow](https://github.com/ShriekinNinja/Markeitech_V2/blob/master/docs/operations/github-workflow.md).

Approval/merge status: **awaiting Markeitect**. The author must not claim approval on his behalf.
Markeitect approves the current head and owns its merge. An agent may merge only when Markeitect
explicitly delegates that specific operation; CI success or review approval alone is not such
delegation. New commits require renewed approval before merge. Do not delete the branch or
worktree unless the approved issue plan includes that task-local cleanup. Record exact targets on
the issue before merge; after a verified merge, remove only a clean task-owned branch/worktree.
