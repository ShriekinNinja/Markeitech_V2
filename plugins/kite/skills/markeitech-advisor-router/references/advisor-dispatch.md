# Advisor Capacity And Dispatch

This is the canonical development-time dispatch contract for issue #47. Primary Kite owns host
inspection, lifecycle tool calls, and evidence preservation. The offline
`scripts/resolve_advisor_dispatch.py` validates supplied records and returns a disposition; it
cannot reserve capacity, close threads, enforce host permissions, or authenticate evidence.
The [dispatch policy](dispatch-policy.toml) owns the bounded capacity-recovery allowance.
The [allocation contract](resource-allocation.md) retains ownership of models and execution budgets.

## Required Procedure

1. Select the smallest sufficient exact-role set and its dependency DAG under council policy.
   Give each consultation a stable ID and exact question. Retain completed findings with their
   scope, source revision, evidence labels, and unresolved gates. Completion here means primary
   Kite has assessed the result for this question; a child merely finishing is not acceptance.
2. Inspect the current host's advertised capacity/counting scope, complete thread inventory, and
   actual lifecycle tool schema. Do not infer a limit from a documented default or configuration
   file. Count running, completed-but-open, and unknown threads. A primary is counted separately;
   do not also put it in the spawned-thread list. Include all threads in the limit's scope, not
   only the advisors relevant to this plan. If completeness or scope cannot be established, say so.
3. Build a sanitized plan record and run:

   ```bash
   python3 -B plugins/kite/scripts/resolve_advisor_dispatch.py plan --record -
   ```

   Use the allocation contract's stdin control-record procedure. No file creation is required.
   The [synthetic example](dispatch-plan.example.json) illustrates shape, never host evidence.
   Inspect `status`, not just process exit. Preflight the whole pending plan before the first
   launch and after a scope/dependency change. If closure is absent or unknown, every remaining
   spawn needs a free slot: running serially does not release completed threads.
4. Respect `after` dependencies. A blocked advisor blocks its dependent decisions; independent
   authorized work may continue. Do not drop required roles or turn primary Kite into a missing
   specialist to make the plan fit. Sort independent consultations by exact role name then ID.
5. Preserve completed findings before considering closure. Only task-owned completed threads
   with retained result evidence and no planned follow-up can be close candidates. If the live
   host provides an actual close operation, use it on those candidates and observe the result.
   Reinspect the inventory after closure; a candidate list or a requested close releases nothing.
   Interrupt/stop is not close unless the host explicitly establishes equivalent release.
   Never close an unrelated thread. Do not invent a tool or use hidden host APIs to reclaim slots.
6. For an eligible pending consultation, validate its allocation normally. Refresh capacity again
   and run admission with that decision and its full dispatch history:

   ```bash
   python3 -B plugins/kite/scripts/resolve_advisor_dispatch.py admit --record -
   ```

   Only `DISPATCH_READY` permits one spawn through the exact role and allocation fields. Dispatch
   calls are serialized: record each response and refresh the inventory before admitting the
   next. Created advisors may work concurrently. Admission is a point-in-time check, not a host
   reservation, so a capacity race remains possible.
7. If a child was created, record its actual execution ID and update the consultation/inventory
   before any further dispatch. Existing allocation receipts govern execution and completion.
   Follow-ups to an existing exact-role advisor must retain its role, evidence, and execution
   budgets; never relabel it as another specialist or rerun completed work to bypass a stop gate.
   Mark an advisor `retain: true` while further work is planned. The helper admits new spawns;
   it does not grant separate follow-up/model-change authority.
8. A confirmed no-child capacity refusal follows the bounded recovery below. Unknown launch or
   close outcomes require reconciliation first. Never loop probes, sleep until a guessed release,
   fabricate an execution ID, or claim that a fresh task necessarily fixes the host limitation.

## Versioned Records

Schema version 1 rejects unknown fields, duplicate JSON keys, invalid types, cycles, duplicate
threads/consultations, and unsupported roles. The same input limits as allocation apply: 1 MiB
JSON, 4,096-character strings, 128-item arrays, and nonnegative signed-32-bit integers. A boolean
is not an integer. Record strings are sanitized identifiers/references, never credentials or raw
advisor prompts/logs. Digests detect inconsistency, not forgery or durable uniqueness.

A plan has exactly `schema_version`, `plan_id`, `selected`, and `host`. Each selected entry has:

| Field | Meaning |
| --- | --- |
| `consultation_id`, `role`, `question` | Stable consultation, exact council role, bounded owned question. |
| `after` | IDs of selected upstream consultations that must be completed and assessed. |
| `state` | `pending`, `running`, `completed`, or `blocked`. |
| `evidence` | Reference for running/completed/blocked state; nullable for pending. Preserve upstream limitations. |

The host snapshot has exactly these fields:

| Field | Meaning |
| --- | --- |
| `snapshot_id`, `task_id`, `evidence` | Fresh observation ID, current task identity, and actual inventory/tool/limit evidence reference. |
| `thread_limit` | Observed nonnegative limit, or `null` for unknown; never a hardcoded default. |
| `limit_scope` | `including_primary`, `spawned_only`, or `unknown`. |
| `primary_threads` | Positive number of primary threads in this limit's scope. Subtracted only for `including_primary`. |
| `inventory_complete` | Whether all spawned threads covered by that limit were observed. |
| `close_supported` | `true` only when an actual callable close operation is exposed; `false` or `null` otherwise. |
| `threads` | Complete observed spawned-thread records, including retained completed threads. |

Each thread has exactly `thread_id`, `role`, nullable `consultation_id`, `state` (`running`,
`completed`, `closed`, `unknown`), `owned_by_task`, `retain`, nullable `result_evidence`, and
nullable `release_evidence`. Closed threads require observed release evidence. Nonclosed threads
cannot assert release. Threads outside this plan still count; associate only matching exact-role
consultations. Preserve previous-task findings as completed consultation evidence without inventing
current-task threads. Existing threads for a pending consultation require reconciliation instead
of duplicate spawning.

Plan results always preserve eligible/pending/blocked IDs and completed evidence references:

| Status | Required response |
| --- | --- |
| `READY` | Allocate an eligible consultation, refresh evidence, then run admission. |
| `PLAN_CAPACITY_BLOCKED` | Without verified closure support, the remaining plan exceeds free slots. Stop its spawns before spending available capacity; explain the host requirement. |
| `CAPACITY_UNKNOWN` | Obtain missing inventory/counting evidence; do not invent a budget. |
| `CLOSE_REQUIRED` | Preserve results, close eligible owned threads using an exposed tool, then verify release. |
| `WAITING` | Await relevant running work or a real host change, preserving results. No blind spawn loop. |
| `CAPACITY_BLOCKED` | No available slot or safe release candidate. Preserve a precise handoff. |
| `RECONCILE_REQUIRED` | Resolve inconsistent/ambiguous thread state before dispatch. |
| `BLOCKED_DEPENDENCIES` | Preserve the affected stop gates and identify the missing decision/evidence. |
| `COMPLETE` | No pending/running/blocked consultations in this supplied plan; not product or Gate acceptance. |

An admission request has exactly `schema_version`, `plan` (the current complete plan record),
`consultation_id`, `decision` (unchanged validated allocation), and `history`. Admission binds the
plan ID, selected questions/roles/edges, council and dispatch policy identities, and allocation
decision. Its result includes the host observation, dispatch number, and digest. Keep all records
in tool history; they are not authenticated host attestations. No source test can prove the
primary actually called the helper or that capacity remained available after the check.

## Refusal Recovery And Budgets

Keep an entry for every dispatch call. Each history entry has exactly `admission` (the full
returned record), `outcome` (`capacity_rejected`, `started`, `failed`, `unknown`), nullable
`execution_id`, boolean `no_child_confirmed`, `evidence`, and `host_after` (fresh full inventory).
Do not map a generic timeout or any error string alone to confirmed no-child refusal; use the
tool outcome and reconciled inventory. A started child follows the model-execution policy even
if it fails immediately.

The reviewed default permits **one additional dispatch**, in the policy envelope 0..3, only when
all prior dispatches are confirmed capacity refusals with no child and the original allocation
is unchanged. It does not authorize a second model execution. The caller must preserve history
and IDs; dropping entries or renaming a consultation to reset the budget is forbidden.

Before redispatch, inspect allocation availability again. If the original role/model/effort or
policy is no longer compatible, stop rather than silently replacing the decision. The helper
requires a fresh same-task snapshot showing a larger usable limit or fewer open threads than
the post-refusal snapshot, plus a free slot and a feasible plan. Merely renaming a snapshot,
changing completed status, or claiming closure without evidence does not qualify. Each recovery
consumes the same bounded dispatch budget. A changed policy/plan/decision invalidates the bound
history and requires explicit reconciliation; it does not reset the consultation automatically.

## Handoff And Acceptance

When capacity blocks work, report the actual host observation, missing roles/questions, dependency
consequences, completed evidence references, current repository revision/branch/PR, and the next
resolving action. Do not repeat finished consultations unnecessarily. A fresh task is a possible
workaround that needs its own preflight; cross-task history must be preserved as provenance and
reconciled before any new admission. The helper deliberately refuses cross-task automatic retries.

Host limits remain outside the plugin. Do not edit global/project Codex settings, change models,
create user-visible tasks, or alter installed caches to escape capacity without applicable user
authorization. Source publication follows the repository PR workflow. Installation and fresh-task
acceptance follow `docs/operations/kite.md`; source validation does not install this change.

Offline fixtures exercise the capacity/lifecycle/dispatch decisions without paid model calls.
Installed behavior requires a separately authorized fresh-host observation of actual router
preflight, launch/refusal handling, and any claimed release. If the host lacks close support,
accept the precise early-block behavior; do not claim reclamation. Larger-limit acceptance
requires observed host capacity after an authorized configuration change.
