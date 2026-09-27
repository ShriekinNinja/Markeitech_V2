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
    source = Path(__file__).parents[2] / "config/system.calendars.toml"
    (tmp_path / "system.calendars.toml").write_text(source.read_text())


def _config():  # noqa: ANN202
    root = Path(__file__).parents[2]
    return load_system_config(root / "config/runtime.example.toml")


def _prerequisites(ready: bool = True) -> StartupPrerequisites:
    return StartupPrerequisites(
        run_id=uuid4(),
        operational_persistence_ready=ready,
    )


def test_actor_plan_has_four_mandatory_actors() -> None:
    prerequisites = _prerequisites()
    config = _config()
    plan = build_actor_plan(config, prerequisites)

    assert [registration.key for registration in plan] == [
        "system_control",
        "operational_persistence",
        "runtime_resources",
        "runtime_resource_health",
    ]
    assert len({registration.actor_id for registration in plan}) == len(plan)
    assert all(
        registration.config.config["run_id"] == str(prerequisites.run_id)
        for registration in plan
    )
    control = plan[0].config.config
    assert "instrument_ids" not in control
    assert control["resource_threshold_version"] == (
        config.runtime_resources.health.threshold_version
    )
    assert {rule["component"] for rule in control["failure_policy"]} == {
        "operational_persistence",
        "runtime_resources",
        "runtime_resource_health",
    }
    # The sampler is registered before the evaluator that consumes its timed samples.
    health = plan[3].config.config
    assert health["stale_critical_ms"] == config.runtime_resources.health.stale_critical_ms
    assert plan[2].config.config["sample_interval_ms"] == (
        config.runtime_resources.sample_interval_ms
    )


def test_disabling_discord_does_not_remove_mandatory_resource_actors() -> None:
    config = _config()
    config = replace(config, discord=replace(config.discord, enabled=False))

    plan = build_actor_plan(config, _prerequisites())

    assert [registration.key for registration in plan] == [
        "system_control",
        "operational_persistence",
        "runtime_resources",
        "runtime_resource_health",
    ]


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
