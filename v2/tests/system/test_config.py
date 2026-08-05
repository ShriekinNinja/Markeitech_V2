from __future__ import annotations

from pathlib import Path

import pytest

from markeitech.system.config import load_system_config

VALID_CONFIG = """\
schema_version = 1

[runtime]
name = "MARKEITECH-V2-TEST-001"
trader_id = "MARKEITECH-001"
environment = "sandbox"

[ib]
host = "127.0.0.1"
port = 4002
client_id = 20
market_data_type = "realtime"
use_regular_trading_hours = false
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

[[instruments]]
id = "ESU6.CME"
"""


def test_loads_standalone_system_config(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG)

    config = load_system_config(path)

    assert config.runtime.name == "MARKEITECH-V2-TEST-001"
    assert config.ib.port == 4002
    assert config.logging.directory == tmp_path.parent / "data/logs"
    assert config.logging.file_name == "markeitech-v2.log"
    assert config.discord.request_timeout_seconds == 5
    assert config.discord.enabled is True
    assert config.persistence.dsn_env == "MARKEITECH_POSTGRES_DSN"
    assert config.persistence.queue_capacity == 64
    assert config.persistence.result_poll_interval_ms == 250
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
