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
