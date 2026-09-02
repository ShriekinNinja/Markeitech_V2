from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from markeitech.intelligence._contract_validation import positive_int
from markeitech.intelligence.metric_messages import MetricSubjectIdentity, MetricValue

MAXIMUM_ADMITTED_METRIC_SUBJECTS = 256


class _MetricValueAdmissionDisposition(StrEnum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    REJECTED_CONFLICT = "REJECTED_CONFLICT"
    REJECTED_STALE = "REJECTED_STALE"
    REJECTED_GAP = "REJECTED_GAP"
    REJECTED_CAPACITY = "REJECTED_CAPACITY"


@dataclass(frozen=True, slots=True)
class _MetricValueAdmissionResult:
    disposition: _MetricValueAdmissionDisposition
    current_value: MetricValue | None


@dataclass(frozen=True, slots=True)
class _MetricValueAdmissionCounters:
    accepted: int
    duplicates: int
    conflicts: int
    stale: int
    gaps: int
    capacity_rejections: int


class _MetricValueAdmissionBook:
    """Pure bounded admission for complete metric subject/run revision chains."""

    def __init__(self, *, maximum_subjects: int = MAXIMUM_ADMITTED_METRIC_SUBJECTS) -> None:
        positive_int(maximum_subjects, "maximum_subjects")
        if maximum_subjects > MAXIMUM_ADMITTED_METRIC_SUBJECTS:
            raise ValueError("maximum_subjects cannot exceed the 256-subject Slice 1 ceiling")
        self._maximum_subjects = maximum_subjects
        self._current: dict[tuple[MetricSubjectIdentity, UUID], MetricValue] = {}
        self._accepted = 0
        self._duplicates = 0
        self._conflicts = 0
        self._stale = 0
        self._gaps = 0
        self._capacity_rejections = 0

    @property
    def counters(self) -> _MetricValueAdmissionCounters:
        return _MetricValueAdmissionCounters(
            accepted=self._accepted,
            duplicates=self._duplicates,
            conflicts=self._conflicts,
            stale=self._stale,
            gaps=self._gaps,
            capacity_rejections=self._capacity_rejections,
        )

    @property
    def subject_count(self) -> int:
        return len(self._current)

    def current(self, subject: MetricSubjectIdentity, run_epoch: UUID) -> MetricValue | None:
        if not isinstance(subject, MetricSubjectIdentity) or not isinstance(run_epoch, UUID):
            raise ValueError("current lookup requires complete subject identity and UUID run epoch")
        return self._current.get((subject, run_epoch))

    def admit(self, value: MetricValue) -> _MetricValueAdmissionResult:
        if not isinstance(value, MetricValue):
            raise ValueError("value must be a MetricValue")
        key = (value.subject, value.run_epoch)
        current = self._current.get(key)
        if current is None:
            if value.revision != 1 or value.previous_revision is not None:
                self._gaps += 1
                return _MetricValueAdmissionResult(
                    _MetricValueAdmissionDisposition.REJECTED_GAP,
                    None,
                )
            if len(self._current) >= self._maximum_subjects:
                self._capacity_rejections += 1
                return _MetricValueAdmissionResult(
                    _MetricValueAdmissionDisposition.REJECTED_CAPACITY,
                    None,
                )
            self._current[key] = value
            self._accepted += 1
            return _MetricValueAdmissionResult(
                _MetricValueAdmissionDisposition.ACCEPTED,
                value,
            )

        if value.revision == current.revision:
            if value == current:
                self._duplicates += 1
                return _MetricValueAdmissionResult(
                    _MetricValueAdmissionDisposition.DUPLICATE,
                    current,
                )
            self._conflicts += 1
            return _MetricValueAdmissionResult(
                _MetricValueAdmissionDisposition.REJECTED_CONFLICT,
                current,
            )
        if value.revision < current.revision:
            self._stale += 1
            return _MetricValueAdmissionResult(
                _MetricValueAdmissionDisposition.REJECTED_STALE,
                current,
            )
        if value.revision != current.revision + 1 or value.previous_revision != current.revision:
            self._gaps += 1
            return _MetricValueAdmissionResult(
                _MetricValueAdmissionDisposition.REJECTED_GAP,
                current,
            )
        self._current[key] = value
        self._accepted += 1
        return _MetricValueAdmissionResult(
            _MetricValueAdmissionDisposition.ACCEPTED,
            value,
        )
