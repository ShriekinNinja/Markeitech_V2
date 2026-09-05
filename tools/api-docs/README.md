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

`docs/api` is the tracked, reviewable build artifact and must be regenerated in a safe batch before
commit. `tools/api-docs/.build` is disposable and ignored. The generator stages a complete set under
`.build` and publishes only the validated result to `docs/api`. Its committed input identity uses
repository-relative paths and the supported Python series; the actual interpreter patch remains
execution provenance in command and CI output.
