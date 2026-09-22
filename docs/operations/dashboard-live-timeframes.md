# Dashboard native timeframes — issue 56

Issue: https://github.com/ShriekinNinja/Markeitech_V2/issues/56
Existing implementation PR: https://github.com/ShriekinNinja/Markeitech_V2/pull/60

## Outcome and scope

Display provider-owned 1m/5m/15m/30m/1h/4h/1d candles with native forming-bar revisions.
All demand goes through DataAcquisitionActor. The operator accepted provider-returned session
boundaries and approved native subscriptions for all timeframes after the ES 1m probe.
This supersedes the previous five-second chart aggregation and deferred 4h/daily design.
Changes remain on the existing branch for local review. No dependency or storage changes.

Open chart selections, shared across browsers, determine native chart subscriptions. The web
thread sends a bounded desired-selection snapshot to DashboardActor; acquisition owns the
native calls and reconciliation. Five-second watchlist prices and quote subscriptions continue.
Selecting another chart or closing the final viewer releases unused streams. Late callbacks
cannot repopulate released state. No source warmup or local candle aggregation is needed.

Native revisions replace the complete same-timestamp OHLCV. Browser merging prefers received
subscription values over overlapping history. Bounded memory is at most configured instruments
and supported frames times candles_per_instrument; active chart streams are bounded by clients.
History requests retain their existing planner/executor budgets, timeout and paging lifecycle.
A failed chart does not remove independent watchlist claims. System-wide reconnect repair is #66;
historical cache/catalog reuse is #65. Neither is part of this batch.

## Native alignment and evidence

Refreshed 2026-09-17: [nightly guides](https://nautilustrader.io/docs/nightly/) and
[nightly Python API](https://nautechsystems.github.io/nautilus_docs/python-api-nightly/).
The API landing page still reports rc4; the executable contract and adapter source used here are
installed 2.0.0rc5. No native indicator, persistence, catalog, cache database or separate scheduler
is needed to project provider candles. Native actor callbacks, subscription ports, runtime timers,
and request_bars are composed with the existing dashboard's bounded display/mailbox layer.

| Requirement | Native candidate | Installed-version evidence | Adapter/provider evidence | Semantic fit | Proposed owner | Decision | Rejection or extension rationale | Acceptance evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Updating selected candle | DataActor.subscribe_bars/on_bar | rc5 installed stubs and offline native actor attachment test | rc5 IB historical update subscription; handle_revised_bars enabled; ES 1m live probe | Exact provider OHLCV and revisions | DataAcquisitionActor/native data engine | USE_NATIVE | Replaces custom five-second rollup | 13 deliveries, 11 revisions, one rollover and next-bar revision; integrated dashboard pending |
| Time labels | Native Bar identity and ts_event | rc5 convert.rs adds nominal duration, daily minus 1ns | Returned 4h/day sample and provider screenshots | Recover provider open without inventing session closes | Acquisition projection helper | WRAP_NATIVE | Only presentation timestamp conversion; no OHLCV reconstruction | Offline all-frame and shortened-session fixtures |
| History | request_bars and existing acquisition executor | rc5 request API and installed tests | Five returned 4h and five daily bars in earlier authorized probe | Provider bars in selected window | Historical planner/DataAcquisitionActor | COMPOSE_NATIVE | Existing bounded HTTP correlation and paging retained | Offline page tests; integrated long-frame acceptance pending |
| Demand lifecycle | Native subscriptions plus existing acquisition coordinator | Installed subscribe/unsubscribe and handler routing | 1m probe unsubscribed and node stopped | One shared claim per selected instrument/frame | DataAcquisitionActor | COMPOSE_NATIVE | Browser selections need bounded union/diff | Shared viewer, switch, release and late-callback tests |

Reference source: [rc5 timestamp conversion](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc5/crates/adapters/interactive_brokers/src/data/convert.rs)
and [IB subscription stream](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc5/crates/adapters/interactive_brokers/src/data/core_streams.rs).

## Configuration and local acceptance

### Browser history window correction

The browser retains at most `candles_per_instrument` displayed candles around the visible
window. Older/newer pages preserve a visible timestamp and its fractional screen position;
eviction occurs outside the visible candles. Scrolling to either edge or using Older/Newer
requests the adjacent page through the existing history endpoint. Removed history is fetched
again, not persisted. Empty session windows advance the relevant request cursor without
fabricating bars. If eviction would remove visible candles, pan toward the requested history
or zoom in before loading another page.
The bounded live tail remains separate and cannot bridge an evicted gap into an old view.
A separate transient recent window retains the newest already-loaded candles, bounded by the
same display capacity, and receives native updates while browsing. Follow live switches to it
immediately without a history request. Only a selection with no successful initial history yet
uses the loading fallback: keep the browsing window visible until recent history succeeds, or
preserve it and show the error on failure. The existing live stream continues. Late responses from superseded browser history work
are ignored; already-admitted provider requests are not claimed to be canceled.

Offline JavaScript regressions run through `pytest tests/dashboard/test_chart_window.py`
using an existing Node executable (no npm/install/build; skipped explicitly if unavailable).
They exercise retention and request control with stubbed transport/chart APIs, not provider or
real-browser acceptance. Local review: select ES 1h, zoom to a portion of the chart, load/scroll
past 720 candles, then navigate right into removed history. The same viewed candles should
remain at the same positions on page arrival. Return to Follow live, including once during a
pending Older request; recent history and native updates should return without changing 1h.
Verify a date range still replaces the view and that a fully zoomed-out capacity prompts for
zoom rather than removing visible candles. This correction changes browser presentation only.

Dashboard policy 6 migrates policies 3–5 in memory, preserving local files. Composition enables
handle_revised_bars when the dashboard is enabled, a requirement of this approved native path.
Without dashboard it respects the configured IB flag. initial_history_minutes and its legacy
source_history_count are retained solely for profile/API compatibility; no warmup is requested.
initial_history_candles and history_page_candles still control selected-frame history windows.
Closed sessions can return fewer candles than the nominal window count.

Markeitect runs the ordinary system launcher using the existing local profile. Select ES 1m,
observe within-candle updates and one rollover; then switch through all seven timeframes. Compare
exact contract, extended-hours setting and UTC labels against provider candles. Load Older and a
date range, ensuring arriving history does not undo the live candle. Open two viewers on the same
chart, close one, then switch/close the last; verify remaining streams and watchlist prices keep
working. Restart to verify preferences and server lifecycle. No four-hour wait is required for
implementation checks; the 1m probe exercised the revision/rollover mechanism.

Stop for wrong contract/selector, stale values masking revisions, added rather than replaced
volume, growing subscriptions after switches, or a server surviving shutdown. Full chart/session
acceptance belongs to Markeitect; isolated native 1m evidence is not an all-instrument guarantee.

## Prior batches — historical evidence, superseded design

The following records preserve prior review and live-test evidence. The native contract above
supersedes their five-second aggregation plan, configuration version and 4h/daily debt.

# Dashboard timeframes — issue 56 local implementation

Issue: https://github.com/ShriekinNinja/Markeitech_V2/issues/56

## Outcome and plan

Match the operator's TWS extended-hours charts with 1m/5m/15m/30m/1h/4h/1d candles,
updating the selected forming candle from the shared five-second input. All provider demand
continues through DataAcquisitionActor and native Nautilus delivery.

Implement in order:
1. Intraday selection and source-time forming updates.
2. Verify TWS/IB 4h and daily boundaries and compose the existing session authority.
3. Selected-timeframe startup/backward/date-range backfill.
4. Reuse bounded historical coverage, inspecting native cache before adding retained state.
5. Persist the instrument/timeframe preference and verify switching/reconnect behavior.
6. Markeitect compares the completed implementation against TWS before the closing PR.

The first increment was approved for commit on 2026-09-17. Subsequent work stays uncommitted for local review. No connected runs, dependency changes, durable raw
market-data storage, new provider client, or SPY/QQQ entitlement changes are included.

## Current first increment

- The selectable intervals are 1m, 5m, 15m, 30m and 1h, with UTC clock boundaries.
- Acquisition composes disjoint minute constituents from the existing bounded source-time book.
  Five-second input exactly at a close belongs to the preceding candle. Late inputs repair their
  own interval. Missing constituents remain incomplete; historical/live overlaps never add volume
  twice. No wall-clock timer closes a candle before its source input arrives.
- Every interval has a separate display projection. HTTP/SSE selection and historical-page
  correlation carry timeframe identity. Invalid timeframes/bounds are rejected.
- Selected-timeframe initial and older/date history now requests native completed bars through
  acquisition: 1/5/15/30-minute and 1-hour LAST EXTERNAL. The default selection window is
  200 selected intervals, capped by display capacity. Pages are bounded to 200 intervals by
  default (maximum 1000). Closed sessions can return fewer candles; no gaps are fabricated.
- Completed provider pages retain their native selector and provider_history provenance.
  Browser overlap chooses the completed provider candle as a whole, never sums its volume
  with a five-second reconstruction, and leaves the current forming interval on the live feed.
- Five-second source warmup covers at least 60 minutes plus one boundary minute, even if
  initial_history_minutes is smaller. This seeds the forming hourly candle without fetching
  the entire selected history at five-second resolution. Source retention also has a 60-minute
  floor; resources are validated against the effective source count.
- Date bounds align to the selected timeframe. Every selection triggers initial history,
  independent of whether the live feed has already produced a candle. Failed history remains
  visible and the live stream continues. Switching selections discards stale pending UI results.
- Provider bars whose boundaries do not match the supported UTC intervals fail projection
  explicitly; they are not silently rebucketed. Connected alignment still needs operator review,
  particularly instruments whose provider sessions use half-hour openings.
- Browser local storage remembers only the selected instrument and timeframe. Invalid, removed,
  or inaccessible preferences fall back safely; market observations are not stored there.
- 4h/daily are not exposed until provider grouping and the reference chart timezone are verified.
  The screenshots establish the desired product appearance, not the timezone/API timestamp map.

## Native capability check

Refreshed both nightly documentation roots and the cache guide on 2026-09-16. Installed package:
NautilusTrader 2.0.0rc4; the API root also reports rc4. Nightly guide claims can differ from the pin.
Local signatures were inspected without a connection. Cache lives in `nautilus_trader.common`
on this pin, not `nautilus_trader.cache`.

| Requirement | Native candidate | Installed evidence | Provider evidence | Fit and owner | Decision | Acceptance |
| --- | --- | --- | --- | --- | --- | --- |
| Shared source delivery and bounded historical fetch | DataActor.request_bars and native subscriptions | Installed request signature and existing NautilusHistoricalPort | Previous accepted one-minute delivery; higher native bar sizes not measured here | Acquisition remains request owner | USE_NATIVE | Existing regression tests; later selected-timeframe provider comparison |
| Forming candles from five-second inputs | Native composite time aggregation / partial builder | Existing rc4 investigation found no exposed partial builder; timer closes before final source arrival in measured case | See dashboard-native-backfill.md; no new provider run | Extend existing acquisition source-time projection to intraday groups | WRAP_NATIVE | Exact constituent, late-input, missing-input and overlap tests |
| Reuse fetched bars | common.Cache.bars/bar/bar_count | Installed signatures verified; no public add_bar method | Native completed-bar cache previously sampled; historical coverage/eviction behavior needs characterization | Acquisition can consult native cache; HTTP cannot | UNKNOWN | Inspect completed historical request cache effects before cache implementation |
| Sessions, trading dates, breaks, DST | Existing SessionStateActor projection contracts | Current architecture assigns sole session ownership | TWS screenshot requires timestamp comparison | Consume canonical session facts | COMPOSE_NATIVE | 4h/daily remains subsequent work |
| Last selection | Browser localStorage | UI preference only | Not provider data | Browser | USE_NATIVE | Refresh/invalid preference/removed instrument browser checks |

## Local review

For the first increment, use the ordinary system launcher only when Markeitect chooses to run it.
Compare 1m through 1h with the same exact contract, session coverage and UTC window. Verify each
five-second input changes the current candle, selecting another timeframe keeps its own candles,
and a page response for an old selection never reaches the newly selected chart. Refresh and
verify instrument/timeframe restoration. Stop on incorrect identities or timestamps, duplicate
volume, frozen updates, or a provider request outside acquisition.

Completed offline tests establish only exercised source-time/HTTP behavior; TWS parity,
4h/daily, reusable cache coverage and connected acceptance remain open.

## First-increment verification — 2026-09-16

- `markeitech verify all`: Ruff passed; 563 offline tests passed, 2 PostgreSQL tests
  deselected; two existing third-party deprecation warnings. Loopback-only tests require
  socket permission outside the restricted sandbox.
- Locked API documentation generation/check passed with 98/98 documented public entries.
- Locked diagram generation/check passed. Its existing example-profile hash was stale after
  the merged December rollover; refreshed the hash against the unchanged tracked TOML.
- Isolated synthetic dashboard on port 18765: selected NQ/5m, confirmed changing forming
  values, refreshed and retained both preferences, then selected 1h. No browser errors/warnings
  were reported. This checks UI wiring, not broker delivery or TWS numerical parity.
- No runtime configuration, IDE files, dependency locks, or external-service settings changed.

## Selected-history correction — 2026-09-16

Dashboard policy 4 replaces fixed-duration pages with selected-candle-count budgets. Existing
policy-3 mappings are normalized in memory: a legacy 60-minute page becomes 60 selected intervals;
initial selected history defaults to 200. Local TOML files are not rewritten. Startup source
history retains its separate minute setting. Configuration and admission enforce both native
page and five-second seed budgets. No persistence, new dependency, actor or provider owner is added.

Native gate: refreshed nightly guide/API roots (API reports rc4) and inspected installed 2.0.0rc4
request_bars and BarType interval construction. The rc4 IB convert.rs maps the selected intervals
and stamps intraday historical bars at their close. Native historical requests are reused directly;
only detached UI projection and completed/live selection policy are custom. Native Cache.bars
exposes retained observations, not a proof that an arbitrary requested interval (including empty
sessions) was fetched. This correction does not claim native cache completeness or implement the
separate reusable-history-cache task. No new raw history store was introduced.

| Requirement | Native candidate | Installed evidence | Adapter/provider evidence | Semantic fit | Owner | Decision | Extension rationale | Acceptance evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Selected completed history | DataActor.request_bars, BarType | All five selectors construct with expected interval; existing request port | rc4 IB conversion maps intervals and open-to-close timestamps; connected delivery unverified | Direct use | DataAcquisitionActor | USE_NATIVE | Dashboard only chooses bounded window and projects native values | Native-object compiler/projection/HTTP tests; operator live comparison pending |
| Current forming hour | Existing native 5s feed plus source-time book | Existing constituent tests | Prior 1m live proof; hourly comparison pending | Composition | DataAcquisitionActor | WRAP_NATIVE | Seed a full supported interval, retain exact source timestamps | Warmup-budget and overlap tests |

Operator review: restart with the current branch, select 30m then 1h, confirm the initial window
contains substantially more than two/one candles when provider data exists, load an older page,
and select a date range. Confirm the current candle continues changing. A closed-session window
can legitimately contain fewer candles than its configured interval count. Changing timeframe
must never show an earlier request's candles. Check matching contract, UTC bounds and extended
hours against TWS; no agent-run broker check is included.

Correction verification: the final full offline suite passed 571 tests (2 PostgreSQL tests
deselected); 73 focused timeframe/history/configuration checks also passed. Ruff, generated API
documentation and diagram validation passed. Immediate projection failure delivery is covered. Synthetic browser inspection verified 200 completed + 1 forming candle for
30m and 1h, 401 candles after an older page, 48 candles for a one-day 30m date range, preserved
selection on refresh, and the separate labeled Select. The fixture never registered a provider.
The browser now reports selected-history completion immediately, independently of source warmup.


## Operator review — 2026-09-16/17

Markeitect reviewed and approved the current 1m-through-1h dashboard, native selected-history
backfill, five-second forming updates, saved selection, and compact timeframe buttons. The
2026-09-16 ES 30m run lasted approximately two hours with no error-level entries before the
operator-induced disconnect. ES received 1470 five-second bars with zero reported out-of-order
observations. This is bounded acceptance of the observed uninterrupted run, not general TWS
parity or all-session validation.

The reconnect test exposed system-wide live subscription recovery failure and an interrupted
historical request reported as an empty completed response. Markeitect confirmed the recovery
failure and explicitly excluded system-wide reconnect work from this dashboard issue. Keep it
as a known external dependency; do not claim reconnect acceptance or hide failed-provider history
as evidence of a genuinely empty market window.

The next implementation order is pending Markeitect review. The 4h/daily work is deferred
as recorded below. Source observations, local configuration, logs and screenshots are not
included in commits.


## Deferred 4h / 1d debt — 2026-09-17

At Markeitect's request, the uncommitted 4h increment was reverted to the reviewed committed
baseline. Supported timeframes remain 1m/5m/15m/30m/1h, dashboard policy remains 4, and the
example historical observation budget remains 20000. No 4h/1d implementation is included.

- **4h:** deferred native selected-history support and five-second forming updates. Revisit
  provider candle boundaries, sufficient bounded source warmup/retention, and resource budgets.
- **1d:** deferred exchange trading-date/session-aware candles using the existing canonical
  session calendar. Daily candles must not be treated as fixed midnight-to-midnight UTC buckets.
- **Reference:** Markeitect confirmed that the supplied TWS extended-hours screenshots use UTC.
  This establishes display timezone, not API grouping or OHLC parity; live comparison remains due.
- **Separate known dashboard defect:** history admission slots can remain occupied by abandoned,
  unread completed requests, blocking other selections. The committed implementation also has a
  lifetime request budget. Neither behavior was changed by this rollback; cleanup/scheduling and
  metadata retirement need a subsequent scoped fix. System-wide reconnect recovery stays excluded.

The debt note was committed as 0c77757. Catalog evaluation is a separate subsequent task;
4h/daily remain deferred.


## Updated master compatibility — 2026-09-17

Integrated master cfa485f (dependency refresh PR 58), including NautilusTrader 2.0.0rc5,
and synced the root and both isolated documentation environments from their locked dependencies.
The combined dashboard branch passed Ruff and 571 offline tests (2 PostgreSQL tests excluded,
2 existing third-party deprecation warnings). Generated documentation conflicts were resolved
through the approved generators; the example configuration hash was recomputed from this branch.
The earlier rc4 cache/catalog research is historical evidence and must be rechecked against rc5
before storage implementation. No connected provider, Discord or PostgreSQL acceptance was run.
The previously observed steady-state dashboard acceptance does not prove rc5 live compatibility.

## Chart loading and favicon — 2026-09-17

The dashboard serves a packaged, byte-identical copy of `docs/assets/favicon.ico` from its
existing static route. The chart-only loading overlay spans the initial snapshot and first
history fetch for each instrument/timeframe selection. It clears when that selection finishes
or fails; stale requests cannot clear a newer selection's overlay. Older pages and explicit
date-range requests keep the chart visible. The spinner respects reduced-motion preferences.
An isolated delayed synthetic feed verified initial loading, completion, nonblocking Older
loading and a new timeframe's loading state. The favicon response returned HTTP 200 with
bytes identical to the approved asset. No live service was accessed for these checks.


## History lifecycle correction — 2026-09-17

Dashboard policy 5 removes the lifetime history-request quota. Policy 3/4 mappings migrate in
memory, validate and discard the obsolete quota without rewriting local files. Active requests
retain the existing `maximum_history_requests` bound. Terminal results have a separate buffer
of the same capacity and retain the existing timeout; oldest results can be evicted, and a
client polling an evicted/expired ID receives 404. Unread results cannot block admission.

When all active slots are occupied, HTTP returns 429 and the current browser selection retries
using `acquisition_retry_interval_ms`, bounded by `history_request_timeout_seconds`. Switching
selection stops that browser retry/poll loop. Already admitted provider requests finish or time
out through the existing coordinator; no unsupported provider cancellation or concurrency
increase is introduced. Existing request expiry, provider retries and history/live isolation remain.

Acquisition publishes terminal lifecycle, data and readiness before removing dashboard page
request metadata. The coordinator retains the most recent dashboard terminal IDs up to
`historical.maximum_outstanding_requests`; active/retrying IDs are never retired. Dashboard
requests use fresh UUIDs, so ordinary browsing does not reuse retired IDs. Duplicate rejection
for page IDs outside this bounded window is not promised. Other consumers retain their existing
terminal identity protection. Immediate terminal submission failures now retain the request long
enough to publish their result instead of raising a lost-request error. Dispatch also forwards
terminal readiness results on submission failure; previously it forwarded only lifecycle events.

Native check, 2026-09-17: installed NautilusTrader 2.0.0rc5 exposes request_bars and no public
historical cancellation on DataActor. Refreshed nightly guide/API roots; the API site still
labels itself rc4, so the installed interface governs this change. No provider probe was run.

| Requirement | Native candidate | Installed evidence | Provider evidence | Fit | Owner | Decision | Extension rationale | Acceptance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bounded provider requests | DataActor.request_bars | rc5 method and existing request port | Existing accepted delivery; no new connected run | Reuse existing execution lane | DataAcquisitionActor | USE_NATIVE | No new provider owner | Existing execution tests |
| Browser abandonment and retained results | HTTP jobs and native request lifecycle | No native historical cancellation exposed | Cancellation not claimed | Finish admitted work; stop obsolete browser waits | Dashboard HTTP worker / acquisition | WRAP_NATIVE | HTTP result retention and page metadata belong to existing application owners | Repeated unread completions/failures, expiry, metadata retirement and rapid switching |

No Redis, catalog, raw-data persistence, new actor, 4h/daily or reconnect changes are included.
Operator review: rapidly switch instrument/timeframe while history loads, then leave one selected;
it should finish without requiring restart. Repeat Older requests, test a failed/empty window,
and verify the current candle continues updating. Busy waits are bounded and a sustained stall
remains visible rather than increasing provider concurrency.
