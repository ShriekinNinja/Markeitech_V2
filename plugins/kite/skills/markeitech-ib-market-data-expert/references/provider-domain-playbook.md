# IB Provider Domain Playbook

Read only sections relevant to the request. Refresh exact limits from current official sources;
this file is a question map, not cached provider policy.

## Contracts And Discovery

Resolve exactly one contract. Preserve `conId`, local symbol, trading class, primary exchange,
multiplier, expiry, and returned details where material. Broad contract-detail requests may return
multiple matches. Use market-rule evidence when price increments matter; the smallest `minTick`
does not describe every price band. Qualification proves identity, not entitlement or delivery.

## Entitlements, Modes, And Resource Families

Identify username, account mode, subscription/API permission, and paper-data sharing. Confirm the
returned mode per request: live, frozen, delayed, and delayed-frozen are distinct. Delayed
availability is not uniform and does not cover every tick request.

Track market-data lines separately from message rate, historical pacing, historical concurrency,
tick-by-tick caps, scanner limits, option-contract breadth, and adapter-local serialization.

## Requests And History

Do not collapse streaming/snapshot `reqMktData`, tick-by-tick, five-second real-time bars,
historical bars/updates/ticks, depth, contract/schedule/market-rule discovery, scanners, or option
definition/per-contract market data. Refresh fields, parameters, entitlement, pacing, callbacks,
cancellation, timestamps, and unsupported cases for the exact family.

For history verify duration/bar-size combinations, small-bar pacing, duplicate restrictions,
concurrency, soft throttling, retention, expired-contract availability, request and return
timezones, `formatDate`, `whatToShow`, `useRTH`, partial bars, and whether timestamps mark interval
start. Validate no-data against contract lifetime, sessions, holidays, permissions, and documented
unavailable cases before classifying it.

## Futures And Options

Markeitech's lineage stays with explicit dated futures unless Markeitect approves otherwise.
Treat `CONTFUT` as an IB data/history alias, not a tradable dated identity. Refresh version-specific
request conditions and preserve rolls, normalization/basis effects, and limited prior-contract
access. Never silently fall back to nearest expiry, continuous series, or another venue.

Discover option expiries/strikes through security-definition or contract discovery, never a
guessed grid. Preserve underlying `conId`, exchange, trading class, multiplier, expiry, strike,
right, and exact option identity. Definition discovery is not full-chain streaming; per-contract
market data/Greeks consumes entitlements and resources. Refresh underlying/option subscription,
model-Greek, generic-tick, snapshot/streaming, breadth, and expired-option rules.

## Time, Sessions, And Closed Markets

Keep distinct: IB timestamp/timezone behavior, exchange schedule, and Markeitech analytical phase.
Compare in UTC while preserving original timezone/format/source. Use IANA zones, never fixed DST
offsets. Distinguish trading from liquid/RTH hours, order acceptance from trading, trade date from
civil date, and regular schedules from dated exceptions.

“London session” is not universal IB truth. If not exchange-defined, it is a policy candidate that
needs an IANA zone, local and UTC bounds by date, DST behavior (including transatlantic mismatch
weeks), instruments, purpose, and version. Data received during London wall-clock hours does not
prove London-market causation.

Expected closed-market silence needs verified session state. Frozen close values, delayed ticks,
empty history, and farm-inactive notices do not prove live availability. Permission rejection,
pacing, line exhaustion, contract error, or farm disconnection remains explicit even when closed.
Map each outcome to informational, dormant, retryable provider, contract/configuration,
entitlement, resource, unsupported/unavailable, partial, adapter/local, or unknown before defining
bounded retry.
