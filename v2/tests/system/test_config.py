from __future__ import annotations

from pathlib import Path

import pytest

from markeitech.system.config import load_system_config

VALID_CONFIG = """\
schema_version = 2

[runtime]
name = "MARKEITECH-V2-TEST-001"
trader_id = "MARKEITECH-001"
environment = "sandbox"

[ib]
host = "127.0.0.1"
port = 4002
client_id = 20
symbology_method = "simplified"
convert_exchange_to_mic_venue = false
market_data_type = "realtime"
use_regular_trading_hours = false
batch_quotes = true
ignore_quote_tick_size_updates = false
handle_revised_bars = false
connection_timeout_seconds = 30
request_timeout_seconds = 30

[logging]
directory = "../data/logs"
file_name = "markeitech-v2.log"

[discord]
enabled = true
request_timeout_seconds = 5

[persistence]
dsn_env = "MARKEITECH_POSTGRES_DSN"
connect_timeout_seconds = 5
queue_capacity = 64
result_poll_interval_ms = 250
shutdown_timeout_seconds = 10
write_max_attempts = 3
write_retry_backoff_ms = 100

[acquisition]
bootstrap_feeds = [
  { instrument_id = "ESU6.CME", kind = "quotes", selector = "default" },
  { instrument_id = "ESU6.CME", kind = "trades", selector = "default" },
]

[[instruments]]
id = "ESU6.CME"
"""


def test_loads_standalone_system_config(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG)

    config = load_system_config(path)

    assert config.runtime.name == "MARKEITECH-V2-TEST-001"
    assert config.ib.port == 4002
    assert config.ib.symbology_method == "simplified"
    assert config.ib.convert_exchange_to_mic_venue is False
    assert config.ib.batch_quotes is True
    assert config.ib.ignore_quote_tick_size_updates is False
    assert config.ib.handle_revised_bars is False
    assert config.logging.directory == tmp_path.parent / "data/logs"
    assert config.logging.file_name == "markeitech-v2.log"
    assert config.discord.request_timeout_seconds == 5
    assert config.discord.enabled is True
    assert config.persistence.dsn_env == "MARKEITECH_POSTGRES_DSN"
    assert config.persistence.queue_capacity == 64
    assert config.persistence.result_poll_interval_ms == 250
    assert config.persistence.write_max_attempts == 3
    assert config.persistence.write_retry_backoff_ms == 100
    assert [
        (feed.instrument_id, feed.kind, feed.selector)
        for feed in config.acquisition.bootstrap_feeds
    ] == [
        ("ESU6.CME", "quotes", "default"),
        ("ESU6.CME", "trades", "default"),
    ]
    assert [instrument.id for instrument in config.instruments] == ["ESU6.CME"]


def test_rejects_unknown_configuration(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG.replace("environment =", "legacy_option = true\nenvironment ="))

    with pytest.raises(ValueError, match="runtime has unknown keys: legacy_option"):
        load_system_config(path)


def test_rejects_duplicate_instruments(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG + '\n[[instruments]]\nid = "ESU6.CME"\n')

    with pytest.raises(ValueError, match="duplicate instrument id: ESU6.CME"):
        load_system_config(path)


def test_rejects_unknown_ib_symbology_method(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'symbology_method = "simplified"',
            'symbology_method = "guess"',
        ),
    )

    with pytest.raises(ValueError, match="unsupported ib.symbology_method: 'guess'"):
        load_system_config(path)


def test_rejects_bootstrap_feed_for_unconfigured_instrument(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG.replace("ESU6.CME\", kind", "NQU6.CME\", kind", 1))

    with pytest.raises(ValueError, match="must reference a configured instrument"):
        load_system_config(path)


def test_rejects_duplicate_bootstrap_feed(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            "]\n\n[[instruments]]",
            (
                '  { instrument_id = "ESU6.CME", kind = "quotes", '
                'selector = "default" },\n]\n\n[[instruments]]'
            ),
            1,
        ),
    )

    with pytest.raises(ValueError, match="duplicate bootstrap feed"):
        load_system_config(path)


def test_rejects_selector_for_feed_without_selector_semantics(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'kind = "quotes", selector = "default"',
            'kind = "quotes", selector = "fast"',
        ),
    )

    with pytest.raises(ValueError, match="selector must be 'default' for quotes"):
        load_system_config(path)
