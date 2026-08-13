# V2 Static Watchlist Handoff

**Status:** Accepted implementation boundary after commits `bb93a2f`, `e5d9f1e`, and `3a58594`.

## Current Truth

- `DataAcquisitionActor` owns provider demand, shared subscription lifetime, and acquisition
  lifecycle.
- `WatchlistActor` is a mandatory core native Nautilus consumer.
- The live POC proved best bid/ask plus external five-second bars across eight instruments.
- Tick-by-tick `AllLast` is a focus-only capability because broad requests reached IB limit
  `10190`.
- Watchlist runtime state is bounded, immutable when exposed, timestamped, and protected from
  out-of-order replacement.
- Consumer registration and observation completeness are separate facts.
- Versioned membership and lifecycle message contracts exist but are not published or persisted
  by the actor yet.
- PostgreSQL currently stores runtime runs and system-health transitions only.

## Approved Static Baseline

The intended configuration-owned baseline contains 18 logical instruments:

- trade expression: SPY, QQQ;
- futures: ES, NQ, YM;
- index and macro context: SPX, VIX, CL; and
- equities: NVDA, AAPL, GOOGL, MSFT, AMZN, TSM, AVGO, SPCX, META, TSLA.

`SPCX` and the choice of `GOOGL` as the sole Google share class are confirmed. Exact provider IDs,
venues, and futures contract resolution remain approval-gated. The current eight-instrument POC
configuration is not the final baseline.

## Mandatory Audit Boundary

PostgreSQL is the durable audit ledger for every meaningful system intent, decision, lifecycle
transition, publication, attempt, and outcome. It must not store raw ticks, quotes, bars, books,
or option-chain payloads. Market-data requests, first observation, freshness, gaps, degradation,
recovery, retry, and cancellation are system facts and must be audited.

The next persistence slice adds one generic append-only operational event ledger. Existing
specialized health storage remains valid. Watchlist membership and lifecycle events are the first
new event families; future components use the same envelope rather than inventing unrelated audit
tables. Read-optimized projections may be added only for concrete query needs.

## Remaining Static Sequence

1. [Implemented for review] Add the generic operational-event schema, idempotent store boundary,
   and restart queries.
2. [Implemented for review] Persist current acquisition control events plus watchlist membership
   and lifecycle events through one ordered worker before treating them as accepted audit history.
3. [Implemented for live review] Gate system control, acquisition, and watchlist startup through a
   versioned persistence request/ready handshake. This closes the missing startup lifecycle without
   an arbitrary timer and preserves `REQUESTED`, `ACCEPTED`, and `SUBSCRIBED` before `ACTIVE`.
4. Add dedicated static watchlist configuration with permanent configuration ownership.
5. Define explicit Watchlist-to-Acquisition demand and outcome messaging.
6. Remove duplicated bootstrap feed declarations and let Watchlist seed baseline demand.
7. Approve and implement freshness/degradation policy without arbitrary thresholds.
8. Resolve the 18 logical instruments to reviewed provider identities and futures contracts.
9. Live-prove bounded operation, shared subscriptions, complete audit history, and shutdown.

## Hard Stop

Stop after the static configuration-owned watchlist is accepted live. Do not implement runtime
add, update, release, focus, ownership leases, expiry, eviction, news-driven membership, or agent
membership authority until Markeitect explicitly reopens dynamic membership.

No analytics, signals, option-chain analysis, warmup policy, custom IB connection, raw-data
persistence, replay, or backtesting belongs in this sequence.
