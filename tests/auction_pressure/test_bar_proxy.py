from datetime import UTC, datetime, timedelta
from decimal import Decimal

from markeitech.auction_pressure import (
    BarPressureDirection,
    build_bar_pressure_proxy,
)
from markeitech.domain.market_data import OneMinuteBar

START = datetime(2026, 7, 17, 12, tzinfo=UTC)


def bar(minute: int, *, volume: str) -> OneMinuteBar:
    open_ts = START + timedelta(minutes=minute)
    close_ts = open_ts + timedelta(minutes=1)
    open_price = Decimal("100") + Decimal(minute)
    close_price = open_price + Decimal("0.75")
    observed_volume = Decimal(volume)
    return OneMinuteBar(
        instrument_id="ESU6.CME",
        event_ts=close_ts,
        ts_init=close_ts,
        open_ts=open_ts,
        close_ts=close_ts,
        open=open_price,
        high=close_price + Decimal("0.25"),
        low=open_price - Decimal("0.25"),
        close=close_price,
        volume=observed_volume,
        buy_volume=Decimal("0"),
        sell_volume=Decimal("0"),
        unknown_volume=observed_volume,
        source="ib",
    )


def test_builds_partial_pressure_from_recent_reported_bars() -> None:
    bars = tuple(
        bar(index, volume="100" if index < 10 else "200")
        for index in range(13)
    )

    snapshot = build_bar_pressure_proxy(
        "ESU6.CME",
        bars,
        as_of=bars[-1].close_ts,
        atr=Decimal("10"),
    )

    assert snapshot is not None
    assert snapshot.direction == BarPressureDirection.UPWARD
    assert snapshot.window_bars == 3
    assert snapshot.up_bar_count == 3
    assert snapshot.price_change == Decimal("2.75")
    assert snapshot.atr_fraction == Decimal("0.275")
    assert snapshot.pace_ratio == Decimal("2")


def test_requires_three_contiguous_reported_bars() -> None:
    bars = (bar(0, volume="100"), bar(2, volume="100"), bar(3, volume="100"))

    assert (
        build_bar_pressure_proxy(
            "ESU6.CME",
            bars,
            as_of=bars[-1].close_ts,
            atr=Decimal("10"),
        )
        is None
    )


def test_ignores_classified_tick_bars() -> None:
    bars = tuple(
        bar(index, volume="100").model_copy(update={"source": "classified_ticks"})
        for index in range(3)
    )

    assert (
        build_bar_pressure_proxy(
            "ESU6.CME",
            bars,
            as_of=bars[-1].close_ts,
            atr=Decimal("10"),
        )
        is None
    )
