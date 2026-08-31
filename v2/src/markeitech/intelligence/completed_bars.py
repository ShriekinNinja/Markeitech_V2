from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from markeitech.intelligence.metrics import MetricFidelity, MetricHealth

COMPLETED_BAR_INPUT_TYPE_NAME = "markeitech.completed_bar.input"
"""Nautilus custom-data type name for normalized completed-bar inputs."""


class CompletedBarSource(StrEnum):
    """Lineage categories for provider and aggregated completed bars."""

    HISTORICAL_PROVIDER = "historical_provider"
    HISTORICAL_AGGREGATE = "historical_aggregate"
    LIVE_NATIVE = "live_native"
    LIVE_AGGREGATE = "live_aggregate"


class BarConflictPolicy(StrEnum):
    """Policies for handling conflicting observations with one completed-bar key."""

    REJECT_CONFLICT = "reject_conflict"


class BarAdmissionStatus(StrEnum):
    """Outcomes from admitting a completed bar to the first-accepted ledger."""

    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"


type CompletedBarKey = tuple[str, str, int]


@dataclass(frozen=True, slots=True)
class CompletedBarInput:
    """Represent one immutable completed-bar observation with analytical lineage.

    Interval and transport timestamps are UTC Unix nanoseconds. Prices and
    optional volume retain ``Decimal`` precision. Missing or partial evidence is
    expressed explicitly through health, fidelity, and reason fields.
    """

    instrument_id: str
    bar_specification: str
    calendar_id: str
    analytical_profile_id: str
    analytical_profile_version: int
    trade_date: date
    session_id: str
    window_id: str
    interval_start_ns: int
    interval_end_ns: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None
    source: CompletedBarSource
    observed_ts_ns: int
    received_ts_ns: int
    normalized_ts_ns: int
    health: MetricHealth
    fidelity: MetricFidelity
    evidence_refs: tuple[str, ...]
    complete: bool
    revision: int = 1
    missing_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field in (
            "instrument_id",
            "bar_specification",
            "calendar_id",
            "analytical_profile_id",
            "session_id",
            "window_id",
        ):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        _positive_int(self.analytical_profile_version, "analytical_profile_version")
        if not isinstance(self.trade_date, date):
            raise ValueError("trade_date must be a date")
        _timestamp(self.interval_start_ns, "interval_start_ns")
        _timestamp(self.interval_end_ns, "interval_end_ns")
        if self.interval_end_ns <= self.interval_start_ns:
            raise ValueError("interval_end_ns must be after interval_start_ns")
        for field in ("open", "high", "low", "close"):
            _positive_decimal(getattr(self, field), field)
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError("bar prices must satisfy low <= open/close <= high")
        if self.high < self.low:
            raise ValueError("high must not be below low")
        if self.volume is not None:
            _non_negative_decimal(self.volume, "volume")
        if not isinstance(self.source, CompletedBarSource):
            raise ValueError("source must be a CompletedBarSource")
        for field in ("observed_ts_ns", "received_ts_ns", "normalized_ts_ns"):
            _timestamp(getattr(self, field), field)
        if not self.observed_ts_ns <= self.received_ts_ns <= self.normalized_ts_ns:
            raise ValueError("bar timestamps must satisfy observed <= received <= normalized")
        if not isinstance(self.health, MetricHealth):
            raise ValueError("health must be a MetricHealth")
        if not isinstance(self.fidelity, MetricFidelity):
            raise ValueError("fidelity must be a MetricFidelity")
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence ref"))
        object.__setattr__(
            self,
            "missing_reasons",
            _text_tuple(self.missing_reasons, "missing reason"),
        )
        if not isinstance(self.complete, bool):
            raise ValueError("complete must be a boolean")
        _positive_int(self.revision, "revision")
        if not self.complete and "interval_incomplete" not in self.missing_reasons:
            raise ValueError("an incomplete bar must report interval_incomplete")
        if self.volume is None and not any(
            reason in self.missing_reasons
            for reason in ("volume_missing", "volume_unsupported", "volume_partial")
        ):
            raise ValueError("a bar without volume must report why volume is unavailable")

    @property
    def key(self) -> CompletedBarKey:
        return (self.instrument_id, self.bar_specification, self.interval_end_ns)

    @property
    def interval_ns(self) -> int:
        return self.interval_end_ns - self.interval_start_ns

    @property
    def ts_event(self) -> int:
        return self.interval_end_ns

    @property
    def ts_init(self) -> int:
        return self.normalized_ts_ns

    @property
    def equivalence_key(self) -> tuple[object, ...]:
        """Market and analytical identity, excluding transport-specific lineage."""
        return (
            self.instrument_id,
            self.bar_specification,
            self.calendar_id,
            self.analytical_profile_id,
            self.analytical_profile_version,
            self.trade_date,
            self.session_id,
            self.window_id,
            self.interval_start_ns,
            self.interval_end_ns,
            self.open,
            self.high,
            self.low,
            self.close,
            self.volume,
            self.complete,
            self.missing_reasons,
        )


@dataclass(frozen=True, slots=True)
class BarAdmission:
    """Report the candidate and canonical bar for one ledger admission attempt."""

    status: BarAdmissionStatus
    candidate: CompletedBarInput
    accepted: CompletedBarInput


class CompletedBarLedger:
    """Bounded first-accepted observation ledger with explicit conflict outcomes."""

    def __init__(
        self,
        *,
        maximum_observations: int,
        conflict_policy: BarConflictPolicy = BarConflictPolicy.REJECT_CONFLICT,
    ) -> None:
        _positive_int(maximum_observations, "maximum_observations")
        if not isinstance(conflict_policy, BarConflictPolicy):
            raise ValueError("conflict_policy must be a BarConflictPolicy")
        self._maximum_observations = maximum_observations
        self._conflict_policy = conflict_policy
        self._bars: dict[CompletedBarKey, CompletedBarInput] = {}

    @property
    def bars(self) -> tuple[CompletedBarInput, ...]:
        return tuple(self._bars[key] for key in sorted(self._bars))

    def admit(self, candidate: CompletedBarInput) -> BarAdmission:
        if not isinstance(candidate, CompletedBarInput):
            raise ValueError("candidate must be a CompletedBarInput")
        existing = self._bars.get(candidate.key)
        if existing is not None:
            status = (
                BarAdmissionStatus.DUPLICATE
                if candidate.equivalence_key == existing.equivalence_key
                else BarAdmissionStatus.CONFLICT
            )
            return BarAdmission(status=status, candidate=candidate, accepted=existing)

        self._bars[candidate.key] = candidate
        while len(self._bars) > self._maximum_observations:
            del self._bars[min(self._bars, key=lambda key: (key[2], key[0], key[1]))]
        return BarAdmission(
            status=BarAdmissionStatus.ACCEPTED,
            candidate=candidate,
            accepted=candidate,
        )


def aggregate_completed_bars(
    bars: tuple[CompletedBarInput, ...],
    *,
    target_bar_specification: str,
    target_interval_seconds: int,
    normalized_ts_ns: int,
    require_full_coverage: bool = True,
) -> CompletedBarInput:
    """Aggregate contiguous completed bars into one deterministic larger interval.

    Args:
        bars: Non-empty tuple of compatible, complete source bars.
        target_bar_specification: Identity assigned to the aggregated interval.
        target_interval_seconds: Positive target duration in seconds.
        normalized_ts_ns: UTC Unix nanosecond normalization timestamp.
        require_full_coverage: Require sources to span the complete target bucket.

    Returns:
        A derived completed bar retaining ordered source evidence lineage.

    Raises:
        ValueError: If bars are empty, incompatible, incomplete, discontinuous,
            outside one target bucket, or do not satisfy requested coverage.
    """

    if not isinstance(bars, tuple) or not bars:
        raise ValueError("bars must be a non-empty tuple")
    if any(not isinstance(bar, CompletedBarInput) for bar in bars):
        raise ValueError("bars must contain CompletedBarInput values")
    target_specification = _required_text(target_bar_specification, "target_bar_specification")
    _positive_int(target_interval_seconds, "target_interval_seconds")
    _timestamp(normalized_ts_ns, "normalized_ts_ns")
    if not isinstance(require_full_coverage, bool):
        raise ValueError("require_full_coverage must be a boolean")

    ordered = tuple(sorted(bars, key=lambda bar: (bar.interval_start_ns, bar.interval_end_ns)))
    first = ordered[0]
    target_interval_ns = target_interval_seconds * 1_000_000_000
    bucket_start_ns = first.interval_start_ns - first.interval_start_ns % target_interval_ns
    bucket_end_ns = bucket_start_ns + target_interval_ns
    identity = (
        first.instrument_id,
        first.bar_specification,
        first.calendar_id,
        first.analytical_profile_id,
        first.analytical_profile_version,
        first.trade_date,
        first.session_id,
        first.window_id,
    )
    for bar in ordered:
        if not bar.complete:
            raise ValueError("cannot aggregate incomplete bars")
        if (
            bar.instrument_id,
            bar.bar_specification,
            bar.calendar_id,
            bar.analytical_profile_id,
            bar.analytical_profile_version,
            bar.trade_date,
            bar.session_id,
            bar.window_id,
        ) != identity:
            raise ValueError("aggregation bars must share analytical identity")
        if bar.interval_ns != first.interval_ns:
            raise ValueError("aggregation bars must share one source interval")
        if bar.interval_start_ns < bucket_start_ns or bar.interval_end_ns > bucket_end_ns:
            raise ValueError("aggregation bars must occupy one target interval")
    for previous, current in zip(ordered, ordered[1:], strict=False):
        if previous.interval_end_ns != current.interval_start_ns:
            raise ValueError("aggregation bars must be contiguous and non-overlapping")
    if require_full_coverage and (
        ordered[0].interval_start_ns != bucket_start_ns
        or ordered[-1].interval_end_ns != bucket_end_ns
    ):
        raise ValueError("aggregation bars do not fully cover the target interval")
    if normalized_ts_ns < max(bar.received_ts_ns for bar in ordered):
        raise ValueError("normalized_ts_ns cannot precede a source receive timestamp")

    volumes = tuple(bar.volume for bar in ordered)
    volume = sum(volumes, Decimal(0)) if all(item is not None for item in volumes) else None
    missing_reasons = tuple(sorted({reason for bar in ordered for reason in bar.missing_reasons}))
    if volume is None and not any(
        reason in missing_reasons
        for reason in ("volume_missing", "volume_unsupported", "volume_partial")
    ):
        missing_reasons = (*missing_reasons, "volume_partial")

    sources = {bar.source for bar in ordered}
    source = (
        CompletedBarSource.HISTORICAL_AGGREGATE
        if sources
        <= {
            CompletedBarSource.HISTORICAL_PROVIDER,
            CompletedBarSource.HISTORICAL_AGGREGATE,
        }
        else CompletedBarSource.LIVE_AGGREGATE
    )
    health = _least_healthy(tuple(bar.health for bar in ordered))
    fidelity = MetricFidelity.DERIVED if health is MetricHealth.READY else MetricFidelity.PARTIAL
    return CompletedBarInput(
        instrument_id=first.instrument_id,
        bar_specification=target_specification,
        calendar_id=first.calendar_id,
        analytical_profile_id=first.analytical_profile_id,
        analytical_profile_version=first.analytical_profile_version,
        trade_date=first.trade_date,
        session_id=first.session_id,
        window_id=first.window_id,
        interval_start_ns=bucket_start_ns,
        interval_end_ns=bucket_end_ns,
        open=ordered[0].open,
        high=max(bar.high for bar in ordered),
        low=min(bar.low for bar in ordered),
        close=ordered[-1].close,
        volume=volume,
        source=source,
        observed_ts_ns=max(bar.observed_ts_ns for bar in ordered),
        received_ts_ns=max(bar.received_ts_ns for bar in ordered),
        normalized_ts_ns=normalized_ts_ns,
        health=health,
        fidelity=fidelity,
        evidence_refs=_ordered_unique(ref for bar in ordered for ref in bar.evidence_refs),
        complete=True,
        revision=max(bar.revision for bar in ordered),
        missing_reasons=missing_reasons,
    )


def _least_healthy(values: tuple[MetricHealth, ...]) -> MetricHealth:
    rank = {
        MetricHealth.READY: 0,
        MetricHealth.WARMING: 1,
        MetricHealth.DEGRADED: 2,
        MetricHealth.STALE: 3,
        MetricHealth.UNAVAILABLE: 4,
        MetricHealth.UNSUPPORTED: 5,
        MetricHealth.FAILED: 6,
    }
    return max(values, key=rank.__getitem__)


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _timestamp(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _positive_decimal(value: object, label: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ValueError(f"{label} must be a positive finite Decimal")


def _non_negative_decimal(value: object, label: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError(f"{label} must be a non-negative finite Decimal")


def _text_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ValueError(f"{label}s must be a tuple")
    normalized = tuple(_required_text(item, label) for item in value)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label}s must be unique")
    return normalized


def _ordered_unique(values: object) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))  # type: ignore[arg-type]
