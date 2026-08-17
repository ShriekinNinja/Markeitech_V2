# V2 Discord System Health

**Status:** Stage 3 accepted after live review on 2026-08-05.

## Responsibility

`DiscordHealthActor` is a read-only projection of accepted system-health events. It does not
determine state, publish health transitions, supervise Interactive Brokers, or participate in
runtime readiness.

The initial actor subscribes only to `markeitech.system.health` and accepts the Stage 2 states:

- `STARTING`
- `READY`
- `FAILED`
- `STOPPING`

There are no analytics, market events, mentions, retries, startup test messages, durable outbox,
or general notification router in this stage.

## Configuration And Secrets

The request timeout is explicit in `v2/config/system.toml`:

```toml
[discord]
request_timeout_seconds = 5
```

The webhook is read only from `MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK` after the V2 environment
file is loaded. The actor configuration contains the environment-variable name, never its value.
An absent webhook disables delivery with a warning and does not prevent the system from starting.

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

## Shutdown

The stop marker is placed behind already queued deliveries. `on_stop` waits no longer than the
configured request timeout, drains final results, and records an error if the worker remains
alive. `STOPPING` delivery remains best effort because actor shutdown ordering is not guaranteed
by the installed API.
