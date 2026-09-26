# Discord Health Webhook

**Status:** Implemented optional outbound projection

## Responsibility

`DiscordHealthActor` projects accepted system-health, resource-health, watchlist, and historical-
readiness evidence to configured Discord webhooks. It does not determine system state, supervise
Interactive Brokers, calculate market truth, admit evidence, or participate in readiness.

The projection is outbound operational infrastructure; it has no inbound conversation or order control.

System-health vocabulary currently includes:

- `STARTING`
- `READY`
- `DEGRADED`
- `FAILED`
- `STOPPING`

The operational-readiness card reports only the joined canonical evidence it observes. It does
not create a new readiness state or establish unrelated runtime capabilities.

## Configuration And Secrets

Tracked configuration contains timeout and environment-variable names, never webhook values.
Local configuration begins from `config/system.example.toml`; actual secrets are read from:

```text
MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK
MARKEITECH_DISCORD_OPERATIONAL_EVENTS_WEBHOOK
```

When Discord is enabled, runtime preflight requires the configured variables. Webhook URLs and
exceptions which may contain URLs must not enter logs, audit payloads, generated artifacts, or
Git.

## Delivery Boundary

Webhook I/O never blocks a Nautilus actor callback. The actor validates and renders a bounded
message, an actor-owned bounded FIFO hands it to one worker, and sanitized completion results
return to actor-owned logging through a timer-driven drain. The worker cannot publish canonical
state or change health.

Delivery is ordered and bounded. Queue overflow, HTTP failure, timeout, and incomplete shutdown
are observable projection failures; they cannot alter market data, broker state, deterministic
analysis, persistence truth, or system-health ownership.

Messages disable unintended mention parsing. Critical resource notifications may use only the
separately configured mention policy. A successful Discord response proves only that Discord
accepted that projection, not that the underlying system is universally ready.

## Operational-Readiness Join

The optional one-shot card waits for observed evidence that:

- system control reached its accepted `READY` meaning;
- every configured watchlist member produced the required instrument-observed lifecycle; and
- every initial historical dependency reached a terminal readiness outcome.

The card reports counts and gaps. It says ready only when every required terminal outcome is
ready; otherwise it reports completion with limitations. Producers may publish in any order, so
the observer starts early enough to retain their bounded declarations and outcomes.

When a profile explicitly disables the watchlist and has no instruments, a separate rendering of
this card reports empty acquisition and persistence initialization without waiting for nonexistent
watchlist members or historical demands. It does not infer zero work from silence or claim that
IB, calendars, resources, or webhook delivery are healthy.

## Shutdown And Acceptance

The stop marker is placed after accepted FIFO work. Shutdown stops new admission, drains only
within the configured deadline, and reports undelivered or incomplete work honestly. `STOPPING`
delivery remains best effort because projection shutdown cannot outrank canonical runtime
teardown.

Delivery tests cover their exercised behavior. Live webhook results apply to the actual destination,
configuration and message. A successful projection does not establish underlying runtime readiness.
