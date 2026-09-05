# V2 Static API Documentation

The API documentation utility generates a curated HTML reference and machine-readable indexes from
`src/markeitech` without importing or running Markeitech. It is documentation infrastructure
only: it does not define runtime behavior, public compatibility guarantees, or accepted
architecture.

## Authority And Scope

- `tools/api-docs/schema/public-surface.toml` is the versioned documentation denominator. Version 5
  selects the literal `__all__` exports from `markeitech.system`, `markeitech.acquisition`, and
  `markeitech.intelligence`, plus the explicit operator entry point.
- `tools/api-docs/schema/attribute-registry.toml` is the only authority for typed custom docstring
  attributes. Version 2 admits only the approved `architecture.component.*` identity, label,
  kind, boundary, and substantive responsibility fields.
- `metadata-index.json` is non-authoritative discovery output. API visibility and author-declared
  metadata do not prove runtime calls, ownership, completeness, or architecture membership.
- `tools/system-diagram/docs/system-dataflow.toml` is not a generator input. Its currently reviewed,
  implementation-referenced component facts were used once to seed V2 class docstrings. Source
  documentation is the upstream declaration surface for future generated TOML and diagrams.
- Retired implementations, tests, private helpers, and third-party Nautilus APIs are outside the
  selected surface.

## Locked Toolchain

The direct dependencies are locked exactly in the isolated `tools/api-docs` project:

| Dependency | Version | License | Purpose |
|---|---:|---|---|
| MkDocs | 1.6.1 | BSD-2-Clause | Strict static-site rendering |
| mkdocs-material | 9.6.5 | MIT | Material theme and Material-style components |
| mkdocstrings-python | 2.0.5 | ISC | Python API rendering and Google docstring support |
| Griffe | 2.2.0 | ISC | Static Python source extraction and the custom extension API |

`uv.lock` records the full transitive closure. These dependencies belong only to documentation;
they must not be added to the V2 runtime project. Dependency updates require a separately reviewed
version, license, configuration, security-boundary, and reproducibility check.

## Provision And Run

From the repository root:

```shell
uv sync --project tools/api-docs --locked
PYTHONPATH="$PWD/src" tools/api-docs/.venv/bin/python -P -m markeitech docs validate
PYTHONPATH="$PWD/src" tools/api-docs/.venv/bin/python -P -m markeitech docs check
PYTHONPATH="$PWD/src" tools/api-docs/.venv/bin/python -P -m markeitech docs generate
```

This dependency-minimal form runs the unified Python CLI through the already-provisioned docs
interpreter and does not require or synchronize the root runtime environment. A developer who has
already run the root `uv sync --locked --dev` may use the shorter equivalent
`.venv/bin/markeitech docs ...` form. Do not use `uv run` for either path: synchronization and
package-index access must remain explicit provisioning operations that happen before the CLI.

Do not invoke bare `mkdocs` or `mkdocstrings`. The wrapper fixes all paths, validates the complete
installed distribution closure against `uv.lock` and enforces configuration allowlists, blocks
imports/network/subprocesses while analyzing and
rendering, verifies that inputs did not change, scans for protected data, writes indexes and hashes,
and promotes only a complete artifact set.

The root CLI dispatches each operation to the exact `tools/api-docs/.venv/bin/python` interpreter
with absolute source binding, safe-path mode, UTC timezone, deterministic hash seed, unbuffered
output, bytecode-disabled execution, and a fixed locale. The child receives only those controls and
the executable `PATH`; caller secrets, runtime configuration, Python startup controls, proxies,
and cloud or publication credentials are not inherited. The CLI validates that the imported tool
CLI resolves to this tool's source tree before execution. It never provisions the tool. A missing
or invalid environment fails non-zero and reports `uv sync --project tools/api-docs --locked` as
the remediation.

Before entering that constrained analysis/rendering environment, the wrapper runs bounded,
read-only `git rev-parse` and scoped `git status` queries to bind the artifact to a commit and dirty
input state. Those identity queries are the only intended child processes.

The committed content identity hashes sorted repository-relative input paths, sizes, and SHA-256
values, so an identical checkout produces identical identity on different machines. The generated
artifact index records the supported Python `3.13` series and exact locked documentation-package
versions. The actual Python patch version remains truthful execution provenance in command and CI
results; it is not part of deterministic committed site bytes.

Generated output is written to `docs/api` and committed as a reviewable tracked artifact after
regeneration. `tools/api-docs/.build` remains disposable and ignored. The legacy `tools/api-docs/site`
ignore rule remains temporarily so a stale local projection cannot enter a commit; the generator no
longer writes it.

MkDocs Material emits whitespace-only lines in generated HTML navigation blocks. The repository
`.gitattributes` disables only Git's trailing-space diagnostic for generator-owned `docs/api` HTML;
hand-edited Markdown, Python, configuration, and every other changed artifact remain covered by
`git diff --check`. Never hand-edit generated HTML to normalize template whitespace.

Architecture-component declarations are rendered separately from the curated public API
denominator. The generator discovers them through the closed custom-attribute registry and
validates their approved identity fields. Relationship, contract, ownership, status, evidence, and
limitation attributes are deferred. Static declarations do not prove runtime calls or delivery.
The current class-component census contains 20 declarations. Seven carry substantive
responsibilities; the other 13 are displayed as incomplete rather than inheriting generic TOML
placeholders.

The site uses one tracked local stylesheet for an always-dark, full-width layout. Wide tables and
signatures must wrap or scroll within their own containers without widening or clipping the page.
Custom JavaScript, template overrides, remote assets, CSS imports, and CSS-loaded assets are not
approved.

Run the focused offline test suite with:

```shell
PYTHONPATH="$PWD/src" tools/api-docs/.venv/bin/python -P -m markeitech docs test
```

CI then verifies that this test command did not alter the committed artifact with scoped
`git diff` and untracked-file checks before upload. That post-test cleanliness gate is deliberately
kept visible in the workflow; `docs test` does not hide source-control policy inside the test
runner.

## Docstring Contract

Use Google-style docstrings on intentionally public objects. Python annotations are the type
authority. Docstrings should add the semantic facts a signature cannot carry: meaning, units,
lineage, time basis, side effects, failure or abstention behavior, and meaningful `Raises` cases.
Do not bulk-fill private callbacks or invent descriptions merely to improve coverage.

Custom attributes use one exact section and either a scalar or list shape:

```text
Summary in normal Google style.

Markeitech Metadata:
    approved.namespace.scalar: one bounded value
    approved.namespace.list:
        - first bounded value
        - second bounded value
```

The names above demonstrate grammar only. The exact production fields are those present in the
versioned registry. A field is valid only after it is registered with an exact name, value type,
cardinality, maximum items, optional value pattern, and exposure policy. The parser strips the raw
custom section, then renders only validated fields whose registry exposure is `public` in a
dedicated **Markeitech Metadata** panel. Scalar values render as text and list values as lists.
When the approved `architecture.component.responsibilities` field is present, the generator also
copies its validated public list into the generated class description. This is an in-memory
documentation projection; the generator does not rewrite the source docstring.

Unknown, invalid, hidden, and conflicting values are quarantined. Generated artifacts may describe
their sanitized status and identity, but must not contain their raw values. Public fields may emit a
typed value only when the registry explicitly allows public exposure.

## Future Attribute Changes

Before adding a production field:

1. obtain Markeitect approval for its exact meaning and downstream use;
2. choose a specific namespace and define type, cardinality, bounds, validation, and exposure;
3. bump the attribute registry version;
4. add parser, static-extension, rendering, invalid/unknown, conflict, and leak tests; and
5. state whether the field is merely author-declared discovery evidence or is reconciled against a
   separately accepted authority.

Do not infer a caller/callee or architecture-flow schema from earlier examples. Relationship
attributes remain deferred until a structured, single-direction declaration and reference
reconciliation contract is separately accepted.

## Public-Surface Changes

An intentional package export change will fail validation until the denominator is reviewed. Check
the changed literal `__all__`, decide whether it belongs in the public reference, then update the
expected ordered-export count and SHA-256 and bump the public-surface registry version in the same
batch. Do not bypass the drift gate or silently drop an exported object.

The generated index reports selected, documented, and missing-docstring counts separately. Missing
docstrings are honest debt, not generator failure. Add documentation incrementally with the code
owner's semantic review.

## Failure Interpretation

- `PUBLIC_SURFACE_DRIFT` means an export denominator changed and needs an explicit decision.
- `TARGET_IMPORT_*`, `DYNAMIC_ANALYSIS_DENIED`, `NETWORK_DENIED`, or `SUBPROCESS_DENIED` means the
  offline/static boundary was violated.
- `SOURCE_CHANGED` means an input changed during the run; rerun from a stable worktree.
- `OUTPUT_LEAK_DETECTED` means protected custom metadata, a repository path, or secret-like content
  reached staged output. Treat it as a failed build and inspect source without publishing artifacts.
- `OUTPUT_PUBLICATION_FAILED` means promotion failed and the prior complete site was retained.
- `OUTPUT_DRIFT` means the committed `docs/api` set does not byte-match a fresh constrained build.
  Regenerate through a scoped review batch; do not bypass or partially ignore the comparison.

GitHub Pages requires one-time maintainer setup under **Settings → Pages → Build and deployment →
Source: GitHub Actions**. Pull requests verify and upload a review artifact but never deploy. A
verified `master` push or manual dispatch deploys the exact committed `docs/api` directory. The
workflow checks again after its tests so a test cannot silently replace the reviewed artifact.

Passing this workflow proves only the bounded static documentation build. It does not prove live
provider behavior, connected services, persistence, performance, trading behavior, or complete API
documentation.
