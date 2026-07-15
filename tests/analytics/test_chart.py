from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from markeitech.analytics import (
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    ContextLevel,
    FairValueGap,
    FairValueGapDirection,
    FeatureInputLineage,
    LevelKind,
    MarketContextFeatureSnapshot,
    MarketContextSnapshot,
    TrendState,
    VolumeProfileSnapshot,
    VwapPosition,
    build_chart_dataset,
    render_analytics_chart,
)
from markeitech.domain import OneMinuteBar

NOW = datetime(2026, 7, 15, 13, 0, tzinfo=UTC)
INSTRUMENT = "NQU6.CME"


def bar(minute: int, *, source: str = "classified_ticks") -> OneMinuteBar:
    open_ts = NOW + timedelta(minutes=minute)
    close_ts = open_ts + timedelta(minutes=1)
    price = Decimal("100") + Decimal(minute) / Decimal("10")
    return OneMinuteBar(
        instrument_id=INSTRUMENT,
        event_ts=close_ts,
        ts_init=close_ts,
        open_ts=open_ts,
        close_ts=close_ts,
        open=price,
        high=price + Decimal("1"),
        low=price - Decimal("1"),
        close=price + Decimal("0.5"),
        volume=Decimal("100"),
        buy_volume=Decimal("60") if source == "classified_ticks" else Decimal("0"),
        sell_volume=Decimal("40") if source == "classified_ticks" else Decimal("0"),
        unknown_volume=Decimal("0") if source == "classified_ticks" else Decimal("100"),
        source=source,
    )


def feature(
    minute: int,
    timeframe: AnalyticsTimeframe,
    *,
    configuration_hash: str = "a" * 64,
) -> MarketContextFeatureSnapshot:
    as_of = NOW + timedelta(minutes=minute)
    snapshot = MarketContextSnapshot(
        instrument_id=INSTRUMENT,
        timeframe=timeframe,
        as_of=as_of,
        source="classified_ticks",
        input_fidelity=AnalyticsInputFidelity.INFERRED,
        bar_count=300,
        close=Decimal("105"),
        ema_20=Decimal("104"),
        ema_50=Decimal("103"),
        ema_200=Decimal("101"),
        atr_14=Decimal("2"),
        session_open=Decimal("100"),
        session_high=Decimal("110"),
        session_low=Decimal("95"),
        session_vwap=Decimal("102"),
        session_range_position=Decimal("0.6"),
        vwap_position=VwapPosition.ABOVE,
        trend=TrendState.BULLISH,
        trend_reason_codes=("test_trend",),
        nearest_support=ContextLevel(
            kind=LevelKind.SWING_SUPPORT,
            price=Decimal("99"),
            observed_ts=as_of,
        ),
        nearest_resistance=ContextLevel(
            kind=LevelKind.SWING_RESISTANCE,
            price=Decimal("109"),
            observed_ts=as_of,
        ),
        prior_session_high=Decimal("108"),
        prior_session_low=Decimal("98"),
        fair_value_gaps=(
            FairValueGap(
                direction=FairValueGapDirection.BULLISH,
                timeframe=timeframe,
                lower=Decimal("100"),
                upper=Decimal("101"),
                detected_ts=as_of - timeframe.duration,
            ),
        ),
        volume_profile=VolumeProfileSnapshot(
            bin_size=Decimal("1"),
            value_area_fraction=Decimal("0.70"),
            poc=Decimal("103"),
            value_area_low=Decimal("100"),
            value_area_high=Decimal("106"),
            total_volume=Decimal("1000"),
            input_fidelity=AnalyticsInputFidelity.INFERRED,
            methodology="test_profile",
        ),
        direction_score=2,
        direction_location_reason_codes=("test_context",),
    )
    return MarketContextFeatureSnapshot(
        configuration_hash=configuration_hash,
        input_lineage=(
            FeatureInputLineage(
                instrument_id=INSTRUMENT,
                timeframe=timeframe,
                source="classified_ticks",
                input_fidelity=AnalyticsInputFidelity.INFERRED,
                start_ts=as_of - timeframe.duration,
                end_ts=as_of,
                event_count=1,
                identity_hash=f"{minute % 10}" * 64,
            ),
        ),
        snapshot=snapshot,
    )


def test_dataset_selects_latest_coherent_features_and_exact_bar_source() -> None:
    bars = tuple(
        [bar(minute) for minute in range(60)] + [bar(minute, source="ib") for minute in range(60)]
    )
    features = tuple(
        [feature(minute + 1, AnalyticsTimeframe.ONE_MINUTE) for minute in range(60)]
        + [feature(60, AnalyticsTimeframe.FIVE_MINUTES)]
        + [
            feature(
                61,
                AnalyticsTimeframe.FIVE_MINUTES,
                configuration_hash="b" * 64,
            )
        ]
    )

    dataset = build_chart_dataset(INSTRUMENT, bars, features, maximum_bars=50)

    assert dataset.as_of == NOW + timedelta(minutes=60)
    assert dataset.source == "classified_ticks"
    assert len(dataset.bars) == 50
    assert {item.source for item in dataset.bars} == {"classified_ticks"}
    assert len(dataset.one_minute_history) == 50
    assert {item.configuration_hash for item in dataset.latest_features} == {"a" * 64}
    assert {item.snapshot.timeframe for item in dataset.latest_features} == {
        AnalyticsTimeframe.ONE_MINUTE,
        AnalyticsTimeframe.FIVE_MINUTES,
    }


def test_renderer_contains_price_volume_ema_levels_and_fvg_annotations() -> None:
    bars = tuple(bar(minute) for minute in range(60))
    features = tuple(
        [feature(minute + 1, AnalyticsTimeframe.ONE_MINUTE) for minute in range(60)]
        + [feature(60, AnalyticsTimeframe.FIVE_MINUTES)]
    )
    figure = render_analytics_chart(
        build_chart_dataset(INSTRUMENT, bars, features, maximum_bars=50)
    )

    assert {trace.name for trace in figure.data} >= {
        "1m price",
        "volume",
        "EMA 20",
        "EMA 50",
        "EMA 200",
    }
    annotations = {item.text for item in figure.layout.annotations}
    assert {"VAL 100", "POC 103", "VAH 106", "VWAP 102"} <= annotations
    assert len(figure.layout.shapes) >= 8
    assert figure.layout.xaxis.rangeslider.visible is False


def test_dataset_refuses_silent_bar_source_fallback() -> None:
    with pytest.raises(ValueError, match="no committed 'classified_ticks' bars"):
        build_chart_dataset(
            INSTRUMENT,
            tuple(bar(minute, source="ib") for minute in range(60)),
            tuple(feature(minute + 1, AnalyticsTimeframe.ONE_MINUTE) for minute in range(60)),
            maximum_bars=50,
        )
