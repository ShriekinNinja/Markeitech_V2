# Discord Webhooks

**Status:** Implemented optional outbound projection

## Responsibility

`DiscordWebhooksActor` projects accepted system-health and resource-health events to one
configured Discord webhook. It does not determine system state or participate in readiness.

The projection is outbound operational infrastructure; it has no inbound conversation or order control.

System-health vocabulary currently includes:

- `STARTING`
- `READY`
- `DEGRADED`
- `FAILED`
- `STOPPING`

## Configuration And Secrets

Tracked configuration contains timeout and environment-variable names, never webhook values.
Local configuration begins from `config/runtime.example.toml`; actual secrets are read from:

```text
MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK
```

When Discord is enabled, runtime preflight requires this variable. Webhook URLs and
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

## Shutdown And Acceptance

The stop marker is placed after accepted FIFO work. Shutdown stops new admission, drains only
within the configured deadline, and reports undelivered or incomplete work honestly. `STOPPING`
delivery remains best effort because projection shutdown cannot outrank canonical runtime
teardown.

Delivery tests cover their exercised behavior. Live webhook results apply to the actual destination,
configuration and message. A successful projection does not establish underlying runtime readiness.
