import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from markeitech.analytics import AnalyticsTimeframe
from markeitech.domain import OneMinuteBar
from markeitech.signals import (
    AggressionEvaluationStatus,
    AggressionPolicyConfig,
    LocationSourceKind,
    SignalDirection,
    SignalEvidenceFidelity,
    SignalEvidenceReference,
    SignalEvidenceStage,
    SignalEvidenceType,
    SignalLocationMatch,
    SignalLocationZone,
    SignalLocationZoneKind,
    SignalSnapshot,
    SignalStatus,
    evaluate_aggression_window,
    intraday_context_definition,
)
from pydantic import ValidationError

NOW = datetime(2026, 7, 15, 13, 0, tzinfo=UTC)
INSTRUMENT_ID = "NQU6.CME"


def evidence(stage: SignalEvidenceStage, evidence_id: str) -> SignalEvidenceReference:
    return SignalEvidenceReference(
        instrument_id=INSTRUMENT_ID,
        stage=stage,
        evidence_type=SignalEvidenceType.MARKET_CONTEXT_FEATURE,
        evidence_id=evidence_id,
        observed_ts=NOW,
        source="market_context",
        fidelity=SignalEvidenceFidelity.REPORTED,
        reason_codes=("test_evidence",),
    )


def armed_signal(direction: SignalDirection = SignalDirection.LONG) -> SignalSnapshot:
    source_feature_id = "b" * 64
    evaluation_feature_id = "c" * 64
    zone = SignalLocationZone(
        instrument_id=INSTRUMENT_ID,
        direction=direction,
        source_kind=LocationSourceKind.STRUCTURAL_LEVEL,
        zone_kind=(
            SignalLocationZoneKind.SUPPORT
            if direction == SignalDirection.LONG
            else SignalLocationZoneKind.RESISTANCE
        ),
        timeframe=AnalyticsTimeframe.FIVE_MINUTES,
        zone_anchor="test-zone",
        source_feature_id=source_feature_id,
        observed_ts=NOW,
        lower_price=Decimal("99"),
        upper_price=Decimal("101"),
        fidelity=SignalEvidenceFidelity.REPORTED,
        reason_codes=("test_zone",),
    )
    match = SignalLocationMatch(
        zone=zone,
        evaluation_feature_id=evaluation_feature_id,
        observed_ts=NOW,
        observed_price=Decimal("100"),
        distance=Decimal("0"),
        tolerance=Decimal("1"),
        fidelity=SignalEvidenceFidelity.REPORTED,
        reason_codes=("test_match",),
    )
    return SignalSnapshot(
        definition_id="intraday_context",
        algorithm_version="1.0",
        configuration_hash="d" * 64,
        setup_key="e" * 64,
        instrument_id=INSTRUMENT_ID,
        direction=direction,
        status=SignalStatus.ARMED,
        created_ts=NOW,
        updated_ts=NOW,
        direction_regime_anchor="test-regime",
        location_episode_id="f" * 64,
        location_matches=(match,),
        evidence=(
            evidence(SignalEvidenceStage.DIRECTION, "a" * 64),
            evidence(SignalEvidenceStage.LOCATION, source_feature_id),
            evidence(SignalEvidenceStage.LOCATION, evaluation_feature_id),
        ),
        reason_codes=("location_episode_armed",),
    )


def bar(
    minute: int,
    *,
    open_price: str,
    high: str,
    low: str,
    close: str,
    buy_volume: str = "70",
    sell_volume: str = "30",
    unknown_volume: str = "0",
    source: str = "classified_ticks",
) -> OneMinuteBar:
    open_ts = NOW + timedelta(minutes=minute)
    close_ts = open_ts + timedelta(minutes=1)
    buy = Decimal(buy_volume)
    sell = Decimal(sell_volume)
    unknown = Decimal(unknown_volume)
    return OneMinuteBar(
        instrument_id=INSTRUMENT_ID,
        event_ts=close_ts,
        ts_init=close_ts,
        open_ts=open_ts,
        close_ts=close_ts,
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=buy + sell + unknown,
        buy_volume=buy,
        sell_volume=sell,
        unknown_volume=unknown,
        source=source,
    )


def qualifying_bars() -> tuple[OneMinuteBar, ...]:
    return (
        bar(0, open_price="100", high="101", low="99.5", close="100.75"),
        bar(1, open_price="100.75", high="101.75", low="100.5", close="101.5"),
        bar(2, open_price="101.5", high="102.25", low="101.25", close="102"),
    )


def test_policy_requires_window_to_fit_observation_expiry() -> None:
    with pytest.raises(ValidationError, match="window cannot exceed"):
        AggressionPolicyConfig(window_bars=6, expiry_observation_bars=5)


def test_disabled_policy_preserves_existing_definition_identity() -> None:
    definition = intraday_context_definition()
    legacy_payload = definition.model_dump(mode="json")
    del legacy_payload["aggression_policy"]
    legacy_hash = hashlib.sha256(
        json.dumps(legacy_payload, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()

    assert definition.aggression_policy is None
    assert definition.configuration_hash == legacy_hash
    assert (
        definition.model_copy(
            update={"aggression_policy": AggressionPolicyConfig()}
        ).configuration_hash
        != legacy_hash
    )


def test_qualifies_directional_delta_and_price_follow_through() -> None:
    result = evaluate_aggression_window(
        armed_signal(),
        AggressionPolicyConfig(),
        qualifying_bars(),
        evaluated_ts=NOW + timedelta(minutes=3),
        elapsed_observation_bars=3,
        atr_at_arm=Decimal("10"),
    )

    assert result.status == AggressionEvaluationStatus.QUALIFIED
    assert result.window is not None
    assert result.window.directional_delta_ratio == Decimal("0.4")
    assert result.window.follow_through_atr_fraction == Decimal("0.2")
    assert result.window.fidelity == SignalEvidenceFidelity.INFERRED
    assert {item.stage for item in result.evidence} == {
        SignalEvidenceStage.AGGRESSION,
        SignalEvidenceStage.FOLLOW_THROUGH,
    }
    assert {item.evidence_id for item in result.evidence} == {result.window.window_id}


def test_short_direction_inverts_delta_progress_and_adverse_excursion() -> None:
    bars = (
        bar(
            0,
            open_price="100",
            high="100.5",
            low="99",
            close="99.25",
            buy_volume="30",
            sell_volume="70",
        ),
        bar(
            1,
            open_price="99.25",
            high="99.5",
            low="98",
            close="98.5",
            buy_volume="30",
            sell_volume="70",
        ),
        bar(
            2,
            open_price="98.5",
            high="98.75",
            low="97.75",
            close="98",
            buy_volume="30",
            sell_volume="70",
        ),
    )

    result = evaluate_aggression_window(
        armed_signal(SignalDirection.SHORT),
        AggressionPolicyConfig(),
        bars,
        evaluated_ts=NOW + timedelta(minutes=3),
        elapsed_observation_bars=3,
        atr_at_arm=Decimal("10"),
    )

    assert result.status == AggressionEvaluationStatus.QUALIFIED
    assert result.window is not None
    assert result.window.directional_delta_ratio == Decimal("0.4")
    assert result.window.follow_through_atr_fraction == Decimal("0.2")
    assert result.window.adverse_atr_fraction == Decimal("0.05")


def test_incomplete_tick_window_expires_by_observed_cadence_not_wall_clock() -> None:
    policy = AggressionPolicyConfig(window_bars=3, expiry_observation_bars=5)
    late_time = NOW + timedelta(hours=8)

    collecting = evaluate_aggression_window(
        armed_signal(),
        policy,
        (),
        evaluated_ts=late_time,
        elapsed_observation_bars=4,
        atr_at_arm=Decimal("10"),
    )
    expired = evaluate_aggression_window(
        armed_signal(),
        policy,
        (),
        evaluated_ts=late_time,
        elapsed_observation_bars=5,
        atr_at_arm=Decimal("10"),
    )

    assert collecting.status == AggressionEvaluationStatus.COLLECTING
    assert expired.status == AggressionEvaluationStatus.EXPIRED
    assert "armed_observation_window_expired" in expired.reason_codes
    assert {item.fidelity for item in expired.evidence} == {SignalEvidenceFidelity.UNAVAILABLE}
    assert {item.stage for item in expired.evidence} == {
        SignalEvidenceStage.AGGRESSION,
        SignalEvidenceStage.FOLLOW_THROUGH,
    }


def test_reported_ib_bars_do_not_impersonate_tick_aggression() -> None:
    reported = tuple(item.model_copy(update={"source": "ib"}) for item in qualifying_bars())

    result = evaluate_aggression_window(
        armed_signal(),
        AggressionPolicyConfig(),
        reported,
        evaluated_ts=NOW + timedelta(minutes=5),
        elapsed_observation_bars=5,
        atr_at_arm=Decimal("10"),
    )

    assert result.status == AggressionEvaluationStatus.EXPIRED
    assert result.window is None
    assert all(item.fidelity == SignalEvidenceFidelity.UNAVAILABLE for item in result.evidence)


def test_latest_consecutive_window_can_qualify_after_a_tick_gap() -> None:
    bars = (
        qualifying_bars()[0],
        bar(2, open_price="100", high="101", low="99.5", close="100.75"),
        bar(3, open_price="100.75", high="101.75", low="100.5", close="101.5"),
        bar(4, open_price="101.5", high="102.25", low="101.25", close="102"),
    )

    result = evaluate_aggression_window(
        armed_signal(),
        AggressionPolicyConfig(expiry_observation_bars=6),
        bars,
        evaluated_ts=NOW + timedelta(minutes=5),
        elapsed_observation_bars=5,
        atr_at_arm=Decimal("10"),
    )

    assert result.status == AggressionEvaluationStatus.QUALIFIED
    assert result.window is not None
    assert result.window.start_ts == NOW + timedelta(minutes=2)


def test_partial_classification_is_explicit_and_threshold_gated() -> None:
    partial = tuple(
        item.model_copy(
            update={
                "buy_volume": Decimal("55"),
                "sell_volume": Decimal("25"),
                "unknown_volume": Decimal("20"),
            }
        )
        for item in qualifying_bars()
    )

    result = evaluate_aggression_window(
        armed_signal(),
        AggressionPolicyConfig(minimum_classified_volume_ratio=Decimal("0.75")),
        partial,
        evaluated_ts=NOW + timedelta(minutes=3),
        elapsed_observation_bars=3,
        atr_at_arm=Decimal("10"),
    )

    assert result.status == AggressionEvaluationStatus.QUALIFIED
    assert result.window is not None
    assert result.window.fidelity == SignalEvidenceFidelity.PARTIAL
    assert result.window.classified_volume_ratio == Decimal("0.8")


def test_optional_pace_gate_fails_closed_without_enough_baseline() -> None:
    result = evaluate_aggression_window(
        armed_signal(),
        AggressionPolicyConfig(minimum_pace_ratio=Decimal("1.2")),
        qualifying_bars(),
        evaluated_ts=NOW + timedelta(minutes=3),
        elapsed_observation_bars=3,
        atr_at_arm=Decimal("10"),
    )

    assert result.status == AggressionEvaluationStatus.OBSERVING
    assert "pace_baseline_unavailable" in result.reason_codes
