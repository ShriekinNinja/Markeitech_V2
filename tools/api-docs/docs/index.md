# Markeitech V2 API

This site documents the curated Python API under `v2/src/markeitech` from static source analysis.
Generation does not import or run Markeitech. The site and its metadata index are regenerable,
non-authoritative documentation projections; they are not runtime configuration, runtime evidence,
or the canonical architecture representation.

The current public-surface denominator is defined by
`tools/api-docs/schema/public-surface.toml`. Missing docstrings are reported honestly in the
generated metadata index and do not become inferred documentation.

Custom machine-readable docstring attributes are accepted only through the versioned registry at
`tools/api-docs/schema/attribute-registry.toml`. Unknown or invalid attributes are quarantined and
their values are never copied into generated artifacts.

The Architecture Components page is generated from validated custom attributes in V2 class
docstrings. It is a source-documentation view, not a Python call graph or proof that a runtime flow
executed.
