from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    name: str
    trader_id: str
    environment: str


@dataclass(frozen=True, slots=True)
class InteractiveBrokersConfig:
    host: str
    port: int
    client_id: int
    symbology_method: str
    convert_exchange_to_mic_venue: bool
    market_data_type: str
    use_regular_trading_hours: bool
    batch_quotes: bool
    ignore_quote_tick_size_updates: bool
    handle_revised_bars: bool
    connection_timeout_seconds: int
    request_timeout_seconds: int


@dataclass(frozen=True, slots=True)
class InstrumentConfig:
    id: str


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    directory: Path
    file_name: str


@dataclass(frozen=True, slots=True)
class DiscordConfig:
    enabled: bool
    request_timeout_seconds: int


@dataclass(frozen=True, slots=True)
class PersistenceConfig:
    dsn_env: str
    connect_timeout_seconds: int
    queue_capacity: int
    result_poll_interval_ms: int
    shutdown_timeout_seconds: int
    write_max_attempts: int
    write_retry_backoff_ms: int


@dataclass(frozen=True, slots=True)
class SystemConfig:
    schema_version: int
    runtime: RuntimeConfig
    ib: InteractiveBrokersConfig
    logging: LoggingConfig
    discord: DiscordConfig
    persistence: PersistenceConfig
    instruments: tuple[InstrumentConfig, ...]


def load_system_config(path: str | Path) -> SystemConfig:
    config_path = Path(path)
    with config_path.open("rb") as file:
        raw = tomllib.load(file)

    _require_keys(
        raw,
        {
            "schema_version",
            "runtime",
            "ib",
            "logging",
            "discord",
            "persistence",
            "instruments",
        },
        "root",
    )
    if raw["schema_version"] != 1:
        raise ValueError(f"unsupported schema_version: {raw['schema_version']!r}")

    runtime = _load_runtime(raw["runtime"])
    ib = _load_ib(raw["ib"])
    logging = _load_logging(raw["logging"], config_path.parent)
    discord = _load_discord(raw["discord"])
    persistence = _load_persistence(raw["persistence"])
    instruments = _load_instruments(raw["instruments"])
    return SystemConfig(
        schema_version=raw["schema_version"],
        runtime=runtime,
        ib=ib,
        logging=logging,
        discord=discord,
        persistence=persistence,
        instruments=instruments,
    )


def _load_runtime(raw: Any) -> RuntimeConfig:
    values = _mapping(raw, "runtime")
    _require_keys(values, {"name", "trader_id", "environment"}, "runtime")
    environment = _non_empty_string(values["environment"], "runtime.environment").lower()
    if environment not in {"live", "sandbox"}:
        raise ValueError("runtime.environment must be 'live' or 'sandbox'")
    return RuntimeConfig(
        name=_non_empty_string(values["name"], "runtime.name"),
        trader_id=_non_empty_string(values["trader_id"], "runtime.trader_id"),
        environment=environment,
    )


def _load_ib(raw: Any) -> InteractiveBrokersConfig:
    values = _mapping(raw, "ib")
    expected = {
        "host",
        "port",
        "client_id",
        "symbology_method",
        "convert_exchange_to_mic_venue",
        "market_data_type",
        "use_regular_trading_hours",
        "batch_quotes",
        "ignore_quote_tick_size_updates",
        "handle_revised_bars",
        "connection_timeout_seconds",
        "request_timeout_seconds",
    }
    _require_keys(values, expected, "ib")
    symbology_method = _non_empty_string(
        values["symbology_method"],
        "ib.symbology_method",
    ).lower()
    if symbology_method not in {"raw", "simplified"}:
        raise ValueError(f"unsupported ib.symbology_method: {symbology_method!r}")
    market_data_type = _non_empty_string(
        values["market_data_type"],
        "ib.market_data_type",
    ).lower()
    if market_data_type not in {"realtime", "frozen", "delayed", "delayed_frozen"}:
        raise ValueError(f"unsupported ib.market_data_type: {market_data_type!r}")
    return InteractiveBrokersConfig(
        host=_non_empty_string(values["host"], "ib.host"),
        port=_positive_int(values["port"], "ib.port"),
        client_id=_non_negative_int(values["client_id"], "ib.client_id"),
        symbology_method=symbology_method,
        convert_exchange_to_mic_venue=_bool(
            values["convert_exchange_to_mic_venue"],
            "ib.convert_exchange_to_mic_venue",
        ),
        market_data_type=market_data_type,
        use_regular_trading_hours=_bool(
            values["use_regular_trading_hours"],
            "ib.use_regular_trading_hours",
        ),
        batch_quotes=_bool(values["batch_quotes"], "ib.batch_quotes"),
        ignore_quote_tick_size_updates=_bool(
            values["ignore_quote_tick_size_updates"],
            "ib.ignore_quote_tick_size_updates",
        ),
        handle_revised_bars=_bool(
            values["handle_revised_bars"],
            "ib.handle_revised_bars",
        ),
        connection_timeout_seconds=_positive_int(
            values["connection_timeout_seconds"],
            "ib.connection_timeout_seconds",
        ),
        request_timeout_seconds=_positive_int(
            values["request_timeout_seconds"],
            "ib.request_timeout_seconds",
        ),
    )


def _load_logging(raw: Any, config_directory: Path) -> LoggingConfig:
    values = _mapping(raw, "logging")
    _require_keys(values, {"directory", "file_name"}, "logging")
    directory = Path(_non_empty_string(values["directory"], "logging.directory"))
    if not directory.is_absolute():
        directory = (config_directory / directory).resolve()
    return LoggingConfig(
        directory=directory,
        file_name=_non_empty_string(values["file_name"], "logging.file_name"),
    )


def _load_discord(raw: Any) -> DiscordConfig:
    values = _mapping(raw, "discord")
    _require_keys(values, {"enabled", "request_timeout_seconds"}, "discord")
    return DiscordConfig(
        enabled=_bool(values["enabled"], "discord.enabled"),
        request_timeout_seconds=_positive_int(
            values["request_timeout_seconds"],
            "discord.request_timeout_seconds",
        ),
    )


def _load_persistence(raw: Any) -> PersistenceConfig:
    values = _mapping(raw, "persistence")
    _require_keys(
        values,
        {
            "dsn_env",
            "connect_timeout_seconds",
            "queue_capacity",
            "result_poll_interval_ms",
            "shutdown_timeout_seconds",
            "write_max_attempts",
            "write_retry_backoff_ms",
        },
        "persistence",
    )
    return PersistenceConfig(
        dsn_env=_non_empty_string(values["dsn_env"], "persistence.dsn_env"),
        connect_timeout_seconds=_positive_int(
            values["connect_timeout_seconds"],
            "persistence.connect_timeout_seconds",
        ),
        queue_capacity=_positive_int(values["queue_capacity"], "persistence.queue_capacity"),
        result_poll_interval_ms=_positive_int(
            values["result_poll_interval_ms"],
            "persistence.result_poll_interval_ms",
        ),
        shutdown_timeout_seconds=_positive_int(
            values["shutdown_timeout_seconds"],
            "persistence.shutdown_timeout_seconds",
        ),
        write_max_attempts=_positive_int(
            values["write_max_attempts"],
            "persistence.write_max_attempts",
        ),
        write_retry_backoff_ms=_non_negative_int(
            values["write_retry_backoff_ms"],
            "persistence.write_retry_backoff_ms",
        ),
    )


def _load_instruments(raw: Any) -> tuple[InstrumentConfig, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("instruments must be a non-empty array")
    instruments: list[InstrumentConfig] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        values = _mapping(item, f"instruments[{index}]")
        _require_keys(values, {"id"}, f"instruments[{index}]")
        instrument_id = _non_empty_string(values["id"], f"instruments[{index}].id")
        if instrument_id in seen:
            raise ValueError(f"duplicate instrument id: {instrument_id}")
        seen.add(instrument_id)
        instruments.append(InstrumentConfig(id=instrument_id))
    return tuple(instruments)


def _require_keys(values: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(values)
    missing = expected - actual
    unknown = actual - expected
    if missing:
        raise ValueError(f"{label} missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"{label} has unknown keys: {', '.join(sorted(unknown))}")


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a table")
    return value


def _non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _non_negative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value
