# Markeitech system-diagram tool

This directory is the standalone, offline development/documentation boundary for the
TOML-driven Markeitech architecture diagrams.

It contains immutable typed models, strict TOML loading and semantic validation, a bounded static
source/configuration drift census, deterministic Diagrams-to-DOT translation, controlled Graphviz
rendering, atomic complete-set publication, and focused tests. It imports no Markeitech or
Nautilus runtime module and has no service, credential, `.env`, operational-data, or network path.

Provision the exact locked documentation environment once:

```text
uv sync --project tools/system-diagram --locked
```

Generate the canonical six-view documentation set from the repository root:

```text
uv run markeitech diagrams generate
```

Run the tests:

```text
uv run markeitech diagrams test
```

`uv run markeitech diagrams check` validates the manifest and source/configuration drift without
modifying output. The root CLI uses this project's exact interpreter and deterministic environment;
it does not merge diagram dependencies into the runtime environment or provision them.

The canonical manifest and maintenance contract are documented under `docs/architecture/`.
Generated files are review artifacts only and must never be edited manually.
