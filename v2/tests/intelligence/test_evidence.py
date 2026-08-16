from __future__ import annotations

from markeitech.intelligence.evidence import EvidencePolicy, assess_evidence

POLICY = EvidencePolicy("quotes", "default", 2_000, 5_000, 15_000)


def test_evidence_age_transitions_are_explicit() -> None:
    receive = 10_000_000_000

    healthy = assess_evidence(
        POLICY,
        evaluated_ts_ns=receive + 2_000_000_000,
        receive_ts_ns=receive,
        subscription_state="ACTIVE",
        session_is_open=True,
    )
    degraded = assess_evidence(
        POLICY,
        evaluated_ts_ns=receive + 3_000_000_000,
        receive_ts_ns=receive,
        subscription_state="ACTIVE",
        session_is_open=True,
    )
    stale = assess_evidence(
        POLICY,
        evaluated_ts_ns=receive + 10_000_000_000,
        receive_ts_ns=receive,
        subscription_state="ACTIVE",
        session_is_open=True,
    )
    unavailable = assess_evidence(
        POLICY,
        evaluated_ts_ns=receive + 16_000_000_000,
        receive_ts_ns=receive,
        subscription_state="ACTIVE",
        session_is_open=True,
    )

    assert [item.state for item in (healthy, degraded, stale, unavailable)] == [
        "HEALTHY",
        "DEGRADED",
        "STALE",
        "UNAVAILABLE",
    ]


def test_failed_subscription_is_unavailable_without_fake_age() -> None:
    assessment = assess_evidence(
        POLICY,
        evaluated_ts_ns=100,
        receive_ts_ns=None,
        subscription_state="FAILED",
        session_is_open=True,
    )

    assert assessment.state == "UNAVAILABLE"
    assert assessment.age_ms is None


def test_missing_first_observation_is_degraded_not_healthy() -> None:
    assessment = assess_evidence(
        POLICY,
        evaluated_ts_ns=100,
        receive_ts_ns=None,
        subscription_state="SUBSCRIBED",
        session_is_open=True,
    )

    assert assessment.state == "DEGRADED"
    assert assessment.reason == "awaiting first observation"


def test_closed_session_is_dormant_even_when_last_observation_is_old() -> None:
    assessment = assess_evidence(
        POLICY,
        evaluated_ts_ns=100_000_000_000,
        receive_ts_ns=1,
        subscription_state="SUBSCRIBED",
        session_is_open=False,
    )

    assert assessment.state == "DORMANT"
    assert assessment.age_ms is None


def test_unknown_session_is_not_evaluated() -> None:
    assessment = assess_evidence(
        POLICY,
        evaluated_ts_ns=100,
        receive_ts_ns=None,
        subscription_state="SUBSCRIBED",
        session_is_open=None,
    )

    assert assessment.state == "NOT_EVALUATED"


def test_explicit_failure_is_unavailable_even_when_session_is_closed() -> None:
    assessment = assess_evidence(
        POLICY,
        evaluated_ts_ns=100,
        receive_ts_ns=None,
        subscription_state="FAILED",
        session_is_open=False,
    )

    assert assessment.state == "UNAVAILABLE"
