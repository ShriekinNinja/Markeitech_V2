from dataclasses import asdict
from types import SimpleNamespace

from markeitech.acquisition import HISTORICAL_EXECUTION_SIGNAL, HistoricalExecutionEventMessage
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


def test_early_live_input_keeps_initial_history_and_queues_tail_after_its_ack() -> None:
    actor = DashboardActor(DashboardActorConfig(dashboard=asdict(DashboardConfig())))
    actor._active = True
    actor._display.set_members(MEMBERS)
    actor._queue_history(ID, START + SECOND)
    initial = actor._history_demands[ID]
    actor.on_bar(bar(START + 5 * SECOND))
    assert actor._history_demands[ID] == initial
    assert actor._pending_history_tail[ID] == START + 5 * SECOND
    event = HistoricalExecutionEventMessage(
        event_id="ack",
        request_id="initial",
        state="QUEUED",
        attempt=1,
        instrument_id=ID,
        selector=initial.selector,
        window=initial.window,
        start_ns=START - initial.maximum_observations * 5 * SECOND,
        end_ns=START - 1,
        limit=initial.maximum_observations,
        consumer_ids=("DASHBOARD",),
        occurred_at_ns=START + 6 * SECOND,
        source="DATA-ACQUISITION",
        detail="queued",
    )
    signal = SimpleNamespace(name=HISTORICAL_EXECUTION_SIGNAL, value=event.to_signal_value())
    actor.on_signal(signal)
    tail = actor._history_demands[ID]
    assert tail.maximum_observations == 24 and tail.as_of_ns == START + 5 * SECOND
    assert ID not in actor._history_acknowledged
    actor.on_signal(signal)  # Old initial acknowledgement cannot suppress the tail.
    assert ID not in actor._history_acknowledged
