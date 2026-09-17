"""Source-time intraday aggregation and timeframe-isolated HTTP history contracts."""

from dataclasses import asdict, replace
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from nautilus_trader.model import Bar, BarType

from markeitech.acquisition.dashboard_history import DashboardHistoryRequest, project_history_page
from markeitech.acquisition.minute_candles import INTRADAY_TIMEFRAMES, _MinuteCandleBook
from markeitech.dashboard.actor import DashboardActor, DashboardActorConfig
from markeitech.dashboard.config import DashboardConfig
from markeitech.dashboard.server import DashboardServer
from markeitech.dashboard.state import DashboardState
from tests.dashboard.test_dashboard import ID, MEMBERS, bar
from tests.dashboard.test_history import batch

SECOND = 1_000_000_000
START = 1_800_000_000  # Whole UTC hour.


@pytest.mark.parametrize("timeframe,seconds", INTRADAY_TIMEFRAMES.items())
def test_forming_and_complete_candles_use_exact_source_coverage(timeframe, seconds):
    book = _MinuteCandleBook({ID}, 120)
    samples = [bar((START + i * 5) * SECOND) for i in range(1, seconds // 5 + 1)]
    for observation in samples[:-1]:
        book.observe(observation)
    forming = book.snapshot(ID, 1, timeframe).candles[0]
    assert forming.status == "FORMING"
    assert forming.time == START
    assert forming.input_count == seconds // 5 - 1
    book.observe(samples[-1])
    completed = book.snapshot(ID, 2, timeframe).candles[0]
    assert completed.status == "COMPLETE"
    assert completed.ts_event_ns == str((START + seconds) * SECOND)
    assert Decimal(completed.volume) == sum(Decimal(str(b.volume)) for b in samples)
    assert completed.open == str(samples[0].open)
    assert completed.close == str(samples[-1].close)
    # The source exactly at the close belongs to the old bar; the next one starts a new bar.
    book.observe(bar((START + seconds + 5) * SECOND))
    assert [c.time for c in book.snapshot(ID, 3, timeframe).candles] == [START, START + seconds]
    assert book.snapshot(ID, 3, timeframe).candles[-1].status == "FORMING"


def test_missing_constituent_stays_incomplete_until_history_repairs_it_without_overlap():
    book = _MinuteCandleBook({ID}, 120)
    for i in range(2, 61):
        book.observe(bar((START + i * 5) * SECOND))
    assert book.snapshot(ID, 1, "5m").candles[0].status == "INCOMPLETE"
    book.observe(bar((START + 5) * SECOND), historical=True)
    before = book.snapshot(ID, 2, "5m").candles[0]
    book.observe(bar((START + 10) * SECOND), historical=True)
    after = book.snapshot(ID, 3, "5m").candles[0]
    assert after.status == "COMPLETE" and after.input_count == 60
    assert after.volume == before.volume
    assert after.historical_inputs == 1 and after.live_inputs == 59


def test_retained_minute_capacity_does_not_claim_a_complete_partial_hour():
    book = _MinuteCandleBook({ID}, 2)
    for i in range(1, 721):
        book.observe(bar((START + i * 5) * SECOND))
    candle = book.snapshot(ID, 1, "1h").candles[0]
    assert candle.status == "INCOMPLETE" and candle.input_count == 24
    assert len(book._buckets[ID]) == 2


def test_http_timeframe_selection_does_not_leak_other_projections():
    config = DashboardConfig()
    display = DashboardState(config)
    display.set_members(MEMBERS)
    book = _MinuteCandleBook({ID}, 120)
    for i in range(1, 61):
        book.observe(bar((START + i * 5) * SECOND))
    for update in book._snapshots(ID, 1):
        display.observe_candles(update)
    worker = DashboardServer(config, display.snapshot())
    with TestClient(worker.app, base_url="http://127.0.0.1:8765") as client:
        minute = client.get(f"/api/snapshot?instrument_id={ID}").json()
        five = client.get(f"/api/snapshot?instrument_id={ID}&timeframe=5m").json()
        assert len(minute["candles"]) == 5 and len(five["candles"]) == 1
        assert five["timeframe"] == "5m" and five["timeframe_seconds"] == 300
        assert "candles_by_timeframe" not in five
        assert client.get("/api/snapshot?timeframe=4h").status_code == 422


def test_history_keeps_timeframe_identity_through_compiler_projection_and_delivery():
    command = DashboardHistoryRequest(str(uuid4()), ID, START, START + 300, "5m")
    source = bar((START + 300) * SECOND)
    observations = [
        Bar(
            BarType.from_str(f"{ID}-5-MINUTE-LAST-EXTERNAL"),
            source.open,
            source.high,
            source.low,
            source.close,
            source.volume,
            source.ts_event,
            source.ts_init,
        )
    ]
    native = batch(command, observations)
    page = project_history_page(native, command.consumer_id, 1)
    assert page.timeframe == "5m" and len(page.candles) == 1
    assert page.candles[0].status == "COMPLETE"
    actor = DashboardActor(DashboardActorConfig(dashboard=asdict(DashboardConfig())))
    actor._active = True
    actor._page_requests[command.consumer_id] = (command, 1, True)
    actor.on_data(replace(page, timeframe="1m"))
    assert command.consumer_id in actor._page_requests
    actor.on_data(page)
    assert not actor._page_requests
    assert actor._server._history_results.get_nowait()["timeframe"] == "5m"
    with pytest.raises(ValueError, match="timeframe boundaries"):
        replace(command, start=START + 60)


@pytest.mark.parametrize("timeframe,seconds", INTRADAY_TIMEFRAMES.items())
def test_two_hundred_selected_candles_use_native_history_not_five_second_inputs(timeframe, seconds):
    command = DashboardHistoryRequest(str(uuid4()), ID, START - 200 * seconds, START, timeframe)
    compiled = batch(command, ()).request
    assert compiled.limit == 200
    assert compiled.end_ns + 1 - compiled.start_ns == 200 * seconds * SECOND
    assert compiled.selector == command.selector
    assert compiled.selector != "5-SECOND-LAST-EXTERNAL"
    observations = []
    for index in range(1, 201):
        source = bar((command.start + index * seconds) * SECOND)
        observations.append(
            Bar(
                BarType.from_str(f"{ID}-{command.selector}"),
                source.open,
                source.high,
                source.low,
                source.close,
                source.volume,
                source.ts_event,
                source.ts_init,
            )
        )
    page = project_history_page(batch(command, observations), command.consumer_id, 1)
    assert len(page.candles) == 200
    assert page.candles[0].time == command.start
    assert page.candles[-1].time == command.end - seconds


def test_legacy_dashboard_config_migrates_without_rewriting_local_profile():
    original = {"policy_version": 3, "history_page_minutes": 60, "initial_history_minutes": 20}
    config = DashboardConfig.from_mapping(original)
    assert config.policy_version == 4 and config.history_page_candles == 60
    assert config.initial_history_candles == 200
    assert config.source_history_count == 61 * 12
    assert original["policy_version"] == 3
    with pytest.raises(ValueError):
        DashboardConfig(history_page_candles=1001)


def test_hour_history_http_accepts_candle_count_window_and_enforces_budget():
    display = DashboardState(DashboardConfig())
    display.set_members(MEMBERS)
    worker = DashboardServer(DashboardConfig(), display.snapshot())
    with TestClient(worker.app, base_url="http://127.0.0.1:8765") as client:
        payload = {
            "instrument_id": ID,
            "start": 1_600_002_000 - 200 * 3600,
            "end": 1_600_002_000,
            "timeframe": "1h",
        }
        assert client.post("/api/history", json=payload).status_code == 202
        assert (
            client.post(
                "/api/history", json={**payload, "start": payload["start"] - 3600}
            ).status_code
            == 422
        )


def test_provider_alignment_failure_reaches_browser_without_waiting_for_timeout():
    from types import SimpleNamespace

    from markeitech.acquisition.dashboard_history import DashboardHistoryPage
    from markeitech.system.acquisition import DataAcquisitionActor

    command = DashboardHistoryRequest(str(uuid4()), ID, START, START + 3600, "1h")
    source = bar((START + 1800) * SECOND)
    observation = Bar(
        BarType.from_str(f"{ID}-{command.selector}"),
        source.open,
        source.high,
        source.low,
        source.close,
        source.volume,
        source.ts_event,
        source.ts_init,
    )
    actor = DashboardActor(DashboardActorConfig(dashboard=asdict(DashboardConfig())))
    actor._active = True
    actor._page_requests[command.consumer_id] = (command, 1, True)
    pages = []

    def publish(_type, data):
        if isinstance(data.data, DashboardHistoryPage):
            pages.append(data.data)
            actor.on_data(data)

    acquisition = SimpleNamespace(
        _minute_book=_MinuteCandleBook({ID}, 120),
        _dashboard_allowed={(ID, "bars")},
        clock=SimpleNamespace(timestamp_ns=lambda: 1),
        log=SimpleNamespace(error=lambda _message: None),
        publish_data=publish,
    )
    native_batch = batch(command, [observation])
    native_batch.ts_event = source.ts_event
    native_batch.ts_init = source.ts_init
    update = SimpleNamespace(events=(), batches=(native_batch,), results=())
    DataAcquisitionActor._publish_historical_update(acquisition, update)
    assert pages[0].status == "FAILED"
    assert not actor._page_requests
    result = actor._server._history_results.get_nowait()
    assert result["status"] == "FAILED" and result["candles"] == ()
    assert "contract" in result["detail"]
