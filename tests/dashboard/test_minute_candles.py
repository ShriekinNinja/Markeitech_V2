from dataclasses import asdict

from markeitech.acquisition.minute_candles import _MinuteCandleBook
from markeitech.dashboard.actor import DashboardActor, DashboardActorConfig
from markeitech.dashboard.config import DashboardConfig
from markeitech.dashboard.state import DashboardState
from tests.dashboard.test_dashboard import ID, MEMBERS, bar

SECOND = 1_000_000_000
START = 1_800_000_000 * SECOND


def test_minute_waits_for_boundary_source_and_preserves_its_event_time() -> None:
    book = _MinuteCandleBook({ID}, 2)
    for i in range(1, 12):
        book.observe(bar(START + i * 5 * SECOND))
    forming = book.snapshot(ID, START + 60 * SECOND + 300_000_000).candles[-1]
    assert forming.status == "FORMING"
    assert forming.input_count == 11
    assert forming.time == START // SECOND
    assert forming.volume == "110"
    # Delivery is late, but the provider event timestamp still closes this minute.
    book.observe(bar(START + 60 * SECOND, "100.75"))
    closed = book.snapshot(ID, START + 60 * SECOND + 400_000_000).candles[-1]
    assert closed.status == "COMPLETE"
    assert closed.close == "100.75" and closed.volume == "120"
    book.observe(bar(START + 65 * SECOND, "100.50"))
    candles = book.snapshot(ID, START + 66 * SECOND).candles
    assert candles[0] == closed
    assert candles[1].status == "FORMING" and candles[1].volume == "10"


def test_out_of_order_boundary_input_repairs_only_its_minute_without_filling_gaps() -> None:
    book = _MinuteCandleBook({ID}, 3)
    for i in range(1, 12):
        book.observe(bar(START + i * 5 * SECOND))
    book.observe(bar(START + 65 * SECOND))
    assert book.snapshot(ID, START + 66 * SECOND).candles[0].status == "INCOMPLETE"
    book.observe(bar(START + 60 * SECOND))
    assert book.snapshot(ID, START + 67 * SECOND).candles[0].status == "COMPLETE"
    book.observe(bar(START + 245 * SECOND))
    assert [c.time for c in book.snapshot(ID, START + 246 * SECOND).candles] == [
        START // SECOND,
        START // SECOND + 60,
        START // SECOND + 240,
    ]


def test_backfill_merges_with_live_without_double_volume_or_overwriting_live() -> None:
    book = _MinuteCandleBook({ID}, 2)
    book.observe(bar(START + 60 * SECOND, "100.75"))
    for i in range(1, 13):
        book.observe(bar(START + i * 5 * SECOND), historical=True)
    result = book.snapshot(ID, START + 61 * SECOND)
    candle = result.candles[-1]
    assert candle.status == "COMPLETE" and candle.volume == "120"
    assert candle.close == "100.75"
    assert candle.live_inputs == 1 and candle.historical_inputs == 11
    assert result.conflicts == 1
    book.observe(bar(START + 60 * SECOND, "100.75"))
    assert book.snapshot(ID, START + 62 * SECOND).candles == result.candles


def test_old_history_cannot_evict_new_buckets_and_misaligned_sources_are_rejected() -> None:
    book = _MinuteCandleBook({ID}, 2)
    for offset in (65, 125, 185, 5):
        book.observe(bar(START + offset * SECOND))
    book.observe(bar(START + 186 * SECOND))
    update = book.snapshot(ID, START + 190 * SECOND)
    assert len(update.candles) == 2
    assert update.candles[0].time == START // SECOND + 120
    assert update.rejected_inputs == 1


def test_display_projects_acquisition_candles_without_aggregating_native_bars() -> None:
    display = DashboardState(DashboardConfig())
    display.set_members(MEMBERS)
    source = bar(START + 5 * SECOND)
    display.observe_bar(source)
    assert display.snapshot()["candles"][ID] == []
    book = _MinuteCandleBook({ID}, 2)
    book.observe(source)
    update = book.snapshot(ID, START + 6 * SECOND)
    display.observe_candles(update)
    assert display.snapshot()["candles"][ID] == [asdict(update.candles[0])]


def test_history_populates_last_without_waiting_for_live_delivery() -> None:
    display = DashboardState(DashboardConfig())
    display.set_members(MEMBERS)
    book = _MinuteCandleBook({ID}, 2)
    book.observe(bar(START + 5 * SECOND), historical=True)
    display.observe_candles(book.snapshot(ID, START + 20 * SECOND))
    row = display.snapshot()["instruments"][0]
    assert row["last"] == "100.25"
    assert row["bar_ts_event_ns"] == str(START + 5 * SECOND)
    display.observe_bar(bar(START + 5 * SECOND))
    assert display.snapshot()["instruments"][0]["rejected_bars"] == 0
    display.observe_bar(bar(START + 5 * SECOND))
    assert display.snapshot()["instruments"][0]["rejected_bars"] == 1


def test_watchlist_source_does_not_start_derived_chart_warmup() -> None:
    actor = DashboardActor(DashboardActorConfig(dashboard=asdict(DashboardConfig())))
    actor._active = True
    actor._display.set_members(MEMBERS)
    actor.on_bar(bar(START + 5 * SECOND))
    assert not actor._page_requests
    assert actor._display.snapshot()["candles"][ID] == []
    assert actor._display.snapshot()["instruments"][0]["last"] == "100.25"
