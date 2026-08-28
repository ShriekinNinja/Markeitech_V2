from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from markeitech.system.composition import StartupPrerequisites, build_actor_plan
from markeitech.system.config import load_system_config


def test_v3_es_minimal_config_activates_only_completed_bar_visual_test() -> None:
    config = load_system_config("v2/config/system.v3-es-minimal.toml")
    plan = build_actor_plan(
        config,
        StartupPrerequisites(
            run_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_persistence_ready=True,
        ),
    )

    assert config.instrument_ids == ("ESU6.CME",)
    assert config.watchlist.members[0].capabilities == ("watchlist_last",)
    assert len(config.sessions.calendars) == 1
    assert config.sessions.calendars[0].calendar_id == "cme_equity"
    assert config.sessions.calendars[0].provider_calendar == "CME_Equity"
    assert config.sessions.calendars[0].timezone == "America/Chicago"
    assert config.sessions.calendars[0].schedule_version == "pmc-5.4"
    assert config.sessions.calendars[0].phases == ()
    assert config.sessions.calendars[0].overrides == ()
    assert config.discord.enabled is False
    assert config.runtime_resources.enabled is False
    assert config.historical.maximum_plan_requests == 1
    assert config.historical.maximum_observations_per_request == 55
    assert config.historical.maximum_total_observations == 55
    assert config.historical.maximum_outstanding_requests == 1
    assert config.historical.maximum_in_flight_requests == 1
    assert config.historical.maximum_attempts == 1
    assert config.historical.probe.enabled is False
    assert config.historical.probe.actor_ids == ("HISTORICAL-PROBE-A",)
    assert config.historical.probe.instrument_id == "ESU6.CME"
    assert config.historical.probe.selector == "1-MINUTE-LAST-EXTERNAL"
    assert config.historical.probe.window == "recent_completed"
    assert config.historical.probe.minimum_observations == 5
    assert config.historical.probe.maximum_observations == 5
    assert config.metrics.quote_quality.enabled is False
    assert config.metrics.session_measurements.enabled is True
    completed_bars = config.metrics.session_measurements.completed_bars
    assert config.metrics.session_measurements.parameter_version == 1
    assert config.metrics.session_measurements.parameter_source == "v3-es-completed-bar-foundation"
    assert config.metrics.session_measurements.parameter_effective_from_ns == int(
        datetime(2026, 8, 27, 15, 2, 56, tzinfo=UTC).timestamp() * 1_000_000_000
    )
    assert config.metrics.session_measurements.conflict_policy == "reject_conflict"
    assert config.metrics.session_measurements.maximum_active_sessions == 1
    assert completed_bars.live_selector == "5-SECOND-LAST-EXTERNAL"
    assert completed_bars.historical_selector == "1-MINUTE-LAST-EXTERNAL"
    assert completed_bars.historical_window == "recent_completed"
    assert completed_bars.minimum_historical_observations == 2
    assert completed_bars.maximum_historical_observations == 55
    assert completed_bars.calculation_interval_seconds == 60
    assert completed_bars.minimum_interval_seconds == 60
    assert completed_bars.maximum_interval_seconds == 60
    assert completed_bars.interval_step_seconds == 60
    assert completed_bars.interval_dynamic is False
    assert completed_bars.aggregation_boundary_policy == "utc_fixed_intraday"
    assert completed_bars.timestamp_policy == "interval_end"
    assert completed_bars.revision_policy == "reject_revision"
    assert completed_bars.maximum_retained_observations == 1000
    assert completed_bars.maximum_output_age_ms == 120000
    assert config.metrics.entity_analysis.enabled is False
    assert config.visual_acceptance.enabled is False
    assert config.live_evidence_review.enabled is False
    assert config.visual_debug_capture.enabled is True
    assert config.visual_debug_capture.configuration_identity == (
        "v3-es-completed-bar-foundation-review-v3-20260827T150256Z"
    )
    assert config.visual_debug_capture.instrument_id == "ESU6.CME"
    assert config.visual_debug_capture.bar_specification == "1-MINUTE-LAST-EXTERNAL"
    assert config.visual_debug_capture.historical_bar_count == 55
    assert config.visual_debug_capture.live_bar_count == 5
    assert config.visual_debug_capture.capture_policy_version == 2
    assert config.visual_debug_capture.parameter_version == 1
    assert [registration.key for registration in plan] == [
        "system_control",
        "session_state",
        "evidence_health",
        "visual_debug_capture",
        "session_metrics",
        "watchlist",
        "data_acquisition",
        "operational_persistence",
    ]


def test_v3_completed_bar_review_composes_only_approved_foundation_and_projection() -> None:
    config = load_system_config("v2/config/system.v3-es-minimal.toml")

    plan = build_actor_plan(
        config,
        StartupPrerequisites(
            run_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_persistence_ready=True,
        ),
    )

    keys = [registration.key for registration in plan]
    assert keys == [
        "system_control",
        "session_state",
        "evidence_health",
        "visual_debug_capture",
        "session_metrics",
        "watchlist",
        "data_acquisition",
        "operational_persistence",
    ]
    assert "visual_acceptance" not in keys
    assert "live_evidence_review" not in keys
    assert "entity_analysis" not in keys
    session_metrics = next(item for item in plan if item.key == "session_metrics")
    assert session_metrics.config.config["visual_snapshot_enabled"] is True
    assert session_metrics.config.config["visual_snapshot_maximum_intervals"] == 60
