from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True, slots=True)
class EvidencePolicy:
    feed_kind: str
    selector: str
    fresh_for_ms: int
    stale_after_ms: int
    unavailable_after_ms: int
    adaptive: bool = False
    minimum_samples: int = 1
    decay_factor: float = 0.95
    fresh_stddev_multiplier: float = 2.0
    stale_stddev_multiplier: float = 4.0
    unavailable_stddev_multiplier: float = 8.0
    min_fresh_ms: int = 1
    max_fresh_ms: int = 60_000
    min_stale_ms: int = 2
    max_stale_ms: int = 120_000
    min_unavailable_ms: int = 3
    max_unavailable_ms: int = 300_000

    @property
    def version(self) -> str:
        return (
            f"{self.feed_kind}/{self.selector}:"
            f"{self.fresh_for_ms}-{self.stale_after_ms}-{self.unavailable_after_ms}ms:"
            f"adaptive={int(self.adaptive)}:min={self.minimum_samples}:"
            f"decay={self.decay_factor}:sigma={self.fresh_stddev_multiplier}-"
            f"{self.stale_stddev_multiplier}-{self.unavailable_stddev_multiplier}:"
            f"bounds={self.min_fresh_ms}-{self.max_fresh_ms}/"
            f"{self.min_stale_ms}-{self.max_stale_ms}/"
            f"{self.min_unavailable_ms}-{self.max_unavailable_ms}"
        )

    def effective(self, profile: RecencyProfile | None) -> EvidencePolicy:
        if not self.adaptive or profile is None or profile.sample_count < self.minimum_samples:
            return self
        deviation = sqrt(max(0.0, profile.variance_ms2))
        fresh = _bounded(
            profile.mean_interval_ms + self.fresh_stddev_multiplier * deviation,
            self.min_fresh_ms,
            self.max_fresh_ms,
        )
        stale = _bounded(
            profile.mean_interval_ms + self.stale_stddev_multiplier * deviation,
            max(self.min_stale_ms, fresh + 1),
            self.max_stale_ms,
        )
        unavailable = _bounded(
            profile.mean_interval_ms + self.unavailable_stddev_multiplier * deviation,
            max(self.min_unavailable_ms, stale + 1),
            self.max_unavailable_ms,
        )
        return EvidencePolicy(
            feed_kind=self.feed_kind,
            selector=self.selector,
            fresh_for_ms=fresh,
            stale_after_ms=stale,
            unavailable_after_ms=unavailable,
        )


@dataclass(slots=True)
class RecencyProfile:
    sample_count: int = 0
    mean_interval_ms: float = 0.0
    variance_ms2: float = 0.0
    last_observed_ns: int | None = None

    def observe(self, interval_ms: int, observed_ns: int, decay_factor: float) -> None:
        if interval_ms < 0:
            raise ValueError("recency interval must be non-negative")
        if self.sample_count == 0:
            self.mean_interval_ms = float(interval_ms)
            self.variance_ms2 = 0.0
        else:
            alpha = 1.0 - decay_factor
            delta = interval_ms - self.mean_interval_ms
            self.mean_interval_ms += alpha * delta
            self.variance_ms2 = decay_factor * (self.variance_ms2 + alpha * delta * delta)
        self.sample_count += 1
        self.last_observed_ns = observed_ns


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


def _bounded(value: float, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, round(value)))
