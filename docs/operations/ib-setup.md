# V2 Interactive Brokers Setup

This guide applies only to the active Markeitech V2 runtime. The archived V1 commands and
active/background instrument model are not part of this workflow.

## Authoritative References

Use the [NautilusTrader V2 nightly Interactive Brokers API reference](https://nautechsystems.github.io/nautilus_docs/python-api-nightly/adapters/interactive_brokers.html)
before changing adapter configuration, instrument discovery, market-data subscriptions, historical
requests, factories, or gateway behavior.

Cross-check documentation against Markeitech's pinned Nautilus release, installed public
signatures, and connected acceptance. The V1 Python/`ibapi` adapter documentation is historical
context and must not be treated as the V2 contract.

## Safety Boundary

Markeitech currently uses Interactive Brokers for market data only:

- paper account;
- read-only socket API;
- no execution client configuration;
- no order-routing actor;
- explicit connection confirmation token; and
- no automated test or setup command that connects to IB.

Execution requires a separately reviewed architecture and risk stage.

## User-Owned Requirements

Every machine/user supplies:

- its own IB paper account;
- TWS or IB Gateway;
- market-data subscriptions and permissions;
- local API port and client ID; and
- current explicit contract configuration.

The repository does not include account credentials or entitlements.

## TWS Or Gateway Checklist

1. Log into paper trading.
2. Enable ActiveX and socket clients.
3. Enable read-only API mode.
4. Allow localhost connections.
5. Note the configured socket port.
6. Ensure the selected client ID is not already in use.
7. Set “Send instrument-specific attributes for dual-mode API client” to **instrument timezone**
   for pinned Nautilus `2.0.0rc3`. Its Rust `ibapi 3.3.0` dependency rejects IB's valid dashed UTC
   `HistoricalDataEnd` metadata. This affects response transport syntax only: Nautilus and
   Markeitech retain absolute Unix-nanosecond timestamps internally. Do not infer API behavior from
   the TWS chart display timezone. Recalibrate with one bounded connected request after a
   consequential TWS/Gateway, Nautilus adapter, or `ibapi` parser change.

Common IB defaults:

| Application | Paper | Live |
| --- | ---: | ---: |
| TWS | `7497` | `7496` |
| IB Gateway | `4002` | `4001` |

A custom port is valid when TWS/Gateway and `v2/config/system.local.toml` agree.

## Local Configuration

Create the ignored local file once:

```bash
test -e v2/config/system.local.toml || \
  cp v2/config/system.example.toml v2/config/system.local.toml
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
./scripts/check-env --with-ib
```

The doctor checks that the configured TCP endpoint is listening. It does not authenticate, request
market data, validate entitlements, or start Nautilus.

Run offline checks before a connected acceptance:

```bash
uv run --project v2 ruff check v2/src v2/tests
uv run --project v2 pytest -q v2/tests -m "not postgres"
```

## Connected Run

Run the guarded command directly or place it in a local, untracked PyCharm Shell configuration:

```bash
docker compose --env-file v2/.env -f v2/compose.yaml up -d --wait postgres
uv run --project v2 markeitech-system v2/config/system.local.toml \
  --connect I_UNDERSTAND_THIS_CONNECTS_TO_IB --keep-awake
```

Startup performs PostgreSQL schema preflight before opening the operational run. Actors then start
independently through the Nautilus runtime. System `READY` requires mandatory persistence and
instrument readiness; unrelated data paths continue attempting recovery when one request degrades.

## Expected Evidence

Inspect:

- console system/actor lifecycle output;
- `v2/data/logs/markeitech-v2.log`;
- Discord system-health transitions;
- PostgreSQL runtime and operational-event records; and
- actor shutdown summaries after controlled `SIGINT`.

Provider observations remain transient. PostgreSQL stores operational intent, status, health,
request, retry, transition, and outcome evidence rather than raw quotes, trades, or bars.

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
