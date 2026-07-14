from datetime import UTC, datetime
from decimal import Decimal

import pytest
from markeitech.analytics import (
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    FairValueGap,
    FairValueGapDirection,
    MarketContextSnapshot,
    TrendState,
    VwapPosition,
)
from markeitech.market_data.operator_context import OperatorContextReporter


def context(
    instrument_id: str,
    timeframe: AnalyticsTimeframe,
    *,
    close: str,
    trend: TrendState,
) -> MarketContextSnapshot:
    return MarketContextSnapshot(
        instrument_id=instrument_id,
        timeframe=timeframe,
        as_of=datetime(2026, 7, 14, 12, tzinfo=UTC),
        source="ib",
        input_fidelity=AnalyticsInputFidelity.REPORTED,
        bar_count=220,
        close=Decimal(close),
        session_open=Decimal("24900"),
        session_high=Decimal("25100"),
        session_low=Decimal("24800"),
        session_vwap=Decimal("24975"),
        session_range_position=Decimal("0.75"),
        vwap_position=VwapPosition.ABOVE,
        trend=trend,
        trend_reason_codes=("test",),
        direction_score=1,
    )


def test_report_is_active_first_top_down_and_bounded_per_instrument() -> None:
    reporter = OperatorContextReporter()
    snapshots = (
        context(
            "ESU6.CME",
            AnalyticsTimeframe.ONE_MINUTE,
            close="6300",
            trend=TrendState.RANGE,
        ),
        context(
            "NQU6.CME",
            AnalyticsTimeframe.FIVE_MINUTES,
            close="25010",
            trend=TrendState.BULLISH,
        ),
        context(
            "NQU6.CME",
            AnalyticsTimeframe.DAILY,
            close="25000",
            trend=TrendState.BEARISH,
        ),
    )

    lines = reporter.render(
        snapshots,
        active_instrument_id="NQU6.CME",
        phase="warmup",
        force=True,
    )

    assert len(lines) == 6
    assert all("NQU6.CME" in line for line in lines[:3])
    assert all("role=ACTIVE" in line for line in lines[:3])
    assert all("ESU6.CME" in line for line in lines[3:])
    assert all("role=BACKGROUND" in line for line in lines[3:])
    assert "TREND[1d=BEARISH 5m=BULLISH]" in lines[0]
    assert lines[1].startswith("OPERATOR_LEVELS")
    assert lines[2].startswith("OPERATOR_AUCTION")
    assert "OR[L15=n/a L30=n/a NY15=n/a NY30=n/a]" in lines[2]


def test_live_report_suppresses_unchanged_instruments_and_emits_changes() -> None:
    reporter = OperatorContextReporter()
    original = context(
        "NQU6.CME",
        AnalyticsTimeframe.ONE_MINUTE,
        close="25000",
        trend=TrendState.BULLISH,
    )
    reporter.render(
        (original,),
        active_instrument_id="NQU6.CME",
        phase="warmup",
        force=True,
    )

    assert (
        reporter.render(
            (original,),
            active_instrument_id="NQU6.CME",
            phase="live",
        )
        == ()
    )

    changed = original.model_copy(update={"close": Decimal("25001")})
    lines = reporter.render(
        (changed,),
        active_instrument_id="NQU6.CME",
        phase="live",
    )

    assert len(lines) == 3
    assert "price=25001" in lines[0]


def test_role_change_is_reportable_even_when_market_values_are_unchanged() -> None:
    reporter = OperatorContextReporter()
    snapshot = context(
        "ESU6.CME",
        AnalyticsTimeframe.ONE_MINUTE,
        close="6300",
        trend=TrendState.RANGE,
    )
    reporter.render(
        (snapshot,),
        active_instrument_id="NQU6.CME",
        phase="live",
        force=True,
    )

    lines = reporter.render(
        (snapshot,),
        active_instrument_id="ESU6.CME",
        phase="live",
    )

    assert len(lines) == 3
    assert "role=ACTIVE" in lines[0]


def test_auction_report_selects_fvgs_nearest_to_price() -> None:
    reporter = OperatorContextReporter()
    snapshot = context(
        "NQU6.CME",
        AnalyticsTimeframe.FIVE_MINUTES,
        close="25000",
        trend=TrendState.RANGE,
    ).model_copy(
        update={
            "fair_value_gaps": tuple(
                FairValueGap(
                    direction=FairValueGapDirection.BULLISH,
                    timeframe=AnalyticsTimeframe.FIVE_MINUTES,
                    lower=Decimal(lower),
                    upper=Decimal(upper),
                    detected_ts=datetime(2026, 7, 14, 11, index, tzinfo=UTC),
                )
                for index, (lower, upper) in enumerate(
                    (("24000", "24010"), ("24990", "24995"), ("25005", "25010"))
                )
            )
        }
    )

    lines = reporter.render(
        (snapshot,),
        active_instrument_id="NQU6.CME",
        phase="live",
        force=True,
    )

    assert "5m=bullish:24990-24995,bullish:25005-25010" in lines[2]
    assert "24000-24010" not in lines[2]


def test_report_rejects_unknown_phase() -> None:
    with pytest.raises(ValueError, match="unsupported operator context phase"):
        OperatorContextReporter().render(
            (),
            active_instrument_id="NQU6.CME",
            phase="replay",
        )
