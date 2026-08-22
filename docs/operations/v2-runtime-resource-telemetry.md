# V2 Runtime Resource Telemetry

## Purpose

`RuntimeResourceActor` measures the running Markeitech process and the public Nautilus cache surface
so performance incidents can be investigated with evidence. It is a passive observer. It does not
change cache configuration, resource limits, system health, acquisition, analytics, or alerting.

The first controlled use is an Observatory-off runtime run with all existing Nautilus cache defaults
unchanged. That preserves the previous runtime configuration and gives us a baseline before any
cache-policy or Redis decision.

## Configuration

The `[runtime_resources]` block in `v2/config/system.toml` owns the behavior:

- `enabled`: registers or omits the actor.
- `sample_interval_ms`: cadence for resource samples; initially 10 seconds.
- `log_every_samples`: compact log cadence expressed in samples.
- `include_cache_counts`: enables inspection through public Nautilus cache methods.

These are operational parameters, not trading parameters. No warning or failure threshold exists in
this slice because no measured baseline yet justifies one.

## Published Contract

Each successful sample publishes `markeitech.runtime.resource` with schema version 1. The payload
contains:

- observation time, sample sequence, and configured sample interval;
- resident and virtual memory;
- actor-observed peak resident memory;
- cumulative user/system CPU time and interval CPU percentage;
- process thread count and open file-descriptor count where the host supports it;
- Nautilus cache instrument, quote, trade, bar-type, and bar counts;
- explicit cache-observation status and error text when cache evidence is unavailable.

CPU percentage is process CPU-time growth divided by elapsed wall time. It may exceed 100 percent
when the process uses multiple cores. Peak RSS is the maximum observed by this actor during the
current run, not an operating-system lifetime high-water mark.

## Persistence And Logging

`OperationalPersistenceActor` stores every accepted sample in the existing `operational_events`
ledger with event type `runtime.resource`. No raw market observation or new database table is
introduced. At the initial 10-second cadence this adds six compact operational records per minute.

The actor writes a compact `RUNTIME_RESOURCE` line at the configured log cadence and one
`RUNTIME_RESOURCE_SUMMARY` during shutdown. The summary includes sample/failure counts, initial,
minimum, final, and peak RSS, RSS growth, maximum CPU percentage, threads, open file descriptors,
and observed cache counts. Shutdown does not publish a final event, avoiding a late message after
persistence has begun stopping.

Sampling failures are caught and logged as `RUNTIME_RESOURCE_SAMPLE_FAILED`. They remain local to
this diagnostic actor and do not degrade system health or stop unrelated actors.

## Controlled Diagnostic Protocol

1. Keep the Observatory disabled and leave all Nautilus cache settings unchanged.
2. Run the normal V2 configuration through a representative market session.
3. Compare RSS growth with quote, trade, and bar-count growth over time.
4. Reconcile `RUNTIME_RESOURCE_SUMMARY` with persisted `runtime.resource` records.
5. Repeat with the Observatory only if an explicit comparison is still needed.
6. Change cache retention or introduce Redis only when the measurements identify a concrete owner.

The actor provides correlation evidence, not proof of causation. A growing cache count beside rising
RSS identifies a candidate for focused investigation; it does not by itself justify an architecture
change.
