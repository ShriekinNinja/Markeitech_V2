# TOML-from-Code Reconciliation — Shallow Feasibility Assessment

**Status:** Reference-only research note; no architecture, schema, dependency, implementation,
runtime, workflow, or product decision is approved by this document

**Prepared:** 2026-08-30

**Inspection depth:** Quick and shallow review of the current offline source census, manifest
model, and command-line boundary; no prototype, benchmark, dependency installation, runtime
connection, or advisor consultation

## Executive Finding

A script can safely update selected mechanical facts in Markeitech's architectural TOML from the
current checkout. The existing offline source census already extracts much of the required input.
It would be practical to add an assisted reconciliation command that reports code/manifest drift
and optionally applies a strict allowlist of unambiguous changes.

A complete automatic rewrite of the architectural manifest from arbitrary code is neither
currently possible nor recommended. Much of the manifest records reviewed architectural meaning,
historical status, limitations, and presentation intent that executable syntax does not contain.
Guessing those fields would reduce rather than improve trustworthiness.

## Existing Foundation

The current
[`source_census.py`](../../tools/system-diagram/src/markeitech_system_diagram/source_census.py)
reads repository-controlled Python and configuration files without importing or executing the
Markeitech runtime. It already extracts or verifies:

- actor registration keys;
- Nautilus actor IDs;
- actor composition order;
- literal signal and custom-data type names;
- tracked profile schema versions and content hashes;
- Boolean enablement conditions from tracked profiles;
- enabled or disabled state for supported conditional actors;
- implementation symbol existence;
- evidence-file existence; and
- a bounded expected `LiveNode` construction shape.

The current command line supports validation and generation only. Its comparison logic fails when
supported source/configuration facts differ from
[`system-dataflow.toml`](../architecture/system-dataflow.toml), but it does not propose or write a
correction.

## Recommended Command Shape

Add an offline command such as:

```text
markeitech_system_diagram reconcile
```

The default mode should be read-only and emit a deterministic proposal, for example:

```text
Actor added in code: visual_foo
Actor order changed: session_metrics 7 -> 8
Profile state changed: discord_health disabled -> enabled
Tracked profile hash changed
New literal contract identity: markeitech.example.event
Manifest actor absent from current composition: actor.old-example
```

An explicit second mode could apply only mechanically safe changes:

```text
markeitech_system_diagram reconcile --apply-mechanical
```

The command should remain offline, use static parsing only, write atomically, preserve the previous
manifest on failure, run full validation after writing, regenerate the complete artifact set, and
leave the resulting TOML and generated-artifact diff for review.

## Candidates for Safe Automatic Updates

The initial allowlist could include:

- composition order for an already mapped component;
- actor ID and composition key where the stable component mapping is already explicit;
- tracked profile schema version and content hash;
- existing component enablement for tracked profiles;
- literal signal or custom-data transport identities where an existing stable contract mapping is
  unambiguous; and
- verified implementation or evidence references where exactly one existing record owns the
  source symbol or file.

Every applied field should record its source path and extraction rule in the reconciliation report.
Unsupported source shapes, ambiguous mappings, and computed identities should fail closed rather
than produce a best guess.

## Facts That Must Remain Reviewer-Owned

Source syntax cannot reliably establish:

- human-readable labels and responsibilities;
- canonical semantic, transport, persistence, recovery, projection, or policy ownership;
- correct system/process boundaries and visual grouping;
- whether a relationship is data, control, request, response, callback, readiness, failure,
  persistence, notification, or projection;
- delivery, ordering, acknowledgement, replay, duplicate, and synchronization semantics;
- timestamp, lineage, fidelity, and retention meaning;
- cardinality and failure-isolation meaning;
- whether an absent component is renamed, replaced, removed, rejected, deferred, or temporarily
  disabled;
- external, future, historical, removed, and tombstone records;
- accepted limitations and intentionally unmodeled behavior; or
- generated-view selection and presentation decisions.

These fields should never be overwritten by the mechanical reconciler. New or changed facts that
require them should be emitted as unresolved review items.

## Flow Inference Is the Main Difficulty

Some subscriptions, publications, requests, responses, handlers, queue admissions, and callbacks
can be detected statically. However, Markeitech flows cross Nautilus signals and custom data,
dynamic composition, callbacks, worker queues, persistence admission, configuration gates, and
external projections.

Static syntax alone often cannot prove the canonical owner, exact source and target, contract
meaning, or delivery semantics. Reliable broad flow generation would probably require a small,
offline-inspectable declarative metadata registry near composition that explicitly maps stable
component IDs, contract IDs, producers, consumers, and flow categories.

Introducing such metadata would be a consequential architecture decision. It could improve
automation, but it must not create duplicated authority, diagram-only runtime behavior, or a path
that imports or starts Markeitech merely to discover its architecture.

## TOML Writing Considerations

Python's standard `tomllib` reads but does not write TOML. A safe writer must preserve the current
manifest's comments, stable ordering, and review-friendly structure. Two likely options are:

1. Add a TOML-preserving dependency such as `tomlkit`, subject to separate dependency and license
   approval.
2. Implement a narrow patch writer that changes only explicitly supported fields and refuses
   structural ambiguity.

The narrow patch writer is the recommended first step. A generic load-and-reserialize operation
could create large formatting diffs, lose comments, and make architectural review harder.

## Proposed Safety Rules

- Static AST and TOML parsing only; never import or execute runtime code.
- Read only repository-controlled source and tracked configuration.
- Never read `.env`, credentials, logs, databases, provider data, or live processes.
- Never connect to IB, PostgreSQL, Discord, Docker, or another service.
- Preserve stable IDs; never infer a rename from textual similarity.
- Never delete a component or contract automatically.
- Never create or delete tombstones automatically.
- Fail on duplicate IDs, unsupported dynamic source shapes, and ambiguous ownership.
- Make the update atomic and retain the previous valid manifest on failure.
- Run schema validation, source/configuration census, generation, artifact hashing, and focused tests
  after any write.
- Require the updated TOML and generated artifacts in the same reviewed commit.
- Keep a review-visible reconciliation report listing applied and unresolved changes.

## Shallow Effort Estimate

The following ranges assume one experienced engineer and the current source census as the starting
point:

| Scope | Estimated effort |
|---|---:|
| Read-only deterministic `reconcile` report using the current census | 2–4 working days |
| Safe mechanical updates for profile hashes, profile enablement, actor IDs/order, and known literal contracts | 1–2 weeks |
| Stable-ID/rename safeguards, atomic patching, rollback, diagnostics, generation, and full focused tests | 2–3 weeks total |
| Broader component and flow generation supported by new declarative source metadata | 4–8 weeks |
| Full automatic manifest generation from arbitrary runtime code | Not recommended |

## Main Unknowns

- Whether the first writer may add a TOML-preserving dependency.
- Which exact fields Markeitect wants the tool to update without per-change confirmation.
- Whether reconciliation applies only to the active profile or every tracked profile.
- How newly discovered code records receive stable manifest IDs without guessing.
- Whether declarative flow metadata belongs near composition or in a separate repository-owned
  static registry.
- Whether unresolved differences should block generation, block CI only, or remain warnings during
  an initial migration period.

## Recommendation

Build an assisted reconciler rather than an autonomous architecture generator:

1. Reuse the current source census to produce a normalized mechanical snapshot.
2. Compare it with the validated manifest and emit an exact proposed delta.
3. Apply only a strict allowlist of unambiguous fields when explicitly requested.
4. Preserve every reviewer-owned semantic, historical, limitation, and presentation field.
5. Stop on additions, removals, renames, or flows that need architectural judgment.
6. Validate, regenerate, hash, and expose the complete resulting diff for the same-batch review.

This would remove routine synchronization work while keeping the TOML a reviewed architectural
authority and preserving an honest distinction between code-derived facts and architectural
decisions.
