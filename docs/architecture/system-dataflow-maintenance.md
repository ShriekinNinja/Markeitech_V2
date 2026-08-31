# System And Data-Flow Manifest Maintenance

During the source-documentation migration interval, the existing system-diagram tool continues to
consume [`system-dataflow.toml`](system-dataflow.toml). It is an offline documentation manifest,
not runtime configuration. The API-documentation tool does not read it: the manifest was used once
to seed the approved class-owned component fields into exact implementation-referenced docstrings.
A future source-to-TOML exporter requires separate review and acceptance before this maintenance
path can be superseded. Generated SVG, PNG, DOT, Markdown, index, and hash files under
[`generated/system-dataflow/`](generated/system-dataflow/) are derived review artifacts. Never
edit a generated file manually or use it as evidence that runtime behavior exists.

## Mandatory Same-Batch Rule

A development batch must update the source docstring first when it changes an
implementation-backed component's approved identity, label, kind, boundary, or substantive local
responsibilities. Until the future exporter is accepted, mirror that reviewed change into the TOML
in the same batch so the existing renderer stays aligned. For all other manifest fields and record
families, a development batch must update the TOML in the same reviewed diff whenever it adds,
changes, renames, enables, disables, replaces, or removes any of the following:

- a component, responsibility, canonical authority, composition rule, lifecycle, cardinality, or
  failure-isolation boundary;
- a configuration condition or named-profile enablement state;
- a contract, type, topic, signal, endpoint, request/response leg, callback, timer, queue, worker,
  transport, delivery claim, or data flow;
- provider request/subscription ownership, persistence, external projection, process/thread/queue
  boundary, or visual grouping;
- current, conditional, disabled, external, removed, rejected, unknown, or future status.

Classify the architectural impact before implementation. Reconcile previously undocumented facts
in the same batch that discovers them; do not use the manifest update to legitimize accidental
architecture. Runtime/code truth remains the implementation and composition in the checkout. The
manifest is the reviewed representation used by the renderer. Generated artifacts are projections.
Git history and accepted records preserve historical truth.

## Stable IDs, Renames, And Removal

- Preserve an ID when only a label, class, file, or configuration path is renamed and its meaning
  and authority remain the same.
- Allocate a new ID when responsibility, canonical ownership, or contract meaning changes. Link
  the old identity through a tombstone or replacement record.
- A removed or rejected identity becomes a tombstone with the full removal commit and evidence. It
  must not remain connected in a current-runtime view.
- A future identity becomes current only after the implementation and current-status evidence
  exist. Planned or rendered existence is never runtime existence.
- Unknown facts stay explicit. Do not fill provider, adapter, delivery, persistence, or lifecycle
  gaps with plausible defaults.

## Required Local Procedure

Provision the separate documentation environment once, independently of runtime setup:

```bash
uv sync --project tools/system-diagram --locked
```

Graphviz `dot` must be installed in an approved macOS location. The accepted implementation was
verified with Diagrams `0.25.1`, Python Graphviz `0.20.3`, Python `3.13.3`, and Graphviz `15.1.1`.
Generation itself is offline and never downloads dependencies.

After every sensitive change:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/system-diagram/src \
  tools/system-diagram/.venv/bin/python -m markeitech_system_diagram \
  validate --manifest docs/architecture/system-dataflow.toml --check-drift

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/system-diagram/src \
  tools/system-diagram/.venv/bin/python -m markeitech_system_diagram \
  generate --manifest docs/architecture/system-dataflow.toml \
  --output docs/architecture/generated/system-dataflow --check-drift

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/system-diagram/src \
  tools/system-diagram/.venv/bin/python -m unittest discover \
  -s tools/system-diagram/tests -v
```

The shared PyCharm configuration **Generate Sys Diagram** runs the same validation, source/config
drift census, and atomic complete-set generation from the repository root. It uses only the
separate locked interpreter and an explicit clean environment. It does not read `.env`, start the
runtime, contact IB, Discord, PostgreSQL, Docker, or the network, or inspect operational data.

## Review And Staged-Diff Expectations

The reviewed diff must contain, as applicable:

1. implementation/configuration changes;
2. the migration-interval TOML projection update, including evidence and limitations;
3. regenerated SVG, PNG, DOT, Markdown, `artifact-index.json`, and `SHA256SUMS`;
4. validator/generator tests when the schema, census, or presentation contract changes;
5. the smallest current-status, architecture, operation, or roadmap update needed to keep a fresh
   checkout accurate.

The generator publishes the full output directory atomically. A partial set, invalid manifest,
source/config drift, missing Graphviz, unsafe output, failed render, or exceeded view budget exits
non-zero and leaves the previous complete set in place. Review `git diff --check`, the manifest and
Markdown companions, every SVG at normal zoom and 200%/400%, every PNG at normal scale, and the
DOT/index/hash changes. Future, disabled, external, and current states must remain distinguishable
without relying on color alone. No current view may admit disabled, removed, rejected, or future
behavior.

The generated DOT, SVG, and PNG views use the manifest-selected opaque dark theme. Markdown
companions follow the reviewer's viewer theme and must not embed CSS or become a second visual
authority. Any palette change must retain explicit status text and shape/line-style redundancy,
pass the declared text and graphical contrast tests, regenerate all artifacts, and receive renewed
visual review.

Graphical component cards, relationships, and nested system boundaries use the installed
Diagrams C4 primitives plus escaped Graphviz-native labels. Manifest text is always treated as
plain content, never executable HTML. The canonical views intentionally use no external icon or
font assets, so SVGs remain standalone and generation remains offline and repository-portable.

The current source census mechanically checks the actor-registration roster and IDs, literal
signal/custom-data identities in its closed source allowlist, named-profile schema/hash and
supported Boolean enablement conditions, implementation symbols, LiveNode construction shape, and
evidence-file existence. Reviewers still own semantics the census cannot prove: responsibility,
authority, completeness, correct edge meaning, undocumented code paths, provider/account truth,
runtime ordering and delivery, PostgreSQL internals, and visual comprehension.

## Exceptions, Rebase, Rollback, And Ownership

Markeitect is the semantic owner and final reviewer. A drift exception must be a scoped manifest
record with a stable ID, exact affected paths/IDs, reason, Markeitect approval reference,
expiry/removal condition, and evidence. Free-form skip flags, commit-message exemptions, and
permanent blanket exclusions are forbidden.

After a rebase or merge, rerun validation and generation because the checkout evidence, source
census, configuration hash, or layouts may have changed. Resolve semantic conflicts in the TOML;
never choose generated-file conflict markers or accept an image-only resolution.

Rollback the generator, canonical manifest, and complete generated directory together to the last
reviewed batch. Removing the utility does not change runtime behavior because nothing in this
system is imported, composed, or consulted by the live runtime.

## Dependencies, Assets, And Licenses

The documentation tool is deliberately separate from `v2`. Diagrams is MIT-licensed; Graphviz is
EPL-2.0. Their exact Python dependency closure is recorded in `tools/system-diagram/uv.lock` and the
native Graphviz identity is recorded in each generated artifact index. Version or Graphviz/font
changes require regeneration and renewed visual review. The initial design is shape-only and uses
no provider logo, custom icon, remote font, or external asset. Any later asset requires a tracked
source, integrity hash, license/attribution decision, accessible text label, and separate review.
