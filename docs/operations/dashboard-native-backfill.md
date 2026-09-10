# Dashboard native backfill live check

## Scope and status

The initial investigation below is a diagnostic for the requested dashboard timeframes, on branch
`dashboard-native-backfill-check`, based on merged POC commit
`af25f09ae80403b0f5421157cfc54cc85a8e5d6c`. Markeitect explicitly requested a live check
and uncommitted local review. The approved follow-up implements the one-minute chart in this checkout; higher timeframes
and the timeframe selector remain deferred. The pre-existing running dashboard was not restarted.

The question is whether the installed native engine can fetch IB five-second history,
seed a one-minute aggregate, and continue correctly with live five-second bars, including
exposing changes before the minute closes. The bounded case is ESU6.CME and one-minute
bars. Other timeframes, session boundaries, scrolling, reconnects, and datetime UI are
outside this measurement.

## Measured result — 2026-09-10

**Native historical backfill passed. The tested live aggregation path did not produce
correct minute candles.** Two bounded connected runs used the default native timer policy.

The first run received 38 historical five-second bars and built three historical minutes;
all three matched their complete source inputs. It received 21 live inputs and two native
minute outputs. Its first live minute mismatched; the probe stopped before the second
minute's final source input arrived, leaving that comparison incomplete. That observation
prompted a timing run which waits for the closing source input before stopping.

The timing run lasted 73.91 seconds and received 45 historical bars, three matching historical
minutes, 15 live five-second bars, and two live minutes. Both live comparisons had all twelve
source inputs. There were zero duplicate inputs, duplicate target timestamps, or five-second
gaps across the observed history/live sequence.

| Minute close (UTC) | Native target callback after close | Final 5s callback after close | Comparison against all twelve inputs |
| --- | --- | --- | --- |
| 2026-09-10 14:31:00 | 3.388 ms | 248.325 ms | Volume mismatched; emitted candle exactly matched the eleven inputs available before the final input |
| 2026-09-10 14:32:00 | 4.911 ms | 288.049 ms | Open, close and volume mismatched |

These callback times establish that the native target arrived before its final constituent.
The inspected live timer resets the builder at emission, while historical aggregation
processes an input exactly at the boundary before emission. This explains the observed
timing failure; assigning a prior minute's late input to the following minute is consistent
with that implementation. This result is specific to the tested rc4 path and configuration,
not a claim that every native aggregation mode fails.

There were **zero same-candle OHLCV mutations** across 289 cache samples in the timing run.
Thus this completed-bar cache did not supply the requested actively changing candle.
That observation does not prove the absence of every possible native extension surface.

Both probe nodes stopped. A socket check confirmed that the pre-existing system process
still owned its IB connection and port 8765, with no remaining probe connection. Neither
run restarted the dashboard or sent Discord/model messages.

Local evidence: `data/review/native-backfill.json` and
`data/review/native-backfill-timing.json`. Both runs exited with status 1 because live
correctness did not pass. The repeatable probe and this report are left uncommitted.

## Live procedure

The manual probe uses a diagnostic `DataAcquisitionActor` subclass. Every native history
and subscription request originates there. Its isolated lifecycle does not start production
acquisition audit, database, Discord, or execution components. It creates a separate native
LiveNode and IB data client; it does not attach a second actor to the running system.

Run only with explicit authorization for the selected live connection. Check that the
chosen client ID is unused; the probe rejects the configured system client ID but cannot
discover all clients registered at IB. The measured run used client 21 alongside the existing
client 20 on loopback port 4002.

```bash
.venv/bin/python -m tests.dashboard.live_backfill \
  --config config/system.example.toml \
  --instrument ESU6.CME \
  --client-id 21 \
  --timeout-seconds 140 \
  --output data/review/native-backfill-timing.json \
  --connect I_UNDERSTAND_THIS_CONNECTS_TO_IB
```

The probe requests one recent bounded history window, then subscribes to the external
five-second bars and native composite minute bars. It stops after two minute closes and
receipt of their final source bar, or the deadline; node shutdown has a further 40-second
deadline. Ctrl-C requests cleanup. Output contains counts, timestamps, and comparisons;
raw OHLCV stays transient in memory. `data/review/` is ignored by Git.
Exit 0 requires complete, matching historical and live candle comparisons, no observed gaps
or duplicates, and a stopped node. Forming-candle observations are a separate report field.

The comparison uses exact decimals and the twelve source bars whose close timestamps fall
in `(minute close - 60 seconds, minute close]`. It checks open, high, low, close, and summed
volume. No provider one-minute candle is substituted for this reference: IB historical and
realtime filtering can differ. Incomplete coverage cannot establish a correct minute.

## Follow-up live result

The production one-minute data path now passes the isolated ES diagnostic in
`tests/dashboard/live_minute.py`: 252 initial history observations, 24 one-time tail observations,
22 live inputs, 21 same-candle HTTP changes, and two live minute closes in 108.11 seconds.
All 22 COMPLETE candle comparisons matched twelve constituent bars exactly. The tail request
repairs the small startup subscription gap using native history; no synthetic input is inserted.

The production historical compiler/executor, acquisition candle helper, dashboard and HTTP/SSE
run unchanged in that diagnostic. Startup audit, membership delivery and calendar synchronization
are explicitly isolated fixtures, so this is not full production startup acceptance. The browser
showed forming updates, retained backfill after reload, fit/follow controls and no console errors.
The final evidence is `data/review/live-minute-dashboard-final.json`; both node and server stopped.
A later focused fix keeps native duplicate counters separate from derived latest-price updates;
it does not change the measured candle arithmetic or history requests.

## Native contract and remaining work

### Approved next implementation batch

Following the live findings, Markeitect approved the next one-minute dashboard increment in
this task, still uncommitted. `DataAcquisitionActor` will own a bounded source-time candle helper;
`DashboardActor` will request recent five-second history through the existing historical planner
and acquisition executor, then project acquisition-owned minute updates. No new actor or provider
client is added to production. The native IB source bars remain unchanged.

The helper groups close-stamped inputs in `(minute start, minute end]`, reports constituent
coverage, and supplies a mutable forming projection. Historical/live overlap is deduplicated by
source timestamp; live observations take precedence with conflicts counted. No empty bars are
invented. UTC minute boundaries apply to this increment; higher/session timeframes remain deferred.

Native extension gate: the installed `nautilus_trader.data` and its native binding expose only
engine configuration, not a Python `BarBuilder`, aggregator, or partial accessor. The standard
live time aggregator failed the measured boundary case. Its build delay shifts output timestamps.
Count-based aggregation cannot establish minute alignment through missing inputs. External IB
minute revisions use a different source subscription. Therefore a narrow source-time helper is
selected for the required forming/complete display contract, while native history, five-second
bars, provider ownership, cache, lifecycle and bus delivery are retained. This rejects those
specific alternatives for this requirement, not Nautilus's other aggregation capabilities.

`DataActor.request_bars` provides bounded start/end/limit requests and delivers through
`on_historical_bars`. The installed engine accepts `params.bar_types` containing the composite
target and `update_subscriptions=true`, preserving native aggregation state for live use.
Bootstrap must precede the target's live subscription: the engine rejects backfilling an
already-running target aggregator. Navigation requests must therefore remain separate from
live aggregate bootstrap.

The tested composite target is
`ESU6.CME-1-MINUTE-LAST-INTERNAL@5-SECOND-EXTERNAL`. Native emitted/cache bars use its standard
form. Cache sampling observes completed output, not a supported partial-builder API.

The native `time_bars_build_delay` option also exists. In the inspected rc4 implementation
it shifts the timer and its emitted event timestamp; setting a delay cannot be assumed to
preserve exact minute labels. It was not changed in the live probe or production config.
The acquisition helper now supplies correct source-time assignment and forming snapshots for
the one-minute dashboard. Higher/session timeframes remain separate work.

## Nautilus Alignment Matrix

| Requirement | Native candidate | Installed-version evidence | Adapter/provider evidence | Semantic fit | Proposed owner | Decision | Rejection or extension rationale | Acceptance evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fetch initial and older history or a datetime window | `request_bars`, `on_historical_bars` | rc4 Python signature and request binding; existing `NautilusHistoricalPort` | rc4 IB request path segments, sorts, deduplicates and limits history | Bounded history fits | `DataAcquisitionActor` | USE_NATIVE | No new provider client or historical fetch engine needed | Recent ES history delivered live; old pages and other timeframes unmeasured |
| Seed aggregates from source history | `params.bar_types`, `update_subscriptions=true` | rc4 request aggregation and cleanup retain native state | Live ES five-second response passed through the native engine | Historical one-minute aggregation fits; live correctness is separate | Native DataEngine, acquisition-owned requests | COMPOSE_NATIVE | Bootstrap is ordered before target subscription; running-target backfill is rejected | Three historical minutes matched all twelve five-second inputs in the first live run |
| Continue completed minute bars from IB five-second delivery | Native composite `TimeBarAggregator` | rc4 live timer emits at the close; historical path processes the boundary input before firing | Two live minutes mismatched despite complete source coverage; final inputs arrived after emission | Native default policy fails tested source-time buckets | DataAcquisitionActor with bounded helper | EXTEND | Close the derived minute only from source coverage; retain native provider delivery and history requests | Both live closes and all 22 complete minute comparisons matched their twelve inputs in the final isolated run |
| Change the current candle every five seconds | Native partial state or revised-bar output | No public Python partial-builder accessor identified; completed cache inspected | External IB longer-bar revisions use a different source subscription | Native candidates do not satisfy the required projection | DataAcquisitionActor with bounded helper | EXTEND | Keep native source bars and fetching; derive only the missing source-time minute projection | 21 same-candle HTTP changes and matching minute constituents in the final isolated live run |
| Scrollback, datetime selectors, retained viewport | Existing dashboard plus native requests | Merged POC has bounded snapshots but no history request UI | Provider request bounds and availability apply | Narrow dashboard extension still needed | Existing dashboard and acquisition | DEFER | This branch implements initial one-minute history and live updates; loading older pages and datetime selection remain later work | Older-page and datetime requests not exercised |

## Sources and freshness

Inspected on **2026-09-10**, installed **NautilusTrader 2.0.0rc4**, targeting nightly
contracts. Both nightly roots were refreshed; an individual common API page reported an
older version, and the data API page was unavailable. Exact conclusions use the installed
interfaces and freshly retrieved tag-pinned source.

- [Nightly guides](https://nautilustrader.io/docs/nightly/)
- [Nightly Python API root](https://nautechsystems.github.io/nautilus_docs/python-api-nightly/)
- [rc4 request aggregation parameters](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc4/crates/data/src/engine/requests.rs)
- [rc4 native engine bootstrap and cleanup](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc4/crates/data/src/engine/mod.rs)
- [rc4 time-bar aggregation and timer timestamps](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc4/crates/data/src/aggregation.rs)
- [rc4 IB historical requests](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc4/crates/adapters/interactive_brokers/src/data/core.rs)
- [rc4 IB realtime bar conversion and delivery](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc4/crates/adapters/interactive_brokers/src/data/core_streams.rs)
- [rc4 IB timestamp conversion](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc4/crates/adapters/interactive_brokers/src/data/convert.rs)
- [rc4 upstream engine tests](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc4/crates/data/tests/engine.rs)

Upstream tests were inspected, not executed. They establish intended native behavior and do
not replace the measured IB case. No dependencies, production settings, persistence schemas,
raw-data retention, or provider ownership were changed by this diagnostic.
