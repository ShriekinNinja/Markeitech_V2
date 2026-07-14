from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from markeitech.analytics import (
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    FeatureInputLineage,
    MarketContextFeatureSnapshot,
    MarketContextSnapshot,
    TrendState,
    VwapPosition,
)
from markeitech.signals import (
    CommittedMarketContextBundle,
    DirectionQualificationStatus,
    DirectionRegimeTracker,
    OpposingContextPolicy,
    SignalDefinitionConfig,
    SignalDirection,
    SignalRuntimeConfig,
    intraday_context_definition,
    qualify_direction,
)
from pydantic import ValidationError

AS_OF = datetime(2026, 7, 14, 13, 30, tzinfo=UTC)
INSTRUMENT_ID = "NQU6.CME"


def feature(
    timeframe: AnalyticsTimeframe,
    score: int,
    *,
    instrument_id: str = INSTRUMENT_ID,
    as_of: datetime = AS_OF,
    fidelity: AnalyticsInputFidelity = AnalyticsInputFidelity.REPORTED,
) -> MarketContextFeatureSnapshot:
    direction = "bullish" if score > 0 else "bearish" if score < 0 else "neutral"
    return MarketContextFeatureSnapshot(
        configuration_hash="a" * 64,
        input_lineage=(
            FeatureInputLineage(
                instrument_id=instrument_id,
                timeframe=timeframe,
                source="ib",
                input_fidelity=fidelity,
                start_ts=as_of - timeframe.duration,
                end_ts=as_of,
                event_count=1,
                identity_hash=f"{list(AnalyticsTimeframe).index(timeframe) + 1:x}" * 64,
            ),
        ),
        snapshot=MarketContextSnapshot(
            instrument_id=instrument_id,
            timeframe=timeframe,
            as_of=as_of,
            source="ib",
            input_fidelity=fidelity,
            bar_count=251,
            close=Decimal("29605.25"),
            session_open=Decimal("29420"),
            session_high=Decimal("29649.75"),
            session_low=Decimal("29320"),
            session_range_position=Decimal("0.865"),
            vwap_position=VwapPosition.ABOVE if score > 0 else VwapPosition.BELOW,
            trend=TrendState.BULLISH if score > 0 else TrendState.BEARISH,
            trend_reason_codes=(f"{direction}_test_context",),
            direction_score=score,
            direction_location_reason_codes=(f"{direction}_direction_score",),
        ),
    )


def bundle(
    *,
    one_minute: int = 1,
    five_minutes: int | None = 1,
    fifteen_minutes: int | None = 1,
    one_hour: int | None = 1,
    daily: int | None = -1,
    as_of: datetime = AS_OF,
) -> CommittedMarketContextBundle:
    scores = (
        (AnalyticsTimeframe.ONE_MINUTE, one_minute),
        (AnalyticsTimeframe.FIVE_MINUTES, five_minutes),
        (AnalyticsTimeframe.FIFTEEN_MINUTES, fifteen_minutes),
        (AnalyticsTimeframe.ONE_HOUR, one_hour),
        (AnalyticsTimeframe.DAILY, daily),
    )
    return CommittedMarketContextBundle(
        instrument_id=INSTRUMENT_ID,
        evaluation_as_of=as_of,
        features=tuple(
            feature(timeframe, score, as_of=as_of)
            for timeframe, score in scores
            if score is not None
        ),
    )


def test_intraday_direction_qualifies_and_degrades_against_daily_context() -> None:
    definition = intraday_context_definition()

    qualification = qualify_direction(bundle(), definition)
    decision = DirectionRegimeTracker(definition).evaluate(bundle())

    assert qualification.status == DirectionQualificationStatus.QUALIFIED
    assert qualification.direction == SignalDirection.LONG
    assert qualification.is_degraded is True
    assert "opposing_context_degraded_1d" in qualification.reason_codes
    assert {item.snapshot.timeframe for item in qualification.evidence_features} == set(
        AnalyticsTimeframe
    ) - {AnalyticsTimeframe.THIRTY_MINUTES}
    assert decision.candidate is not None
    assert decision.candidate.definition_id == "intraday_context"
    assert len(decision.candidate.evidence) == 5


@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        ({"one_hour": None}, DirectionQualificationStatus.MISSING_EVIDENCE),
        ({"one_hour": -1}, DirectionQualificationStatus.CONFLICTED),
        ({"five_minutes": None}, DirectionQualificationStatus.MISSING_EVIDENCE),
        ({"five_minutes": 0}, DirectionQualificationStatus.NEUTRAL),
        ({"five_minutes": -1}, DirectionQualificationStatus.CONFLICTED),
    ],
)
def test_direction_requires_primary_agreement_and_configured_confirmation(
    updates: dict[str, int | None],
    expected: DirectionQualificationStatus,
) -> None:
    qualification = qualify_direction(bundle(**updates), intraday_context_definition())

    assert qualification.status == expected
    assert qualification.direction is None


def test_context_policy_can_veto_an_otherwise_qualified_direction() -> None:
    definition = intraday_context_definition().model_copy(
        update={"opposing_context_policy": OpposingContextPolicy.VETO}
    )

    qualification = qualify_direction(bundle(), definition)

    assert qualification.status == DirectionQualificationStatus.VETOED
    assert qualification.direction is None


def test_bundle_rejects_cross_instrument_future_and_duplicate_features() -> None:
    with pytest.raises(ValidationError, match="cannot cross instruments"):
        CommittedMarketContextBundle(
            instrument_id=INSTRUMENT_ID,
            evaluation_as_of=AS_OF,
            features=(feature(AnalyticsTimeframe.ONE_MINUTE, 1, instrument_id="ESU6.CME"),),
        )
    with pytest.raises(ValidationError, match="future evidence"):
        CommittedMarketContextBundle(
            instrument_id=INSTRUMENT_ID,
            evaluation_as_of=AS_OF,
            features=(
                feature(
                    AnalyticsTimeframe.ONE_MINUTE,
                    1,
                    as_of=AS_OF + timedelta(minutes=1),
                ),
            ),
        )
    duplicate = feature(AnalyticsTimeframe.ONE_MINUTE, 1)
    with pytest.raises(ValidationError, match="one feature per timeframe"):
        CommittedMarketContextBundle(
            instrument_id=INSTRUMENT_ID,
            evaluation_as_of=AS_OF,
            features=(duplicate, duplicate),
        )


def test_alternate_scalp_definition_uses_its_own_timeframe_roles() -> None:
    definition = SignalDefinitionConfig(
        definition_id="scalp",
        evaluation_timeframe=AnalyticsTimeframe.ONE_MINUTE,
        primary_direction_timeframes=(
            AnalyticsTimeframe.FIFTEEN_MINUTES,
            AnalyticsTimeframe.FIVE_MINUTES,
        ),
        confirmation_timeframes=(AnalyticsTimeframe.ONE_MINUTE,),
        minimum_confirmation_count=1,
    )

    decision = DirectionRegimeTracker(definition).evaluate(
        bundle(one_hour=None, daily=None)
    )

    assert decision.qualification.status == DirectionQualificationStatus.QUALIFIED
    assert decision.candidate is not None
    assert decision.candidate.definition_id == "scalp"
    assert len(decision.candidate.evidence) == 3


def test_tracker_emits_once_per_direction_regime_and_requalifies_after_neutral() -> None:
    tracker = DirectionRegimeTracker(intraday_context_definition())
    first = tracker.evaluate(bundle())
    repeated = tracker.evaluate(bundle(as_of=AS_OF + timedelta(minutes=1)))
    ended = tracker.evaluate(
        bundle(fifteen_minutes=0, as_of=AS_OF + timedelta(minutes=2))
    )
    resumed = tracker.evaluate(bundle(as_of=AS_OF + timedelta(minutes=3)))

    assert first.candidate is not None
    assert repeated.candidate is None
    assert repeated.ended_signal_id is None
    assert ended.candidate is None
    assert ended.ended_signal_id == first.candidate.signal_id
    assert resumed.candidate is not None
    assert resumed.candidate.signal_id != first.candidate.signal_id


def test_missing_evidence_preserves_regime_and_does_not_duplicate_on_recovery() -> None:
    tracker = DirectionRegimeTracker(intraday_context_definition())
    first = tracker.evaluate(bundle())
    missing = tracker.evaluate(
        bundle(one_hour=None, as_of=AS_OF + timedelta(minutes=1))
    )
    recovered = tracker.evaluate(bundle(as_of=AS_OF + timedelta(minutes=2)))

    assert first.candidate is not None
    assert missing.qualification.status == DirectionQualificationStatus.MISSING_EVIDENCE
    assert missing.ended_signal_id is None
    assert recovered.candidate is None


def test_opposite_direction_ends_old_regime_and_starts_distinct_candidate() -> None:
    tracker = DirectionRegimeTracker(intraday_context_definition())
    long = tracker.evaluate(bundle(daily=1))
    short = tracker.evaluate(
        bundle(
            five_minutes=-1,
            fifteen_minutes=-1,
            one_hour=-1,
            daily=-1,
            as_of=AS_OF + timedelta(minutes=1),
        )
    )

    assert long.candidate is not None
    assert short.candidate is not None
    assert short.ended_signal_id == long.candidate.signal_id
    assert short.candidate.direction == SignalDirection.SHORT
    assert short.candidate.signal_id != long.candidate.signal_id


def test_restart_seed_suppresses_duplicate_and_rejects_invalid_regime_identity() -> None:
    definition = intraday_context_definition()
    original = DirectionRegimeTracker(definition).evaluate(bundle()).candidate
    assert original is not None
    restarted = DirectionRegimeTracker(definition)
    restarted.seed_open_signals((original,))

    assert restarted.evaluate(bundle(as_of=AS_OF + timedelta(minutes=1))).candidate is None

    corrupt = original.model_copy(update={"setup_key": "f" * 64})
    with pytest.raises(ValueError, match="does not match direction regime"):
        DirectionRegimeTracker(definition).seed_open_signals((corrupt,))


def test_definition_identity_configuration_and_instrument_enablement_are_explicit() -> None:
    intraday = intraday_context_definition()
    scalp = SignalDefinitionConfig(
        definition_id="scalp",
        primary_direction_timeframes=(AnalyticsTimeframe.FIFTEEN_MINUTES,),
    )
    runtime = SignalRuntimeConfig(
        definitions=(intraday, scalp),
        enabled_definition_ids_by_instrument={
            INSTRUMENT_ID: ("intraday_context", "scalp"),
            "ESU6.CME": ("intraday_context",),
        },
    )

    assert runtime.enabled_definitions(INSTRUMENT_ID) == (intraday, scalp)
    assert runtime.enabled_definitions("ESU6.CME") == (intraday,)
    assert intraday.configuration_hash != intraday.model_copy(
        update={"minimum_direction_score": 2}
    ).configuration_hash

    with pytest.raises(ValidationError, match="unknown enabled signal definitions"):
        SignalRuntimeConfig(
            definitions=(intraday,),
            enabled_definition_ids_by_instrument={INSTRUMENT_ID: ("unknown",)},
        )
    with pytest.raises(ValidationError, match="must be unique per instrument"):
        SignalRuntimeConfig(
            definitions=(intraday,),
            enabled_definition_ids_by_instrument={
                INSTRUMENT_ID: ("intraday_context", "intraday_context")
            },
        )


def test_same_market_regime_has_distinct_identity_for_each_definition() -> None:
    intraday = DirectionRegimeTracker(intraday_context_definition()).evaluate(bundle()).candidate
    alternate = intraday_context_definition().model_copy(
        update={"definition_id": "alternate_context"}
    )
    other = DirectionRegimeTracker(alternate).evaluate(bundle()).candidate

    assert intraday is not None
    assert other is not None
    assert intraday.setup_key != other.setup_key
    assert intraday.signal_id != other.signal_id
