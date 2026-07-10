from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from markeitech.domain import (
    CanonicalQuoteTick,
    CanonicalTradeTick,
    GapSeverity,
    OneMinuteBar,
    ReadinessStatus,
    SourceStatus,
)
from markeitech.market_data import (
    MarketDataHealthMonitor,
    MarketDataHealthPolicy,
    MarketDataStreamStatus,
)

BASE = datetime(2026, 7, 10, 12, tzinfo=UTC)


def trade(instrument_id: str, event_ts: datetime) -> CanonicalTradeTick:
    return CanonicalTradeTick(
        instrument_id=instrument_id,
        event_ts=event_ts,
        ts_init=event_ts,
        price=Decimal("20000.25"),
        size=Decimal("1"),
    )


def quote(instrument_id: str, event_ts: datetime) -> CanonicalQuoteTick:
    return CanonicalQuoteTick(
        instrument_id=instrument_id,
        event_ts=event_ts,
        ts_init=event_ts,
        bid_price=Decimal("20000.00"),
        ask_price=Decimal("20000.50"),
        bid_size=Decimal("2"),
        ask_size=Decimal("3"),
    )


def bar(
    instrument_id: str,
    open_ts: datetime,
    *,
    source: str = "ib",
    is_complete: bool = True,
) -> OneMinuteBar:
    close_ts = open_ts + timedelta(minutes=1)
    return OneMinuteBar(
        instrument_id=instrument_id,
        event_ts=close_ts,
        ts_init=close_ts,
        open_ts=open_ts,
        close_ts=close_ts,
        open=Decimal("20000"),
        high=Decimal("20001"),
        low=Decimal("19999"),
        close=Decimal("20000.50"),
        volume=Decimal("4"),
        buy_volume=Decimal("0"),
        sell_volume=Decimal("0"),
        unknown_volume=Decimal("4"),
        source=source,
        is_complete=is_complete,
    )


def monitor(
    now: list[datetime],
    active: list[str],
    *,
    session_open: bool = True,
    changes: list[object] | None = None,
) -> MarketDataHealthMonitor:
    return MarketDataHealthMonitor(
        instrument_ids={"NQU6.CME", "ESU6.CME"},
        active_instrument_id=lambda: active[0],
        now=lambda: now[0],
        is_session_open=lambda instrument_id, checked_at: session_open,
        policy=MarketDataHealthPolicy(
            tick_stale_after=timedelta(seconds=30),
            bar_stale_after=timedelta(seconds=90),
        ),
        on_change=None if changes is None else changes.append,
    )


def instrument(snapshot: object, instrument_id: str) -> object:
    return next(item for item in snapshot.instruments if item.instrument_id == instrument_id)


def test_initial_health_waits_for_role_required_streams() -> None:
    health = monitor([BASE], ["NQU6.CME"])

    snapshot = health.evaluate()

    assert snapshot.source.status == SourceStatus.CONNECTING
    assert instrument(snapshot, "NQU6.CME").readiness == ReadinessStatus.NOT_READY
    assert len(instrument(snapshot, "NQU6.CME").streams) == 3
    assert instrument(snapshot, "ESU6.CME").readiness == ReadinessStatus.NOT_READY
    assert len(instrument(snapshot, "ESU6.CME").streams) == 1


def test_required_streams_become_healthy_then_stale() -> None:
    now = [BASE]
    health = monitor(now, ["NQU6.CME"])
    for event in (
        quote("NQU6.CME", BASE),
        trade("NQU6.CME", BASE),
        bar("NQU6.CME", BASE - timedelta(minutes=1)),
        bar("ESU6.CME", BASE - timedelta(minutes=1)),
    ):
        health.observe(event)

    healthy = health.evaluate()
    assert healthy.source.status == SourceStatus.HEALTHY
    assert instrument(healthy, "NQU6.CME").readiness == ReadinessStatus.READY
    assert instrument(healthy, "ESU6.CME").readiness == ReadinessStatus.READY

    now[0] += timedelta(seconds=31)
    stale = health.evaluate()

    assert stale.source.status == SourceStatus.DEGRADED
    assert instrument(stale, "NQU6.CME").readiness == ReadinessStatus.DEGRADED
    tick_statuses = {stream.kind: stream.status for stream in instrument(stale, "NQU6.CME").streams}
    assert MarketDataStreamStatus.STALE in tick_statuses.values()
    assert instrument(stale, "ESU6.CME").readiness == ReadinessStatus.READY


def test_role_switch_changes_required_streams_without_losing_bar_health() -> None:
    now = [BASE]
    active = ["NQU6.CME"]
    health = monitor(now, active)
    health.observe(bar("NQU6.CME", BASE - timedelta(minutes=1)))
    health.observe(bar("ESU6.CME", BASE - timedelta(minutes=1)))

    active[0] = "ESU6.CME"
    snapshot = health.evaluate()

    assert instrument(snapshot, "NQU6.CME").readiness == ReadinessStatus.READY
    assert instrument(snapshot, "ESU6.CME").readiness == ReadinessStatus.NOT_READY
    assert "waiting_for_trade_tick" in instrument(snapshot, "ESU6.CME").reason_codes


def test_bar_gap_opens_and_late_bar_recovers_it() -> None:
    now = [BASE]
    health = monitor(now, ["NQU6.CME"])
    health.observe(bar("ESU6.CME", BASE))
    now[0] += timedelta(minutes=3)
    health.observe(bar("ESU6.CME", BASE + timedelta(minutes=3)))

    opened = instrument(health.current, "ESU6.CME").gap
    assert opened.severity == GapSeverity.DEGRADED
    assert opened.missing_intervals == 2

    health.observe(bar("ESU6.CME", BASE + timedelta(minutes=1)))
    health.observe(bar("ESU6.CME", BASE + timedelta(minutes=2)))

    recovered = instrument(health.current, "ESU6.CME").gap
    assert recovered.severity == GapSeverity.NONE
    assert recovered.missing_intervals == 0


def test_tick_built_bars_do_not_mask_external_bar_health() -> None:
    health = monitor([BASE], ["NQU6.CME"])

    health.observe(
        bar(
            "NQU6.CME",
            BASE - timedelta(minutes=1),
            source="classified_ticks",
            is_complete=False,
        )
    )

    snapshot = health.current
    bar_stream = next(
        stream
        for stream in instrument(snapshot, "NQU6.CME").streams
        if stream.kind.value == "bar_1m"
    )
    assert bar_stream.status == MarketDataStreamStatus.WAITING


def test_closed_session_pauses_staleness_and_callbacks_emit_only_transitions() -> None:
    changes: list[object] = []
    health = monitor(
        [BASE],
        ["NQU6.CME"],
        session_open=False,
        changes=changes,
    )

    first = health.evaluate()
    health.evaluate()

    assert len(changes) == 1
    assert instrument(first, "NQU6.CME").readiness == ReadinessStatus.READY
    assert all(
        stream.status == MarketDataStreamStatus.PAUSED
        for stream in instrument(first, "NQU6.CME").streams
    )


def test_late_bar_recovers_gap_without_refreshing_newer_bar_freshness() -> None:
    now = [BASE]
    health = monitor(now, ["NQU6.CME"])
    health.observe(bar("ESU6.CME", BASE))
    now[0] += timedelta(minutes=3)
    health.observe(bar("ESU6.CME", BASE + timedelta(minutes=3)))
    newest_received = next(
        stream
        for stream in instrument(health.current, "ESU6.CME").streams
        if stream.kind.value == "bar_1m"
    ).last_received_ts

    now[0] += timedelta(seconds=30)
    health.observe(bar("ESU6.CME", BASE + timedelta(minutes=1)))

    after_late_bar = next(
        stream
        for stream in instrument(health.current, "ESU6.CME").streams
        if stream.kind.value == "bar_1m"
    )
    assert after_late_bar.last_received_ts == newest_received
