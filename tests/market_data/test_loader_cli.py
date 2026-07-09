from datetime import date
from pathlib import Path

import pytest
from markeitech.domain import InstrumentDataMode, InstrumentRole, WarmupTimeframe
from markeitech.market_data.cli import build_plan_summary
from markeitech.market_data.loader import (
    load_market_data_runtime_config,
    parse_market_data_runtime_config,
)
from pydantic import ValidationError


def raw_config() -> dict[str, object]:
    return {
        "runtime": {
            "active_instrument_id": "NQU6.CME",
            "trader_id": "MARK-001",
            "data_only": True,
            "run_live_node": False,
        },
        "ib": {
            "host": "127.0.0.1",
            "port": 7497,
            "client_id": 3,
            "read_only": True,
        },
        "instruments": [
            {
                "role": "active",
                "data_mode": "tick_by_tick",
                "analysis_profile": "active_tick",
                "contract": {
                    "root_symbol": "NQ",
                    "exchange": "CME",
                    "instrument_id": "NQU6.CME",
                    "security_type": "FUT",
                    "ib_symbol": "NQ",
                    "ib_exchange": "CME",
                    "ib_security_type": "FUT",
                    "expiry": date(2026, 9, 18),
                    "ib_last_trade_date_or_contract_month": "20260918",
                },
                "warmup": {
                    "lookback_sessions": 5,
                    "timeframes": ["1m", "5m", "15m"],
                },
            },
            {
                "role": "background",
                "data_mode": "live_1m_bars",
                "analysis_profile": "background_bar",
                "contract": {
                    "root_symbol": "SPX",
                    "exchange": "CBOE",
                    "instrument_id": "^SPX.CBOE",
                    "security_type": "IND",
                    "ib_symbol": "SPX",
                    "ib_exchange": "CBOE",
                    "ib_security_type": "IND",
                },
                "warmup": {
                    "lookback_sessions": 10,
                    "timeframes": ["1m", "30m", "1d"],
                },
            },
        ],
    }


def test_parse_market_data_runtime_config() -> None:
    config = parse_market_data_runtime_config(raw_config())

    assert config.trader_id == "MARK-001"
    assert config.ib.client_id == 3
    assert config.instrument_registry.active_instrument_id == "NQU6.CME"
    assert config.instrument_registry.active_runtime.role == InstrumentRole.ACTIVE
    background = config.instrument_registry.instruments[1]
    assert background.data_mode == InstrumentDataMode.LIVE_1M_BARS
    assert background.warmup is not None
    assert WarmupTimeframe.DAILY in background.warmup.timeframes


def test_parse_rejects_runtime_that_would_start_livenode() -> None:
    raw = raw_config()
    raw["runtime"]["run_live_node"] = True  # type: ignore[index]

    with pytest.raises(ValidationError, match="must not start"):
        parse_market_data_runtime_config(raw)


def test_loads_checked_in_example_config() -> None:
    config = load_market_data_runtime_config(Path("config/market-data.example.toml"))

    assert config.instrument_registry.active_instrument_id == "NQU6.CME"
    assert len(config.instrument_registry.instruments) == 3


def test_cli_plan_summary_for_checked_in_example() -> None:
    summary = build_plan_summary(Path("config/market-data.example.toml"))

    assert summary["active_instrument_id"] == "NQU6.CME"
    assert summary["data_client_names"] == ["IB"]
    assert summary["execution_clients"] == []
    assert summary["run_live_node"] is False
    assert len(summary["planned_warmups"]) == 3
    assert {"instrument_id": "NQU6.CME", "kind": "tick_last", "source": "nautilus_ib"} in summary[
        "planned_subscriptions"
    ]
    assert {
        "instrument_id": "NQU6.CME",
        "kind": "subscribe_trade_ticks",
        "data_client_name": "IB",
        "bar_type": None,
    } in summary["nautilus_subscription_intents"]
    assert {
        "instrument_id": "ESU6.CME",
        "kind": "subscribe_bars",
        "data_client_name": "IB",
        "bar_type": "ESU6.CME-1-MINUTE-LAST-EXTERNAL",
    } in summary["nautilus_subscription_intents"]
