"""Provider revisions and browser-owned chart demand, without broker connections."""

from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest
from nautilus_trader.model import Bar, BarType, Price, Quantity

from markeitech.acquisition.dashboard_history import _chart_selector
from markeitech.acquisition.minute_candles import CHART_TIMEFRAMES
from markeitech.dashboard.actor import DashboardActor, DashboardActorConfig
from markeitech.dashboard.config import DashboardConfig
from markeitech.dashboard.messages import DashboardDemand
from markeitech.dashboard.server import DashboardServer
from markeitech.dashboard.state import DashboardState
from markeitech.system.config import load_system_config
from markeitech.system.node import build_ib_data_client_config
from tests.dashboard.test_dashboard import ID, MEMBERS, ROOT


def native_bar(frame, opening, close="101.00", volume="20"):
    timestamp = (opening + CHART_TIMEFRAMES[frame]) * 1_000_000_000
    if frame == "1d":
        timestamp -= 1
    return Bar(
        BarType.from_str(f"{ID}-{_chart_selector(frame)}"),
        Price.from_str("100.00"),
        Price.from_str("102.00"),
        Price.from_str("99.00"),
        Price.from_str(close),
        Quantity.from_str(volume),
        timestamp,
        timestamp,
    )


@pytest.mark.parametrize("frame", CHART_TIMEFRAMES)
def test_provider_revisions_replace_same_candle_without_summing_volume(frame):
    display = DashboardState(DashboardConfig(candles_per_instrument=2))
    display.set_members(MEMBERS)
    opening = 1_800_000_000
    display.observe_bar(native_bar(frame, opening))
    display.observe_bar(native_bar(frame, opening, "102.00", "25"))
    rows = display.snapshot()["candles_by_timeframe"][ID][frame]
    assert len(rows) == 1
    assert rows[0]["time"] == opening
    assert rows[0]["close"] == "102.00" and rows[0]["volume"] == "25"
    assert rows[0]["provenance"] == "provider_subscription"
    # Provider timestamps, including session offsets, survive unchanged.
    display.observe_bar(native_bar(frame, opening + CHART_TIMEFRAMES[frame]))
    display.observe_bar(native_bar(frame, opening + 2 * CHART_TIMEFRAMES[frame]))
    assert len(display.snapshot()["candles_by_timeframe"][ID][frame]) == 2
    assert display.snapshot()["instruments"][0]["bar_ts_event_ns"] is None


def test_browser_demand_is_shared_released_and_clears_old_revisions():
    actor = DashboardActor(DashboardActorConfig(dashboard=asdict(DashboardConfig())))
    actor._active = True
    actor._display.set_members(MEMBERS)
    server = actor._server
    published = []
    wrapper = SimpleNamespace(
        _server=server,
        _display=actor._display,
        _demands={},
        publish_signal=lambda _, value: published.append(DashboardDemand.from_signal_value(value)),
    )
    server._chart_clients = {"a": (ID, "1m"), "b": (ID, "1m")}
    server._publish_chart_selections()
    DashboardActor._accept_chart_selections(wrapper)
    assert [(d.action, d.timeframe) for d in published] == [("REQUEST", "1m")]
    actor._display.observe_bar(native_bar("1m", 1_800_000_000))
    del server._chart_clients["a"]
    server._publish_chart_selections()
    DashboardActor._accept_chart_selections(wrapper)
    assert len(published) == 1
    server._chart_clients["b"] = (ID, "4h")
    server._publish_chart_selections()
    DashboardActor._accept_chart_selections(wrapper)
    assert [(d.action, d.timeframe) for d in published[1:]] == [
        ("RELEASE", "1m"),
        ("REQUEST", "4h"),
    ]
    assert actor._display.snapshot()["candles"][ID] == []
    server._chart_clients.clear()
    server._publish_chart_selections()
    DashboardActor._accept_chart_selections(wrapper)
    assert not wrapper._demands and published[-1].action == "RELEASE"


def test_selection_mailbox_conflates_without_losing_final_release():
    worker = DashboardServer(DashboardConfig(), DashboardState(DashboardConfig()).snapshot())
    worker._chart_clients = {"a": (ID, "1m")}
    worker._publish_chart_selections()
    worker._chart_clients.clear()
    worker._publish_chart_selections()
    assert worker.take_chart_selections() == frozenset()
    assert worker.take_chart_selections() is None


def test_dashboard_policy_enables_native_revisions_without_changing_profile():
    config = load_system_config(ROOT / "config/system.example.toml")
    config = replace(config, ib=replace(config.ib, handle_revised_bars=False))
    assert build_ib_data_client_config(config).handle_revised_bars is True
    assert config.ib.handle_revised_bars is False
    disabled = replace(config, dashboard=replace(config.dashboard, enabled=False))
    assert build_ib_data_client_config(disabled).handle_revised_bars is False


def test_history_keeps_off_grid_session_bar_with_nominal_close_after_page_end():
    from uuid import uuid4

    from markeitech.acquisition.dashboard_history import (
        DashboardHistoryRequest,
        project_history_page,
    )
    from tests.dashboard.test_history import batch

    start = 1_800_000_000 // 14400 * 14400
    command = DashboardHistoryRequest(str(uuid4()), ID, start, start + 14400, "4h")
    observation = native_bar("4h", start + 7200)
    page = project_history_page(batch(command, [observation]), command.consumer_id, 1)
    assert [c.time for c in page.candles] == [start + 7200]
