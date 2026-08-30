from __future__ import annotations

import pytest

from markeitech.intelligence.messages import (
    EvidenceHealthEvent,
    EvidenceHealthSnapshot,
    EvidenceHealthSnapshotRequest,
    EvidenceRecencyProfileEvent,
)


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

    request = EvidenceHealthSnapshotRequest(
        requester="QUOTE-QUALITY-METRICS",
        instrument_ids=("SPY.ARCA",),
        feed_kind="quotes",
        selector="default",
    )
    snapshot = EvidenceHealthSnapshot(
        requester=request.requester,
        source="EVIDENCE-HEALTH",
        events=(event,),
        snapshot_ts_ns=4,
    )

    assert EvidenceHealthSnapshotRequest.from_signal_value(request.to_signal_value()) == request
    assert EvidenceHealthSnapshot.from_signal_value(snapshot.to_signal_value()) == snapshot


def test_evidence_recency_profile_round_trip() -> None:
    event = EvidenceRecencyProfileEvent(
        event_id="evidence-profile:SPY.ARCA:quotes:default:IB:RTH:25",
        instrument_id="SPY.ARCA",
        feed_kind="quotes",
        selector="default",
        provider_id="IB",
        session_phase="RTH",
        policy_version="quotes-v1",
        sample_count=25,
        mean_interval_ms=950.0,
        variance_ms2=22500.0,
        last_observed_ns=1_000_000_000,
        fresh_for_ms=2000,
        stale_after_ms=5000,
        unavailable_after_ms=15000,
        source="EVIDENCE-HEALTH",
    )

    assert EvidenceRecencyProfileEvent.from_signal_value(event.to_signal_value()) == event


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
        EvidenceHealthEvent.from_signal_value('{"schema_version":1,"unexpected":true}')
