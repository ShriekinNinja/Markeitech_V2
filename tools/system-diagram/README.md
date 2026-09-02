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
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/system-diagram/src \
  tools/system-diagram/.venv/bin/python -m markeitech_system_diagram \
  generate --manifest docs/architecture/system-dataflow.toml \
  --output docs/architecture/generated/system-dataflow --check-drift
```

Run the tests:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/system-diagram/src \
  tools/system-diagram/.venv/bin/python -m unittest discover \
  -s tools/system-diagram/tests -v
```

The canonical manifest and maintenance contract are documented under `docs/architecture/`.
Generated files are review artifacts only and must never be edited manually.
