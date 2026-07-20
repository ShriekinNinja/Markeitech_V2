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
)
from markeitech.domain.market_data import OneMinuteBar
from markeitech.signals import (
    CommittedMarketContextBundle,
    LocationPolicyConfig,
    LocationQualificationStatus,
    LocationSourceKind,
    LocationSourcePolicyConfig,
    SignalDefinitionConfig,
    SignalDirection,
    SignalEvidenceFidelity,
    SignalLocationZoneKind,
    derive_location_zones,
    intraday_context_definition,
    qualify_location,
)

AS_OF = datetime(2026, 7, 14, 13, 30, tzinfo=UTC)
SESSION_START = datetime(2026, 7, 13, 22, 0, tzinfo=UTC)
INSTRUMENT_ID = "NQU6.CME"


def feature(
    timeframe: AnalyticsTimeframe,
    *,
    as_of: datetime = AS_OF,
    close: Decimal = Decimal("100"),
    atr: Decimal | None = Decimal("10"),
    structural: bool = True,
    support_price: Decimal | None = Decimal("99"),
    resistance_price: Decimal | None = Decimal("101"),
    fvg: bool = True,
    profile: bool = True,
    vwap: bool = True,
    revision: str = "a",
) -> MarketContextFeatureSnapshot:
    support = (
        ContextLevel(
            kind=LevelKind.SWING_SUPPORT,
            price=support_price,
            observed_ts=AS_OF - timedelta(minutes=30),
            touches=2,
        )
        if structural and support_price is not None
        else None
    )
    resistance = (
        ContextLevel(
            kind=LevelKind.SWING_RESISTANCE,
            price=resistance_price,
            observed_ts=AS_OF - timedelta(minutes=30),
            touches=2,
        )
        if structural and resistance_price is not None
        else None
    )
    gaps = (
        (
            FairValueGap(
                direction=FairValueGapDirection.BULLISH,
                timeframe=timeframe,
                lower=Decimal("99"),
                upper=Decimal("101"),
                detected_ts=AS_OF - timedelta(minutes=15),
            ),
            FairValueGap(
                direction=FairValueGapDirection.BEARISH,
                timeframe=timeframe,
                lower=Decimal("99"),
                upper=Decimal("101"),
                detected_ts=AS_OF - timedelta(minutes=10),
            ),
        )
        if fvg
        else ()
    )
    volume_profile = (
        VolumeProfileSnapshot(
            bin_size=Decimal("1"),
            value_area_fraction=Decimal("0.70"),
            poc=Decimal("100"),
            value_area_low=Decimal("99"),
            value_area_high=Decimal("101"),
            total_volume=Decimal("1000"),
            input_fidelity=AnalyticsInputFidelity.INFERRED,
            methodology="bar_range_uniform_volume",
        )
        if profile
        else None
    )
    return MarketContextFeatureSnapshot(
        configuration_hash="a" * 64,
        input_lineage=(
            FeatureInputLineage(
                instrument_id=INSTRUMENT_ID,
                timeframe=timeframe,
                source="ib",
                input_fidelity=AnalyticsInputFidelity.REPORTED,
                start_ts=as_of - timeframe.duration,
                end_ts=as_of,
                event_count=1,
                identity_hash=revision * 64,
            ),
        ),
        snapshot=MarketContextSnapshot(
            instrument_id=INSTRUMENT_ID,
            timeframe=timeframe,
            as_of=as_of,
            source="ib",
            input_fidelity=AnalyticsInputFidelity.REPORTED,
            bar_count=251,
            close=close,
            atr_14=atr,
            session_open=Decimal("98"),
            session_high=Decimal("105"),
            session_low=Decimal("95"),
            session_vwap=Decimal("101") if vwap else None,
            session_range_position=Decimal("0.5"),
            vwap_position=VwapPosition.BELOW,
            trend=TrendState.RANGE,
            trend_reason_codes=("range_test_context",),
            nearest_support=support,
            nearest_resistance=resistance,
            fair_value_gaps=gaps,
            volume_profile=volume_profile,
        ),
    )


def bundle(
    *,
    as_of: datetime = AS_OF,
    close: Decimal = Decimal("100"),
    atr: Decimal | None = Decimal("10"),
    structural: bool = True,
    support_price: Decimal | None = Decimal("99"),
    resistance_price: Decimal | None = Decimal("101"),
    fvg: bool = True,
    profile: bool = True,
    vwap: bool = True,
    timeframes: tuple[AnalyticsTimeframe, ...] = (
        AnalyticsTimeframe.ONE_MINUTE,
        AnalyticsTimeframe.FIVE_MINUTES,
        AnalyticsTimeframe.FIFTEEN_MINUTES,
    ),
    revision: str = "a",
) -> CommittedMarketContextBundle:
    return CommittedMarketContextBundle(
        instrument_id=INSTRUMENT_ID,
        evaluation_as_of=as_of,
        features=tuple(
            feature(
                timeframe,
                as_of=as_of,
                close=close,
                atr=atr,
                structural=structural,
                support_price=support_price,
                resistance_price=resistance_price,
                fvg=fvg,
                profile=profile,
                vwap=vwap,
                revision=revision,
            )
            for timeframe in timeframes
        ),
    )


def test_derives_only_direction_aligned_zones_from_configured_sources() -> None:
    definition = intraday_context_definition()

    long = derive_location_zones(
        bundle(), definition, SignalDirection.LONG, session_start=SESSION_START
    )
    short = derive_location_zones(
        bundle(), definition, SignalDirection.SHORT, session_start=SESSION_START
    )

    assert {zone.zone_kind for zone in long.zones} == {
        SignalLocationZoneKind.SUPPORT,
        SignalLocationZoneKind.BULLISH_FVG,
        SignalLocationZoneKind.VALUE_AREA_LOW,
        SignalLocationZoneKind.SESSION_VWAP,
    }
    assert {zone.zone_kind for zone in short.zones} == {
        SignalLocationZoneKind.RESISTANCE,
        SignalLocationZoneKind.BEARISH_FVG,
        SignalLocationZoneKind.VALUE_AREA_HIGH,
        SignalLocationZoneKind.SESSION_VWAP,
    }
    assert all(zone.direction == SignalDirection.LONG for zone in long.zones)
    assert long.available_source_kinds == frozenset(LocationSourceKind)


def test_session_zones_keep_identity_across_feature_revisions_and_moving_bounds() -> None:
    definition = intraday_context_definition()
    first = derive_location_zones(
        bundle(), definition, SignalDirection.LONG, session_start=SESSION_START
    )
    revised = derive_location_zones(
        bundle(
            as_of=AS_OF + timedelta(minutes=1),
            revision="b",
        ),
        definition,
        SignalDirection.LONG,
        session_start=SESSION_START,
    )
    session_kinds = {
        SignalLocationZoneKind.VALUE_AREA_LOW,
        SignalLocationZoneKind.SESSION_VWAP,
    }

    assert {zone.zone_id for zone in first.zones if zone.zone_kind in session_kinds} == {
        zone.zone_id for zone in revised.zones if zone.zone_kind in session_kinds
    }
    assert {zone.source_feature_id for zone in first.zones if zone.zone_kind in session_kinds} != {
        zone.source_feature_id for zone in revised.zones if zone.zone_kind in session_kinds
    }


def test_qualifies_exact_matches_and_preserves_source_and_evaluation_fidelity() -> None:
    result = qualify_location(
        bundle(),
        intraday_context_definition(),
        SignalDirection.LONG,
        session_start=SESSION_START,
    )

    assert result.status == LocationQualificationStatus.QUALIFIED
    assert {item.zone.source_kind for item in result.matches} == set(LocationSourceKind)
    assert all(item.observed_price == Decimal("100") for item in result.matches)
    profile_match = next(
        item
        for item in result.matches
        if item.zone.source_kind == LocationSourceKind.VALUE_AREA_EDGE
    )
    assert profile_match.zone.fidelity == SignalEvidenceFidelity.INFERRED
    assert profile_match.fidelity == SignalEvidenceFidelity.PARTIAL
    fvg_matches = [
        item
        for item in result.matches
        if item.zone.source_kind == LocationSourceKind.FAIR_VALUE_GAP
    ]
    assert all(item.distance == 0 and item.tolerance == 0 for item in fvg_matches)


def test_partial_matches_can_fail_configured_distinct_source_confluence() -> None:
    definition = intraday_context_definition()
    assert definition.location_policy is not None
    definition = definition.model_copy(
        update={
            "location_policy": definition.location_policy.model_copy(
                update={"minimum_distinct_sources": 2}
            )
        }
    )

    result = qualify_location(
        bundle(fvg=False, profile=False, vwap=False),
        definition,
        SignalDirection.LONG,
        session_start=SESSION_START,
    )

    assert result.status == LocationQualificationStatus.INSUFFICIENT_CONFLUENCE
    assert {item.zone.source_kind for item in result.matches} == {
        LocationSourceKind.STRUCTURAL_LEVEL
    }
    assert result.is_degraded is True


def test_returns_not_at_location_when_sources_exist_but_price_is_outside() -> None:
    result = qualify_location(
        bundle(close=Decimal("130"), structural=False),
        intraday_context_definition(),
        SignalDirection.LONG,
        session_start=SESSION_START,
    )

    assert result.status == LocationQualificationStatus.NOT_AT_LOCATION
    assert result.matches == ()


def test_completed_bar_range_can_touch_location_after_close_has_departed() -> None:
    observed_bar = OneMinuteBar(
        instrument_id=INSTRUMENT_ID,
        event_ts=AS_OF,
        ts_init=AS_OF,
        open_ts=AS_OF - timedelta(minutes=1),
        close_ts=AS_OF,
        open=Decimal("99"),
        high=Decimal("101"),
        low=Decimal("96"),
        close=Decimal("97"),
        volume=Decimal("100"),
        buy_volume=Decimal("0"),
        sell_volume=Decimal("0"),
        unknown_volume=Decimal("100"),
        source="ib",
    )

    result = qualify_location(
        bundle(
            close=Decimal("97"),
            fvg=False,
            profile=False,
            vwap=False,
            support_price=None,
        ),
        intraday_context_definition(),
        SignalDirection.SHORT,
        session_start=SESSION_START,
        evaluation_bar=observed_bar,
    )

    assert result.status == LocationQualificationStatus.QUALIFIED
    assert len(result.matches) == 2
    assert all(item.zone.zone_kind == SignalLocationZoneKind.RESISTANCE for item in result.matches)
    assert all(item.observed_price == Decimal("101") for item in result.matches)
    assert all(item.distance == Decimal("0") for item in result.matches)


def test_missing_current_clock_or_all_sources_fails_closed() -> None:
    definition = intraday_context_definition()
    missing_clock = qualify_location(
        bundle(timeframes=(AnalyticsTimeframe.FIVE_MINUTES,)),
        definition,
        SignalDirection.LONG,
        session_start=SESSION_START,
    )
    no_sources = qualify_location(
        bundle(
            structural=False,
            fvg=False,
            profile=False,
            vwap=False,
            timeframes=(AnalyticsTimeframe.ONE_MINUTE,),
        ),
        definition,
        SignalDirection.LONG,
        session_start=SESSION_START,
    )

    assert missing_clock.status == LocationQualificationStatus.MISSING_EVIDENCE
    assert no_sources.status == LocationQualificationStatus.MISSING_EVIDENCE
    assert no_sources.is_degraded is True


def test_missing_atr_does_not_block_price_already_inside_a_zone() -> None:
    result = qualify_location(
        bundle(atr=None, profile=False, vwap=False),
        intraday_context_definition(),
        SignalDirection.LONG,
        session_start=SESSION_START,
    )

    assert result.status == LocationQualificationStatus.QUALIFIED
    assert {item.zone.source_kind for item in result.matches} == {LocationSourceKind.FAIR_VALUE_GAP}
    assert result.is_degraded is True


def test_alternate_policy_uses_only_its_configured_source_and_timeframe() -> None:
    definition = SignalDefinitionConfig(
        definition_id="alternate_location",
        primary_direction_timeframes=(AnalyticsTimeframe.FIFTEEN_MINUTES,),
        location_policy=LocationPolicyConfig(
            sources=(
                LocationSourcePolicyConfig(
                    source_kind=LocationSourceKind.STRUCTURAL_LEVEL,
                    timeframes=(AnalyticsTimeframe.THIRTY_MINUTES,),
                    proximity_atr_fraction=Decimal("0.2"),
                ),
            )
        ),
    )

    result = qualify_location(
        bundle(
            timeframes=(
                AnalyticsTimeframe.ONE_MINUTE,
                AnalyticsTimeframe.THIRTY_MINUTES,
            )
        ),
        definition,
        SignalDirection.LONG,
        session_start=SESSION_START,
    )

    assert result.status == LocationQualificationStatus.QUALIFIED
    assert {item.zone.timeframe for item in result.matches} == {AnalyticsTimeframe.THIRTY_MINUTES}
    assert all(item.tolerance == Decimal("2") for item in result.matches)


def test_rejects_session_identity_from_the_future() -> None:
    with pytest.raises(ValueError, match="cannot follow evaluation time"):
        derive_location_zones(
            bundle(),
            intraday_context_definition(),
            SignalDirection.LONG,
            session_start=AS_OF + timedelta(minutes=1),
        )


def test_rejects_nested_zone_evidence_newer_than_its_committed_feature() -> None:
    original = feature(AnalyticsTimeframe.FIVE_MINUTES)
    future_gap = FairValueGap(
        direction=FairValueGapDirection.BULLISH,
        timeframe=AnalyticsTimeframe.FIVE_MINUTES,
        lower=Decimal("99"),
        upper=Decimal("101"),
        detected_ts=AS_OF + timedelta(minutes=1),
    )
    corrupt_snapshot = original.snapshot.model_copy(update={"fair_value_gaps": (future_gap,)})
    corrupt_feature = original.model_copy(update={"snapshot": corrupt_snapshot})
    evaluation = feature(AnalyticsTimeframe.ONE_MINUTE)
    committed = CommittedMarketContextBundle(
        instrument_id=INSTRUMENT_ID,
        evaluation_as_of=AS_OF,
        features=(evaluation, corrupt_feature),
    )

    with pytest.raises(ValueError, match="cannot follow source feature"):
        derive_location_zones(
            committed,
            intraday_context_definition(),
            SignalDirection.LONG,
            session_start=SESSION_START,
        )
