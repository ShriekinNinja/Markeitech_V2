from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from markeitech.system.composition import (
    StartupPrerequisites,
    build_actor_plan,
    validate_runtime_environment,
)
from markeitech.system.config import load_system_config
from markeitech.system.discord import (
    OPERATIONAL_EVENTS_WEBHOOK_ENV,
    SYSTEM_HEALTH_WEBHOOK_ENV,
)


@pytest.fixture(autouse=True)
def _write_calendar_catalog(tmp_path: Path) -> None:
    source = Path(__file__).parents[2] / "config/market-calendars.toml"
    (tmp_path / "market-calendars.toml").write_text(source.read_text())


def _config():  # noqa: ANN202
    root = Path(__file__).parents[2]
    return load_system_config(root / "config/system.example.toml")


def _prerequisites(ready: bool = True) -> StartupPrerequisites:
    return StartupPrerequisites(
        run_id=uuid4(),
        operational_persistence_ready=ready,
    )


def test_actor_plan_has_mandatory_core_and_enabled_discord() -> None:
    plan = build_actor_plan(_config(), _prerequisites())

    assert [registration.key for registration in plan] == [
        "system_control",
        "session_state",
        "evidence_health",
        "discord_health",
        "historical_evidence_planner",
        "watchlist",
        "data_acquisition",
        "runtime_resources",
        "runtime_resource_health",
        "operational_persistence",
        "dashboard",
    ]
    assert len({registration.actor_id for registration in plan}) == len(plan)
    session_state = next(item for item in plan if item.key == "session_state")
    assert session_state.config.config["allowed_current_state_requesters"] == [
        "EVIDENCE-HEALTH",
        "HISTORICAL-EVIDENCE-PLANNER",
    ]
    assert session_state.config.config["current_state_delivery"] == {
        "policy_version": 1,
        "response_timeout_ms": 5000,
        "maximum_attempts": 3,
        "retry_backoff_ms": 1000,
        "maximum_elapsed_ms": 60000,
        "maximum_buffered_transitions_per_calendar": 8,
        "maximum_total_buffered_transitions": 32,
        "boundary_delivery_grace_ms": 2000,
    }
    evidence_health = next(item for item in plan if item.key == "evidence_health")
    assert (
        evidence_health.config.config["current_state_delivery"]
        == (session_state.config.config["current_state_delivery"])
    )
    assert {
        item["calendar_id"] for item in evidence_health.config.config["calendar_expectations"]
    } == {calendar.calendar_id for calendar in _config().sessions.calendars}
    acquisition = next(item for item in plan if item.key == "data_acquisition")
    assert acquisition.config.config["actor_id"] == "DATA-ACQUISITION"
    assert acquisition.config.config["instrument_ids"] == list(_config().instrument_ids)
    assert acquisition.config.config["historical"] == {
        "maximum_plan_requests": 64,
        "maximum_observations_per_request": 5000,
        "maximum_total_observations": 20000,
        "maximum_outstanding_requests": 64,
        "maximum_in_flight_requests": 1,
        "timeout_seconds": 30,
        "maximum_attempts": 3,
        "retry_backoff_ms": 500,
        "poll_interval_ms": 100,
    }
    assert "instrument_calendars" not in acquisition.config.config
    assert "calendars" not in acquisition.config.config
    planner = next(item for item in plan if item.key == "historical_evidence_planner")
    assert planner.config.config["instrument_calendars"]["ESU6.CME"] == "cme_equity"
    assert set(planner.config.config["expected_calendar_digests"]) == {
        "cboe_spxw",
        "us_equities",
        "cme_equity",
        "cbot_equity",
        "cme_energy",
    }
    assert (
        planner.config.config["current_state_delivery"]
        == (session_state.config.config["current_state_delivery"])
    )
    assert (
        planner.config.config["calendar_expectations"]
        == (evidence_health.config.config["calendar_expectations"])
    )
    watchlist = next(item for item in plan if item.key == "watchlist")
    assert watchlist.config.config["consumer_retry_interval_ms"] == 1000
    assert watchlist.config.config["members"] == [
        {
            "instrument_id": instrument_id,
            "calendar_id": (
                "cme_equity"
                if instrument_id in {"ESU6.CME", "NQU6.CME"}
                else "cme_energy"
                if instrument_id == "CLV6.NYMEX"
                else "us_equities"
            ),
            "owner_ids": ["config:system"],
            "capabilities": (
                ["watchlist_last"]
                if instrument_id in {"^SPX.CBOE", "^VIX.CBOE"}
                else ["top_of_book", "watchlist_last"]
            ),
        }
        for instrument_id in [
            "ESU6.CME",
            "NQU6.CME",
            "CLV6.NYMEX",
            "SPY.ARCA",
            "QQQ.NASDAQ",
            "^SPX.CBOE",
            "^VIX.CBOE",
        ]
    ]
    evidence = next(item for item in plan if item.key == "evidence_health")
    assert evidence.config.config["consumer_retry_interval_ms"] == 1000
    resources = next(item for item in plan if item.key == "runtime_resources")
    assert resources.config.config == {
        "actor_id": "RUNTIME-RESOURCES",
        "sample_interval_ms": 10000,
        "log_every_samples": 1,
        "include_cache_counts": True,
        "disk_path": "/",
    }
    health = next(item for item in plan if item.key == "runtime_resource_health")
    assert health.config.config["threshold_version"] == "2026-08-22-v2"
    assert health.config.config["warning"]["host_memory_available_percent"] == 15.0
    assert health.config.config["critical"]["disk_free_percent"] == 2.0
    discord = next(item for item in plan if item.key == "discord_health")
    assert discord.config.config["operational_events_webhook_env"] == (
        OPERATIONAL_EVENTS_WEBHOOK_ENV
    )


def test_actor_plan_omits_disabled_discord_but_never_core() -> None:
    config = _config()
    config = replace(config, discord=replace(config.discord, enabled=False))

    plan = build_actor_plan(config, _prerequisites())

    assert [registration.key for registration in plan] == [
        "system_control",
        "session_state",
        "evidence_health",
        "historical_evidence_planner",
        "watchlist",
        "data_acquisition",
        "runtime_resources",
        "runtime_resource_health",
        "operational_persistence",
        "dashboard",
    ]


def test_actor_plan_omits_disabled_runtime_resource_telemetry() -> None:
    config = _config()
    config = replace(
        config,
        runtime_resources=replace(config.runtime_resources, enabled=False),
    )

    plan = build_actor_plan(config, _prerequisites())

    assert "runtime_resources" not in {registration.key for registration in plan}
    assert "runtime_resource_health" not in {registration.key for registration in plan}


def test_actor_plan_rejects_missing_required_preflight() -> None:
    with pytest.raises(ValueError, match="persistence must pass preflight"):
        build_actor_plan(_config(), _prerequisites(ready=False))


def test_enabled_discord_and_postgres_environment_are_required() -> None:
    config = _config()

    with pytest.raises(RuntimeError, match=SYSTEM_HEALTH_WEBHOOK_ENV):
        validate_runtime_environment(
            config,
            {config.persistence.dsn_env: "postgresql://configured"},
        )

    with pytest.raises(RuntimeError, match=OPERATIONAL_EVENTS_WEBHOOK_ENV):
        validate_runtime_environment(
            config,
            {
                config.persistence.dsn_env: "postgresql://configured",
                SYSTEM_HEALTH_WEBHOOK_ENV: "https://configured",
            },
        )


def test_disabled_discord_requires_only_postgres_environment() -> None:
    config = _config()
    config = replace(config, discord=replace(config.discord, enabled=False))

    validate_runtime_environment(
        config,
        {config.persistence.dsn_env: "postgresql://configured"},
    )
