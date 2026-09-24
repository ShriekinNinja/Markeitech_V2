# V2 Interactive Brokers Setup

This runbook describes the tracked market-data profiles and the optional native execution-client
configuration. Account monitoring remains an active priority in the
[live foundation plan](../roadmap/live-foundation-plan.md); issue #78 has not delivered a monitor
or authorized a connected execution-client run.

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

The tracked profiles still use Interactive Brokers for market data only:

- trader-selected account;
- read-only socket API;
- an empty `[ib].execution_account_id`, so no execution client is registered;
- no order-routing actor;
- explicit connection confirmation token; and
- no automated test or setup command that connects to IB.

Setting the actual broker-visible account in an ignored local profile registers the native IB
execution client on the live node. On a connected run, that client requests an order ID and open
orders and participates in Nautilus reconciliation. No account monitor or order-action route is
implemented, and the existing market-data run approval does not authorize starting this optional
client. Leave the value empty until Markeitect approves an exact connected scenario.

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
   for pinned Nautilus `2.0.0rc5`. The [rc4 Cargo lockfile](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc4/Cargo.lock)
   retained Rust `ibapi 3.3.0`, whose rejection of IB's valid dashed UTC `HistoricalDataEnd`
   metadata was established under rc3. Rc5 connected timestamp calibration remains pending, so
   retain this setting until the provider response is checked. This affects response transport
   syntax only: Nautilus and Markeitech retain absolute Unix-nanosecond timestamps internally.
   Do not infer API behavior from the TWS chart display timezone. Recalibrate with one bounded
   connected request after a consequential TWS/Gateway, Nautilus adapter, or `ibapi` parser change.
   Record the rc5 result in [issue #59](https://github.com/ShriekinNinja/Markeitech_V2/issues/59).

This checklist is accepted only for the implemented market-data client. Do not change to client ID
`0`, enable automatic open-order download/binding, disable read-only mode, or add an execution
client in an ordinary market-data run. Those settings may affect which manual TWS orders are
visible or controllable and belong to the selected execution issue and its authorized live scenario.

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
execution_account_id = "" # Leave empty for the existing market-data run.
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

Run the tests added/changed for the issue. Broad regression checks run on the PR; a full local
suite is not a prerequisite for this runbook.

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

This market-data run does not observe orders, fills, positions or P&L.

## Execution And Account Monitor Development

Use the native Nautilus execution client, cache, account/order/position events and reconciliation
where they meet the issue. Inspect the exact startup and order paths needed for the chosen account,
client settings and scenario. Reach a small authorized live run promptly; resolve observed gaps
without a mandatory staged proof programme.

The issue must identify the account and TWS session, intended order actions, instrument/quantity
limits and stop condition. Market-data run approval does not authorize orders. Account monitoring
must preserve account/order/fill/position identity. Unexpected account or order behavior stops the
scenario. Markeitect runs and reviews acceptance unless he delegates that particular run.

The [earlier native-client inspection](../reference/ib-observation-gate1.md) is historical evidence
which may save work where still applicable; it is not a prerequisite gate or current execution
acceptance. Do not assume that a setting from the old observation experiment fits the new task.

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
