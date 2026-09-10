# V2 Interactive Brokers Setup

This guide applies to the currently implemented Markeitech V2 **market-data** runtime. Retired
commands and the former active/background instrument model are not part of this workflow. The
accepted future Sir Loke broker-observation boundary is described separately below; it is not
implemented or authorized by the current run command.

## Authoritative References

Use the [NautilusTrader V2 nightly Interactive Brokers API reference](https://nautechsystems.github.io/nautilus_docs/python-api-nightly/adapters/interactive_brokers.html)
before changing adapter configuration, instrument discovery, market-data subscriptions, historical
requests, factories, or gateway behavior.

Cross-check documentation against Markeitech's pinned Nautilus release, installed public
signatures, and connected acceptance. Superseded Python/`ibapi` adapter documentation is not a
contract for the current Rust-backed integration.

For TWS-side safety, use the current official IBKR pages for
[API settings](https://www.interactivebrokers.com/docs/tws-api/doc/tws-settings/introduction),
[manual TWS orders](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/requesting-currently-active-orders/manually-submitted-tws-orders),
[order binding](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/requesting-currently-active-orders/order-binding-notification),
and [order modification](https://www.interactivebrokers.com/docs/tws-api/doc/orders/modifying-orders).

## Safety Boundary

Markeitech currently uses Interactive Brokers for market data only:

- trader-selected account;
- read-only socket API;
- no execution client configuration;
- no order-routing actor;
- explicit connection confirmation token; and
- no automated test or setup command that connects to IB.

The Sir Loke v1 product now requires future read-only observation of broker account, order, fill,
and position facts, but no such client or actor exists in the current checkout. Observation must
not be confused with order routing. Any submit, modify, bind for control, cancel, replace,
exercise, or close capability
requires a separately reviewed future execution and risk program and is outside Sir Loke v1.

## User-Owned Requirements

Every machine/user supplies:

- its own selected IB account;
- TWS or IB Gateway;
- market-data subscriptions and permissions;
- local API port and client ID; and
- current explicit contract configuration.

The repository does not include account credentials or entitlements.

## TWS Or Gateway Checklist

1. Log into the broker account/session selected by the trader.
2. Enable ActiveX and socket clients.
3. Enable read-only API mode.
4. Allow localhost connections.
5. Note the configured socket port.
6. Ensure the selected client ID is not already in use.
7. Treat the connection client ID and TWS **Master API Client ID** as separate settings. Gate 1A
   characterizes connection client `1`; Markeitect reports Master `1`, but that TWS setting has not
   been inspected. Master `1` does not give connection `1` the special behavior of client `0`.
8. Set “Send instrument-specific attributes for dual-mode API client” to **instrument timezone**
   for pinned Nautilus `2.0.0rc4`. The [rc4 Cargo lockfile](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc4/Cargo.lock)
   retains Rust `ibapi 3.3.0`, whose rejection of IB's valid dashed UTC `HistoricalDataEnd`
   metadata was established under rc3. The upgrade does not close this debt; rc4 connected
   timestamp calibration remains pending. This affects response transport syntax only: Nautilus and
   Markeitech retain absolute Unix-nanosecond timestamps internally. Do not infer API behavior from
   the TWS chart display timezone. Recalibrate with one bounded connected request after a
   consequential TWS/Gateway, Nautilus adapter, or `ibapi` parser change.

This checklist is accepted only for the implemented market-data client. Do not change to client ID
`0`, enable automatic open-order download/binding, disable read-only mode, or add an execution
client in an ordinary market-data run. Those settings may affect which manual TWS orders are
visible or controllable and belong to the separately reviewed observation proof.

Use the socket port configured in the actual TWS/Gateway session and set the same value in
`config/system.local.toml`. The example port is a connection setting, not account classification.

## Local Configuration

Create the ignored local file once:

```bash
test -e config/system.local.toml || \
  cp config/system.example.toml config/system.local.toml
```

Review the `[ib]` section:

```toml
[ib]
host = "127.0.0.1"
port = 4002
client_id = 20
symbology_method = "simplified"
convert_exchange_to_mic_venue = false
market_data_type = "realtime"
use_regular_trading_hours = false
```

These are example values, not universal machine settings. Keep the local file outside Git.

## Instruments And Entitlements

The tracked template is a reviewed project starting point. Before a connected run:

- roll expired futures everywhere they appear;
- verify venue and simplified Nautilus instrument identity;
- remove or disable instruments the user cannot lawfully receive;
- confirm real-time versus delayed data behavior;
- verify each instrument's calendar/profile assignment; and
- keep explicit-expiry futures for canonical observation unless a separate decision changes that
  boundary.

Definitions may load successfully while live data remains unavailable because of entitlement,
session, venue, or contract errors. Markeitech reports those failures honestly rather than
fabricating readiness.

## Preflight

With Docker Desktop running and local files configured:

```bash
.venv/bin/markeitech environment check --with-ib
```

The doctor checks that the configured TCP endpoint is listening. It does not authenticate, request
market data, validate entitlements, or start Nautilus.

Run offline checks before a connected acceptance:

```bash
.venv/bin/markeitech verify all
```

## Connected Run

Run the guarded command directly or place it in a local, untracked PyCharm Shell configuration:

```bash
docker compose --env-file .env -f compose.yaml up -d --wait postgres
.venv/bin/markeitech system run \
  --config config/system.local.toml \
  --connect I_UNDERSTAND_THIS_CONNECTS_TO_IB --keep-awake
```

Startup performs PostgreSQL schema preflight before opening the operational run. Actors then start
independently through the Nautilus runtime. System `READY` requires mandatory persistence and
instrument readiness; unrelated data paths continue attempting recovery when one request degrades.

## Expected Evidence

Inspect:

- console system/actor lifecycle output;
- `data/logs/markeitech-v2.log`;
- Discord system-health transitions;
- PostgreSQL runtime and operational-event records; and
- actor shutdown summaries after controlled `SIGINT`.

Provider observations remain transient. PostgreSQL stores operational intent, status, health,
request, retry, transition, and outcome evidence rather than raw quotes, trades, or bars.

With execution disabled, this run does not observe the account's orders, fills, positions, or P&L.
A successful market-data run is not evidence that Sir Loke can detect a manually entered TWS trade.

## Optional Native Execution-Client Connection POC

System schema 27 adds these required sections to both tracked templates:

```toml
[ib_execution]
enabled = false
client_id = 42
account_id = ""

[risk_engine]
bypass = false
```

To migrate an existing ignored local configuration, change its `schema_version` to `27` and add
these sections. Preserve all existing local settings. To test the connection, set the actual
account, select an unused execution client ID distinct from `[ib].client_id`, and set
`ib_execution.enabled = true`. Endpoint, timeouts, and instrument-provider settings come from
`[ib]`; other native execution and risk settings retain their defaults. No strategy is added.

Markeitect runs the existing connected system command above at the reviewed PR head. Check native
logs for execution-client startup and the selected account, then stop with `Ctrl+C` and check
shutdown. A listening socket or offline node construction is not connected acceptance. Stop on
an account mismatch, unexpected order action, or repeated startup failure. Keep account-bearing
logs local and share only sanitized startup/shutdown results. Setting the flag back to false and
restarting omits the client; shutdown does not imply cancellation of broker orders.

This POC's explicitly enabled connection is separate from the data-only setup checklist and the
historical observation proof below. No TWS setting is changed by the application. Native startup
may request account/order/fill/position state. The application sends no order commands and adds
no broker-state projection or persistence. Connected startup and shutdown remain untested.

## Planned Sir Loke Broker-Observation Proof

Markeitect selects the Interactive Brokers account and TWS session for connected acceptance.
Sir Loke uses one analysis and mentoring workflow. Broker facts retain a stable non-secret account
identity or alias; account-mode classification is not required by the product or test protocol.

The proof must evaluate the exact pinned NautilusTrader capabilities before custom IB access:

- `InteractiveBrokersExecutionClientConfig` and its factory;
- live execution-engine reconciliation and external-order settings;
- native cache account/order/position state;
- typed order and position events/callbacks; and
- native execution/position reports.

The proof is observation-only. It must establish event coverage and identity for manually entered
orders, partial fills, cancel/replace, scale changes, manual closure, duplicates, reconnect, and
reconciliation without submitting an order or silently taking control of a manual TWS order.

The [Gate 1A evidence reference](../reference/ib-observation-gate1.md) records the exact pinned
construction, configuration, startup, request, report, reconciliation, recovery, and disconnect
source inventory. Client `1` constructs offline; client `0` is rejected by the pinned constructor's
modulo-1000 order-ID partition. No lifecycle or connected behavior was exercised.

Official IBKR documentation distinguishes several materially different paths. `reqOpenOrders`
returns orders placed by the same API client; when client `0` invokes it, existing manual TWS
orders are also bound for API control. `reqAutoOpenOrders(True)` is restricted to client `0` and
associates future manual TWS orders. `reqAllOpenOrders` is a one-time download of current open
orders in associated accounts and does not start a future-order subscription. Automatic download
is therefore not synonymous with automatic binding. Binding makes a manual order
modifiable/cancelable by the API and can cancel/resubmit a working exchange order, potentially
changing queue priority.

The inspected rc4 startup calls its `all_open_orders()` request while establishing an order-ID
baseline even though the public `fetch_all_open_orders` default is `False`; the field is logged but
was not found controlling the inspected execution paths. Treat that as an unresolved pinned-source
inconsistency. The TWS API read-only setting prevents API modifications; it is not by itself
evidence that the surrounding client startup avoids all control effects or that the required
manual-order events are visible.

Therefore no client ID, binding mode, open-order request, reconciliation setting, or read-only
combination is accepted for this product until the offline safety review identifies every exact
call and the bounded connected proof measures the chosen configuration. An unexpected bind,
resubmission, modification, cancellation, replacement, exercise, or order submission is an
immediate stop condition.

Relevant provider references:

- [TWS API settings](https://www.interactivebrokers.com/docs/tws-api/doc/tws-settings/introduction)
- [API client orders and client-0 binding](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/requesting-currently-active-orders/api-clients-orders)
- [All submitted orders snapshot](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/requesting-currently-active-orders/all-submitted-orders)
- [Manual TWS orders and client ID 0](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/requesting-currently-active-orders/manually-submitted-tws-orders)
- [Order binding notification](https://www.interactivebrokers.com/docs/tws-api/doc/order-management/requesting-currently-active-orders/order-binding-notification)
- [Modifying orders and queue-priority warning](https://www.interactivebrokers.com/docs/tws-api/doc/orders/modifying-orders)

The proof needs separate explicit authorization for its connected run. It must use dedicated local
configuration outside Git, record the exact TWS instance/account identity/client ID/settings,
and stop on any unexpected order-control behavior. Markeitect performs and reviews the run.

## Common Failures

### Connection refused

TWS/Gateway is not listening at the configured host/port, the API is disabled, or localhost is not
allowed.

### Client ID conflict

Another process is using the configured ID. Select a free value in `system.local.toml`.

### Instrument definition failure

Review expiry, symbol, exchange, symbology mode, and whether the contract is available from IB.

### Definition succeeds but observations do not arrive

Review market session, exchange entitlement, real-time/delayed permissions, and requested feed
kind. Do not treat retries as an entitlement fix.

### Historical request parsing or timezone failure

Preserve UTC internally, inspect the exact request/adapter boundary, and verify behavior against the
pinned Nautilus V2 API and connected logs before changing timestamp ownership. Do not reintroduce
provider-format conversions into unrelated analytical actors.
