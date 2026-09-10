from __future__ import annotations

import asyncio
import inspect
import json
import socket
import time
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from nautilus_trader.common import Environment
from nautilus_trader.live import LiveNode
from nautilus_trader.model import Bar, BarType, InstrumentId, Price, Quantity, QuoteTick, TraderId

from markeitech.acquisition import (
    AcquisitionCoordinator,
    DemandOwner,
    DemandOwnerKind,
    FeedKind,
    FeedRequirement,
    ObservationDemand,
)
from markeitech.dashboard.actor import DashboardActor, DashboardActorConfig
from markeitech.dashboard.config import DashboardConfig
from markeitech.dashboard.messages import (
    DASHBOARD_DEMAND_SIGNAL,
    DASHBOARD_READY_SIGNAL,
    DashboardDemand,
    DashboardReadyEvent,
)
from markeitech.dashboard.server import DashboardServer
from markeitech.dashboard.state import DashboardState
from markeitech.system.acquisition import DataAcquisitionActor, DataAcquisitionActorConfig
from markeitech.system.composition import StartupPrerequisites, build_actor_plan
from markeitech.system.config import load_system_config
from markeitech.system.discord import (
    DiscordDeliveryWorker,
    DiscordHealthActor,
    DiscordHealthActorConfig,
)

ROOT = Path(__file__).parents[2]
ID = "ESU6.CME"
MEMBERS = [
    {"instrument_id": ID, "capabilities": ["top_of_book", "watchlist_last"]},
    {"instrument_id": "^SPX.CBOE", "capabilities": ["watchlist_last"]},
]


def bar(timestamp: int, close: str = "100.25", instrument_id: str = ID) -> Bar:
    return Bar(
        BarType.from_str(f"{instrument_id}-5-SECOND-LAST-EXTERNAL"),
        Price.from_str("100.00"),
        Price.from_str("101.00"),
        Price.from_str("99.00"),
        Price.from_str(close),
        Quantity.from_int(10),
        timestamp,
        timestamp + 10,
    )


def state(capacity: int = 2) -> DashboardState:
    result = DashboardState(DashboardConfig(candles_per_instrument=capacity))
    result.set_members(MEMBERS)
    return result


def test_native_values_keep_identity_precision_timestamps_and_bounded_immutable_candles() -> None:
    display = state()
    ts = 1_800_000_000_000_000_000
    display.observe_quote(
        QuoteTick(
            InstrumentId.from_str(ID),
            Price.from_str("100.00"),
            Price.from_str("100.25"),
            Quantity.from_int(1),
            Quantity.from_int(2),
            ts,
            ts + 10,
        )
    )
    for offset in (0, 5, 10):
        display.observe_bar(bar(ts + offset * 1_000_000_000))
    display.observe_bar(bar(ts + 10_000_000_000, "100.75"))
    display.observe_bar(bar(ts))
    snapshot = display.snapshot()
    assert len(snapshot["candles"][ID]) == 2
    assert snapshot["candles"][ID][-1]["close"] == "100.25"
    assert snapshot["instruments"][0]["quote_ts_event_ns"] == str(ts)
    assert snapshot["instruments"][0]["bid"] == "100.00"
    assert snapshot["instruments"][0]["rejected_bars"] == 2
    snapshot["candles"][ID].clear()
    assert len(display.snapshot()["candles"][ID]) == 2
    assert display.snapshot()["instruments"][1]["bid"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("port", 80),
        ("enabled", 1),
        ("candles_per_instrument", 0),
        ("maximum_clients", 17),
        ("publish_interval_ms", 1),
        ("policy_version", 2),
        ("maximum_instruments", 257),
        ("shutdown_timeout_seconds", 0),
    ],
)
def test_configuration_rejects_out_of_bounds_resources(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        DashboardConfig.from_mapping({field: value})


def test_dashboard_composition_is_optional_and_configuration_driven() -> None:
    config = load_system_config(ROOT / "config/system.example.toml")
    assert config.dashboard.enabled is True
    config = replace(config, dashboard=replace(config.dashboard, enabled=False))
    prerequisites = StartupPrerequisites(uuid4(), True)
    assert not any(item.key == "dashboard" for item in build_actor_plan(config, prerequisites))
    enabled = replace(config, dashboard=replace(config.dashboard, enabled=True))
    dashboard = next(
        item for item in build_actor_plan(enabled, prerequisites) if item.key == "dashboard"
    )
    assert dashboard.config.config["dashboard"] == asdict(enabled.dashboard)
    assert config.schema_version == 26
    with pytest.raises(ValueError, match="maximum_instruments"):
        build_actor_plan(
            replace(enabled, dashboard=DashboardConfig(enabled=True, maximum_instruments=1)),
            prerequisites,
        )


def test_http_projection_selects_only_enabled_instruments_and_rejects_foreign_origins() -> None:
    display = state()
    display.observe_bar(bar(1_800_000_000_000_000_000))
    server = DashboardServer(display.config, display.snapshot())
    with TestClient(server.app, base_url="http://127.0.0.1:8765") as client:
        response = client.get("/api/snapshot", params={"instrument_id": ID})
        assert response.status_code == 200
        assert len(response.json()["candles"]) == 1
        assert (
            client.get("/api/snapshot", params={"instrument_id": "^SPX.CBOE"}).json()["candles"]
            == []
        )
        assert client.get("/api/snapshot", params={"instrument_id": "UNKNOWN"}).status_code == 404
        assert (
            client.get("/api/snapshot", headers={"origin": "https://untrusted.example"}).status_code
            == 403
        )
        assert client.get("/api/snapshot", headers={"host": "untrusted.example"}).status_code == 403
        assert client.get("/").status_code == 200
        assert "script-src 'self'" in client.get("/").headers["content-security-policy"]
        assert client.get("/static/dashboard.js").status_code == 200
        assert client.post("/api/snapshot").status_code == 405


class _Port:
    def __init__(self) -> None:
        self.calls = []

    def subscribe(self, requirement: FeedRequirement) -> None:
        self.calls.append(("subscribe", requirement.stream_key))

    def unsubscribe(self, requirement: FeedRequirement) -> None:
        self.calls.append(("unsubscribe", requirement.stream_key))


def test_acquisition_admits_and_registers_dashboard_and_preserves_watchlist_claim() -> None:
    provider, consumer = _Port(), _Port()
    coordinator = AcquisitionCoordinator(provider)
    requirement = FeedRequirement(ID, FeedKind.BARS, selector="5-SECOND-LAST-EXTERNAL")
    coordinator.request(
        ObservationDemand(
            "watchlist", DemandOwner(DemandOwnerKind.WATCHLIST, "WATCHLIST"), requirement
        ),
        now=datetime.now(UTC),
    )
    request = DashboardDemand(ID, "bars")
    published = []
    acquisition = SimpleNamespace(
        _dashboard_port=consumer,
        _dashboard_allowed={(ID, "bars")},
        _dashboard_desired={},
        _dashboard_attached={},
        _coordinator=coordinator,
        _startup_released=True,
        _tracker=SimpleNamespace(missing=()),
        _managed_stream_keys=set(),
        clock=SimpleNamespace(utc_now=lambda: datetime.now(UTC)),
        _publish_lifecycle_events=published.extend,
        log=SimpleNamespace(error=lambda value: None),
    )
    DataAcquisitionActor.on_signal(
        acquisition, SimpleNamespace(name=DASHBOARD_DEMAND_SIGNAL, value=request.to_signal_value())
    )
    assert consumer.calls == []  # Signal handling stages intent; no nested native mutation.
    DataAcquisitionActor._reconcile_dashboard(acquisition, None)
    DataAcquisitionActor._reconcile_dashboard(acquisition, None)
    assert consumer.calls == [("subscribe", requirement.stream_key)]
    assert provider.calls == [("subscribe", requirement.stream_key)]
    DataAcquisitionActor.on_signal(
        acquisition,
        SimpleNamespace(
            name=DASHBOARD_DEMAND_SIGNAL, value=replace(request, action="RELEASE").to_signal_value()
        ),
    )
    DataAcquisitionActor._reconcile_dashboard(acquisition, None)
    assert consumer.calls[-1] == ("unsubscribe", requirement.stream_key)
    assert [d.demand_id for d in coordinator.demands] == ["watchlist"]
    assert len(provider.calls) == 1
    for method in ("subscribe_quotes(", "subscribe_bars(", "unsubscribe_quotes(", "request_bars("):
        assert method not in inspect.getsource(DashboardActor)


def test_acquisition_rejects_dashboard_demand_outside_configured_feed_set() -> None:
    rejected = []
    acquisition = SimpleNamespace(
        _dashboard_allowed={(ID, "bars")},
        _dashboard_desired={},
        log=SimpleNamespace(error=rejected.append),
    )
    DataAcquisitionActor.on_signal(
        acquisition,
        SimpleNamespace(
            name=DASHBOARD_DEMAND_SIGNAL, value=DashboardDemand(ID, "quotes").to_signal_value()
        ),
    )
    assert acquisition._dashboard_desired == {}
    assert len(rejected) == 1


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_server_streams_snapshot_updates_and_stops_with_system_actor(monkeypatch) -> None:
    deliveries = []
    operational_url = "https://operational.invalid/webhook"
    health_url = "https://health.invalid/webhook"
    monkeypatch.setenv("MARKEITECH_DISCORD_OPERATIONAL_EVENTS_WEBHOOK", operational_url)
    monkeypatch.setenv("MARKEITECH_DISCORD_SYSTEM_HEALTH_WEBHOOK", health_url)

    def fake_post(url, **kwargs):  # noqa: ANN001, ANN202
        deliveries.append((url, json.loads(kwargs["data"])))
        return SimpleNamespace(status_code=200)

    monkeypatch.setattr(
        "markeitech.system.discord.DiscordDeliveryWorker",
        lambda url, timeout, capacity: DiscordDeliveryWorker(
            url, timeout, capacity, post=fake_post
        ),
    )

    async def run() -> None:
        config = DashboardConfig(port=free_port(), publish_interval_ms=100)
        actor = DashboardActor(
            DashboardActorConfig(dashboard=asdict(config), watchlist_enabled=False)
        )
        discord = DiscordHealthActor(
            DiscordHealthActorConfig(
                request_timeout_seconds=1,
                queue_capacity=4,
                ping_critical_resource_alerts=False,
            )
        )
        node = (
            LiveNode.builder(
                "DASHBOARD-OFFLINE-TEST",
                TraderId.from_str("DASHBOARD-TEST-001"),
                Environment.SANDBOX,
            )
            .with_delay_post_stop_secs(0)
            .build()
        )
        node.add_actor(discord)
        node.add_actor(actor)
        handle = node.handle()
        task = asyncio.create_task(node.run_async())
        try:
            async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{config.port}") as client:
                for _attempt in range(50):
                    try:
                        response = await client.get("/api/snapshot")
                        break
                    except httpx.ConnectError:
                        await asyncio.sleep(0.05)
                else:
                    pytest.fail("dashboard did not start with the native actor")
                assert response.status_code == 200
                for _attempt in range(50):
                    if deliveries:
                        break
                    await asyncio.sleep(0.02)
                assert actor._server.ready.is_set()
                assert len(deliveries) == 1
                url, payload = deliveries[0]
                assert url == operational_url + "?wait=true"
                assert payload["allowed_mentions"] == {"parse": []}
                assert payload["embeds"][0]["title"] == "Markeitech | Dashboard ready to view"
                assert f"http://127.0.0.1:{config.port}" in payload["embeds"][0]["description"]
                # Multiple projection intervals do not repeat the startup announcement.
                await asyncio.sleep(0.25)
                assert len(deliveries) == 1
                async with client.stream("GET", "/api/events") as stream:
                    lines = stream.aiter_lines()
                    assert await anext(lines) == "event: update"
                    assert '"instruments":[]' in await anext(lines)
                    # Stop with an active browser connection, not just idle HTTP.
                    handle.stop()
                    await asyncio.wait_for(task, 10)
        finally:
            handle.stop()
            await task
        assert not actor._server.ready.is_set()
        assert not actor._server._thread.is_alive()
        assert len(deliveries) == 1
        with socket.socket() as sock:
            assert sock.connect_ex(("127.0.0.1", config.port)) != 0

    asyncio.run(run())


def test_ready_notification_is_gated_by_accepting_listener_and_not_socket_binding() -> None:
    from threading import Event

    ready, stopping = Event(), Event()
    published = []
    actor = SimpleNamespace(
        _active=True,
        _ready_announced=False,
        _server_failure_reported=False,
        _server=SimpleNamespace(ready=ready, stopping=stopping, failure=None, epoch=str(uuid4())),
        _policy=DashboardConfig(),
        _display=SimpleNamespace(sequence=0),
        _published_sequence=0,
        publish_signal=lambda name, value: published.append((name, value)),
        log=SimpleNamespace(info=lambda _: None, error=lambda _: None),
    )
    DashboardActor._publish(actor, None)
    assert published == []
    ready.set()
    actor._server.failure = "OSError"
    DashboardActor._publish(actor, None)
    assert published == []
    actor._server.failure = None
    stopping.set()
    DashboardActor._publish(actor, None)
    assert published == []
    stopping.clear()
    DashboardActor._publish(actor, None)
    DashboardActor._publish(actor, None)
    assert len(published) == 1
    assert published[0][0] == DASHBOARD_READY_SIGNAL
    assert DashboardReadyEvent.from_signal_value(published[0][1]).url == "http://127.0.0.1:8765"


def test_discord_deduplicates_dashboard_ready_and_rejects_untrusted_address() -> None:
    submitted, errors = [], []
    actor = SimpleNamespace(
        _operational_worker=SimpleNamespace(submit=lambda item: submitted.append(item) or True),
        _dashboard_ready_epoch=None,
        log=SimpleNamespace(error=errors.append),
    )
    event = DashboardReadyEvent(server_epoch=str(uuid4()), port=9876)
    signal = SimpleNamespace(value=event.to_signal_value())
    DiscordHealthActor._handle_dashboard_ready(actor, signal)
    DiscordHealthActor._handle_dashboard_ready(actor, signal)
    assert len(submitted) == 1
    assert submitted[0].state == "DASHBOARD_READY"
    assert "http://127.0.0.1:9876" in json.loads(submitted[0].body)["embeds"][0]["description"]
    tampered = json.loads(event.to_signal_value())
    tampered["url"] = "https://untrusted.invalid"
    DiscordHealthActor._handle_dashboard_ready(actor, SimpleNamespace(value=json.dumps(tampered)))
    assert len(errors) == 1 and len(submitted) == 1
    actor._operational_worker = None
    DiscordHealthActor._handle_dashboard_ready(actor, signal)
    assert len(submitted) == 1


def test_stream_conflates_updates_bounds_clients_and_resets_on_reconnect() -> None:
    async def run() -> None:
        display = state()
        config = replace(
            display.config, port=free_port(), maximum_clients=1, publish_interval_ms=100
        )
        server = DashboardServer(config, display.snapshot())
        server.start()

        async def next_update(lines):  # noqa: ANN001, ANN202
            async for line in lines:
                if line.startswith("data: "):
                    return json.loads(line.removeprefix("data: "))
            pytest.fail("stream ended before update")

        try:
            async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{config.port}") as client:
                for _attempt in range(50):
                    try:
                        await client.get("/api/snapshot")
                        break
                    except httpx.ConnectError:
                        await asyncio.sleep(0.05)
                async with client.stream(
                    "GET", "/api/events", params={"instrument_id": ID}
                ) as response:
                    lines = response.aiter_lines()
                    first = await next_update(lines)
                    assert first["reset"] and first["candles"] == []
                    assert (await client.get("/api/events")).status_code == 503
                    for offset in (0, 5, 10):
                        display.observe_bar(bar(1_800_000_000_000_000_000 + offset * 1_000_000_000))
                        server.publish(display.snapshot())
                    assert server._mailbox.qsize() == 1
                    update = await next_update(lines)
                    assert not update["reset"]
                    assert len(update["candles"]) == 2
                    assert update["window_start"] == 1_800_000_005
                    display.observe_bar(bar(1_800_000_015_000_000_000))
                    server.publish(display.snapshot())
                    update = await next_update(lines)
                    assert len(update["candles"]) == 1
                    assert update["window_start"] == 1_800_000_010
                for _attempt in range(50):
                    if server._clients == 0:
                        break
                    await asyncio.sleep(0.02)
                async with client.stream(
                    "GET", "/api/events", params={"instrument_id": ID}
                ) as response:
                    reset = await next_update(response.aiter_lines())
                    assert reset["reset"]
                    assert len(reset["candles"]) == 2
                    assert reset["epoch"] == first["epoch"]
        finally:
            assert server.stop()

    asyncio.run(run())


class _OfflineAcquisition(DataAcquisitionActor):
    """Release readiness without providers; exercise native consumer attachment only."""

    def on_start(self) -> None:
        self._coordinator = AcquisitionCoordinator(_Port())
        super().on_start()
        self._startup_released = True


def test_native_acquisition_timer_attaches_other_actor_callbacks_without_nested_borrow() -> None:
    async def run() -> None:
        config = load_system_config(ROOT / "config/system.example.toml")
        dashboard = DashboardActor(
            DashboardActorConfig(
                dashboard=asdict(DashboardConfig(port=free_port())),
                watchlist_enabled=False,
            )
        )
        acquisition = _OfflineAcquisition(
            DataAcquisitionActorConfig(instrument_ids=[], historical=asdict(config.historical))
        )
        acquisition.bind_dashboard_consumer(dashboard, {(ID, "bars"), (ID, "quotes")}, 100)
        requests = [DashboardDemand(ID, kind) for kind in ("bars", "quotes")]
        acquisition._dashboard_desired = {item.demand_id: item for item in requests}
        node = (
            LiveNode.builder(
                "DASHBOARD-NATIVE-ATTACH",
                TraderId.from_str("DASHBOARD-TEST-002"),
                Environment.SANDBOX,
            )
            .with_delay_post_stop_secs(0)
            .build()
        )
        node.add_actor(acquisition)
        node.add_actor(dashboard)
        task = asyncio.create_task(node.run_async())
        try:
            for _attempt in range(60):
                if len(acquisition._dashboard_attached) == 2:
                    break
                await asyncio.sleep(0.05)
            assert set(acquisition._dashboard_attached) == {item.demand_id for item in requests}
            acquisition._dashboard_desired.clear()
            for _attempt in range(60):
                if not acquisition._dashboard_attached:
                    break
                await asyncio.sleep(0.05)
            assert not acquisition._dashboard_attached
            assert not acquisition._coordinator.demands
        finally:
            node.handle().stop()
            await task

    asyncio.run(run())


def test_port_conflict_stays_inside_dashboard_worker() -> None:
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        config = DashboardConfig(port=occupied.getsockname()[1])
        server = DashboardServer(config, state().snapshot())
        server.start()
        deadline = time.monotonic() + 2
        while server.failure is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.failure == "OSError"
        assert server.stop()
