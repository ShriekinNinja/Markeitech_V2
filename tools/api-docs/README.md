# Markeitech V2 API Documentation Tool

This isolated tool statically generates the curated V2 Python API reference. It must not import or
run Markeitech and must be invoked through the first-party wrapper, never bare MkDocs.

The complete operating contract, commands, custom-attribute grammar, update procedure, dependency
licenses, and failure meanings are documented in
[`docs/operations/v2-api-documentation.md`](../../docs/operations/v2-api-documentation.md).

Key inputs are:

- `schema/public-surface.toml` — versioned public denominator and drift gate;
- `schema/attribute-registry.toml` — approved typed custom fields;
- `mkdocs.yml` — strict, offline, static rendering policy;
- `uv.lock` — exact isolated dependency closure; and
- `tests` — import, network, subprocess, metadata, drift, leakage, determinism, and publication
  safety evidence.

`site` and `.build` are disposable, ignored projections. They are not source or architecture
authority.
