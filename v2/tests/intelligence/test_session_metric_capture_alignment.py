from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from markeitech.intelligence.session_metric_actor import (
    _completed_bar_foundation_historical_demand,
)
from markeitech.system.composition import StartupPrerequisites, build_actor_plan
from markeitech.system.config import load_system_config

_MINUTE_NS = 60_000_000_000


def test_foundation_history_demand_has_no_visual_capture_parameters() -> None:
    demand = _completed_bar_foundation_historical_demand(
        demand_id="session-metrics:ESU6.CME:completed-bars:v1",
        consumer_id="SESSION-METRICS",
        instrument_id="ESU6.CME",
        selector="1-MINUTE-LAST-EXTERNAL",
        window="recent_completed",
        minimum_observations=2,
        maximum_observations=55,
        priority=40,
        as_of_ns=10 * _MINUTE_NS + 25_000_000_000,
        calculation_interval_seconds=60,
        parameter_version=1,
    )

    assert demand.purpose == "warm completed-bar foundation metrics"
    assert demand.parameters == {
        "calculation_interval_seconds": 60,
        "parameter_version": 1,
    }


def test_capture_on_off_changes_only_passive_observer_registration() -> None:
    enabled = load_system_config("v2/config/system.v3-es-minimal.toml")
    disabled = replace(
        enabled,
        visual_debug_capture=replace(enabled.visual_debug_capture, enabled=False),
    )
    prerequisites = StartupPrerequisites(
        run_id=UUID("00000000-0000-0000-0000-000000000001"),
        operational_persistence_ready=True,
    )

    enabled_plan = build_actor_plan(enabled, prerequisites)
    disabled_plan = build_actor_plan(disabled, prerequisites)
    without_observer = tuple(
        registration
        for registration in enabled_plan
        if registration.key != "visual_debug_capture"
    )

    def normalized(plan):  # noqa: ANN001, ANN202
        return tuple(
            (
                item.key,
                item.actor_id,
                item.config.actor_path,
                item.config.config_path,
                item.config.config,
            )
            for item in plan
        )

    assert normalized(without_observer) == normalized(disabled_plan)
    session = next(item for item in enabled_plan if item.key == "session_metrics")
    assert not any(key.startswith("visual_") for key in session.config.config)
