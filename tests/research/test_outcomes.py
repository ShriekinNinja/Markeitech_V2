from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from markeitech.analytics import AnalyticsTimeframe
from markeitech.domain.market_data import OneMinuteBar
from markeitech.research import (
    AuditEventKind,
    HorizonOutcomeStatus,
    SignalAuditHistory,
    audit_signal_outcomes,
    render_signal_outcome_report,
    write_signal_outcome_artifacts,
)
from markeitech.signals import (
    LocationSourceKind,
    SignalConfirmationContext,
    SignalConfirmationMethod,
    SignalDirection,
    SignalEvidenceFidelity,
    SignalEvidenceReference,
    SignalEvidenceStage,
    SignalEvidenceType,
    SignalFamily,
    SignalLocationMatch,
    SignalLocationZone,
    SignalLocationZoneKind,
    SignalSnapshot,
    SignalStatus,
    signal_setup_key,
    transition_signal,
)

INSTRUMENT = "NQU6.CME"
NOW = datetime(2026, 7, 17, 13, 30, tzinfo=UTC)
FEATURE_IDS = frozenset({"b" * 64, "d" * 64})


class FixedCalendar:
    def __init__(
        self,
        open_ts: datetime = NOW - timedelta(minutes=30),
        close_ts: datetime = NOW + timedelta(minutes=30),
    ) -> None:
        self.open_ts = open_ts
        self.close_ts = close_ts

    def session_window(
        self,
        instrument_id: str,
        timestamp: datetime,
    ) -> tuple[datetime, datetime]:
        assert instrument_id == INSTRUMENT
        if not self.open_ts <= timestamp < self.close_ts:
            raise ValueError("outside session")
        return self.open_ts, self.close_ts

    def expected_minute_opens(
        self,
        instrument_id: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> tuple[datetime, ...]:
        assert instrument_id == INSTRUMENT
        cursor = start_ts.replace(second=0, microsecond=0)
        if cursor < start_ts:
            cursor += timedelta(minutes=1)
        values = []
        while cursor < min(end_ts, self.close_ts):
            values.append(cursor)
            cursor += timedelta(minutes=1)
        return tuple(values)


def test_long_outcome_uses_only_forward_session_minutes() -> None:
    history = signal_history(SignalDirection.LONG)
    bars = (
        bar(NOW - timedelta(minutes=1), "100", "101", "99", "100"),
        bar(NOW, "100", "102", "99", "101"),
        bar(NOW + timedelta(minutes=1), "101", "103", "98", "99"),
        bar(NOW + timedelta(minutes=2), "99", "101", "97", "98"),
    )

    record = audit(history, bars, horizons=(3,))[0]
    outcome = record.horizons[0]

    assert record.event_reference_price == Decimal("100")
    assert record.event_reference_ts == NOW
    assert outcome.status == HorizonOutcomeStatus.COMPLETE
    assert outcome.directional_return_points == Decimal("-2")
    assert outcome.maximum_favorable_excursion_points == Decimal("3")
    assert outcome.maximum_adverse_excursion_points == Decimal("3")
    assert outcome.favorable_extreme_ts == NOW + timedelta(minutes=2)
    assert outcome.adverse_extreme_ts == NOW + timedelta(minutes=3)


def test_short_outcome_is_direction_adjusted_and_armed_is_distinct_from_triggered() -> None:
    history = signal_history(SignalDirection.SHORT, trigger_ts=NOW + timedelta(minutes=1))
    bars = tuple(
        bar(open_ts, *prices)
        for open_ts, prices in (
            (NOW - timedelta(minutes=1), ("100", "101", "99", "100")),
            (NOW, ("100", "102", "98", "99")),
            (NOW + timedelta(minutes=1), ("99", "100", "96", "97")),
            (NOW + timedelta(minutes=2), ("97", "99", "95", "96")),
        )
    )

    armed, triggered = audit(history, bars, horizons=(2,))

    assert armed.event_kind == AuditEventKind.ARMED
    assert triggered.event_kind == AuditEventKind.TRIGGERED
    assert armed.horizons[0].directional_return_points == Decimal("3")
    assert armed.horizons[0].maximum_favorable_excursion_points == Decimal("4")
    assert armed.horizons[0].maximum_adverse_excursion_points == Decimal("2")
    assert triggered.event_reference_price == Decimal("99")
    assert triggered.horizons[0].directional_return_points == Decimal("3")


def test_missing_bar_and_session_end_are_explicitly_unavailable() -> None:
    history = signal_history(SignalDirection.LONG)
    bars = (
        bar(NOW - timedelta(minutes=1), "100", "101", "99", "100"),
        bar(NOW, "100", "101", "99", "100"),
        bar(NOW + timedelta(minutes=2), "100", "102", "100", "101"),
    )

    missing = audit(history, bars, horizons=(3,))[0].horizons[0]
    ended = audit(
        history,
        bars,
        horizons=(3,),
        calendar=FixedCalendar(close_ts=NOW + timedelta(minutes=2)),
    )[0].horizons[0]

    assert missing.status == HorizonOutcomeStatus.UNAVAILABLE
    assert missing.reason_codes == ("forward_bar_window_incomplete",)
    assert missing.observed_bar_count == 1
    assert ended.reason_codes == ("session_ended_before_horizon",)


def test_conflicting_reported_revision_and_missing_feature_fail_visibly() -> None:
    history = signal_history(SignalDirection.LONG)
    original = bar(NOW - timedelta(minutes=1), "100", "101", "99", "100")
    conflicting = original.model_copy(
        update={
            "close": Decimal("101"),
            "is_revision": True,
            "ts_init": original.ts_init + timedelta(seconds=1),
        }
    )

    with pytest.raises(ValueError, match="conflicting reported bar revisions"):
        audit(history, (original, conflicting), horizons=(1,))
    with pytest.raises(ValueError, match="unavailable committed features"):
        audit(
            history,
            (original, bar(NOW, "100", "101", "99", "100")),
            horizons=(1,),
            features=frozenset({"d" * 64}),
        )


def test_duplicate_transition_history_fails_visibly() -> None:
    history = signal_history(SignalDirection.LONG)
    duplicate = SignalAuditHistory(
        current=history.current,
        transitions=(history.transitions[0], history.transitions[0]),
    )
    bars = (
        bar(NOW - timedelta(minutes=1), "100", "101", "99", "100"),
        bar(NOW, "100", "101", "99", "100"),
    )

    with pytest.raises(ValueError, match="duplicate transition"):
        audit(duplicate, bars, horizons=(1,))


def test_artifacts_are_byte_stable_and_disclose_role_provenance(tmp_path: Path) -> None:
    history = signal_history(SignalDirection.LONG)
    bars = (
        bar(NOW - timedelta(minutes=1), "100", "101", "99", "100"),
        bar(NOW, "100", "102", "99", "101"),
    )
    records = audit(history, bars, horizons=(1,))
    report = render_signal_outcome_report(
        records,
        start_ts=NOW,
        end_ts=NOW + timedelta(minutes=1),
    )

    first = write_signal_outcome_artifacts(records, report=report, output_directory=tmp_path)
    before = tuple(path.read_bytes() for path in first)
    second = write_signal_outcome_artifacts(records, report=report, output_directory=tmp_path)

    assert before == tuple(path.read_bytes() for path in second)
    assert records[0].instrument_role_source == "audit_configuration_not_point_in_time"
    assert "not claimed as durable point-in-time evidence" in report


def audit(
    history: SignalAuditHistory,
    bars: tuple[OneMinuteBar, ...],
    *,
    horizons: tuple[int, ...],
    calendar: FixedCalendar | None = None,
    features: frozenset[str] = FEATURE_IDS,
):
    return audit_signal_outcomes(
        (history,),
        {INSTRUMENT: bars},
        calendar=calendar or FixedCalendar(),
        role_by_instrument={INSTRUMENT: "active"},
        available_feature_ids=features,
        start_ts=NOW,
        end_ts=NOW + timedelta(minutes=10),
        horizons_minutes=horizons,
    )


def signal_history(
    direction: SignalDirection,
    *,
    trigger_ts: datetime | None = None,
) -> SignalAuditHistory:
    candidate = candidate_signal(direction)
    location = location_match(direction)
    armed = transition_signal(
        candidate,
        SignalStatus.ARMED,
        occurred_ts=NOW,
        reason_codes=("qualified_location_entered",),
        evidence=(feature_evidence(SignalEvidenceStage.LOCATION, "b" * 64, NOW),),
        location_matches=(location,),
        confirmation_context=SignalConfirmationContext(
            method=SignalConfirmationMethod.TICK_AGGRESSION,
            window_started_ts=NOW,
            atr_at_arm=Decimal("4"),
        ),
    )
    transitions = [armed]
    current = armed.current
    if trigger_ts is not None:
        triggered = transition_signal(
            current,
            SignalStatus.TRIGGERED,
            occurred_ts=trigger_ts,
            reason_codes=("aggression_confirmed",),
            evidence=(market_window_evidence(trigger_ts),),
        )
        transitions.append(triggered)
        current = triggered.current
    return SignalAuditHistory(current=current, transitions=tuple(transitions))


def candidate_signal(direction: SignalDirection) -> SignalSnapshot:
    created = NOW - timedelta(minutes=1)
    return SignalSnapshot(
        definition_id="intraday_context",
        algorithm_version="1.0",
        configuration_hash="c" * 64,
        setup_key=signal_setup_key(
            family=SignalFamily.DIRECTION_LOCATION_AGGRESSION,
            definition_id="intraday_context",
            instrument_id=INSTRUMENT,
            direction=direction,
            anchor=f"audit:{direction.value}",
        ),
        instrument_id=INSTRUMENT,
        direction=direction,
        created_ts=created,
        updated_ts=created,
        direction_regime_anchor="direction_regime:audit",
        location_episode_id="e" * 64,
        evidence=(feature_evidence(SignalEvidenceStage.DIRECTION, "d" * 64, created),),
        reason_codes=("audit_candidate",),
    )


def location_match(direction: SignalDirection) -> SignalLocationMatch:
    zone_kind = (
        SignalLocationZoneKind.SUPPORT
        if direction == SignalDirection.LONG
        else SignalLocationZoneKind.RESISTANCE
    )
    zone = SignalLocationZone(
        instrument_id=INSTRUMENT,
        direction=direction,
        source_kind=LocationSourceKind.STRUCTURAL_LEVEL,
        zone_kind=zone_kind,
        timeframe=AnalyticsTimeframe.FIVE_MINUTES,
        zone_anchor="audit-level",
        source_feature_id="b" * 64,
        observed_ts=NOW,
        lower_price=Decimal("100"),
        upper_price=Decimal("100"),
        fidelity=SignalEvidenceFidelity.INFERRED,
        reason_codes=("audit_level",),
    )
    return SignalLocationMatch(
        zone=zone,
        evaluation_feature_id="b" * 64,
        observed_ts=NOW,
        observed_price=Decimal("100"),
        distance=Decimal("0"),
        tolerance=Decimal("1"),
        fidelity=SignalEvidenceFidelity.INFERRED,
        reason_codes=("audit_match",),
    )


def feature_evidence(
    stage: SignalEvidenceStage,
    evidence_id: str,
    observed_ts: datetime,
) -> SignalEvidenceReference:
    return SignalEvidenceReference(
        instrument_id=INSTRUMENT,
        stage=stage,
        evidence_type=SignalEvidenceType.MARKET_CONTEXT_FEATURE,
        evidence_id=evidence_id,
        observed_ts=observed_ts,
        source="market_context",
        fidelity=SignalEvidenceFidelity.INFERRED,
        reason_codes=(f"audit_{stage.value}",),
    )


def market_window_evidence(observed_ts: datetime) -> SignalEvidenceReference:
    return SignalEvidenceReference(
        instrument_id=INSTRUMENT,
        stage=SignalEvidenceStage.AGGRESSION,
        evidence_type=SignalEvidenceType.MARKET_DATA_WINDOW,
        evidence_id="a" * 64,
        observed_ts=observed_ts,
        source="ib",
        fidelity=SignalEvidenceFidelity.INFERRED,
        reason_codes=("audit_aggression",),
    )


def bar(
    open_ts: datetime,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> OneMinuteBar:
    close_ts = open_ts + timedelta(minutes=1)
    return OneMinuteBar(
        instrument_id=INSTRUMENT,
        event_ts=close_ts,
        ts_init=close_ts,
        open_ts=open_ts,
        close_ts=close_ts,
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("10"),
        buy_volume=Decimal("0"),
        sell_volume=Decimal("0"),
        unknown_volume=Decimal("10"),
        source="ib",
    )
