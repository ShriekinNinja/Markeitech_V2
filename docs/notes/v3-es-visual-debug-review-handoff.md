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

The rejected `VisualAcceptanceActor` and `LiveEvidenceReviewActor` have been removed from the
current runtime, configuration schema, source tree, and test suite. Schema 18 rejects their old
configuration sections. The progressive `visual_debug_capture` path is independent and remains
the sole visual-review actor in this profile. Ignored historical artifacts and ignored obsolete
local configurations were preserved as recovery evidence and must not be treated as runnable
current profiles.

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
  analytical windows, or legacy visual-review actors.

The configuration still contains schema-required disabled placeholders for inactive analytical
capabilities. Those values are not accepted analytical defaults.

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
The committed `visual_snapshot_enabled` coupling changed SessionMetrics historical-demand timing
and therefore breached the current non-interference invariant. The uncommitted correction removes
that path.

The corrected design makes capture a passive selector of canonical records the independently
configured runtime already produces. Capture mode controls which records enter the artifact; it
does not add, suppress, align, refresh, or retime historical/live provider demand or change what a
producer calculates. Capture-off versus capture-on composition equivalence is covered offline;
connected operational equivalence remains open.

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
- The committed baseline changed SessionMetrics history bootstrap through
  `visual_snapshot_enabled`; the current uncommitted correction removes that coupling.
- The candle pane is configured at 720 pixels; exact browser geometry and overlap acceptance remain
  open.
- Historical/live counts are configurable, but the configuration is spread across capture,
  session-metric, and global historical-resource fields.
- Projection targets now allow historical-only, live-only, or mixed selection; they never change
  normal live operation or create a historical request.
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

## Current Temporary Baseline

### 1. Increase candle-panel height

Markeitect requested at least 200 additional pixels for the candle portion. The intended change
should increase the overall Plotly height and allocate the added pixels to row 1 while retaining the
current approximate pixel heights of volume, simple return, and true range. Merely increasing the
total height while keeping the current 60/15/12.5/12.5 percentages would distribute part of the
increase to the metric rows and would not satisfy the request precisely.

The current uncommitted renderer uses a 720-pixel candle pane, 130-pixel volume pane, two 110-pixel
metric panes, 18-pixel gaps, and a 1,204-pixel Plotly figure. Browser geometry and accessibility
acceptance remain open.

### 2. Make timeframe and historical/live composition understandable

Three different choices must remain explicit:

1. candle timeframe, such as one, five, or fifteen minutes;
2. historical and live bar counts; and
3. capture selection mode, especially when live bars are unnecessary.

The current TOML exposes `target_historical_bars` and `target_live_bars` under
`[visual_debug_capture]`. Either may be zero; both cannot be zero. These values select artifact
records only. Timeframe remains a normal SessionMetrics producer choice: historical selector,
calculation interval, fixed interval envelope, and matching capture bar specification change
together between sequential runs. The loader verifies that the historical selector equals the
calculation interval and that the live selector divides it exactly.

The visual actor does not infer a historical boundary or call Interactive Brokers. Provider
ownership remains with acquisition, and SessionMetrics remains the owner of canonical completed
bars and metric cohorts.

One-, five-, and fifteen-minute sequential configuration is structurally supported, but only one
completed-bar foundation series may be active per run while `MetricValue` lacks full series
identity. This is a singular `SessionMetricsActor` configuration shape, not a system-wide
historical-timeframe rule. Other actors/capabilities may declare their own historical selectors;
the disabled session-reference configuration already carries a separate fifteen-minute selector.
The temporary profile nevertheless allows only one distinct outstanding historical request, so a
concurrent second selector would currently be rejected rather than queued. Five-minute connected
source/series evidence is accepted only for the bounded run below; other-timeframe provider parity
and metric acceptance remain open.

After passive baseline `1f3ead2`, the current temporary configuration baseline selects one direct
`5-MINUTE-LAST-EXTERNAL` producer series, up to 60 normal historical observations, 60 historical
artifact bars, and zero live-source artifact bars. The normal five-second live stream remains
configured and operating; zero live bars is a projection choice only. The nominal artifact span is
five hours before real gaps.

The 2026-08-28 connected run passed and Markeitect accepted the bounded five-minute source/series
gate. IB returned 60/60 direct five-minute bars for the exact UTC request, SessionMetrics accepted
all 60 with zero duplicates, conflicts, or calculation failures, and the passive artifact selected
60 historical and zero live bars as `COMPLETE_CONTIGUOUS` with no declared gaps. The current chart
layout is provisionally accepted as the working debug baseline. Repeated per-bar historical-source
markers are visual cleanup debt; simple-return and true-range formulas remain unaccepted.

Markeitect accepted this as a usable debug baseline, not as the desired final configuration
experience. Producing the single review series currently requires coordinated edits to the active
producer selector and interval, acquisition capacities, projection selector and counts, and an
inert rolling placeholder used by validation/retention. That coupling is recorded configuration
interface debt. It must not be hidden by treating the projection as an operating mode or by letting
`visual_debug_capture` alter normal acquisition and calculation.

## Accepted Source/Series Gate And Next Walkthrough

The accepted connected run reconciled these facts:

1. The normal five-second live selector remains the live constituent stream even though the
   artifact selects zero live-source bars.
2. The direct five-minute historical selector and 300-second calculation interval identify the
   single active completed-bar foundation series.
3. Producer history count, global per-request/total capacities, and observer target are all 60,
   but remain separate contracts rather than one visual setting controlling runtime behavior.
4. Acquisition emits one direct five-minute historical request; record its exact UTC bounds,
   requested limit, request identity, terminal state, and returned observation count.
5. SessionMetrics publishes canonical five-minute completed bars with explicit historical source
   identity and UTC interval ends; the observer selects up to exactly 60 of those records and zero
   live-source records without changing their production.
6. Reconcile logs, capture manifest, canonical-bar table, interval continuity, and every real gap
   before judging the chart.

The next step is a setting-by-setting walkthrough of
`[metrics.session_measurements.completed_bars]`, then raw OHLCV, simple return, and true range.
Return and true-range acceptance must remain blocked until predecessor identity, lineage,
contiguity, and session-transition debt is resolved or explicitly bounded.

`SessionMetricsActor` currently combines four responsibility families: the completed-bar
foundation, session references, calendar-relative windows, and rolling measurements. The composed
runtime has one such actor instance, and the foundation fields are singular. Therefore it cannot
currently maintain parallel canonical five-minute and fifteen-minute foundations even though the
historical-demand protocol and Nautilus `BarType` identity permit another actor to request its own
fifteen-minute history. The temporary `maximum_outstanding_requests = 1` profile further prevents
a second distinct request from waiting while the first is active. Record both limitations as
architecture/configuration debt; do not infer that all history must be five minutes, and do not
select a redesign until the later multi-series review.

## Handoff Procedure For The Next Agent

1. Read `AGENTS.md`, `markeitech.md`, `docs/current-status.md`,
   `docs/development-guidelines.md`, and `docs/README.md` before planning or editing.
2. Confirm branch `v3-es-progressive-capability-review`, passive-observer baseline `1f3ead2`, the
   latest five-minute configuration baseline, and current worktree.
3. Do not run connected IB, PostgreSQL-destructive paths, or external integrations unless
   Markeitect explicitly authorizes that exact run.
4. While Kite mode is active, obtain the required narrow Nautilus advisor consultation before a
   consequential timeframe, request, actor, or configuration design/edit.
5. Preserve the non-interference contract in `v3-visual-debug-review-contract.md`; capture modes
   select artifact records only and must not become runtime operating modes.
6. Continue the completed-bar configuration walkthrough before visually accepting any metric.
7. Keep the next implementation batch separate and uncommitted for local review.
8. Verify focused contracts, the proportional offline suite, Ruff, `git diff --check`, the final
   diff, and worktree contents before presenting it.
9. Do not claim provider, source-series, metric, or visual acceptance until Markeitect reviews the
   corresponding connected evidence.

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
