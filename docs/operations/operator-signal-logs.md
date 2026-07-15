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

## Terminal And Trigger Messages

The same stable layout supports:

- `SIGNAL_TRIGGERED`: Aggression evidence advanced an Armed signal.
- `SIGNAL_INVALIDATED`: Direction or Location semantics ended the setup.
- `SIGNAL_EXPIRED`: the configured observation window ended without a trigger.

Triggered and Expired behavior belongs to Stage 5D. Their formatter vocabulary
exists before live activation so presentation does not shape lifecycle design.

## Failure Semantics

The projector uses a bounded non-blocking queue and bounded dedupe memory.
Formatting or log-sink failure increments health counters but does not stop
ingestion, feature persistence, or signal evaluation. A rejected projection is
observable damage to operator presentation; it does not roll back an already
committed signal transition.

Always inspect SQLite when investigating missing or ambiguous lifecycle output.
Console and JSONL logs are evidence about presentation, not the durable signal
aggregate.
