from __future__ import annotations

import pytest

from markeitech.intelligence.evidence import EvidencePolicy, RecencyProfile, assess_evidence

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


def test_adaptive_policy_uses_learned_profile_only_after_minimum_samples() -> None:
    policy = EvidencePolicy(
        "quotes",
        "default",
        5_000,
        15_000,
        60_000,
        adaptive=True,
        minimum_samples=20,
        min_fresh_ms=2_000,
        max_fresh_ms=15_000,
        min_stale_ms=5_000,
        max_stale_ms=45_000,
        min_unavailable_ms=15_000,
        max_unavailable_ms=120_000,
    )
    cold = RecencyProfile(
        sample_count=19,
        mean_interval_ms=1_000,
        variance_ms2=250_000,
    )
    warm = RecencyProfile(
        sample_count=20,
        mean_interval_ms=1_000,
        variance_ms2=250_000,
    )

    assert policy.effective(cold) is policy
    effective = policy.effective(warm)
    assert (
        effective.fresh_for_ms,
        effective.stale_after_ms,
        effective.unavailable_after_ms,
    ) == (2_000, 5_000, 15_000)


def test_recency_profile_updates_bounded_rolling_statistics() -> None:
    profile = RecencyProfile()

    profile.observe(1_000, 1_000_000_000, 0.95)
    profile.observe(2_000, 3_000_000_000, 0.95)

    assert profile.sample_count == 2
    assert profile.mean_interval_ms == 1_050
    assert profile.variance_ms2 == pytest.approx(47_500)
    assert profile.last_observed_ns == 3_000_000_000
