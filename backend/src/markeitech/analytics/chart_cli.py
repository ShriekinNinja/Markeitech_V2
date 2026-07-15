from __future__ import annotations

import argparse
from pathlib import Path

from markeitech.analytics.chart import build_chart_dataset, render_analytics_chart
from markeitech.market_data.loader import load_market_data_runtime_config
from markeitech.persistence import NautilusParquetTimeSeriesStore, ParquetFeatureStore


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
    figure = render_analytics_chart(dataset)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(output, include_plotlyjs=True, full_html=True, auto_open=False)
    print(
        f"ANALYTICS_CHART | instrument={instrument_id} | as_of={dataset.as_of.isoformat()} "
        f"| source={dataset.source} | bars={len(dataset.bars)} | output={output.resolve()}"
    )


def _safe_name(value: str) -> str:
    return "".join(character if character.isalnum() else "-" for character in value).strip("-")
