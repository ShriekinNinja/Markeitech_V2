from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from nautilus_trader.common import ImportableActorConfig

from markeitech.system.config import SystemConfig
from markeitech.system.discord import SYSTEM_HEALTH_WEBHOOK_ENV


def _watchlist_feeds(config: SystemConfig) -> list[dict[str, str]]:
    feeds: list[dict[str, str]] = []
    for member in config.watchlist.members:
        capabilities = set(member.capabilities)
        if "top_of_book" in capabilities:
            feeds.append(
                {
                    "instrument_id": member.instrument_id,
                    "calendar_id": member.calendar_id,
                    "kind": "quotes",
                    "selector": "default",
                },
            )
        if "watchlist_last" in capabilities:
            feeds.append(
                {
                    "instrument_id": member.instrument_id,
                    "calendar_id": member.calendar_id,
                    "kind": "bars",
                    "selector": "5-SECOND-LAST-EXTERNAL",
                },
            )
    return feeds


def _watchlist_instruments_with_capability(
    config: SystemConfig,
    capability: str,
) -> list[str]:
    return [
        member.instrument_id
        for member in config.watchlist.members
        if capability in member.capabilities
    ]


@dataclass(frozen=True, slots=True)
class StartupPrerequisites:
    run_id: UUID
    operational_persistence_ready: bool
    evidence_recency_profiles: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class ActorRegistration:
    key: str
    actor_id: str
    config: ImportableActorConfig


def build_actor_plan(
    config: SystemConfig,
    prerequisites: StartupPrerequisites,
) -> tuple[ActorRegistration, ...]:
    if not prerequisites.operational_persistence_ready:
        raise ValueError("operational persistence must pass preflight before actor composition")

    instrument_ids = list(config.instrument_ids)
    registrations = [
        ActorRegistration(
            key="system_control",
            actor_id="SYSTEM-CONTROL",
            config=ImportableActorConfig(
                actor_path="markeitech.system.actor:SystemControlActor",
                config_path="markeitech.system.actor:SystemControlActorConfig",
                config={
                    "actor_id": "SYSTEM-CONTROL",
                    "instrument_ids": instrument_ids,
                    "operational_persistence_ready": True,
                },
            ),
        ),
        ActorRegistration(
            key="session_state",
            actor_id="SESSION-STATE",
            config=ImportableActorConfig(
                actor_path="markeitech.intelligence.actors:SessionStateActor",
                config_path="markeitech.intelligence.actors:SessionStateActorConfig",
                config={
                    "actor_id": "SESSION-STATE",
                    "evaluation_interval_ms": config.sessions.evaluation_interval_ms,
                    "calendars": [
                        {
                            "calendar_id": calendar.calendar_id,
                            "provider_calendar": calendar.provider_calendar,
                            "timezone": calendar.timezone,
                            "schedule_version": calendar.schedule_version,
                            "phases": [
                                {
                                    "name": phase.name,
                                    "start": phase.start,
                                    "end": phase.end,
                                    "start_day_offset": phase.start_day_offset,
                                }
                                for phase in calendar.phases
                            ],
                            "overrides": [
                                {
                                    "trade_date": override.trade_date,
                                    "phase": override.phase,
                                    "start": override.start,
                                    "end": override.end,
                                    "start_day_offset": override.start_day_offset,
                                }
                                for override in calendar.overrides
                            ],
                        }
                        for calendar in config.sessions.calendars
                    ],
                },
            ),
        ),
        ActorRegistration(
            key="evidence_health",
            actor_id="EVIDENCE-HEALTH",
            config=ImportableActorConfig(
                actor_path="markeitech.intelligence.actors:EvidenceHealthActor",
                config_path="markeitech.intelligence.actors:EvidenceHealthActorConfig",
                config={
                    "actor_id": "EVIDENCE-HEALTH",
                    "feeds": _watchlist_feeds(config),
                    "evaluation_interval_ms": config.evidence_health.evaluation_interval_ms,
                    "consumer_retry_interval_ms": (
                        config.evidence_health.consumer_retry_interval_ms
                    ),
                    "provider_id": config.evidence_health.provider_id,
                    "profile_checkpoint_samples": (
                        config.evidence_health.profile_checkpoint_samples
                    ),
                    "recency_profiles": list(prerequisites.evidence_recency_profiles),
                    "policies": [
                        {
                            "feed_kind": policy.feed_kind,
                            "selector": policy.selector,
                            "fresh_for_ms": policy.fresh_for_ms,
                            "stale_after_ms": policy.stale_after_ms,
                            "unavailable_after_ms": policy.unavailable_after_ms,
                            "adaptive": policy.adaptive,
                            "minimum_samples": policy.minimum_samples,
                            "decay_factor": policy.decay_factor,
                            "fresh_stddev_multiplier": policy.fresh_stddev_multiplier,
                            "stale_stddev_multiplier": policy.stale_stddev_multiplier,
                            "unavailable_stddev_multiplier": (policy.unavailable_stddev_multiplier),
                            "min_fresh_ms": policy.min_fresh_ms,
                            "max_fresh_ms": policy.max_fresh_ms,
                            "min_stale_ms": policy.min_stale_ms,
                            "max_stale_ms": policy.max_stale_ms,
                            "min_unavailable_ms": policy.min_unavailable_ms,
                            "max_unavailable_ms": policy.max_unavailable_ms,
                        }
                        for policy in config.evidence_health.policies
                    ],
                },
            ),
        ),
    ]
    if config.metrics.quote_quality.enabled:
        quote_metrics = config.metrics.quote_quality
        registrations.append(
            ActorRegistration(
                key="quote_quality_metrics",
                actor_id="QUOTE-QUALITY-METRICS",
                config=ImportableActorConfig(
                    actor_path=(
                        "markeitech.intelligence.quote_metric_actor:QuoteQualityMetricsActor"
                    ),
                    config_path=(
                        "markeitech.intelligence.quote_metric_actor:QuoteQualityMetricsActorConfig"
                    ),
                    config={
                        "actor_id": "QUOTE-QUALITY-METRICS",
                        "instrument_ids": _watchlist_instruments_with_capability(
                            config,
                            quote_metrics.required_watchlist_capability,
                        ),
                        "parameter_version": quote_metrics.parameter_version,
                        "minimum_update_interval_ms": (quote_metrics.minimum_update_interval_ms),
                        "maximum_output_age_ms": quote_metrics.maximum_output_age_ms,
                        "demand_retry_interval_ms": quote_metrics.demand_retry_interval_ms,
                        "evidence_snapshot_retry_interval_ms": (
                            quote_metrics.evidence_snapshot_retry_interval_ms
                        ),
                        "priority": quote_metrics.priority,
                    },
                ),
            ),
        )
    if config.metrics.session_measurements.enabled:
        session_metrics = config.metrics.session_measurements
        selected_instruments = _watchlist_instruments_with_capability(
            config,
            session_metrics.required_watchlist_capability,
        )
        profile_by_instrument = {
            instrument_id: binding.profile_id
            for binding in session_metrics.profile_bindings
            for instrument_id in binding.instrument_ids
        }
        completed = session_metrics.completed_bars
        registrations.append(
            ActorRegistration(
                key="session_metrics",
                actor_id="SESSION-METRICS",
                config=ImportableActorConfig(
                    actor_path=("markeitech.intelligence.session_metric_actor:SessionMetricsActor"),
                    config_path=(
                        "markeitech.intelligence.session_metric_actor:SessionMetricsActorConfig"
                    ),
                    config={
                        "actor_id": "SESSION-METRICS",
                        "instrument_ids": selected_instruments,
                        "instrument_calendars": {
                            member.instrument_id: member.calendar_id
                            for member in config.watchlist.members
                            if member.instrument_id in selected_instruments
                        },
                        "calendars": [
                            {
                                "calendar_id": calendar.calendar_id,
                                "provider_calendar": calendar.provider_calendar,
                                "timezone": calendar.timezone,
                                "schedule_version": calendar.schedule_version,
                                "phases": [
                                    {
                                        "name": phase.name,
                                        "start": phase.start,
                                        "end": phase.end,
                                        "start_day_offset": phase.start_day_offset,
                                    }
                                    for phase in calendar.phases
                                ],
                                "overrides": [
                                    {
                                        "trade_date": override.trade_date,
                                        "phase": override.phase,
                                        "start": override.start,
                                        "end": override.end,
                                        "start_day_offset": override.start_day_offset,
                                    }
                                    for override in calendar.overrides
                                ],
                            }
                            for calendar in config.sessions.calendars
                        ],
                        "profiles": [
                            {
                                "profile_id": profile.profile_id,
                                "version": profile.version,
                                "calendar_id": profile.calendar_id,
                                "primary_phase": profile.primary_phase,
                                "overnight_enabled": profile.overnight_enabled,
                                "overnight_phase": profile.overnight_phase,
                                "volume_supported": profile.volume_supported,
                                "windows": [
                                    {
                                        "window_id": window.window_id,
                                        "purpose": window.purpose,
                                        "anchor_phase": window.anchor_phase,
                                        "anchor_boundary": window.anchor_boundary,
                                        "offset_seconds": window.offset_seconds,
                                        "duration_seconds": window.duration_seconds,
                                        "minimum_duration_seconds": (
                                            window.minimum_duration_seconds
                                        ),
                                        "maximum_duration_seconds": (
                                            window.maximum_duration_seconds
                                        ),
                                        "duration_step_seconds": window.duration_step_seconds,
                                        "dynamic": window.dynamic,
                                        "historical_selector": window.historical_selector,
                                        "minimum_historical_observations": (
                                            window.minimum_historical_observations
                                        ),
                                        "maximum_historical_observations": (
                                            window.maximum_historical_observations
                                        ),
                                    }
                                    for window in profile.windows
                                ],
                            }
                            for profile in session_metrics.profiles
                        ],
                        "profile_bindings": {
                            instrument_id: profile_by_instrument[instrument_id]
                            for instrument_id in selected_instruments
                        },
                        "parameter_version": session_metrics.parameter_version,
                        "parameter_source": session_metrics.parameter_source,
                        "parameter_effective_from_ns": (
                            session_metrics.parameter_effective_from_ns
                        ),
                        "conflict_policy": session_metrics.conflict_policy,
                        "demand_retry_interval_ms": session_metrics.demand_retry_interval_ms,
                        "evidence_snapshot_retry_interval_ms": (
                            session_metrics.evidence_snapshot_retry_interval_ms
                        ),
                        "priority": session_metrics.priority,
                        "completed_bars": {
                            "live_selector": completed.live_selector,
                            "historical_selector": completed.historical_selector,
                            "historical_window": completed.historical_window,
                            "minimum_historical_observations": (
                                completed.minimum_historical_observations
                            ),
                            "maximum_historical_observations": (
                                completed.maximum_historical_observations
                            ),
                            "calculation_interval_seconds": (
                                completed.calculation_interval_seconds
                            ),
                            "minimum_interval_seconds": completed.minimum_interval_seconds,
                            "maximum_interval_seconds": completed.maximum_interval_seconds,
                            "interval_step_seconds": completed.interval_step_seconds,
                            "interval_dynamic": completed.interval_dynamic,
                            "aggregation_boundary_policy": (completed.aggregation_boundary_policy),
                            "timestamp_policy": completed.timestamp_policy,
                            "revision_policy": completed.revision_policy,
                            "maximum_retained_observations": (
                                completed.maximum_retained_observations
                            ),
                            "maximum_output_age_ms": completed.maximum_output_age_ms,
                        },
                        "session_references": {
                            "enabled": session_metrics.session_references.enabled,
                            "historical_selector": (
                                session_metrics.session_references.historical_selector
                            ),
                            "active_window": session_metrics.session_references.active_window,
                            "previous_window": session_metrics.session_references.previous_window,
                            "overnight_window": (
                                session_metrics.session_references.overnight_window
                            ),
                            "minimum_historical_observations": (
                                session_metrics.session_references.minimum_historical_observations
                            ),
                            "maximum_historical_observations": (
                                session_metrics.session_references.maximum_historical_observations
                            ),
                            "vwap_price_basis": (
                                session_metrics.session_references.vwap_price_basis
                            ),
                            "vwap_price_basis_dynamic": (
                                session_metrics.session_references.vwap_price_basis_dynamic
                            ),
                            "minimum_coverage_ratio": (
                                session_metrics.session_references.minimum_coverage_ratio
                            ),
                            "minimum_coverage_ratio_floor": (
                                session_metrics.session_references.minimum_coverage_ratio_floor
                            ),
                            "minimum_coverage_ratio_ceiling": (
                                session_metrics.session_references.minimum_coverage_ratio_ceiling
                            ),
                            "minimum_coverage_ratio_step": (
                                session_metrics.session_references.minimum_coverage_ratio_step
                            ),
                            "minimum_coverage_ratio_dynamic": (
                                session_metrics.session_references.minimum_coverage_ratio_dynamic
                            ),
                            "maximum_retained_sessions": (
                                session_metrics.session_references.maximum_retained_sessions
                            ),
                            "maximum_output_age_ms": (
                                session_metrics.session_references.maximum_output_age_ms
                            ),
                        },
                        "session_windows": {
                            "enabled": session_metrics.session_windows.enabled,
                            "price_basis": session_metrics.session_windows.price_basis,
                            "price_basis_dynamic": (
                                session_metrics.session_windows.price_basis_dynamic
                            ),
                            "minimum_coverage_ratio": (
                                session_metrics.session_windows.minimum_coverage_ratio
                            ),
                            "minimum_coverage_ratio_floor": (
                                session_metrics.session_windows.minimum_coverage_ratio_floor
                            ),
                            "minimum_coverage_ratio_ceiling": (
                                session_metrics.session_windows.minimum_coverage_ratio_ceiling
                            ),
                            "minimum_coverage_ratio_step": (
                                session_metrics.session_windows.minimum_coverage_ratio_step
                            ),
                            "minimum_coverage_ratio_dynamic": (
                                session_metrics.session_windows.minimum_coverage_ratio_dynamic
                            ),
                            "maximum_retained_sessions": (
                                session_metrics.session_windows.maximum_retained_sessions
                            ),
                            "maximum_output_age_ms": (
                                session_metrics.session_windows.maximum_output_age_ms
                            ),
                        },
                    },
                ),
            ),
        )
    registrations.extend(
        [
            ActorRegistration(
                key="watchlist",
                actor_id="WATCHLIST",
                config=ImportableActorConfig(
                    actor_path="markeitech.system.watchlist:WatchlistActor",
                    config_path="markeitech.system.watchlist:WatchlistActorConfig",
                    config={
                        "actor_id": "WATCHLIST",
                        "consumer_retry_interval_ms": config.watchlist.consumer_retry_interval_ms,
                        "members": [
                            {
                                "instrument_id": member.instrument_id,
                                "calendar_id": member.calendar_id,
                                "owner_ids": list(member.owner_ids),
                                "capabilities": list(member.capabilities),
                            }
                            for member in config.watchlist.members
                        ],
                    },
                ),
            ),
            ActorRegistration(
                key="data_acquisition",
                actor_id="DATA-ACQUISITION",
                config=ImportableActorConfig(
                    actor_path="markeitech.system.acquisition:DataAcquisitionActor",
                    config_path="markeitech.system.acquisition:DataAcquisitionActorConfig",
                    config={
                        "actor_id": "DATA-ACQUISITION",
                        "instrument_ids": instrument_ids,
                        "instrument_calendars": {
                            member.instrument_id: member.calendar_id
                            for member in config.watchlist.members
                        },
                        "calendars": [
                            {
                                "calendar_id": calendar.calendar_id,
                                "provider_calendar": calendar.provider_calendar,
                                "timezone": calendar.timezone,
                                "schedule_version": calendar.schedule_version,
                                "phases": [
                                    {
                                        "name": phase.name,
                                        "start": phase.start,
                                        "end": phase.end,
                                        "start_day_offset": phase.start_day_offset,
                                    }
                                    for phase in calendar.phases
                                ],
                                "overrides": [
                                    {
                                        "trade_date": override.trade_date,
                                        "phase": override.phase,
                                        "start": override.start,
                                        "end": override.end,
                                        "start_day_offset": override.start_day_offset,
                                    }
                                    for override in calendar.overrides
                                ],
                            }
                            for calendar in config.sessions.calendars
                        ],
                        "historical": {
                            "maximum_plan_requests": config.historical.maximum_plan_requests,
                            "maximum_observations_per_request": (
                                config.historical.maximum_observations_per_request
                            ),
                            "maximum_total_observations": (
                                config.historical.maximum_total_observations
                            ),
                            "maximum_outstanding_requests": (
                                config.historical.maximum_outstanding_requests
                            ),
                            "maximum_in_flight_requests": (
                                config.historical.maximum_in_flight_requests
                            ),
                            "timeout_seconds": config.historical.timeout_seconds,
                            "maximum_attempts": config.historical.maximum_attempts,
                            "retry_backoff_ms": config.historical.retry_backoff_ms,
                            "poll_interval_ms": config.historical.poll_interval_ms,
                        },
                    },
                ),
            ),
        ],
    )
    if config.historical.probe.enabled:
        probe = config.historical.probe
        registrations.extend(
            ActorRegistration(
                key=f"historical_dependency_probe:{index}",
                actor_id=actor_id,
                config=ImportableActorConfig(
                    actor_path=(
                        "markeitech.system.historical_probe:HistoricalDependencyProbeActor"
                    ),
                    config_path=(
                        "markeitech.system.historical_probe:HistoricalDependencyProbeActorConfig"
                    ),
                    config={
                        "actor_id": actor_id,
                        "instrument_id": probe.instrument_id,
                        "selector": probe.selector,
                        "window": probe.window,
                        "minimum_observations": probe.minimum_observations,
                        "maximum_observations": probe.maximum_observations,
                        "priority": probe.priority,
                    },
                ),
            )
            for index, actor_id in enumerate(probe.actor_ids, start=1)
        )
    if config.acquisition.native_consumer_probe_enabled:
        registrations.append(
            ActorRegistration(
                key="native_consumer_probe",
                actor_id="NATIVE-CONSUMER-PROBE",
                config=ImportableActorConfig(
                    actor_path=("markeitech.system.native_consumer_probe:NativeConsumerProbeActor"),
                    config_path=(
                        "markeitech.system.native_consumer_probe:NativeConsumerProbeActorConfig"
                    ),
                    config={
                        "actor_id": "NATIVE-CONSUMER-PROBE",
                        "feeds": _watchlist_feeds(config),
                        "unsubscribe_after_seconds": (
                            config.acquisition.native_consumer_probe_unsubscribe_after_seconds
                        ),
                    },
                ),
            ),
        )
    if config.discord.enabled:
        registrations.append(
            ActorRegistration(
                key="discord_health",
                actor_id="DISCORD-HEALTH",
                config=ImportableActorConfig(
                    actor_path="markeitech.system.discord:DiscordHealthActor",
                    config_path="markeitech.system.discord:DiscordHealthActorConfig",
                    config={
                        "actor_id": "DISCORD-HEALTH",
                        "request_timeout_seconds": config.discord.request_timeout_seconds,
                        "webhook_env": SYSTEM_HEALTH_WEBHOOK_ENV,
                    },
                ),
            ),
        )
    registrations.append(
        ActorRegistration(
            key="operational_persistence",
            actor_id="OPERATIONAL-PERSISTENCE",
            config=ImportableActorConfig(
                actor_path="markeitech.system.persistence:OperationalPersistenceActor",
                config_path=("markeitech.system.persistence:OperationalPersistenceActorConfig"),
                config={
                    "actor_id": "OPERATIONAL-PERSISTENCE",
                    "run_id": str(prerequisites.run_id),
                    "dsn_env": config.persistence.dsn_env,
                    "connect_timeout_seconds": config.persistence.connect_timeout_seconds,
                    "queue_capacity": config.persistence.queue_capacity,
                    "critical_queue_reserve": config.persistence.critical_queue_reserve,
                    "write_batch_size": config.persistence.write_batch_size,
                    "result_poll_interval_ms": config.persistence.result_poll_interval_ms,
                    "shutdown_timeout_seconds": config.persistence.shutdown_timeout_seconds,
                    "write_max_attempts": config.persistence.write_max_attempts,
                    "write_retry_backoff_ms": config.persistence.write_retry_backoff_ms,
                },
            ),
        ),
    )
    _reject_duplicate_actor_ids(registrations)
    return tuple(registrations)


def validate_runtime_environment(
    config: SystemConfig,
    environment: Mapping[str, str],
) -> None:
    required = [config.persistence.dsn_env]
    if config.discord.enabled:
        required.append(SYSTEM_HEALTH_WEBHOOK_ENV)
    missing = [name for name in required if not environment.get(name, "").strip()]
    if missing:
        raise RuntimeError(f"required runtime environment is missing: {', '.join(sorted(missing))}")


def _reject_duplicate_actor_ids(registrations: list[ActorRegistration]) -> None:
    actor_ids = [registration.actor_id for registration in registrations]
    duplicates = sorted({actor_id for actor_id in actor_ids if actor_ids.count(actor_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate actor ids: {', '.join(duplicates)}")
