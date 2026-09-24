# Live Trading Foundation Development Plan

**Direction approved:** 2026-09-24. Prioritize a working live system, practical feedback and
issue-scoped delivery. This plan does not implement or authorize connected execution.

## Sequence

1. **Direction reset.** Align active instructions, documentation and backlog with this plan.
   Preserve the generic Discord health webhook. This is document review plus a neutral webhook
   title change, not a connected runtime acceptance task.
2. **Execution engine and account monitor.** Bring up the native Nautilus execution path and expose
   actual account, order, fill and position state. Reach a small explicitly authorized live order
   lifecycle promptly. The issue selects account/client settings, exact actions and operating
   limits; inspect only the native contracts needed for that implementation and run.
3. **Concurrent actors, strategies and indicators.** Add the composition, configuration, data access
   and indicator warmup/output needed by real consumers. Reuse the existing acquisition owner and
   native streams. Demonstrate the selected consumers operating together in real time.
4. **Operate and improve.** Fix failures, bottlenecks and missing capabilities encountered in use.
   Each improvement has a concrete issue; the catalogue need not be known in advance.

These are direction priorities, not permission to implement several stages in one issue. The
active issue and Markeitect's latest instruction select the task. Do not choose future work or
advance to another capability automatically.

## Definition Of A Small Task

State the useful outcome, exact scope, direct dependencies, unresolved decisions and a short
acceptance scenario. Use existing architecture until that task or observed operation supplies a
reason to change it. No speculative framework, exhaustive audit or unrelated reliability gate is
required to begin useful work.

For execution, distinguish implementation authority from permission to operate a connected account.
Account identity, intended order actions and limits must be explicit for the live scenario.
Changes to account mode are not inferred from ports or account prefixes.

## Development And Review

Agents locally run tests they add/change and specific CI failures they need to reproduce. PR CI
owns broad regression checks. Keep generation and integrity checks limited to changed artifacts.
A simple change need not acquire a new test solely to satisfy process.

Reach the live scenario as soon as the implementation is runnable. Supply the revision, setup,
commands, intended actions, expected result and stop condition. Markeitect performs and reviews
live acceptance unless he delegates a particular run. Record real findings and address them on
the same PR. Passing CI establishes only its exercised scope; live results establish the scenario
actually run. Missing cases are recorded rather than turned into a universal proof programme.

Markeitect approves the current PR head and owns merge. Documentation-only work requires document
review. Use [GitHub operations](../operations/github-workflow.md) for issue and PR mechanics and
[current status](../current-status.md) for what is implemented.
