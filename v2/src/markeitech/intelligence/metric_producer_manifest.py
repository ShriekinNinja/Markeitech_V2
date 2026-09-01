from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID

from markeitech.intelligence._contract_validation import (
    bounded_ascii,
    canonical_bytes,
    canonical_digest,
    digest,
    positive_int,
    positive_int64,
    topic_token,
    uuid_value,
)
from markeitech.intelligence.completed_bar_messages import CompletedBarSeriesIdentity
from markeitech.intelligence.metric_messages import MetricSubjectIdentity

MAXIMUM_SERIES_PER_INSTANCE = 16
MAXIMUM_TOTAL_SERIES = 64
MAXIMUM_RETAINED_COMPLETED_BARS = 16
MAXIMUM_HISTORY_LIVE_OVERLAP_BARS = 1
MAXIMUM_BUFFERED_LIVE_COMPLETED_BARS = 2
CONSUMER_READINESS_TIMEOUT_MS = 5_000


class _ActivationDisposition(StrEnum):
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    SHADOW = "SHADOW"


@dataclass(frozen=True, slots=True)
class _FoundationInstanceAssignment:
    actor_id: str
    series_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "actor_id", bounded_ascii(self.actor_id, "actor_id"))
        if not isinstance(self.series_ids, tuple) or not self.series_ids:
            raise ValueError("series_ids must be a non-empty tuple")
        normalized = tuple(topic_token(series_id) for series_id in self.series_ids)
        if len(normalized) != len(set(normalized)):
            raise ValueError("an instance cannot assign the same series more than once")
        if len(normalized) > MAXIMUM_SERIES_PER_INSTANCE:
            raise ValueError("a foundation instance cannot own more than 16 series")
        if normalized != tuple(sorted(normalized)):
            raise ValueError("instance series_ids must use deterministic sorted order")
        object.__setattr__(self, "series_ids", normalized)


@dataclass(frozen=True, slots=True)
class _BarSeriesProducerClaim:
    series_identity: CompletedBarSeriesIdentity
    producer_actor_id: str
    producer_version: int
    output_schema_version: int
    dependencies: tuple[str, ...]
    activation: _ActivationDisposition
    maximum_retained_completed_bars: int
    maximum_history_live_overlap_bars: int
    maximum_buffered_live_completed_bars: int

    def __post_init__(self) -> None:
        if not isinstance(self.series_identity, CompletedBarSeriesIdentity):
            raise ValueError("series_identity must be a CompletedBarSeriesIdentity")
        object.__setattr__(
            self,
            "producer_actor_id",
            bounded_ascii(self.producer_actor_id, "producer_actor_id"),
        )
        if self.producer_actor_id != self.series_identity.canonical_producer_id:
            raise ValueError("bar claim producer must match the complete series identity")
        positive_int(self.producer_version, "producer_version")
        positive_int(self.output_schema_version, "output_schema_version")
        if self.output_schema_version != self.series_identity.output_schema_version:
            raise ValueError("bar claim schema must match the complete series identity")
        object.__setattr__(
            self, "dependencies", _sorted_identifiers(self.dependencies, "dependencies")
        )
        if not isinstance(self.activation, _ActivationDisposition):
            raise ValueError("activation must be an _ActivationDisposition")
        for field_name in (
            "maximum_retained_completed_bars",
            "maximum_history_live_overlap_bars",
            "maximum_buffered_live_completed_bars",
        ):
            positive_int(getattr(self, field_name), field_name)
        ceilings = {
            "maximum_retained_completed_bars": MAXIMUM_RETAINED_COMPLETED_BARS,
            "maximum_history_live_overlap_bars": MAXIMUM_HISTORY_LIVE_OVERLAP_BARS,
            "maximum_buffered_live_completed_bars": MAXIMUM_BUFFERED_LIVE_COMPLETED_BARS,
        }
        for field_name, ceiling in ceilings.items():
            if getattr(self, field_name) > ceiling:
                raise ValueError(f"{field_name} cannot exceed the Slice 1 ceiling of {ceiling}")

    @property
    def series_id(self) -> str:
        return self.series_identity.series_id


@dataclass(frozen=True, slots=True)
class _MetricProducerClaim:
    claim_id: str
    subject: MetricSubjectIdentity
    producer_actor_id: str
    producer_version: int
    output_schema_version: int
    input_series_ids: tuple[str, ...]
    dependency_claim_ids: tuple[str, ...]
    parameter_set_id: str
    activation: _ActivationDisposition

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim_id", bounded_ascii(self.claim_id, "claim_id"))
        if not isinstance(self.subject, MetricSubjectIdentity):
            raise ValueError("subject must be a MetricSubjectIdentity")
        object.__setattr__(
            self,
            "producer_actor_id",
            bounded_ascii(self.producer_actor_id, "producer_actor_id"),
        )
        if self.producer_actor_id != self.subject.canonical_producer_id:
            raise ValueError("metric claim producer must match the complete subject identity")
        positive_int(self.producer_version, "producer_version")
        positive_int(self.output_schema_version, "output_schema_version")
        if self.output_schema_version != self.subject.output_schema_version:
            raise ValueError("metric claim schema must match the complete subject identity")
        normalized_series = tuple(topic_token(item) for item in self.input_series_ids)
        if normalized_series != tuple(sorted(set(normalized_series))):
            raise ValueError("input_series_ids must be unique and sorted")
        object.__setattr__(self, "input_series_ids", normalized_series)
        object.__setattr__(
            self,
            "dependency_claim_ids",
            _sorted_identifiers(self.dependency_claim_ids, "dependency_claim_ids"),
        )
        object.__setattr__(
            self,
            "parameter_set_id",
            bounded_ascii(self.parameter_set_id, "parameter_set_id"),
        )
        if not isinstance(self.activation, _ActivationDisposition):
            raise ValueError("activation must be an _ActivationDisposition")
        if self.subject.input_series_id is not None and (
            self.subject.input_series_id not in self.input_series_ids
        ):
            raise ValueError("complete subject input series must be declared by the metric claim")


@dataclass(frozen=True, slots=True)
class _ProducerManifestV1:
    configuration_epoch: UUID
    configuration_digest: str
    instance_assignments: tuple[_FoundationInstanceAssignment, ...]
    bar_claims: tuple[_BarSeriesProducerClaim, ...]
    metric_claims: tuple[_MetricProducerClaim, ...]
    manifest_schema_version: int = 1
    manifest_digest: str = field(init=False)

    def __post_init__(self) -> None:
        uuid_value(self.configuration_epoch, "configuration_epoch")
        object.__setattr__(
            self,
            "configuration_digest",
            digest(self.configuration_digest, "configuration_digest"),
        )
        if self.manifest_schema_version != 1:
            raise ValueError("manifest_schema_version must be 1")
        self._validate_sorted_inputs()
        self._validate_assignments()
        self._validate_metric_claims()
        object.__setattr__(self, "manifest_digest", canonical_digest(self._content_dict()))

    def _validate_sorted_inputs(self) -> None:
        if not isinstance(self.instance_assignments, tuple) or any(
            not isinstance(item, _FoundationInstanceAssignment)
            for item in self.instance_assignments
        ):
            raise ValueError("instance_assignments must contain typed values")
        if not isinstance(self.bar_claims, tuple) or any(
            not isinstance(item, _BarSeriesProducerClaim) for item in self.bar_claims
        ):
            raise ValueError("bar_claims must contain typed values")
        if not isinstance(self.metric_claims, tuple) or any(
            not isinstance(item, _MetricProducerClaim) for item in self.metric_claims
        ):
            raise ValueError("metric_claims must contain typed values")
        if tuple(item.actor_id for item in self.instance_assignments) != tuple(
            sorted(item.actor_id for item in self.instance_assignments)
        ):
            raise ValueError("instance assignments must use deterministic actor order")
        bar_series_ids = tuple(item.series_id for item in self.bar_claims)
        if bar_series_ids != tuple(sorted(set(bar_series_ids))):
            raise ValueError("bar claims must use unique deterministic series order")
        if tuple(item.claim_id for item in self.metric_claims) != tuple(
            sorted(item.claim_id for item in self.metric_claims)
        ):
            raise ValueError("metric claims must use deterministic claim order")

    def _validate_assignments(self) -> None:
        actor_ids = tuple(item.actor_id for item in self.instance_assignments)
        if len(actor_ids) != len(set(actor_ids)):
            raise ValueError("foundation instance actor IDs must be unique")
        enabled_series = {
            claim.series_id
            for claim in self.bar_claims
            if claim.activation is _ActivationDisposition.ENABLED
        }
        if len(enabled_series) > MAXIMUM_TOTAL_SERIES:
            raise ValueError("enabled canonical series cannot exceed the 64-series total ceiling")
        for claim in self.bar_claims:
            if (
                claim.series_identity.configuration_epoch != self.configuration_epoch
                or claim.series_identity.configuration_digest != self.configuration_digest
            ):
                raise ValueError("bar claim configuration must match the manifest authority")
        assignments: dict[str, str] = {}
        for instance in self.instance_assignments:
            for series_id in instance.series_ids:
                if series_id in assignments:
                    raise ValueError(f"series assigned to more than one instance: {series_id}")
                assignments[series_id] = instance.actor_id
        unknown = set(assignments) - enabled_series
        if unknown:
            raise ValueError(
                f"instance assignments reference unknown or disabled series: {sorted(unknown)!r}"
            )
        missing = enabled_series - set(assignments)
        if missing:
            raise ValueError(f"enabled canonical series are unassigned: {sorted(missing)!r}")
        for claim in self.bar_claims:
            if claim.activation is _ActivationDisposition.ENABLED:
                instance_actor_id = assignments[claim.series_id]
                if instance_actor_id != claim.producer_actor_id:
                    raise ValueError("series assignment actor must match its canonical producer")

    def _validate_metric_claims(self) -> None:
        claim_ids = tuple(item.claim_id for item in self.metric_claims)
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("metric claim IDs must be unique")
        enabled_subjects: dict[str, str] = {}
        enabled_series = {
            item.series_id
            for item in self.bar_claims
            if item.activation is _ActivationDisposition.ENABLED
        }
        for claim in self.metric_claims:
            if (
                claim.subject.configuration_epoch != self.configuration_epoch
                or claim.subject.configuration_digest != self.configuration_digest
            ):
                raise ValueError("metric subject configuration must match the manifest authority")
            if claim.activation is not _ActivationDisposition.DISABLED:
                missing_series = set(claim.input_series_ids) - enabled_series
                if missing_series:
                    message = (
                        "active metric claim references missing input series: "
                        f"{sorted(missing_series)!r}"
                    )
                    raise ValueError(message)
            if claim.activation is _ActivationDisposition.ENABLED:
                subject_digest = claim.subject.identity_digest
                if subject_digest in enabled_subjects:
                    raise ValueError(
                        "enabled metric producer claims overlap on one complete subject: "
                        f"{enabled_subjects[subject_digest]!r}, {claim.claim_id!r}",
                    )
                enabled_subjects[subject_digest] = claim.claim_id
                if any(
                    dependency.activation is not _ActivationDisposition.ENABLED
                    for dependency in self.metric_claims
                    if dependency.claim_id in claim.dependency_claim_ids
                ):
                    raise ValueError("canonical metric claims require enabled dependency outputs")
        by_id = {item.claim_id: item for item in self.metric_claims}
        for claim in self.metric_claims:
            missing = set(claim.dependency_claim_ids) - set(by_id)
            if missing:
                raise ValueError(f"metric dependencies are not declared: {sorted(missing)!r}")
        _reject_dependency_cycles(by_id)

    def _content_dict(self) -> dict[str, Any]:
        assignments = [
            {"actor_id": item.actor_id, "series_ids": list(item.series_ids)}
            for item in self.instance_assignments
        ]
        bars = [
            {
                "series_identity": item.series_identity.to_dict(),
                "series_identity_digest": item.series_identity.identity_digest,
                "producer_actor_id": item.producer_actor_id,
                "producer_version": item.producer_version,
                "output_schema_version": item.output_schema_version,
                "dependencies": list(item.dependencies),
                "activation": item.activation.value,
                "maximum_retained_completed_bars": item.maximum_retained_completed_bars,
                "maximum_history_live_overlap_bars": item.maximum_history_live_overlap_bars,
                "maximum_buffered_live_completed_bars": item.maximum_buffered_live_completed_bars,
            }
            for item in self.bar_claims
        ]
        metrics = [
            {
                "claim_id": item.claim_id,
                "subject": item.subject.to_dict(),
                "subject_digest": item.subject.identity_digest,
                "producer_actor_id": item.producer_actor_id,
                "producer_version": item.producer_version,
                "output_schema_version": item.output_schema_version,
                "input_series_ids": list(item.input_series_ids),
                "dependency_claim_ids": list(item.dependency_claim_ids),
                "parameter_set_id": item.parameter_set_id,
                "activation": item.activation.value,
            }
            for item in self.metric_claims
        ]
        return {
            "manifest_schema_version": self.manifest_schema_version,
            "configuration_epoch": str(self.configuration_epoch),
            "configuration_digest": self.configuration_digest,
            "instance_assignments": assignments,
            "bar_claims": bars,
            "metric_claims": metrics,
        }

    def to_dict(self) -> dict[str, Any]:
        result = self._content_dict()
        result["manifest_digest"] = self.manifest_digest
        return result

    def to_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())


class _SubscriptionReadinessStatus(StrEnum):
    SUBSCRIBED = "SUBSCRIBED"
    REJECTED = "REJECTED"


class _AcknowledgementDisposition(StrEnum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    REJECTED = "REJECTED"
    LATE_REJECTED = "LATE_REJECTED"


@dataclass(frozen=True, slots=True)
class _StartupConsumerRequirement:
    consumer_actor_id: str
    series_id: str
    producer_actor_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "consumer_actor_id",
            bounded_ascii(self.consumer_actor_id, "consumer_actor_id"),
        )
        object.__setattr__(self, "series_id", topic_token(self.series_id))
        object.__setattr__(
            self,
            "producer_actor_id",
            bounded_ascii(self.producer_actor_id, "producer_actor_id"),
        )

    @property
    def key(self) -> tuple[str, str]:
        return (self.consumer_actor_id, self.series_id)


@dataclass(frozen=True, slots=True)
class _SubscriptionReadinessAcknowledgement:
    startup_epoch: UUID
    consumer_actor_id: str
    series_id: str
    manifest_digest: str
    status: _SubscriptionReadinessStatus
    acknowledged_ts_ns: int
    reason: str | None = None

    def __post_init__(self) -> None:
        uuid_value(self.startup_epoch, "startup_epoch")
        object.__setattr__(
            self,
            "consumer_actor_id",
            bounded_ascii(self.consumer_actor_id, "consumer_actor_id"),
        )
        object.__setattr__(self, "series_id", topic_token(self.series_id))
        object.__setattr__(self, "manifest_digest", digest(self.manifest_digest, "manifest_digest"))
        if not isinstance(self.status, _SubscriptionReadinessStatus):
            raise ValueError("status must be a _SubscriptionReadinessStatus")
        positive_int64(self.acknowledged_ts_ns, "acknowledged_ts_ns")
        if self.status is _SubscriptionReadinessStatus.SUBSCRIBED:
            if self.reason is not None:
                raise ValueError("SUBSCRIBED acknowledgements cannot carry a rejection reason")
        else:
            object.__setattr__(self, "reason", bounded_ascii(self.reason, "reason"))

    @property
    def key(self) -> tuple[str, str]:
        return (self.consumer_actor_id, self.series_id)


@dataclass(frozen=True, slots=True)
class _StartupReadinessDecision:
    sealed: bool
    sealed_at_ns: int | None
    demand_series_ids: tuple[str, ...]
    subscribed_pairs: tuple[tuple[str, str], ...]
    quarantined_pairs: tuple[tuple[str, str], ...]
    missing_pairs: tuple[tuple[str, str], ...]


class _StartupReadinessValidator:
    """Pure bounded acknowledgement barrier with deterministic sealing."""

    def __init__(
        self,
        *,
        requirements: tuple[_StartupConsumerRequirement, ...],
        startup_epoch: UUID,
        manifest_digest: str,
        started_at_ns: int,
        timeout_ms: int = CONSUMER_READINESS_TIMEOUT_MS,
    ) -> None:
        if not isinstance(requirements, tuple) or not requirements:
            raise ValueError("requirements must be a non-empty tuple")
        if any(not isinstance(item, _StartupConsumerRequirement) for item in requirements):
            raise ValueError("requirements must contain typed values")
        keys = tuple(item.key for item in requirements)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError("requirements must be unique and deterministically sorted")
        uuid_value(startup_epoch, "startup_epoch")
        self._requirements = {item.key: item for item in requirements}
        producers_by_series: dict[str, str] = {}
        for requirement in requirements:
            existing_producer = producers_by_series.setdefault(
                requirement.series_id,
                requirement.producer_actor_id,
            )
            if existing_producer != requirement.producer_actor_id:
                raise ValueError("one readiness series cannot name conflicting producers")
        self._startup_epoch = startup_epoch
        self._manifest_digest = digest(manifest_digest, "manifest_digest")
        self._started_at_ns = positive_int64(started_at_ns, "started_at_ns")
        if timeout_ms != CONSUMER_READINESS_TIMEOUT_MS:
            raise ValueError("Slice 1 readiness timeout must be exactly 5000 ms")
        self._timeout_ns = timeout_ms * 1_000_000
        self._acks: dict[tuple[str, str], _SubscriptionReadinessAcknowledgement] = {}
        self._conflicts: set[tuple[str, str]] = set()
        self._latest_acknowledged_ts_ns = self._started_at_ns
        self._sealed_at_ns: int | None = None

    def acknowledge(
        self,
        acknowledgement: _SubscriptionReadinessAcknowledgement,
    ) -> _AcknowledgementDisposition:
        if not isinstance(acknowledgement, _SubscriptionReadinessAcknowledgement):
            raise ValueError("acknowledgement must be typed")
        if self._sealed_at_ns is not None:
            return _AcknowledgementDisposition.LATE_REJECTED
        deadline_ns = self._started_at_ns + self._timeout_ns
        if acknowledgement.acknowledged_ts_ns >= deadline_ns:
            self._sealed_at_ns = deadline_ns
            return _AcknowledgementDisposition.LATE_REJECTED
        if (
            acknowledgement.startup_epoch != self._startup_epoch
            or acknowledgement.manifest_digest != self._manifest_digest
            or acknowledgement.key not in self._requirements
            or acknowledgement.acknowledged_ts_ns < self._started_at_ns
        ):
            return _AcknowledgementDisposition.REJECTED
        existing = self._acks.get(acknowledgement.key)
        if existing == acknowledgement:
            return _AcknowledgementDisposition.DUPLICATE
        self._latest_acknowledged_ts_ns = max(
            self._latest_acknowledged_ts_ns,
            acknowledgement.acknowledged_ts_ns,
        )
        if existing is not None:
            self._conflicts.add(acknowledgement.key)
            self._seal_if_terminal()
            return _AcknowledgementDisposition.CONFLICT
        self._acks[acknowledgement.key] = acknowledgement
        self._seal_if_terminal()
        return _AcknowledgementDisposition.ACCEPTED

    def _seal_if_terminal(self) -> None:
        terminal_keys = set(self._acks) | self._conflicts
        if terminal_keys == set(self._requirements):
            self._sealed_at_ns = self._latest_acknowledged_ts_ns

    def evaluate(self, *, now_ns: int) -> _StartupReadinessDecision:
        positive_int64(now_ns, "now_ns")
        if now_ns < self._started_at_ns:
            raise ValueError("now_ns cannot precede startup")
        if self._sealed_at_ns is None:
            terminal_keys = set(self._acks) | self._conflicts
            if terminal_keys == set(self._requirements) or (
                now_ns - self._started_at_ns >= self._timeout_ns
            ):
                self._sealed_at_ns = min(
                    now_ns,
                    self._started_at_ns + self._timeout_ns,
                )
        subscribed = tuple(
            sorted(
                key
                for key, acknowledgement in self._acks.items()
                if acknowledgement.status is _SubscriptionReadinessStatus.SUBSCRIBED
                and key not in self._conflicts
            ),
        )
        rejected = {
            key
            for key, acknowledgement in self._acks.items()
            if acknowledgement.status is _SubscriptionReadinessStatus.REJECTED
        } | self._conflicts
        missing = set(self._requirements) - set(self._acks) - self._conflicts
        quarantined = tuple(
            sorted(rejected | (missing if self._sealed_at_ns is not None else set()))
        )
        demand_series = (
            tuple(sorted({series_id for _, series_id in subscribed}))
            if self._sealed_at_ns is not None
            else ()
        )
        return _StartupReadinessDecision(
            sealed=self._sealed_at_ns is not None,
            sealed_at_ns=self._sealed_at_ns,
            demand_series_ids=demand_series,
            subscribed_pairs=subscribed,
            quarantined_pairs=quarantined,
            missing_pairs=tuple(sorted(missing)),
        )


def _sorted_identifiers(values: object, label: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{label} must be a tuple")
    normalized = tuple(bounded_ascii(value, label) for value in values)
    if normalized != tuple(sorted(set(normalized))):
        raise ValueError(f"{label} must be unique and sorted")
    return normalized


def _reject_dependency_cycles(claims: dict[str, _MetricProducerClaim]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(claim_id: str) -> None:
        if claim_id in visiting:
            raise ValueError("metric producer dependencies must be acyclic")
        if claim_id in visited:
            return
        visiting.add(claim_id)
        for dependency_id in claims[claim_id].dependency_claim_ids:
            visit(dependency_id)
        visiting.remove(claim_id)
        visited.add(claim_id)

    for claim_id in sorted(claims):
        visit(claim_id)
