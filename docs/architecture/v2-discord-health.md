# V2 Discord System Health

**Status:** Stage 3 accepted after live review on 2026-08-05.

## Responsibility

`DiscordHealthActor` is a read-only projection of accepted system-health and operational-readiness
evidence. It does not determine state, publish health transitions, supervise Interactive Brokers,
or participate in runtime readiness.

The actor projects `markeitech.system.health` and accepted runtime-resource health transitions to
the system-health webhook. It also observes existing watchlist membership/lifecycle and historical
demand/readiness signals for the one-shot operational-readiness card.

System-health states are:

- `STARTING`
- `READY`
- `FAILED`
- `STOPPING`

There are no analytics, market events, delivery retries, startup test messages, durable outbox, or
general notification router. Critical resource messages may mention `@here` when explicitly
configured; the operational-readiness card never mentions anyone.

## Configuration And Secrets

The request timeout is explicit in local `v2/config/system.local.toml`, initially copied from
tracked `v2/config/system.example.toml`:

```toml
[discord]
request_timeout_seconds = 5
```

Webhook URLs are read only from `MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK` and
`MARKEITECH_DISCORD_OPERATIONAL_EVENTS_WEBHOOK` after the V2 environment file is loaded. Actor
configuration contains environment-variable names, never their values. Runtime environment
validation requires both values whenever Discord is enabled.

Webhook URLs and exception messages that may contain URLs are never written to runtime logs.

## Delivery Boundary

The installed NautilusTrader `2.0.0rc1` actor API exposes neither a task executor nor a running
Python `asyncio` loop. Its asynchronous HTTP client therefore cannot be awaited from actor
callbacks, while its synchronous `http_post` would block the Nautilus event thread.

The approved boundary is one actor-owned worker thread:

1. `on_signal` validates and renders the event without performing I/O.
2. A bounded FIFO accepts at most the four possible lifecycle transitions.
3. One worker sends messages in order using Nautilus `http_post`.
4. A completion queue carries sanitized results back to the actor.
5. A Nautilus clock timer drains completions and writes actor-owned logs.

Queue overflow and HTTP failure are observable but cannot alter system health.

## Discord Message

Each event becomes one Discord embed containing:

- current state and reason;
- source actor;
- available and expected instrument counts;
- configured instrument IDs;
- previous state when available;
- the Nautilus event timestamp when provided.

`allowed_mentions` explicitly disables all mention parsing. The request sets `wait=true` so a
successful response confirms that Discord saved the message rather than merely accepting the
request.

The operational-events webhook receives one unmentioned startup card after existing canonical
evidence proves all three conditions:

- system control is `READY`;
- every configured watchlist member has emitted `INSTRUMENT_OBSERVED`; and
- every historical dependency published during initial warmup has reached terminal readiness.

The card reports watchlist and historical outcome counts. It says `READY` only when every terminal
historical outcome is `READY`; otherwise it reports completion with gaps. This projection creates
no new readiness event, state owner, or persistence schema.

Because membership and historical demands are one-shot startup evidence, runtime composition starts
the Discord observer before their producers. Readiness outcomes may then arrive in any order without
losing the declarations needed to prove the final join.

## Shutdown

The stop marker is placed behind already queued deliveries. `on_stop` waits no longer than the
configured request timeout, drains final results, and records an error if the worker remains
alive. `STOPPING` delivery remains best effort because actor shutdown ordering is not guaranteed
by the installed API.
