from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from markeitech.auction_pressure import (
    AuctionPressureFidelity,
    SessionAuctionPressureAccumulator,
)
from markeitech.domain.market_data import (
    CanonicalTradeTick,
    ClassifiedTrade,
    TradeSide,
)

SESSION_START = datetime(2026, 7, 17, 1, tzinfo=UTC)


class DailySessionResolver:
    def session_window(self, instrument_id: str, timestamp: datetime) -> tuple[datetime, datetime]:
        del instrument_id
        start = timestamp.replace(hour=1, minute=0, second=0, microsecond=0)
        if timestamp < start:
            start -= timedelta(days=1)
        return start, start + timedelta(hours=23)


def classified_trade(
    minute: int,
    side: TradeSide,
    *,
    size: str = "2",
    sequence: int | None = None,
    second: int = 0,
) -> ClassifiedTrade:
    event_ts = SESSION_START + timedelta(minutes=minute, seconds=second)
    trade = CanonicalTradeTick(
        instrument_id="NQU6.CME",
        event_ts=event_ts,
        ts_init=event_ts,
        price=Decimal("30000"),
        size=Decimal(size),
        sequence=sequence,
    )
    reason = {
        TradeSide.BUY: "at_or_above_ask",
        TradeSide.SELL: "at_or_below_bid",
        TradeSide.UNKNOWN: "no_quote_available",
    }[side]
    return ClassifiedTrade(
        instrument_id=trade.instrument_id,
        event_ts=event_ts,
        ts_init=event_ts,
        trade=trade,
        side=side,
        classification_reason=reason,
    )


def accumulator() -> SessionAuctionPressureAccumulator:
    return SessionAuctionPressureAccumulator("NQU6.CME", DailySessionResolver())


def test_accumulates_conserved_volume_delta_ratio_and_session_cvd() -> None:
    subject = accumulator()

    subject.observe(classified_trade(0, TradeSide.BUY, size="5", sequence=1))
    subject.observe(classified_trade(1, TradeSide.SELL, size="2", sequence=2))
    snapshot = subject.observe(classified_trade(2, TradeSide.UNKNOWN, size="3", sequence=3))

    assert snapshot.trade_count == 3
    assert snapshot.classified_trade_count == 2
    assert snapshot.unknown_trade_count == 1
    assert snapshot.total_volume == Decimal("10")
    assert snapshot.classified_volume == Decimal("7")
    assert snapshot.classified_volume_ratio == Decimal("0.7")
    assert snapshot.delta == Decimal("3")
    assert snapshot.cvd == Decimal("3")
    assert snapshot.delta_ratio == Decimal("3") / Decimal("7")
    assert snapshot.fidelity == AuctionPressureFidelity.PARTIAL


def test_all_unknown_volume_makes_directional_pressure_unavailable() -> None:
    snapshot = accumulator().observe(classified_trade(0, TradeSide.UNKNOWN))

    assert snapshot.delta == 0
    assert snapshot.delta_ratio is None
    assert snapshot.fidelity == AuctionPressureFidelity.UNAVAILABLE


def test_complete_inferred_classification_retains_inferred_fidelity() -> None:
    snapshot = accumulator().observe(classified_trade(0, TradeSide.BUY))

    assert snapshot.classified_volume_ratio == 1
    assert snapshot.fidelity == AuctionPressureFidelity.INFERRED


def test_duplicate_and_stale_trades_do_not_change_pressure_totals() -> None:
    subject = accumulator()
    latest = classified_trade(2, TradeSide.BUY, sequence=3)
    subject.observe(latest)

    duplicate = subject.observe(latest)
    stale = subject.observe(classified_trade(1, TradeSide.SELL, sequence=2))

    assert duplicate.trade_count == 1
    assert duplicate.duplicate_count == 1
    assert stale.trade_count == 1
    assert stale.stale_count == 1
    assert stale.delta == Decimal("2")


def test_sequence_gap_degrades_fidelity_without_fabricating_volume() -> None:
    subject = accumulator()
    subject.observe(classified_trade(0, TradeSide.BUY, sequence=10))

    snapshot = subject.observe(classified_trade(1, TradeSide.SELL, sequence=13))

    assert snapshot.sequence_gap_count == 2
    assert snapshot.total_volume == Decimal("4")
    assert snapshot.fidelity == AuctionPressureFidelity.PARTIAL


def test_new_product_session_resets_cvd_and_accounting() -> None:
    subject = accumulator()
    subject.observe(classified_trade(0, TradeSide.BUY, size="5", sequence=1))

    snapshot = subject.observe(classified_trade(24 * 60, TradeSide.SELL, sequence=1))

    assert snapshot.session_start == SESSION_START + timedelta(days=1)
    assert snapshot.trade_count == 1
    assert snapshot.cvd == Decimal("-2")
    assert snapshot.duplicate_count == 0
    assert snapshot.stale_count == 0


def test_rejects_wrong_instrument_and_invalid_session_window() -> None:
    subject = accumulator()
    wrong = classified_trade(0, TradeSide.BUY).model_copy(update={"instrument_id": "ESU6.CME"})

    with pytest.raises(ValueError, match="does not match"):
        subject.observe(wrong)

    wrong_source = classified_trade(0, TradeSide.BUY)
    wrong_source = wrong_source.model_copy(
        update={"trade": wrong_source.trade.model_copy(update={"source": "other"})}
    )
    with pytest.raises(ValueError, match="source"):
        subject.observe(wrong_source)

    class InvalidResolver:
        def session_window(
            self,
            instrument_id: str,
            timestamp: datetime,
        ) -> tuple[datetime, datetime]:
            del instrument_id
            return timestamp + timedelta(minutes=1), timestamp + timedelta(minutes=2)

    invalid = SessionAuctionPressureAccumulator("NQU6.CME", InvalidResolver())
    with pytest.raises(ValueError, match="excludes the trade"):
        invalid.observe(classified_trade(0, TradeSide.BUY))
