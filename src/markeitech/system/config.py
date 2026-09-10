from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas_market_calendars as market_calendars

from markeitech.dashboard.config import DashboardConfig


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
class InteractiveBrokersExecutionConfig:
    """Select optional native IB execution connectivity for one explicit account.

    Connection and instrument-provider settings are shared with ``ib``. Enabling
    this client does not add an application order-submission interface.
    """

    enabled: bool
    client_id: int
    account_id: str


@dataclass(frozen=True, slots=True)
class RiskEngineConfig:
    """Configure native risk-check bypass; other native settings retain their defaults."""

    bypass: bool


@dataclass(frozen=True, slots=True)
class WatchlistMemberConfig:
    instrument_id: str
    calendar_id: str
    owner_ids: tuple[str, ...]
    capabilities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WatchlistConfig:
    consumer_retry_interval_ms: int
    members: tuple[WatchlistMemberConfig, ...]
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class HistoricalConfig:
    maximum_plan_requests: int
    maximum_observations_per_request: int
    maximum_total_observations: int
    maximum_outstanding_requests: int
    maximum_in_flight_requests: int
    timeout_seconds: int
    maximum_attempts: int
    retry_backoff_ms: int
    poll_interval_ms: int


@dataclass(frozen=True, slots=True)
class SessionPhaseConfig:
    name: str
    timezone: str
    start_kind: str
    start_value: str
    start_day_offset: int
    end_kind: str
    end_value: str
    end_day_offset: int
    exchange_constraint: str


@dataclass(frozen=True, slots=True)
class CalendarSourceConfig:
    source_id: str
    title: str
    url: str
    retrieved_at_ns: int
    content_sha256: str | None
    retrieval_status: str


@dataclass(frozen=True, slots=True)
class CalendarCorrectionConfig:
    correction_id: str
    kind: str
    source_id: str
    product_roots: tuple[str, ...]
    effective_from_trade_date: str
    timezone: str
    expected_start: str
    expected_end: str


@dataclass(frozen=True, slots=True)
class SessionCalendarConfig:
    calendar_id: str
    calendar_engine: str
    calendar_engine_version: str
    provider_calendar: str
    provider_calendar_class: str
    exchange_timezone: str
    schedule_columns: tuple[str, ...]
    definition_version: int
    effective_from_ns: int
    definition_digest: str
    schedule_version: str
    phases: tuple[SessionPhaseConfig, ...]
    corrections: tuple[CalendarCorrectionConfig, ...]
    sources: tuple[CalendarSourceConfig, ...]


@dataclass(frozen=True, slots=True)
class ProjectionRetryConfig:
    response_timeout_ms: int
    maximum_attempts: int
    retry_backoff_ms: int
    maximum_elapsed_ms: int


@dataclass(frozen=True, slots=True)
class CurrentStateDeliveryConfig:
    """Bound current-session snapshot delivery and consumer reconciliation.

    All durations are positive integer milliseconds. Buffer limits bound transient consumer
    synchronization state; they do not authorize persistence of calendar snapshots.

    Attributes:
        policy_version: Exact supported delivery-policy version.
        response_timeout_ms: Per-attempt response timeout in milliseconds.
        maximum_attempts: Maximum attempts in one synchronization cycle.
        retry_backoff_ms: Fixed retry delay in milliseconds.
        maximum_elapsed_ms: Maximum total synchronization-cycle duration in milliseconds.
        maximum_buffered_transitions_per_calendar: Per-calendar consumer transition bound.
        maximum_total_buffered_transitions: Total consumer transition bound.
        boundary_delivery_grace_ms: Grace period for transition/response reordering in
            milliseconds.
    """

    policy_version: int
    response_timeout_ms: int
    maximum_attempts: int
    retry_backoff_ms: int
    maximum_elapsed_ms: int
    maximum_buffered_transitions_per_calendar: int
    maximum_total_buffered_transitions: int
    boundary_delivery_grace_ms: int


@dataclass(frozen=True, slots=True)
class SessionsConfig:
    evaluation_interval_ms: int
    projection_lookback_days: int
    projection_lookahead_days: int
    maximum_projection_days: int
    maximum_calendars_per_request: int
    projection_retry: ProjectionRetryConfig
    current_state_delivery: CurrentStateDeliveryConfig
    catalog_id: str
    catalog_version: int
    catalog_path: Path
    catalog_digest: str
    available_calendars: tuple[SessionCalendarConfig, ...]
    calendars: tuple[SessionCalendarConfig, ...]


@dataclass(frozen=True, slots=True)
class EvidencePolicyConfig:
    feed_kind: str
    selector: str
    fresh_for_ms: int
    stale_after_ms: int
    unavailable_after_ms: int
    adaptive: bool
    minimum_samples: int
    decay_factor: float
    fresh_stddev_multiplier: float
    stale_stddev_multiplier: float
    unavailable_stddev_multiplier: float
    min_fresh_ms: int
    max_fresh_ms: int
    min_stale_ms: int
    max_stale_ms: int
    min_unavailable_ms: int
    max_unavailable_ms: int


@dataclass(frozen=True, slots=True)
class EvidenceHealthConfig:
    evaluation_interval_ms: int
    consumer_retry_interval_ms: int
    provider_id: str
    profile_checkpoint_samples: int
    policies: tuple[EvidencePolicyConfig, ...]






@dataclass(frozen=True, slots=True)
class LoggingConfig:
    directory: Path
    file_name: str


@dataclass(frozen=True, slots=True)
class DiscordConfig:
    enabled: bool
    request_timeout_seconds: int
    queue_capacity: int
    ping_critical_resource_alerts: bool


@dataclass(frozen=True, slots=True)
class RuntimeResourceThresholdConfig:
    host_memory_available_percent: float
    host_cpu_percent: float
    host_swap_percent: float
    disk_free_bytes: int
    disk_free_percent: float
    process_rss_bytes: int
    process_rss_growth_bytes: int
    process_cpu_percent: float
    thread_count: int
    open_fd_ratio: float

    def to_dict(self) -> dict[str, int | float]:
        return {
            "host_memory_available_percent": self.host_memory_available_percent,
            "host_cpu_percent": self.host_cpu_percent,
            "host_swap_percent": self.host_swap_percent,
            "disk_free_bytes": self.disk_free_bytes,
            "disk_free_percent": self.disk_free_percent,
            "rss_bytes": self.process_rss_bytes,
            "rss_growth_bytes": self.process_rss_growth_bytes,
            "cpu_percent": self.process_cpu_percent,
            "thread_count": self.thread_count,
            "open_fd_ratio": self.open_fd_ratio,
        }


@dataclass(frozen=True, slots=True)
class RuntimeResourceHealthConfig:
    enabled: bool
    threshold_version: str
    warning_consecutive_samples: int
    critical_consecutive_samples: int
    recovery_consecutive_samples: int
    notification_cooldown_ms: int
    rss_growth_window_samples: int
    stale_warning_ms: int
    stale_critical_ms: int
    warning: RuntimeResourceThresholdConfig
    critical: RuntimeResourceThresholdConfig


@dataclass(frozen=True, slots=True)
class RuntimeResourcesConfig:
    enabled: bool
    sample_interval_ms: int
    log_every_samples: int
    include_cache_counts: bool
    disk_path: str
    health: RuntimeResourceHealthConfig


@dataclass(frozen=True, slots=True)
class PersistenceConfig:
    dsn_env: str
    connect_timeout_seconds: int
    queue_capacity: int
    critical_queue_reserve: int
    write_batch_size: int
    result_poll_interval_ms: int
    shutdown_timeout_seconds: int
    write_max_attempts: int
    write_retry_backoff_ms: int


@dataclass(frozen=True, slots=True)
class SystemConfig:
    """Hold the fully validated, immutable V2 runtime configuration."""

    schema_version: int
    runtime: RuntimeConfig
    ib: InteractiveBrokersConfig
    ib_execution: InteractiveBrokersExecutionConfig
    risk_engine: RiskEngineConfig
    logging: LoggingConfig
    discord: DiscordConfig
    runtime_resources: RuntimeResourcesConfig
    persistence: PersistenceConfig
    historical: HistoricalConfig
    watchlist: WatchlistConfig
    sessions: SessionsConfig
    evidence_health: EvidenceHealthConfig
    dashboard: DashboardConfig = DashboardConfig()

    @property
    def instrument_ids(self) -> tuple[str, ...]:
        return tuple(member.instrument_id for member in self.watchlist.members)


def load_system_config(path: str | Path) -> SystemConfig:
    """Load and validate one schema-versioned V2 TOML configuration.

    Relative filesystem paths are resolved against the configuration file's
    directory. The loader performs no provider, database, or runtime connection.

    Args:
        path: Filesystem path to the V2 TOML configuration.

    Returns:
        The normalized immutable system configuration.

    Raises:
        OSError: If the configuration file cannot be opened.
        tomllib.TOMLDecodeError: If the file is not valid TOML.
        ValueError: If schema identity, fields, values, or cross-references are invalid.
    """

    config_path = Path(path)
    with config_path.open("rb") as file:
        raw = tomllib.load(file)

    if raw.get("schema_version") != 27:
        raise ValueError(f"unsupported schema_version: {raw.get('schema_version')!r}; expected 27")

    root_keys = {
        "schema_version",
        "runtime",
        "ib",
        "ib_execution",
        "risk_engine",
        "logging",
        "discord",
        "runtime_resources",
        "persistence",
        "historical",
        "watchlist",
        "sessions",
        "evidence_health",
    }
    _require_keys(
        raw,
        root_keys | ({"dashboard"} if "dashboard" in raw else set()),
        "root",
    )

    runtime = _load_runtime(raw["runtime"])
    ib = _load_ib(raw["ib"])
    ib_execution = _load_ib_execution(raw["ib_execution"])
    risk_engine = _load_risk_engine(raw["risk_engine"])
    if ib_execution.enabled and ib_execution.client_id == ib.client_id:
        raise ValueError("ib_execution.client_id must differ from ib.client_id when enabled")
    logging = _load_logging(raw["logging"], config_path.parent)
    discord = _load_discord(raw["discord"])
    runtime_resources = _load_runtime_resources(raw["runtime_resources"])
    persistence = _load_persistence(raw["persistence"])
    watchlist = _load_watchlist(raw["watchlist"])
    historical = _load_historical(raw["historical"])
    sessions = _load_sessions(raw["sessions"], config_path.parent)
    evidence_health = _load_evidence_health(raw["evidence_health"])
    dashboard = DashboardConfig.from_mapping(raw.get("dashboard", {}))
    if dashboard.enabled and len(watchlist.members) > dashboard.maximum_instruments:
        raise ValueError("dashboard maximum_instruments is below watchlist size")
    known_calendars = {calendar.calendar_id for calendar in sessions.calendars}
    unknown_calendars = sorted(
        {member.calendar_id for member in watchlist.members} - known_calendars,
    )
    if unknown_calendars:
        raise ValueError(
            f"watchlist references unknown calendars: {', '.join(unknown_calendars)}",
        )
    available_policies = {
        (policy.feed_kind, policy.selector) for policy in evidence_health.policies
    }
    required_policies: set[tuple[str, str]] = set()
    for member in watchlist.members:
        if "top_of_book" in member.capabilities:
            required_policies.add(("quotes", "default"))
        if "watchlist_last" in member.capabilities:
            required_policies.add(("bars", "5-SECOND-LAST-EXTERNAL"))
    missing_policies = sorted(required_policies - available_policies)
    if missing_policies:
        formatted = ", ".join(f"{kind}/{selector}" for kind, selector in missing_policies)
        raise ValueError(f"watchlist feeds lack evidence-health policies: {formatted}")
    feed_count = sum(len(member.capabilities) for member in watchlist.members)
    minimum_normal_capacity = feed_count * 4 + len(watchlist.members) * 2 + 16
    normal_capacity = persistence.queue_capacity - persistence.critical_queue_reserve
    if normal_capacity < minimum_normal_capacity:
        raise ValueError(
            "persistence normal queue capacity is below the configured startup event envelope: "
            f"capacity={normal_capacity}, required={minimum_normal_capacity}",
        )
    return SystemConfig(
        schema_version=raw["schema_version"],
        runtime=runtime,
        ib=ib,
        ib_execution=ib_execution,
        risk_engine=risk_engine,
        logging=logging,
        discord=discord,
        runtime_resources=runtime_resources,
        persistence=persistence,
        historical=historical,
        watchlist=watchlist,
        sessions=sessions,
        evidence_health=evidence_health,
        dashboard=dashboard,
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


def _load_ib_execution(raw: Any) -> InteractiveBrokersExecutionConfig:
    values = _mapping(raw, "ib_execution")
    _require_keys(values, {"enabled", "client_id", "account_id"}, "ib_execution")
    enabled = _bool(values["enabled"], "ib_execution.enabled")
    client_id = _positive_int(values["client_id"], "ib_execution.client_id")
    if client_id > 2_147_483_647 or client_id % 1000 == 0:
        raise ValueError(
            "ib_execution.client_id must fit a signed 32-bit integer and not be a multiple of 1000",
        )
    account_id = values["account_id"]
    if not isinstance(account_id, str):
        raise ValueError("ib_execution.account_id must be a string")
    account_id = account_id.strip()
    if enabled and not account_id:
        raise ValueError("ib_execution.account_id must be nonempty when enabled")
    return InteractiveBrokersExecutionConfig(enabled, client_id, account_id)


def _load_risk_engine(raw: Any) -> RiskEngineConfig:
    values = _mapping(raw, "risk_engine")
    _require_keys(values, {"bypass"}, "risk_engine")
    return RiskEngineConfig(bypass=_bool(values["bypass"], "risk_engine.bypass"))


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
    _require_keys(
        values,
        {
            "enabled",
            "request_timeout_seconds",
            "queue_capacity",
            "ping_critical_resource_alerts",
        },
        "discord",
    )
    return DiscordConfig(
        enabled=_bool(values["enabled"], "discord.enabled"),
        request_timeout_seconds=_positive_int(
            values["request_timeout_seconds"],
            "discord.request_timeout_seconds",
        ),
        queue_capacity=_positive_int(values["queue_capacity"], "discord.queue_capacity"),
        ping_critical_resource_alerts=_bool(
            values["ping_critical_resource_alerts"],
            "discord.ping_critical_resource_alerts",
        ),
    )


def _load_runtime_resources(raw: Any) -> RuntimeResourcesConfig:
    values = _mapping(raw, "runtime_resources")
    _require_keys(
        values,
        {
            "enabled",
            "sample_interval_ms",
            "log_every_samples",
            "include_cache_counts",
            "disk_path",
            "health",
        },
        "runtime_resources",
    )
    health_values = _mapping(values["health"], "runtime_resources.health")
    _require_keys(
        health_values,
        {
            "enabled",
            "threshold_version",
            "warning_consecutive_samples",
            "critical_consecutive_samples",
            "recovery_consecutive_samples",
            "notification_cooldown_ms",
            "rss_growth_window_samples",
            "stale_warning_ms",
            "stale_critical_ms",
            "warning",
            "critical",
        },
        "runtime_resources.health",
    )
    warning = _load_runtime_resource_thresholds(
        health_values["warning"],
        "runtime_resources.health.warning",
    )
    critical = _load_runtime_resource_thresholds(
        health_values["critical"],
        "runtime_resources.health.critical",
    )
    _validate_runtime_resource_threshold_order(warning, critical)
    stale_warning_ms = _positive_int(
        health_values["stale_warning_ms"],
        "runtime_resources.health.stale_warning_ms",
    )
    stale_critical_ms = _positive_int(
        health_values["stale_critical_ms"],
        "runtime_resources.health.stale_critical_ms",
    )
    if stale_critical_ms <= stale_warning_ms:
        raise ValueError(
            "runtime_resources.health.stale_critical_ms must exceed stale_warning_ms",
        )
    return RuntimeResourcesConfig(
        enabled=_bool(values["enabled"], "runtime_resources.enabled"),
        sample_interval_ms=_positive_int(
            values["sample_interval_ms"],
            "runtime_resources.sample_interval_ms",
        ),
        log_every_samples=_positive_int(
            values["log_every_samples"],
            "runtime_resources.log_every_samples",
        ),
        include_cache_counts=_bool(
            values["include_cache_counts"],
            "runtime_resources.include_cache_counts",
        ),
        disk_path=_non_empty_string(values["disk_path"], "runtime_resources.disk_path"),
        health=RuntimeResourceHealthConfig(
            enabled=_bool(health_values["enabled"], "runtime_resources.health.enabled"),
            threshold_version=_non_empty_string(
                health_values["threshold_version"],
                "runtime_resources.health.threshold_version",
            ),
            warning_consecutive_samples=_positive_int(
                health_values["warning_consecutive_samples"],
                "runtime_resources.health.warning_consecutive_samples",
            ),
            critical_consecutive_samples=_positive_int(
                health_values["critical_consecutive_samples"],
                "runtime_resources.health.critical_consecutive_samples",
            ),
            recovery_consecutive_samples=_positive_int(
                health_values["recovery_consecutive_samples"],
                "runtime_resources.health.recovery_consecutive_samples",
            ),
            notification_cooldown_ms=_positive_int(
                health_values["notification_cooldown_ms"],
                "runtime_resources.health.notification_cooldown_ms",
            ),
            rss_growth_window_samples=_positive_int(
                health_values["rss_growth_window_samples"],
                "runtime_resources.health.rss_growth_window_samples",
            ),
            stale_warning_ms=stale_warning_ms,
            stale_critical_ms=stale_critical_ms,
            warning=warning,
            critical=critical,
        ),
    )


def _load_runtime_resource_thresholds(
    raw: Any,
    label: str,
) -> RuntimeResourceThresholdConfig:
    values = _mapping(raw, label)
    keys = {
        "host_memory_available_percent",
        "host_cpu_percent",
        "host_swap_percent",
        "disk_free_bytes",
        "disk_free_percent",
        "process_rss_bytes",
        "process_rss_growth_bytes",
        "process_cpu_percent",
        "thread_count",
        "open_fd_ratio",
    }
    _require_keys(values, keys, label)
    return RuntimeResourceThresholdConfig(
        host_memory_available_percent=_percentage(
            values["host_memory_available_percent"],
            f"{label}.host_memory_available_percent",
        ),
        host_cpu_percent=_percentage(
            values["host_cpu_percent"],
            f"{label}.host_cpu_percent",
        ),
        host_swap_percent=_percentage(
            values["host_swap_percent"],
            f"{label}.host_swap_percent",
        ),
        disk_free_bytes=_positive_int(values["disk_free_bytes"], f"{label}.disk_free_bytes"),
        disk_free_percent=_percentage(
            values["disk_free_percent"],
            f"{label}.disk_free_percent",
        ),
        process_rss_bytes=_positive_int(
            values["process_rss_bytes"],
            f"{label}.process_rss_bytes",
        ),
        process_rss_growth_bytes=_positive_int(
            values["process_rss_growth_bytes"],
            f"{label}.process_rss_growth_bytes",
        ),
        process_cpu_percent=_positive_float(
            values["process_cpu_percent"],
            f"{label}.process_cpu_percent",
        ),
        thread_count=_positive_int(values["thread_count"], f"{label}.thread_count"),
        open_fd_ratio=_unit_float(values["open_fd_ratio"], f"{label}.open_fd_ratio"),
    )


def _validate_runtime_resource_threshold_order(
    warning: RuntimeResourceThresholdConfig,
    critical: RuntimeResourceThresholdConfig,
) -> None:
    lower_is_worse = (
        "host_memory_available_percent",
        "disk_free_bytes",
        "disk_free_percent",
    )
    upper_is_worse = (
        "host_cpu_percent",
        "host_swap_percent",
        "process_rss_bytes",
        "process_rss_growth_bytes",
        "process_cpu_percent",
        "thread_count",
        "open_fd_ratio",
    )
    for field_name in lower_is_worse:
        if getattr(critical, field_name) >= getattr(warning, field_name):
            raise ValueError(f"critical {field_name} must be below warning")
    for field_name in upper_is_worse:
        if getattr(critical, field_name) <= getattr(warning, field_name):
            raise ValueError(f"critical {field_name} must exceed warning")


def _load_persistence(raw: Any) -> PersistenceConfig:
    values = _mapping(raw, "persistence")
    _require_keys(
        values,
        {
            "dsn_env",
            "connect_timeout_seconds",
            "queue_capacity",
            "critical_queue_reserve",
            "write_batch_size",
            "result_poll_interval_ms",
            "shutdown_timeout_seconds",
            "write_max_attempts",
            "write_retry_backoff_ms",
        },
        "persistence",
    )
    queue_capacity = _positive_int(values["queue_capacity"], "persistence.queue_capacity")
    critical_queue_reserve = _non_negative_int(
        values["critical_queue_reserve"],
        "persistence.critical_queue_reserve",
    )
    write_batch_size = _positive_int(
        values["write_batch_size"],
        "persistence.write_batch_size",
    )
    if critical_queue_reserve >= queue_capacity:
        raise ValueError("persistence.critical_queue_reserve must be smaller than queue_capacity")
    if write_batch_size > queue_capacity:
        raise ValueError("persistence.write_batch_size must not exceed queue_capacity")
    return PersistenceConfig(
        dsn_env=_non_empty_string(values["dsn_env"], "persistence.dsn_env"),
        connect_timeout_seconds=_positive_int(
            values["connect_timeout_seconds"],
            "persistence.connect_timeout_seconds",
        ),
        queue_capacity=queue_capacity,
        critical_queue_reserve=critical_queue_reserve,
        write_batch_size=write_batch_size,
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


def _load_watchlist(raw: Any) -> WatchlistConfig:
    values = _mapping(raw, "watchlist")
    keys = {"consumer_retry_interval_ms", "members"}
    if "enabled" in values:
        keys.add("enabled")
    _require_keys(values, keys, "watchlist")
    enabled = _bool(values.get("enabled", True), "watchlist.enabled")
    members_raw = values["members"]
    if not isinstance(members_raw, list) or (enabled and not members_raw):
        raise ValueError("enabled watchlist.members must be a non-empty array")
    if not enabled and members_raw:
        raise ValueError("disabled watchlist must have no members")
    members: list[WatchlistMemberConfig] = []
    seen_instruments: set[str] = set()
    for index, item in enumerate(members_raw):
        label = f"watchlist.members[{index}]"
        member = _mapping(item, label)
        _require_keys(
            member,
            {"instrument_id", "calendar_id", "owner_ids", "capabilities"},
            label,
        )
        instrument_id = _non_empty_string(
            member["instrument_id"],
            f"{label}.instrument_id",
        )
        if instrument_id in seen_instruments:
            raise ValueError(f"duplicate watchlist instrument id: {instrument_id}")
        seen_instruments.add(instrument_id)
        owner_ids = _unique_non_empty_strings(member["owner_ids"], f"{label}.owner_ids")
        capabilities = _unique_non_empty_strings(
            member["capabilities"],
            f"{label}.capabilities",
        )
        supported_capabilities = {"top_of_book", "watchlist_last"}
        unknown_capabilities = set(capabilities) - supported_capabilities
        if unknown_capabilities:
            raise ValueError(
                f"{label}.capabilities contains unsupported values: "
                f"{', '.join(sorted(unknown_capabilities))}",
            )
        members.append(
            WatchlistMemberConfig(
                instrument_id=instrument_id,
                calendar_id=_non_empty_string(member["calendar_id"], f"{label}.calendar_id"),
                owner_ids=tuple(sorted(owner_ids)),
                capabilities=tuple(sorted(capabilities)),
            ),
        )
    return WatchlistConfig(
        consumer_retry_interval_ms=_positive_int(
            values["consumer_retry_interval_ms"],
            "watchlist.consumer_retry_interval_ms",
        ),
        members=tuple(members),
        enabled=enabled,
    )


def _load_sessions(raw: Any, config_directory: Path) -> SessionsConfig:
    values = _mapping(raw, "sessions")
    _require_keys(
        values,
        {
            "evaluation_interval_ms",
            "projection_lookback_days",
            "projection_lookahead_days",
            "maximum_projection_days",
            "maximum_calendars_per_request",
            "projection_retry",
            "current_state_delivery",
            "calendar_catalog",
            "calendar_ids",
        },
        "sessions",
    )
    catalog_path = config_directory / _non_empty_string(
        values["calendar_catalog"],
        "sessions.calendar_catalog",
    )
    try:
        with catalog_path.open("rb") as file:
            catalog_raw = tomllib.load(file)
    except FileNotFoundError as exc:
        raise ValueError(f"session calendar catalog does not exist: {catalog_path}") from exc
    catalog = _mapping(catalog_raw, "calendar_catalog")
    _require_keys(
        catalog,
        {
            "schema_version",
            "catalog_id",
            "catalog_version",
            "calendar_engine_version",
            "sources",
            "corrections",
            "calendars",
        },
        "calendar_catalog",
    )
    if catalog["schema_version"] != 3:
        raise ValueError(
            f"unsupported calendar_catalog.schema_version: {catalog['schema_version']!r}",
        )
    catalog_id = _non_empty_string(catalog["catalog_id"], "calendar_catalog.catalog_id")
    catalog_version = _positive_int(
        catalog["catalog_version"],
        "calendar_catalog.catalog_version",
    )
    calendar_engine_version = _non_empty_string(
        catalog["calendar_engine_version"],
        "calendar_catalog.calendar_engine_version",
    )
    if calendar_engine_version != market_calendars.__version__:
        raise ValueError(
            "calendar catalog requires pandas-market-calendars "
            f"{calendar_engine_version}, installed {market_calendars.__version__}",
        )
    sources = _load_calendar_sources(catalog["sources"])
    sources_by_id = {source.source_id: source for source in sources}
    corrections = _load_calendar_corrections(catalog["corrections"], sources_by_id)
    corrections_by_id = {correction.correction_id: correction for correction in corrections}
    calendars_raw = catalog["calendars"]
    if not isinstance(calendars_raw, list) or not calendars_raw:
        raise ValueError("calendar_catalog.calendars must be a non-empty array")
    calendars: list[SessionCalendarConfig] = []
    seen: set[str] = set()
    for index, item in enumerate(calendars_raw):
        label = f"calendar_catalog.calendars[{index}]"
        calendar = _mapping(item, label)
        _require_keys(
            calendar,
            {
                "calendar_id",
                "calendar_engine",
                "provider_calendar",
                "schedule_columns",
                "definition_version",
                "effective_from",
                "phases",
                "correction_ids",
            },
            label,
        )
        calendar_id = _non_empty_string(calendar["calendar_id"], f"{label}.calendar_id")
        if calendar_id in seen:
            raise ValueError(f"duplicate session calendar id: {calendar_id}")
        seen.add(calendar_id)
        phases = _load_session_phases(calendar["phases"], f"{label}.phases")
        correction_ids = _unique_strings(
            calendar["correction_ids"],
            f"{label}.correction_ids",
        )
        unknown_corrections = sorted(set(correction_ids) - set(corrections_by_id))
        if unknown_corrections:
            raise ValueError(
                f"{label}.correction_ids reference unknown corrections: "
                f"{', '.join(unknown_corrections)}",
            )
        selected_corrections = tuple(corrections_by_id[item] for item in correction_ids)
        calendar_engine = _non_empty_string(
            calendar["calendar_engine"],
            f"{label}.calendar_engine",
        )
        if calendar_engine != "pandas_market_calendars":
            raise ValueError(
                f"{label}.calendar_engine must be 'pandas_market_calendars'",
            )
        provider_calendar = _non_empty_string(
            calendar["provider_calendar"],
            f"{label}.provider_calendar",
        )
        try:
            provider = market_calendars.get_calendar(provider_calendar)
        except (KeyError, RuntimeError) as exc:
            raise ValueError(
                f"{label}.provider_calendar is unavailable: {provider_calendar}",
            ) from exc
        exchange_timezone = str(provider.tz)
        schedule_columns = _unique_strings(
            calendar["schedule_columns"],
            f"{label}.schedule_columns",
        )
        if not schedule_columns:
            raise ValueError(f"{label}.schedule_columns must not be empty")
        for phase in phases:
            timezone = exchange_timezone if phase.timezone == "provider" else phase.timezone
            try:
                ZoneInfo(timezone)
            except ZoneInfoNotFoundError as exc:
                raise ValueError(
                    f"{label}.phases[{phase.name}].timezone is not an IANA timezone",
                ) from exc
            for kind, value, boundary in (
                (phase.start_kind, phase.start_value, "start"),
                (phase.end_kind, phase.end_value, "end"),
            ):
                if kind == "schedule_boundary" and value not in schedule_columns:
                    raise ValueError(
                        f"{label}.phases[{phase.name}].{boundary}_value must be admitted "
                        "in schedule_columns",
                    )
        if schedule_columns[0] != "market_open" or schedule_columns[-1] != "market_close":
            raise ValueError(
                f"{label}.schedule_columns must start with market_open and end with market_close",
            )
        available_market_times = set(provider.regular_market_times)
        unknown_schedule_columns = sorted(set(schedule_columns) - available_market_times)
        if unknown_schedule_columns:
            raise ValueError(
                f"{label}.schedule_columns are unavailable from {provider_calendar}: "
                f"{', '.join(unknown_schedule_columns)}",
            )
        if ("break_start" in schedule_columns) != ("break_end" in schedule_columns):
            raise ValueError(
                f"{label}.schedule_columns must admit break_start and break_end together",
            )
        definition_version = _positive_int(
            calendar["definition_version"],
            f"{label}.definition_version",
        )
        effective_from_ns = _utc_timestamp_ns(
            calendar["effective_from"],
            f"{label}.effective_from",
        )
        provider_calendar_class = (
            f"{provider.__class__.__module__}.{provider.__class__.__qualname__}"
        )
        normalized_definition = {
            "calendar_id": calendar_id,
            "calendar_engine": calendar_engine,
            "calendar_engine_version": calendar_engine_version,
            "provider_calendar": provider_calendar,
            "provider_calendar_class": provider_calendar_class,
            "exchange_timezone": exchange_timezone,
            "schedule_columns": schedule_columns,
            "definition_version": definition_version,
            "effective_from_ns": effective_from_ns,
            "phases": [
                {
                    "name": phase.name,
                    "timezone": phase.timezone,
                    "start_kind": phase.start_kind,
                    "start_value": phase.start_value,
                    "start_day_offset": phase.start_day_offset,
                    "end_kind": phase.end_kind,
                    "end_value": phase.end_value,
                    "end_day_offset": phase.end_day_offset,
                    "exchange_constraint": phase.exchange_constraint,
                }
                for phase in phases
            ],
            "corrections": [
                {
                    "correction_id": correction.correction_id,
                    "kind": correction.kind,
                    "source_id": correction.source_id,
                    "product_roots": correction.product_roots,
                    "effective_from_trade_date": correction.effective_from_trade_date,
                    "timezone": correction.timezone,
                    "expected_start": correction.expected_start,
                    "expected_end": correction.expected_end,
                }
                for correction in selected_corrections
            ],
            "sources": [
                {
                    "source_id": source.source_id,
                    "title": source.title,
                    "url": source.url,
                    "retrieved_at_ns": source.retrieved_at_ns,
                    "content_sha256": source.content_sha256,
                    "retrieval_status": source.retrieval_status,
                }
                for source in sources
                if source.source_id in {item.source_id for item in selected_corrections}
            ],
        }
        definition_digest = _sha256_digest(normalized_definition)
        schedule_version = (
            f"pmc-{calendar_engine_version}:{calendar_id}:"
            f"v{definition_version}:{definition_digest[:12]}"
        )
        calendars.append(
            SessionCalendarConfig(
                calendar_id=calendar_id,
                calendar_engine=calendar_engine,
                calendar_engine_version=calendar_engine_version,
                provider_calendar=provider_calendar,
                provider_calendar_class=provider_calendar_class,
                exchange_timezone=exchange_timezone,
                schedule_columns=schedule_columns,
                definition_version=definition_version,
                effective_from_ns=effective_from_ns,
                definition_digest=definition_digest,
                schedule_version=schedule_version,
                phases=phases,
                corrections=selected_corrections,
                sources=tuple(
                    source
                    for source in sources
                    if source.source_id in {item.source_id for item in selected_corrections}
                ),
            ),
        )
    selected_calendar_ids = _unique_strings(values["calendar_ids"], "sessions.calendar_ids")
    if not selected_calendar_ids:
        raise ValueError("sessions.calendar_ids must not be empty")
    calendars_by_id = {calendar.calendar_id: calendar for calendar in calendars}
    unknown_selected_calendars = sorted(set(selected_calendar_ids) - set(calendars_by_id))
    if unknown_selected_calendars:
        raise ValueError(
            "sessions.calendar_ids reference unknown catalog calendars: "
            f"{', '.join(unknown_selected_calendars)}",
        )
    selected_calendars = tuple(calendars_by_id[item] for item in selected_calendar_ids)
    catalog_digest = _sha256_digest(
        {
            "catalog_id": catalog_id,
            "catalog_version": catalog_version,
            "definitions": [calendar.definition_digest for calendar in calendars],
        },
    )
    projection_lookback_days = _positive_int(
        values["projection_lookback_days"],
        "sessions.projection_lookback_days",
    )
    projection_lookahead_days = _positive_int(
        values["projection_lookahead_days"],
        "sessions.projection_lookahead_days",
    )
    maximum_projection_days = _positive_int(
        values["maximum_projection_days"],
        "sessions.maximum_projection_days",
    )
    requested_projection_days = projection_lookback_days + projection_lookahead_days + 1
    if requested_projection_days > maximum_projection_days:
        raise ValueError(
            "sessions projection lookback and lookahead exceed maximum_projection_days",
        )
    maximum_calendars_per_request = _positive_int(
        values["maximum_calendars_per_request"],
        "sessions.maximum_calendars_per_request",
    )
    if len(selected_calendars) > maximum_calendars_per_request:
        raise ValueError(
            "sessions.calendar_ids exceed maximum_calendars_per_request",
        )
    retry_values = _mapping(values["projection_retry"], "sessions.projection_retry")
    _require_keys(
        retry_values,
        {
            "response_timeout_ms",
            "maximum_attempts",
            "retry_backoff_ms",
            "maximum_elapsed_ms",
        },
        "sessions.projection_retry",
    )
    response_timeout_ms = _positive_int(
        retry_values["response_timeout_ms"],
        "sessions.projection_retry.response_timeout_ms",
    )
    maximum_attempts = _positive_int(
        retry_values["maximum_attempts"],
        "sessions.projection_retry.maximum_attempts",
    )
    retry_backoff_ms = _positive_int(
        retry_values["retry_backoff_ms"],
        "sessions.projection_retry.retry_backoff_ms",
    )
    maximum_elapsed_ms = _positive_int(
        retry_values["maximum_elapsed_ms"],
        "sessions.projection_retry.maximum_elapsed_ms",
    )
    for value, minimum, maximum, label in (
        (response_timeout_ms, 100, 60_000, "response_timeout_ms"),
        (maximum_attempts, 1, 10, "maximum_attempts"),
        (retry_backoff_ms, 100, 60_000, "retry_backoff_ms"),
        (maximum_elapsed_ms, 1_000, 600_000, "maximum_elapsed_ms"),
    ):
        if not minimum <= value <= maximum:
            raise ValueError(
                f"sessions.projection_retry.{label} must be between {minimum} and {maximum}",
            )
    if maximum_elapsed_ms < response_timeout_ms:
        raise ValueError(
            "sessions.projection_retry.maximum_elapsed_ms must cover response_timeout_ms",
        )
    delivery_values = _mapping(
        values["current_state_delivery"],
        "sessions.current_state_delivery",
    )
    delivery_keys = {
        "policy_version",
        "response_timeout_ms",
        "maximum_attempts",
        "retry_backoff_ms",
        "maximum_elapsed_ms",
        "maximum_buffered_transitions_per_calendar",
        "maximum_total_buffered_transitions",
        "boundary_delivery_grace_ms",
    }
    _require_keys(
        delivery_values,
        delivery_keys,
        "sessions.current_state_delivery",
    )
    delivery_policy_version = _positive_int(
        delivery_values["policy_version"],
        "sessions.current_state_delivery.policy_version",
    )
    if delivery_policy_version != 1:
        raise ValueError("sessions.current_state_delivery.policy_version must be 1")
    delivery_response_timeout_ms = _positive_int(
        delivery_values["response_timeout_ms"],
        "sessions.current_state_delivery.response_timeout_ms",
    )
    delivery_maximum_attempts = _positive_int(
        delivery_values["maximum_attempts"],
        "sessions.current_state_delivery.maximum_attempts",
    )
    delivery_retry_backoff_ms = _positive_int(
        delivery_values["retry_backoff_ms"],
        "sessions.current_state_delivery.retry_backoff_ms",
    )
    delivery_maximum_elapsed_ms = _positive_int(
        delivery_values["maximum_elapsed_ms"],
        "sessions.current_state_delivery.maximum_elapsed_ms",
    )
    per_calendar_buffer = _positive_int(
        delivery_values["maximum_buffered_transitions_per_calendar"],
        "sessions.current_state_delivery.maximum_buffered_transitions_per_calendar",
    )
    total_buffer = _positive_int(
        delivery_values["maximum_total_buffered_transitions"],
        "sessions.current_state_delivery.maximum_total_buffered_transitions",
    )
    boundary_delivery_grace_ms = _positive_int(
        delivery_values["boundary_delivery_grace_ms"],
        "sessions.current_state_delivery.boundary_delivery_grace_ms",
    )
    for value, minimum, maximum, label in (
        (delivery_response_timeout_ms, 100, 60_000, "response_timeout_ms"),
        (delivery_maximum_attempts, 1, 10, "maximum_attempts"),
        (delivery_retry_backoff_ms, 100, 60_000, "retry_backoff_ms"),
        (delivery_maximum_elapsed_ms, 1_000, 600_000, "maximum_elapsed_ms"),
        (per_calendar_buffer, 1, 256, "maximum_buffered_transitions_per_calendar"),
        (total_buffer, 1, 1_024, "maximum_total_buffered_transitions"),
        (boundary_delivery_grace_ms, 1, 60_000, "boundary_delivery_grace_ms"),
    ):
        if not minimum <= value <= maximum:
            raise ValueError(
                f"sessions.current_state_delivery.{label} must be between {minimum} and {maximum}",
            )
    if delivery_maximum_elapsed_ms < delivery_response_timeout_ms:
        raise ValueError(
            "sessions.current_state_delivery.maximum_elapsed_ms must cover response_timeout_ms",
        )
    if total_buffer < per_calendar_buffer:
        raise ValueError(
            "sessions.current_state_delivery.maximum_total_buffered_transitions must not be "
            "below maximum_buffered_transitions_per_calendar",
        )
    return SessionsConfig(
        evaluation_interval_ms=_positive_int(
            values["evaluation_interval_ms"],
            "sessions.evaluation_interval_ms",
        ),
        projection_lookback_days=projection_lookback_days,
        projection_lookahead_days=projection_lookahead_days,
        maximum_projection_days=maximum_projection_days,
        maximum_calendars_per_request=maximum_calendars_per_request,
        projection_retry=ProjectionRetryConfig(
            response_timeout_ms=response_timeout_ms,
            maximum_attempts=maximum_attempts,
            retry_backoff_ms=retry_backoff_ms,
            maximum_elapsed_ms=maximum_elapsed_ms,
        ),
        current_state_delivery=CurrentStateDeliveryConfig(
            policy_version=delivery_policy_version,
            response_timeout_ms=delivery_response_timeout_ms,
            maximum_attempts=delivery_maximum_attempts,
            retry_backoff_ms=delivery_retry_backoff_ms,
            maximum_elapsed_ms=delivery_maximum_elapsed_ms,
            maximum_buffered_transitions_per_calendar=per_calendar_buffer,
            maximum_total_buffered_transitions=total_buffer,
            boundary_delivery_grace_ms=boundary_delivery_grace_ms,
        ),
        catalog_id=catalog_id,
        catalog_version=catalog_version,
        catalog_path=catalog_path.resolve(),
        catalog_digest=catalog_digest,
        available_calendars=tuple(calendars),
        calendars=selected_calendars,
    )


def _load_session_phases(raw: Any, label: str) -> tuple[SessionPhaseConfig, ...]:
    if not isinstance(raw, list):
        raise ValueError(f"{label} must be an array")
    phases: list[SessionPhaseConfig] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        item_label = f"{label}[{index}]"
        phase = _mapping(item, item_label)
        _require_keys(
            phase,
            {
                "name",
                "timezone",
                "start_kind",
                "start_value",
                "start_day_offset",
                "end_kind",
                "end_value",
                "end_day_offset",
                "exchange_constraint",
            },
            item_label,
        )
        name = _non_empty_string(phase["name"], f"{item_label}.name").upper()
        if name in {"CLOSED", "BREAK"}:
            raise ValueError(f"{item_label}.name uses a reserved market state")
        if name in seen:
            raise ValueError(f"duplicate session phase: {name}")
        seen.add(name)
        timezone = _non_empty_string(phase["timezone"], f"{item_label}.timezone")
        start_kind = _phase_boundary_kind(phase["start_kind"], f"{item_label}.start_kind")
        end_kind = _phase_boundary_kind(phase["end_kind"], f"{item_label}.end_kind")
        phases.append(
            SessionPhaseConfig(
                name=name,
                timezone=timezone,
                start_kind=start_kind,
                start_value=_phase_boundary_value(
                    phase["start_value"],
                    start_kind,
                    f"{item_label}.start_value",
                ),
                start_day_offset=_small_day_offset(
                    phase["start_day_offset"],
                    f"{item_label}.start_day_offset",
                ),
                end_kind=end_kind,
                end_value=_phase_boundary_value(
                    phase["end_value"],
                    end_kind,
                    f"{item_label}.end_value",
                ),
                end_day_offset=_small_day_offset(
                    phase["end_day_offset"],
                    f"{item_label}.end_day_offset",
                ),
                exchange_constraint=_enum_string(
                    phase["exchange_constraint"],
                    {"none", "clip", "omit_if_exchange_closes_before_start"},
                    f"{item_label}.exchange_constraint",
                ),
            ),
        )
    return tuple(phases)


def _load_calendar_sources(raw: Any) -> tuple[CalendarSourceConfig, ...]:
    if not isinstance(raw, list):
        raise ValueError("calendar_catalog.sources must be an array")
    sources: list[CalendarSourceConfig] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        label = f"calendar_catalog.sources[{index}]"
        source = _mapping(item, label)
        _require_keys(
            source,
            {
                "source_id",
                "title",
                "url",
                "retrieved_at",
                "content_sha256",
                "retrieval_status",
            },
            label,
        )
        source_id = _non_empty_string(source["source_id"], f"{label}.source_id")
        if source_id in seen:
            raise ValueError(f"duplicate calendar source: {source_id}")
        seen.add(source_id)
        digest = source["content_sha256"]
        if digest == "":
            digest = None
        if digest is not None and (
            not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            raise ValueError(f"{label}.content_sha256 must be null or lowercase SHA-256")
        retrieval_status = _non_empty_string(
            source["retrieval_status"],
            f"{label}.retrieval_status",
        ).upper()
        if retrieval_status not in {"VERIFIED", "HASH_UNAVAILABLE"}:
            raise ValueError(f"{label}.retrieval_status is unsupported")
        if retrieval_status == "VERIFIED" and digest is None:
            raise ValueError(f"{label} VERIFIED source requires content_sha256")
        sources.append(
            CalendarSourceConfig(
                source_id=source_id,
                title=_non_empty_string(source["title"], f"{label}.title"),
                url=_non_empty_string(source["url"], f"{label}.url"),
                retrieved_at_ns=_utc_timestamp_ns(
                    source["retrieved_at"],
                    f"{label}.retrieved_at",
                ),
                content_sha256=digest,
                retrieval_status=retrieval_status,
            ),
        )
    return tuple(sources)


def _load_calendar_corrections(
    raw: Any,
    sources: dict[str, CalendarSourceConfig],
) -> tuple[CalendarCorrectionConfig, ...]:
    if not isinstance(raw, list):
        raise ValueError("calendar_catalog.corrections must be an array")
    corrections: list[CalendarCorrectionConfig] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        label = f"calendar_catalog.corrections[{index}]"
        correction = _mapping(item, label)
        _require_keys(
            correction,
            {
                "correction_id",
                "kind",
                "source_id",
                "product_roots",
                "effective_from_trade_date",
                "timezone",
                "expected_start",
                "expected_end",
            },
            label,
        )
        correction_id = _non_empty_string(
            correction["correction_id"],
            f"{label}.correction_id",
        )
        if correction_id in seen:
            raise ValueError(f"duplicate calendar correction: {correction_id}")
        seen.add(correction_id)
        kind = _non_empty_string(correction["kind"], f"{label}.kind")
        if kind != "remove_regular_break":
            raise ValueError(f"{label}.kind is unsupported")
        source_id = _non_empty_string(correction["source_id"], f"{label}.source_id")
        if source_id not in sources:
            raise ValueError(f"{label}.source_id references unknown source: {source_id}")
        timezone = _non_empty_string(correction["timezone"], f"{label}.timezone")
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"{label}.timezone is not an IANA timezone") from exc
        corrections.append(
            CalendarCorrectionConfig(
                correction_id=correction_id,
                kind=kind,
                source_id=source_id,
                product_roots=_unique_non_empty_strings(
                    correction["product_roots"],
                    f"{label}.product_roots",
                ),
                effective_from_trade_date=_iso_date(
                    correction["effective_from_trade_date"],
                    f"{label}.effective_from_trade_date",
                ),
                timezone=timezone,
                expected_start=_clock_time(
                    correction["expected_start"],
                    f"{label}.expected_start",
                ),
                expected_end=_clock_time(
                    correction["expected_end"],
                    f"{label}.expected_end",
                ),
            ),
        )
    return tuple(corrections)


def _phase_boundary_kind(value: Any, label: str) -> str:
    kind = _non_empty_string(value, label)
    if kind not in {"schedule_boundary", "local_time"}:
        raise ValueError(f"{label} must be schedule_boundary or local_time")
    return kind


def _enum_string(value: Any, allowed: set[str], label: str) -> str:
    normalized = _non_empty_string(value, label)
    if normalized not in allowed:
        raise ValueError(f"{label} must be one of: {', '.join(sorted(allowed))}")
    return normalized


def _phase_boundary_value(value: Any, kind: str, label: str) -> str:
    if kind == "local_time":
        return _clock_time(value, label)
    return _non_empty_string(value, label)


def _load_evidence_health(raw: Any) -> EvidenceHealthConfig:
    values = _mapping(raw, "evidence_health")
    _require_keys(
        values,
        {
            "evaluation_interval_ms",
            "consumer_retry_interval_ms",
            "provider_id",
            "profile_checkpoint_samples",
            "policies",
        },
        "evidence_health",
    )
    policies_raw = values["policies"]
    if not isinstance(policies_raw, list) or not policies_raw:
        raise ValueError("evidence_health.policies must be a non-empty array")
    policies: list[EvidencePolicyConfig] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(policies_raw):
        label = f"evidence_health.policies[{index}]"
        policy = _mapping(item, label)
        _require_keys(
            policy,
            {
                "feed_kind",
                "selector",
                "fresh_for_ms",
                "stale_after_ms",
                "unavailable_after_ms",
                "adaptive",
                "minimum_samples",
                "decay_factor",
                "fresh_stddev_multiplier",
                "stale_stddev_multiplier",
                "unavailable_stddev_multiplier",
                "min_fresh_ms",
                "max_fresh_ms",
                "min_stale_ms",
                "max_stale_ms",
                "min_unavailable_ms",
                "max_unavailable_ms",
            },
            label,
        )
        feed_kind = _non_empty_string(policy["feed_kind"], f"{label}.feed_kind").lower()
        if feed_kind not in {"quotes", "bars"}:
            raise ValueError(f"unsupported evidence feed kind: {feed_kind}")
        selector = _non_empty_string(policy["selector"], f"{label}.selector")
        identity = (feed_kind, selector)
        if identity in seen:
            raise ValueError(f"duplicate evidence policy: {feed_kind}/{selector}")
        seen.add(identity)
        fresh = _positive_int(policy["fresh_for_ms"], f"{label}.fresh_for_ms")
        stale = _positive_int(policy["stale_after_ms"], f"{label}.stale_after_ms")
        unavailable = _positive_int(
            policy["unavailable_after_ms"],
            f"{label}.unavailable_after_ms",
        )
        if not fresh < stale < unavailable:
            raise ValueError(
                f"{label} thresholds must satisfy fresh_for_ms < stale_after_ms"
                " < unavailable_after_ms",
            )
        minimums = (
            _positive_int(policy["min_fresh_ms"], f"{label}.min_fresh_ms"),
            _positive_int(policy["min_stale_ms"], f"{label}.min_stale_ms"),
            _positive_int(policy["min_unavailable_ms"], f"{label}.min_unavailable_ms"),
        )
        maximums = (
            _positive_int(policy["max_fresh_ms"], f"{label}.max_fresh_ms"),
            _positive_int(policy["max_stale_ms"], f"{label}.max_stale_ms"),
            _positive_int(
                policy["max_unavailable_ms"],
                f"{label}.max_unavailable_ms",
            ),
        )
        if not minimums[0] < minimums[1] < minimums[2]:
            raise ValueError(f"{label} minimum adaptive thresholds must be increasing")
        if not maximums[0] < maximums[1] < maximums[2]:
            raise ValueError(f"{label} maximum adaptive thresholds must be increasing")
        if any(minimum > maximum for minimum, maximum in zip(minimums, maximums, strict=True)):
            raise ValueError(f"{label} adaptive threshold minimum exceeds maximum")
        decay_factor = _unit_float(policy["decay_factor"], f"{label}.decay_factor")
        multipliers = (
            _positive_float(
                policy["fresh_stddev_multiplier"],
                f"{label}.fresh_stddev_multiplier",
            ),
            _positive_float(
                policy["stale_stddev_multiplier"],
                f"{label}.stale_stddev_multiplier",
            ),
            _positive_float(
                policy["unavailable_stddev_multiplier"],
                f"{label}.unavailable_stddev_multiplier",
            ),
        )
        if not multipliers[0] < multipliers[1] < multipliers[2]:
            raise ValueError(f"{label} adaptive standard-deviation multipliers must increase")
        policies.append(
            EvidencePolicyConfig(
                feed_kind=feed_kind,
                selector=selector,
                fresh_for_ms=fresh,
                stale_after_ms=stale,
                unavailable_after_ms=unavailable,
                adaptive=_bool(policy["adaptive"], f"{label}.adaptive"),
                minimum_samples=_positive_int(
                    policy["minimum_samples"],
                    f"{label}.minimum_samples",
                ),
                decay_factor=decay_factor,
                fresh_stddev_multiplier=multipliers[0],
                stale_stddev_multiplier=multipliers[1],
                unavailable_stddev_multiplier=multipliers[2],
                min_fresh_ms=minimums[0],
                max_fresh_ms=maximums[0],
                min_stale_ms=minimums[1],
                max_stale_ms=maximums[1],
                min_unavailable_ms=minimums[2],
                max_unavailable_ms=maximums[2],
            ),
        )
    return EvidenceHealthConfig(
        evaluation_interval_ms=_positive_int(
            values["evaluation_interval_ms"],
            "evidence_health.evaluation_interval_ms",
        ),
        consumer_retry_interval_ms=_positive_int(
            values["consumer_retry_interval_ms"],
            "evidence_health.consumer_retry_interval_ms",
        ),
        provider_id=_non_empty_string(values["provider_id"], "evidence_health.provider_id"),
        profile_checkpoint_samples=_positive_int(
            values["profile_checkpoint_samples"],
            "evidence_health.profile_checkpoint_samples",
        ),
        policies=tuple(policies),
    )




def _load_historical(raw: Any) -> HistoricalConfig:
    values = _mapping(raw, "historical")
    _require_keys(
        values,
        {
            "maximum_plan_requests",
            "maximum_observations_per_request",
            "maximum_total_observations",
            "maximum_outstanding_requests",
            "maximum_in_flight_requests",
            "timeout_seconds",
            "maximum_attempts",
            "retry_backoff_ms",
            "poll_interval_ms",
        },
        "historical",
    )
    maximum_plan_requests = _positive_int(
        values["maximum_plan_requests"],
        "historical.maximum_plan_requests",
    )
    maximum_per_request = _positive_int(
        values["maximum_observations_per_request"],
        "historical.maximum_observations_per_request",
    )
    maximum_total = _positive_int(
        values["maximum_total_observations"],
        "historical.maximum_total_observations",
    )
    if maximum_total < maximum_per_request:
        raise ValueError(
            "historical.maximum_total_observations must not be below "
            "maximum_observations_per_request",
        )
    maximum_outstanding = _positive_int(
        values["maximum_outstanding_requests"],
        "historical.maximum_outstanding_requests",
    )
    if maximum_outstanding > maximum_plan_requests:
        raise ValueError(
            "historical.maximum_outstanding_requests must not exceed maximum_plan_requests",
        )
    maximum_in_flight = _positive_int(
        values["maximum_in_flight_requests"],
        "historical.maximum_in_flight_requests",
    )
    if maximum_in_flight != 1:
        raise ValueError(
            "historical.maximum_in_flight_requests must be 1 until the provider "
            "exposes reliable request correlation",
        )
    return HistoricalConfig(
        maximum_plan_requests=maximum_plan_requests,
        maximum_observations_per_request=maximum_per_request,
        maximum_total_observations=maximum_total,
        maximum_outstanding_requests=maximum_outstanding,
        maximum_in_flight_requests=maximum_in_flight,
        timeout_seconds=_positive_int(values["timeout_seconds"], "historical.timeout_seconds"),
        maximum_attempts=_positive_int(
            values["maximum_attempts"],
            "historical.maximum_attempts",
        ),
        retry_backoff_ms=_positive_int(
            values["retry_backoff_ms"],
            "historical.retry_backoff_ms",
        ),
        poll_interval_ms=_positive_int(
            values["poll_interval_ms"],
            "historical.poll_interval_ms",
        ),
    )


def _require_keys(values: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(values)
    missing = expected - actual
    unknown = actual - expected
    if missing:
        raise ValueError(f"{label} missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"{label} has unknown keys: {', '.join(sorted(unknown))}")


def _require_keys_allowing(
    values: dict[str, Any],
    required: set[str],
    optional: set[str],
    label: str,
) -> None:
    actual = set(values)
    missing = required - actual
    unknown = actual - required - optional
    if missing:
        raise ValueError(f"{label} missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"{label} has unknown keys: {', '.join(sorted(unknown))}")


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a table")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


def _table_array(value: Any, label: str) -> list[dict[str, Any]]:
    items = _array(value, label)
    if any(not isinstance(item, dict) for item in items):
        raise ValueError(f"{label} must contain tables")
    return items


def _non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _positive_float(value: Any, label: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive number")
    return float(value)


def _percentage(value: Any, label: str) -> float:
    result = _positive_float(value, label)
    if result > 100:
        raise ValueError(f"{label} must not exceed 100")
    return result


def _unit_float(value: Any, label: str) -> float:
    result = _positive_float(value, label)
    if result >= 1:
        raise ValueError(f"{label} must be less than 1")
    return result


def _unique_non_empty_strings(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty array")
    items = tuple(_non_empty_string(item, f"{label}[]") for item in value)
    if len(set(items)) != len(items):
        raise ValueError(f"{label} must contain unique values")
    return items


def _unique_strings(value: Any, label: str) -> tuple[str, ...]:
    items = tuple(_non_empty_string(item, f"{label}[]") for item in _array(value, label))
    if len(set(items)) != len(items):
        raise ValueError(f"{label} must contain unique values")
    return items


def _positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _non_negative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _clock_time(value: Any, label: str) -> str:
    text = _non_empty_string(value, label)
    try:
        parsed = time.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO local time") from exc
    if parsed.second or parsed.microsecond or parsed.tzinfo is not None:
        raise ValueError(f"{label} must use HH:MM precision without a timezone")
    return parsed.strftime("%H:%M")


def _iso_date(value: Any, label: str) -> str:
    text = _non_empty_string(value, label)
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO date") from exc


def _utc_timestamp_ns(value: Any, label: str) -> int:
    text = _non_empty_string(value, label)
    if not text.endswith("Z"):
        raise ValueError(f"{label} must be an ISO timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO UTC timestamp") from exc
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError(f"{label} must use UTC")
    delta = parsed - datetime(1970, 1, 1, tzinfo=UTC)
    return (delta.days * 86_400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1_000


def _small_day_offset(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not -7 <= value <= 7:
        raise ValueError(f"{label} must be an integer from -7 through 7")
    return value


def _sha256_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value
