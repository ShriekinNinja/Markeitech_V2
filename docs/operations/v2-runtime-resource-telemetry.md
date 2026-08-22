# V2 Runtime Resource Telemetry

## Purpose

`RuntimeResourceActor` measures the running Markeitech process, host pressure, disk headroom, and
the public Nautilus cache surface so performance incidents can be investigated with evidence. It is
a passive observer and never changes cache configuration, resource limits, acquisition, analytics,
or system-health ownership.

`RuntimeResourceHealthActor` is a separate policy owner. It consumes the raw samples and publishes
only sustained `NORMAL`, `WARNING`, and `CRITICAL` transitions. This separation keeps measured facts
independent from configurable alert policy.

The first controlled use is an Observatory-off runtime run with all existing Nautilus cache defaults
unchanged. That preserves the previous runtime configuration and gives us a baseline before any
cache-policy or Redis decision.

## Configuration

The `[runtime_resources]` block in `v2/config/system.toml` owns the behavior:

- `enabled`: registers or omits the actor.
- `sample_interval_ms`: cadence for resource samples; initially 10 seconds.
- `log_every_samples`: compact log cadence expressed in samples.
- `include_cache_counts`: enables inspection through public Nautilus cache methods.
- `disk_path`: filesystem whose capacity is measured.

The nested `[runtime_resources.health]` block owns transition confirmation, recovery confirmation,
notification cooldown, RSS-growth window, stale-sample limits, and a policy version. Its `warning`
and `critical` tables own every host/process threshold. The initial values are conservative
operational guards for review, not optimized truths. A change to any value or confirmation policy
must receive a new `threshold_version`.

Policy version `2026-08-22-v2` treats disk headroom below 10% as warning evidence after six
consecutive samples and below 2% as critical evidence after three. The independent 15 GiB warning
and 5 GiB critical byte thresholds remain active, so a small absolute reserve cannot be hidden by a
large filesystem. These are reviewable starting values, not machine-independent truths.

These are operational parameters, not trading parameters. They do not change global system health;
`SystemControlActor` remains the sole owner of that state.

## Published Contract

Each successful sample publishes `markeitech.runtime.resource` with schema version 2. The payload
contains:

- observation time, sample sequence, and configured sample interval;
- resident and virtual memory;
- actor-observed peak resident memory;
- cumulative user/system CPU time and interval CPU percentage;
- process thread count, open file-descriptor count, and soft descriptor limit where supported;
- host CPU, available memory, swap use, and configured-filesystem free capacity;
- Nautilus cache instrument, quote, trade, bar-type, and bar counts;
- explicit cache-observation status and error text when cache evidence is unavailable.

CPU percentage is process CPU-time growth divided by elapsed wall time. It may exceed 100 percent
when the process uses multiple cores. Peak RSS is the maximum observed by this actor during the
current run, not an operating-system lifetime high-water mark.

The health actor publishes `markeitech.runtime.health` schema version 1 only when a
configured state transition survives its confirmation window. Evaluated dimensions are host
available-memory percentage, host CPU, swap percentage, disk bytes/percentage free, process RSS,
rolling RSS growth, process CPU, thread count, file-descriptor ratio, and raw-sample staleness.
Unavailable descriptor capacity remains unknown and cannot cause a fabricated breach.

Raw resource samples and resource-health transitions use non-overlapping signal names because
Nautilus signal subscriptions are prefix-matched. Consumers must also reject unrelated signal names
before parsing payloads. This prevents one transition from being observed through multiple
subscriptions or re-entering the health evaluator as a raw sample.

## Persistence And Logging

`OperationalPersistenceActor` stores every accepted sample in the existing `operational_events`
ledger with event type `runtime.resource`. No raw market observation or new database table is
introduced. At the initial 10-second cadence this adds six compact operational records per minute.

Every accepted transition uses the same ledger with event type `runtime.resource_health`.
`CRITICAL` transitions receive the persistence worker's reserved critical capacity. Discord renders
eligible transitions as compact resource-health cards; only `CRITICAL` may ping `@here`. Warnings
and recoveries never ping, raw samples never reach Discord, and cooldown-suppressed transitions
remain durable even when no Discord card is sent.

The actor writes a compact `RUNTIME_RESOURCE` line at the configured log cadence and one
`RUNTIME_RESOURCE_SUMMARY` during shutdown. The summary includes sample/failure counts, initial,
minimum, final, and peak RSS, RSS growth, maximum CPU percentage, threads, open file descriptors,
and observed cache counts. Shutdown does not publish a final event, avoiding a late message after
persistence has begun stopping.

Sampling failures are caught and logged as `RUNTIME_RESOURCE_SAMPLE_FAILED`. Missing samples are
then visible to the independent stale-sample policy. Neither actor blocks or stops unrelated actors.

## Controlled Diagnostic Protocol

1. Keep the Observatory disabled and leave all Nautilus cache settings unchanged.
2. Run the normal V2 configuration through a representative market session.
3. Compare RSS growth with quote, trade, and bar-count growth over time.
4. Reconcile `RUNTIME_RESOURCE_SUMMARY` with persisted `runtime.resource` records.
5. Repeat with the Observatory only if an explicit comparison is still needed.
6. Change cache retention or introduce Redis only when the measurements identify a concrete owner.
7. Exercise warning, critical, and recovery transitions with controlled configuration before
   treating the initial policy as live-accepted.

The actor provides correlation evidence, not proof of causation. A growing cache count beside rising
RSS identifies a candidate for focused investigation; it does not by itself justify an architecture
change.
