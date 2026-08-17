# V2 Historical Dependency Execution

**Status:** Stage 9B implemented and live-accepted on 2026-08-17.

## Current Implementation Slice

The provider-backed acceptance path is implemented. It proves:

- a consumer-owned dependency intent published on the Nautilus signal bus;
- deterministic compilation of every catalog window into exact UTC bounds;
- session-aware resolution from the same authoritative calendars used by session state;
- bounded, single-lane execution through `DataAcquisitionActor.request_bars`;
- response validation against the requested instrument, bar specification, bounds, ordering, and
  observation limit before completion;
- transient delivery of the immutable historical batch through Nautilus custom data;
- one shared provider request with independent readiness for every consumer; and
- PostgreSQL audit of demand, execution lifecycle, and readiness without raw bars.

The single provider lane is intentional. Nautilus' actor callback returns the bar sequence without a
request identifier, so concurrent native requests cannot yet be correlated honestly. Late responses
after local timeout or cancellation are ignored and audited in runtime logs rather than attached to
another request.

The acceptance consumers are two independently registered `HistoricalDependencyProbeActor`
instances configured under `historical.probe.actor_ids`. They deliberately publish the same logical
dependency. The request identity excludes consumer identity, so acquisition submits one provider
request, emits `SHARED` when the second consumer attaches, delivers one transient batch, and emits
one readiness result per consumer.

`HistoricalWindowResolver` accepts explicit policy only. It uses configured session phases for
RTH/GTH/curb/premarket/overnight windows, configured durations for opening range and power hour,
configured offsets for named slices, configured counts for previous sessions, and exact supplied
UTC bounds for anchored and synchronized intervals. It never invents a phase, duration, offset,
count, or anchor.

To run the live acceptance once, set `historical.probe.enabled = true`. Expected evidence is:

- two `HISTORICAL_PROBE_DEMAND` records with different consumer IDs;
- one `QUEUED`/`SUBMITTED` provider lifecycle plus one `SHARED` attachment;
- `HISTORICAL_EXECUTION` transitions ending in `COMPLETED` or an honest terminal failure;
- `HISTORICAL_PROBE_BATCH` for the transient payload;
- `HISTORICAL_RESPONSE_ACCEPTED` with the exact bar type, count, and first/last event timestamps;
- two `HISTORICAL_PROBE_READINESS` records with independent `READY` or `DEGRADED` state; and
- corresponding `historical.dependency_demand`, `historical.execution`, and
  `historical.readiness` rows in `operational_events`.

No raw bar array belongs in those PostgreSQL rows.

Final live acceptance used two independent probe actors against one identical ES one-minute
dependency. The runtime emitted one `QUEUED`, one `SUBMITTED`, one `SHARED`, one accepted provider
response with 10/10 observations, one `COMPLETED`, and two independent `READY` results. Both
consumers received the same immutable batch and request ID. Watchlist observations, evidence-health
evaluation, Discord health, and operational persistence continued throughout; PostgreSQL stored the
two demand facts, execution lifecycle, and two readiness facts without raw bars.

## Purpose

Stage 9B gives analytical capabilities exact, bounded historical evidence without allowing them to
own Interactive Brokers or Nautilus request mechanics. A capability declares what it needs. The
acquisition boundary resolves session-aware time windows, shares identical requests, enforces
resource policy, executes through Nautilus, and returns an immutable transient result.

This stage does not define EMA, opening-range, VWAP, profile, trend, or signal formulas. Stage 9C
owns those meanings. Stage 9B only makes their input dependencies expressible and executable.

The complete product-wide request vocabulary is maintained in
[`../market-intelligence-request-catalog.md`](../market-intelligence-request-catalog.md). Stage 9B
must remain compatible with that destination even where execution is deferred to later stages.

## Non-Negotiable Rules

1. Analytical actors never call IB or Nautilus historical request methods directly.
2. Session/calendar state owns temporal boundaries. A capability cannot invent RTH or overnight
   timestamps.
3. Every request has exact UTC bounds, a maximum observation count, consumer lineage, purpose,
   priority, and immutable provider parameters.
4. Identical provider requests are executed once and fanned out to every declared consumer.
5. Requests are bounded by configurable per-request, total-observation, concurrency, timeout,
   retry, and pacing policies.
6. One failed, empty, timed-out, or canceled dependency cannot block unrelated requests.
7. Completion is not readiness. Each consumer is evaluated against its own minimum observation
   requirement.
8. Raw historical observations are transient. PostgreSQL stores lifecycle/audit facts and later
   approved derived summaries, never a replay archive of raw bars.
9. No parameter is permanently hard-coded. Defaults and safety bounds are configuration; future
   optimization may alter only parameters explicitly marked dynamic by the Stage 9C registry.
10. Provider unavailability degrades the affected dependency. It does not halt the event-driven
    runtime or unrelated actors.

## Ownership

| Concern | Owner |
|---|---|
| Declare required evidence | Analytical capability |
| Resolve RTH/overnight/session windows | Session/calendar component |
| Compile, deduplicate, budget, queue, retry, cancel | Data acquisition |
| Issue `DataActor.request_bars(...)` | Nautilus historical adapter |
| Validate minimum evidence | Historical dependency coordinator |
| Consume immutable transient batch | Declaring capability |
| Audit request lifecycle and readiness | Operational persistence |
| Persist approved metric/entity summaries | Later metric/entity owner |

## Request Catalog

The initial catalog supports bar history only. Historical quotes and trades are deliberately not
counterfeited by bars and are not enabled until a concrete use case and provider budget are
accepted.

| Window | Meaning | Typical future use |
|---|---|---|
| `previous_rth` | Previous completed regular session | Prior OHLC/close, prior-session references |
| `previous_gth_overnight` | Previous completed global/overnight phase | Prior global-session evidence |
| `current_overnight` | Current overnight phase through now or RTH open | Overnight high/low and gap |
| `current_rth` | Current regular session through last completed interval | RTH range and participation |
| `current_gth` | Current global session through last completed interval | SPXW GTH evidence |
| `curb` | Exact accepted curb phase | Product-specific post-RTH evidence |
| `premarket` | Configured premarket phase | Cash-product premarket context |
| `power_hour` | Configurable final regular-session segment | Durable prior-session summaries |
| `session_to_date` | Current named session phase through last completed interval | Generic session calculations |
| `opening_range` | Configurable duration from authoritative phase open | Opening-range families |
| `named_phase_slice` | Configurable offsets inside a named phase | Any approved session segment |
| `previous_sessions` | Bounded previous N completed sessions | Baselines and structure |
| `recent_completed` | Last bounded number of completed bars before `as_of` | Rolling measurements |
| `anchored_interval` | Exact interval from an approved event/entity anchor | Anchored calculations |
| `synchronized_interval` | Common UTC bounds across instruments | Cross-market comparisons |

`overnight` remains as a compatibility-neutral generic phase name where a market does not use the
GTH vocabulary. The exact configured calendar phase remains authoritative.

Each requirement contains:

- `kind`: currently `bars` only;
- `selector`: canonical Nautilus bar selector;
- `window`: one catalog window;
- `minimum_observations`: readiness threshold for that consumer;
- `maximum_observations`: provider request and memory ceiling; and
- `window_parameters`: immutable resolver policy, separate from provider behavior; and
- `parameters`: immutable provider-neutral request parameters.

Supported resolver policy is explicit:

| Window family | Required `window_parameters` |
|---|---|
| `recent_completed` | `observation_count` (the demand adapter derives it from the configured maximum when omitted) |
| `previous_rth`, `previous_gth_overnight`, current phase aliases, `curb`, `premarket`, `overnight`, `session_to_date` | `phase` |
| `opening_range`, `power_hour` | `phase`, `duration_minutes` |
| `named_phase_slice` | `phase`, `start_offset_minutes`, `end_offset_minutes` |
| `previous_sessions` | `phase`, `session_count` |
| `anchored_interval`, `synchronized_interval` | `start_ns`, `end_ns` |

`minimum_observations` and `maximum_observations` are intentionally distinct. A response can be
usable but incomplete, and two consumers sharing one request may reach different readiness states.

## Compile Flow

```text
capability declarations
    + instrument bindings
    + authoritative session bounds
    + resource policy
        -> validate declarations
        -> expand dependencies
        -> create exact request keys
        -> merge identical keys
        -> preserve consumer lineage and highest priority
        -> reject plans outside configured budgets
        -> deterministic request plan
```

The request identity is content-derived from instrument, feed kind, selector, exact bounds, limit,
and parameters. Consumer identity is excluded, allowing safe sharing without losing lineage.

## Execution Flow

The runtime executor is event-driven and bounded:

```text
request plan
    -> priority queue
    -> pacing admission
    -> Nautilus request_bars
    -> on_historical_bars callback
    -> immutable transient batch
    -> per-dependency validation
    -> readiness/failure publication
    -> operational lifecycle audit
```

The installed Nautilus API returns historical bars through actor callbacks without exposing the
request ID in the callback. The first adapter therefore permits one active historical request per
actor while preserving an extensible configurable concurrency contract. This is asynchronous and
does not sequence unrelated runtime components; it only serializes this provider request lane so a
response can be correlated honestly.

## Responses

### Historical Batch

The transient batch will carry request identity, exact bounds, received observations, provider
source, receive timestamp, completeness, and lineage. Observations remain native canonical
Nautilus objects inside the runtime boundary; analytics receives a read-only view.

### Dependency Readiness

Every consumer receives one terminal result:

- `READY`: minimum observations met and validation passed;
- `DEGRADED`: response is valid but below the declared minimum;
- `FAILED`: provider or validation failure exhausted its retry policy;
- `CANCELED`: owner withdrew demand or shutdown canceled work; or
- `EXPIRED`: configured deadline elapsed before completion.

Terminal results include request ID, capability/version, consumer, instrument, expected and
observed counts, exact bounds, fidelity, reason, and source. Stage 9B does not publish analytical
market events from these results.

## Configuration Contract

Stage 9B configuration will own:

- maximum requests per plan;
- maximum observations per request and per plan;
- maximum queued and active requests;
- minimum interval between provider requests;
- timeout and retry count/backoff;
- shutdown cancellation timeout;
- allowed historical feed kinds and selectors; and
- catalog window parameters such as phase, opening-range duration, previous-session count, and
  explicit anchors.

Instrument configuration selects capabilities; capabilities declare dependencies. Instruments do
not duplicate raw request recipes. Stage 9C introduces parameter records with `dynamic`, bounds,
step, version, and optimization authority. Setting `dynamic = false` prevents runtime optimizer or
agent mutation but never prevents a reviewed configuration change.

## Persistence

Persist:

- plan accepted/rejected;
- request queued, submitted, retried, completed, timed out, failed, or canceled;
- consumer readiness result;
- counts, bounds, latency, source, and failure reason; and
- capability/version and request lineage.

Do not persist raw historical bars merely because they were requested. Later approved metrics,
session entities, and compact prior-session summaries own their own durable contracts.

## Stage Exit

9B is complete only when:

- a capability can declare each initial catalog window;
- plans are deterministic, bounded, deduplicated, and session-aware;
- real Nautilus historical bars are requested and correlated without blocking the runtime;
- multiple consumers share one request and receive independent readiness;
- timeout, retry, empty, partial, cancellation, and shutdown behavior are tested;
- lifecycle facts are present in PostgreSQL but raw bars are absent; and
- live acceptance proves unrelated watchlist and health processing continue during historical
  success and failure.
