# Dashboard POC — Local Review

The observable outcome is an enabled-watchlist sidebar with latest quotes and completed
five-second candles, and one chart selected from that sidebar. The interface uses neutral dark
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
  TradingView Lightweight Charts 5.2.1 asset. Selection changes the browser projection only.

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

The system configuration schema is **27**. Dashboard policy is version **1**. Copy the commented
`[dashboard]` section from `config/system.example.toml` into your existing ignored local profile,
preserving its machine/provider settings. For schema-25/26 profiles, add `[ib_execution]` and `[risk_engine]` from the tracked example
and set `schema_version = 27`. The dashboard section is optional; omission disables it.
For older profiles, first follow [developer setup](developer-setup.md). Local files are never
migrated automatically.

| Setting | Default | Valid range / meaning |
| --- | --- | --- |
| `policy_version` | `1` | Exactly `1` |
| `enabled` | `false` | Boolean; compose dashboard on startup |
| `port` | `8765` | 1024–65535; host fixed to `127.0.0.1` |
| `maximum_instruments` | `64` | 1–256; reject an enabled watchlist beyond this limit |
| `candles_per_instrument` | `720` | 2–5000; transient completed bars per instrument |
| `publish_interval_ms` | `250` | 100–5000; browser projection cadence |
| `acquisition_retry_interval_ms` | `1000` | 100–10000; membership and attachment retry cadence |
| `maximum_clients` | `4` | 1–16; concurrent SSE clients |
| `shutdown_timeout_seconds` | `5` | 1–30; worker shutdown/join deadline |

The tracked example and operational profiles explicitly enable the dashboard; omission uses the
disabled default. All settings are startup-only, typed and bounded; unknown dashboard fields are rejected.
`--dashboard` enables the dashboard for that invocation without rewriting the TOML. No npm
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
reload, and observe new candles every five seconds. Ctrl-C stops the preview and releases port 8765.
Stop this preview before starting the connected system on the same port.

## Markeitect's connected scenario

Review the dashboard PR on `watchlist-review`. The existing IB/Discord/persistence prerequisites
and explicit connection confirmation apply. Use your reviewed schema-26 local configuration:

```bash
.venv/bin/markeitech system build --config config/system.local.toml --dashboard
.venv/bin/markeitech system run --config config/system.local.toml --dashboard --connect I_UNDERSTAND_THIS_CONNECTS_TO_IB
```

The first command constructs but does not connect the node. The second is **Markeitect-run only**.
The server starts when DashboardActor starts. Open the configured loopback port and confirm all
enabled members appear. Confirm exactly one operational Discord message contains the same
configured dashboard address; refreshing/selecting instruments must not repeat it. During a session with data, compare bid/ask and five-second close against
the source, select another member, confirm incoming completed candles, reload and confirm bounded
in-process history remains. Missing bid/ask capability must say not configured. Source timestamps
and age must remain visible when a feed stops. Ctrl-C the system; confirm the page disconnects and
the listening port closes. Restarting begins with empty candle history.

Stop for mismatched instrument identity, apparent fabricated continuity, incorrect values,
unbounded resources, or a surviving server after system shutdown. Record a sanitized verdict in
an ignored local result file (for example `data/review/dashboard-result.md`), without secrets or
raw market-data exports. Offline tests and visual inspection do not award connected acceptance.

## Evidence and limits

The chart retains provider bar event timestamps and decimal OHLCV strings in its API. JavaScript
converts prices only for rendering. The displayed "last" is explicitly the five-second bar close,
not a trade-tick claim. Bid/ask timestamps are independent. Received realtime/delayed mode is unknown;
the configured requested mode is labeled separately. Duplicate/older completed bars are rejected
and counted; no revision reconciliation, aggregation, gap filling, historical backfill, or durable
market-data storage is introduced. The browser receives conflated projections, not every quote.

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
| Aggregation / indicators | Native bar aggregation and indicator facilities | Not needed: consume existing external five-second bars unchanged. |
| Historical requests / catalog | Existing native historical acquisition owner | Defer backfill/catalog; POC begins collecting at startup. |
| Persistence | Existing operational persistence actor | No new schema or persisted market observations. |
| External projection | No native HTTP browser presentation surface | Approved FastAPI + SSE worker and Lightweight Charts UI; loopback only, local assets. |

Configuration, admission/release, bounded state, HTTP selection, native lifecycle, and browser
behavior are offline checks. Provider subscription deduplication, connected callback delivery,
entitlements, received mode, session continuity, and shutdown under actual provider load remain
outside that evidence.

## Local verification record

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
