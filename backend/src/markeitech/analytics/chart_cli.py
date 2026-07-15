from __future__ import annotations

import argparse
from pathlib import Path

from markeitech.analytics.chart import (
    build_chart_dataset,
    market_closed_minutes,
    render_analytics_chart,
)
from markeitech.market_data.loader import load_market_data_runtime_config
from markeitech.persistence import (
    NautilusParquetTimeSeriesStore,
    PandasMarketSessionCalendar,
    ParquetFeatureStore,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render committed Markeitech analytics as an interactive Plotly chart.",
    )
    parser.add_argument("config", type=Path, help="Path to a market-data TOML config file.")
    parser.add_argument(
        "--instrument",
        help="Instrument id; defaults to the configured active instrument.",
    )
    parser.add_argument("--bars", type=int, default=720, help="Maximum one-minute bars.")
    parser.add_argument("--output", type=Path, help="Output HTML path.")
    args = parser.parse_args()

    config = load_market_data_runtime_config(args.config)
    if config.persistence is None:
        raise ValueError("analytics chart requires configured persistence")
    instrument_id = args.instrument or config.instrument_registry.active_instrument_id
    output = args.output or Path("data/charts") / f"{_safe_name(instrument_id)}.html"
    bars = NautilusParquetTimeSeriesStore(config.persistence).query_one_minute_bars(instrument_id)
    features = ParquetFeatureStore(config.persistence).query_history(instrument_id)
    dataset = build_chart_dataset(
        instrument_id,
        bars,
        features,
        maximum_bars=args.bars,
    )
    calendar = PandasMarketSessionCalendar.from_registry(config.instrument_registry)
    expected_minutes = calendar.expected_minute_opens(
        instrument_id,
        dataset.window_start,
        dataset.as_of,
    )
    range_breaks = market_closed_minutes(
        dataset.window_start,
        dataset.as_of,
        expected_minutes,
    )
    figure = render_analytics_chart(dataset, range_breaks=range_breaks)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(output, include_plotlyjs=True, full_html=True, auto_open=False)
    print(
        f"ANALYTICS_CHART | instrument={instrument_id} | as_of={dataset.as_of.isoformat()} "
        f"| window=4h | analytics_source={dataset.source} "
        f"| candle_source={dataset.bar_source} | bars={len(dataset.bars)} "
        f"| closed_minutes={len(range_breaks)} | output={output.resolve()}"
    )


def _safe_name(value: str) -> str:
    return "".join(character if character.isalnum() else "-" for character in value).strip("-")
