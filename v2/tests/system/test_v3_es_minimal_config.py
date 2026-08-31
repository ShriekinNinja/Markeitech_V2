from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from markeitech.intelligence.actors import SessionStateActor, SessionStateActorConfig
from markeitech.system.composition import StartupPrerequisites, build_actor_plan
from markeitech.system.config import load_system_config


def test_v3_es_minimal_config_disables_faulty_session_metrics_surface() -> None:
    config = load_system_config("v2/config/system.v3-es-minimal.toml")
    plan = build_actor_plan(
        config,
        StartupPrerequisites(
            run_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_persistence_ready=True,
        ),
    )

    session_state = next(item for item in plan if item.key == "session_state")
    acquisition = next(item for item in plan if item.key == "data_acquisition")
    planner = next(item for item in plan if item.key == "historical_evidence_planner")
    evidence_health = next(item for item in plan if item.key == "evidence_health")
    assert len(session_state.config.config["calendars"]) == 1
    assert all(
        "definition_digest" in calendar
        for calendar in session_state.config.config["calendars"]
    )
    assert session_state.config.config["allowed_current_state_requesters"] == [
        "EVIDENCE-HEALTH",
        "HISTORICAL-EVIDENCE-PLANNER",
    ]
    assert session_state.config.config["current_state_delivery"]["policy_version"] == 1
    assert "calendars" not in acquisition.config.config
    assert planner.config.config["expected_calendar_digests"]
    for registration in (evidence_health, planner):
        assert registration.config.config["calendar_source"] == "SESSION-STATE"
        assert registration.config.config["calendar_source_epoch"] == (
            "00000000-0000-0000-0000-000000000001"
        )
        assert registration.config.config["projection_retry"] == {
            "response_timeout_ms": 5000,
            "maximum_attempts": 3,
            "retry_backoff_ms": 1000,
            "maximum_elapsed_ms": 60000,
        }

    actor = SessionStateActor(SessionStateActorConfig(**session_state.config.config))
    assert len(actor._calendars) == len(config.sessions.calendars)
    assert set(actor._calendars) == {
        calendar.calendar_id for calendar in config.sessions.calendars
    }
    maintenance_break_ns = int(
        datetime(2026, 8, 24, 20, 20, tzinfo=UTC).timestamp() * 1_000_000_000
    )
    assert actor._calendars["cme_equity"].evaluate(maintenance_break_ns).market_state == "OPEN"

    assert config.instrument_ids == ("ESU6.CME",)
    assert config.watchlist.members[0].capabilities == ("watchlist_last",)
    assert len(config.sessions.calendars) == 1
    assert len(config.sessions.available_calendars) == 5
    assert config.sessions.catalog_id == "markeitech-market-calendars"
    assert config.sessions.catalog_version == 4
    assert config.sessions.projection_retry.response_timeout_ms == 5000
    assert config.sessions.projection_retry.maximum_attempts == 3
    cme_equity = next(
        calendar
        for calendar in config.sessions.calendars
        if calendar.calendar_id == "cme_equity"
    )
    assert cme_equity.provider_calendar == "CME_Equity"
    assert cme_equity.exchange_timezone == "America/Chicago"
    assert cme_equity.schedule_version.startswith("pmc-5.4.0:cme_equity:v4:")
    assert cme_equity.schedule_columns == (
        "market_open",
        "break_start",
        "break_end",
        "market_close",
    )
    assert tuple(phase.name for phase in cme_equity.phases) == (
        "GLOBEX",
        "ASIA",
        "LONDON",
        "NEW_YORK",
    )
    assert tuple(item.correction_id for item in cme_equity.corrections) == (
        "cme-equity-remove-1515-pause",
    )
    assert config.discord.enabled is False
    assert config.runtime_resources.enabled is False
    assert config.historical.maximum_plan_requests == 1
    assert config.historical.maximum_observations_per_request == 60
    assert config.historical.maximum_total_observations == 60
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
    assert config.metrics.session_measurements.enabled is False
    completed_bars = config.metrics.session_measurements.completed_bars
    assert config.metrics.session_measurements.parameter_version == 2
    assert config.metrics.session_measurements.parameter_source == (
        "v3-es-5m-completed-bar-foundation"
    )
    assert config.metrics.session_measurements.parameter_effective_from_ns == int(
        datetime(2026, 8, 28, 11, 3, 7, tzinfo=UTC).timestamp() * 1_000_000_000
    )
    assert config.metrics.session_measurements.conflict_policy == "reject_conflict"
    assert config.metrics.session_measurements.maximum_active_sessions == 1
    assert completed_bars.live_selector == "5-SECOND-LAST-EXTERNAL"
    assert completed_bars.historical_selector == "5-MINUTE-LAST-EXTERNAL"
    assert completed_bars.historical_window == "recent_completed"
    assert completed_bars.minimum_historical_observations == 2
    assert completed_bars.maximum_historical_observations == 60
    assert completed_bars.calculation_interval_seconds == 300
    assert completed_bars.minimum_interval_seconds == 300
    assert completed_bars.maximum_interval_seconds == 300
    assert completed_bars.interval_step_seconds == 300
    assert completed_bars.interval_dynamic is False
    assert completed_bars.aggregation_boundary_policy == "utc_fixed_intraday"
    assert completed_bars.timestamp_policy == "interval_end"
    assert completed_bars.revision_policy == "reject_revision"
    assert completed_bars.maximum_retained_observations == 1000
    assert completed_bars.maximum_output_age_ms == 120000
    assert config.metrics.entity_analysis.enabled is False
    assert config.visual_debug_capture.enabled is False
    assert config.visual_debug_capture.configuration_identity == (
        "v3-es-5m-historical-60-review-v1-20260828T110307Z"
    )
    assert config.visual_debug_capture.instrument_id == "ESU6.CME"
    assert config.visual_debug_capture.bar_specification == "5-MINUTE-LAST-EXTERNAL"
    assert config.visual_debug_capture.parameter_version == 2
    assert config.visual_debug_capture.target_historical_bars == 60
    assert config.visual_debug_capture.target_live_bars == 0
    assert config.visual_debug_capture.candle_pane_height_px == 720
    assert config.visual_debug_capture.capture_policy_version == 3
    assert config.visual_debug_capture.parameter_version == 2
    assert [registration.key for registration in plan] == [
        "system_control",
        "session_state",
        "evidence_health",
        "historical_evidence_planner",
        "watchlist",
        "data_acquisition",
        "operational_persistence",
    ]


def test_v3_es_minimal_composes_only_active_calendar_and_operational_path() -> None:
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
        "historical_evidence_planner",
        "watchlist",
        "data_acquisition",
        "operational_persistence",
    ]
    assert "entity_analysis" not in keys
    assert "session_metrics" not in keys
    assert "visual_debug_capture" not in keys
