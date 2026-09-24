# Development Guidelines

The [charter](../markeitech.md) and [live foundation plan](roadmap/live-foundation-plan.md) govern
this work. The aim is a working real-time trading runtime with execution, account monitoring,
actors, strategies and indicators.

## Scope And Architecture

The selected issue defines the outcome. Inspect the affected implementation and direct contracts;
read additional architecture only when it can change that result. Reuse the current system and
native Nautilus facilities. A concrete defect, missing capability or observed failure justifies
improvement; a hypothetical future need does not.

Keep one owner for provider demand and canonical state. Consumers own their independent claims,
calculations and lifecycle. Console, Discord and UI are projections. Preserve exact account,
instrument, contract, timestamp, source and freshness. Use typed configuration for variable
behavior and only the abstraction/mutability needed by the issue.

Execution capability is an active priority. An implementation request does not authorize a live
account connection or order action. The selected run must identify the account, intended actions
and limits. Markeitect performs and reviews live acceptance unless he explicitly delegates it.

## Practical Verification

Agents locally run the tests they add or change, plus specific CI failures they need to reproduce.
Do not routinely run the full suite or unrelated tools. Do not create tests merely to satisfy
process for simple changes. PR CI runs the broad root, PostgreSQL, lint, Kite and API-doc checks.
Standalone tool suites are not universally included; use only checks required by a changed tool.

For a runtime issue, prepare a short usable live scenario as soon as the change runs. State the
revision, setup/commands, account/instruments, intended actions, expected result and stop condition.
Live findings drive fixes and subsequent priorities. Do not gate the first useful run on exhaustive
offline proofs, repeat unchanged acceptance, or claim behavior which was not exercised.

For documentation or generated artifacts, inspect the changed links/output and use the required
generator. No artificial connected run is needed. Keep test and live results honest and concise.

## Collaboration

Follow [GitHub operations](operations/github-workflow.md): issue, approved milestone plan, scoped
branch, PR, Markeitect review and merge. Preserve unrelated local work. Record substantive decisions
on the issue and stop at each agreed milestone. Do not start another task automatically.

Consult Markeitect for material changes to architecture, provider ownership, dependencies, schema,
persistence, runtime policy or issue scope. Ordinary implementation choices within the approved
issue do not need an additional permission cycle.

## Documentation

Update the smallest authoritative document needed. Current status records implementation; the plan
records direction; the backlog records optional candidates. History remains in Git.

Public API changes follow the isolated [API documentation procedure](operations/v2-api-documentation.md).
Changes to the diagram manifest use its [maintenance procedure](../tools/system-diagram/docs/maintenance.md).
Generate only affected required artifacts and do not hand-edit generated output. No incidental
package, infrastructure, database or host-plugin changes belong in an issue.
