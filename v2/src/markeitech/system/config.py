from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date, time
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
class WatchlistMemberConfig:
    instrument_id: str
    calendar_id: str
    owner_ids: tuple[str, ...]
    capabilities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WatchlistConfig:
    consumer_retry_interval_ms: int
    members: tuple[WatchlistMemberConfig, ...]


@dataclass(frozen=True, slots=True)
class AcquisitionConfig:
    native_consumer_probe_enabled: bool
    native_consumer_probe_unsubscribe_after_seconds: int


@dataclass(frozen=True, slots=True)
class SessionPhaseConfig:
    name: str
    start: str
    end: str
    start_day_offset: int


@dataclass(frozen=True, slots=True)
class SessionOverrideConfig:
    trade_date: str
    phase: str
    start: str
    end: str
    start_day_offset: int


@dataclass(frozen=True, slots=True)
class SessionCalendarConfig:
    calendar_id: str
    provider_calendar: str
    timezone: str
    schedule_version: str
    phases: tuple[SessionPhaseConfig, ...]
    overrides: tuple[SessionOverrideConfig, ...]


@dataclass(frozen=True, slots=True)
class SessionsConfig:
    evaluation_interval_ms: int
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
    schema_version: int
    runtime: RuntimeConfig
    ib: InteractiveBrokersConfig
    logging: LoggingConfig
    discord: DiscordConfig
    persistence: PersistenceConfig
    acquisition: AcquisitionConfig
    watchlist: WatchlistConfig
    sessions: SessionsConfig
    evidence_health: EvidenceHealthConfig

    @property
    def instrument_ids(self) -> tuple[str, ...]:
        return tuple(member.instrument_id for member in self.watchlist.members)


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
            "acquisition",
            "watchlist",
            "sessions",
            "evidence_health",
        },
        "root",
    )
    if raw["schema_version"] != 7:
        raise ValueError(f"unsupported schema_version: {raw['schema_version']!r}")

    runtime = _load_runtime(raw["runtime"])
    ib = _load_ib(raw["ib"])
    logging = _load_logging(raw["logging"], config_path.parent)
    discord = _load_discord(raw["discord"])
    persistence = _load_persistence(raw["persistence"])
    watchlist = _load_watchlist(raw["watchlist"])
    acquisition = _load_acquisition(raw["acquisition"], watchlist)
    sessions = _load_sessions(raw["sessions"])
    evidence_health = _load_evidence_health(raw["evidence_health"])
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
        logging=logging,
        discord=discord,
        persistence=persistence,
        acquisition=acquisition,
        watchlist=watchlist,
        sessions=sessions,
        evidence_health=evidence_health,
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
    _require_keys(values, {"consumer_retry_interval_ms", "members"}, "watchlist")
    members_raw = values["members"]
    if not isinstance(members_raw, list) or not members_raw:
        raise ValueError("watchlist.members must be a non-empty array")
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
    )


def _load_sessions(raw: Any) -> SessionsConfig:
    values = _mapping(raw, "sessions")
    _require_keys(values, {"evaluation_interval_ms", "calendars"}, "sessions")
    calendars_raw = values["calendars"]
    if not isinstance(calendars_raw, list) or not calendars_raw:
        raise ValueError("sessions.calendars must be a non-empty array")
    calendars: list[SessionCalendarConfig] = []
    seen: set[str] = set()
    for index, item in enumerate(calendars_raw):
        label = f"sessions.calendars[{index}]"
        calendar = _mapping(item, label)
        _require_keys(
            calendar,
            {
                "calendar_id",
                "provider_calendar",
                "timezone",
                "schedule_version",
                "phases",
                "overrides",
            },
            label,
        )
        calendar_id = _non_empty_string(calendar["calendar_id"], f"{label}.calendar_id")
        if calendar_id in seen:
            raise ValueError(f"duplicate session calendar id: {calendar_id}")
        seen.add(calendar_id)
        phases = _load_session_phases(calendar["phases"], f"{label}.phases")
        overrides = _load_session_overrides(calendar["overrides"], f"{label}.overrides")
        phase_names = {phase.name for phase in phases}
        unknown_override_phases = sorted(
            {override.phase for override in overrides} - phase_names,
        )
        if unknown_override_phases:
            raise ValueError(
                f"{label}.overrides reference undefined phases: "
                f"{', '.join(unknown_override_phases)}",
            )
        calendars.append(
            SessionCalendarConfig(
                calendar_id=calendar_id,
                provider_calendar=_non_empty_string(
                    calendar["provider_calendar"],
                    f"{label}.provider_calendar",
                ),
                timezone=_non_empty_string(calendar["timezone"], f"{label}.timezone"),
                schedule_version=_non_empty_string(
                    calendar["schedule_version"],
                    f"{label}.schedule_version",
                ),
                phases=phases,
                overrides=overrides,
            ),
        )
    return SessionsConfig(
        evaluation_interval_ms=_positive_int(
            values["evaluation_interval_ms"],
            "sessions.evaluation_interval_ms",
        ),
        calendars=tuple(calendars),
    )


def _load_session_phases(raw: Any, label: str) -> tuple[SessionPhaseConfig, ...]:
    if not isinstance(raw, list):
        raise ValueError(f"{label} must be an array")
    phases: list[SessionPhaseConfig] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        item_label = f"{label}[{index}]"
        phase = _mapping(item, item_label)
        _require_keys(phase, {"name", "start", "end", "start_day_offset"}, item_label)
        name = _non_empty_string(phase["name"], f"{item_label}.name").upper()
        if name == "CLOSED":
            raise ValueError(f"{item_label}.name cannot use reserved phase CLOSED")
        if name in seen:
            raise ValueError(f"duplicate session phase: {name}")
        seen.add(name)
        phases.append(
            SessionPhaseConfig(
                name=name,
                start=_clock_time(phase["start"], f"{item_label}.start"),
                end=_clock_time(phase["end"], f"{item_label}.end"),
                start_day_offset=_small_day_offset(
                    phase["start_day_offset"],
                    f"{item_label}.start_day_offset",
                ),
            ),
        )
    return tuple(phases)


def _load_session_overrides(raw: Any, label: str) -> tuple[SessionOverrideConfig, ...]:
    if not isinstance(raw, list):
        raise ValueError(f"{label} must be an array")
    overrides: list[SessionOverrideConfig] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(raw):
        item_label = f"{label}[{index}]"
        override = _mapping(item, item_label)
        _require_keys(
            override,
            {"trade_date", "phase", "start", "end", "start_day_offset"},
            item_label,
        )
        trade_date = _iso_date(override["trade_date"], f"{item_label}.trade_date")
        phase = _non_empty_string(override["phase"], f"{item_label}.phase").upper()
        identity = (trade_date, phase)
        if identity in seen:
            raise ValueError(f"duplicate session override: {trade_date}/{phase}")
        seen.add(identity)
        overrides.append(
            SessionOverrideConfig(
                trade_date=trade_date,
                phase=phase,
                start=_clock_time(override["start"], f"{item_label}.start"),
                end=_clock_time(override["end"], f"{item_label}.end"),
                start_day_offset=_small_day_offset(
                    override["start_day_offset"],
                    f"{item_label}.start_day_offset",
                ),
            ),
        )
    return tuple(overrides)


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


def _load_acquisition(
    raw: Any,
    _watchlist: WatchlistConfig,
) -> AcquisitionConfig:
    values = _mapping(raw, "acquisition")
    _require_keys(
        values,
        {
            "native_consumer_probe_enabled",
            "native_consumer_probe_unsubscribe_after_seconds",
        },
        "acquisition",
    )
    return AcquisitionConfig(
        native_consumer_probe_enabled=_bool(
            values["native_consumer_probe_enabled"],
            "acquisition.native_consumer_probe_enabled",
        ),
        native_consumer_probe_unsubscribe_after_seconds=_positive_int(
            values["native_consumer_probe_unsubscribe_after_seconds"],
            "acquisition.native_consumer_probe_unsubscribe_after_seconds",
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


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a table")
    return value


def _non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _positive_float(value: Any, label: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive number")
    return float(value)


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


def _small_day_offset(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not -7 <= value <= 7:
        raise ValueError(f"{label} must be an integer from -7 through 7")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value
