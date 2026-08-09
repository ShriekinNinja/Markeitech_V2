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
from markeitech.system.discord import SYSTEM_HEALTH_WEBHOOK_ENV


def _config():  # noqa: ANN202
    root = Path(__file__).parents[2]
    return load_system_config(root / "config/system.toml")


def _prerequisites(ready: bool = True) -> StartupPrerequisites:
    return StartupPrerequisites(
        run_id=uuid4(),
        operational_persistence_ready=ready,
    )


def test_actor_plan_has_mandatory_core_and_enabled_discord() -> None:
    plan = build_actor_plan(_config(), _prerequisites())

    assert [registration.key for registration in plan] == [
        "system_control",
        "data_acquisition",
        "discord_health",
        "operational_persistence",
    ]
    assert len({registration.actor_id for registration in plan}) == len(plan)


def test_actor_plan_omits_disabled_discord_but_never_core() -> None:
    config = _config()
    config = replace(config, discord=replace(config.discord, enabled=False))

    plan = build_actor_plan(config, _prerequisites())

    assert [registration.key for registration in plan] == [
        "system_control",
        "data_acquisition",
        "operational_persistence",
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


def test_disabled_discord_requires_only_postgres_environment() -> None:
    config = _config()
    config = replace(config, discord=replace(config.discord, enabled=False))

    validate_runtime_environment(
        config,
        {config.persistence.dsn_env: "postgresql://configured"},
    )
