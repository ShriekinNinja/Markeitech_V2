from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from markeitech.intelligence.actors import SessionStateActor, SessionStateActorConfig
from markeitech.system.composition import StartupPrerequisites, build_actor_plan
from tests.system.config_fixtures import minimal_calendar_config


def test_minimal_calendar_config_has_operational_calendar_surface() -> None:
    config = minimal_calendar_config()
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
        "definition_digest" in calendar for calendar in session_state.config.config["calendars"]
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
        assert registration.config.config["current_state_delivery"]["policy_version"] == 1
        assert registration.config.config["calendar_expectations"]
    assert planner.config.config["projection_retry"] == {
        "response_timeout_ms": 5000,
        "maximum_attempts": 3,
        "retry_backoff_ms": 1000,
        "maximum_elapsed_ms": 60000,
    }
    assert "projection_retry" not in evidence_health.config.config

    actor = SessionStateActor(SessionStateActorConfig(**session_state.config.config))
    assert len(actor._calendars) == len(config.sessions.calendars)
    assert set(actor._calendars) == {calendar.calendar_id for calendar in config.sessions.calendars}
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
        calendar for calendar in config.sessions.calendars if calendar.calendar_id == "cme_equity"
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
    assert [registration.key for registration in plan] == [
        "system_control",
        "session_state",
        "evidence_health",
        "historical_evidence_planner",
        "watchlist",
        "data_acquisition",
        "operational_persistence",
    ]


def test_minimal_calendar_composes_active_calendar_operational_path() -> None:
    config = minimal_calendar_config()

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
