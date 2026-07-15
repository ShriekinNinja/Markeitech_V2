# Analytics Chart

The experimental analytics chart is a read-only projection of committed market
data and feature snapshots. It does not call analytics calculators, participate
in signal evaluation, or write runtime state.

Run `Analytics - Active Instrument Chart` in PyCharm, or:

```bash
uv run markeitech-analytics-chart config/market-data.local.toml
```

The command defaults to the configured active instrument and writes a standalone
HTML file under `data/charts/`. Plotly JavaScript is embedded, so the resulting
chart does not require a server or internet connection.

The first slice displays:

- committed one-minute candles and volume from the exact source used by the
  latest one-minute feature
- EMA 20, EMA 50, and EMA 200 history
- session VWAP and current-session VAL, POC, and VAH
- prior-session high and low
- latest support and resistance across available analytical timeframes
- active fair value gaps across available analytical timeframes
- latest multi-timeframe trend summary and evidence timestamp

This command renders one point-in-time artifact. Automatic generation at
`ANALYTICS_READY`, periodic replacement, and browser refresh are deliberately
deferred until the chart itself has been visually accepted.
