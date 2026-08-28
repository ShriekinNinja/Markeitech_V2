# V3 ES Visual-Debug Review Handoff

## Purpose

This document hands off the V3 progressive visual-debug side mission at its first almost-acceptable
baseline. Its purpose is to let a future agent continue the review without reconstructing intent
from chat history or confusing a working capture with accepted analytical behavior.

The active review procedure and acceptance taxonomy are consolidated in
`docs/notes/v3-visual-debug-review-contract.md`. Read that contract with this handoff. The prior
indicator report and Pillow snapshot suggestion are historical source notes and may be moved out of
the active side-mission scope.

Markeitect retains final architecture, product, provider, visual-acceptance, and release authority.
Nothing described here is accepted merely because it is implemented, committed, rendered, or
covered by offline tests.

## Recovery Point

- Branch: `v3-es-progressive-capability-review`
- Baseline commit: `623f0b7` (`Add V3 ES one-hour visual debug baseline`)
- Disposition: almost acceptable baseline; not final visual acceptance
- Connected instrument: `ESU6.CME`
- Runtime: connected Interactive Brokers through installed NautilusTrader `2.0.0rc3`
- Active local configuration: `v2/config/system.v3-es-minimal.toml`

The baseline commit intentionally excludes these unrelated, untracked documents:

- `docs/notes/current-indicators-and-intelligence-report.md`
- `docs/notes/es-live-knowledge-snapshot-suggestion.md`

Do not add, edit, delete, or commit those files as part of this review unless Markeitect separately
authorizes it.

Their still-valid debug requirements have now been consolidated into
`docs/notes/v3-visual-debug-review-contract.md`; they are no longer required as active authorities.

## Goal

Build a deliberately small live-runtime review process that shows what Markeitech actually knows
about one instrument, one configured analytical period, and one metric family at a time.

The review artifact must:

- originate from the real connected runtime, not a replay or display-side reconstruction;
- show canonical completed candles and the canonical values calculated from them;
- preserve UTC timestamps, provider/source identity, health, fidelity, revisions, missingness, and
  request/readiness lineage;
- use an interactive Plotly candlestick chart only as a projection of captured canonical records;
- avoid reusing the rejected periodic visual-acceptance implementation or the rejected Pillow
  exhaustive snapshot implementation;
- fail honestly on gaps, source-order violations, incomplete metric cohorts, conflicts, timeouts,
  rendering failure, or shutdown before freeze; and
- support a one-by-one review of enabled and disabled analytical capabilities before any broad
  visual dashboard is considered.

The current baseline reviews only the completed-bar foundation family. It is not yet the general
multi-timeframe or historical-only review process.

## Implemented Baseline

### Minimal connected configuration

`v2/config/system.v3-es-minimal.toml` activates only the bounded surface required for the ES review:

- `ESU6.CME` as the only watchlist instrument;
- the shared five-second last-price bar acquisition needed for live aggregation;
- session/calendar and evidence-health infrastructure;
- the completed-bar foundation metric actor;
- the isolated visual-debug projection;
- bounded operational PostgreSQL audit; and
- no Discord, entity analysis, quote-quality metrics, rolling measurements, session references,
  analytical windows, legacy visual acceptance, or legacy live-evidence review.

The configuration still contains schema-required disabled placeholders. Those values are not
accepted analytical defaults.

### Current capture policy

The committed baseline freezes one contiguous hour of one-minute ES bars:

```text
55 HISTORICAL_PROVIDER bars | 5 LIVE_AGGREGATE bars
                            ^
                     exact contiguous seam
```

The capture contains:

- 60 canonical `CompletedBarInput` records;
- seven canonical `MetricValue` subjects per interval;
- 420 selected metric records in one complete revision cohort per interval;
- one exact historical readiness event for all 55 historical bars;
- a frozen canonical payload digest;
- a self-contained interactive `snapshot.html`; and
- a `manifest.json` with expected and observed population, lineage disclosures, and integrity
  hashes.

The seven displayed subjects are:

- open;
- high;
- low;
- close;
- volume;
- simple return; and
- true range.

The projection does not calculate any of those values. Plotly converts Decimal copies to browser
numbers only for geometry; exact canonical strings remain available in the captured record table.

### Historical/live seam correction

The first connected attempt requested history at startup. It returned five bars ending at 13:53
UTC, while the runtime began partway through the 13:53-13:54 five-second aggregation bucket. That
partial minute could never contain all twelve constituents, so the first complete live minute began
at 13:54 and the strict historical/live sequence could never become contiguous.

The committed Option 1 correction is active only when visual debug is enabled:

1. wait for the first complete live aggregate;
2. take its interval start as the exclusive historical `as_of_ns` boundary;
3. publish one typed, bounded historical dependency demand;
4. let `DataAcquisitionActor` remain the sole provider-facing request owner;
5. request the immediately preceding 55 completed one-minute bars; and
6. require the last historical interval end to equal the first live interval start.

It does not accept partial live bars, fabricate observations, relabel historical data as live,
split the history request, issue a second request, or change ordinary session-metric startup when
visual debug is disabled.

### Post-baseline boundary correction

The behavior above is committed recovery evidence, not an accepted final boundary. Markeitect has
clarified that enabling `visual_debug_capture` must have no effect on normal runtime operation.
The committed `visual_snapshot_enabled` coupling currently changes SessionMetrics historical-demand
timing and therefore breaches the current non-interference invariant.

The next design must make the capture a passive selector of canonical records the independently
configured runtime already produces. Capture mode may control which records enter the artifact; it
must not add, suppress, align, refresh, or retime historical/live provider demand or change what a
producer calculates. Capture-off versus capture-on equivalence is a required acceptance fixture.

### Native historical boundary correction

A prior connected calibration exposed an inclusive-to-exclusive request-end defect: converting an
exclusive nanosecond boundary to a whole-second native request end produced repeatable 4/5 results.
The committed native-port correction preserves the exclusive completed-minute boundary. One
connected ES calibration returned exactly five consecutive completed one-minute bars after this
correction.

This is narrow evidence for the recent-completed intraday path, not acceptance of every selector,
bar size, duration, session window, or provider edge case.

## Runtime Evidence

### Measured connected evidence

The rejected first visual-capture attempt still established that:

- Interactive Brokers returned the bounded five-bar calibration request;
- session metrics reached historical readiness;
- 279 live five-second bars entered the metric actor;
- 27 completed one-minute bars were admitted;
- 189 completed-bar metric values were published;
- there were zero completed-bar duplicates, conflicts, or calculation failures;
- the configured 15-minute capture deadline fired;
- persistence reconciled 35 accepted/stored operational records with zero retries, failures,
  rejections, or pending writes; and
- SIGINT shutdown completed cleanly.

No artifact was created because the strict seam was impossible, which was correct behavior. The
shutdown-flushed records refuted the earlier timer-stall hypothesis.

The corrected 55+5 capture has not yet been connected-accepted or visually approved.

### Offline evidence at the baseline commit

Immediately before commit `623f0b7`:

- 438 non-PostgreSQL tests passed;
- 3 tests belonging to the rejected static Plotly/Kaleido path were deliberately deselected;
- focused coverage exercised startup offsets at 00, 01, 25, and 59 seconds;
- the compiler produced one exact 55-minute request ending immediately before the first full live
  interval;
- the collector froze exactly 60 bars and 420 metric values;
- readiness rejected the old five-observation population and accepted the configured 55;
- the one-hour Plotly HTML rendered deterministically;
- atomic output publication and shutdown fencing passed;
- Ruff passed for changed Python files; and
- `git diff --check` passed.

These are offline contract results. They do not prove connected provider delivery, browser visual
acceptance, accessibility, performance, formula parity, or downstream evidence fitness.

## Provider And Time Boundary

UTC remains the internal timestamp identity. Installed NautilusTrader `2.0.0rc3` sends intraday
historical bounds in UTC, but its pinned Rust `ibapi 3.3.0` cannot parse Interactive Brokers' valid
dashed UTC `HistoricalDataEnd` response metadata. TWS/Gateway therefore currently needs the
instrument-timezone API attribute setting for this path even though the resulting observations are
normalized to Unix nanoseconds internally.

The current one-hour history request is one 3,300-second request for 55 one-minute bars, with one
outstanding and one in-flight slot. The 30-second timeout remains provisional. A timeout or short
response must fail honestly; it must not cause splitting or an automatic second request.

Run the current strict capture away from an exchange maintenance break, session/window transition,
or trade-date boundary. All 60 bars must share one configured identity and be exactly contiguous.
The current broad CME `OPEN` envelope and empty phase definitions are known calendar-model debt,
not accepted analytical-session semantics.

## Known Debt And Non-Acceptance

- The chart is almost acceptable, not approved.
- `visual_debug_capture.enabled` currently changes SessionMetrics history bootstrap through
  `visual_snapshot_enabled`; this violates the clarified passive-projection boundary.
- The candle panel is too short for the intended review and needs at least 200 additional vertical
  pixels without shrinking the three metric panels.
- Historical/live counts are configurable, but the configuration is spread across capture,
  session-metric, and global historical-resource fields.
- `live_bar_count` is currently required to be positive. Historical-only capture is not supported.
- Option 1 history alignment depends on a first complete live bar, so historical-only mode requires
  a separately defined boundary policy rather than setting the current value to zero.
- Only the one-minute completed-bar definition is composed and tested in this V3 profile.
- Multi-timeframe review must coordinate the historical bar specification, live aggregation target,
  interval bounds, capture specification, request limits, and duration/count semantics.
- File logging has measured live-observability debt: consequential records were buffered until
  shutdown, so absence from a tailed log does not prove a stall.
- Parameter effective time is stored but not enforced or published on `MetricValue`.
- Completed-bar retention remains provisionally coupled to a disabled rolling placeholder.
- Maximum output age is metadata rather than actor-enforced expiry.
- `MetricValue` lacks bar specification, analytical profile, trade date, and window identity.
- Prior-close metrics omit predecessor lineage and do not completely define predecessor health,
  contiguity, or session-transition compatibility.
- Common metric revision is an implementation-derived cohort rule, not a formal typed cohort ID.
- The projection does not receive upstream rejected-bar conflict evidence or the twelve five-second
  constituent records.
- Browser accessibility, performance, exact formula parity, licensing, and final evidence-fitness
  acceptance remain incomplete.

## Requested Next Decisions — Not Implemented

### 1. Increase candle-panel height

Markeitect requested at least 200 additional pixels for the candle portion. The intended change
should increase the overall Plotly height and allocate the added pixels to row 1 while retaining the
current approximate pixel heights of volume, simple return, and true range. Merely increasing the
total height while keeping the current 60/15/12.5/12.5 percentages would distribute part of the
increase to the metric rows and would not satisfy the request precisely.

No height change is included after baseline commit `623f0b7`.

### 2. Make timeframe and historical/live composition understandable

Three different choices must remain explicit:

1. candle timeframe, such as one, five, or fifteen minutes;
2. historical and live bar counts; and
3. capture mode and boundary policy, especially when live bars are unnecessary.

The current TOML exposes counts under `[visual_debug_capture]`, but timeframe changes require
coordinated edits in the session-measurement completed-bar definition. Historical-only mode cannot
be enabled honestly through the current schema because the live count must be positive and the
aligned history request is anchored by the first complete live aggregate.

A future batch should first present the exact proposed configuration contract to Markeitect. It
must not silently treat zero as a normal count, infer a historical boundary, or make the visual
actor call Interactive Brokers. Provider ownership remains with acquisition, and the
session-metric producer remains the owner of canonical completed bars and metric cohorts.

No multi-timeframe or historical-only change is included after baseline commit `623f0b7`.

## Handoff Procedure For The Next Agent

1. Read `AGENTS.md`, `markeitech.md`, `docs/current-status.md`,
   `docs/development-guidelines.md`, and `docs/README.md` before planning or editing.
2. Confirm branch `v3-es-progressive-capability-review`, baseline `623f0b7`, and current worktree.
3. Preserve the two unrelated untracked note documents listed above.
4. Treat this handoff document itself as an uncommitted review artifact until Markeitect approves
   its disposition.
5. Do not run connected IB, PostgreSQL-destructive paths, or external integrations unless
   Markeitect explicitly authorizes that exact run.
6. While Kite mode is active, obtain the required narrow Nautilus advisor consultation before a
   consequential timeframe, request, actor, or configuration design/edit.
7. Preserve the non-interference contract in `v3-visual-debug-review-contract.md`; capture modes
   select artifact records only and must not become runtime operating modes.
8. Explain the candle-height and multi-timeframe/historical-only design before implementing either.
9. Keep the next implementation batch separate and uncommitted for local review.
10. Verify focused contracts, the proportional offline suite, Ruff, `git diff --check`, the final
   diff, and worktree contents before presenting it.
11. Do not claim visual acceptance until Markeitect reviews the connected artifact.

## Current Run Command

```bash
docker compose \
  --env-file "/Users/markeitect/PycharmProjects/Markeitech/v2/.env" \
  -f "/Users/markeitect/PycharmProjects/Markeitech/v2/compose.yaml" \
  up -d --wait postgres \
&& exec "/Users/markeitect/PycharmProjects/Markeitech/v2/.venv/bin/python" \
  -m markeitech.system.cli \
  "/Users/markeitect/PycharmProjects/Markeitech/v2/config/system.v3-es-minimal.toml" \
  --connect I_UNDERSTAND_THIS_CONNECTS_TO_IB \
  --keep-awake
```

Expected output root:

`v2/data/visual-debug-captures/`

The expected success marker is `VISUAL_DEBUG_CAPTURE_OUTPUT_PUBLISHED`, but the output directory and
shutdown-flushed lifecycle counters are stronger evidence while the file-buffering debt remains.
