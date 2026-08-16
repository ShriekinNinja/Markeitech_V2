from __future__ import annotations

import pytest

from markeitech.intelligence.messages import EvidenceHealthEvent, SessionStateEvent


def test_session_state_round_trip() -> None:
    event = SessionStateEvent(
        event_id="session:cboe_spxw:1",
        calendar_id="cboe_spxw",
        schedule_version="test-1",
        timezone="America/New_York",
        trade_date="2026-08-17",
        phase="GTH",
        previous_phase=None,
        is_open=True,
        phase_open_ns=1,
        phase_close_ns=2,
        next_transition_ns=2,
        source="SESSION-STATE",
        reason="initial session evaluation",
        revision=1,
    )

    assert SessionStateEvent.from_signal_value(event.to_signal_value()) == event


def test_session_state_accepts_configured_uppercase_phase_names() -> None:
    event = SessionStateEvent(
        event_id="session:cme_equity:1",
        calendar_id="cme_equity",
        schedule_version="test-v1",
        timezone="America/New_York",
        trade_date="2026-08-17",
        phase="OVERNIGHT",
        previous_phase="CLOSED",
        is_open=True,
        phase_open_ns=1,
        phase_close_ns=2,
        next_transition_ns=2,
        source="SESSION-STATE",
        reason="session phase changed",
        revision=1,
    )

    assert SessionStateEvent.from_signal_value(event.to_signal_value()).phase == "OVERNIGHT"


def test_evidence_health_round_trip() -> None:
    event = EvidenceHealthEvent(
        event_id="evidence:SPY.ARCA:quotes:default:1",
        instrument_id="SPY.ARCA",
        calendar_id="us_equities",
        feed_kind="quotes",
        selector="default",
        state="HEALTHY",
        previous_state="DEGRADED",
        reason="observation is fresh",
        fidelity="REPORTED",
        subscription_state="ACTIVE",
        event_ts_ns=1,
        receive_ts_ns=2,
        evaluated_ts_ns=3,
        age_ms=0,
        session_phase="RTH",
        session_trade_date="2026-08-17",
        session_alignment="IN_SESSION",
        source="EVIDENCE-HEALTH",
        policy_version="quotes/default:2000-5000-15000ms",
        revision=1,
    )

    assert EvidenceHealthEvent.from_signal_value(event.to_signal_value()) == event


@pytest.mark.parametrize("state", ["NOT_EVALUATED", "DORMANT"])
def test_evidence_health_accepts_non_failure_silence_states(state: str) -> None:
    event = EvidenceHealthEvent(
        event_id=f"evidence:SPY.ARCA:quotes:default:{state}",
        instrument_id="SPY.ARCA",
        calendar_id="us_equities",
        feed_kind="quotes",
        selector="default",
        state=state,
        previous_state=None,
        reason="observations are not currently expected",
        fidelity="UNAVAILABLE",
        subscription_state="SUBSCRIBED",
        event_ts_ns=None,
        receive_ts_ns=None,
        evaluated_ts_ns=3,
        age_ms=None,
        session_phase="CLOSED" if state == "DORMANT" else None,
        session_trade_date=None,
        session_alignment="OUTSIDE_SESSION" if state == "DORMANT" else "UNKNOWN",
        source="EVIDENCE-HEALTH",
        policy_version="quotes/default:2000-5000-15000ms",
        revision=1,
    )

    assert EvidenceHealthEvent.from_signal_value(event.to_signal_value()) == event


def test_message_contract_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError, match="fields"):
        SessionStateEvent.from_signal_value('{"schema_version":1,"unexpected":true}')
