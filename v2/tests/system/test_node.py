from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from nautilus_trader.adapters.interactive_brokers import (
    MarketDataType,
    SymbologyMethod,
)

from markeitech.system.composition import StartupPrerequisites
from markeitech.system.config import load_system_config
from markeitech.system.node import build_ib_data_client_config, build_system_node


def test_maps_provider_boundary_to_installed_ib_config() -> None:
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.toml")

    data_config = build_ib_data_client_config(config)
    provider_config = data_config.instrument_provider

    assert data_config.market_data_type == MarketDataType.REALTIME
    assert data_config.use_regular_trading_hours is False
    assert data_config.batch_quotes is True
    assert data_config.ignore_quote_tick_size_updates is False
    assert data_config.handle_revised_bars is False
    assert provider_config.symbology_method == SymbologyMethod.SIMPLIFIED
    assert provider_config.convert_exchange_to_mic_venue is False
    assert {str(instrument_id) for instrument_id in provider_config.load_ids} == {
        "ESU6.CME",
        "NQU6.CME",
        "YMU6.CBOT",
        "CLV6.NYMEX",
        "SPY.ARCA",
        "QQQ.NASDAQ",
        "^SPX.CBOE",
        "^VIX.CBOE",
        "NVDA.NASDAQ",
        "AAPL.NASDAQ",
        "GOOGL.NASDAQ",
        "MSFT.NASDAQ",
        "AMZN.NASDAQ",
        "TSM.NYSE",
        "AVGO.NASDAQ",
        "SPCX.NASDAQ",
        "META.NASDAQ",
        "TSLA.NASDAQ",
    }


def test_builds_v2_node_without_connecting() -> None:
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.toml")

    node = build_system_node(
        config,
        StartupPrerequisites(run_id=uuid4(), operational_persistence_ready=True),
    )

    assert str(node.trader_id) == config.runtime.trader_id
    assert node.is_running is False
