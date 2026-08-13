from __future__ import annotations

from pathlib import Path

import pytest

from markeitech.system.config import load_system_config

VALID_CONFIG = """\
schema_version = 5

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
native_consumer_probe_enabled = true
native_consumer_probe_unsubscribe_after_seconds = 15
[[watchlist.members]]
instrument_id = "ESU6.CME"
owner_ids = ["config:system"]
capabilities = ["top_of_book", "watchlist_last"]
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
    assert config.acquisition.native_consumer_probe_enabled is True
    assert config.acquisition.native_consumer_probe_unsubscribe_after_seconds == 15
    assert config.instrument_ids == ("ESU6.CME",)
    assert config.watchlist.members[0].owner_ids == ("config:system",)
    assert config.watchlist.members[0].capabilities == ("top_of_book", "watchlist_last")


def test_rejects_unknown_configuration(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG.replace("environment =", "legacy_option = true\nenvironment ="))

    with pytest.raises(ValueError, match="runtime has unknown keys: legacy_option"):
        load_system_config(path)


def test_rejects_duplicate_watchlist_instruments(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG
        + '\n[[watchlist.members]]\ninstrument_id = "ESU6.CME"\n'
        + 'owner_ids = ["config:system"]\n'
        + 'capabilities = ["top_of_book", "watchlist_last"]\n',
    )

    with pytest.raises(ValueError, match="duplicate watchlist instrument id: ESU6.CME"):
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


def test_rejects_removed_bootstrap_feed_configuration(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            "native_consumer_probe_enabled = true",
            "native_consumer_probe_enabled = true\nbootstrap_feeds = []",
        ),
    )

    with pytest.raises(ValueError, match="acquisition has unknown keys: bootstrap_feeds"):
        load_system_config(path)


def test_rejects_incomplete_watchlist_capabilities(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'capabilities = ["top_of_book", "watchlist_last"]',
            'capabilities = ["top_of_book"]',
        ),
    )

    with pytest.raises(ValueError, match="capabilities must contain exactly"):
        load_system_config(path)


def test_rejects_duplicate_watchlist_owners(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'owner_ids = ["config:system"]',
            'owner_ids = ["config:system", "config:system"]',
        ),
    )

    with pytest.raises(ValueError, match="owner_ids must contain unique values"):
        load_system_config(path)
