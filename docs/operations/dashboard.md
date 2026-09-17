For issue #56 intraday implementation and its remaining gates, see
[dashboard live timeframes](dashboard-live-timeframes.md).

# Dashboard POC — Local Review

For the subsequent timeframe investigation, see the
[native backfill live check](dashboard-native-backfill.md). It records the native timer failure, the acquisition-owned source-time extension,
and subsequent live verification of the one-minute dashboard.

The observable outcome is an enabled-watchlist sidebar with latest quotes and one-minute candles
that update from each five-second source bar, and one chart selected from that sidebar. The interface uses neutral dark
grays, gold accents, white up candles, and red down candles. This is a display projection;
connected acceptance remains Markeitect's run and review.

## Components and data path

- `DashboardActor` is an optional Nautilus `DataActor`. It receives membership from
  `WatchlistActor`, submits display demand to `DataAcquisitionActor`, and receives native
  `QuoteTick` and `Bar` callbacks. It retains bounded transient display state.
- `DashboardServer` is the actor-owned FastAPI/Uvicorn worker. A capacity-one mailbox transfers
  detached snapshots from the actor thread. It serves local HTTP snapshots and Server-Sent Events
  (SSE), with a bounded number of browser connections. New snapshots replace unconsumed snapshots.
- `DashboardUI` is the locally served HTML/CSS/JavaScript interface using the bundled
  TradingView Lightweight Charts 5.2.1 asset. Selection changes the browser projection. Live updates arrive through SSE;
  requested history arrives as detached pages. Reload restores runtime history and the last instrument/timeframe preference; operator-fetched
  pages and selected date windows are transient browser state.

Every dashboard market-data request and release goes through `DataAcquisitionActor`. Composition
binds a native subscription port for the dashboard to acquisition before startup. Acquisition
admits the logical demand, then executes native subscribe/unsubscribe methods on the dashboard's
behalf from its timer. This registers the dashboard's own native callbacks without issuing
provider commands from the dashboard. Acquisition retains the provider-demand ownership and
existing watchlist claims. The web worker has no actor, cache, acquisition, or provider reference.

Membership requests are retried until Watchlist's startup audit is ready; Watchlist then repeats
its immutable membership projection. Quotes are requested only for `top_of_book`; completed bars
only for `watchlist_last`. All enabled members appear, including members whose feeds are not yet
available. A disabled watchlist produces an empty dashboard.

## Configuration and migration

The system configuration schema is **28**. Dashboard policy is version **4**. Copy the commented
`[dashboard]` section from `config/system.example.toml` into your existing ignored local profile,
preserving its machine/provider settings. For schema-25/26/27 profiles set `schema_version = 28`. If `[dashboard]` already exists,
use policy 4 for new profiles. Policy-3 input is normalized in memory without changing the file;
its legacy page-minute count becomes the selected candle count. `initial_history_minutes` defaults
to 20, with a 60-minute minimum effective source warmup. The section remains
optional and omission disables the dashboard. Preserve machine-specific connection settings.
For older profiles, first follow [developer setup](developer-setup.md). Local files are never
migrated automatically.

| Setting | Default | Valid range / meaning |
| --- | --- | --- |
| `policy_version` | `4` | Exactly `4`; version-3 mappings migrate in memory |
| `enabled` | `false` | Boolean; compose dashboard on startup |
| `port` | `8765` | 1024–65535; host fixed to `127.0.0.1` |
| `maximum_instruments` | `64` | 1–256; reject an enabled watchlist beyond this limit |
| `candles_per_instrument` | `720` | 2–5000; display candles per timeframe; underlying source-minute retention has a 60-minute floor |
| `initial_history_minutes` | `20` | 1–120 source minutes; effective minimum 60, plus one boundary minute |
| `initial_history_candles` | `200` | 1–1000 selected intervals on selection, capped by display capacity |
| `history_page_candles` | `200` | 1–1000 selected intervals per native page; closed sessions may return fewer |
| `maximum_history_requests` | `4` | 1–16 pending/unread jobs across browsers |
| `maximum_history_requests_per_session` | `256` | 1–4096 admitted pages per process; bounds retained executor request metadata |
| `history_request_timeout_seconds` | `120` | 10–300 seconds; web jobs/results and unacknowledged actor requests expire |
| `publish_interval_ms` | `250` | 100–5000; browser projection cadence |
| `acquisition_retry_interval_ms` | `1000` | 100–10000; membership and attachment retry cadence |
| `maximum_clients` | `4` | 1–16; concurrent SSE clients |
| `shutdown_timeout_seconds` | `5` | 1–30; worker shutdown/join deadline |

The tracked example and operational profiles explicitly enable the dashboard; omission uses the
disabled default. All settings are startup-only, typed and bounded; unknown dashboard fields are rejected.
`--dashboard` enables the dashboard for that invocation without rewriting the TOML. The loader validates the initial history count against per-request, total-observation and
queue budgets in `[historical]`. Every admitted bar-enabled member requests recent history
on membership readiness; a new live bar is not required to start backfill. A one-time two-minute history tail at the first live bar covers the subscription
handshake; initial and tail requests each retain their bounds and acknowledgements.
Resource validation includes both requests per bar-enabled member. Requests are
acknowledged by the existing executor and use its configured timeout/retry policy.
No npm
installation or frontend build is required. Provision Python dependencies with `uv sync --locked`.

## Dashboard-ready Discord notification

When the HTTP listener has completed startup and is accepting connections, `DashboardActor`
publishes one version-1 `DashboardReadyEvent` on `markeitech.dashboard.ready`. The existing
`DiscordHealthActor` projects it through its operational delivery worker to
`MARKEITECH_DISCORD_OPERATIONAL_EVENTS_WEBHOOK`. It sends **Markeitech | Dashboard ready to view**
with the actual configured `http://127.0.0.1:<port>` address and no mentions. The message notes
that the address opens on the machine running Markeitech and market data may still be loading.

Use the existing `[discord].enabled` switch and webhook environment setup; there is no new
configuration field or separate webhook client. The existing Discord actor requires its system
health webhook as well as the operational webhook. Disabled/missing delivery stays disabled.
A server bind/startup failure does not publish readiness. Browser refreshes and instrument
changes do not publish it again. Discord deduplicates by server instance; existing bounded queue
admission and HTTP delivery failure logging apply, without claiming guaranteed external delivery.

## Offline local review

From the repository root:

```bash
.venv/bin/python -m tests.dashboard.preview
```

Open `http://127.0.0.1:8765`. The banner says **OFFLINE PREVIEW** and all observations are synthetic.
This fixture uses a real provider-free LiveNode and DashboardActor/server lifecycle, and directly
invokes native-object callbacks to exercise display behavior. It does not prove native provider
delivery or entitlement. Select instruments, search the sidebar, pan/zoom, toggle follow-live,
reload, and observe the forming minute update every five seconds. Ctrl-C stops the preview and releases port 8765.
Stop this preview before starting the connected system on the same port.

## Markeitect's connected scenario

Review the dashboard PR on `watchlist-review`. The existing IB/Discord/persistence prerequisites
and explicit connection confirmation apply. Use your reviewed schema-28 local configuration:

```bash
.venv/bin/markeitech system build --config config/system.local.toml --dashboard
.venv/bin/markeitech system run --config config/system.local.toml --dashboard --connect I_UNDERSTAND_THIS_CONNECTS_TO_IB
```

The first command constructs but does not connect the node. The second is **Markeitect-run only**.
The server starts when DashboardActor starts. Open the configured loopback port and confirm all
enabled members appear. Confirm exactly one operational Discord message contains the same
configured dashboard address; refreshing/selecting instruments must not repeat it. During a session with data, compare bid/ask and five-second last against
the source. Confirm the 1m label, initial backfill, changes within one candle every five seconds,
and a new candle after a minute boundary. Select another member and reload; confirm bounded
in-process history remains. Missing source constituents must remain labeled incomplete. Missing bid/ask capability must say not configured. Source timestamps
and age must remain visible when a feed stops. Ctrl-C the system; confirm the page disconnects and
the listening port closes. Restarting begins empty and requests a fresh bounded backfill; it does not restore a raw-data archive.

Stop for mismatched instrument identity, apparent fabricated continuity, incorrect values,
unbounded resources, or a surviving server after system shutdown. Record a sanitized verdict in
an ignored local result file (for example `data/review/dashboard-result.md`), without secrets or
raw market-data exports. Offline tests and visual inspection do not award connected acceptance.

## Evidence and limits

The chart receives acquisition-owned derived minute snapshots with decimal OHLCV strings,
source counts, status, and exact close timestamps. Chart labels use the minute opening time in
UTC. A forming candle updates on source arrivals, not a wall-clock timer. COMPLETE requires all
twelve unique five-second inputs. INCOMPLETE means the source has passed the close with missing
inputs; no synthetic candles or volumes fill gaps. The current source age remains visible.

The displayed last remains the five-second close; history can populate it before live delivery.
Bid/ask timestamps are independent. Requested and received market-data modes remain distinct.
Historical overlap never replaces an observed live value; conflicts and rejected source counts
are retained in the API. Later history can repair an incomplete derived candle, and SSE delivers
same-time changes and older inserts. The browser merges, sorts and trims these projections while
preserving the visible range when follow-live is off. It does not calculate OHLCV. There is no
provider revision policy change or durable raw market-data storage.

Server failures remain local and are logged; port conflicts require correcting configuration and
restarting the system. Dashboard membership is immutable for a run. Chart state is capped, but
maximum-setting throughput and connected recovery have not been measured. Existing acquisition
recovery limitations still apply. No trading, analytics or broker action is added.

## Nautilus Alignment Matrix

Inspected installation: **NautilusTrader 2.0.0rc4**, refreshed 2026-09-10. The
[nightly documentation](https://nautilustrader.io/docs/nightly/) and
[nightly Python API root](https://nautechsystems.github.io/nautilus_docs/python-api-nightly/)
were retrieved; an individual cached common-API page reported an older version. Exact behavior is
therefore bound to the installed Python signatures and
[tagged rc4 DataActor source](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc4/crates/common/src/actor/data_actor.rs),
not that mismatched cached page.

| Area | Native capability inspected | Decision and bounded verification |
| --- | --- | --- |
| Lifecycle / concurrency | `LiveNode`, `DataActor.on_start/on_stop/on_dispose/on_fault`, actor clock timers | Native actor owns startup/stop; custom HTTP worker receives detached state. Offline LiveNode checks exercise lifecycle. |
| Native market data | `subscribe_quotes`, `subscribe_bars`, `unsubscribe_*`, `on_quote`, `on_bar` | Native methods both register callbacks and issue commands. Acquisition executes these on behalf of the composed consumer after admission. No second provider owner. |
| Message bus | `publish_signal`, `subscribe_signal`; Python MessageBus constructor and `subscribe_any` | Use native signals for typed serialized demand/membership. Do not construct another MessageBus: the Python constructor registers a thread-local bus, and generic handlers are not native typed handlers. |
| Cache / state | Native cache and normalized QuoteTick/Bar identity | Acquisition keeps instrument readiness. Bounded presentation history is explicitly transient; no new canonical market state. |
| Aggregation / indicators | Native composite time bars and partial-state surfaces | The rc4 timer failed the measured IB close-boundary case and exposes no Python partial builder. Acquisition owns the narrow source-time minute extension; see the detailed native gate. |
| Historical requests / catalog | Existing native historical planner/executor and request_bars | Reuse for bounded initial five-second history; no catalog/archive. |
| Persistence | Existing operational persistence actor | No new schema or persisted market observations. |
| External projection | No native HTTP browser presentation surface | Approved FastAPI + SSE worker and Lightweight Charts UI; loopback only, local assets. |

Configuration, admission/release, bounded state, HTTP selection, native lifecycle, and browser
behavior are offline checks. Provider subscription deduplication, connected callback delivery,
entitlements, received mode, session continuity, and shutdown under actual provider load remain
outside that evidence.

## Original POC verification record

The offline V2 suite passes **530 tests**, with two PostgreSQL tests excluded from the offline
command. The dashboard's 19 checks cover bounded state/configuration, native attachment/release,
HTTP and SSE lifecycle, reconnect and slow-client bounds, port conflicts, and operational readiness
notification. The native Discord actor uses a mocked HTTP sender; no real webhook is called.

Browser inspection verified instrument selection, search, live synthetic updates, reload, compact
dark styling, white up candles, deeper red down candles, and the requested label removals. Markeitect
approved the POC presentation. This does not establish connected-provider delivery or failure recovery.

Lint, API documentation checks, and system-diagram source/configuration census are required before
publication. Test fixtures now reflect the seven-instrument example, and single-calendar delivery
checks use an isolated test configuration instead of the removed runtime profile. Generated diagrams
use the current tracked profiles. An offline `system build --dashboard` succeeds with seven
instruments and reports `connected=false`. PostgreSQL integration is exercised by the isolated CI job.

The two upstream Starlette/httpx/AnyIO deprecation warnings remain dependency debt. Connected
IB/Discord acceptance remains Markeitect's run using the procedure above.

## One-minute live verification

The implementation uses the same production planner, acquisition executor, candle helper,
dashboard and HTTP/SSE path in `tests/dashboard/live_minute.py`. Its diagnostic startup skips
durable audit and calendar synchronization and supplies reviewed ES membership; this is not
full-system startup acceptance. With explicit authorization it uses client 21 and port 8766
alongside the running system. The first successful run fetched 252 source bars, observed 15
same-candle HTTP changes and two live minute closes. All 22 complete historical/live minute
comparisons matched their twelve source inputs. Browser inspection confirmed forming updates,
fit/follow, reload retention and no console errors. The probe and HTTP listener stopped cleanly.

Only one-minute ES delivery was measured. The other requested timeframes, backward-loading pages,
and datetime selectors remain the next increment. Session-aligned 4h/daily bars require their
separate boundary contract; this UTC-minute helper does not silently define them.

The final startup-tail run fetched 252 initial plus 24 tail observations, received 22 live
inputs, and exposed 21 same-candle HTTP changes over 108.11 seconds. Both live minute closes
and all 22 complete historical/live candles matched their twelve constituents. Its sanitized
result is `data/review/live-minute-dashboard-final.json`. A prior membership-only run correctly
marked a missing startup input incomplete; the tail request supplies real history for that gap.
A subsequent source-counter fix separates native duplicate detection from the derived latest-price
projection; focused checks cover that callback ordering. The chart arithmetic and history path
were unchanged by that counter fix.

For local review, stop your currently running system with Ctrl-C in its terminal, then run:

```bash
.venv/bin/markeitech system run --config config/system.example.toml --dashboard --connect I_UNDERSTAND_THIS_CONNECTS_TO_IB
```

Use the current uncommitted `dashboard-native-backfill-check` checkout. Open port 8765 and verify
all enabled members, history status, forming updates and minute boundaries. Stop with Ctrl-C.
The existing production process was left running throughout development; only the isolated
client-21/port-8766 diagnostics were started and stopped by the agent. This is ready for Markeitect's
full-system local review; no commit, push or PR was made.

## Older history and UTC date selection

The **Older** button requests a page before the earliest loaded minute. Dragging/scrolling to the
left edge also requests one page per user interaction; installing a result never recursively
fetches more pages. Page duration is elapsed time, so a closed-market page can legitimately return
no bars; the next Older action advances to the preceding window. Large gaps are not filled.

**From** and **To** are explicitly UTC, regardless of the browser's local timezone. **Show** loads
the half-open range `[From, To)` in sequential bounded pages. The end must be a completed minute;
the range is limited to `candles_per_instrument` elapsed minutes. **Follow live** leaves the date
window and restores current runtime candles. The watchlist keeps receiving live prices while a
past range is displayed. Chart pages and live candles remain bounded in browser memory.

`POST /api/history` accepts only `instrument_id`, `start`, and `end` (Unix seconds on minute
boundaries). It returns a UUID-correlated pending job. `GET /api/history/{request_id}` returns its
state and detached candles. Same-origin/Host checks, JSON size bounds, configured membership,
page duration, future-time rejection, queue capacity, finite lifetime, and a per-process admission
budget apply. A full queue returns 429; expired results return 404. Retry is an explicit new
operator action. No provider calls occur in the HTTP worker.

DashboardActor republishes unacknowledged demand through the existing native historical planner.
The request uses `recent_completed` anchored at the selected past end, giving exact UTC bounds
without requiring a new calendar resolver. DataAcquisitionActor owns the native request, validates
the response, and projects a one-minute page from its five-second constituents. A separate result
mailbox returns it to HTTP. Pages do not evict the acquisition live book; matching live candles
win at the browser display boundary. Request metadata is bounded by the session admission budget;
raw inputs are discarded after projection, with no new persistence or dependencies.

Verification on 2026-09-10 used the same isolated ES/client-21/port-8766 diagnostic with
`--check-history-pages`. The run passed in 66.76 seconds: 13 forming-candle changes, two live
minute closes, and a two-minute page older than initial history. Every compared complete candle
matched its twelve source inputs. During that run the browser also loaded 13:00–13:02 UTC and a
60-minute Older page, displayed live prices while viewing the past, and returned with Follow live;
no browser errors were reported. Evidence: `data/review/live-minute-history-navigation.json`.
Automatic left-edge triggering and instrument changes during a pending page remain manual review
items; the bounded server/actor request paths and exact correlation have focused tests.
This is isolated provider/data-path evidence, not full production startup acceptance.

The 2026-09-14 completion review added a focused re-fetch fix: each explicit operator page has a
UUID-scoped execution identity, so a completed historical window can be requested again after its
HTTP result expires. Redelivery/retries retain that intent's identity and exact provider bounds.
This fix passed the existing compiler/executor integration test; the September 10 provider run
predates it. The web queue also rejects expired intents before they reach the actor.

## September 14 startup log review

The operator's runs at 19:28 and 19:29 UTC exposed a signal-routing defect. On the installed
NautilusTrader 2.0.0rc4, subscribing to `markeitech.watchlist.membership` also delivers
`markeitech.watchlist.membership.request`. The dashboard published the latter with the value
`DASHBOARD`. Discord previously parsed this unknown signal as system health; persistence rejected
it as an unsupported operational record and published a component failure. System control then
entered `FAILED` before startup readiness. This did not demonstrate a PostgreSQL or HTTP outage:
the later run stored 251 accepted records without worker failures and delivered Discord HTTP 200.

The request channel is now `markeitech.watchlist.request_membership`, outside the membership-event
prefix. Dashboard and Watchlist share that definition for publication, subscription, dispatch,
and unsubscribe. The response remains `markeitech.watchlist.membership`. No compatibility alias
publishes the old request channel. This internal transient-channel rename takes effect on system
restart and requires no durable-data migration or operator configuration change.

Both consumers also check exact signal identity before parsing. Persistence admits only its
registered audit/request contracts; Discord parses system health only on the exact health signal.
Invalid payloads on admitted contracts still follow their existing rejection paths. These checks
are defensive dispatch; the channel rename prevents the unintended native delivery itself.
Provider ownership, dependencies, persistence policy, and topology remain unchanged.

Native alignment was refreshed on September 15 against the nightly guide/API roots and the
installed rc4. The [nightly Common API](https://nautechsystems.github.io/nautilus_docs/python-api-nightly/common.html)
currently displays rc5, so an offline rc4 native-node reproduction governs this fix. Native signal
pub/sub remains the existing transport; custom data, cache, and durable storage are not needed
to repair routing. The regression test uses the production Watchlist response handler after
fixture-supplied audit readiness, plus unfiltered native subscribers representing Dashboard,
Discord, and persistence. Each receives exactly one membership response and no request.

| Requirement | Native candidate | Installed-version evidence | Adapter/provider evidence | Semantic fit | Proposed owner | Decision | Rejection or extension rationale | Acceptance evidence |
|---|---|---|---|---|---|---|---|---|
| Keep membership requests distinct from audit facts and health | `DataActor.subscribe_signal` / `publish_signal` and `Signal.name` | rc4 delivers the old request to membership-prefix subscribers; the renamed request reaches only its intended subscriber in the routing fixture | No provider involved; reproduced without clients | Separate request/event names on native transport, plus defensive exact dispatch | Existing Dashboard, Watchlist, Discord and persistence actors | USE_NATIVE | Move the request outside the event prefix; retain the existing native bus and validated response | Unfiltered subscribers receive only the membership response; offline boot reaches readiness; malformed admitted events remain rejected; operator restart remains unverified |

Other observed conditions remain separate:

- IB error 420 denied SPY/AMEX and QQQ/ISLAND real-time bars in the first run; QQQ was explicitly
  denied again in the later run. Neither stock received live observations in that later run.
  Their historical responses ended 15 minutes before the requested endpoint. Historical data
  availability therefore does not establish live API entitlements or freshness.
- The first run's native adapter reported six timestamp parse failures on
  `20260914-17:57:20` (expected `YYYYMMDD HH:MM:SS TZ`), plus a CL historical request interrupted
  by notice 165 reporting an HMDS connection. These became empty native responses and degraded
  historical readiness. The later run returned history for all seven instruments and completed
  an ES Older page with 720 observations. The adapter parsing/notice issue is not fixed by this
  dispatch change; the logs do not establish why the restart succeeded.
- IB error 300 appeared immediately after rejected live subscriptions (missing ticker ID).
  The ordering is consistent with cleanup of a rejected subscription; that cause is an inference.
- Host resource health reported 6.36% free disk space, about 29.3 GB, and entered `WARNING`.
  No files or resource thresholds were changed.

For local review, restart with the existing run command and inspect fresh log timestamps.
The membership request should no longer produce `invalid_operational_event`, `DISCORD_HEALTH_REJECTED`,
or a consequent false global `FAILED`. Genuine provider and resource errors must remain visible.
All verification of this repair uses offline fixtures; no IB, Discord, or PostgreSQL run was made.
