from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvidencePolicy:
    feed_kind: str
    selector: str
    fresh_for_ms: int
    stale_after_ms: int
    unavailable_after_ms: int

    @property
    def version(self) -> str:
        return (
            f"{self.feed_kind}/{self.selector}:"
            f"{self.fresh_for_ms}-{self.stale_after_ms}-{self.unavailable_after_ms}ms"
        )


@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    state: str
    reason: str
    age_ms: int | None


def assess_evidence(
    policy: EvidencePolicy,
    *,
    evaluated_ts_ns: int,
    receive_ts_ns: int | None,
    subscription_state: str,
    session_is_open: bool | None,
) -> EvidenceAssessment:
    if subscription_state in {"REJECTED", "FAILED", "CANCELED", "EXPIRED"}:
        return EvidenceAssessment("UNAVAILABLE", f"subscription {subscription_state.lower()}", None)
    if session_is_open is None:
        return EvidenceAssessment("NOT_EVALUATED", "session state is not known", None)
    if not session_is_open:
        return EvidenceAssessment(
            "DORMANT",
            "session is closed; observations are not expected",
            None,
        )
    if receive_ts_ns is None:
        return EvidenceAssessment("DEGRADED", "awaiting first observation", None)
    age_ms = max(0, (evaluated_ts_ns - receive_ts_ns) // 1_000_000)
    if age_ms <= policy.fresh_for_ms:
        return EvidenceAssessment("HEALTHY", "observation is fresh", age_ms)
    if age_ms <= policy.stale_after_ms:
        return EvidenceAssessment("DEGRADED", "observation freshness is degrading", age_ms)
    if age_ms <= policy.unavailable_after_ms:
        return EvidenceAssessment("STALE", "observation is stale", age_ms)
    return EvidenceAssessment("UNAVAILABLE", "observation freshness expired", age_ms)
