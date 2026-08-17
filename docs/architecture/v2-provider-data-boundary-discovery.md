# V2 Provider And Canonical Data Boundary Discovery

**Status:** Decision Gate 7 accepted; implementation awaiting review.

**Scope:** NautilusTrader `2.0.0rc1` as installed in `v2/.venv`, the Interactive Brokers
adapter, and the current ES and SPY instrument configuration. This stage concerns source facts,
identity, timestamps, sessions, and fidelity. It does not define analytics, indicators, levels,
ranges, trends, signals, or acquisition workflows.

## Executive Finding

Nautilus already provides the canonical market-data objects V2 needs. Markeitech should preserve
those objects rather than wrap every instrument, tick, quote, bar, or book update in a parallel
model.

The missing boundary is acquisition context, not market-data shape. A native `TradeTick` knows its
instrument, price, size, aggressor side, trade identifier, event time, and initialization time. It
does not need a Markeitech copy. The actor that requested or subscribed to that data separately
knows the provider, client, delivery mode, regular-trading-hours policy, and request or
subscription identity. Those concerns should remain with that owner.

This gives V2 a small rule:

> Native market facts remain native. Markeitech records acquisition context and derived meaning
> separately, only when a real consumer requires them.

## Current Runtime Facts

- V2 configures `ESU6.CME` and `SPY.ARCA` as Nautilus `InstrumentId` values.
- The IB instrument provider loads those identifiers during startup.
- The provider currently uses IB simplified symbology and does not convert exchange values to MIC
  venues.
- V2 explicitly configures realtime market data and permits data outside regular trading hours.
- Several adapter behaviors currently rely on installed defaults rather than explicit Markeitech
  configuration.
- Stage 7 does not subscribe to or request market data. That ownership belongs to Stage 8.

## Native Type Inventory

| Concern | Nautilus native type | Important facts preserved | Stage 7 decision |
|---|---|---|---|
| Equity definition | `Equity` | Instrument identity, raw symbol, venue, currency, precision, increments, metadata, timestamps | Flow unchanged |
| Futures definition | `FuturesContract` | Contract identity, expiry, multiplier, increments, venue, metadata, timestamps | Flow unchanged |
| Index definition | `IndexInstrument` | Index identity, venue, currency, precision, metadata, timestamps | Flow unchanged |
| Option definition | `OptionContract` | Underlying, expiry, strike, option kind, multiplier, venue, metadata, timestamps | Flow unchanged when options enter scope |
| Best bid and offer | `QuoteTick` | Bid/ask price and size, instrument, event/init timestamps | Flow unchanged |
| Trade | `TradeTick` | Price, size, trade ID, aggressor side, instrument, event/init timestamps | Flow unchanged |
| OHLCV bar | `Bar` and `BarType` | OHLCV, interval, aggregation source, price type, event/init timestamps | Flow unchanged |
| Order-book change | `OrderBookDelta` / `OrderBookDeltas` / `OrderBookDepth10` | Side, action, price, size, order ID, flags, sequence, timestamps | Flow unchanged when subscribed |
| Venue state | `InstrumentStatus` / `InstrumentClose` | Provider-reported status or close facts and timestamps | Flow unchanged when available |
| Option analytics | `OptionGreeks` / `OptionChainSlice` | Native option analytics containers | Preserve for later options design; do not activate now |
| Markeitech output | `DataType` / `CustomData` | Timestamped structured data published through Nautilus | Candidate for future derived outputs, not raw-data wrappers |

Native availability does not prove that IB supplies every field or stream for every instrument and
permission set. Unsupported, absent, or unknown values must remain visibly absent or unknown.
In particular, `OptionGreeks` exists in Nautilus, but the reviewed IB support table does not prove
that this adapter publishes it. Stage 8 must verify actual adapter output before V2 depends on it.

## Instrument Identity Policy

`InstrumentId` is the canonical identity inside the current Nautilus runtime. Its form is
`{native symbol}.{venue}`. With IB simplified symbology, examples include `SPY.ARCA` and
`ESU6.CME`.

That identity is not declared universal across future providers:

- the venue identifies the instrument inside Nautilus; it is not a provider identifier;
- an equity's primary venue is not the same fact as its IB routing destination;
- provider-native contract details remain available in the instrument's `info` metadata;
- V2 must preserve `raw_symbol` and `info` rather than reconstructing them from the normalized ID;
- a future second provider may require an explicit alias registry backed by verified contract
  facts.

No alias registry is justified while IB is the only provider. No component may join instruments
across providers by string resemblance alone.

For futures, a specific contract such as `ESU6.CME` is a durable market identity. Any future
continuous-futures symbol must be treated as a rolling alias, not as the identity of the contract
that produced an observation.

## Timestamp Policy

V2 preserves the two native timestamps without rewriting them:

| Timestamp | Meaning | Constraint |
|---|---|---|
| `ts_event` | Time assigned to the market event by the source or adapter contract | Keep unchanged; interpret according to the concrete data type |
| `ts_init` | Time the Nautilus object was initialized | Keep unchanged; it is often close to local receipt for live venue data but is not a universal network-arrival guarantee |

Additional rules:

- Do not invent a third source timestamp when IB did not provide one.
- Do not derive latency from historical or replayed `ts_event` and `ts_init` values.
- Bar timestamps must be interpreted with their `BarType` and aggregation configuration. A bar's
  timestamp does not independently prove whether it marks open or close.
- Ordering claims belong to the acquisition workflow. Historical responses and live streams have
  different delivery semantics even when their payload type is the same.

## Session Policy

Regular-hours versus extended-hours selection is acquisition context. It is not embedded as a
universal property of each native tick or bar.

- The current IB client requests bars with `use_regular_trading_hours = false`.
- The acquisition owner must retain the policy used for each historical request or subscription.
- A consumer must not infer RTH, ETH, or a named session only from local clock time.
- Instrument trading-hour metadata may inform a later calendar/session component, but Stage 7
  does not create session analytics.

This prevents the same bar from acquiring different meaning merely because two consumers apply
different timezone or holiday assumptions.

## Source And Fidelity Policy

Source and fidelity are field-specific facts. One blanket label on an entire payload would be
misleading.

### Source

- `InstrumentId.venue` is not the provider name.
- The acquisition owner knows that the current source is IB and which configured client produced
  the stream or response.
- `BarType` preserves whether bars are externally supplied or internally aggregated.
- Live data and requested pipeline data must remain distinguishable by the Nautilus delivery path
  and the owner's request/subscription state.

### Fidelity

- Reported trade price and size may be preserved as reported values.
- `AggressorSide` must remain unknown when the adapter or source cannot establish it. Stage 7 does
  not claim that IB supplies exchange-authoritative aggressor classification.
- External OHLCV bars are provider aggregates, not reconstructed tick truth.
- Internally aggregated bars are derived data even though `Bar` is a native type.
- IB order-book depth, when available, must not be described as a consolidated full-market book
  without separate evidence.
- Delayed or frozen market data must retain its configured delivery mode and must never be labeled
  realtime.

Unknown is valid information. V2 must not improve a field's apparent quality through naming.

Preservation in this document means preserving meaning while native data moves through the live
runtime. It does not mean durable retention. V2 currently stores no raw market data, and Stage 8
must not add raw storage for replay, backtesting, or unspecified future use.

## Acquisition Context Boundary

The Stage 8 acquisition owner should maintain context beside native data rather than inside a new
market-data envelope. Expected context includes:

- provider and configured client identity;
- requested instrument and resolved native instrument identity;
- live subscription or historical request identity;
- realtime, delayed, frozen, or delayed-frozen delivery mode;
- regular-hours policy for bar requests;
- requested data type, interval, and time range;
- request completion, cancellation, timeout, and failure facts; and
- observed provider capability or absence.

Most of this is workflow state. It should not be copied onto every high-volume market object.

If a later consumer needs durable acquisition evidence, Stage 8 may define a small timestamped
acquisition lifecycle event using Nautilus custom data. That event would describe the request or
subscription. It would not wrap the returned ticks or bars.

Nautilus cache remains the owner of current runtime instrument and recent market-data state. It is
not Markeitech's durable analytical database. The DataEngine updates supported cache state before
dispatching native market data to handlers, so consumers should use that facility rather than
building a duplicate in-memory quote, trade, or bar cache without a separate requirement.

## Adapter Defaults Requiring An Explicit Decision

The installed IB adapter currently supplies these defaults:

| Setting | Installed default | Recommendation | Reason |
|---|---:|---|---|
| Instrument symbology | Simplified | Keep | Already matches `ESU6.CME` and `SPY.ARCA`; changing it would alter identity across V2 |
| Convert exchange to MIC venue | `false` | Keep for IB-only V2 | Avoid an identity migration without a second-provider requirement |
| Quote batching | `true` | Keep, but make explicit | Preserve adapter behavior; evaluate only against an acquisition requirement |
| Ignore quote size-only updates | `false` | Keep, but make explicit | Size-only changes are real source observations and may matter later |
| Handle revised bars | `false` | Keep initially, but make explicit | Gives committed consumers immutable completed bars; accepting revisions requires a defined correction policy |

The recommendation is not that these values are perfect forever. It is that V2 should own its
current behavior explicitly and change it only with evidence.

## Release-Candidate Compatibility Rule

The installed `2.0.0rc1` API is authoritative for implementation. Current official examples
already contain names associated with newer builds that differ from the installed package. For
example, the installed client uses `host`, `port`, `client_id`, and `request_timeout`, and its
enums expose names such as `MarketDataType.REALTIME` and `SymbologyMethod.SIMPLIFIED`.

Documentation remains authoritative for concepts and supported behavior, but code must be checked
against the installed signatures. No nightly-only API should enter V2 without an approved
dependency upgrade.

## Canonical Contract Decision

No Markeitech-owned raw market-data contract is needed in Stage 7. This is a deferment, not a
permanent prohibition: V2 may introduce one later when a concrete cross-provider, persistence, or
analytics requirement cannot be represented safely by native Nautilus types plus acquisition
context.

Creating `MarkeitechTrade`, `MarkeitechBar`, or a generic provider envelope now would:

- duplicate stable native fields;
- add conversion and allocation to high-volume paths;
- weaken direct compatibility with Nautilus cache, handlers, indicators, and catalog facilities;
- encourage provider context to be repeated on every observation; and
- imply uniform fidelity that the source does not provide.

Future analytics contracts such as `Level`, `Zone`, `Range`, or `TrendAssessment` are separate
derived domain objects. They will be designed only after acquisition is trustworthy and their
requirements are approved.

## Proposed Stage 7 Implementation

After approval, the smallest implementation is:

1. Add explicit IB configuration fields for simplified symbology, MIC conversion, quote batching,
   quote size-only updates, and revised-bar handling.
2. Pass those values directly into the native IB provider and data-client configs.
3. Add focused offline tests proving exact configuration mapping.
4. Add contract tests proving native instrument IDs and native event/init timestamps cross the
   provider boundary unchanged.
5. Do not add subscriptions, historical requests, custom market-data classes, persistence tables,
   session analytics, or provider aliases.

## Accepted Decision

Markeitect approved these decisions:

1. Keep IB simplified symbology and `convert_exchange_to_mic_venue = false` for the current
   single-provider runtime.
2. Keep quote batching enabled.
3. Preserve quote size-only updates.
4. Keep revised-bar handling disabled until a correction policy exists.
5. Make all four adapter behaviors explicit in V2 configuration.
6. Accept native Nautilus market objects as the canonical transport types and defer any custom
   acquisition lifecycle event to Stage 8.

## References

- [Nautilus data](https://nautilustrader.io/docs/latest/concepts/data/)
- [Nautilus instruments](https://nautilustrader.io/docs/latest/concepts/instruments/)
- [Nautilus message bus](https://nautilustrader.io/docs/latest/concepts/message_bus/)
- [Nautilus Interactive Brokers integration](https://nautilustrader.io/docs/latest/integrations/ib/)
