# Signal Outcome Audit

The Signal Outcome Audit is an offline, read-only research command. It measures
what happened after persisted Armed and Triggered transitions without replaying
signal logic, changing lifecycle truth, or mutating live storage.

## Run It

Stop the live process or use a stable copy of its persistence files before a
formal research run. The SQLite connection itself is opened with `mode=ro` and
`query_only`; Parquet inputs are read without a writer.

```bash
uv run markeitech-signal-audit config/market-data.live.toml \
  --start 2026-07-17T14:52:10Z \
  --end 2026-07-17T19:42:00Z \
  --output data/research/signal-outcomes/2026-07-17-primary-run
```

`--start` is inclusive and `--end` is exclusive. Both must be UTC ISO-8601
timestamps. The default output path is grouped by the start date under
`data/research/signal-outcomes/`; research output is intentionally ignored by
Git.

The command writes:

- `signal-outcomes.jsonl`: versioned, deterministic machine-readable records
- `signal-outcomes.md`: a concise human-readable session report

## Evidence Boundary

Each record is anchored to a verified SQLite transition history and retains the
exact transition snapshot, reason codes, locations, evidence references,
algorithm version, and configuration hash. Every market-context feature ID must
exist in both the feature catalog and SQLite commit metadata. A missing feature,
broken lifecycle chain, duplicate transition, or conflicting reported-bar
revision fails the audit visibly.

Only complete `source=ib` one-minute bars are used for outcomes. Inferred bars
from classified ticks are not mixed into this dataset. The reference price is
the latest completed reported bar close at or before the lifecycle event, never
a later bar. The reference timestamp and source method are retained alongside
the price.

Forward horizons represent valid configured market minutes within the event's
product session. Weekends, holidays, maintenance gaps, and closed minutes are
not counted. A horizon never crosses into another session. Missing bars, a
session ending before the horizon, and an event outside its configured session
produce explicit unavailable outcomes rather than filled prices.

## Interpretation

Armed and Triggered records are separate populations. Outcome calculations do
not relabel either lifecycle state.

- Directional return is positive when price moved with the signal direction.
- MFE is the largest direction-adjusted favorable excursion from the event
  reference price.
- MAE is the largest direction-adjusted adverse excursion from the same price.
- ATR-normalized values use only `atr_at_arm` persisted with the signal.
- Extreme timestamps use the earliest bar when equal highs or lows tie.
- Candidate, confirmation, and terminal latencies come from persisted lifecycle
  timestamps.
- Replacement identity is retained when a terminal `location_episode_replaced`
  transition and its new Arm can be joined unambiguously.

Instrument role is reconstructed from the supplied audit configuration. The
record labels this source as `audit_configuration_not_point_in_time`; it must
not be mistaken for durable historical role evidence after runtime switching.

## July 17 Baselines

The primary live run began at `2026-07-17T14:52:10Z` and ended before
`2026-07-17T19:42:00Z`. Its durable audit contains 34 Armed and 2 Triggered
observations, matching the run log.

Auditing the full UTC day instead produces 64 Armed and 5 Triggered observations
because it includes earlier development and test runs. Always name the intended
run window; a calendar date is not automatically one experimental population.

The output is research evidence, not a trading recommendation. Small sample
statistics describe this persisted run only and do not establish calibration,
profitability, or causality.
