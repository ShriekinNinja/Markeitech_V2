# Freshness And Evidence

Use this protocol on every invocation to keep nightly documentation, the installed package, current code, and provider behavior distinct.

## Refresh Upstream

Open these exact roots during the task:

- `https://nautilustrader.io/docs/nightly/`
- `https://nautechsystems.github.io/nautilus_docs/python-api-nightly/`

Record access date, channel, displayed version or build, redirects, and nightly warnings. Read relevant guide pages for semantics and exact API pages for public contracts. Do not silently substitute stable or `latest` pages.

Begin with broad subsystem navigation before exact-symbol search. Likely guide families include architecture, Python, actors, message bus, cache, data, indicators, custom data, persistence, catalogs, live nodes, adapters, and Interactive Brokers. Treat these as search families, not permanent URLs or a complete catalog.

## Establish The Executable Contract

Inspect without modifying:

- `v2/pyproject.toml` and `v2/uv.lock`;
- installed distribution version and module path;
- public package exports and `.pyi` stubs;
- exact imports, constructors, fields, methods, callbacks, and enums;
- relevant Markeitech actors, composition, configuration, and tests;
- accepted runtime evidence when provider behavior matters;
- release notes and migration guidance when version drift is plausible.

Use the locked project environment for import or introspection probes. Compiled symbols may require stubs, API pages, focused construction probes, or existing tests. Do not update dependencies or run connected services merely to investigate.

## Evidence Classes

Label consequential claims as:

- **Local verified:** installed package, source, stub, or focused test.
- **Local measured:** accepted runtime, provider, persistence, or performance observation with scope.
- **Nightly documented:** refreshed nightly guide semantics.
- **Nightly API:** refreshed nightly public API contract.
- **Provider documented:** adapter or provider statement not yet measured locally.
- **Inference:** reasoned conclusion from named evidence.
- **Proposal:** unimplemented target.
- **Unknown:** missing or conflicting evidence.

A successful import is not provider acceptance. A core type is not adapter delivery. A passing unit test is not live-session, persistence, performance, or trading validation.

## Resolve Version Drift

When nightly differs from the installed version, separate:

- **Current-pin design:** only locally verified contracts.
- **Upgrade-target design:** named nightly behavior plus migration, regression, adapter, and connected-acceptance work.

Executable local evidence governs current behavior. Preserve documentation mismatches as findings. Never recommend an upgrade merely because a newer API is convenient.

## Freshness Statement

For substantive answers, state:

- sources refreshed and access date;
- installed NautilusTrader version examined;
- whether the answer targets the current pin, nightly, or both;
- unavailable or version-mismatched sources;
- connected behavior that remains unverified.

Cite specific upstream pages beside time-sensitive claims and local files or tests beside checkout claims.
