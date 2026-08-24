# V2 Dynamic Watchlist Plan

**Status:** Architecture plan for Markeitect review. No dynamic watchlist behavior is implemented
by this document.

**Approved stopping boundary:** Complete and live-prove the static configuration-owned watchlist,
then stop before W5 dynamic membership. See
[`v2-static-watchlist-handoff.md`](v2-static-watchlist-handoff.md) for the exact implementation
state and remaining order.

## Objective

Make `WatchlistActor` a mandatory core actor and the owner of Markeitech's effective observation
universe. Configuration supplies the durable startup baseline. Approved runtime intents from an
operator, deterministic component, news workflow, or later advisory agent may add, modify, focus,
or release instruments without restarting the node.

`DataAcquisitionActor` remains the provider control plane. Nautilus remains the native data plane.
No actor republishes raw quotes or bars through Markeitech messages.

```text
Configuration baseline ---------+
Operator intent -----------------+
News-derived intent -------------+--> WatchlistActor --> logical capability demand
Advisory-agent intent -----------+                            |
                                                             v
                                                   DataAcquisitionActor
                                                   policy, budget, lifetime
                                                             |
                                                             v
                                                        Nautilus / IB
                                                             |
                                             native callbacks to consumers
                                                             |
                                                             v
                                                      WatchlistActor
```

## Initial Baseline

The first configured baseline must represent every instrument shown in Markeitect's TWS
watchlist. The image is interpreted as:

| Group | Logical instruments |
|---|---|
| Trade-expression underlyings | SPY, QQQ |
| Equity-index futures | ES, NQ, YM |
| Index and macro context | SPX, VIX, CL |
| Equity context | NVDA, AAPL, GOOGL, MSFT, AMZN, TSM, AVGO, SPCX, META, TSLA |

Markeitect confirmed `SPCX` from the IB contract description and selected `GOOGL` as the sole
Google share class in the baseline. Provider-ready identities and venues still require explicit
resolution before subscription; the screenshot is a logical-universe decision, not permission to
guess a Nautilus instrument ID.

Futures entries are logical roots in the watchlist model. A separately approved instrument
resolution policy selects an explicit tradable contract for ES, NQ, YM, and CL. Continuous-chart
identity must not leak into provider subscription identity. Cash instruments must use verified
Nautilus/IB canonical IDs and venues rather than inferred IDs.

Configured baseline ownership does not expire. A runtime source may add a second claim to a
baseline instrument, but releasing that claim must not remove the configured claim.

## Actor Ownership

### `WatchlistActor`

- Owns configured and runtime watchlist membership.
- Merges multiple ownership claims for the same instrument.
- Converts business capabilities such as `top_of_book` and `watchlist_last` into logical demand.
- Registers for approved native Nautilus callbacks after acquisition accepts demand.
- Maintains one bounded latest-state record and bounded counters per instrument.
- Owns per-instrument freshness, readiness, and degraded observation state.
- Publishes watchlist membership and readiness facts, never raw market observations.
- Detaches its native consumer before releasing its final acquisition claim.

### `DataAcquisitionActor`

- Resolves or verifies provider-ready instrument definitions.
- Validates feed demand against entitlements, supported feed classes, and resource policy.
- Expands approved watchlist capabilities into exact native requirements.
- Reconciles shared demand and anchors provider subscription lifetime.
- Owns provider request pacing, retry, cancellation, and acquisition lifecycle facts.
- Does not calculate watchlist state, choose membership, or relay raw market data.

### Nautilus and IB

- Own provider connectivity and normalized native objects.
- Deduplicate actor-level registrations where the adapter supports it.
- Deliver quotes and bars directly to registered actors.
- Retain native timestamps and provider semantics.

## Initial Capability Mapping

| Watchlist capability | Native requirement | Fidelity |
|---|---|---|
| `top_of_book` | Nautilus quotes with IB `reqMktData` batching | Best bid and ask updates |
| `watchlist_last` | Nautilus external 5-second bars | Latest completed 5-second close, explicitly labeled bar-derived |
| `tick_trades` | Nautilus trades / IB tick-by-tick | Focus capability only; subject to the observed IB subscription cap |

The initial scalable watchlist must not request tick-by-tick trades for every member. The live POC
showed IB error `10190` when broad `AllLast` subscriptions exceeded the account's tick-by-tick
limit. Exact `reqMktData` Last is not currently emitted by the installed Nautilus quote path. If a
5-second close is insufficient, extend the Nautilus IB adapter boundary deliberately; do not add a
competing unmanaged IB connection.

## Membership Contract

Each effective membership claim must contain:

- stable intent and owner identity;
- canonical instrument identity or a resolvable logical instrument reference;
- action: add, update, release, or focus;
- requested capabilities;
- reason and correlation/causation identity;
- priority;
- creation time and optional expiry;
- policy result; and
- acquisition lifecycle state.

The effective capabilities for an instrument are the union of all active claims. The instrument
leaves only after every claim has been released or expired.

## Intent Durability

The current PostgreSQL schema stores only runtime runs and system-health events. It does not yet
store watchlist intents or effective membership. Dynamic watchlist delivery must add that durable
boundary before runtime mutation is considered complete.

Under the global V2 operational-audit invariant, PostgreSQL must retain:

- every configured and runtime intent with stable identity, owner, source, reason, capabilities,
  priority, correlation/causation identity, creation time, and optional expiry;
- every deterministic disposition: accepted, modified, queued, rejected, released, expired, or
  failed, including its reason;
- acquisition and membership lifecycle transitions needed to explain what became effective; and
- a current effective-membership projection that can be rebuilt from the append-only history.

Configured claims require deterministic idempotency keys so restart does not create duplicate
intent history. Active, unexpired runtime claims may be reconstructed according to the approved
restart policy; expired claims must never be resurrected.

Raw quotes, bars, and per-update watchlist state do not belong in PostgreSQL. They remain on the
native Nautilus data plane and in bounded runtime state. Persistence records control intent and
decisions, not a duplicate market-data stream. Subscription requests and outcomes, first
observation, freshness transitions, degradation, recovery, and release remain auditable system
facts.

Example intent:

```text
owner=news-agent
instrument=XYZ
action=add
capabilities=[top_of_book, watchlist_last]
reason=material company event
priority=high
expires_after=90m
```

A `NewsEvent` is evidence for an intent, not permission to subscribe. Deterministic policy may
accept, modify, queue, reject, or expire the request. The advisory agent cannot call IB directly.

## Runtime Lifecycle

### Add or expand

1. Receive and validate a watchlist intent.
2. Resolve the logical reference to a canonical instrument definition.
3. Merge the claim with existing ownership and compute the capability delta.
4. Request the delta from `DataAcquisitionActor`.
5. Acquisition checks policy and resource budgets, then anchors missing native feeds.
6. Watchlist registers for the accepted native feeds.
7. Native callbacks establish fresh field-level readiness.
8. Publish an effective-membership snapshot and lifecycle fact.

### Release or expiry

1. Release only the requesting owner's claim.
2. Recompute effective capabilities from remaining claims.
3. Detach native callbacks no longer needed by Watchlist.
4. Acknowledge consumer detachment.
5. Acquisition releases its anchor only when no approved consumer demand remains.
6. Publish the resulting membership and acquisition lifecycle.

Ordering and failure behavior for steps 3-5 require an explicit live proof before runtime removal
is considered complete.

## State And Readiness

Each member tracks field-level state rather than one vague ready flag:

- instrument definition available;
- best bid observed and timestamp;
- best ask observed and timestamp;
- bar-derived last observed and timestamp;
- requested and active capabilities;
- active owners and nearest expiry;
- acquisition state;
- freshness state; and
- degradation reason.

The watchlist is operational when every protected baseline member has its required definition and
accepted acquisition plan. Data readiness is reported independently because a quiet or closed
market may legitimately have no recent bar.

## Deterministic Policy Boundary

Before an intent becomes effective, policy must be able to enforce:

- allowed instrument classes and resolvable identity;
- protected baseline membership;
- maximum effective members;
- provider market-data-line and tick-by-tick budgets;
- capability-specific cost;
- maximum lease duration by owner type;
- priority and eviction rules for optional claims;
- entitlement and unsupported-feed behavior; and
- operator override.

Initial limits must be based on measured IB/runtime behavior, not invented constants.

## Delivery Slices

### W1: Close the scalable watchlist POC

- [x] Prove native bid/ask callbacks across eight instruments.
- [x] Identify broad tick-trade failure as IB tick-by-tick limit `10190`.
- [x] Live-prove quotes plus 5-second bars across all eight instruments.
- [x] Remove temporary per-update logging after evidence review.
- [x] Commit the accepted POC and its evidence.

### W2: Promote Watchlist to a core bounded state owner

- [x] Separate native-consumer registration from whether required fields have been observed.
- [ ] Define session-aware live field-freshness policy; elapsed-time thresholds remain deferred.
- [x] Define versioned membership snapshot and lifecycle contracts.
- [x] Keep one immutable latest snapshot, native event timestamps, and bounded counters per member.
- [x] Prevent older callbacks from replacing newer latest-value state.
- [x] Replace proof-only logging with bounded summaries and state transitions.
- [x] Persist static demand, acquisition outcome, lifecycle, and membership records.

### W3: Make configuration seed Watchlist

- [x] Add a dedicated baseline watchlist configuration section.
- [x] Map every screenshot instrument to a Nautilus IB simplified provider identity.
- [x] Configure explicit dated contracts: September 2026 ES/NQ/YM and October 2026 CL; automatic
      rolling remains deferred.
- [x] Remove duplicated bootstrap subscription declarations from system configuration.
- [x] Have Watchlist create logical baseline demand through acquisition.

### W4: Define Watchlist-Acquisition messaging

- [x] Define versioned static demand plus acquisition outcome contracts for request, acceptance,
      rejection/failure, release, and provider detachment.
- [x] Expand approved static capabilities into exact native feed demands while Acquisition remains
      the sole provider-subscription owner.
- [ ] Prove shared claims do not duplicate provider subscriptions.
- [ ] Prove one owner expiry does not remove another owner's data.
- [x] Enforce actor stop ordering so Watchlist detaches and releases before Acquisition stops.

### W5: Add dynamic membership

**Deferred by Markeitect. Do not begin without new explicit approval.**

- [ ] Support add, update, release, focus, and lease expiry intents.
- [ ] Persist each intent and deterministic disposition in PostgreSQL with idempotent identity.
- [ ] Persist lifecycle transitions and maintain a rebuildable effective-membership projection.
- [ ] Add deterministic policy and measured resource budgets.
- [ ] Support operator and deterministic test sources first.
- [ ] Add news-derived and advisory-agent intent sources only after lifecycle tests pass.
- [ ] Prove restart reconstructs configuration claims but does not resurrect expired runtime claims.

### W6: Review provider gaps

- [ ] Decide whether 5-second bar-derived Last is sufficient for broad observation.
- [ ] If insufficient, design a narrow extension to expose `reqMktData` Last through Nautilus.
- [ ] Keep direct custom IB connectivity rejected unless the adapter extension is demonstrably
      impossible or unsafe.

## Non-Goals

- No analytics, indicators, signals, option-chain logic, or trade proposals in this track.
- No raw market-data persistence or custom raw-data bus.
- No direct subscription authority for news or advisory agents.
- No arbitrary global warmup plan.
- No silent ticker, venue, or futures-contract guessing.

## Approval Gates

1. Approve canonical identity and futures-resolution policy before expanding the baseline.
2. Approve versioned watchlist/acquisition and durable-intent contracts before W4 implementation.
3. Approve resource limits only after live evidence exists.
4. Approve any Nautilus adapter extension before provider-specific code is added.
