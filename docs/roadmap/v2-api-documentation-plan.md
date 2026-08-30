# V2 API Documentation Plan

Status: accepted and implemented for local review on branch `v2-api-documentation`.

## Recommendation

Use **MkDocs + `mkdocstrings[python]` (Griffe)** with **Google-style docstrings**.
Keep the generator in a separately locked `tools/api-docs` environment. A first-party wrapper owns
fixed paths, strict configuration, source snapshots, leak checks, deterministic rendering, and
atomic publication. Never import or run Markeitech while building documentation, and do not expose
a bare MkDocs command as the authoritative workflow. Track sources, configuration, registries,
tests, and the lockfile; keep generated HTML untracked unless hosting is approved later.

Use a small static Griffe extension to strip and parse namespaced custom docstring attributes into
each object's `extra["markeitech"]` metadata and emit a sanitized machine-readable index alongside
the HTML. Raw unknown, invalid, hidden, and conflicting values remain quarantined. Attribute names
and schemas are separately approved, versioned, reviewable, and extensible.

Why: Markeitech already uses Markdown, V2 has a clear `src` layout and explicit `__all__` exports,
and Griffe can extract source statically. Current docstrings are sparse, so a curated public API is
more useful than dumping every actor callback and private helper.

## Toolchain Options

| Option | Pros | Cons |
|---|---|---|
| **MkDocs + mkdocstrings/Griffe** — recommended | Markdown-native; static extraction; custom extensions can attach namespaced metadata and render custom templates | Adds extension code and requires explicit metadata schemas, tests, navigation, and public-member policy |
| **Sphinx + autodoc + autosummary + Napoleon** | Mature ecosystem; built-in custom Napoleon sections; strong cross-references and multiple outputs | `autodoc` imports modules, which is fragile and unsafe for runtime/provider boundaries; more configuration and reStructuredText concepts |
| **pdoc** | Smallest setup; fast module-tree documentation | Imports modules; less control over a mixed narrative/API site and strict public-surface governance |

Optional presentation: start with MkDocs' built-in theme for fewer dependencies; add Material only
if search, navigation, or branding justifies another dependency.

## Docstring Style Options

| Style | Pros | Cons |
|---|---|---|
| **Google** — recommended | Concise and readable in Python; supported by mkdocstrings and Sphinx Napoleon | Less table-oriented for large scientific parameter sets |
| **NumPy** | Familiar for numerical/scientific APIs; strong structured sections | Verbose for Markeitech's many small typed contracts |
| **Sphinx/reStructuredText** | Direct, mature Sphinx integration and precise roles | Markup-heavy in source; weakest fit with the repository's Markdown-first documentation |

Use annotations as the type authority. Docstrings should explain meaning, units, lineage,
side effects, failure/abstention behavior, and `Raises`; they should not repeat obvious types.

## Custom Attribute Requirement

- Support arbitrary **namespaced key/value or list attributes** without changing the base
  docstring style or generator.
- Preserve the declaring object, source location, raw value, schema/version identity, and parser
  outcome during parsing, but do not publish a raw value unless an approved field explicitly permits
  public exposure. The deterministic artifact index carries only sanitized identities and status.
- Validate only attributes whose schemas have been approved; represent unknown attributes as
  unknown without publishing their keys or values, guessing meaning, or turning them into
  architecture facts.
- Allow a future component to gather relationship hints. For example, attributes conceptually
  resembling “who calls this” or “what this calls” may later contribute architecture-flow evidence,
  but these examples do **not** establish field names, semantics, ownership, or a design demand.
- Treat docstring metadata as author-declared discovery evidence. It must be reconciled with source,
  tests, runtime evidence, and the canonical system/data-flow manifest before any authoritative
  architecture claim.

## Suggested Implementation

1. Define scope: `v2/src/markeitech` only. Seed the public surface from package `__all__` exports,
   then explicitly add operator entry points and stable subsystem contracts. Exclude V1, tests,
   private members, and undocumented third-party Nautilus APIs.
2. Add the isolated docs tool, lockfile, first-party wrapper, MkDocs configuration, static custom-
   attribute extension, machine-readable metadata/artifact indexes, and curated pages for `system`,
   `acquisition`, `intelligence`, and the operator CLI.
3. Add Google docstrings incrementally, starting with exported contracts and configuration/load
   entry points; do not bulk-document private helpers or lifecycle overrides.
4. Add offline verification: `mkdocs build --strict`, broken-reference checking, deterministic
   metadata fixtures, invalid/unknown-attribute cases, and Ruff's `pydocstyle` Google convention
   only after the selected public surface is documented. Consider Griffe API-diff checks later if
   compatibility becomes a release contract.
5. Accept the infrastructure when a stable checkout builds without target imports, dynamic
   inspection, network, or connected IB, PostgreSQL, or Discord access; source analysis and
   rendering launch no child processes beyond the wrapper's bounded read-only Git identity
   preflight; denominator drift and missing docstrings are reported honestly; generated HTML is
   reproducible, atomically published, scanned, and untracked. Complete descriptive coverage
   remains incremental documentation debt.

## Implemented Boundary

- Public denominator: the literal `__all__` of `system`, `acquisition`, and `intelligence`, plus
  `markeitech.system.cli.main`; 258 selected objects in registry version 1.
- Current coverage: 16 selected objects have source docstrings and 242 are reported missing. The
  generator does not invent descriptions.
- Custom metadata: the parser and registry support bounded scalar/list fields, cardinality,
  validation patterns, and public/status-only exposure. Registry version 1 intentionally approves
  no production field semantics.
- Outputs: a static site, sanitized metadata index, artifact index, and SHA-256 manifest. Generated
  output is ignored and non-authoritative.
- Architecture boundary: no caller/callee, ownership, or flow field is currently approved. Future
  relationship fields remain discovery evidence and cannot mutate or replace the canonical
  system/data-flow manifest.

## References

- [mkdocstrings Python usage](https://mkdocstrings.github.io/python/usage/)
- [Griffe static versus dynamic loading](https://mkdocstrings.github.io/griffe/guide/users/loading/)
- [Griffe extensions and namespaced extra metadata](https://mkdocstrings.github.io/griffe/guide/users/extending/)
- [Sphinx Napoleon custom sections](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html#confval-napoleon_custom_sections)
- [Sphinx autodoc](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html)
- [pdoc API documentation](https://pdoc.dev/docs/pdoc.html)
- [Ruff docstring conventions](https://docs.astral.sh/ruff/faq/#how-does-ruffs-linter-compare-to-pydocstyle)
