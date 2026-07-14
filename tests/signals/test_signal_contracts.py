from datetime import UTC, datetime, timedelta

import pytest
from markeitech.signals import (
    SignalDirection,
    SignalEvidenceFidelity,
    SignalEvidenceReference,
    SignalEvidenceStage,
    SignalEvidenceType,
    SignalFamily,
    SignalSnapshot,
    SignalStatus,
    signal_setup_key,
    transition_signal,
)
from pydantic import ValidationError

NOW = datetime(2026, 7, 14, 13, 30, tzinfo=UTC)


def evidence(
    stage: SignalEvidenceStage,
    *,
    evidence_id: str | None = None,
    evidence_type: SignalEvidenceType = SignalEvidenceType.MARKET_CONTEXT_FEATURE,
    fidelity: SignalEvidenceFidelity = SignalEvidenceFidelity.INFERRED,
    instrument_id: str = "NQU6.CME",
) -> SignalEvidenceReference:
    default_ids = {
        SignalEvidenceStage.DIRECTION: "d" * 64,
        SignalEvidenceStage.LOCATION: "b" * 64,
        SignalEvidenceStage.AGGRESSION: "a" * 64,
        SignalEvidenceStage.FOLLOW_THROUGH: "f" * 64,
    }
    return SignalEvidenceReference(
        instrument_id=instrument_id,
        stage=stage,
        evidence_type=evidence_type,
        evidence_id=evidence_id or default_ids[stage],
        observed_ts=NOW,
        source="market_context",
        fidelity=fidelity,
        reason_codes=(f"{stage.value}_confirmed",),
    )


def candidate(**updates: object) -> SignalSnapshot:
    values: dict[str, object] = {
        "algorithm_version": "1.0",
        "definition_id": "intraday_context",
        "configuration_hash": "c" * 64,
        "setup_key": signal_setup_key(
            family=SignalFamily.DIRECTION_LOCATION_AGGRESSION,
            definition_id="intraday_context",
            instrument_id="NQU6.CME",
            direction=SignalDirection.LONG,
            anchor="2026-07-14:CME_Equity:prior_value_area_low",
        ),
        "instrument_id": "NQU6.CME",
        "direction": SignalDirection.LONG,
        "created_ts": NOW,
        "updated_ts": NOW,
        "evidence": (evidence(SignalEvidenceStage.DIRECTION),),
        "reason_codes": ("bullish_direction_candidate",),
    }
    values.update(updates)
    return SignalSnapshot(**values)


def test_signal_identity_is_stable_across_lifecycle_content() -> None:
    initial = candidate()
    armed = transition_signal(
        initial,
        SignalStatus.ARMED,
        occurred_ts=NOW + timedelta(seconds=1),
        reason_codes=("location_held",),
        evidence=(evidence(SignalEvidenceStage.LOCATION),),
    ).current

    assert armed.signal_id == initial.signal_id
    assert armed.content_hash != initial.content_hash
    assert initial.feature_ids == ("d" * 64,)

    revised_algorithm = candidate(algorithm_version="1.1")
    revised_configuration = candidate(configuration_hash="e" * 64)
    assert len(
        {initial.signal_id, revised_algorithm.signal_id, revised_configuration.signal_id}
    ) == 3


def test_setup_identity_changes_with_direction_instrument_or_anchor() -> None:
    base = signal_setup_key(
        family=SignalFamily.DIRECTION_LOCATION_AGGRESSION,
        definition_id="intraday_context",
        instrument_id="NQU6.CME",
        direction=SignalDirection.LONG,
        anchor="session:level-a",
    )
    changed = {
        signal_setup_key(
            family=SignalFamily.DIRECTION_LOCATION_AGGRESSION,
            definition_id="intraday_context",
            instrument_id="NQU6.CME",
            direction=SignalDirection.SHORT,
            anchor="session:level-a",
        ),
        signal_setup_key(
            family=SignalFamily.DIRECTION_LOCATION_AGGRESSION,
            definition_id="intraday_context",
            instrument_id="ESU6.CME",
            direction=SignalDirection.LONG,
            anchor="session:level-a",
        ),
        signal_setup_key(
            family=SignalFamily.DIRECTION_LOCATION_AGGRESSION,
            definition_id="intraday_context",
            instrument_id="NQU6.CME",
            direction=SignalDirection.LONG,
            anchor="session:level-b",
        ),
    }

    assert base not in changed
    assert len(changed) == 3

    with pytest.raises(ValueError, match="requires definition, instrument, and anchor"):
        signal_setup_key(
            family=SignalFamily.DIRECTION_LOCATION_AGGRESSION,
            definition_id="intraday_context",
            instrument_id="NQU6.CME",
            direction=SignalDirection.LONG,
            anchor=" session:level-a",
        )


def test_direction_and_location_reject_non_feature_evidence() -> None:
    with pytest.raises(ValidationError, match="require market-context feature"):
        evidence(
            SignalEvidenceStage.LOCATION,
            evidence_type=SignalEvidenceType.MARKET_DATA_WINDOW,
        )


def test_signal_rejects_cross_instrument_and_duplicate_evidence() -> None:
    with pytest.raises(ValidationError, match="instrument must match"):
        candidate(
            evidence=(
                evidence(SignalEvidenceStage.DIRECTION),
                evidence(SignalEvidenceStage.LOCATION, instrument_id="ESU6.CME"),
            )
        )
    direction = evidence(SignalEvidenceStage.DIRECTION)
    with pytest.raises(ValidationError, match="must be unique"):
        candidate(evidence=(direction, direction))


def test_unavailable_evidence_cannot_arm_or_trigger_signal() -> None:
    with pytest.raises(ValidationError, match="available direction"):
        candidate(
            evidence=(
                evidence(
                    SignalEvidenceStage.DIRECTION,
                    fidelity=SignalEvidenceFidelity.UNAVAILABLE,
                ),
            )
        )
    with pytest.raises(ValidationError, match="available direction and location"):
        candidate(
            status=SignalStatus.ARMED,
            evidence=(
                evidence(SignalEvidenceStage.DIRECTION),
                evidence(
                    SignalEvidenceStage.LOCATION,
                    fidelity=SignalEvidenceFidelity.UNAVAILABLE,
                ),
            ),
        )
    with pytest.raises(ValidationError, match="available aggression"):
        candidate(
            status=SignalStatus.TRIGGERED,
            evidence=(
                evidence(SignalEvidenceStage.DIRECTION),
                evidence(SignalEvidenceStage.LOCATION),
            ),
        )


def test_one_feature_can_support_multiple_stages_without_duplicate_feature_ids() -> None:
    shared_id = "9" * 64
    snapshot = candidate(
        status=SignalStatus.ARMED,
        evidence=(
            evidence(SignalEvidenceStage.DIRECTION, evidence_id=shared_id),
            evidence(SignalEvidenceStage.LOCATION, evidence_id=shared_id),
        ),
    )

    assert snapshot.feature_ids == (shared_id,)


def test_lifecycle_requires_ordered_evidence_and_stable_identity() -> None:
    initial = candidate()
    armed_event = transition_signal(
        initial,
        SignalStatus.ARMED,
        occurred_ts=NOW + timedelta(seconds=1),
        reason_codes=("location_held",),
        evidence=(evidence(SignalEvidenceStage.LOCATION),),
    )
    aggression = evidence(
        SignalEvidenceStage.AGGRESSION,
        evidence_type=SignalEvidenceType.MARKET_DATA_WINDOW,
        evidence_id="a" * 64,
        fidelity=SignalEvidenceFidelity.PARTIAL,
    )
    triggered_event = transition_signal(
        armed_event.current,
        SignalStatus.TRIGGERED,
        occurred_ts=NOW + timedelta(seconds=2),
        reason_codes=("buy_aggression_confirmed",),
        evidence=(aggression,),
    )

    assert triggered_event.signal_id == initial.signal_id
    assert triggered_event.current.status == SignalStatus.TRIGGERED
    assert triggered_event.appended_evidence == (aggression,)
    assert triggered_event.transition_id == triggered_event.transition_id
    assert type(triggered_event).model_validate_json(triggered_event.model_dump_json()) == (
        triggered_event
    )


def test_lifecycle_rejects_skips_regressions_and_terminal_mutation() -> None:
    initial = candidate()
    with pytest.raises(ValueError, match="cannot move from candidate to triggered"):
        transition_signal(
            initial,
            SignalStatus.TRIGGERED,
            occurred_ts=NOW,
            reason_codes=("skip",),
        )
    with pytest.raises(ValueError, match="cannot move time backward"):
        transition_signal(
            initial,
            SignalStatus.ARMED,
            occurred_ts=NOW - timedelta(seconds=1),
            reason_codes=("late_event",),
        )
    expired = transition_signal(
        initial,
        SignalStatus.EXPIRED,
        occurred_ts=NOW + timedelta(minutes=5),
        reason_codes=("setup_timeout",),
    ).current
    with pytest.raises(ValueError, match="cannot move from expired"):
        transition_signal(
            expired,
            SignalStatus.ARMED,
            occurred_ts=NOW + timedelta(minutes=6),
            reason_codes=("too_late",),
        )
