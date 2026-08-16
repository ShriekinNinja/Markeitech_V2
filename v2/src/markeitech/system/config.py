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


@dataclass(frozen=True, slots=True)
class EvidenceHealthConfig:
    evaluation_interval_ms: int
    consumer_retry_interval_ms: int
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
    if raw["schema_version"] != 6:
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
        required_capabilities = {"top_of_book", "watchlist_last"}
        if set(capabilities) != required_capabilities:
            raise ValueError(
                f"{label}.capabilities must contain exactly: "
                f"{', '.join(sorted(required_capabilities))}",
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
        {"evaluation_interval_ms", "consumer_retry_interval_ms", "policies"},
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
        policies.append(
            EvidencePolicyConfig(
                feed_kind=feed_kind,
                selector=selector,
                fresh_for_ms=fresh,
                stale_after_ms=stale,
                unavailable_after_ms=unavailable,
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
