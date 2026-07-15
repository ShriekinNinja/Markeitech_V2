# Operator Signal Log Guide

Signal operator logs are a sparse projection of the durable signal runtime. They
do not calculate evidence and are never restart truth. SQLite signal snapshots
and transition history remain authoritative.

These messages are separate from `OPERATOR_CONTEXT`, `OPERATOR_LEVELS`, and
`OPERATOR_AUCTION`. Context lines describe analytical state; signal lines report
runtime presence or a committed lifecycle change.

## `SIGNAL_RUNTIME`

`SIGNAL_RUNTIME` proves that the configured signal consumer exists even when no
setup qualifies.

```text
SIGNAL_RUNTIME | event=HEARTBEAT | status=RUNNING | watermark=2026-07-15T06:00:00+00:00 | restored=0 | revisions=48 | stale=36 | evaluations=4 | writes=0 | open=0 | projection_rejected=0 | projection_errors=0 | render_errors=0
```

Fields:

- `event`: `STARTED`, `HEARTBEAT`, `FAILED`, or `STOPPED`.
- `status`: current managed signal-runtime status.
- `watermark`: startup time. Completed evidence at or before this timestamp may
  rebuild state but cannot create a live setup.
- `restored`: verified open Armed or Triggered signals restored from SQLite.
- `revisions`: committed feature revisions consumed across all instruments and
  timeframes.
- `stale`: pre-watermark evaluation-clock revisions used only for rebuilding.
- `evaluations`: post-watermark definition evaluations.
- `writes`: atomic lifecycle persistence operations, not individual SQL rows.
- `open`: current Armed or Triggered signals.
- `projection_rejected`: signal projections rejected by the bounded queue.
- `projection_errors`: exceptions raised while offering a projection.
- `render_errors`: formatting or log-sink failures isolated by the projector.

Zero lifecycle messages with increasing `evaluations` means the engine evaluated
and no setup changed state. Zero evaluations with increasing revisions usually
means evidence is still rebuilding or no complete definition bundle exists.

## `SIGNAL_ARMED`

Location entry persists the Candidate and immediate Candidate-to-Armed
transition atomically. The operator therefore sees one `SIGNAL_ARMED` line, not
a misleading transient Candidate line.

```text
SIGNAL_ARMED | role=ACTIVE | NQU6.CME | definition=intraday_context | direction=LONG | from=CANDIDATE | location=support@5m:29600-29608 | evidence=D:4,L:2;fidelity=inferred+reported | reason=location_episode_armed | as_of=2026-07-15T13:42:00+00:00 | signal=7ac1e4e9085d | transition=458d74161ba2
```

- `role` is current presentation metadata and is not part of signal identity.
- `location` shows up to three semantic entry zones plus an omitted count.
- `evidence` counts Direction, Location, Aggression, and Follow-through evidence
  stages that are present, followed by their fidelity classes. Triggered and
  terminal observation lines also include `confirmation=tick_aggression` or
  `confirmation=bar_impulse_proxy`; the latter is always partial evidence.
- `signal` and `transition` are shortened display forms of durable identities.

## `SIGNAL_RESTORED`

```text
SIGNAL_RESTORED | role=ACTIVE | NQU6.CME | definition=intraday_context | direction=LONG | from=N/A | location=support@5m:29600-29608 | evidence=D:4,L:2;fidelity=inferred+reported | reason=verified_open_signal_restored | as_of=2026-07-15T13:50:00+00:00 | signal=7ac1e4e9085d | transition=n/a
```

This is recovery evidence, not a new alert. The projector deduplicates the same
restored content within one process, while SQLite verification decides whether
the signal is eligible for restoration.

## `SIGNAL_INVALIDATED`

```text
SIGNAL_INVALIDATED | role=ACTIVE | NQU6.CME | definition=intraday_context | direction=LONG | from=ARMED | location=bullish_fvg@15m:30009.5-30027.75 | evidence=D:5,L:2;fidelity=reported | reason=location_adverse_breach_confirmed | as_of=2026-07-15T13:48:00+00:00 | signal=7ac1e4e9085d | transition=a963bc6b7fd1
```

Invalidation means the setup thesis ended before normal observation expiry. The
terminal `reason` is essential:

- `location_adverse_breach_confirmed` means configured consecutive closes
  crossed beyond every original entry zone's adverse tolerated edge.
- `location_episode_replaced` means a wholly disjoint qualified Location became
  the active opportunity.
- Direction-regime invalidation requires a newly fully qualified opposite
  Direction. Neutral, conflicted, vetoed, or missing Direction blocks Trigger
  but does not emit this line.

Favorable departure and unresolved displacement preserve the Armed signal and
therefore do not emit a lifecycle transition line.

## `SIGNAL_TRIGGERED`

```text
SIGNAL_TRIGGERED | role=ACTIVE | NQU6.CME | definition=intraday_context | direction=LONG | from=ARMED | location=support@5m:29600-29608 | evidence=D:4,L:2,A:1,F:1;fidelity=inferred+reported;confirmation=tick_aggression | reason=aggression_and_follow_through_confirmed | as_of=2026-07-15T13:45:00+00:00 | signal=7ac1e4e9085d | transition=be78f819b6a0
```

This line will be enabled by Stage 5D lifecycle wiring. `confirmation` names the
actual evidence method. Active classified-tick confirmation and background
bar-impulse confirmation must never be silently substituted for each other.

## `SIGNAL_EXPIRED`

```text
SIGNAL_EXPIRED | role=BACKGROUND | ESU6.CME | definition=intraday_context | direction=LONG | from=ARMED | location=support@15m:7600-7602 | evidence=D:4,L:2,A:1,F:1;fidelity=partial+reported;confirmation=bar_impulse_proxy | reason=armed_observation_window_expired,bar_proxy_pace_below_threshold | as_of=2026-07-15T13:47:00+00:00 | signal=cbe0479be4f2 | transition=7b58038e0c71
```

Expiry means the configured number of completed observations elapsed without a
qualified confirmation. It is not invalidation and it is not measured by wall
clock. Terminal unavailable or failed-window evidence remains attached so the
operator can distinguish absent input from a measured threshold failure.

## Observation Logs

Committed one-minute bars do not emit one signal log line per bar. They are
retained in a bounded source-specific observation store and become evidence only
through a lifecycle decision. This keeps signal logs sparse. Observation-store
health counters will join `SIGNAL_RUNTIME` when Stage 5D runtime coordination is
wired; until then, Triggered and Expired examples above describe reserved output
rather than active behavior.

## Failure Semantics

The projector uses a bounded non-blocking queue and bounded dedupe memory.
Formatting or log-sink failure increments health counters but does not stop
ingestion, feature persistence, or signal evaluation. A rejected projection is
observable damage to operator presentation; it does not roll back an already
committed signal transition.

Always inspect SQLite when investigating missing or ambiguous lifecycle output.
Console and JSONL logs are evidence about presentation, not the durable signal
aggregate.
