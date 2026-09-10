from __future__ import annotations

import asyncio
import importlib
import json
from dataclasses import replace
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from uuid import uuid4

import pytest
from nautilus_trader.common import Environment, LoggerConfig
from nautilus_trader.live import LiveNode
from nautilus_trader.model import TraderId

from markeitech.system.acquisition import InstrumentDefinitionTracker
from markeitech.system.composition import StartupPrerequisites, build_actor_plan
from markeitech.system.config import load_system_config
from markeitech.system.discord import (
    OPERATIONAL_EVENTS_WEBHOOK_ENV,
    SYSTEM_HEALTH_WEBHOOK_ENV,
    DiscordDeliveryWorker,
    OperationalReadinessProjection,
    render_operational_readiness_message,
)
from markeitech.system.messages import AcquisitionStatusEvent, SystemHealthEvent
from markeitech.system.node import build_ib_data_client_config
from markeitech.system.persistence import OperationalStore
from markeitech.system.resource_actor import ProcessResourceSample, ProcessResourceSampler

PROFILE = Path(__file__).parents[2] / "config/system.operational.toml"
ROSTER = [
    "system_control",
    "session_state",
    "evidence_health",
    "discord_health",
    "historical_evidence_planner",
    "data_acquisition",
    "runtime_resources",
    "runtime_resource_health",
    "operational_persistence",
]


def test_operational_profile_has_exact_roster_and_empty_native_provider_loads() -> None:
    config = load_system_config(PROFILE)
    assert config.instrument_ids == ()
    assert not config.watchlist.enabled
    plan = build_actor_plan(config, StartupPrerequisites(uuid4(), True))
    assert [item.key for item in plan] == ROSTER
    assert build_ib_data_client_config(config).instrument_provider.load_ids == set()


@pytest.mark.parametrize(
    ("old", "new", "error"),
    [
        ("[watchlist]\nenabled = false", "[watchlist]\nenabled = true", "non-empty"),
    ],
)
def test_empty_profile_rejects_instrument_consumers(tmp_path, old, new, error) -> None:
    (tmp_path / "market-calendars.toml").write_bytes(
        (PROFILE.parent / "market-calendars.toml").read_bytes(),
    )
    path = tmp_path / "system.toml"
    path.write_text(PROFILE.read_text().replace(old, new))
    with pytest.raises(ValueError, match=error):
        load_system_config(path)


def test_empty_acquisition_status_roundtrips_without_provider_requests() -> None:
    tracker = InstrumentDefinitionTracker(())
    assert tracker.take_unrequested() == ()
    status = tracker.status("DATA-ACQUISITION")
    assert AcquisitionStatusEvent.from_signal_value(status.to_signal_value()) == status
    assert status.expected_instrument_ids == ()
    assert "idle" in status.reason


def test_discord_zero_work_summary_requires_explicit_configuration_and_ready() -> None:
    ready = SystemHealthEvent(
        state="READY", reason="empty acquisition initialized", source="SYSTEM", evidence={}
    )
    assert OperationalReadinessProjection().accept_system_health(ready, 100) is None
    projection = OperationalReadinessProjection(empty_universe=True)
    starting = SystemHealthEvent(
        state="STARTING", reason="initializing", source="SYSTEM", evidence={}
    )
    assert projection.accept_system_health(starting, 99) is None
    result = projection.accept_system_health(ready, 100)
    assert result is not None and result.is_ready and result.completed_at_ns == 100
    embed = json.loads(render_operational_readiness_message(result))["embeds"][0]
    assert "zero instruments" in embed["title"]
    assert "separate operational checks" in embed["description"]
    assert all(field["value"] for field in embed["fields"])
    assert projection.accept_system_health(ready, 101) is None


def test_nine_operational_actors_boot_and_stop_offline(monkeypatch) -> None:
    """Exercise native lifecycle/workers with SQL, HTTP and host samples replaced."""
    records = []
    deliveries = []
    monkeypatch.setenv(SYSTEM_HEALTH_WEBHOOK_ENV, "https://example.invalid/health")
    monkeypatch.setenv(OPERATIONAL_EVENTS_WEBHOOK_ENV, "https://example.invalid/operational")
    monkeypatch.setattr(
        OperationalStore,
        "from_environment",
        classmethod(
            lambda cls, *args: SimpleNamespace(check=lambda: None, write_records=records.extend),
        ),
    )

    def post(url, **kwargs):
        deliveries.append(json.loads(kwargs["data"]))
        return SimpleNamespace(status_code=204)

    monkeypatch.setattr(
        "markeitech.system.discord.DiscordDeliveryWorker",
        lambda *args, **kwargs: DiscordDeliveryWorker(*args, **kwargs, post=post),
    )
    monkeypatch.setattr(
        ProcessResourceSampler,
        "sample",
        lambda self: ProcessResourceSample(
            rss_bytes=100_000_000,
            vms_bytes=200_000_000,
            cpu_user_seconds=1.0,
            cpu_system_seconds=0.1,
            thread_count=8,
            open_fd_count=12,
            open_fd_soft_limit=1024,
            host_cpu_percent=5.0,
            host_memory_total_bytes=32_000_000_000,
            host_memory_available_bytes=16_000_000_000,
            host_memory_available_percent=50.0,
            host_swap_used_bytes=0,
            host_swap_percent=0.0,
            disk_total_bytes=1_000_000_000_000,
            disk_free_bytes=500_000_000_000,
            disk_free_percent=50.0,
            monotonic_seconds=monotonic(),
        ),
    )
    config = load_system_config(PROFILE)
    config = replace(
        config, runtime_resources=replace(config.runtime_resources, sample_interval_ms=50)
    )
    plan = build_actor_plan(config, StartupPrerequisites(uuid4(), True))
    node = (
        LiveNode.builder(
            "operational-offline-test", TraderId.from_str("BOOT-001"), Environment.LIVE
        )
        .with_logging(LoggerConfig(bypass_logging=True))
        .with_delay_post_stop_secs(0)
        .with_delay_shutdown_secs(0)
        .build()
    )
    actors = {}
    for entry in plan:
        module, name = entry.config.actor_path.split(":")
        actor_cls = getattr(importlib.import_module(module), name)
        module, name = entry.config.config_path.split(":")
        actor_config = getattr(importlib.import_module(module), name)(**entry.config.config)
        actors[entry.key] = actor_cls(actor_config)
        node.add_actor(actors[entry.key])

    async def exercise():
        task = asyncio.create_task(node.run_async())
        try:
            async with asyncio.timeout(15):
                while not (
                    any(
                        getattr(record, "event_type", "") == "runtime.resource"
                        for record in records
                    )
                    and any("zero instruments" in d["embeds"][0]["title"] for d in deliveries)
                    and actors["session_state"]._revisions
                    and actors["evidence_health"]._session_state.phase.value == "LIVE"
                    and actors["historical_evidence_planner"]._session_state.phase.value == "LIVE"
                ):
                    if task.done():
                        await task
                        pytest.fail("node stopped before operational initialization")
                    await asyncio.sleep(0.02)
            acquisition = actors["data_acquisition"]
            assert acquisition._startup_released
            assert acquisition._instrument_requests == 0
            assert "historical-execution" not in acquisition.clock.timer_names()
            assert actors["runtime_resource_health"]._samples > 0
            assert actors["runtime_resource_health"]._rejected == 0
            assert not acquisition._managed_stream_keys
            assert not acquisition._pending_demands
            assert actors["historical_evidence_planner"]._counts["planned"] == 0
            assert actors["evidence_health"]._requirements == ()
            samples = [r for r in records if getattr(r, "event_type", "") == "runtime.resource"]
            assert all(r.payload["cache_instrument_count"] == 0 for r in samples)
        finally:
            node.handle().stop()
            await asyncio.wait_for(task, 5)
        assert not node.is_running
        for name in ("discord_health", "operational_persistence"):
            stats = actors[name]._worker.snapshot()
            assert stats.pending == stats.failed == stats.rejected == 0
        operational = actors["discord_health"]._operational_worker.snapshot()
        assert operational.pending == operational.failed == operational.rejected == 0
        assert any(getattr(getattr(r, "event", None), "state", None) == "STOPPING" for r in records)

    asyncio.run(exercise())


def test_empty_control_waits_for_acquisition_acknowledgement() -> None:
    from markeitech.system.actor import SystemControlActor, SystemControlActorConfig

    actor = SystemControlActor(SystemControlActorConfig(instrument_ids=[]))
    actor._evaluation_started = True
    actor._persistence_ready = True
    # Without acquisition's matching status the empty set cannot release READY.
    actor._publish_ready_if_complete()
    assert actor._health.state is None
