# Reference Set Enrichment

The assisted reference-set workflow keeps human trading judgment separate from
derived system evidence. Markeitect supplies the setup interpretation;
Markeitech fills identity, persisted context, nearby lifecycle evidence, and
forward price response without rewriting the human label.

The workspace is intentionally ignored by Git:

```text
data/research/reference-set/
  markeitect-reference-set.csv
  screenshots/
  output/
```

## Add A Screenshot

Use this filename contract:

```text
YYYY-MM-DDTHH-MMZ_INSTRUMENT_1m|5m_long|short_setup-name.png
```

Example:

```text
2026-07-16T22-50Z_NQ_1m_short_resistance-poc-val-rejection.png
```

The timestamp is UTC and represents when the annotated decision became
available. On a one-minute chart, a decision requiring the completed `22:50`
candle normally becomes available at `22:51`. Do not use the candle's opening
label when its close, wick, or volume is part of the evidence. The same rule
applies to a five-minute chart: evidence from the candle labeled `22:50`
normally becomes available at `22:55`.

Use `1m` for execution-sensitive examples and `5m` for clearer intraday and
0DTE decision structure. They are separate evidence classes and will not be
pooled blindly during calibration. Forward outcomes still use canonical,
complete one-minute bars so both classes have comparable path measurements.

The instrument alias must resolve unambiguously through the supplied runtime
configuration. The current `NQ` alias resolves to `NQU6.CME`; exact contract
identity is retained in the CSV and enriched dataset.

## Create Draft Rows

```bash
uv run markeitech-reference-set \
  config/market-data.live.toml \
  data/research/reference-set \
  --sync-only
```

The sync command derives and preserves:

- stable annotation identity and version
- instrument alias and exact configured instrument ID
- observed and initial Candidate timestamp
- direction and setup-family slug
- chart timeframe (`1m` or `5m`)
- relative screenshot path and content hash

Existing human-authored cells are preserved. A screenshot changed in place,
missing declared image, duplicate path, malformed header, unknown alias, unsafe
path, or invalid filename fails visibly. Create a new file for revised visual
evidence instead of overwriting an existing screenshot.

## Human Fields

A draft becomes complete after Markeitect supplies five fields:

- `expected_lifecycle`: `ignore`, `warn`, `candidate`, `armed`, or `triggered`
- `qualification_reason`
- `invalidation_condition`
- `target_1`
- `annotated_by`

Candidate, Armed, and Triggered timestamps may be added independently. Each
unique timestamp receives its own forward price-response path. Zone bounds,
semantic level, timeframe, confirmation modalities, second target, and notes
are optional but improve defensible matching.

`chart_timeframe` describes the screenshot and is inferred from its filename.
`level_timeframe` describes the source of the traded level. Optional
`trigger_timeframe` records the timeframe that supplied confirmation. These
may differ; for example, a 5m chart can reject a 15m resistance and trigger on
1m confirmation.

## Enrich The Set

```bash
uv run markeitech-reference-set \
  config/market-data.live.toml \
  data/research/reference-set
```

This writes:

- `output/enriched-reference-set.jsonl`
- `output/reference-set-report.md`

Enrichment is read-only. It uses complete reported IB one-minute bars and the
same session-aware forward response rules as the Signal Outcome Audit. Context
features must be committed in both Parquet and SQLite and must have
`as_of <= annotation timestamp`; later features are never substituted.

The latest committed feature per timeframe is labeled matched, stale,
ambiguous, or unavailable. Same-time revisions remain ambiguous. Nearby signal
transitions are filtered by instrument and direction. A signal is called a
matched candidate only when the human annotation supplies zone bounds and
exactly one nearby lifecycle overlaps that zone. Otherwise candidate identities
remain unmatched, unresolved, or ambiguous.

Current persistence cannot prove every rejected pre-Candidate evaluation.
Therefore no nearby durable signal means `not observed before durable
lifecycle`, not automatically `Direction rejected` or `Location rejected`.

## First Screenshot

The initial July 16 NQ example has complete reported-bar outcomes. Persisted
intraday context is stale because the feature runtime was not operating near
the annotation, and no durable signal transition exists in its nearby window.
Those are evidence findings, not import failures. Completing the five human
fields will turn it into a usable missed-setup reference while retaining those
limitations.
