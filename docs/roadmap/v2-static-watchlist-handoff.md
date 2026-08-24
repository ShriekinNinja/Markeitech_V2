# V2 Static Watchlist Handoff

**Status:** Static configuration-owned watchlist complete and live-accepted; dynamic membership
remains explicitly deferred.

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
- Versioned membership and lifecycle contracts are published and persisted with complete startup
  and shutdown history.
- PostgreSQL stores runtime runs, system-health transitions, and the approved operational event
  families without raw market payloads.

## Approved Static Baseline

The intended configuration-owned baseline contains 18 logical instruments:

- trade expression: SPY, QQQ;
- futures: ES, NQ, YM;
- index and macro context: SPX, VIX, CL; and
- equities: NVDA, AAPL, GOOGL, MSFT, AMZN, TSM, AVGO, SPCX, META, TSLA.

`SPCX` and the choice of `GOOGL` as the sole Google share class are confirmed. The runtime now uses
Nautilus IB simplified `load_ids` for the complete baseline:

- futures: `ESU6.CME`, `NQU6.CME`, `YMU6.CBOT`, `CLV6.NYMEX`;
- trade expression and indices: `SPY.ARCA`, `QQQ.NASDAQ`, `^SPX.CBOE`, `^VIX.CBOE`; and
- equities: `NVDA.NASDAQ`, `AAPL.NASDAQ`, `GOOGL.NASDAQ`, `MSFT.NASDAQ`, `AMZN.NASDAQ`,
  `TSM.NYSE`, `AVGO.NASDAQ`, `SPCX.NASDAQ`, `META.NASDAQ`, `TSLA.NASDAQ`.

All entries are required provider loads. Nautilus therefore fails client initialization rather
than starting with a partially resolved watchlist. ES, NQ, and YM use explicit September 2026
contracts; `CLV6` is the explicit October 2026 CL contract. Automatic contract rolling remains a
separately approved future policy. See
[`../operations/v2-futures-rollover.md`](../operations/v2-futures-rollover.md).

## Mandatory Audit Boundary

PostgreSQL is the durable audit ledger for every meaningful system intent, decision, lifecycle
transition, publication, attempt, and outcome. It must not store raw ticks, quotes, bars, books,
or option-chain payloads. Market-data requests, first observation, freshness, gaps, degradation,
recovery, retry, and cancellation are system facts and must be audited.

The next persistence slice adds one generic append-only operational event ledger. Existing
specialized health storage remains valid. Watchlist membership and lifecycle events are the first
new event families; future components use the same envelope rather than inventing unrelated audit
tables. Read-optimized projections may be added only for concrete query needs.

## Historical Static Delivery Sequence

1. [Complete] Add the generic operational-event schema, idempotent store boundary,
   and restart queries.
2. [Complete] Persist current acquisition control events plus watchlist membership
   and lifecycle events through one ordered worker before treating them as accepted audit history.
3. [Complete] Gate system control, acquisition, and watchlist startup through a
   versioned persistence request/ready handshake. This closes the missing startup lifecycle without
   an arbitrary timer and preserves `REQUESTED`, `ACCEPTED`, and `SUBSCRIBED` before `ACTIVE`.
4. [Complete] Add dedicated static watchlist configuration with permanent
   configuration ownership.
5. [Complete] Watchlist publishes versioned, stable demand messages; Acquisition
   owns provider subscriptions and returns outcomes on the acquisition lifecycle contract.
6. [Complete] Removed duplicated bootstrap feed configuration. Capabilities are the
   sole source of baseline feed requirements, including the optional native-consumer probe.
7. [Complete] Provider failures, rejection, expiry, and recovery produce durable
   degradation/recovery lifecycle facts. Elapsed-time staleness is intentionally deferred until a
   session-aware policy exists; a quiet or closed market must not be mislabeled as degraded.
8. [Live-accepted] Resolve all 18 logical instruments through Nautilus IB simplified provider IDs
   and explicit dated contracts: September 2026 ES/NQ/YM plus October 2026 CL.
9. [Live-accepted] Prove bounded operation, shared subscriptions, complete audit history, and
   shutdown.

## Runtime Contract

1. Persistence announces readiness.
2. Watchlist publishes the configuration membership and one demand per member capability.
3. Acquisition resolves every configured instrument, accepts demands, and alone owns provider
   subscription lifetime.
4. After a provider subscription is confirmed, Watchlist registers its native Nautilus observer.
5. First observations mark acquisition streams active and eventually mark each member observed.
6. Watchlist releases its demands before Acquisition stops; both intent and outcome are persisted.

The configured 18 members therefore produce 36 request records and 36 complete acquisition
lifecycles without duplicating feed declarations. PostgreSQL contains those operational
facts, never quote values, bar closes, or per-update watchlist state.

## Hard Stop

Stop after the static configuration-owned watchlist is accepted live. Do not implement runtime
add, update, release, focus, ownership leases, expiry, eviction, news-driven membership, or agent
membership authority until Markeitect explicitly reopens dynamic membership.

No analytics, signals, option-chain analysis, warmup policy, custom IB connection, raw-data
persistence, replay, or backtesting belongs in this sequence.
