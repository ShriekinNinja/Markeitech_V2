# Operator Context Log Guide

This guide explains the human-readable messages produced around
`MarkeitechMarketDataActor` during warmup and live operation. The operator log is
an observability surface: it summarizes the current analytical state, but it is
not a signal, an order instruction, or the canonical persistence layer.

Signal lifecycle console messages are documented in the
[operator signal log guide](operator-signal-logs.md). Do not interpret the
Direction score in these context lines as a durable signal transition.

## `MARKET_EVENT`

Example:

```text
MARKET_EVENT | event=FEATURE_COMMITTED | instrument=NQU6.CME | aggregate=NQU6.CME:market_context:1m | sequence=812 | payload_id=<feature-id>
```

This line proves that a durable feature commit crossed the bounded worker-to-
event-loop bridge and was consumed through the Nautilus message bus. It does
not duplicate the feature payload and is not a new analytical calculation.

- `aggregate` identifies the instrument, feature family, and timeframe.
- `sequence` is the SQLite-assigned durable feature commit order.
- `payload_id` identifies the canonical feature snapshot in persistence.
- Missing sequence numbers can reflect bus saturation or shutdown discard; the
  durable feature remains authoritative and recoverable.

`MARKET_EVENT_RUNTIME | event=STOPPED` summarizes accepted, published,
rejected, scheduling-failure, publication-failure, and duplicate counts.
Duplicates are expected from idempotent durable resubmission and are suppressed
by the projection actor's bounded identity window. Any nonzero
failure or rejection count is logged as a warning and requires review before
the event spine is treated as complete operational evidence.

## Log Envelope

The local runtime writes Nautilus JSONL logs under `data/logs/` while also
printing a readable console stream. A JSONL record contains the timestamp,
level, component, and message. The message begins with a stable type token such
as `OPERATOR_CONTEXT` or `ANALYTICS_READY`.

General conventions:

- Timestamps and `as_of` values are UTC unless the message explicitly names a
  timezone.
- Prices use the instrument's native price units.
- `n/a` means the value is not available for the current window. It does not
  mean zero.
- `WARMUP` describes analysis built from boot-time historical requests.
- `LIVE` describes the change-aware report emitted after live subscriptions
  begin.
- `ACTIVE` is the one instrument receiving tick-by-tick data.
- `BACKGROUND` instruments receive live 1-minute bars and are analytically
  equal participants in the report.
- The active instrument is printed first, followed by background instruments
  in instrument-id order.

The warmup report is always complete. Live reports run on the configured
interval, one minute by default, and include only instruments whose snapshot or
role changed. Each included instrument has three context lines:
`OPERATOR_CONTEXT`, `OPERATOR_LEVELS`, and `OPERATOR_AUCTION`. The block also
includes one cumulative `OPERATOR_FLOW` fidelity line for the active instrument.

## Normal Startup Order

A healthy boot normally reads as follows:

1. `[REQ]--> RequestBars` requests historical bars.
2. `Received <Bar[n]> data` confirms each response.
3. `WARMUP_RETRY` appears only for an empty or timed-out request.
4. `ANALYTICS_READY` reports readiness for every configured instrument.
5. `OPERATOR_CONTEXT_BEGIN | phase=WARMUP` opens the warmup briefing.
6. Three operator lines are printed for each instrument.
7. `OPERATOR_CONTEXT_COMPLETE | phase=WARMUP` closes the briefing.
8. `[CMD]--> Subscribe...` messages show live subscription requests.
9. `LIVE` operator blocks appear when context changes.

## `WARMUP_RETRY`

Example:

```text
WARMUP_RETRY | ESU6.CME-1-DAY-LAST-EXTERNAL | attempt=2/3 | reason=empty_or_timed_out_response
```

This message means a required historical request returned no usable bars before
its timeout. The actor retries the same request up to the displayed maximum.

- The value after the first separator is the Nautilus bar type.
- `attempt` is the next attempt and configured maximum.
- `reason` currently combines empty responses and response timeouts.
- Repeated exhaustion can block analytics startup.

If the process is interrupted with `SIGINT` during warmup, pending callbacks may
briefly produce retry messages while shutdown completes. In that case, use the
surrounding lifecycle and shutdown messages to distinguish an operator stop
from an IB data failure.

## `ANALYTICS_READY`

Example:

```text
ANALYTICS_READY | NQU6.CME | status=READY | 1d=current/full/bars:251/lag:0 | 1h=current/full/bars:251/lag:0 | reasons=all_timeframes_current_and_full_depth
```

This is a boot-time quality gate for the historical analytical inputs. It is
not a directional opinion or trading signal.

Instrument status:

- `READY`: every configured timeframe is current and has full indicator depth.
- `DEGRADED`: 1-minute data is current and all required timeframes exist, but
  one or more higher timeframes are stale or below full depth.
- `BLOCKED`: a required timeframe is unavailable, or 1-minute data is missing
  or stale by more than one completed interval. Live subscriptions do not
  proceed through this gate.

Exactly one stale 1-minute interval is `DEGRADED` with reason
`one_minute_startup_lag_tolerated`. This bounded tolerance handles a sequential
warmup crossing a minute boundary without hiding a larger outage or fabricating
the missing bar.

Each timeframe has the form:

```text
<timeframe>=<freshness>/<depth>/bars:<count>/lag:<intervals>
```

- Freshness is `current`, `stale`, or `unavailable`.
- Depth is `full` at 200 or more completed bars, `partial` from 50 through 199,
  and `insufficient` below 50.
- `bars` counts completed historical bars accepted for that timeframe.
- `lag` counts missing completed intervals. The currently forming interval is
  not treated as late.
- `reasons` contains stable machine-readable reason codes for the aggregate
  instrument status.

## `OPERATOR_CONTEXT_BEGIN`

Example:

```text
OPERATOR_CONTEXT_BEGIN | phase=LIVE | instruments=2
```

This is the boundary at the start of one coherent human-readable report.
`instruments` is the number included in this block, not necessarily the full
watchlist. Warmup forces all instruments into the block; a live block contains
only changed instruments.

## `OPERATOR_CONTEXT`

Example:

```text
OPERATOR_CONTEXT | phase=LIVE | role=ACTIVE | NQU6.CME | price=29605.00 | direction=+1 | location=upper_value | TREND[1d=BULLISH 1h=BULLISH 15m=RANGE 5m=BEARISH 30m=RANGE 1m=BEARISH] | as_of=2026-07-14T09:45:00+00:00
```

Fields:

- `phase`: `WARMUP` or `LIVE`.
- `role`: `ACTIVE` or `BACKGROUND`.
- Instrument id: explicit contract and venue, for example `NQU6.CME`.
- `price`: close of the 1-minute reference snapshot, or the shortest available
  timeframe if 1-minute context is absent.
- `direction`: deterministic signed context score from `-2` through `+2`. It
  summarizes direction and location evidence; it is not an entry signal.
- `location`: price relative to the current full-session value area. Values are
  `below_value`, `lower_value`, `at_poc`, `upper_value`, `above_value`, or
  `unavailable`.
- `TREND`: top-down trend classification. A timeframe can be `BULLISH`,
  `BEARISH`, `RANGE`, or `INSUFFICIENT_DATA`.
- `as_of`: close time of the reference snapshot.

Conflicting trends across timeframes are intentional information. For example,
a bearish 1-minute pullback can coexist with a bullish daily and hourly regime.

## `OPERATOR_LEVELS`

Example:

```text
OPERATOR_LEVELS | phase=LIVE | role=ACTIVE | NQU6.CME | SESSION[29320.00/29649.75 @86.5%] | PRIOR[29110.00/29420.00] | VWAP[29478.00 above] | S/R[1d=29250.00/29700.00 1h=29540.00/29650.00 15m=29580.00/29635.00 5m=29595.00/29620.00]
```

Fields:

- `SESSION[low/high @position]`: current product-session range and the current
  price's normalized position. `0%` is the session low and `100%` the high.
- `PRIOR[low/high]`: completed prior product-session range.
- `VWAP[price position]`: full product-session VWAP and whether current price is
  `above`, `below`, `at`, or `unavailable` relative to it.
- `S/R`: nearest confirmed swing support and resistance for `1d`, `1h`, `15m`,
  and `5m`. Each pair is `support/resistance`; either side can be `n/a` when no
  confirmed swing exists on that side of price.

These are analytical references, not stop, target, or order recommendations.

## `OPERATOR_AUCTION`

Example:

```text
OPERATOR_AUCTION | phase=LIVE | role=ACTIVE | NQU6.CME | PROFILE[current=29410/29595/29637:inferred prior=29140/29280/29400:inferred london=29390/29435/29480:inferred new_york=n/a] | COMPOSITE[2s=29220/29410/29610:inferred:developing 5s=28980/29250/29590:inferred:developing] | RANGES[london=29380/29500:complete new_york=n/a] | OR[L15=29380/29420:complete L30=29380/29460:complete NY15=n/a NY30=n/a] | FVG[1d=none 1h=bullish:29420-29440 15m=none 5m=bearish:29610-29618] | input=inferred:classified_ticks
```

### Profiles

`PROFILE` values are encoded as:

```text
VAL/POC/VAH:fidelity
```

- `VAL` and `VAH` bound the 70% value area.
- `POC` is the price bin with the greatest inferred volume.
- `current` covers the calendar-resolved current product session.
- `prior` covers the last completed product session.
- `london` covers 08:00 through 11:30 `Europe/London`.
- `new_york` covers 09:30 through 16:00 `America/New_York`.

Session anchors are timezone-aware and move correctly with daylight-saving
rules. Do not hard-code the local Israel equivalent when validating a session.

Current profiles are candle-derived estimates using
`bar_range_uniform_volume`: each 1-minute bar's volume is distributed uniformly
across price bins intersecting its high-low range. They are therefore marked
`inferred`. They are not footprint, bid/ask, or trade-at-price profiles.

### Composite Profiles

`COMPOSITE` uses the form:

```text
<count>s=VAL/POC/VAH:fidelity:<state>
```

`2s` and `5s` are rolling two-session and five-session product profiles,
including the current session. They are `developing` until the current session
closes. Exact session counts are required; a profile is not silently produced
from fewer sessions.

### Ranges And Opening Ranges

- `RANGES` reports London and New York low/high with `developing` or `complete`.
- `OR` reports the first 15 and 30 minutes of London (`L15`, `L30`) and New York
  (`NY15`, `NY30`).
- A window that has not started is normally `n/a`.

### Fair Value Gaps

`FVG` reports active gaps for `1d`, `1h`, `15m`, and `5m`:

```text
<direction>:<lower>-<upper>
```

The engine confirms three-bar bullish or bearish gaps, removes them after they
are filled, and displays at most the two active gaps nearest current price per
timeframe. Nearest does not necessarily mean newest.

### Input Fidelity

The final field describes the reference snapshot's incoming bars:

- `reported:ib`: bars reported directly by Interactive Brokers.
- `inferred:classified_ticks`: active-instrument 1-minute bars classified and
  built from the tick stream.
- `mixed:mixed`: a higher-timeframe bar spans persisted/provider history and a
  tick-built live suffix, commonly across a restart boundary.

Profile fidelity remains `inferred` even when the surrounding snapshot input is
`reported:ib`, because candle bars do not contain volume-at-price distribution.

## `OPERATOR_FLOW`

Example:

```text
OPERATOR_FLOW | role=ACTIVE | NQU6.CME | trades=2012 | classified=1890 | unknown=122 | volume=2834 | classified_volume=2668 | unknown_volume=166 | classified_ratio=94.14% | reasons=at_or_above_ask:955,at_or_below_bid:935,inside_spread_tick_rule_unchanged:112,no_quote_at_or_before_trade:10
```

This cumulative line describes active tick-classification fidelity since the
current process started. It is observation quality, not directional evidence.

- `trades`, `classified`, and `unknown` count trade messages.
- `volume`, `classified_volume`, and `unknown_volume` use the provider-reported
  trade sizes and therefore need not have the same ratio as the message counts.
- `classified_ratio` is classified volume divided by total observed volume.
- `reasons` accounts for every trade using stable classification outcomes.
  Quote failures distinguish no received quote, no quote event at or before the
  trade, stale quote, and instrument mismatch. Inside-spread outcomes distinguish
  tick-rule direction from unavailable or unchanged references.

Quotes are selected only from messages already received by Markeitech. Because
IB trade and quote streams can arrive out of event-time order, the router keeps
a bounded quote history and selects the most recently received quote whose
event timestamp is not after the trade. The existing two-second freshness gate
still applies. This prevents event-time lookahead without discarding a trade
merely because the latest-arrived quote is future-dated relative to it.

## `OPERATOR_CONTEXT_COMPLETE`

Example:

```text
OPERATOR_CONTEXT_COMPLETE | phase=LIVE
```

This closes the report block. Its absence after a `BEGIN` usually means the
process was interrupted while writing the block. Consumers should use the begin
and complete markers rather than assuming every neighboring log line belongs
to the report.

## `MARKET_CONTEXT_EVENT`

Example shape:

```text
MARKET_CONTEXT_EVENT | phase=LIVE | {"schema_version":1,"instrument_id":"NQU6.CME",...}
```

This DEBUG-only message contains the complete versioned
`MarketContextSnapshot` JSON for every calculated snapshot. Normal INFO logging
suppresses it to keep live logs readable. Enabling global DEBUG also exposes
substantial Nautilus and IB detail, so use it as a temporary diagnostic rather
than a normal operator view. The log file is not a substitute for canonical
market-data or feature persistence.

## Nautilus Request And Subscription Messages

The following messages are generated by Nautilus around actor calls. They are
useful lifecycle evidence but are not Markeitech analytical report types.

### `[REQ]--> RequestBars`

Shows a historical request, including bar type, UTC start/end, and data client.
Use it to verify the requested contract, timeframe, and lookback window.

### `Received <Bar[n]> data`

Confirms the number of bars delivered for a historical request. Read it
together with `ANALYTICS_READY`; a nonzero response can still be stale or too
shallow for full-depth analytics.

### `[CMD]--> SubscribeTradeTicks`, `SubscribeQuoteTicks`, And `SubscribeBars`

Shows the live subscriptions requested by the actor. The active instrument
receives tick subscriptions; background instruments receive 1-minute bars.
Subsequent `Subscribed ...` messages confirm that the data client accepted the
request. Acceptance does not guarantee that the market is currently producing
events.

## Reading One Report

Read each instrument's three lines in order:

1. `OPERATOR_CONTEXT`: top-down regime, current price, direction, and auction
   location.
2. `OPERATOR_LEVELS`: session geometry, VWAP, and nearby structural levels.
3. `OPERATOR_AUCTION`: profiles, regional ranges, opening ranges, fair value
   gaps, and data lineage.

Confirm that `as_of` is current before acting on any interpretation. Background
instruments are as important as the active instrument analytically; `ACTIVE`
only identifies the higher-resolution ingestion path.

## Visual Validation

Screenshots are welcome whenever they can confirm analytical values or reveal a
definition mismatch. Record or show the following with each comparison:

- instrument and exact contract;
- feed and platform;
- chart timezone;
- exact start and end timestamps;
- regular, extended, or product-session setting;
- fixed-range versus visible-range study;
- value-area percentage;
- row size or price-bin size; and
- whether the study uses actual volume-at-price or candle approximation.

TradingView and Tradovate are useful deterministic references when their study
settings and window are visible. Bookmap and order-flow streams provide valuable
live auction context, but they do not directly validate a historical
candle-derived profile unless contract, feed, delay, and window are aligned.

## Troubleshooting

| Observation | Interpretation or next check |
| --- | --- |
| `BLOCKED` readiness | Inspect each timeframe for unavailable or stale 1-minute data. |
| `DEGRADED` readiness | Live analysis can start, but one or more higher timeframes are stale or below 200 bars. |
| Repeated `WARMUP_RETRY` | Check IB historical-data availability, pacing, and connection state. |
| Retry messages immediately after `SIGINT` | Likely pending warmup callbacks during operator-initiated shutdown; inspect surrounding lifecycle lines. |
| London or New York values are `n/a` | The window may not have started, or no usable bars exist for it yet. |
| Profile differs from a chart | Match contract, exact window, session anchor, 70% value area, price bins, and allocation methodology. |
| Active input remains `reported:ib` | The report may still reflect warmup, or no completed tick-built 1-minute bar has advanced context yet. |
| A live block repeats some values | At least one snapshot field changed; every displayed field need not change. |
| No live operator block | No instrument context changed, the market produced no completed input, or the report timer is disabled. |
| `BEGIN` without `COMPLETE` | The process was interrupted during the report block. |

## Filtering JSONL Logs

Show messages from the actor component:

```bash
jq -r 'select(.component == "MarkeitechMarketDataActor") | .message' data/logs/*.jsonl
```

Show only operator report blocks:

```bash
jq -r 'select(.message | startswith("OPERATOR_")) | .message' data/logs/*.jsonl
```

Find readiness failures and warmup retries without parsing JSON:

```bash
rg 'ANALYTICS_READY|WARMUP_RETRY' data/logs/
```
