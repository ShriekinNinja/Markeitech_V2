from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum
from typing import Any

from markeitech.intelligence._contract_validation import (
    bounded_ascii,
    canonical_bytes,
    canonical_digest,
    decimal_value,
    digest,
    evidence_references,
    positive_int,
    positive_int64,
)
from markeitech.intelligence.completed_bar_messages import (
    BarCompletionState,
    CompletedBarInputIdentity,
    CompletedBarLineageEntry,
    CompletedBarSeriesIdentity,
    VolumeState,
)
from markeitech.intelligence.metric_messages import MetricFidelity, MetricHealth

MAXIMUM_HISTORICAL_REQUEST_INTERVALS = 15
MAXIMUM_HISTORICAL_RAW_OBSERVATIONS = 16


class _HistoricalUsage(StrEnum):
    CANONICAL_SERIES_BOOTSTRAP = "canonical_series_bootstrap"
    BOUNDED_BATCH_CALCULATION = "bounded_batch_calculation"


class _HistoricalValidationDisposition(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"


class _HistoricalValidationReason(StrEnum):
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    ORDERING_INVALID = "ORDERING_INVALID"
    OUTSIDE_REQUEST_BOUNDS = "OUTSIDE_REQUEST_BOUNDS"
    INTERVAL_MISMATCH = "INTERVAL_MISMATCH"
    UNEQUAL_INTERVAL_CONFLICT = "UNEQUAL_INTERVAL_CONFLICT"
    REVISION_REJECTED = "REVISION_REJECTED"
    MISSING_INTERVALS = "MISSING_INTERVALS"
    PARTIAL_OBSERVATION = "PARTIAL_OBSERVATION"
    EMPTY_BATCH = "EMPTY_BATCH"


_REASON_ORDER = {reason: index for index, reason in enumerate(_HistoricalValidationReason)}
_HEALTH_RANK = {
    MetricHealth.READY: 0,
    MetricHealth.WARMING: 1,
    MetricHealth.DEGRADED: 2,
    MetricHealth.STALE: 3,
    MetricHealth.UNAVAILABLE: 4,
    MetricHealth.UNSUPPORTED: 5,
    MetricHealth.FAILED: 6,
}
_FIDELITY_RANK = {
    MetricFidelity.REPORTED: 0,
    MetricFidelity.DERIVED: 1,
    MetricFidelity.INFERRED: 2,
    MetricFidelity.PARTIAL: 3,
    MetricFidelity.UNAVAILABLE: 4,
}


@dataclass(frozen=True, slots=True)
class _HistoricalBarObservation:
    series_identity: CompletedBarSeriesIdentity
    interval_start_ns: int
    interval_end_ns: int
    completion_state: BarCompletionState
    expected_constituent_count: int
    received_constituent_count: int
    missing_subintervals: tuple[tuple[int, int], ...]
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None
    volume_state: VolumeState
    source_revision: int
    health: MetricHealth
    fidelity: MetricFidelity
    lineage: tuple[CompletedBarLineageEntry, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.series_identity, CompletedBarSeriesIdentity):
            raise ValueError("series_identity must be a CompletedBarSeriesIdentity")
        positive_int64(self.interval_start_ns, "interval_start_ns")
        positive_int64(self.interval_end_ns, "interval_end_ns")
        if self.interval_end_ns - self.interval_start_ns != self.series_identity.interval_ns:
            raise ValueError("historical observation interval must match its series identity")
        if not isinstance(self.completion_state, BarCompletionState):
            raise ValueError("completion_state must be a BarCompletionState")
        positive_int(self.expected_constituent_count, "expected_constituent_count")
        positive_int(self.received_constituent_count, "received_constituent_count")
        if self.received_constituent_count > self.expected_constituent_count:
            raise ValueError("received constituents cannot exceed expected constituents")
        if not isinstance(self.missing_subintervals, tuple):
            raise ValueError("missing_subintervals must be a tuple")
        if len(self.missing_subintervals) != (
            self.expected_constituent_count - self.received_constituent_count
        ):
            raise ValueError("historical constituent accounting must reconcile")
        if self.series_identity.interval_ns % self.expected_constituent_count:
            raise ValueError("historical interval must divide into exact constituent slots")
        constituent_interval_ns = (
            self.series_identity.interval_ns // self.expected_constituent_count
        )
        previous_end = self.interval_start_ns
        for start_ns, end_ns in self.missing_subintervals:
            positive_int64(start_ns, "missing interval start")
            positive_int64(end_ns, "missing interval end")
            if (
                start_ns < self.interval_start_ns
                or end_ns > self.interval_end_ns
                or end_ns <= start_ns
            ):
                raise ValueError("missing subinterval must be contained by the observation")
            if start_ns < previous_end:
                raise ValueError(
                    "missing subintervals must be unique, ordered, and non-overlapping"
                )
            if (
                end_ns - start_ns != constituent_interval_ns
                or (start_ns - self.interval_start_ns) % constituent_interval_ns
            ):
                raise ValueError("missing subintervals must be exact constituent slots")
            previous_end = end_ns
        if self.completion_state is BarCompletionState.COMPLETE and self.missing_subintervals:
            raise ValueError("COMPLETE historical observations cannot have missing subintervals")
        if self.completion_state is BarCompletionState.PARTIAL and not self.missing_subintervals:
            raise ValueError("PARTIAL historical observations require missing subintervals")
        for field_name in ("open", "high", "low", "close"):
            decimal_value(getattr(self, field_name), field_name)
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("historical OHLC values are inconsistent")
        if not isinstance(self.volume_state, VolumeState):
            raise ValueError("volume_state must be a VolumeState")
        if self.volume_state in {VolumeState.OBSERVED, VolumeState.PARTIAL}:
            if self.volume is None:
                raise ValueError("observed historical volume requires a value")
            decimal_value(self.volume, "volume")
            if self.volume < 0:
                raise ValueError("volume cannot be negative")
        elif self.volume is not None:
            raise ValueError("missing historical volume requires a null value")
        positive_int(self.source_revision, "source_revision")
        if not isinstance(self.health, MetricHealth):
            raise ValueError("health must be a MetricHealth")
        if not isinstance(self.fidelity, MetricFidelity):
            raise ValueError("fidelity must be a MetricFidelity")
        if self.completion_state is BarCompletionState.COMPLETE and (
            self.health is not MetricHealth.READY
            or self.fidelity not in {MetricFidelity.REPORTED, MetricFidelity.DERIVED}
        ):
            raise ValueError(
                "COMPLETE historical observations require READY valid reported or derived evidence",
            )
        if self.completion_state is BarCompletionState.PARTIAL and (
            self.health is not MetricHealth.DEGRADED or self.fidelity is not MetricFidelity.PARTIAL
        ):
            raise ValueError(
                "PARTIAL historical observations require DEGRADED health and PARTIAL fidelity",
            )
        if (
            not isinstance(self.lineage, tuple)
            or not self.lineage
            or any(not isinstance(item, CompletedBarLineageEntry) for item in self.lineage)
        ):
            raise ValueError("lineage must contain typed entries")
        if len(self.lineage) > 64 or len(self.lineage) != len(set(self.lineage)):
            raise ValueError("lineage must contain at most 64 unique entries")
        object.__setattr__(self, "evidence_refs", evidence_references(self.evidence_refs))

    @property
    def key(self) -> tuple[str, int, int]:
        return (
            self.series_identity.series_id,
            self.interval_start_ns,
            self.interval_end_ns,
        )

    @property
    def equivalence_key(self) -> tuple[object, ...]:
        return (
            self.series_identity,
            self.interval_start_ns,
            self.interval_end_ns,
            self.completion_state,
            self.expected_constituent_count,
            self.received_constituent_count,
            self.missing_subintervals,
            self.open,
            self.high,
            self.low,
            self.close,
            self.volume,
            self.volume_state,
            self.source_revision,
            self.health,
            self.fidelity,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "series_identity": self.series_identity.to_dict(),
            "interval_start_ns": self.interval_start_ns,
            "interval_end_ns": self.interval_end_ns,
            "completion_state": self.completion_state.value,
            "expected_constituent_count": self.expected_constituent_count,
            "received_constituent_count": self.received_constituent_count,
            "missing_subintervals": [list(item) for item in self.missing_subintervals],
            "open": str(self.open),
            "high": str(self.high),
            "low": str(self.low),
            "close": str(self.close),
            "volume": None if self.volume is None else str(self.volume),
            "volume_state": self.volume_state.value,
            "source_revision": self.source_revision,
            "health": self.health.value,
            "fidelity": self.fidelity.value,
            "lineage": [item.to_dict() for item in self.lineage],
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class _HistoricalValidationRequest:
    request_id: str
    request_digest: str
    usage: _HistoricalUsage
    series_identity: CompletedBarSeriesIdentity
    expected_input_identity: CompletedBarInputIdentity
    requested_start_ns: int
    requested_end_ns: int
    maximum_raw_observations: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", bounded_ascii(self.request_id, "request_id"))
        object.__setattr__(self, "request_digest", digest(self.request_digest, "request_digest"))
        if not isinstance(self.usage, _HistoricalUsage):
            raise ValueError("usage must be a _HistoricalUsage")
        if not isinstance(self.series_identity, CompletedBarSeriesIdentity):
            raise ValueError("series_identity must be a CompletedBarSeriesIdentity")
        if not isinstance(self.expected_input_identity, CompletedBarInputIdentity):
            raise ValueError("expected_input_identity must be a CompletedBarInputIdentity")
        positive_int64(self.requested_start_ns, "requested_start_ns")
        positive_int64(self.requested_end_ns, "requested_end_ns")
        if self.requested_end_ns <= self.requested_start_ns:
            raise ValueError("requested_end_ns must be after requested_start_ns")
        if (self.requested_end_ns - self.requested_start_ns) % self.series_identity.interval_ns:
            raise ValueError("historical bounds must align to complete series intervals")
        positive_int(self.maximum_raw_observations, "maximum_raw_observations")
        if self.maximum_raw_observations < self.expected_observation_count:
            raise ValueError("maximum_raw_observations cannot be below requested interval count")
        if self.expected_observation_count > MAXIMUM_HISTORICAL_REQUEST_INTERVALS:
            raise ValueError("historical requests cannot exceed the 15-interval Slice 1 ceiling")
        if self.maximum_raw_observations > MAXIMUM_HISTORICAL_RAW_OBSERVATIONS:
            raise ValueError("maximum_raw_observations cannot exceed the 16-observation ceiling")
        expected_digest = canonical_digest(self._digest_content())
        if self.request_digest != expected_digest:
            raise ValueError("request_digest does not match the historical request content")

    @property
    def expected_observation_count(self) -> int:
        return (self.requested_end_ns - self.requested_start_ns) // self.series_identity.interval_ns

    def _digest_content(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "usage": self.usage.value,
            "series_identity_digest": self.series_identity.identity_digest,
            "expected_input_identity": self.expected_input_identity.to_dict(),
            "requested_start_ns": self.requested_start_ns,
            "requested_end_ns": self.requested_end_ns,
            "maximum_raw_observations": self.maximum_raw_observations,
        }

    @classmethod
    def build(
        cls,
        *,
        request_id: str,
        usage: _HistoricalUsage,
        series_identity: CompletedBarSeriesIdentity,
        expected_input_identity: CompletedBarInputIdentity,
        requested_start_ns: int,
        requested_end_ns: int,
        maximum_raw_observations: int,
    ) -> _HistoricalValidationRequest:
        content = {
            "request_id": request_id,
            "usage": usage.value,
            "series_identity_digest": series_identity.identity_digest,
            "expected_input_identity": expected_input_identity.to_dict(),
            "requested_start_ns": requested_start_ns,
            "requested_end_ns": requested_end_ns,
            "maximum_raw_observations": maximum_raw_observations,
        }
        return cls(
            request_id=request_id,
            request_digest=canonical_digest(content),
            usage=usage,
            series_identity=series_identity,
            expected_input_identity=expected_input_identity,
            requested_start_ns=requested_start_ns,
            requested_end_ns=requested_end_ns,
            maximum_raw_observations=maximum_raw_observations,
        )


@dataclass(frozen=True, slots=True)
class _HistoricalValidationResult:
    request_id: str
    request_digest: str
    usage: _HistoricalUsage
    series_identity: CompletedBarSeriesIdentity
    expected_input_identity: CompletedBarInputIdentity
    requested_start_ns: int
    requested_end_ns: int
    disposition: _HistoricalValidationDisposition
    raw_count: int
    accepted_unique_count: int
    duplicate_count: int
    conflict_count: int
    gap_count: int
    missing_intervals: tuple[tuple[int, int], ...]
    health: MetricHealth
    fidelity: MetricFidelity
    lineage: tuple[CompletedBarLineageEntry, ...]
    evidence_refs: tuple[str, ...]
    reasons: tuple[_HistoricalValidationReason, ...]
    observations: tuple[_HistoricalBarObservation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", bounded_ascii(self.request_id, "request_id"))
        object.__setattr__(self, "request_digest", digest(self.request_digest, "request_digest"))
        if not isinstance(self.usage, _HistoricalUsage):
            raise ValueError("usage must be typed")
        if not isinstance(self.series_identity, CompletedBarSeriesIdentity):
            raise ValueError("series_identity must be typed")
        if not isinstance(self.expected_input_identity, CompletedBarInputIdentity):
            raise ValueError("expected_input_identity must be typed")
        positive_int64(self.requested_start_ns, "requested_start_ns")
        positive_int64(self.requested_end_ns, "requested_end_ns")
        if self.requested_end_ns <= self.requested_start_ns:
            raise ValueError("requested historical result bounds are invalid")
        if not isinstance(self.disposition, _HistoricalValidationDisposition):
            raise ValueError("disposition must be typed")
        for field_name in (
            "raw_count",
            "accepted_unique_count",
            "duplicate_count",
            "conflict_count",
            "gap_count",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if (
            self.raw_count
            != self.accepted_unique_count + self.duplicate_count + self.conflict_count
        ):
            raise ValueError("historical validation counts must reconcile")
        if self.gap_count != len(self.missing_intervals):
            raise ValueError("gap_count must match missing_intervals")
        if not isinstance(self.missing_intervals, tuple):
            raise ValueError("missing_intervals must be a tuple")
        expected_interval_ns = self.series_identity.interval_ns
        prior_missing_start: int | None = None
        for start_ns, end_ns in self.missing_intervals:
            positive_int64(start_ns, "missing interval start")
            positive_int64(end_ns, "missing interval end")
            if (
                end_ns - start_ns != expected_interval_ns
                or start_ns < self.requested_start_ns
                or end_ns > self.requested_end_ns
            ):
                raise ValueError("missing intervals must be exact requested series intervals")
            if prior_missing_start is not None and start_ns <= prior_missing_start:
                raise ValueError("missing intervals must be unique and ordered")
            prior_missing_start = start_ns
        if not isinstance(self.health, MetricHealth):
            raise ValueError("health must be typed")
        if not isinstance(self.fidelity, MetricFidelity):
            raise ValueError("fidelity must be typed")
        if not isinstance(self.lineage, tuple) or any(
            not isinstance(item, CompletedBarLineageEntry) for item in self.lineage
        ):
            raise ValueError("lineage must be a typed tuple")
        if len(self.lineage) > 64 or len(self.lineage) != len(set(self.lineage)):
            raise ValueError("lineage must contain at most 64 unique entries")
        object.__setattr__(self, "evidence_refs", evidence_references(self.evidence_refs))
        if not isinstance(self.reasons, tuple) or any(
            not isinstance(reason, _HistoricalValidationReason) for reason in self.reasons
        ):
            raise ValueError("historical validation reasons must be typed")
        if tuple(sorted(self.reasons, key=_REASON_ORDER.__getitem__)) != self.reasons:
            raise ValueError("historical validation reasons must use canonical order")
        if len(self.reasons) != len(set(self.reasons)):
            raise ValueError("historical validation reasons must be unique")
        if not isinstance(self.observations, tuple) or any(
            not isinstance(item, _HistoricalBarObservation) for item in self.observations
        ):
            raise ValueError("observations must be a typed tuple")
        observation_keys = tuple(item.key for item in self.observations)
        if observation_keys != tuple(
            sorted(observation_keys, key=lambda item: (item[1], item[2], item[0]))
        ) or len(observation_keys) != len(set(observation_keys)):
            raise ValueError("usable historical observations must be unique and ordered")
        if any(
            item.series_identity != self.series_identity
            or item.interval_start_ns < self.requested_start_ns
            or item.interval_end_ns > self.requested_end_ns
            for item in self.observations
        ):
            raise ValueError("usable observations must match the result identity and bounds")
        if self.disposition is _HistoricalValidationDisposition.REJECTED:
            if self.observations:
                raise ValueError("REJECTED validation must expose no usable observations")
        elif len(self.observations) != self.accepted_unique_count:
            raise ValueError("usable observation count must match accepted_unique_count")
        expected_count = (
            self.requested_end_ns - self.requested_start_ns
        ) // self.series_identity.interval_ns
        if self.disposition is _HistoricalValidationDisposition.COMPLETE:
            if (
                self.accepted_unique_count != expected_count
                or self.gap_count
                or self.conflict_count
                or self.reasons
                or self.health is not MetricHealth.READY
                or self.fidelity not in {MetricFidelity.REPORTED, MetricFidelity.DERIVED}
            ):
                raise ValueError(
                    "COMPLETE historical results require exact valid requested evidence"
                )
        elif self.disposition is _HistoricalValidationDisposition.PARTIAL:
            if not self.reasons:
                raise ValueError("PARTIAL historical results require typed reasons")
            if self.observations:
                if (
                    self.health is not MetricHealth.DEGRADED
                    or self.fidelity is not MetricFidelity.PARTIAL
                ):
                    raise ValueError(
                        "PARTIAL historical results with evidence require DEGRADED/PARTIAL state",
                    )
            elif (
                self.health is not MetricHealth.UNAVAILABLE
                or self.fidelity is not MetricFidelity.UNAVAILABLE
            ):
                raise ValueError(
                    "empty PARTIAL historical results require UNAVAILABLE evidence state",
                )
        elif (
            self.health is not MetricHealth.FAILED
            or self.fidelity is not MetricFidelity.UNAVAILABLE
            or not self.reasons
        ):
            raise ValueError("REJECTED historical results require FAILED unavailable evidence")

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "request_digest": self.request_digest,
            "usage": self.usage.value,
            "series_identity": self.series_identity.to_dict(),
            "expected_input_identity": self.expected_input_identity.to_dict(),
            "requested_start_ns": self.requested_start_ns,
            "requested_end_ns": self.requested_end_ns,
            "disposition": self.disposition.value,
            "raw_count": self.raw_count,
            "accepted_unique_count": self.accepted_unique_count,
            "duplicate_count": self.duplicate_count,
            "conflict_count": self.conflict_count,
            "gap_count": self.gap_count,
            "missing_intervals": [list(item) for item in self.missing_intervals],
            "health": self.health.value,
            "fidelity": self.fidelity.value,
            "lineage": [item.to_dict() for item in self.lineage],
            "evidence_refs": list(self.evidence_refs),
            "reasons": [reason.value for reason in self.reasons],
            "observations": [item.to_dict() for item in self.observations],
        }

    def to_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())


def _validate_historical_batch(
    request: _HistoricalValidationRequest,
    observations: tuple[_HistoricalBarObservation, ...],
) -> _HistoricalValidationResult:
    if not isinstance(request, _HistoricalValidationRequest):
        raise ValueError("request must be a _HistoricalValidationRequest")
    if not isinstance(observations, tuple) or any(
        not isinstance(item, _HistoricalBarObservation) for item in observations
    ):
        raise ValueError("observations must be a typed tuple")
    if len(observations) > request.maximum_raw_observations:
        raise ValueError("raw historical batch exceeds its configured hard bound")

    accepted: dict[tuple[str, int, int], _HistoricalBarObservation] = {}
    duplicates = 0
    conflicts = 0
    rejection_reasons: set[_HistoricalValidationReason] = set()
    prior_start: int | None = None
    for observation in observations:
        if observation.series_identity != request.series_identity or any(
            item.source_class != "HISTORICAL"
            or item.input_identity != request.expected_input_identity
            for item in observation.lineage
        ):
            rejection_reasons.add(_HistoricalValidationReason.IDENTITY_MISMATCH)
        if observation.source_revision != 1:
            rejection_reasons.add(_HistoricalValidationReason.REVISION_REJECTED)
        if (
            observation.interval_start_ns < request.requested_start_ns
            or observation.interval_end_ns > request.requested_end_ns
        ):
            rejection_reasons.add(_HistoricalValidationReason.OUTSIDE_REQUEST_BOUNDS)
        if prior_start is not None and observation.interval_start_ns < prior_start:
            rejection_reasons.add(_HistoricalValidationReason.ORDERING_INVALID)
        prior_start = observation.interval_start_ns
        existing = accepted.get(observation.key)
        if existing is None:
            accepted[observation.key] = observation
        elif existing.equivalence_key == observation.equivalence_key:
            duplicates += 1
            accepted[observation.key] = _merge_duplicate_observations(existing, observation)
        else:
            conflicts += 1
            rejection_reasons.add(_HistoricalValidationReason.UNEQUAL_INTERVAL_CONFLICT)

    ordered = tuple(sorted(accepted.values(), key=lambda item: item.interval_start_ns))
    expected_intervals = tuple(
        (
            start_ns,
            start_ns + request.series_identity.interval_ns,
        )
        for start_ns in range(
            request.requested_start_ns,
            request.requested_end_ns,
            request.series_identity.interval_ns,
        )
    )
    observed_intervals = {(item.interval_start_ns, item.interval_end_ns) for item in ordered}
    missing = tuple(item for item in expected_intervals if item not in observed_intervals)
    partial_present = any(item.completion_state is BarCompletionState.PARTIAL for item in ordered)
    if missing:
        rejection_reasons.add(_HistoricalValidationReason.MISSING_INTERVALS)
    if partial_present:
        rejection_reasons.add(_HistoricalValidationReason.PARTIAL_OBSERVATION)
    if not observations:
        rejection_reasons.add(_HistoricalValidationReason.EMPTY_BATCH)

    hard_rejection = bool(
        rejection_reasons
        & {
            _HistoricalValidationReason.IDENTITY_MISMATCH,
            _HistoricalValidationReason.SCHEMA_MISMATCH,
            _HistoricalValidationReason.ORDERING_INVALID,
            _HistoricalValidationReason.OUTSIDE_REQUEST_BOUNDS,
            _HistoricalValidationReason.INTERVAL_MISMATCH,
            _HistoricalValidationReason.UNEQUAL_INTERVAL_CONFLICT,
            _HistoricalValidationReason.REVISION_REJECTED,
        },
    )
    if hard_rejection:
        disposition = _HistoricalValidationDisposition.REJECTED
        usable: tuple[_HistoricalBarObservation, ...] = ()
    elif missing or partial_present or not observations:
        disposition = _HistoricalValidationDisposition.PARTIAL
        usable = ordered
    else:
        disposition = _HistoricalValidationDisposition.COMPLETE
        usable = ordered
    lineage = _ordered_unique_lineage(
        item for observation in ordered for item in observation.lineage
    )
    refs = evidence_references(
        ref
        for observation in ordered
        for ref in (
            *observation.evidence_refs,
            *(item.provider_observation_ref for item in observation.lineage),
            *(lineage_ref for item in observation.lineage for lineage_ref in item.evidence_refs),
        )
    )
    health = (
        max((item.health for item in ordered), key=_HEALTH_RANK.__getitem__)
        if ordered
        else MetricHealth.UNAVAILABLE
    )
    fidelity = (
        max((item.fidelity for item in ordered), key=_FIDELITY_RANK.__getitem__)
        if ordered
        else MetricFidelity.UNAVAILABLE
    )
    if disposition is _HistoricalValidationDisposition.PARTIAL:
        health = max((health, MetricHealth.DEGRADED), key=_HEALTH_RANK.__getitem__)
        fidelity = max((fidelity, MetricFidelity.PARTIAL), key=_FIDELITY_RANK.__getitem__)
    if disposition is _HistoricalValidationDisposition.REJECTED:
        health = MetricHealth.FAILED
        fidelity = MetricFidelity.UNAVAILABLE
    reasons = tuple(sorted(rejection_reasons, key=_REASON_ORDER.__getitem__))
    return _HistoricalValidationResult(
        request_id=request.request_id,
        request_digest=request.request_digest,
        usage=request.usage,
        series_identity=request.series_identity,
        expected_input_identity=request.expected_input_identity,
        requested_start_ns=request.requested_start_ns,
        requested_end_ns=request.requested_end_ns,
        disposition=disposition,
        raw_count=len(observations),
        accepted_unique_count=len(accepted),
        duplicate_count=duplicates,
        conflict_count=conflicts,
        gap_count=len(missing),
        missing_intervals=missing,
        health=health,
        fidelity=fidelity,
        lineage=lineage,
        evidence_refs=refs,
        reasons=reasons,
        observations=usable,
    )


def _canonical_admission_observations(
    result: _HistoricalValidationResult,
) -> tuple[_HistoricalBarObservation, ...]:
    if result.usage is not _HistoricalUsage.CANONICAL_SERIES_BOOTSTRAP:
        raise ValueError("bounded batch calculations cannot enter canonical admission")
    if result.disposition is _HistoricalValidationDisposition.REJECTED:
        return ()
    return result.observations


def _bounded_calculation_observations(
    result: _HistoricalValidationResult,
) -> tuple[_HistoricalBarObservation, ...]:
    if result.usage is not _HistoricalUsage.BOUNDED_BATCH_CALCULATION:
        raise ValueError("canonical bootstrap history cannot use the local calculation path")
    if result.disposition is _HistoricalValidationDisposition.REJECTED:
        return ()
    return result.observations


def _merge_duplicate_observations(
    first: _HistoricalBarObservation,
    second: _HistoricalBarObservation,
) -> _HistoricalBarObservation:
    return replace(
        first,
        lineage=_ordered_unique_lineage((*first.lineage, *second.lineage)),
        evidence_refs=evidence_references((*first.evidence_refs, *second.evidence_refs)),
    )


def _ordered_unique_lineage(
    values: Any,
) -> tuple[CompletedBarLineageEntry, ...]:
    result: list[CompletedBarLineageEntry] = []
    seen: set[CompletedBarLineageEntry] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    if len(result) > 64:
        raise ValueError("historical lineage exceeds the 64-entry payload bound")
    return tuple(result)
