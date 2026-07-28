from datetime import date
from pathlib import Path

import pytest
from markeitech.domain import (
    CryptoContractConfig,
    InstrumentDataMode,
    InstrumentRole,
    WarmupTimeframe,
)
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
                    "calendar_id": "CME_Equity",
                    "session_profile": "full",
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
                    "calendar_id": "NYSE",
                    "session_profile": "regular",
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
    assert config.instrument_registry.active_runtime.contract.calendar_id == "CME_Equity"
    assert config.instrument_registry.active_runtime.contract.session_profile.value == "full"
    background = config.instrument_registry.instruments[1]
    assert background.data_mode == InstrumentDataMode.LIVE_1M_BARS
    assert background.warmup is not None
    assert WarmupTimeframe.DAILY in background.warmup.timeframes
    assert config.persistence is None


def test_parse_optional_persistence_runtime_config(tmp_path: Path) -> None:
    raw = raw_config()
    raw["persistence"] = {
        "catalog_path": tmp_path / "catalog",
        "metadata_path": tmp_path / "metadata.sqlite3",
        "journal_path": tmp_path / "journal",
        "catalog_writer_queue_size": 25,
        "catalog_batch_size": 10,
    }

    config = parse_market_data_runtime_config(raw)

    assert config.persistence is not None
    assert config.persistence.catalog_path == tmp_path / "catalog"
    assert config.persistence.catalog_writer_queue_size == 25


def test_parse_optional_runtime_file_logging_config(tmp_path: Path) -> None:
    raw = raw_config()
    raw["logging"] = {
        "enabled": True,
        "directory": tmp_path / "logs",
        "file_name": "live-review",
        "max_file_size_bytes": 1024,
        "max_backup_count": 2,
    }

    config = parse_market_data_runtime_config(raw)

    assert config.logging.enabled is True
    assert config.logging.directory == tmp_path / "logs"
    assert config.logging.file_name == "live-review"
    assert config.logging.max_file_size_bytes == 1024
    assert config.logging.max_backup_count == 2


def test_parse_operator_context_config() -> None:
    raw = raw_config()
    raw["operator_context"] = {"enabled": False, "interval_seconds": 90}

    config = parse_market_data_runtime_config(raw)

    assert config.operator_context.enabled is False
    assert config.operator_context.interval_seconds == 90


def test_parse_domain_event_config() -> None:
    raw = raw_config()
    raw["domain_events"] = {
        "enabled": True,
        "queue_size": 32,
        "drain_batch_size": 8,
        "operator_dedupe_size": 128,
    }

    config = parse_market_data_runtime_config(raw)

    assert config.domain_events.enabled is True
    assert config.domain_events.queue_size == 32
    assert config.domain_events.drain_batch_size == 8
    assert config.domain_events.operator_dedupe_size == 128


def test_parse_named_signal_definitions_and_instrument_enablement(tmp_path: Path) -> None:
    raw = raw_config()
    raw["persistence"] = {
        "catalog_path": tmp_path / "catalog",
        "metadata_path": tmp_path / "metadata.sqlite3",
        "journal_path": tmp_path / "journal",
    }
    raw["signals"] = {
        "definitions": [
            {
                "definition_id": "intraday_context",
                "evaluation_timeframe": "1m",
                "primary_direction_timeframes": ["15m", "5m"],
                "confirmation_timeframes": ["1m"],
                "minimum_confirmation_count": 1,
                "context_timeframes": ["1d"],
            }
        ],
        "enabled_definition_ids_by_instrument": {
            "NQU6.CME": ["intraday_context"],
        },
    }

    config = parse_market_data_runtime_config(raw)

    assert config.signals is not None
    definition = config.signals.enabled_definitions("NQU6.CME")[0]
    assert definition.definition_id == "intraday_context"
    assert [timeframe.value for timeframe in definition.primary_direction_timeframes] == [
        "15m",
        "5m",
    ]


def test_enabled_signals_require_persistence_and_matching_warmup() -> None:
    raw = raw_config()
    raw["signals"] = {
        "definitions": [
            {
                "definition_id": "intraday_context",
                "primary_direction_timeframes": ["1h", "15m"],
            }
        ],
        "enabled_definition_ids_by_instrument": {
            "NQU6.CME": ["intraday_context"],
        },
    }

    with pytest.raises(ValidationError, match="require durable persistence"):
        parse_market_data_runtime_config(raw)

    raw["persistence"] = {}
    with pytest.raises(ValidationError, match="requires warmup timeframes.*1h"):
        parse_market_data_runtime_config(raw)


def test_enabled_location_policy_requires_its_configured_timeframes() -> None:
    raw = raw_config()
    raw["persistence"] = {}
    raw["signals"] = {
        "definitions": [
            {
                "definition_id": "intraday_context",
                "primary_direction_timeframes": ["15m"],
                "location_policy": {
                    "sources": [
                        {
                            "source_kind": "structural_level",
                            "timeframes": ["30m"],
                        }
                    ]
                },
            }
        ],
        "enabled_definition_ids_by_instrument": {
            "NQU6.CME": ["intraday_context"],
        },
    }

    with pytest.raises(ValidationError, match="requires warmup timeframes.*30m"):
        parse_market_data_runtime_config(raw)


def test_parse_crypto_market_data_runtime_config() -> None:
    raw = raw_config()
    raw["runtime"]["active_instrument_id"] = "BTC/USD.PAXOS"  # type: ignore[index]
    raw["instruments"] = [  # type: ignore[index]
        {
            "role": "active",
            "data_mode": "tick_by_tick",
            "analysis_profile": "active_tick",
            "contract": {
                "root_symbol": "BTC",
                "exchange": "PAXOS",
                "instrument_id": "BTC/USD.PAXOS",
                "security_type": "CRYPTO",
                "ib_symbol": "BTC",
                "ib_exchange": "PAXOS",
                "ib_security_type": "CRYPTO",
                "quote_currency": "USD",
                "session_timezone": "UTC",
                "calendar_id": "24/7",
                "session_profile": "continuous",
            },
            "warmup": {"lookback_sessions": 1, "timeframes": ["1m"]},
        },
    ]

    config = parse_market_data_runtime_config(raw)

    assert isinstance(config.instrument_registry.active_runtime.contract, CryptoContractConfig)
    assert config.instrument_registry.active_instrument_id == "BTC/USD.PAXOS"


def test_parse_rejects_runtime_that_would_start_livenode() -> None:
    raw = raw_config()
    raw["runtime"]["run_live_node"] = True  # type: ignore[index]

    with pytest.raises(ValidationError, match="manual_live_node_start"):
        parse_market_data_runtime_config(raw)


def test_loads_checked_in_example_config() -> None:
    config = load_market_data_runtime_config(Path("config/market-data.example.toml"))

    assert config.instrument_registry.active_instrument_id == "NQU6.CME"
    assert len(config.instrument_registry.instruments) == 10
    assert config.persistence is not None
    assert config.signals is not None
    assert {item.definition_id for item in config.signals.definitions} == {
        "intraday_context"
    }
    assert config.signals.enabled_definition_ids_by_instrument == {}
    assert config.signals.enabled_definitions("NQU6.CME") == ()
    assert config.signals.enabled_definitions("ESU6.CME") == ()
    order_flow = {
        runtime.contract.instrument_id: runtime.large_trade_threshold
        for runtime in config.instrument_registry.order_flow_runtimes
    }
    assert order_flow == {
        "NQU6.CME": 40,
        "ESU6.CME": 120,
    }


@pytest.mark.parametrize(
    ("path", "expected_instruments"),
    (
        (Path("config/market-data.live.toml"), 10),
        (Path("config/market-data.test.toml"), 2),
    ),
)
def test_live_and_test_configs_have_explicit_instrument_scope(
    path: Path,
    expected_instruments: int,
) -> None:
    config = load_market_data_runtime_config(path)
    enabled = tuple(
        runtime for runtime in config.instrument_registry.instruments if runtime.enabled
    )

    assert len(enabled) == expected_instruments
    assert config.instrument_registry.active_instrument_id == "ESU6.CME"
    assert config.signals is not None
    assert config.signals.enabled_definition_ids_by_instrument == {}
    assert config.signals.enabled_definitions("NQU6.CME") == ()
    assert config.signals.enabled_definitions("ESU6.CME") == ()
    assert {
        route.destination_key: route.environment_variable
        for route in config.discord.routes
    }["operator-flow"] == "MARKEITECH_DISCORD_OPERATOR_FLOW_WEBHOOK"
    assert {
        runtime.contract.instrument_id: runtime.large_trade_threshold
        for runtime in config.instrument_registry.order_flow_runtimes
    } == {"NQU6.CME": 250, "ESU6.CME": 500}
    if expected_instruments == 2:
        assert {
            runtime.contract.instrument_id
            for runtime in enabled
        } == {"NQU6.CME", "ESU6.CME"}


def test_cli_plan_summary_for_checked_in_example() -> None:
    summary = build_plan_summary(Path("config/market-data.example.toml"))

    assert summary["active_instrument_id"] == "NQU6.CME"
    assert summary["data_client_names"] == ["IB"]
    assert summary["execution_clients"] == []
    assert summary["run_live_node"] is False
    assert summary["bootstrap"] == {
        "schema_version": "1.0",
        "can_build_node": True,
        "will_start_node": False,
        "data_only": True,
        "read_only_ib": True,
        "execution_clients_enabled": False,
        "data_client_name": "IB",
        "persistence_enabled": True,
    }
    assert len(summary["planned_warmups"]) == 10
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
    assert {
        "instrument_id": "NQU6.CME",
        "kind": "subscribe_trade_ticks",
        "phase": "live_subscription",
        "data_client_name": "IB",
        "bar_type": None,
        "lookback_sessions": None,
    } in summary["livenode_actions"]
    assert {
        "instrument_id": "NQU6.CME",
        "kind": "request_historical_bars",
        "phase": "warmup",
        "data_client_name": "IB",
        "bar_type": "NQU6.CME-1-MINUTE-LAST-EXTERNAL",
        "lookback_sessions": 5,
    } in summary["livenode_actions"]
