# V2 Static API Documentation

The API documentation utility generates a curated HTML reference and machine-readable indexes from
`v2/src/markeitech` without importing or running Markeitech. It is documentation infrastructure
only: it does not define runtime behavior, public compatibility guarantees, or accepted
architecture.

## Authority And Scope

- `tools/api-docs/schema/public-surface.toml` is the versioned documentation denominator. Version 1
  selects the literal `__all__` exports from `markeitech.system`, `markeitech.acquisition`, and
  `markeitech.intelligence`, plus the explicit operator entry point.
- `tools/api-docs/schema/attribute-registry.toml` is the only authority for typed custom docstring
  attributes. Version 2 admits only the approved `architecture.component.*` identity, label,
  kind, boundary, and substantive responsibility fields.
- `metadata-index.json` is non-authoritative discovery output. API visibility and author-declared
  metadata do not prove runtime calls, ownership, completeness, or architecture membership.
- `docs/architecture/system-dataflow.toml` is not a generator input. Its currently reviewed,
  implementation-referenced component facts were used once to seed V2 class docstrings. Source
  documentation is the upstream declaration surface for future generated TOML and diagrams.
- V1, tests, private helpers, and third-party Nautilus APIs are outside the selected surface.

## Locked Toolchain

The direct dependencies are locked exactly in the isolated `tools/api-docs` project:

| Dependency | Version | License | Purpose |
|---|---:|---|---|
| MkDocs | 1.6.1 | BSD-2-Clause | Strict static-site rendering with the built-in theme |
| mkdocstrings-python | 2.0.5 | ISC | Python API rendering and Google docstring support |
| Griffe | 2.2.0 | ISC | Static Python source extraction and the custom extension API |

`uv.lock` records the full transitive closure. These dependencies belong only to documentation;
they must not be added to the V2 runtime project. Dependency updates require a separately reviewed
version, license, configuration, security-boundary, and reproducibility check.

## Provision And Run

From the repository root:

```shell
uv sync --project tools/api-docs --locked
env PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  PYTHONPATH=tools/api-docs/src TZ=UTC \
  tools/api-docs/.venv/bin/python -m markeitech_api_docs validate
env PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  PYTHONPATH=tools/api-docs/src TZ=UTC \
  tools/api-docs/.venv/bin/python -m markeitech_api_docs generate
```

Do not invoke bare `mkdocs` or `mkdocstrings`. The wrapper fixes all paths, validates the complete
installed distribution closure against `uv.lock` and enforces configuration allowlists, blocks
imports/network/subprocesses while analyzing and
rendering, verifies that inputs did not change, scans for protected data, writes indexes and hashes,
and promotes only a complete artifact set.

Before entering that constrained analysis/rendering environment, the wrapper runs bounded,
read-only `git rev-parse` and scoped `git status` queries to bind the artifact to a commit and dirty
input state. Those identity queries are the only intended child processes.

Generated output is written to `tools/api-docs/site`. Both `site` and `.build` are ignored and must
not be committed or edited manually.

Architecture-component declarations are rendered separately from the curated public API
denominator. The generator discovers them through the closed custom-attribute registry and
validates their approved identity fields. Relationship, contract, ownership, status, evidence, and
limitation attributes are deferred. Static declarations do not prove runtime calls or delivery.
The current class-component census contains 19 declarations. Six carry substantive
responsibilities; the other 13 are displayed as incomplete rather than inheriting generic TOML
placeholders.

The site uses one tracked local stylesheet for an always-dark, full-width layout. Wide tables and
signatures must wrap or scroll within their own containers without widening or clipping the page.
Custom JavaScript, template overrides, remote assets, CSS imports, and CSS-loaded assets are not
approved.

Run the focused offline test suite with:

```shell
env PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  PYTHONPATH=tools/api-docs/src TZ=UTC \
  tools/api-docs/.venv/bin/python -m unittest discover -s tools/api-docs/tests -v
```

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
cardinality, maximum items, optional value pattern, and exposure policy. The parser strips the
entire custom section before rendering.

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

Passing this workflow proves only the bounded static documentation build. It does not prove live
provider behavior, connected services, persistence, performance, trading behavior, or complete API
documentation.
