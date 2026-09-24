# Markeitech Project Charter

Markeitech is a live trading platform built on NautilusTrader. Its immediate goal is a working
real-time foundation for market data, the execution engine, account monitoring, and multiple
actors, strategies, and indicators operating together. Markeitect owns product, trading,
architecture, review, and release decisions.

## Current Direction

The first operational priority is to bring up the native execution engine and account monitor,
expose actual account/order/fill/position state, and exercise an explicitly authorized order
lifecycle. Then extend concurrent actors, strategies, and indicators through concrete working
consumers. The [development plan](docs/roadmap/live-foundation-plan.md) records this direction;
the selected issue defines the actual work.

Execution is in scope. The current implementation remains market-data-only until the execution
issue delivers it. Planning or implementing order capability does not authorize an agent to
connect to an account or place, modify, cancel, or close an order. Actual connected and order
actions need explicit authorization for the selected account and scenario.

The generic outbound Discord health webhook remains operational infrastructure. Instruments and
strategy choices belong to their issues; there is no project-wide preferred trade expression or
required options product. Replay and backtesting remain outside the current direction.

## Issue-Scoped Delivery

Build small changes that reach practical live use quickly. Use the current architecture and native
framework capabilities unless the selected issue or observed operation identifies a concrete gap.
Do not reopen accepted foundations, add speculative abstractions, invent product prerequisites,
or turn the backlog into work inside the current issue.

An issue names its outcome, scope, decisions and a short acceptance scenario. Investigate adjacent
code only for a direct dependency, defect or blocker. Report the connection before expanding work;
material scope changes need Markeitect's decision. Finish the issue's requested work, then stop.
Future capability selection is a separate task when requested.

Live operation and Markeitect's feedback drive priorities. A runtime change should reach a small
practical live scenario as soon as it is runnable. Record the actual result and fix concrete
findings. Do not require a subsystem-wide proof programme before the first useful run, and do not
claim an unexercised condition works. Documentation changes require document review.

## Engineering Principles

- Prefer NautilusTrader's native lifecycle, actors, strategies, indicators, cache, data delivery,
  execution and account facilities where they fit the issue.
- Keep one owner for provider demand and each canonical stream/state. Consumers declare their
  own needs; external projections render canonical state.
- Preserve exact instrument, contract and account identity, UTC internal timestamps, source and
  freshness. Distinguish observations, calculations, interpretations and unknowns.
- Use typed configuration with explicit defaults and units for variable behavior. Implement only
  the mutability and versioning needed by the issue.
- Keep callbacks non-blocking, resources bounded, and unrelated actors/strategies operating through
  a local failure. Improve recovery where the current issue or live operation requires it.
- PostgreSQL owns approved operational and semantic records. Raw market-data retention needs a
  named consumer and an explicit storage decision; do not store data for hypothetical future use.
- Preserve local work and secrets. Destructive data changes require approval and a recovery plan.

## Testing And Live Feedback

Locally, agents run the tests they add or change for the issue. They may also run a specific failing
CI test to diagnose and fix it. Do not routinely run the full suite or unrelated validation tools.
Do not create a test merely to satisfy a ritual for a simple change. Narrow document/package
checks or required artifact generation are appropriate when those files change.

PR CI owns broad regression checks: root offline tests, PostgreSQL integration, Ruff, Kite package
checks and API documentation verification. Standalone tool suites are not all included; add or run
only the checks required by the selected tool change. CI failures must be resolved before merge.

Tests support delivery. They do not replace live feedback or establish provider behavior. Keep the
live handoff short: exact revision, setup, commands, account/instruments and intended actions,
expected result, stop condition and a place to record findings. Markeitect performs and reviews
live acceptance unless he explicitly delegates a particular run. Never infer order authorization
from a development request.

## Working Agreement

Use the issue, approved plan, scoped branch and PR workflow in
[GitHub operations](docs/operations/github-workflow.md). Record meaningful decisions and milestone
results on the issue. Preserve Markeitect's current-head approval and merge authority. Do not
push directly to `master`, auto-merge, force-push or bypass checks.

Update the smallest authoritative documents affected by a change. Keep implemented state in
[current status](docs/current-status.md), direction in the development plan, and optional work in
[the backlog](docs/roadmap/development-backlog.md). Historical plans remain recoverable in Git.
