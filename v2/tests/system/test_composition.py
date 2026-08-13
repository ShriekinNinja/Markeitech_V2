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
        "watchlist",
        "discord_health",
        "operational_persistence",
    ]
    assert len({registration.actor_id for registration in plan}) == len(plan)
    acquisition = next(item for item in plan if item.key == "data_acquisition")
    assert acquisition.config.config["bootstrap_feeds"] == [
        {"instrument_id": "ESU6.CME", "kind": "quotes", "selector": "default"},
        {"instrument_id": "ESU6.CME", "kind": "bars", "selector": "5-SECOND-LAST-EXTERNAL"},
        {"instrument_id": "NQU6.CME", "kind": "quotes", "selector": "default"},
        {"instrument_id": "NQU6.CME", "kind": "bars", "selector": "5-SECOND-LAST-EXTERNAL"},
        {"instrument_id": "SPY.ARCA", "kind": "quotes", "selector": "default"},
        {"instrument_id": "SPY.ARCA", "kind": "bars", "selector": "5-SECOND-LAST-EXTERNAL"},
        {"instrument_id": "QQQ.NASDAQ", "kind": "quotes", "selector": "default"},
        {"instrument_id": "QQQ.NASDAQ", "kind": "bars", "selector": "5-SECOND-LAST-EXTERNAL"},
        {"instrument_id": "XLK.ARCA", "kind": "quotes", "selector": "default"},
        {"instrument_id": "XLK.ARCA", "kind": "bars", "selector": "5-SECOND-LAST-EXTERNAL"},
        {"instrument_id": "XLF.ARCA", "kind": "quotes", "selector": "default"},
        {"instrument_id": "XLF.ARCA", "kind": "bars", "selector": "5-SECOND-LAST-EXTERNAL"},
        {"instrument_id": "IWM.ARCA", "kind": "quotes", "selector": "default"},
        {"instrument_id": "IWM.ARCA", "kind": "bars", "selector": "5-SECOND-LAST-EXTERNAL"},
        {"instrument_id": "SOXL.ARCA", "kind": "quotes", "selector": "default"},
        {"instrument_id": "SOXL.ARCA", "kind": "bars", "selector": "5-SECOND-LAST-EXTERNAL"},
    ]
    watchlist = next(item for item in plan if item.key == "watchlist")
    assert watchlist.config.config["members"] == [
        {
            "instrument_id": instrument_id,
            "owner_ids": ["config:system"],
            "capabilities": ["top_of_book", "watchlist_last"],
        }
        for instrument_id in [
            "ESU6.CME",
            "NQU6.CME",
            "SPY.ARCA",
            "QQQ.NASDAQ",
            "XLK.ARCA",
            "XLF.ARCA",
            "IWM.ARCA",
            "SOXL.ARCA",
        ]
    ]


def test_actor_plan_omits_disabled_discord_but_never_core() -> None:
    config = _config()
    config = replace(config, discord=replace(config.discord, enabled=False))

    plan = build_actor_plan(config, _prerequisites())

    assert [registration.key for registration in plan] == [
        "system_control",
        "data_acquisition",
        "watchlist",
        "operational_persistence",
    ]


def test_actor_plan_omits_disabled_native_consumer_probe() -> None:
    config = _config()
    config = replace(
        config,
        acquisition=replace(config.acquisition, native_consumer_probe_enabled=False),
    )

    plan = build_actor_plan(config, _prerequisites())

    assert "native_consumer_probe" not in {registration.key for registration in plan}


def test_actor_plan_adds_enabled_native_consumer_probe() -> None:
    config = _config()
    config = replace(
        config,
        acquisition=replace(config.acquisition, native_consumer_probe_enabled=True),
    )

    plan = build_actor_plan(config, _prerequisites())

    acquisition = next(item for item in plan if item.key == "data_acquisition")
    probe = next(item for item in plan if item.key == "native_consumer_probe")
    assert probe.config.config["feeds"] == acquisition.config.config["bootstrap_feeds"]
    assert probe.config.config["unsubscribe_after_seconds"] == 15


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
