from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from nautilus_trader.common import ImportableActorConfig

from markeitech.intelligence.rolling_measurements import (
    ROLLING_METRIC_SUFFIXES,
    rolling_metric_id,
)
from markeitech.intelligence.session_references import SESSION_REFERENCE_METRIC_IDS
from markeitech.intelligence.session_windows import OPENING_RANGE_FIELDS
from markeitech.system.config import SystemConfig
from markeitech.system.discord import (
    OPERATIONAL_EVENTS_WEBHOOK_ENV,
    SYSTEM_HEALTH_WEBHOOK_ENV,
)


def _canonical_calendar_payload(calendar) -> dict[str, object]:  # noqa: ANN001
    return {
        "calendar_id": calendar.calendar_id,
        "schedule_version": calendar.schedule_version,
        "calendar_engine": calendar.calendar_engine,
        "calendar_engine_version": calendar.calendar_engine_version,
        "provider_calendar": calendar.provider_calendar,
        "provider_calendar_class": calendar.provider_calendar_class,
        "exchange_timezone": calendar.exchange_timezone,
        "schedule_columns": list(calendar.schedule_columns),
        "definition_version": calendar.definition_version,
        "effective_from_ns": calendar.effective_from_ns,
        "definition_digest": calendar.definition_digest,
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
            for phase in calendar.phases
        ],
        "corrections": [
            {
                "correction_id": correction.correction_id,
                "kind": correction.kind,
                "source_id": correction.source_id,
                "product_roots": list(correction.product_roots),
                "effective_from_trade_date": correction.effective_from_trade_date,
                "timezone": correction.timezone,
                "expected_start": correction.expected_start,
                "expected_end": correction.expected_end,
            }
            for correction in calendar.corrections
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
            for source in calendar.sources
        ],
    }


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


def _entity_definition_payload(definition) -> dict[str, object]:  # noqa: ANN001
    return {
        "definition_id": definition.definition_id,
        "group": definition.group,
        "entity_type": definition.entity_type,
        "entity_version": definition.entity_version,
        "decision_question": definition.decision_question,
        "implementation_id": definition.implementation_id,
        "formula_version": definition.formula_version,
        "identity_dimensions": list(definition.identity_dimensions),
        "durability": definition.durability,
        "completion_rule": definition.completion_rule,
        "invalidation_rule": definition.invalidation_rule,
        "expiry_rule": definition.expiry_rule,
        "permitted_health": list(definition.permitted_health),
        "permitted_fidelities": list(definition.permitted_fidelities),
        "applications": [
            {
                "application_id": application.application_id,
                "parameter_set_id": application.parameter_set_id,
                "analytical_profile_ids": list(application.analytical_profile_ids),
                "instrument_ids": list(application.instrument_ids),
                "instrument_classes": list(application.instrument_classes),
                "session_phases": list(application.session_phases),
                "horizon": application.horizon,
                "source_selector": application.source_selector,
                "requires_volume": application.requires_volume,
            }
            for application in definition.applications
        ],
        "metric_inputs": [
            {
                "role": dependency.role,
                "metric_id": dependency.metric_id,
                "metric_version": dependency.metric_version,
                "parameter_version": dependency.parameter_version,
                "required": dependency.required,
                "permitted_health": list(dependency.permitted_health),
                "permitted_fidelities": list(dependency.permitted_fidelities),
            }
            for dependency in definition.metric_inputs
        ],
        "entity_inputs": [
            {
                "role": dependency.role,
                "entity_type": dependency.entity_type,
                "entity_version": dependency.entity_version,
                "required": dependency.required,
                "permitted_health": list(dependency.permitted_health),
                "permitted_fidelities": list(dependency.permitted_fidelities),
            }
            for dependency in definition.entity_inputs
        ],
        "parameters": [
            {
                "parameter_id": parameter.parameter_id,
                "meaning": parameter.meaning,
                "value_kind": parameter.value_kind,
                "unit": parameter.unit,
                "default": parameter.default,
                "dynamic": parameter.dynamic,
                "mutability": parameter.mutability,
                "source": parameter.source,
                "minimum": parameter.minimum,
                "maximum": parameter.maximum,
                "step": parameter.step,
                "allowed_values": list(parameter.allowed_values),
            }
            for parameter in definition.parameters
        ],
        "parameter_sets": [
            {
                "parameter_set_id": parameter_set.parameter_set_id,
                "parameter_version": parameter_set.parameter_version,
                "effective_from_ns": parameter_set.effective_from_ns,
                "source": parameter_set.source,
                "values": dict(parameter_set.values),
            }
            for parameter_set in definition.parameter_sets
        ],
        "market_state": (
            None
            if definition.market_state is None
            else {
                "parameter_set_id": definition.market_state.parameter_set_id,
                **(
                    {}
                    if definition.market_state.normalization is None
                    else {"normalization": definition.market_state.normalization}
                ),
                **(
                    {}
                    if definition.market_state.reference_id is None
                    else {"reference_id": definition.market_state.reference_id}
                ),
                **(
                    {}
                    if definition.market_state.reference_kind is None
                    else {"reference_kind": definition.market_state.reference_kind}
                ),
                "policies": [
                    {
                        "axis": policy.axis,
                        "policy_id": policy.policy_id,
                        "policy_version": policy.policy_version,
                        "measure_role": policy.measure_role,
                        "coverage_role": policy.coverage_role,
                        "unavailable_category": policy.unavailable_category,
                        "bands": [
                            {
                                "category": band.category,
                                **(
                                    {}
                                    if band.lower_bound_parameter_id is None
                                    else {
                                        "lower_bound_parameter_id": (band.lower_bound_parameter_id),
                                    }
                                ),
                                **(
                                    {}
                                    if band.upper_bound_parameter_id is None
                                    else {
                                        "upper_bound_parameter_id": (band.upper_bound_parameter_id),
                                    }
                                ),
                            }
                            for band in policy.bands
                        ],
                        "hysteresis_parameter_id": policy.hysteresis_parameter_id,
                        "confirmation_observations_parameter_id": (
                            policy.confirmation_observations_parameter_id
                        ),
                        "minimum_coverage_ratio_parameter_id": (
                            policy.minimum_coverage_ratio_parameter_id
                        ),
                        "maximum_evidence_age_ms_parameter_id": (
                            policy.maximum_evidence_age_ms_parameter_id
                        ),
                        "permitted_health": list(policy.permitted_health),
                        "permitted_fidelities": list(policy.permitted_fidelities),
                    }
                    for policy in definition.market_state.policies
                ],
            }
        ),
    }


def _available_session_entity_metric_keys(config: SystemConfig) -> set[tuple[str, int]]:
    session_metrics = config.metrics.session_measurements
    keys = (
        {(metric_id, 1) for metric_id in SESSION_REFERENCE_METRIC_IDS}
        if session_metrics.session_references.enabled
        else set()
    )
    if session_metrics.session_windows.enabled:
        for profile in session_metrics.profiles:
            for window in profile.windows:
                if window.purpose != "opening_range":
                    continue
                prefix = f"opening_range.{profile.profile_id}.{window.window_id}"
                keys.update((f"{prefix}.{field}", 1) for field in OPENING_RANGE_FIELDS)
    return keys


def _available_market_state_metric_keys(config: SystemConfig) -> set[tuple[str, int]]:
    rolling = config.metrics.session_measurements.rolling_measurements
    if not rolling.enabled:
        return set()
    return {
        (rolling_metric_id(family.family_id, candidate.candidate_id, suffix), 1)
        for family in rolling.families
        for candidate in family.candidates
        if candidate.active
        for suffix in ROLLING_METRIC_SUFFIXES
    }


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
    projection_retry = {
        "response_timeout_ms": config.sessions.projection_retry.response_timeout_ms,
        "maximum_attempts": config.sessions.projection_retry.maximum_attempts,
        "retry_backoff_ms": config.sessions.projection_retry.retry_backoff_ms,
        "maximum_elapsed_ms": config.sessions.projection_retry.maximum_elapsed_ms,
    }
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
                    "source_epoch": str(prerequisites.run_id),
                    "maximum_projection_days": config.sessions.maximum_projection_days,
                    "maximum_calendars_per_request": (
                        config.sessions.maximum_calendars_per_request
                    ),
                    "calendars": [
                        _canonical_calendar_payload(calendar)
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
                    "projection_lookback_days": config.sessions.projection_lookback_days,
                    "projection_lookahead_days": config.sessions.projection_lookahead_days,
                    "expected_calendar_digests": {
                        calendar.calendar_id: calendar.definition_digest
                        for calendar in config.sessions.calendars
                    },
                    "calendar_source": "SESSION-STATE",
                    "calendar_source_epoch": str(prerequisites.run_id),
                    "projection_retry": projection_retry,
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
                        "queue_capacity": config.discord.queue_capacity,
                        "ping_critical_resource_alerts": (
                            config.discord.ping_critical_resource_alerts
                        ),
                        "webhook_env": SYSTEM_HEALTH_WEBHOOK_ENV,
                        "operational_events_webhook_env": OPERATIONAL_EVENTS_WEBHOOK_ENV,
                    },
                ),
            ),
        )
    if config.visual_debug_capture.enabled:
        capture = config.visual_debug_capture
        registrations.append(
            ActorRegistration(
                key="visual_debug_capture",
                actor_id="VISUAL-DEBUG-CAPTURE",
                config=ImportableActorConfig(
                    actor_path=(
                        "markeitech.intelligence.visual_debug_capture_actor:VisualDebugCaptureActor"
                    ),
                    config_path=(
                        "markeitech.intelligence.visual_debug_capture_actor:"
                        "VisualDebugCaptureActorConfig"
                    ),
                    config={
                        "actor_id": "VISUAL-DEBUG-CAPTURE",
                        "run_id": str(prerequisites.run_id),
                        "configuration_identity": capture.configuration_identity,
                        "instrument_id": capture.instrument_id,
                        "analytical_profile_id": capture.analytical_profile_id,
                        "analytical_profile_version": capture.analytical_profile_version,
                        "bar_specification": capture.bar_specification,
                        "parameter_version": capture.parameter_version,
                        "output_directory": str(capture.output_directory),
                        "capture_policy_version": capture.capture_policy_version,
                        "target_historical_bars": capture.target_historical_bars,
                        "target_live_bars": capture.target_live_bars,
                        "quiet_period_ms": capture.quiet_period_ms,
                        "completion_deadline_ms": capture.completion_deadline_ms,
                        "output_drain_timeout_ms": capture.output_drain_timeout_ms,
                        "candle_pane_height_px": capture.candle_pane_height_px,
                        "volume_pane_height_px": capture.volume_pane_height_px,
                        "metric_pane_height_px": capture.metric_pane_height_px,
                        "pane_gap_px": capture.pane_gap_px,
                    },
                ),
            ),
        )
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
                        "expected_calendar_digests": {
                            calendar.calendar_id: calendar.definition_digest
                            for calendar in config.sessions.calendars
                            if calendar.calendar_id
                            in {
                                member.calendar_id
                                for member in config.watchlist.members
                                if member.instrument_id in selected_instruments
                            }
                        },
                        "projection_lookback_days": config.sessions.projection_lookback_days,
                        "projection_lookahead_days": config.sessions.projection_lookahead_days,
                        "calendar_source": "SESSION-STATE",
                        "calendar_source_epoch": str(prerequisites.run_id),
                        "projection_retry": projection_retry,
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
                        "rolling_measurements": {
                            "enabled": session_metrics.rolling_measurements.enabled,
                            "minimum_coverage_ratio": (
                                session_metrics.rolling_measurements.minimum_coverage_ratio
                            ),
                            "minimum_coverage_ratio_floor": (
                                session_metrics.rolling_measurements.minimum_coverage_ratio_floor
                            ),
                            "minimum_coverage_ratio_ceiling": (
                                session_metrics.rolling_measurements.minimum_coverage_ratio_ceiling
                            ),
                            "minimum_coverage_ratio_step": (
                                session_metrics.rolling_measurements.minimum_coverage_ratio_step
                            ),
                            "minimum_coverage_ratio_dynamic": (
                                session_metrics.rolling_measurements.minimum_coverage_ratio_dynamic
                            ),
                            "maximum_retained_observations": (
                                session_metrics.rolling_measurements.maximum_retained_observations
                            ),
                            "maximum_output_age_ms": (
                                session_metrics.rolling_measurements.maximum_output_age_ms
                            ),
                            "baseline": {
                                "eligible_reference_health": list(
                                    session_metrics.rolling_measurements.baseline.eligible_reference_health
                                ),
                                "eligible_reference_fidelities": list(
                                    session_metrics.rolling_measurements.baseline.eligible_reference_fidelities
                                ),
                                "recent_reference_count": (
                                    session_metrics.rolling_measurements.baseline.recent_reference_count
                                ),
                                "recent_reference_count_minimum": (
                                    session_metrics.rolling_measurements.baseline.recent_reference_count_minimum
                                ),
                                "recent_reference_count_maximum": (
                                    session_metrics.rolling_measurements.baseline.recent_reference_count_maximum
                                ),
                                "recent_reference_count_step": (
                                    session_metrics.rolling_measurements.baseline.recent_reference_count_step
                                ),
                                "recent_reference_count_dynamic": (
                                    session_metrics.rolling_measurements.baseline.recent_reference_count_dynamic
                                ),
                                "minimum_recent_references": (
                                    session_metrics.rolling_measurements.baseline.minimum_recent_references
                                ),
                                "phase_reference_count": (
                                    session_metrics.rolling_measurements.baseline.phase_reference_count
                                ),
                                "phase_reference_count_minimum": (
                                    session_metrics.rolling_measurements.baseline.phase_reference_count_minimum
                                ),
                                "phase_reference_count_maximum": (
                                    session_metrics.rolling_measurements.baseline.phase_reference_count_maximum
                                ),
                                "phase_reference_count_step": (
                                    session_metrics.rolling_measurements.baseline.phase_reference_count_step
                                ),
                                "phase_reference_count_dynamic": (
                                    session_metrics.rolling_measurements.baseline.phase_reference_count_dynamic
                                ),
                                "minimum_phase_references": (
                                    session_metrics.rolling_measurements.baseline.minimum_phase_references
                                ),
                            },
                            "families": [
                                {
                                    "family_id": family.family_id,
                                    "source_selector": family.source_selector,
                                    "input_selector": family.input_selector,
                                    "input_interval_seconds": family.input_interval_seconds,
                                    "aggregation_policy": family.aggregation_policy,
                                    "selected_context_candidate_id": (
                                        family.selected_context_candidate_id
                                    ),
                                    "candidates": [
                                        {
                                            "candidate_id": candidate.candidate_id,
                                            "purpose": candidate.purpose,
                                            "duration_seconds": candidate.duration_seconds,
                                            "minimum_duration_seconds": (
                                                candidate.minimum_duration_seconds
                                            ),
                                            "maximum_duration_seconds": (
                                                candidate.maximum_duration_seconds
                                            ),
                                            "duration_step_seconds": (
                                                candidate.duration_step_seconds
                                            ),
                                            "dynamic": candidate.dynamic,
                                            "active": candidate.active,
                                        }
                                        for candidate in family.candidates
                                    ],
                                }
                                for family in session_metrics.rolling_measurements.families
                            ],
                        },
                    },
                ),
            ),
        )
    if config.metrics.entity_analysis.enabled:
        entity_analysis = config.metrics.entity_analysis
        session_metrics = config.metrics.session_measurements
        profile_by_id = {profile.profile_id: profile for profile in session_metrics.profiles}
        profile_by_instrument = {
            instrument_id: binding.profile_id
            for binding in session_metrics.profile_bindings
            for instrument_id in binding.instrument_ids
        }
        selected_instruments = _watchlist_instruments_with_capability(
            config,
            entity_analysis.required_watchlist_capability,
        )
        group_one = [
            definition
            for definition in entity_analysis.definitions
            if definition.enabled and definition.group == "objective_session_reference_level"
        ]
        available_metric_keys = _available_session_entity_metric_keys(config)
        missing_metric_keys = sorted(
            {
                (dependency.metric_id, dependency.metric_version)
                for definition in group_one
                for dependency in definition.metric_inputs
            }
            - available_metric_keys,
        )
        if missing_metric_keys:
            raise ValueError(
                "session-reference entity definitions require unavailable metrics: "
                f"{missing_metric_keys!r}",
            )
        registrations.append(
            ActorRegistration(
                key="session_reference_entities",
                actor_id="SESSION-REFERENCE-ENTITIES",
                config=ImportableActorConfig(
                    actor_path=(
                        "markeitech.intelligence.session_entity_actor:SessionReferenceEntityActor"
                    ),
                    config_path=(
                        "markeitech.intelligence.session_entity_actor:"
                        "SessionReferenceEntityActorConfig"
                    ),
                    config={
                        "actor_id": "SESSION-REFERENCE-ENTITIES",
                        "instrument_profiles": {
                            instrument_id: {
                                "profile_id": profile_by_instrument[instrument_id],
                                "profile_version": profile_by_id[
                                    profile_by_instrument[instrument_id]
                                ].version,
                            }
                            for instrument_id in selected_instruments
                        },
                        "definitions": [
                            _entity_definition_payload(definition) for definition in group_one
                        ],
                        "maximum_entities_global": (entity_analysis.maximum_entities_global),
                        "maximum_entities_per_instrument": (
                            entity_analysis.maximum_entities_per_instrument
                        ),
                        "maximum_entities_per_type": (
                            entity_analysis.maximum_entities_per_instrument_type
                        ),
                        "maximum_metric_values": (
                            entity_analysis.maximum_metric_values
                            or entity_analysis.maximum_entities_global
                        ),
                        "minimum_snapshot_interval_ms": (
                            entity_analysis.minimum_snapshot_interval_ms
                        ),
                        "maximum_publications_per_cycle": (
                            entity_analysis.maximum_publications_per_cycle
                        ),
                        "schema_version": entity_analysis.catalog_version,
                    },
                ),
            ),
        )
        market_state_definitions = [
            definition
            for definition in entity_analysis.definitions
            if definition.enabled
            and definition.market_state is not None
            and definition.group
            in {
                "volatility_compression_expansion",
                "direction_trend_rotation_reference",
            }
        ]
        unsupported_state_types = sorted(
            definition.entity_type
            for definition in market_state_definitions
            if definition.entity_type
            not in {
                "volatility_state",
                "compression_expansion_state",
                "directional_state",
            }
            and not definition.entity_type.startswith("reference_state.")
        )
        if unsupported_state_types:
            raise ValueError(
                "metric-driven market-state definitions use unsupported entity types: "
                f"{unsupported_state_types!r}",
            )
        available_state_metric_keys = _available_market_state_metric_keys(config)
        missing_state_metric_keys = sorted(
            {
                (dependency.metric_id, dependency.metric_version)
                for definition in market_state_definitions
                for dependency in definition.metric_inputs
            }
            - available_state_metric_keys,
        )
        if missing_state_metric_keys:
            raise ValueError(
                "market-state entity definitions require unavailable runtime metrics: "
                f"{missing_state_metric_keys!r}",
            )
        if market_state_definitions:
            assert entity_analysis.maximum_metric_values is not None
            assert entity_analysis.market_state_reconciliation_interval_ms is not None
            registrations.append(
                ActorRegistration(
                    key="market_state_entities",
                    actor_id="MARKET-STATE-ENTITIES",
                    config=ImportableActorConfig(
                        actor_path=(
                            "markeitech.intelligence.market_state_actor:MarketStateEntityActor"
                        ),
                        config_path=(
                            "markeitech.intelligence.market_state_actor:"
                            "MarketStateEntityActorConfig"
                        ),
                        config={
                            "actor_id": "MARKET-STATE-ENTITIES",
                            "instrument_profiles": {
                                instrument_id: {
                                    "profile_id": profile_by_instrument[instrument_id],
                                    "profile_version": profile_by_id[
                                        profile_by_instrument[instrument_id]
                                    ].version,
                                }
                                for instrument_id in selected_instruments
                            },
                            "definitions": [
                                _entity_definition_payload(definition)
                                for definition in market_state_definitions
                            ],
                            "maximum_entities_global": (entity_analysis.maximum_entities_global),
                            "maximum_entities_per_instrument": (
                                entity_analysis.maximum_entities_per_instrument
                            ),
                            "maximum_entities_per_type": (
                                entity_analysis.maximum_entities_per_instrument_type
                            ),
                            "maximum_metric_values": entity_analysis.maximum_metric_values,
                            "reconciliation_interval_ms": (
                                entity_analysis.market_state_reconciliation_interval_ms
                            ),
                            "minimum_snapshot_interval_ms": (
                                entity_analysis.minimum_snapshot_interval_ms
                            ),
                            "maximum_publications_per_cycle": (
                                entity_analysis.maximum_publications_per_cycle
                            ),
                            "schema_version": entity_analysis.catalog_version,
                        },
                    ),
                ),
            )
        market_structure_definitions = [
            definition
            for definition in entity_analysis.definitions
            if definition.enabled and definition.group == "swing_fvg_zone"
        ]
        if market_structure_definitions:
            registrations.append(
                ActorRegistration(
                    key="market_structure_entities",
                    actor_id="MARKET-STRUCTURE-ENTITIES",
                    config=ImportableActorConfig(
                        actor_path=(
                            "markeitech.intelligence.market_structure_actor:"
                            "MarketStructureEntityActor"
                        ),
                        config_path=(
                            "markeitech.intelligence.market_structure_actor:"
                            "MarketStructureEntityActorConfig"
                        ),
                        config={
                            "actor_id": "MARKET-STRUCTURE-ENTITIES",
                            "instrument_profiles": {
                                instrument_id: {
                                    "profile_id": profile_by_instrument[instrument_id],
                                    "profile_version": profile_by_id[
                                        profile_by_instrument[instrument_id]
                                    ].version,
                                }
                                for instrument_id in selected_instruments
                            },
                            "definitions": [
                                _entity_definition_payload(definition)
                                for definition in market_structure_definitions
                            ],
                            "maximum_entities_global": (entity_analysis.maximum_entities_global),
                            "maximum_entities_per_instrument": (
                                entity_analysis.maximum_entities_per_instrument
                            ),
                            "maximum_entities_per_type": (
                                entity_analysis.maximum_entities_per_instrument_type
                            ),
                            "minimum_snapshot_interval_ms": (
                                entity_analysis.minimum_snapshot_interval_ms
                            ),
                            "maximum_publications_per_cycle": (
                                entity_analysis.maximum_publications_per_cycle
                            ),
                            "schema_version": entity_analysis.catalog_version,
                        },
                    ),
                ),
            )
    registrations.extend(
        [
            ActorRegistration(
                key="historical_evidence_planner",
                actor_id="HISTORICAL-EVIDENCE-PLANNER",
                config=ImportableActorConfig(
                    actor_path=(
                        "markeitech.system.historical_planner:HistoricalEvidencePlannerActor"
                    ),
                    config_path=(
                        "markeitech.system.historical_planner:"
                        "HistoricalEvidencePlannerActorConfig"
                    ),
                    config={
                        "actor_id": "HISTORICAL-EVIDENCE-PLANNER",
                        "instrument_ids": instrument_ids,
                        "instrument_calendars": {
                            member.instrument_id: member.calendar_id
                            for member in config.watchlist.members
                        },
                        "expected_calendar_digests": {
                            calendar.calendar_id: calendar.definition_digest
                            for calendar in config.sessions.calendars
                        },
                        "projection_lookback_days": config.sessions.projection_lookback_days,
                        "projection_lookahead_days": config.sessions.projection_lookahead_days,
                        "calendar_source": "SESSION-STATE",
                        "calendar_source_epoch": str(prerequisites.run_id),
                        "projection_retry": projection_retry,
                        "historical": {
                            "maximum_plan_requests": config.historical.maximum_plan_requests,
                            "maximum_observations_per_request": (
                                config.historical.maximum_observations_per_request
                            ),
                            "maximum_total_observations": (
                                config.historical.maximum_total_observations
                            ),
                        },
                    },
                ),
            ),
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
    if config.runtime_resources.enabled:
        registrations.append(
            ActorRegistration(
                key="runtime_resources",
                actor_id="RUNTIME-RESOURCES",
                config=ImportableActorConfig(
                    actor_path="markeitech.system.resource_actor:RuntimeResourceActor",
                    config_path=("markeitech.system.resource_actor:RuntimeResourceActorConfig"),
                    config={
                        "actor_id": "RUNTIME-RESOURCES",
                        "sample_interval_ms": config.runtime_resources.sample_interval_ms,
                        "log_every_samples": config.runtime_resources.log_every_samples,
                        "include_cache_counts": (config.runtime_resources.include_cache_counts),
                        "disk_path": config.runtime_resources.disk_path,
                    },
                ),
            ),
        )
        if config.runtime_resources.health.enabled:
            health = config.runtime_resources.health
            registrations.append(
                ActorRegistration(
                    key="runtime_resource_health",
                    actor_id="RUNTIME-RESOURCE-HEALTH",
                    config=ImportableActorConfig(
                        actor_path=(
                            "markeitech.system.resource_health_actor:RuntimeResourceHealthActor"
                        ),
                        config_path=(
                            "markeitech.system.resource_health_actor:"
                            "RuntimeResourceHealthActorConfig"
                        ),
                        config={
                            "actor_id": "RUNTIME-RESOURCE-HEALTH",
                            "sample_interval_ms": config.runtime_resources.sample_interval_ms,
                            "threshold_version": health.threshold_version,
                            "warning_consecutive_samples": health.warning_consecutive_samples,
                            "critical_consecutive_samples": health.critical_consecutive_samples,
                            "recovery_consecutive_samples": health.recovery_consecutive_samples,
                            "notification_cooldown_ms": health.notification_cooldown_ms,
                            "rss_growth_window_samples": health.rss_growth_window_samples,
                            "stale_warning_ms": health.stale_warning_ms,
                            "stale_critical_ms": health.stale_critical_ms,
                            "warning": health.warning.to_dict(),
                            "critical": health.critical.to_dict(),
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
        required.extend((SYSTEM_HEALTH_WEBHOOK_ENV, OPERATIONAL_EVENTS_WEBHOOK_ENV))
    missing = [name for name in required if not environment.get(name, "").strip()]
    if missing:
        raise RuntimeError(f"required runtime environment is missing: {', '.join(sorted(missing))}")


def _reject_duplicate_actor_ids(registrations: list[ActorRegistration]) -> None:
    actor_ids = [registration.actor_id for registration in registrations]
    duplicates = sorted({actor_id for actor_id in actor_ids if actor_ids.count(actor_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate actor ids: {', '.join(duplicates)}")
