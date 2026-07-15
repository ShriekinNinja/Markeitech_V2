from datetime import UTC, datetime, timedelta
from decimal import Decimal

from markeitech.domain import OneMinuteBar
from markeitech.signals import BoundedAggressionObservationStore

START = datetime(2026, 7, 15, 10, 0, tzinfo=UTC)


def bar(
    minute: int,
    *,
    source: str = "classified_ticks",
    close: Decimal = Decimal("100"),
    is_revision: bool = False,
    is_complete: bool = True,
) -> OneMinuteBar:
    open_ts = START + timedelta(minutes=minute)
    return OneMinuteBar(
        instrument_id="NQU6.CME",
        event_ts=open_ts + timedelta(minutes=1),
        ts_init=open_ts + timedelta(minutes=1, microseconds=1),
        open_ts=open_ts,
        close_ts=open_ts + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("98"),
        close=close,
        volume=Decimal("10"),
        buy_volume=Decimal("6") if source == "classified_ticks" else Decimal("0"),
        sell_volume=Decimal("3") if source == "classified_ticks" else Decimal("0"),
        unknown_volume=Decimal("1") if source == "classified_ticks" else Decimal("10"),
        source=source,
        is_revision=is_revision,
        is_complete=is_complete,
    )


def test_store_retains_independent_committed_source_streams() -> None:
    store = BoundedAggressionObservationStore(3)

    assert store.offer_committed((bar(0), bar(0, source="ib"), object()))

    assert store.bars("NQU6.CME", "classified_ticks") == (bar(0),)
    assert store.bars("NQU6.CME", "ib") == (bar(0, source="ib"),)
    assert store.snapshot.stream_count == 2
    assert store.snapshot.retained_bar_count == 2


def test_store_is_idempotent_and_preserves_durable_bar_on_conflicting_retry() -> None:
    store = BoundedAggressionObservationStore(3)
    original = bar(0)

    assert store.offer_committed((original,))
    assert store.offer_committed((original,))
    assert store.offer_committed((bar(0, close=Decimal("101")),))

    assert store.bars("NQU6.CME", "classified_ticks") == (original,)
    assert store.snapshot.duplicate_bar_count == 1
    assert store.snapshot.conflicting_retry_count == 1


def test_store_ignores_new_receipt_time_for_identical_historical_bar() -> None:
    store = BoundedAggressionObservationStore(3)
    original = bar(0)
    rereceived = original.model_copy(update={"ts_init": original.ts_init + timedelta(days=1)})

    assert store.offer_committed((original,))
    assert store.offer_committed((rereceived,))

    assert store.bars("NQU6.CME", "classified_ticks") == (original,)
    assert store.snapshot.duplicate_bar_count == 1
    assert store.snapshot.conflicting_retry_count == 0


def test_store_bounds_each_stream_by_latest_observation_time() -> None:
    store = BoundedAggressionObservationStore(2)

    assert store.offer_committed((bar(2), bar(0), bar(1)))

    assert store.bars("NQU6.CME", "classified_ticks") == (bar(1), bar(2))
    assert store.snapshot.evicted_bar_count == 1


def test_store_filters_unusable_bars_and_supports_point_in_time_reads() -> None:
    store = BoundedAggressionObservationStore(5)

    assert store.offer_committed(
        (
            bar(0),
            bar(1),
            bar(2, is_revision=True),
            bar(3, is_complete=False),
            bar(4, source="other"),
        )
    )

    assert store.bars(
        "NQU6.CME",
        "classified_ticks",
        through_ts=START + timedelta(minutes=1),
    ) == (bar(0),)
    assert store.snapshot.accepted_bar_count == 2
