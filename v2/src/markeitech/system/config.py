from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any

from nautilus_trader.model import BarSpecification

type EntityConfigScalar = str | int | float | bool

_ENTITY_GROUPS = {
    "objective_session_reference_level",
    "volatility_compression_expansion",
    "direction_trend_rotation_reference",
    "swing_fvg_zone",
    "inferred_bar_volume_distribution",
}
_ENTITY_HEALTH_VALUES = {
    "READY",
    "WARMING",
    "DEGRADED",
    "STALE",
    "UNAVAILABLE",
    "UNSUPPORTED",
    "FAILED",
}
_ENTITY_FIDELITY_VALUES = {
    "REPORTED",
    "DERIVED",
    "INFERRED",
    "PARTIAL",
    "UNAVAILABLE",
}
_ENTITY_DURABILITY_VALUES = {
    "TRANSIENT",
    "FINALIZED_SESSION",
    "CROSS_SESSION_CHECKPOINT",
}
_PARAMETER_VALUE_KINDS = {"number", "integer", "boolean", "text"}
_PARAMETER_MUTABILITY_VALUES = {"startup_only", "policy_controlled_runtime"}


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
class HistoricalProbeConfig:
    enabled: bool
    actor_ids: tuple[str, ...]
    instrument_id: str
    selector: str
    window: str
    minimum_observations: int
    maximum_observations: int
    priority: int


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
    probe: HistoricalProbeConfig


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
class QuoteQualityMetricsConfig:
    enabled: bool
    required_watchlist_capability: str
    parameter_version: int
    minimum_update_interval_ms: int
    maximum_output_age_ms: int
    demand_retry_interval_ms: int
    evidence_snapshot_retry_interval_ms: int
    priority: int


@dataclass(frozen=True, slots=True)
class AnalyticalWindowConfig:
    window_id: str
    purpose: str
    anchor_phase: str
    anchor_boundary: str
    offset_seconds: int
    duration_seconds: int
    minimum_duration_seconds: int
    maximum_duration_seconds: int
    duration_step_seconds: int
    dynamic: bool
    historical_selector: str
    minimum_historical_observations: int
    maximum_historical_observations: int


@dataclass(frozen=True, slots=True)
class AnalyticalSessionProfileConfig:
    profile_id: str
    version: int
    calendar_id: str
    primary_phase: str
    overnight_enabled: bool
    overnight_phase: str
    volume_supported: bool
    windows: tuple[AnalyticalWindowConfig, ...]


@dataclass(frozen=True, slots=True)
class AnalyticalProfileBindingConfig:
    profile_id: str
    instrument_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompletedBarMetricsConfig:
    live_selector: str
    historical_selector: str
    historical_window: str
    minimum_historical_observations: int
    maximum_historical_observations: int
    calculation_interval_seconds: int
    minimum_interval_seconds: int
    maximum_interval_seconds: int
    interval_step_seconds: int
    interval_dynamic: bool
    aggregation_boundary_policy: str
    timestamp_policy: str
    revision_policy: str
    maximum_retained_observations: int
    maximum_output_age_ms: int


@dataclass(frozen=True, slots=True)
class SessionReferenceMetricsConfig:
    enabled: bool
    historical_selector: str
    active_window: str
    previous_window: str
    overnight_window: str
    minimum_historical_observations: int
    maximum_historical_observations: int
    vwap_price_basis: str
    vwap_price_basis_dynamic: bool
    minimum_coverage_ratio: float
    minimum_coverage_ratio_floor: float
    minimum_coverage_ratio_ceiling: float
    minimum_coverage_ratio_step: float
    minimum_coverage_ratio_dynamic: bool
    maximum_retained_sessions: int
    maximum_output_age_ms: int


@dataclass(frozen=True, slots=True)
class SessionWindowMetricsConfig:
    enabled: bool
    price_basis: str
    price_basis_dynamic: bool
    minimum_coverage_ratio: float
    minimum_coverage_ratio_floor: float
    minimum_coverage_ratio_ceiling: float
    minimum_coverage_ratio_step: float
    minimum_coverage_ratio_dynamic: bool
    maximum_retained_sessions: int
    maximum_output_age_ms: int


@dataclass(frozen=True, slots=True)
class RollingCandidateConfig:
    candidate_id: str
    purpose: str
    duration_seconds: int
    minimum_duration_seconds: int
    maximum_duration_seconds: int
    duration_step_seconds: int
    dynamic: bool
    active: bool


@dataclass(frozen=True, slots=True)
class RollingFamilyConfig:
    family_id: str
    source_selector: str
    input_selector: str
    input_interval_seconds: int
    aggregation_policy: str
    selected_context_candidate_id: str
    candidates: tuple[RollingCandidateConfig, ...]


@dataclass(frozen=True, slots=True)
class RollingBaselineConfig:
    eligible_reference_health: tuple[str, ...]
    eligible_reference_fidelities: tuple[str, ...]
    recent_reference_count: int
    recent_reference_count_minimum: int
    recent_reference_count_maximum: int
    recent_reference_count_step: int
    recent_reference_count_dynamic: bool
    minimum_recent_references: int
    phase_reference_count: int
    phase_reference_count_minimum: int
    phase_reference_count_maximum: int
    phase_reference_count_step: int
    phase_reference_count_dynamic: bool
    minimum_phase_references: int


@dataclass(frozen=True, slots=True)
class RollingMeasurementsConfig:
    enabled: bool
    minimum_coverage_ratio: float
    minimum_coverage_ratio_floor: float
    minimum_coverage_ratio_ceiling: float
    minimum_coverage_ratio_step: float
    minimum_coverage_ratio_dynamic: bool
    maximum_retained_observations: int
    maximum_output_age_ms: int
    baseline: RollingBaselineConfig
    families: tuple[RollingFamilyConfig, ...]


@dataclass(frozen=True, slots=True)
class SessionMeasurementsConfig:
    enabled: bool
    required_watchlist_capability: str
    parameter_version: int
    parameter_source: str
    parameter_effective_from_ns: int
    conflict_policy: str
    maximum_active_sessions: int
    demand_retry_interval_ms: int
    evidence_snapshot_retry_interval_ms: int
    priority: int
    completed_bars: CompletedBarMetricsConfig
    session_references: SessionReferenceMetricsConfig
    session_windows: SessionWindowMetricsConfig
    rolling_measurements: RollingMeasurementsConfig
    profiles: tuple[AnalyticalSessionProfileConfig, ...]
    profile_bindings: tuple[AnalyticalProfileBindingConfig, ...]


@dataclass(frozen=True, slots=True)
class EntityApplicationConfig:
    application_id: str
    parameter_set_id: str
    analytical_profile_ids: tuple[str, ...]
    instrument_ids: tuple[str, ...]
    instrument_classes: tuple[str, ...]
    session_phases: tuple[str, ...]
    horizon: str
    source_selector: str
    requires_volume: bool


@dataclass(frozen=True, slots=True)
class EntityMetricInputConfig:
    role: str
    metric_id: str
    metric_version: int
    parameter_version: int
    required: bool
    permitted_health: tuple[str, ...]
    permitted_fidelities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EntityInputConfig:
    role: str
    entity_type: str
    entity_version: int
    required: bool
    permitted_health: tuple[str, ...]
    permitted_fidelities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EntityParameterConfig:
    parameter_id: str
    meaning: str
    value_kind: str
    unit: str
    default: EntityConfigScalar
    dynamic: bool
    mutability: str
    source: str
    minimum: int | float | None
    maximum: int | float | None
    step: int | float | None
    allowed_values: tuple[EntityConfigScalar, ...]


@dataclass(frozen=True, slots=True)
class EntityParameterSetConfig:
    parameter_set_id: str
    parameter_version: int
    effective_from_ns: int
    source: str
    values: tuple[tuple[str, EntityConfigScalar], ...]


@dataclass(frozen=True, slots=True)
class EntityStateBandConfig:
    category: str
    lower_bound_parameter_id: str | None
    upper_bound_parameter_id: str | None


@dataclass(frozen=True, slots=True)
class EntityStatePolicyConfig:
    axis: str
    policy_id: str
    policy_version: int
    measure_role: str
    coverage_role: str
    unavailable_category: str
    bands: tuple[EntityStateBandConfig, ...]
    hysteresis_parameter_id: str
    confirmation_observations_parameter_id: str
    minimum_coverage_ratio_parameter_id: str
    maximum_evidence_age_ms_parameter_id: str
    permitted_health: tuple[str, ...]
    permitted_fidelities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EntityMarketStateConfig:
    parameter_set_id: str
    normalization: str | None
    reference_id: str | None
    reference_kind: str | None
    policies: tuple[EntityStatePolicyConfig, ...]


@dataclass(frozen=True, slots=True)
class EntityDefinitionConfig:
    definition_id: str
    group: str
    entity_type: str
    entity_version: int
    enabled: bool
    decision_question: str
    implementation_id: str
    formula_version: int
    identity_dimensions: tuple[str, ...]
    durability: str
    completion_rule: str
    invalidation_rule: str
    expiry_rule: str
    permitted_health: tuple[str, ...]
    permitted_fidelities: tuple[str, ...]
    applications: tuple[EntityApplicationConfig, ...]
    metric_inputs: tuple[EntityMetricInputConfig, ...]
    entity_inputs: tuple[EntityInputConfig, ...]
    parameters: tuple[EntityParameterConfig, ...]
    parameter_sets: tuple[EntityParameterSetConfig, ...]
    market_state: EntityMarketStateConfig | None


@dataclass(frozen=True, slots=True)
class EntityAnalysisConfig:
    enabled: bool
    required_watchlist_capability: str
    catalog_version: int
    parameter_source: str
    parameter_effective_from_ns: int
    maximum_entities_global: int
    maximum_entities_per_instrument: int
    maximum_entities_per_instrument_type: int
    completed_session_retention: int
    completed_session_maximum_age_days: int
    maximum_input_age_ms: int
    maximum_metric_values: int | None
    market_state_reconciliation_interval_ms: int | None
    minimum_snapshot_interval_ms: int
    maximum_publications_per_cycle: int
    definitions: tuple[EntityDefinitionConfig, ...]


@dataclass(frozen=True, slots=True)
class MetricsConfig:
    quote_quality: QuoteQualityMetricsConfig
    session_measurements: SessionMeasurementsConfig
    entity_analysis: EntityAnalysisConfig


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
class VisualDebugCaptureConfig:
    enabled: bool
    configuration_identity: str
    instrument_id: str
    analytical_profile_id: str
    analytical_profile_version: int
    bar_specification: str
    parameter_version: int
    output_directory: Path
    capture_policy_version: int
    target_historical_bars: int
    target_live_bars: int
    quiet_period_ms: int
    completion_deadline_ms: int
    output_drain_timeout_ms: int
    candle_pane_height_px: int
    volume_pane_height_px: int
    metric_pane_height_px: int
    pane_gap_px: int


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
    schema_version: int
    runtime: RuntimeConfig
    ib: InteractiveBrokersConfig
    logging: LoggingConfig
    discord: DiscordConfig
    visual_debug_capture: VisualDebugCaptureConfig
    runtime_resources: RuntimeResourcesConfig
    persistence: PersistenceConfig
    acquisition: AcquisitionConfig
    historical: HistoricalConfig
    watchlist: WatchlistConfig
    sessions: SessionsConfig
    evidence_health: EvidenceHealthConfig
    metrics: MetricsConfig

    @property
    def instrument_ids(self) -> tuple[str, ...]:
        return tuple(member.instrument_id for member in self.watchlist.members)


def load_system_config(path: str | Path) -> SystemConfig:
    config_path = Path(path)
    with config_path.open("rb") as file:
        raw = tomllib.load(file)

    root_keys = {
            "schema_version",
            "runtime",
            "ib",
            "logging",
            "discord",
            "runtime_resources",
            "persistence",
            "acquisition",
            "historical",
            "watchlist",
            "sessions",
            "evidence_health",
            "metrics",
        }
    if "visual_debug_capture" in raw:
        root_keys.add("visual_debug_capture")
    _require_keys(
        raw,
        root_keys,
        "root",
    )
    if raw["schema_version"] != 18:
        raise ValueError(f"unsupported schema_version: {raw['schema_version']!r}")

    runtime = _load_runtime(raw["runtime"])
    ib = _load_ib(raw["ib"])
    logging = _load_logging(raw["logging"], config_path.parent)
    discord = _load_discord(raw["discord"])
    visual_debug_capture = _load_visual_debug_capture(
        raw.get(
            "visual_debug_capture",
            {
                "enabled": False,
                "configuration_identity": "not-configured",
                "instrument_id": "ESU6.CME",
                "analytical_profile_id": "cme_equity_primary",
                "analytical_profile_version": 1,
                "bar_specification": "1-MINUTE-LAST-EXTERNAL",
                "parameter_version": 1,
                "output_directory": "../data/visual-debug-captures",
                "capture_policy_version": 1,
                "target_historical_bars": 5,
                "target_live_bars": 5,
                "quiet_period_ms": 2000,
                "completion_deadline_ms": 900000,
                "output_drain_timeout_ms": 30000,
                "candle_pane_height_px": 720,
                "volume_pane_height_px": 130,
                "metric_pane_height_px": 110,
                "pane_gap_px": 18,
            },
        ),
        config_path.parent,
    )
    runtime_resources = _load_runtime_resources(raw["runtime_resources"])
    persistence = _load_persistence(raw["persistence"])
    watchlist = _load_watchlist(raw["watchlist"])
    acquisition = _load_acquisition(raw["acquisition"], watchlist)
    historical = _load_historical(raw["historical"], watchlist)
    sessions = _load_sessions(raw["sessions"])
    evidence_health = _load_evidence_health(raw["evidence_health"])
    metrics = _load_metrics(raw["metrics"])
    if visual_debug_capture.enabled:
        if not metrics.session_measurements.enabled:
            raise ValueError("visual debug capture requires session measurements enabled")
        if tuple(member.instrument_id for member in watchlist.members) != (
            visual_debug_capture.instrument_id,
        ):
            raise ValueError("visual debug capture requires an exact matching one-member watchlist")
        completed = metrics.session_measurements.completed_bars
        if (
            visual_debug_capture.bar_specification != completed.historical_selector
            or visual_debug_capture.parameter_version
            != metrics.session_measurements.parameter_version
        ):
            raise ValueError("visual debug capture must match the completed-bar producer identity")
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
    if metrics.quote_quality.enabled and not any(
        metrics.quote_quality.required_watchlist_capability in member.capabilities
        for member in watchlist.members
    ):
        raise ValueError("enabled quote-quality metrics scope selects no watchlist instruments")
    if metrics.session_measurements.enabled and not any(
        metrics.session_measurements.required_watchlist_capability in member.capabilities
        for member in watchlist.members
    ):
        raise ValueError("enabled session measurements scope selects no watchlist instruments")
    if metrics.entity_analysis.enabled and not any(
        metrics.entity_analysis.required_watchlist_capability in member.capabilities
        for member in watchlist.members
    ):
        raise ValueError("enabled entity analysis scope selects no watchlist instruments")
    if metrics.entity_analysis.enabled and not metrics.session_measurements.enabled:
        raise ValueError("enabled entity analysis requires enabled session measurements")
    profile_calendars = {profile.calendar_id for profile in metrics.session_measurements.profiles}
    unknown_profile_calendars = sorted(profile_calendars - known_calendars)
    if unknown_profile_calendars:
        raise ValueError(
            "session measurement profiles reference unknown calendars: "
            f"{', '.join(unknown_profile_calendars)}",
        )
    calendars_by_id = {calendar.calendar_id: calendar for calendar in sessions.calendars}
    for profile in metrics.session_measurements.profiles:
        calendar = calendars_by_id[profile.calendar_id]
        available_phases = {phase.name for phase in calendar.phases} or {"OPEN"}
        if profile.primary_phase not in available_phases:
            raise ValueError(
                "session measurement profile primary phase is not defined by its calendar: "
                f"profile={profile.profile_id}, phase={profile.primary_phase}",
            )
        if profile.overnight_enabled and profile.overnight_phase not in available_phases:
            raise ValueError(
                "session measurement profile overnight phase is not defined by its calendar: "
                f"profile={profile.profile_id}, phase={profile.overnight_phase}",
            )
        for window in profile.windows:
            if window.anchor_phase not in available_phases:
                raise ValueError(
                    "session measurement window phase is not defined by its calendar: "
                    f"profile={profile.profile_id}, window={window.window_id}, "
                    f"phase={window.anchor_phase}",
                )
    profile_by_id = {
        profile.profile_id: profile for profile in metrics.session_measurements.profiles
    }
    watchlist_by_id = {member.instrument_id: member for member in watchlist.members}
    configured_binding_ids = {
        instrument_id
        for binding in metrics.session_measurements.profile_bindings
        for instrument_id in binding.instrument_ids
    }
    unknown_binding_ids = sorted(configured_binding_ids - set(watchlist_by_id))
    if unknown_binding_ids:
        raise ValueError(
            "session measurement bindings reference unknown watchlist instruments: "
            f"{', '.join(unknown_binding_ids)}",
        )
    bound_instruments: dict[str, str] = {}
    for binding in metrics.session_measurements.profile_bindings:
        profile = profile_by_id[binding.profile_id]
        for instrument_id in binding.instrument_ids:
            member = watchlist_by_id[instrument_id]
            if member.calendar_id != profile.calendar_id:
                raise ValueError(
                    "session measurement profile binding calendar mismatch: "
                    f"{instrument_id} uses {member.calendar_id}, profile {profile.profile_id} "
                    f"uses {profile.calendar_id}",
                )
            bound_instruments[instrument_id] = profile.profile_id
    _validate_entity_analysis_scope(
        metrics.entity_analysis,
        profiles=profile_by_id,
        bound_instruments=bound_instruments,
        watchlist=watchlist_by_id,
        rolling_families=metrics.session_measurements.rolling_measurements.families,
        completed_bars=metrics.session_measurements.completed_bars,
    )
    if metrics.session_measurements.enabled:
        selected_instruments = {
            member.instrument_id
            for member in watchlist.members
            if metrics.session_measurements.required_watchlist_capability in member.capabilities
        }
        missing_bindings = sorted(selected_instruments - set(bound_instruments))
        if missing_bindings:
            raise ValueError(
                "enabled session measurements lack analytical profile bindings: "
                f"{', '.join(missing_bindings)}",
            )
        selected_calendars = {
            watchlist_by_id[instrument_id].calendar_id for instrument_id in selected_instruments
        }
        if len(selected_calendars) > metrics.session_measurements.maximum_active_sessions:
            raise ValueError(
                "enabled session measurements exceed maximum_active_sessions: "
                f"selected={len(selected_calendars)}, "
                f"maximum={metrics.session_measurements.maximum_active_sessions}",
            )
        if ib.handle_revised_bars:
            raise ValueError(
                "enabled session measurements with reject_revision require "
                "ib.handle_revised_bars = false",
            )
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
        visual_debug_capture=visual_debug_capture,
        runtime_resources=runtime_resources,
        persistence=persistence,
        acquisition=acquisition,
        historical=historical,
        watchlist=watchlist,
        sessions=sessions,
        evidence_health=evidence_health,
        metrics=metrics,
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


def _load_visual_debug_capture(
    raw: Any,
    config_directory: Path,
) -> VisualDebugCaptureConfig:
    values = _mapping(raw, "visual_debug_capture")
    keys = {
        "enabled",
        "configuration_identity",
        "instrument_id",
        "analytical_profile_id",
        "analytical_profile_version",
        "bar_specification",
        "parameter_version",
        "output_directory",
        "capture_policy_version",
        "target_historical_bars",
        "target_live_bars",
        "quiet_period_ms",
        "completion_deadline_ms",
        "output_drain_timeout_ms",
        "candle_pane_height_px",
        "volume_pane_height_px",
        "metric_pane_height_px",
        "pane_gap_px",
    }
    _require_keys(values, keys, "visual_debug_capture")
    output_directory = Path(
        _non_empty_string(values["output_directory"], "visual_debug_capture.output_directory"),
    )
    if not output_directory.is_absolute():
        output_directory = (config_directory / output_directory).resolve()
    target_historical_bars = _non_negative_int(
        values["target_historical_bars"],
        "visual_debug_capture.target_historical_bars",
    )
    target_live_bars = _non_negative_int(
        values["target_live_bars"],
        "visual_debug_capture.target_live_bars",
    )
    if target_historical_bars + target_live_bars == 0:
        raise ValueError("visual debug capture requires at least one positive population target")
    return VisualDebugCaptureConfig(
        enabled=_bool(values["enabled"], "visual_debug_capture.enabled"),
        configuration_identity=_non_empty_string(
            values["configuration_identity"],
            "visual_debug_capture.configuration_identity",
        ),
        instrument_id=_non_empty_string(
            values["instrument_id"], "visual_debug_capture.instrument_id"
        ),
        analytical_profile_id=_non_empty_string(
            values["analytical_profile_id"],
            "visual_debug_capture.analytical_profile_id",
        ),
        analytical_profile_version=_positive_int(
            values["analytical_profile_version"],
            "visual_debug_capture.analytical_profile_version",
        ),
        bar_specification=_non_empty_string(
            values["bar_specification"],
            "visual_debug_capture.bar_specification",
        ),
        parameter_version=_positive_int(
            values["parameter_version"], "visual_debug_capture.parameter_version"
        ),
        output_directory=output_directory,
        capture_policy_version=_positive_int(
            values["capture_policy_version"],
            "visual_debug_capture.capture_policy_version",
        ),
        target_historical_bars=target_historical_bars,
        target_live_bars=target_live_bars,
        quiet_period_ms=_positive_int(
            values["quiet_period_ms"], "visual_debug_capture.quiet_period_ms"
        ),
        completion_deadline_ms=_positive_int(
            values["completion_deadline_ms"],
            "visual_debug_capture.completion_deadline_ms",
        ),
        output_drain_timeout_ms=_positive_int(
            values["output_drain_timeout_ms"],
            "visual_debug_capture.output_drain_timeout_ms",
        ),
        candle_pane_height_px=_positive_int(
            values["candle_pane_height_px"],
            "visual_debug_capture.candle_pane_height_px",
        ),
        volume_pane_height_px=_positive_int(
            values["volume_pane_height_px"],
            "visual_debug_capture.volume_pane_height_px",
        ),
        metric_pane_height_px=_positive_int(
            values["metric_pane_height_px"],
            "visual_debug_capture.metric_pane_height_px",
        ),
        pane_gap_px=_positive_int(
            values["pane_gap_px"],
            "visual_debug_capture.pane_gap_px",
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


def _load_metrics(raw: Any) -> MetricsConfig:
    values = _mapping(raw, "metrics")
    _require_keys(
        values,
        {"quote_quality", "session_measurements", "entity_analysis"},
        "metrics",
    )
    quote = _mapping(values["quote_quality"], "metrics.quote_quality")
    _require_keys(
        quote,
        {
            "enabled",
            "required_watchlist_capability",
            "parameter_version",
            "minimum_update_interval_ms",
            "maximum_output_age_ms",
            "demand_retry_interval_ms",
            "evidence_snapshot_retry_interval_ms",
            "priority",
        },
        "metrics.quote_quality",
    )
    priority = _non_negative_int(quote["priority"], "metrics.quote_quality.priority")
    if priority > 100:
        raise ValueError("metrics.quote_quality.priority must not exceed 100")
    quote_config = QuoteQualityMetricsConfig(
        enabled=_bool(quote["enabled"], "metrics.quote_quality.enabled"),
        required_watchlist_capability=_non_empty_string(
            quote["required_watchlist_capability"],
            "metrics.quote_quality.required_watchlist_capability",
        ),
        parameter_version=_positive_int(
            quote["parameter_version"],
            "metrics.quote_quality.parameter_version",
        ),
        minimum_update_interval_ms=_non_negative_int(
            quote["minimum_update_interval_ms"],
            "metrics.quote_quality.minimum_update_interval_ms",
        ),
        maximum_output_age_ms=_positive_int(
            quote["maximum_output_age_ms"],
            "metrics.quote_quality.maximum_output_age_ms",
        ),
        demand_retry_interval_ms=_positive_int(
            quote["demand_retry_interval_ms"],
            "metrics.quote_quality.demand_retry_interval_ms",
        ),
        evidence_snapshot_retry_interval_ms=_positive_int(
            quote["evidence_snapshot_retry_interval_ms"],
            "metrics.quote_quality.evidence_snapshot_retry_interval_ms",
        ),
        priority=priority,
    )
    session = _load_session_measurements(values["session_measurements"])
    entity_analysis = _load_entity_analysis(values["entity_analysis"])
    return MetricsConfig(
        quote_quality=quote_config,
        session_measurements=session,
        entity_analysis=entity_analysis,
    )


def _load_entity_analysis(raw: Any) -> EntityAnalysisConfig:
    values = _mapping(raw, "metrics.entity_analysis")
    _require_keys_allowing(
        values,
        {
            "enabled",
            "required_watchlist_capability",
            "catalog_version",
            "parameter_source",
            "parameter_effective_from",
            "maximum_entities_global",
            "maximum_entities_per_instrument",
            "maximum_entities_per_instrument_type",
            "completed_session_retention",
            "completed_session_maximum_age_days",
            "maximum_input_age_ms",
            "minimum_snapshot_interval_ms",
            "maximum_publications_per_cycle",
            "definitions",
        },
        {"maximum_metric_values", "market_state_reconciliation_interval_ms"},
        "metrics.entity_analysis",
    )
    enabled = _bool(values["enabled"], "metrics.entity_analysis.enabled")
    definitions = tuple(
        _load_entity_definition(item, index=index)
        for index, item in enumerate(
            _table_array(values["definitions"], "metrics.entity_analysis.definitions"),
        )
    )
    if enabled and not definitions:
        raise ValueError("metrics.entity_analysis.definitions must not be empty")
    catalog_version = _positive_int(
        values["catalog_version"],
        "metrics.entity_analysis.catalog_version",
    )
    if any(item.market_state is not None for item in definitions) and catalog_version < 2:
        raise ValueError("market-state bindings require entity-analysis catalog version 2")
    if any(item.market_state is not None for item in definitions):
        missing_runtime_limits = {
            key
            for key in ("maximum_metric_values", "market_state_reconciliation_interval_ms")
            if key not in values
        }
        if missing_runtime_limits:
            raise ValueError(
                "market-state bindings require explicit runtime limits: "
                f"{', '.join(sorted(missing_runtime_limits))}",
            )
    definition_ids = tuple(item.definition_id for item in definitions)
    if len(definition_ids) != len(set(definition_ids)):
        raise ValueError("entity definition IDs must be unique")
    definition_keys = tuple((item.entity_type, item.entity_version) for item in definitions)
    if len(definition_keys) != len(set(definition_keys)):
        raise ValueError("entity type/version definitions must be unique")
    if enabled:
        represented_groups = {item.group for item in definitions if item.enabled}
        missing_groups = sorted(_ENTITY_GROUPS - represented_groups)
        if missing_groups:
            raise ValueError(
                f"enabled entity analysis lacks definition groups: {', '.join(missing_groups)}",
            )
    maximum_entities_global = _positive_int(
        values["maximum_entities_global"],
        "metrics.entity_analysis.maximum_entities_global",
    )
    maximum_entities_per_instrument = _positive_int(
        values["maximum_entities_per_instrument"],
        "metrics.entity_analysis.maximum_entities_per_instrument",
    )
    maximum_entities_per_instrument_type = _positive_int(
        values["maximum_entities_per_instrument_type"],
        "metrics.entity_analysis.maximum_entities_per_instrument_type",
    )
    if maximum_entities_per_instrument > maximum_entities_global:
        raise ValueError("entity per-instrument bound cannot exceed the global bound")
    if maximum_entities_per_instrument_type > maximum_entities_per_instrument:
        raise ValueError("entity per-instrument/type bound cannot exceed per-instrument bound")
    completed_session_retention = _positive_int(
        values["completed_session_retention"],
        "metrics.entity_analysis.completed_session_retention",
    )
    completed_session_maximum_age_days = _positive_int(
        values["completed_session_maximum_age_days"],
        "metrics.entity_analysis.completed_session_maximum_age_days",
    )
    return EntityAnalysisConfig(
        enabled=enabled,
        required_watchlist_capability=_non_empty_string(
            values["required_watchlist_capability"],
            "metrics.entity_analysis.required_watchlist_capability",
        ),
        catalog_version=catalog_version,
        parameter_source=_non_empty_string(
            values["parameter_source"],
            "metrics.entity_analysis.parameter_source",
        ),
        parameter_effective_from_ns=_utc_timestamp_ns(
            values["parameter_effective_from"],
            "metrics.entity_analysis.parameter_effective_from",
        ),
        maximum_entities_global=maximum_entities_global,
        maximum_entities_per_instrument=maximum_entities_per_instrument,
        maximum_entities_per_instrument_type=maximum_entities_per_instrument_type,
        completed_session_retention=completed_session_retention,
        completed_session_maximum_age_days=completed_session_maximum_age_days,
        maximum_input_age_ms=_positive_int(
            values["maximum_input_age_ms"],
            "metrics.entity_analysis.maximum_input_age_ms",
        ),
        maximum_metric_values=(
            None
            if "maximum_metric_values" not in values
            else _positive_int(
                values["maximum_metric_values"],
                "metrics.entity_analysis.maximum_metric_values",
            )
        ),
        market_state_reconciliation_interval_ms=(
            None
            if "market_state_reconciliation_interval_ms" not in values
            else _positive_int(
                values["market_state_reconciliation_interval_ms"],
                "metrics.entity_analysis.market_state_reconciliation_interval_ms",
            )
        ),
        minimum_snapshot_interval_ms=_non_negative_int(
            values["minimum_snapshot_interval_ms"],
            "metrics.entity_analysis.minimum_snapshot_interval_ms",
        ),
        maximum_publications_per_cycle=_positive_int(
            values["maximum_publications_per_cycle"],
            "metrics.entity_analysis.maximum_publications_per_cycle",
        ),
        definitions=definitions,
    )


def _load_entity_definition(raw: Any, *, index: int) -> EntityDefinitionConfig:
    label = f"metrics.entity_analysis.definitions[{index}]"
    values = _mapping(raw, label)
    _require_keys_allowing(
        values,
        {
            "definition_id",
            "group",
            "entity_type",
            "entity_version",
            "enabled",
            "decision_question",
            "implementation_id",
            "formula_version",
            "identity_dimensions",
            "durability",
            "completion_rule",
            "invalidation_rule",
            "expiry_rule",
            "permitted_health",
            "permitted_fidelities",
            "applications",
            "metric_inputs",
            "entity_inputs",
            "parameters",
            "parameter_sets",
        },
        {"market_state"},
        label,
    )
    group = _non_empty_string(values["group"], f"{label}.group")
    if group not in _ENTITY_GROUPS:
        raise ValueError(f"{label}.group is unsupported: {group}")
    durability = _non_empty_string(values["durability"], f"{label}.durability")
    if durability not in _ENTITY_DURABILITY_VALUES:
        raise ValueError(f"{label}.durability is unsupported: {durability}")
    permitted_health = _enum_strings(
        values["permitted_health"],
        f"{label}.permitted_health",
        _ENTITY_HEALTH_VALUES,
    )
    permitted_fidelities = _enum_strings(
        values["permitted_fidelities"],
        f"{label}.permitted_fidelities",
        _ENTITY_FIDELITY_VALUES,
    )
    applications = tuple(
        _load_entity_application(item, label=f"{label}.applications[{position}]")
        for position, item in enumerate(
            _table_array(values["applications"], f"{label}.applications")
        )
    )
    if not applications:
        raise ValueError(f"{label}.applications must not be empty")
    application_ids = tuple(item.application_id for item in applications)
    if len(application_ids) != len(set(application_ids)):
        raise ValueError(f"{label} application IDs must be unique")
    metric_inputs = tuple(
        _load_entity_metric_input(item, label=f"{label}.metric_inputs[{position}]")
        for position, item in enumerate(
            _table_array(values["metric_inputs"], f"{label}.metric_inputs")
        )
    )
    entity_inputs = tuple(
        _load_entity_input(item, label=f"{label}.entity_inputs[{position}]")
        for position, item in enumerate(
            _table_array(values["entity_inputs"], f"{label}.entity_inputs")
        )
    )
    if not metric_inputs and not entity_inputs:
        raise ValueError(f"{label} must declare at least one metric or entity input")
    input_roles = tuple(item.role for item in (*metric_inputs, *entity_inputs))
    if len(input_roles) != len(set(input_roles)):
        raise ValueError(f"{label} dependency roles must be unique")
    parameters = tuple(
        _load_entity_parameter(item, label=f"{label}.parameters[{position}]")
        for position, item in enumerate(_table_array(values["parameters"], f"{label}.parameters"))
    )
    parameter_ids = tuple(item.parameter_id for item in parameters)
    if len(parameter_ids) != len(set(parameter_ids)):
        raise ValueError(f"{label} parameter IDs must be unique")
    parameter_sets = tuple(
        _load_entity_parameter_set(
            item,
            label=f"{label}.parameter_sets[{position}]",
            parameters=parameters,
        )
        for position, item in enumerate(
            _table_array(values["parameter_sets"], f"{label}.parameter_sets"),
        )
    )
    if parameters and not parameter_sets:
        raise ValueError(f"{label} parameters require at least one parameter set")
    parameter_set_ids = tuple(item.parameter_set_id for item in parameter_sets)
    if len(parameter_set_ids) != len(set(parameter_set_ids)):
        raise ValueError(f"{label} parameter-set IDs must be unique")
    unavailable_parameter_sets = sorted(
        {
            application.parameter_set_id
            for application in applications
            if application.parameter_set_id not in set(parameter_set_ids)
        },
    )
    if unavailable_parameter_sets:
        raise ValueError(
            f"{label} applications reference unavailable parameter sets: "
            + ", ".join(unavailable_parameter_sets),
        )
    market_state = (
        None
        if "market_state" not in values
        else _load_entity_market_state(
            values["market_state"],
            label=f"{label}.market_state",
            parameters=parameters,
            parameter_sets=parameter_sets,
            metric_inputs=metric_inputs,
        )
    )
    if market_state is not None and group not in {
        "volatility_compression_expansion",
        "direction_trend_rotation_reference",
    }:
        raise ValueError(f"{label}.market_state is unsupported for group: {group}")
    return EntityDefinitionConfig(
        definition_id=_non_empty_string(values["definition_id"], f"{label}.definition_id"),
        group=group,
        entity_type=_non_empty_string(values["entity_type"], f"{label}.entity_type"),
        entity_version=_positive_int(values["entity_version"], f"{label}.entity_version"),
        enabled=_bool(values["enabled"], f"{label}.enabled"),
        decision_question=_non_empty_string(
            values["decision_question"],
            f"{label}.decision_question",
        ),
        implementation_id=_non_empty_string(
            values["implementation_id"],
            f"{label}.implementation_id",
        ),
        formula_version=_positive_int(values["formula_version"], f"{label}.formula_version"),
        identity_dimensions=_unique_non_empty_strings(
            values["identity_dimensions"],
            f"{label}.identity_dimensions",
        ),
        durability=durability,
        completion_rule=_non_empty_string(
            values["completion_rule"],
            f"{label}.completion_rule",
        ),
        invalidation_rule=_non_empty_string(
            values["invalidation_rule"],
            f"{label}.invalidation_rule",
        ),
        expiry_rule=_non_empty_string(values["expiry_rule"], f"{label}.expiry_rule"),
        permitted_health=permitted_health,
        permitted_fidelities=permitted_fidelities,
        applications=applications,
        metric_inputs=metric_inputs,
        entity_inputs=entity_inputs,
        parameters=parameters,
        parameter_sets=parameter_sets,
        market_state=market_state,
    )


def _load_entity_application(raw: Any, *, label: str) -> EntityApplicationConfig:
    values = _mapping(raw, label)
    _require_keys(
        values,
        {
            "application_id",
            "parameter_set_id",
            "analytical_profile_ids",
            "instrument_ids",
            "instrument_classes",
            "session_phases",
            "horizon",
            "source_selector",
            "requires_volume",
        },
        label,
    )
    instrument_ids = _unique_strings(values["instrument_ids"], f"{label}.instrument_ids")
    instrument_classes = _unique_strings(
        values["instrument_classes"],
        f"{label}.instrument_classes",
    )
    if not instrument_ids and not instrument_classes:
        raise ValueError(f"{label} must select instrument IDs or instrument classes")
    return EntityApplicationConfig(
        application_id=_non_empty_string(values["application_id"], f"{label}.application_id"),
        parameter_set_id=_non_empty_string(
            values["parameter_set_id"],
            f"{label}.parameter_set_id",
        ),
        analytical_profile_ids=_unique_non_empty_strings(
            values["analytical_profile_ids"],
            f"{label}.analytical_profile_ids",
        ),
        instrument_ids=instrument_ids,
        instrument_classes=instrument_classes,
        session_phases=_unique_non_empty_strings(
            values["session_phases"],
            f"{label}.session_phases",
        ),
        horizon=_non_empty_string(values["horizon"], f"{label}.horizon"),
        source_selector=_non_empty_string(
            values["source_selector"],
            f"{label}.source_selector",
        ),
        requires_volume=_bool(values["requires_volume"], f"{label}.requires_volume"),
    )


def _load_entity_metric_input(raw: Any, *, label: str) -> EntityMetricInputConfig:
    values = _mapping(raw, label)
    _require_keys(
        values,
        {
            "role",
            "metric_id",
            "metric_version",
            "parameter_version",
            "required",
            "permitted_health",
            "permitted_fidelities",
        },
        label,
    )
    return EntityMetricInputConfig(
        role=_non_empty_string(values["role"], f"{label}.role"),
        metric_id=_non_empty_string(values["metric_id"], f"{label}.metric_id"),
        metric_version=_positive_int(values["metric_version"], f"{label}.metric_version"),
        parameter_version=_positive_int(
            values["parameter_version"],
            f"{label}.parameter_version",
        ),
        required=_bool(values["required"], f"{label}.required"),
        permitted_health=_enum_strings(
            values["permitted_health"],
            f"{label}.permitted_health",
            _ENTITY_HEALTH_VALUES,
        ),
        permitted_fidelities=_enum_strings(
            values["permitted_fidelities"],
            f"{label}.permitted_fidelities",
            _ENTITY_FIDELITY_VALUES,
        ),
    )


def _load_entity_input(raw: Any, *, label: str) -> EntityInputConfig:
    values = _mapping(raw, label)
    _require_keys(
        values,
        {
            "role",
            "entity_type",
            "entity_version",
            "required",
            "permitted_health",
            "permitted_fidelities",
        },
        label,
    )
    return EntityInputConfig(
        role=_non_empty_string(values["role"], f"{label}.role"),
        entity_type=_non_empty_string(values["entity_type"], f"{label}.entity_type"),
        entity_version=_positive_int(values["entity_version"], f"{label}.entity_version"),
        required=_bool(values["required"], f"{label}.required"),
        permitted_health=_enum_strings(
            values["permitted_health"],
            f"{label}.permitted_health",
            _ENTITY_HEALTH_VALUES,
        ),
        permitted_fidelities=_enum_strings(
            values["permitted_fidelities"],
            f"{label}.permitted_fidelities",
            _ENTITY_FIDELITY_VALUES,
        ),
    )


def _load_entity_parameter(raw: Any, *, label: str) -> EntityParameterConfig:
    values = _mapping(raw, label)
    base_keys = {
        "parameter_id",
        "meaning",
        "value_kind",
        "unit",
        "default",
        "dynamic",
        "mutability",
        "source",
    }
    value_kind = _non_empty_string(values.get("value_kind"), f"{label}.value_kind")
    if value_kind not in _PARAMETER_VALUE_KINDS:
        raise ValueError(f"{label}.value_kind is unsupported: {value_kind}")
    numeric = value_kind in {"number", "integer"}
    expected = base_keys | ({"minimum", "maximum", "step"} if numeric else {"allowed_values"})
    _require_keys(values, expected, label)
    default = _entity_scalar(values["default"], f"{label}.default")
    dynamic = _bool(values["dynamic"], f"{label}.dynamic")
    mutability = _non_empty_string(values["mutability"], f"{label}.mutability")
    if mutability not in _PARAMETER_MUTABILITY_VALUES:
        raise ValueError(f"{label}.mutability is unsupported: {mutability}")
    expected_mutability = "policy_controlled_runtime" if dynamic else "startup_only"
    if mutability != expected_mutability:
        raise ValueError(f"{label} dynamic eligibility conflicts with mutability")
    minimum: int | float | None = None
    maximum: int | float | None = None
    step: int | float | None = None
    allowed_values: tuple[EntityConfigScalar, ...] = ()
    if numeric:
        minimum = _finite_number(values["minimum"], f"{label}.minimum")
        maximum = _finite_number(values["maximum"], f"{label}.maximum")
        step = _finite_number(values["step"], f"{label}.step")
        if minimum > maximum:
            raise ValueError(f"{label}.minimum cannot exceed maximum")
        if step <= 0:
            raise ValueError(f"{label}.step must be positive")
    else:
        allowed_values = tuple(
            _entity_scalar(item, f"{label}.allowed_values[]")
            for item in _array(values["allowed_values"], f"{label}.allowed_values")
        )
        if not allowed_values or len(allowed_values) != len(set(allowed_values)):
            raise ValueError(f"{label}.allowed_values must be non-empty and unique")
    parameter = EntityParameterConfig(
        parameter_id=_non_empty_string(values["parameter_id"], f"{label}.parameter_id"),
        meaning=_non_empty_string(values["meaning"], f"{label}.meaning"),
        value_kind=value_kind,
        unit=_non_empty_string(values["unit"], f"{label}.unit"),
        default=default,
        dynamic=dynamic,
        mutability=mutability,
        source=_non_empty_string(values["source"], f"{label}.source"),
        minimum=minimum,
        maximum=maximum,
        step=step,
        allowed_values=allowed_values,
    )
    _validate_entity_parameter_value(parameter, default, label=f"{label}.default")
    return parameter


def _load_entity_parameter_set(
    raw: Any,
    *,
    label: str,
    parameters: tuple[EntityParameterConfig, ...],
) -> EntityParameterSetConfig:
    values = _mapping(raw, label)
    _require_keys(
        values,
        {"parameter_set_id", "parameter_version", "effective_from", "source", "values"},
        label,
    )
    configured = _mapping(values["values"], f"{label}.values")
    by_id = {item.parameter_id: item for item in parameters}
    if set(configured) != set(by_id):
        raise ValueError(f"{label}.values must provide every declared parameter exactly once")
    normalized: list[tuple[str, EntityConfigScalar]] = []
    for parameter_id, raw_value in sorted(configured.items()):
        value = _entity_scalar(raw_value, f"{label}.values.{parameter_id}")
        _validate_entity_parameter_value(
            by_id[parameter_id],
            value,
            label=f"{label}.values.{parameter_id}",
        )
        normalized.append((parameter_id, value))
    return EntityParameterSetConfig(
        parameter_set_id=_non_empty_string(
            values["parameter_set_id"],
            f"{label}.parameter_set_id",
        ),
        parameter_version=_positive_int(
            values["parameter_version"],
            f"{label}.parameter_version",
        ),
        effective_from_ns=_utc_timestamp_ns(
            values["effective_from"],
            f"{label}.effective_from",
        ),
        source=_non_empty_string(values["source"], f"{label}.source"),
        values=tuple(normalized),
    )


def _load_entity_market_state(
    raw: Any,
    *,
    label: str,
    parameters: tuple[EntityParameterConfig, ...],
    parameter_sets: tuple[EntityParameterSetConfig, ...],
    metric_inputs: tuple[EntityMetricInputConfig, ...],
) -> EntityMarketStateConfig:
    values = _mapping(raw, label)
    _require_keys_allowing(
        values,
        {"parameter_set_id", "policies"},
        {"normalization", "reference_id", "reference_kind"},
        label,
    )
    parameter_set_id = _non_empty_string(
        values["parameter_set_id"],
        f"{label}.parameter_set_id",
    )
    parameter_set = next(
        (item for item in parameter_sets if item.parameter_set_id == parameter_set_id),
        None,
    )
    if parameter_set is None:
        raise ValueError(f"{label} references an unknown parameter set: {parameter_set_id}")
    dependency_parameter_versions = {item.parameter_version for item in metric_inputs}
    if dependency_parameter_versions != {parameter_set.parameter_version}:
        raise ValueError(
            f"{label} metric dependencies must match the selected parameter-set version",
        )
    policies = tuple(
        _load_entity_state_policy(
            item,
            label=f"{label}.policies[{position}]",
            parameters=parameters,
            parameter_set=parameter_set,
            metric_inputs=metric_inputs,
        )
        for position, item in enumerate(_table_array(values["policies"], f"{label}.policies"))
    )
    if not policies:
        raise ValueError(f"{label}.policies must not be empty")
    axes = tuple(item.axis for item in policies)
    if len(axes) != len(set(axes)):
        raise ValueError(f"{label} policy axes must be unique")
    identities = tuple((item.policy_id, item.policy_version) for item in policies)
    if len(identities) != len(set(identities)):
        raise ValueError(f"{label} policy identities must be unique")
    return EntityMarketStateConfig(
        parameter_set_id=parameter_set_id,
        normalization=_optional_config_text(values, "normalization", label),
        reference_id=_optional_config_text(values, "reference_id", label),
        reference_kind=_optional_config_text(values, "reference_kind", label),
        policies=policies,
    )


def _load_entity_state_policy(
    raw: Any,
    *,
    label: str,
    parameters: tuple[EntityParameterConfig, ...],
    parameter_set: EntityParameterSetConfig,
    metric_inputs: tuple[EntityMetricInputConfig, ...],
) -> EntityStatePolicyConfig:
    values = _mapping(raw, label)
    _require_keys(
        values,
        {
            "axis",
            "policy_id",
            "policy_version",
            "measure_role",
            "coverage_role",
            "unavailable_category",
            "bands",
            "hysteresis_parameter_id",
            "confirmation_observations_parameter_id",
            "minimum_coverage_ratio_parameter_id",
            "maximum_evidence_age_ms_parameter_id",
            "permitted_health",
            "permitted_fidelities",
        },
        label,
    )
    input_by_role = {item.role: item for item in metric_inputs}
    measure_role = _non_empty_string(values["measure_role"], f"{label}.measure_role")
    coverage_role = _non_empty_string(values["coverage_role"], f"{label}.coverage_role")
    for role, role_label in ((measure_role, "measure"), (coverage_role, "coverage")):
        dependency = input_by_role.get(role)
        if dependency is None:
            raise ValueError(f"{label} references an unknown {role_label} role: {role}")
        if not dependency.required:
            raise ValueError(f"{label} {role_label} role must be required: {role}")
    parameter_by_id = {item.parameter_id: item for item in parameters}
    configured_values = dict(parameter_set.values)
    parameter_refs = {
        "hysteresis_parameter_id": _non_empty_string(
            values["hysteresis_parameter_id"],
            f"{label}.hysteresis_parameter_id",
        ),
        "confirmation_observations_parameter_id": _non_empty_string(
            values["confirmation_observations_parameter_id"],
            f"{label}.confirmation_observations_parameter_id",
        ),
        "minimum_coverage_ratio_parameter_id": _non_empty_string(
            values["minimum_coverage_ratio_parameter_id"],
            f"{label}.minimum_coverage_ratio_parameter_id",
        ),
        "maximum_evidence_age_ms_parameter_id": _non_empty_string(
            values["maximum_evidence_age_ms_parameter_id"],
            f"{label}.maximum_evidence_age_ms_parameter_id",
        ),
    }
    expected_kinds = {
        "hysteresis_parameter_id": "number",
        "confirmation_observations_parameter_id": "integer",
        "minimum_coverage_ratio_parameter_id": "number",
        "maximum_evidence_age_ms_parameter_id": "integer",
    }
    for field, parameter_id in parameter_refs.items():
        _require_state_parameter(
            parameter_id,
            expected_kind=expected_kinds[field],
            parameter_by_id=parameter_by_id,
            configured_values=configured_values,
            label=f"{label}.{field}",
        )
    bands = tuple(
        _load_entity_state_band(
            item,
            label=f"{label}.bands[{position}]",
            parameter_by_id=parameter_by_id,
            configured_values=configured_values,
        )
        for position, item in enumerate(_table_array(values["bands"], f"{label}.bands"))
    )
    if len(bands) < 2:
        raise ValueError(f"{label}.bands must contain at least two categories")
    categories = tuple(item.category for item in bands)
    if len(categories) != len(set(categories)):
        raise ValueError(f"{label}.bands categories must be unique")
    unavailable_category = _non_empty_string(
        values["unavailable_category"],
        f"{label}.unavailable_category",
    )
    if unavailable_category in categories:
        raise ValueError(f"{label}.unavailable_category must not be a classified category")
    if bands[0].lower_bound_parameter_id is not None:
        raise ValueError(f"{label} first band must be unbounded below")
    if bands[-1].upper_bound_parameter_id is not None:
        raise ValueError(f"{label} last band must be unbounded above")
    for previous, current in zip(bands, bands[1:], strict=False):
        if previous.upper_bound_parameter_id != current.lower_bound_parameter_id:
            raise ValueError(f"{label}.bands must share contiguous boundary parameters")
    return EntityStatePolicyConfig(
        axis=_non_empty_string(values["axis"], f"{label}.axis"),
        policy_id=_non_empty_string(values["policy_id"], f"{label}.policy_id"),
        policy_version=_positive_int(values["policy_version"], f"{label}.policy_version"),
        measure_role=measure_role,
        coverage_role=coverage_role,
        unavailable_category=unavailable_category,
        bands=bands,
        hysteresis_parameter_id=parameter_refs["hysteresis_parameter_id"],
        confirmation_observations_parameter_id=parameter_refs[
            "confirmation_observations_parameter_id"
        ],
        minimum_coverage_ratio_parameter_id=parameter_refs[
            "minimum_coverage_ratio_parameter_id"
        ],
        maximum_evidence_age_ms_parameter_id=parameter_refs[
            "maximum_evidence_age_ms_parameter_id"
        ],
        permitted_health=_enum_strings(
            values["permitted_health"],
            f"{label}.permitted_health",
            _ENTITY_HEALTH_VALUES,
        ),
        permitted_fidelities=_enum_strings(
            values["permitted_fidelities"],
            f"{label}.permitted_fidelities",
            _ENTITY_FIDELITY_VALUES,
        ),
    )


def _load_entity_state_band(
    raw: Any,
    *,
    label: str,
    parameter_by_id: dict[str, EntityParameterConfig],
    configured_values: dict[str, EntityConfigScalar],
) -> EntityStateBandConfig:
    values = _mapping(raw, label)
    _require_keys_allowing(
        values,
        {"category"},
        {"lower_bound_parameter_id", "upper_bound_parameter_id"},
        label,
    )
    lower = _optional_config_text(values, "lower_bound_parameter_id", label)
    upper = _optional_config_text(values, "upper_bound_parameter_id", label)
    for field, parameter_id in (
        ("lower_bound_parameter_id", lower),
        ("upper_bound_parameter_id", upper),
    ):
        if parameter_id is not None:
            _require_state_parameter(
                parameter_id,
                expected_kind="number",
                parameter_by_id=parameter_by_id,
                configured_values=configured_values,
                label=f"{label}.{field}",
            )
    return EntityStateBandConfig(
        category=_non_empty_string(values["category"], f"{label}.category"),
        lower_bound_parameter_id=lower,
        upper_bound_parameter_id=upper,
    )


def _require_state_parameter(
    parameter_id: str,
    *,
    expected_kind: str,
    parameter_by_id: dict[str, EntityParameterConfig],
    configured_values: dict[str, EntityConfigScalar],
    label: str,
) -> None:
    parameter = parameter_by_id.get(parameter_id)
    if parameter is None or parameter_id not in configured_values:
        raise ValueError(f"{label} references an unknown configured parameter: {parameter_id}")
    if parameter.value_kind != expected_kind:
        raise ValueError(f"{label} requires a {expected_kind} parameter: {parameter_id}")


def _optional_config_text(values: dict[str, Any], key: str, label: str) -> str | None:
    if key not in values:
        return None
    return _non_empty_string(values[key], f"{label}.{key}")


def _validate_entity_analysis_scope(
    config: EntityAnalysisConfig,
    *,
    profiles: dict[str, AnalyticalSessionProfileConfig],
    bound_instruments: dict[str, str],
    watchlist: dict[str, WatchlistMemberConfig],
    rolling_families: tuple[RollingFamilyConfig, ...],
    completed_bars: CompletedBarMetricsConfig,
) -> None:
    if not config.enabled:
        return
    if not bound_instruments:
        raise ValueError("enabled entity analysis requires session measurement profile bindings")
    available_selectors = {
        completed_bars.live_selector,
        completed_bars.historical_selector,
        *(item.source_selector for item in rolling_families),
        *(item.input_selector for item in rolling_families),
    }
    definition_keys = {(item.entity_type, item.entity_version) for item in config.definitions}
    for definition in config.definitions:
        for dependency in definition.entity_inputs:
            if (dependency.entity_type, dependency.entity_version) not in definition_keys:
                raise ValueError(
                    "entity analysis references an unknown entity dependency: "
                    f"{definition.definition_id}/{dependency.role}",
                )
            if (dependency.entity_type, dependency.entity_version) == (
                definition.entity_type,
                definition.entity_version,
            ):
                raise ValueError("an entity analysis definition cannot depend on itself")
        versions = tuple(item.parameter_version for item in definition.parameter_sets)
        if len(versions) != len(set(versions)):
            raise ValueError(
                f"entity parameter versions must be unique: {definition.definition_id}",
            )
        for application in definition.applications:
            unknown_profiles = sorted(set(application.analytical_profile_ids) - set(profiles))
            if unknown_profiles:
                raise ValueError(
                    "entity application references unknown analytical profiles: "
                    f"{', '.join(unknown_profiles)}",
                )
            unknown_instruments = sorted(set(application.instrument_ids) - set(watchlist))
            if unknown_instruments:
                raise ValueError(
                    "entity application references unknown watchlist instruments: "
                    f"{', '.join(unknown_instruments)}",
                )
            for instrument_id in application.instrument_ids:
                if bound_instruments.get(instrument_id) not in application.analytical_profile_ids:
                    raise ValueError(
                        "entity application instrument/profile mismatch: "
                        f"{definition.definition_id}/{application.application_id}/"
                        f"{instrument_id}",
                    )
            if application.requires_volume:
                unsupported = sorted(
                    profile_id
                    for profile_id in application.analytical_profile_ids
                    if not profiles[profile_id].volume_supported
                )
                if unsupported:
                    raise ValueError(
                        "volume-dependent entity application selects unsupported profiles: "
                        f"{', '.join(unsupported)}",
                    )
            if (
                application.source_selector not in available_selectors
                and not _is_supported_bar_selector(application.source_selector)
            ):
                raise ValueError(
                    "entity application source selector is unsupported: "
                    f"{application.source_selector}",
                )
            selected_instruments = set(application.instrument_ids) or {
                instrument_id
                for instrument_id, profile_id in bound_instruments.items()
                if profile_id in application.analytical_profile_ids
            }
            if not selected_instruments:
                raise ValueError(
                    "entity application selects no profile-bound instruments: "
                    f"{definition.definition_id}/{application.application_id}",
                )


def _validate_entity_parameter_value(
    parameter: EntityParameterConfig,
    value: EntityConfigScalar,
    *,
    label: str,
) -> None:
    valid_kind = {
        "number": isinstance(value, int | float) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "text": isinstance(value, str) and bool(value.strip()),
    }[parameter.value_kind]
    if not valid_kind:
        raise ValueError(f"{label} does not match {parameter.value_kind}")
    if parameter.value_kind in {"number", "integer"}:
        assert parameter.minimum is not None
        assert parameter.maximum is not None
        assert parameter.step is not None
        if value < parameter.minimum or value > parameter.maximum:
            raise ValueError(f"{label} is outside its configured envelope")
        offset = Decimal(str(value)) - Decimal(str(parameter.minimum))
        if offset % Decimal(str(parameter.step)) != 0:
            raise ValueError(f"{label} does not align with its configured step")
        return
    if value not in parameter.allowed_values:
        raise ValueError(f"{label} is outside its allowed values")


def _is_supported_bar_selector(value: str) -> bool:
    return (
        re.fullmatch(
            r"[1-9][0-9]*-(SECOND|MINUTE|HOUR|DAY|WEEK)-[A-Z_]+-(EXTERNAL|INTERNAL)",
            value,
        )
        is not None
    )


def _load_session_measurements(raw: Any) -> SessionMeasurementsConfig:
    values = _mapping(raw, "metrics.session_measurements")
    _require_keys(
        values,
        {
            "enabled",
            "required_watchlist_capability",
            "parameter_version",
            "parameter_source",
            "parameter_effective_from",
            "conflict_policy",
            "maximum_active_sessions",
            "demand_retry_interval_ms",
            "evidence_snapshot_retry_interval_ms",
            "priority",
            "completed_bars",
            "session_references",
            "session_windows",
            "rolling_measurements",
            "profiles",
            "profile_bindings",
        },
        "metrics.session_measurements",
    )
    conflict_policy = _non_empty_string(
        values["conflict_policy"],
        "metrics.session_measurements.conflict_policy",
    )
    if conflict_policy != "reject_conflict":
        raise ValueError("metrics.session_measurements.conflict_policy must be reject_conflict")
    priority = _non_negative_int(values["priority"], "metrics.session_measurements.priority")
    if priority > 100:
        raise ValueError("metrics.session_measurements.priority must not exceed 100")
    completed = _mapping(
        values["completed_bars"],
        "metrics.session_measurements.completed_bars",
    )
    _require_keys(
        completed,
        {
            "live_selector",
            "historical_selector",
            "historical_window",
            "minimum_historical_observations",
            "maximum_historical_observations",
            "calculation_interval_seconds",
            "minimum_interval_seconds",
            "maximum_interval_seconds",
            "interval_step_seconds",
            "interval_dynamic",
            "aggregation_boundary_policy",
            "timestamp_policy",
            "revision_policy",
            "maximum_retained_observations",
            "maximum_output_age_ms",
        },
        "metrics.session_measurements.completed_bars",
    )
    minimum_history = _positive_int(
        completed["minimum_historical_observations"],
        "metrics.session_measurements.completed_bars.minimum_historical_observations",
    )
    maximum_history = _positive_int(
        completed["maximum_historical_observations"],
        "metrics.session_measurements.completed_bars.maximum_historical_observations",
    )
    if maximum_history < minimum_history:
        raise ValueError("completed-bar maximum historical observations cannot be below minimum")
    minimum_interval = _positive_int(
        completed["minimum_interval_seconds"],
        "metrics.session_measurements.completed_bars.minimum_interval_seconds",
    )
    maximum_interval = _positive_int(
        completed["maximum_interval_seconds"],
        "metrics.session_measurements.completed_bars.maximum_interval_seconds",
    )
    interval = _positive_int(
        completed["calculation_interval_seconds"],
        "metrics.session_measurements.completed_bars.calculation_interval_seconds",
    )
    interval_step = _positive_int(
        completed["interval_step_seconds"],
        "metrics.session_measurements.completed_bars.interval_step_seconds",
    )
    if not minimum_interval <= interval <= maximum_interval:
        raise ValueError("completed-bar calculation interval is outside its configured envelope")
    if (interval - minimum_interval) % interval_step:
        raise ValueError("completed-bar calculation interval does not align to its step")
    aggregation_boundary_policy = _non_empty_string(
        completed["aggregation_boundary_policy"],
        "metrics.session_measurements.completed_bars.aggregation_boundary_policy",
    )
    if aggregation_boundary_policy != "utc_fixed_intraday":
        raise ValueError(
            "metrics.session_measurements.completed_bars.aggregation_boundary_policy "
            "must be utc_fixed_intraday",
        )
    if 86_400 % interval:
        raise ValueError("completed-bar UTC-fixed interval must divide one UTC day exactly")
    historical_selector = _non_empty_string(
        completed["historical_selector"],
        "metrics.session_measurements.completed_bars.historical_selector",
    )
    live_selector = _non_empty_string(
        completed["live_selector"],
        "metrics.session_measurements.completed_bars.live_selector",
    )
    try:
        historical_interval = BarSpecification.from_str(
            historical_selector.rsplit("-", maxsplit=1)[0],
        ).get_interval_ns()
        live_interval = BarSpecification.from_str(
            live_selector.rsplit("-", maxsplit=1)[0],
        ).get_interval_ns()
    except ValueError as exc:
        raise ValueError(
            "completed-bar selectors must be valid Nautilus bar specifications",
        ) from exc
    interval_ns = interval * 1_000_000_000
    if historical_interval != interval_ns:
        raise ValueError(
            "completed-bar historical selector interval must equal calculation interval",
        )
    if live_interval > interval_ns or interval_ns % live_interval:
        raise ValueError(
            "completed-bar live selector interval must divide calculation interval",
        )
    timestamp_policy = _non_empty_string(
        completed["timestamp_policy"],
        "metrics.session_measurements.completed_bars.timestamp_policy",
    )
    if timestamp_policy not in {"interval_start", "interval_end"}:
        raise ValueError(
            "metrics.session_measurements.completed_bars.timestamp_policy must be "
            "interval_start or interval_end",
        )
    revision_policy = _non_empty_string(
        completed["revision_policy"],
        "metrics.session_measurements.completed_bars.revision_policy",
    )
    if revision_policy != "reject_revision":
        raise ValueError(
            "metrics.session_measurements.completed_bars.revision_policy must be reject_revision",
        )
    historical_window = _non_empty_string(
        completed["historical_window"],
        "metrics.session_measurements.completed_bars.historical_window",
    )
    supported_historical_windows = {
        "previous_rth",
        "previous_gth_overnight",
        "current_overnight",
        "current_rth",
        "current_gth",
        "curb",
        "premarket",
        "power_hour",
        "overnight",
        "session_to_date",
        "opening_range",
        "named_phase_slice",
        "previous_sessions",
        "recent_completed",
        "anchored_interval",
        "synchronized_interval",
    }
    if historical_window not in supported_historical_windows:
        raise ValueError(
            "metrics.session_measurements.completed_bars.historical_window is unsupported: "
            f"{historical_window!r}",
        )
    references = _load_session_reference_metrics(values["session_references"])
    session_windows = _load_session_window_metrics(values["session_windows"])
    rolling_measurements = _load_rolling_measurements(values["rolling_measurements"])
    if (
        rolling_measurements.maximum_retained_observations
        > completed["maximum_retained_observations"]
    ):
        raise ValueError(
            "rolling measurements cannot retain more observations than the completed-bar ledger",
        )
    for family in rolling_measurements.families:
        if family.source_selector != completed["historical_selector"]:
            raise ValueError(
                "rolling family source_selector must match the completed-bar historical selector",
            )
        if family.input_interval_seconds < interval or family.input_interval_seconds % interval:
            raise ValueError(
                "rolling family input interval must be an integer multiple of the completed-bar "
                "calculation interval",
            )
        expected_policy = (
            "identity" if family.input_interval_seconds == interval else "utc_fixed_intraday"
        )
        if family.aggregation_policy != expected_policy:
            raise ValueError(
                "rolling family aggregation policy does not match its configured input interval",
            )
    minimum_recent_retention = max(
        (candidate.duration_seconds // interval)
        * (rolling_measurements.baseline.minimum_recent_references + 1)
        for family in rolling_measurements.families
        for candidate in family.candidates
        if candidate.active
    )
    if rolling_measurements.maximum_retained_observations < minimum_recent_retention:
        raise ValueError(
            "rolling measurement retention cannot satisfy its configured minimum recent "
            "reference count",
        )
    profiles_raw = values["profiles"]
    if not isinstance(profiles_raw, list) or not profiles_raw:
        raise ValueError("metrics.session_measurements.profiles must be a non-empty array")
    profiles = tuple(
        _load_analytical_profile(item, index) for index, item in enumerate(profiles_raw)
    )
    profile_ids = [profile.profile_id for profile in profiles]
    if len(profile_ids) != len(set(profile_ids)):
        raise ValueError("metrics.session_measurements profile IDs must be unique")
    bindings_raw = values["profile_bindings"]
    if not isinstance(bindings_raw, list) or not bindings_raw:
        raise ValueError("metrics.session_measurements.profile_bindings must be a non-empty array")
    bindings = tuple(
        _load_analytical_profile_binding(item, index) for index, item in enumerate(bindings_raw)
    )
    known_profile_ids = set(profile_ids)
    unknown_binding_profiles = sorted(
        {binding.profile_id for binding in bindings} - known_profile_ids,
    )
    if unknown_binding_profiles:
        raise ValueError(
            "session measurement bindings reference unknown profiles: "
            f"{', '.join(unknown_binding_profiles)}",
        )
    bound_ids = [instrument_id for binding in bindings for instrument_id in binding.instrument_ids]
    if len(bound_ids) != len(set(bound_ids)):
        raise ValueError("session measurement instruments must have exactly one profile binding")
    return SessionMeasurementsConfig(
        enabled=_bool(values["enabled"], "metrics.session_measurements.enabled"),
        required_watchlist_capability=_non_empty_string(
            values["required_watchlist_capability"],
            "metrics.session_measurements.required_watchlist_capability",
        ),
        parameter_version=_positive_int(
            values["parameter_version"],
            "metrics.session_measurements.parameter_version",
        ),
        parameter_source=_non_empty_string(
            values["parameter_source"],
            "metrics.session_measurements.parameter_source",
        ),
        parameter_effective_from_ns=_utc_timestamp_ns(
            values["parameter_effective_from"],
            "metrics.session_measurements.parameter_effective_from",
        ),
        conflict_policy=conflict_policy,
        maximum_active_sessions=_positive_int(
            values["maximum_active_sessions"],
            "metrics.session_measurements.maximum_active_sessions",
        ),
        demand_retry_interval_ms=_positive_int(
            values["demand_retry_interval_ms"],
            "metrics.session_measurements.demand_retry_interval_ms",
        ),
        evidence_snapshot_retry_interval_ms=_positive_int(
            values["evidence_snapshot_retry_interval_ms"],
            "metrics.session_measurements.evidence_snapshot_retry_interval_ms",
        ),
        priority=priority,
        completed_bars=CompletedBarMetricsConfig(
            live_selector=_non_empty_string(
                completed["live_selector"],
                "metrics.session_measurements.completed_bars.live_selector",
            ),
            historical_selector=_non_empty_string(
                completed["historical_selector"],
                "metrics.session_measurements.completed_bars.historical_selector",
            ),
            historical_window=historical_window,
            minimum_historical_observations=minimum_history,
            maximum_historical_observations=maximum_history,
            calculation_interval_seconds=interval,
            minimum_interval_seconds=minimum_interval,
            maximum_interval_seconds=maximum_interval,
            interval_step_seconds=interval_step,
            interval_dynamic=_bool(
                completed["interval_dynamic"],
                "metrics.session_measurements.completed_bars.interval_dynamic",
            ),
            aggregation_boundary_policy=aggregation_boundary_policy,
            timestamp_policy=timestamp_policy,
            revision_policy=revision_policy,
            maximum_retained_observations=_positive_int(
                completed["maximum_retained_observations"],
                "metrics.session_measurements.completed_bars.maximum_retained_observations",
            ),
            maximum_output_age_ms=_positive_int(
                completed["maximum_output_age_ms"],
                "metrics.session_measurements.completed_bars.maximum_output_age_ms",
            ),
        ),
        session_references=references,
        session_windows=session_windows,
        rolling_measurements=rolling_measurements,
        profiles=profiles,
        profile_bindings=bindings,
    )


def _load_analytical_profile_binding(
    raw: Any,
    index: int,
) -> AnalyticalProfileBindingConfig:
    label = f"metrics.session_measurements.profile_bindings[{index}]"
    values = _mapping(raw, label)
    _require_keys(values, {"profile_id", "instrument_ids"}, label)
    return AnalyticalProfileBindingConfig(
        profile_id=_non_empty_string(values["profile_id"], f"{label}.profile_id"),
        instrument_ids=_unique_non_empty_strings(
            values["instrument_ids"],
            f"{label}.instrument_ids",
        ),
    )


def _load_analytical_profile(raw: Any, index: int) -> AnalyticalSessionProfileConfig:
    label = f"metrics.session_measurements.profiles[{index}]"
    values = _mapping(raw, label)
    _require_keys(
        values,
        {
            "profile_id",
            "version",
            "calendar_id",
            "primary_phase",
            "overnight_enabled",
            "overnight_phase",
            "volume_supported",
            "windows",
        },
        label,
    )
    windows_raw = values["windows"]
    if not isinstance(windows_raw, list):
        raise ValueError(f"{label}.windows must be an array")
    windows = tuple(
        _load_analytical_window(item, f"{label}.windows[{window_index}]")
        for window_index, item in enumerate(windows_raw)
    )
    window_ids = [window.window_id for window in windows]
    if len(window_ids) != len(set(window_ids)):
        raise ValueError(f"{label} window IDs must be unique")
    overnight_enabled = _bool(values["overnight_enabled"], f"{label}.overnight_enabled")
    overnight_phase = _non_empty_string(values["overnight_phase"], f"{label}.overnight_phase")
    return AnalyticalSessionProfileConfig(
        profile_id=_non_empty_string(values["profile_id"], f"{label}.profile_id"),
        version=_positive_int(values["version"], f"{label}.version"),
        calendar_id=_non_empty_string(values["calendar_id"], f"{label}.calendar_id"),
        primary_phase=_non_empty_string(values["primary_phase"], f"{label}.primary_phase"),
        overnight_enabled=overnight_enabled,
        overnight_phase=overnight_phase,
        volume_supported=_bool(values["volume_supported"], f"{label}.volume_supported"),
        windows=windows,
    )


def _load_session_reference_metrics(raw: Any) -> SessionReferenceMetricsConfig:
    label = "metrics.session_measurements.session_references"
    values = _mapping(raw, label)
    _require_keys(
        values,
        {
            "enabled",
            "historical_selector",
            "active_window",
            "previous_window",
            "overnight_window",
            "minimum_historical_observations",
            "maximum_historical_observations",
            "vwap_price_basis",
            "vwap_price_basis_dynamic",
            "minimum_coverage_ratio",
            "minimum_coverage_ratio_floor",
            "minimum_coverage_ratio_ceiling",
            "minimum_coverage_ratio_step",
            "minimum_coverage_ratio_dynamic",
            "maximum_retained_sessions",
            "maximum_output_age_ms",
        },
        label,
    )
    active_window = _non_empty_string(values["active_window"], f"{label}.active_window")
    if active_window not in {"session_to_date", "current_rth", "current_gth"}:
        raise ValueError(f"{label}.active_window is unsupported: {active_window!r}")
    previous_window = _non_empty_string(
        values["previous_window"],
        f"{label}.previous_window",
    )
    if previous_window not in {"previous_sessions", "previous_rth"}:
        raise ValueError(f"{label}.previous_window is unsupported: {previous_window!r}")
    overnight_window = _non_empty_string(
        values["overnight_window"],
        f"{label}.overnight_window",
    )
    if overnight_window not in {"current_overnight", "current_gth", "premarket", "overnight"}:
        raise ValueError(f"{label}.overnight_window is unsupported: {overnight_window!r}")
    minimum = _positive_int(
        values["minimum_historical_observations"],
        f"{label}.minimum_historical_observations",
    )
    maximum = _positive_int(
        values["maximum_historical_observations"],
        f"{label}.maximum_historical_observations",
    )
    if maximum < minimum:
        raise ValueError(f"{label} maximum historical observations cannot be below minimum")
    basis = _non_empty_string(values["vwap_price_basis"], f"{label}.vwap_price_basis")
    if basis not in {"typical", "close", "ohlc4"}:
        raise ValueError(f"{label}.vwap_price_basis is unsupported: {basis!r}")
    coverage = _coverage_ratio(values["minimum_coverage_ratio"], f"{label}.minimum_coverage_ratio")
    floor = _coverage_ratio(
        values["minimum_coverage_ratio_floor"],
        f"{label}.minimum_coverage_ratio_floor",
    )
    ceiling = _coverage_ratio(
        values["minimum_coverage_ratio_ceiling"],
        f"{label}.minimum_coverage_ratio_ceiling",
    )
    step = _positive_float(
        values["minimum_coverage_ratio_step"],
        f"{label}.minimum_coverage_ratio_step",
    )
    if not floor <= coverage <= ceiling:
        raise ValueError(f"{label}.minimum_coverage_ratio is outside its configured envelope")
    if step > ceiling - floor:
        raise ValueError(f"{label}.minimum_coverage_ratio_step exceeds its envelope")
    return SessionReferenceMetricsConfig(
        enabled=_bool(values["enabled"], f"{label}.enabled"),
        historical_selector=_non_empty_string(
            values["historical_selector"],
            f"{label}.historical_selector",
        ),
        active_window=active_window,
        previous_window=previous_window,
        overnight_window=overnight_window,
        minimum_historical_observations=minimum,
        maximum_historical_observations=maximum,
        vwap_price_basis=basis,
        vwap_price_basis_dynamic=_bool(
            values["vwap_price_basis_dynamic"],
            f"{label}.vwap_price_basis_dynamic",
        ),
        minimum_coverage_ratio=coverage,
        minimum_coverage_ratio_floor=floor,
        minimum_coverage_ratio_ceiling=ceiling,
        minimum_coverage_ratio_step=step,
        minimum_coverage_ratio_dynamic=_bool(
            values["minimum_coverage_ratio_dynamic"],
            f"{label}.minimum_coverage_ratio_dynamic",
        ),
        maximum_retained_sessions=_positive_int(
            values["maximum_retained_sessions"],
            f"{label}.maximum_retained_sessions",
        ),
        maximum_output_age_ms=_positive_int(
            values["maximum_output_age_ms"],
            f"{label}.maximum_output_age_ms",
        ),
    )


def _load_analytical_window(raw: Any, label: str) -> AnalyticalWindowConfig:
    values = _mapping(raw, label)
    _require_keys(
        values,
        {
            "window_id",
            "purpose",
            "anchor_phase",
            "anchor_boundary",
            "offset_seconds",
            "duration_seconds",
            "minimum_duration_seconds",
            "maximum_duration_seconds",
            "duration_step_seconds",
            "dynamic",
            "historical_selector",
            "minimum_historical_observations",
            "maximum_historical_observations",
        },
        label,
    )
    purpose = _non_empty_string(values["purpose"], f"{label}.purpose")
    if purpose not in {"opening_range", "power_hour", "custom"}:
        raise ValueError(f"{label}.purpose is unsupported: {purpose!r}")
    boundary = _non_empty_string(values["anchor_boundary"], f"{label}.anchor_boundary")
    if boundary not in {"start", "end"}:
        raise ValueError(f"{label}.anchor_boundary must be start or end")
    offset = values["offset_seconds"]
    if not isinstance(offset, int) or isinstance(offset, bool) or not -604_800 <= offset <= 604_800:
        raise ValueError(f"{label}.offset_seconds must be an integer within one week")
    duration = _positive_int(values["duration_seconds"], f"{label}.duration_seconds")
    minimum = _positive_int(
        values["minimum_duration_seconds"],
        f"{label}.minimum_duration_seconds",
    )
    maximum = _positive_int(
        values["maximum_duration_seconds"],
        f"{label}.maximum_duration_seconds",
    )
    step = _positive_int(values["duration_step_seconds"], f"{label}.duration_step_seconds")
    if not minimum <= duration <= maximum:
        raise ValueError(f"{label}.duration_seconds is outside its configured envelope")
    if (duration - minimum) % step:
        raise ValueError(f"{label}.duration_seconds does not align to its step")
    minimum_observations = _positive_int(
        values["minimum_historical_observations"],
        f"{label}.minimum_historical_observations",
    )
    maximum_observations = _positive_int(
        values["maximum_historical_observations"],
        f"{label}.maximum_historical_observations",
    )
    if maximum_observations < minimum_observations:
        raise ValueError(f"{label} maximum historical observations cannot be below minimum")
    return AnalyticalWindowConfig(
        window_id=_non_empty_string(values["window_id"], f"{label}.window_id"),
        purpose=purpose,
        anchor_phase=_non_empty_string(values["anchor_phase"], f"{label}.anchor_phase"),
        anchor_boundary=boundary,
        offset_seconds=offset,
        duration_seconds=duration,
        minimum_duration_seconds=minimum,
        maximum_duration_seconds=maximum,
        duration_step_seconds=step,
        dynamic=_bool(values["dynamic"], f"{label}.dynamic"),
        historical_selector=_non_empty_string(
            values["historical_selector"],
            f"{label}.historical_selector",
        ),
        minimum_historical_observations=minimum_observations,
        maximum_historical_observations=maximum_observations,
    )


def _load_session_window_metrics(raw: Any) -> SessionWindowMetricsConfig:
    label = "metrics.session_measurements.session_windows"
    values = _mapping(raw, label)
    _require_keys(
        values,
        {
            "enabled",
            "price_basis",
            "price_basis_dynamic",
            "minimum_coverage_ratio",
            "minimum_coverage_ratio_floor",
            "minimum_coverage_ratio_ceiling",
            "minimum_coverage_ratio_step",
            "minimum_coverage_ratio_dynamic",
            "maximum_retained_sessions",
            "maximum_output_age_ms",
        },
        label,
    )
    basis = _non_empty_string(values["price_basis"], f"{label}.price_basis")
    if basis not in {"typical", "close", "ohlc4"}:
        raise ValueError(f"{label}.price_basis is unsupported: {basis!r}")
    coverage = _coverage_ratio(values["minimum_coverage_ratio"], f"{label}.minimum_coverage_ratio")
    floor = _coverage_ratio(
        values["minimum_coverage_ratio_floor"],
        f"{label}.minimum_coverage_ratio_floor",
    )
    ceiling = _coverage_ratio(
        values["minimum_coverage_ratio_ceiling"],
        f"{label}.minimum_coverage_ratio_ceiling",
    )
    step = _positive_float(
        values["minimum_coverage_ratio_step"],
        f"{label}.minimum_coverage_ratio_step",
    )
    if not floor <= coverage <= ceiling:
        raise ValueError(f"{label}.minimum_coverage_ratio is outside its configured envelope")
    if step > ceiling - floor:
        raise ValueError(f"{label}.minimum_coverage_ratio_step exceeds its envelope")
    return SessionWindowMetricsConfig(
        enabled=_bool(values["enabled"], f"{label}.enabled"),
        price_basis=basis,
        price_basis_dynamic=_bool(
            values["price_basis_dynamic"],
            f"{label}.price_basis_dynamic",
        ),
        minimum_coverage_ratio=coverage,
        minimum_coverage_ratio_floor=floor,
        minimum_coverage_ratio_ceiling=ceiling,
        minimum_coverage_ratio_step=step,
        minimum_coverage_ratio_dynamic=_bool(
            values["minimum_coverage_ratio_dynamic"],
            f"{label}.minimum_coverage_ratio_dynamic",
        ),
        maximum_retained_sessions=_positive_int(
            values["maximum_retained_sessions"],
            f"{label}.maximum_retained_sessions",
        ),
        maximum_output_age_ms=_positive_int(
            values["maximum_output_age_ms"],
            f"{label}.maximum_output_age_ms",
        ),
    )


def _load_rolling_measurements(raw: Any) -> RollingMeasurementsConfig:
    label = "metrics.session_measurements.rolling_measurements"
    values = _mapping(raw, label)
    _require_keys(
        values,
        {
            "enabled",
            "minimum_coverage_ratio",
            "minimum_coverage_ratio_floor",
            "minimum_coverage_ratio_ceiling",
            "minimum_coverage_ratio_step",
            "minimum_coverage_ratio_dynamic",
            "maximum_retained_observations",
            "maximum_output_age_ms",
            "baseline",
            "families",
        },
        label,
    )
    coverage = _coverage_ratio(values["minimum_coverage_ratio"], f"{label}.minimum_coverage_ratio")
    floor = _coverage_ratio(
        values["minimum_coverage_ratio_floor"],
        f"{label}.minimum_coverage_ratio_floor",
    )
    ceiling = _coverage_ratio(
        values["minimum_coverage_ratio_ceiling"],
        f"{label}.minimum_coverage_ratio_ceiling",
    )
    step = _positive_float(
        values["minimum_coverage_ratio_step"],
        f"{label}.minimum_coverage_ratio_step",
    )
    if not floor <= coverage <= ceiling:
        raise ValueError(f"{label}.minimum_coverage_ratio is outside its configured envelope")
    if step > ceiling - floor:
        raise ValueError(f"{label}.minimum_coverage_ratio_step exceeds its envelope")
    baseline = _load_rolling_baseline(values["baseline"], f"{label}.baseline")
    families_raw = values["families"]
    if not isinstance(families_raw, list) or not families_raw:
        raise ValueError(f"{label}.families must be a non-empty array")
    families = tuple(
        _load_rolling_family(item, f"{label}.families[{index}]")
        for index, item in enumerate(families_raw)
    )
    family_ids = tuple(item.family_id for item in families)
    if len(family_ids) != len(set(family_ids)):
        raise ValueError(f"{label} family IDs must be unique")
    return RollingMeasurementsConfig(
        enabled=_bool(values["enabled"], f"{label}.enabled"),
        minimum_coverage_ratio=coverage,
        minimum_coverage_ratio_floor=floor,
        minimum_coverage_ratio_ceiling=ceiling,
        minimum_coverage_ratio_step=step,
        minimum_coverage_ratio_dynamic=_bool(
            values["minimum_coverage_ratio_dynamic"],
            f"{label}.minimum_coverage_ratio_dynamic",
        ),
        maximum_retained_observations=_positive_int(
            values["maximum_retained_observations"],
            f"{label}.maximum_retained_observations",
        ),
        maximum_output_age_ms=_positive_int(
            values["maximum_output_age_ms"],
            f"{label}.maximum_output_age_ms",
        ),
        baseline=baseline,
        families=families,
    )


def _load_rolling_baseline(raw: Any, label: str) -> RollingBaselineConfig:
    values = _mapping(raw, label)
    keys = {
        "eligible_reference_health",
        "eligible_reference_fidelities",
        "recent_reference_count",
        "recent_reference_count_minimum",
        "recent_reference_count_maximum",
        "recent_reference_count_step",
        "recent_reference_count_dynamic",
        "minimum_recent_references",
        "phase_reference_count",
        "phase_reference_count_minimum",
        "phase_reference_count_maximum",
        "phase_reference_count_step",
        "phase_reference_count_dynamic",
        "minimum_phase_references",
    }
    _require_keys(values, keys, label)
    integer_keys = keys - {"eligible_reference_health", "eligible_reference_fidelities"}
    integers = {
        key: _positive_int(values[key], f"{label}.{key}")
        for key in integer_keys
        if not key.endswith("_dynamic")
    }
    eligible_health = _unique_non_empty_strings(
        values["eligible_reference_health"],
        f"{label}.eligible_reference_health",
    )
    unsupported_health = set(eligible_health) - {
        "READY",
        "WARMING",
        "DEGRADED",
        "STALE",
        "UNAVAILABLE",
        "UNSUPPORTED",
        "FAILED",
    }
    if unsupported_health:
        raise ValueError(f"{label}.eligible_reference_health contains unsupported values")
    eligible_fidelities = _unique_non_empty_strings(
        values["eligible_reference_fidelities"],
        f"{label}.eligible_reference_fidelities",
    )
    unsupported_fidelities = set(eligible_fidelities) - {
        "REPORTED",
        "DERIVED",
        "INFERRED",
        "PARTIAL",
        "UNAVAILABLE",
    }
    if unsupported_fidelities:
        raise ValueError(f"{label}.eligible_reference_fidelities contains unsupported values")
    _validate_integer_envelope(
        integers["recent_reference_count"],
        integers["recent_reference_count_minimum"],
        integers["recent_reference_count_maximum"],
        integers["recent_reference_count_step"],
        f"{label}.recent_reference_count",
    )
    _validate_integer_envelope(
        integers["phase_reference_count"],
        integers["phase_reference_count_minimum"],
        integers["phase_reference_count_maximum"],
        integers["phase_reference_count_step"],
        f"{label}.phase_reference_count",
    )
    if integers["minimum_recent_references"] > integers["recent_reference_count"]:
        raise ValueError(f"{label}.minimum_recent_references exceeds requested count")
    if integers["minimum_phase_references"] > integers["phase_reference_count"]:
        raise ValueError(f"{label}.minimum_phase_references exceeds requested count")
    return RollingBaselineConfig(
        **integers,
        eligible_reference_health=eligible_health,
        eligible_reference_fidelities=eligible_fidelities,
        recent_reference_count_dynamic=_bool(
            values["recent_reference_count_dynamic"],
            f"{label}.recent_reference_count_dynamic",
        ),
        phase_reference_count_dynamic=_bool(
            values["phase_reference_count_dynamic"],
            f"{label}.phase_reference_count_dynamic",
        ),
    )


def _load_rolling_family(raw: Any, label: str) -> RollingFamilyConfig:
    values = _mapping(raw, label)
    _require_keys(
        values,
        {
            "family_id",
            "source_selector",
            "input_selector",
            "input_interval_seconds",
            "aggregation_policy",
            "selected_context_candidate_id",
            "candidates",
        },
        label,
    )
    input_interval = _positive_int(
        values["input_interval_seconds"],
        f"{label}.input_interval_seconds",
    )
    aggregation_policy = _non_empty_string(
        values["aggregation_policy"],
        f"{label}.aggregation_policy",
    )
    if aggregation_policy not in {"identity", "utc_fixed_intraday"}:
        raise ValueError(f"{label}.aggregation_policy is unsupported")
    candidates_raw = values["candidates"]
    if not isinstance(candidates_raw, list) or not candidates_raw:
        raise ValueError(f"{label}.candidates must be a non-empty array")
    candidates = tuple(
        _load_rolling_candidate(item, f"{label}.candidates[{index}]", input_interval)
        for index, item in enumerate(candidates_raw)
    )
    candidate_ids = tuple(item.candidate_id for item in candidates)
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError(f"{label} candidate IDs must be unique")
    selected_id = _non_empty_string(
        values["selected_context_candidate_id"],
        f"{label}.selected_context_candidate_id",
    )
    selected = next((item for item in candidates if item.candidate_id == selected_id), None)
    if selected is None or selected.purpose != "context" or not selected.active:
        raise ValueError(f"{label}.selected_context_candidate_id must select an active context")
    return RollingFamilyConfig(
        family_id=_non_empty_string(values["family_id"], f"{label}.family_id"),
        source_selector=_non_empty_string(
            values["source_selector"],
            f"{label}.source_selector",
        ),
        input_selector=_non_empty_string(values["input_selector"], f"{label}.input_selector"),
        input_interval_seconds=input_interval,
        aggregation_policy=aggregation_policy,
        selected_context_candidate_id=selected_id,
        candidates=candidates,
    )


def _load_rolling_candidate(
    raw: Any,
    label: str,
    input_interval_seconds: int,
) -> RollingCandidateConfig:
    values = _mapping(raw, label)
    _require_keys(
        values,
        {
            "candidate_id",
            "purpose",
            "duration_seconds",
            "minimum_duration_seconds",
            "maximum_duration_seconds",
            "duration_step_seconds",
            "dynamic",
            "active",
        },
        label,
    )
    purpose = _non_empty_string(values["purpose"], f"{label}.purpose")
    if purpose not in {"context", "expansion"}:
        raise ValueError(f"{label}.purpose must be context or expansion")
    duration = _positive_int(values["duration_seconds"], f"{label}.duration_seconds")
    minimum = _positive_int(
        values["minimum_duration_seconds"],
        f"{label}.minimum_duration_seconds",
    )
    maximum = _positive_int(
        values["maximum_duration_seconds"],
        f"{label}.maximum_duration_seconds",
    )
    step = _positive_int(values["duration_step_seconds"], f"{label}.duration_step_seconds")
    _validate_integer_envelope(duration, minimum, maximum, step, f"{label}.duration_seconds")
    if duration % input_interval_seconds:
        raise ValueError(f"{label}.duration_seconds must contain whole input intervals")
    return RollingCandidateConfig(
        candidate_id=_non_empty_string(values["candidate_id"], f"{label}.candidate_id"),
        purpose=purpose,
        duration_seconds=duration,
        minimum_duration_seconds=minimum,
        maximum_duration_seconds=maximum,
        duration_step_seconds=step,
        dynamic=_bool(values["dynamic"], f"{label}.dynamic"),
        active=_bool(values["active"], f"{label}.active"),
    )


def _validate_integer_envelope(
    value: int,
    minimum: int,
    maximum: int,
    step: int,
    label: str,
) -> None:
    if not minimum <= value <= maximum:
        raise ValueError(f"{label} is outside its configured envelope")
    if (value - minimum) % step:
        raise ValueError(f"{label} does not align to its step")


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


def _load_historical(raw: Any, watchlist: WatchlistConfig) -> HistoricalConfig:
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
            "probe",
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
    probe_values = _mapping(values["probe"], "historical.probe")
    _require_keys(
        probe_values,
        {
            "enabled",
            "actor_ids",
            "instrument_id",
            "selector",
            "window",
            "minimum_observations",
            "maximum_observations",
            "priority",
        },
        "historical.probe",
    )
    minimum = _positive_int(
        probe_values["minimum_observations"],
        "historical.probe.minimum_observations",
    )
    maximum = _positive_int(
        probe_values["maximum_observations"],
        "historical.probe.maximum_observations",
    )
    if maximum < minimum:
        raise ValueError(
            "historical.probe.maximum_observations must not be below minimum_observations",
        )
    if maximum > maximum_per_request:
        raise ValueError(
            "historical.probe.maximum_observations exceeds the per-request policy",
        )
    priority = _non_negative_int(probe_values["priority"], "historical.probe.priority")
    if priority > 100:
        raise ValueError("historical.probe.priority must be from 0 through 100")
    instrument_id = _non_empty_string(
        probe_values["instrument_id"],
        "historical.probe.instrument_id",
    )
    if instrument_id not in {member.instrument_id for member in watchlist.members}:
        raise ValueError("historical.probe.instrument_id must be in the configured watchlist")
    window = _non_empty_string(probe_values["window"], "historical.probe.window")
    actor_ids = _unique_non_empty_strings(
        probe_values["actor_ids"],
        "historical.probe.actor_ids",
    )
    if not actor_ids:
        raise ValueError("historical.probe.actor_ids must be non-empty")
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
        probe=HistoricalProbeConfig(
            enabled=_bool(probe_values["enabled"], "historical.probe.enabled"),
            actor_ids=actor_ids,
            instrument_id=instrument_id,
            selector=_non_empty_string(probe_values["selector"], "historical.probe.selector"),
            window=window,
            minimum_observations=minimum,
            maximum_observations=maximum,
            priority=priority,
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


def _coverage_ratio(value: Any, label: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{label} must be a number")
    result = float(value)
    if not 0 <= result <= 1:
        raise ValueError(f"{label} must be between 0 and 1")
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


def _enum_strings(value: Any, label: str, allowed: set[str]) -> tuple[str, ...]:
    items = _unique_non_empty_strings(value, label)
    unsupported = sorted(set(items) - allowed)
    if unsupported:
        raise ValueError(f"{label} contains unsupported values: {', '.join(unsupported)}")
    return items


def _entity_scalar(value: Any, label: str) -> EntityConfigScalar:
    if not isinstance(value, str | int | float | bool):
        raise ValueError(f"{label} must be a string, number, or boolean")
    if isinstance(value, float) and (value != value or value in {float("inf"), float("-inf")}):
        raise ValueError(f"{label} must be finite")
    if isinstance(value, str) and not value.strip():
        raise ValueError(f"{label} must not be empty")
    return value


def _finite_number(value: Any, label: str) -> int | float:
    normalized = _entity_scalar(value, label)
    if not isinstance(normalized, int | float) or isinstance(normalized, bool):
        raise ValueError(f"{label} must be a finite number")
    return normalized


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


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value
