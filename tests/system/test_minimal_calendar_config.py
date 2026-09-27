from __future__ import annotations

from uuid import UUID

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

    assert config.instrument_ids == ("ESZ6.CME",)
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
    assert config.historical.maximum_plan_requests == 1
    assert config.historical.maximum_observations_per_request == 60
    assert config.historical.maximum_total_observations == 60
    assert config.historical.maximum_outstanding_requests == 1
    assert config.historical.maximum_in_flight_requests == 1
    assert config.historical.maximum_attempts == 1
    assert [registration.key for registration in plan] == [
        "system_control",
        "operational_persistence",
        "runtime_resources",
        "runtime_resource_health",
    ]


def test_minimal_calendar_is_configured_but_its_actors_are_not_yet_composed() -> None:
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
        "operational_persistence",
        "runtime_resources",
        "runtime_resource_health",
    ]
    # Calendar definitions remain loaded for the next composition stage.
    assert {item.calendar_id for item in config.sessions.calendars} == {"cme_equity"}
    assert "entity_analysis" not in keys
    assert "session_metrics" not in keys
