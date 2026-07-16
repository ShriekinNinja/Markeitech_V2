from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from markeitech.analytics import (
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    FeatureInputLineage,
    MarketContextFeatureSnapshot,
    MarketContextSnapshot,
    ProfileLocation,
    TrendState,
    VwapPosition,
)
from markeitech.context_events import (
    ContextDetectionStatus,
    ContextEventKind,
    MarketContextTransitionDetector,
)
from markeitech.persistence import CommittedFeatureRevision

START = datetime(2026, 7, 16, 10, 0, tzinfo=UTC)


def revision(
    sequence: int,
    *,
    minute: int,
    trend: TrendState = TrendState.RANGE,
    location: ProfileLocation = ProfileLocation.LOWER_VALUE,
    configuration_hash: str = "a" * 64,
) -> CommittedFeatureRevision:
    as_of = START + timedelta(minutes=minute)
    snapshot = MarketContextSnapshot(
        instrument_id="NQU6.CME",
        timeframe=AnalyticsTimeframe.ONE_MINUTE,
        as_of=as_of,
        source="classified_ticks",
        input_fidelity=AnalyticsInputFidelity.INFERRED,
        bar_count=250,
        close=Decimal("29600"),
        session_open=Decimal("29500"),
        session_high=Decimal("29650"),
        session_low=Decimal("29450"),
        session_range_position=Decimal("0.75"),
        vwap_position=VwapPosition.ABOVE,
        trend=trend,
        trend_reason_codes=("test_trend",),
        profile_location=location,
        location_reason_codes=("test_location",),
    )
    feature = MarketContextFeatureSnapshot(
        configuration_hash=configuration_hash,
        input_lineage=(
            FeatureInputLineage(
                instrument_id="NQU6.CME",
                timeframe=AnalyticsTimeframe.ONE_MINUTE,
                source="classified_ticks",
                input_fidelity=AnalyticsInputFidelity.INFERRED,
                start_ts=as_of - timedelta(minutes=249),
                end_ts=as_of,
                event_count=250,
                identity_hash=f"{sequence:x}".zfill(64),
            ),
        ),
        snapshot=snapshot,
    )
    return CommittedFeatureRevision(
        feature=feature,
        committed_ts=as_of + timedelta(seconds=1),
        commit_sequence=sequence,
    )


def test_initial_revision_seeds_without_historical_event() -> None:
    detector = MarketContextTransitionDetector()

    result = detector.apply(revision(1, minute=0))

    assert result.status == ContextDetectionStatus.SEEDED
    assert result.events == ()


def test_detects_trend_and_value_region_in_deterministic_order() -> None:
    detector = MarketContextTransitionDetector()
    previous = revision(
        1,
        minute=0,
        trend=TrendState.BULLISH,
        location=ProfileLocation.BELOW_VALUE,
    )
    current = revision(
        2,
        minute=1,
        trend=TrendState.BEARISH,
        location=ProfileLocation.LOWER_VALUE,
    )
    detector.apply(previous)

    result = detector.apply(current)

    assert result.status == ContextDetectionStatus.APPLIED
    assert [event.kind for event in result.events] == [
        ContextEventKind.TREND_CHANGED,
        ContextEventKind.VALUE_AREA_REGION_CHANGED,
    ]
    trend, value = result.events
    assert (trend.previous_value, trend.current_value) == ("bullish", "bearish")
    assert (value.previous_value, value.current_value) == ("below", "inside")
    assert trend.previous_feature_id == previous.feature.feature_id
    assert trend.current_feature_id == current.feature.feature_id
    assert len(trend.event_id) == 64
    assert trend.event_id == trend.model_copy().event_id


def test_movement_inside_value_does_not_emit_region_noise() -> None:
    detector = MarketContextTransitionDetector()
    detector.apply(revision(1, minute=0, location=ProfileLocation.LOWER_VALUE))

    result = detector.apply(revision(2, minute=1, location=ProfileLocation.UPPER_VALUE))

    assert result.events == ()
    assert result.reason_codes == ("no_context_transition",)


def test_unavailable_evidence_breaks_transition_comparison() -> None:
    detector = MarketContextTransitionDetector()
    detector.apply(
        revision(
            1,
            minute=0,
            trend=TrendState.BULLISH,
            location=ProfileLocation.BELOW_VALUE,
        )
    )
    unavailable = detector.apply(
        revision(
            2,
            minute=1,
            trend=TrendState.INSUFFICIENT_DATA,
            location=ProfileLocation.UNAVAILABLE,
        )
    )
    resumed = detector.apply(
        revision(
            3,
            minute=2,
            trend=TrendState.BEARISH,
            location=ProfileLocation.ABOVE_VALUE,
        )
    )

    assert unavailable.events == ()
    assert resumed.events == ()


def test_duplicate_stale_and_same_timestamp_correction_do_not_emit() -> None:
    detector = MarketContextTransitionDetector()
    initial = revision(2, minute=1)
    detector.apply(initial)

    duplicate = detector.apply(initial)
    stale = detector.apply(revision(1, minute=0, trend=TrendState.BEARISH))
    correction = detector.apply(
        revision(
            3,
            minute=1,
            trend=TrendState.BEARISH,
            configuration_hash="b" * 64,
        )
    )

    assert duplicate.status == ContextDetectionStatus.DUPLICATE
    assert stale.status == ContextDetectionStatus.STALE
    assert correction.status == ContextDetectionStatus.CORRECTION
    assert duplicate.events == stale.events == correction.events == ()


def test_conflicting_commit_sequence_fails_closed() -> None:
    detector = MarketContextTransitionDetector()
    detector.apply(revision(1, minute=0))

    with pytest.raises(ValueError, match="commit sequence identifies conflicting"):
        detector.apply(revision(1, minute=1, trend=TrendState.BEARISH))


def test_newer_market_time_cannot_regress_durable_commit_order() -> None:
    detector = MarketContextTransitionDetector()
    detector.apply(revision(3, minute=0))

    result = detector.apply(revision(2, minute=1, trend=TrendState.BEARISH))

    assert result.status == ContextDetectionStatus.STALE
    assert result.reason_codes == ("feature_commit_sequence_precedes_current_state",)
