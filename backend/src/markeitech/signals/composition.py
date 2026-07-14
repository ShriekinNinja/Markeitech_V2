from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock

from markeitech.analytics import AnalyticsTimeframe
from markeitech.persistence.feature_pipeline import CommittedFeatureRevision
from markeitech.signals.config import SignalDefinitionConfig
from markeitech.signals.direction import CommittedMarketContextBundle


class FeatureHandoffStatus(StrEnum):
    ACCEPTED = "accepted"
    QUEUE_FULL = "queue_full"
    CLOSED = "closed"


@dataclass(frozen=True)
class FeatureHandoffSnapshot:
    pending_count: int
    accepted_count: int
    drained_count: int
    rejected_count: int
    is_closed: bool


class BoundedFeatureCommitHandoff:
    """All-or-nothing queue between durable feature commit and signal composition."""

    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("feature commit handoff capacity must be positive")
        self._capacity = capacity
        self._lock = Lock()
        self._queue: deque[CommittedFeatureRevision] = deque()
        self._accepted_count = 0
        self._drained_count = 0
        self._rejected_count = 0
        self._closed = False

    @property
    def snapshot(self) -> FeatureHandoffSnapshot:
        with self._lock:
            return FeatureHandoffSnapshot(
                pending_count=len(self._queue),
                accepted_count=self._accepted_count,
                drained_count=self._drained_count,
                rejected_count=self._rejected_count,
                is_closed=self._closed,
            )

    def publish(
        self,
        revisions: tuple[CommittedFeatureRevision, ...],
    ) -> FeatureHandoffStatus:
        with self._lock:
            if self._closed:
                self._rejected_count += len(revisions)
                return FeatureHandoffStatus.CLOSED
            if len(self._queue) + len(revisions) > self._capacity:
                self._rejected_count += len(revisions)
                return FeatureHandoffStatus.QUEUE_FULL
            self._queue.extend(revisions)
            self._accepted_count += len(revisions)
            return FeatureHandoffStatus.ACCEPTED

    def offer(self, revisions: tuple[CommittedFeatureRevision, ...]) -> bool:
        return self.publish(revisions) == FeatureHandoffStatus.ACCEPTED

    def drain(self, limit: int) -> tuple[CommittedFeatureRevision, ...]:
        if limit < 1:
            raise ValueError("feature commit handoff drain limit must be positive")
        with self._lock:
            values = tuple(self._queue.popleft() for _ in range(min(limit, len(self._queue))))
            self._drained_count += len(values)
            return values

    def close(self) -> None:
        with self._lock:
            self._closed = True


class CommittedFeatureState:
    """Latest durable revision per instrument and timeframe for live composition."""

    def __init__(self) -> None:
        self._latest: dict[
            tuple[str, AnalyticsTimeframe], CommittedFeatureRevision
        ] = {}

    def apply(self, revision: CommittedFeatureRevision) -> bool:
        feature = revision.feature
        key = (feature.snapshot.instrument_id, feature.snapshot.timeframe)
        current = self._latest.get(key)
        for latest in self._latest.values():
            if (
                latest.commit_sequence == revision.commit_sequence
                and latest.feature.feature_id != feature.feature_id
            ):
                raise ValueError("durable commit sequence identifies multiple live features")
        if current is not None and current.feature.feature_id == feature.feature_id:
            if current != revision:
                raise ValueError("feature revision conflicts with prior durable evidence")
            return False
        candidate_order = (feature.snapshot.as_of, revision.commit_sequence)
        if current is not None:
            current_order = (current.feature.snapshot.as_of, current.commit_sequence)
            if candidate_order <= current_order:
                return False
        self._latest[key] = revision
        return True

    def compose(
        self,
        revision: CommittedFeatureRevision,
        definition: SignalDefinitionConfig,
    ) -> CommittedMarketContextBundle | None:
        feature = revision.feature
        if feature.snapshot.timeframe != definition.evaluation_timeframe:
            return None
        key = (feature.snapshot.instrument_id, feature.snapshot.timeframe)
        current_evaluation = self._latest.get(key)
        if current_evaluation is None:
            raise ValueError("feature revision must be applied before composition")
        if current_evaluation.feature.feature_id != feature.feature_id:
            return None
        if current_evaluation != revision:
            raise ValueError("feature revision conflicts with applied durable evidence")

        values = []
        for timeframe in definition.analytical_timeframes:
            current = self._latest.get((feature.snapshot.instrument_id, timeframe))
            if current is not None and current.feature.snapshot.as_of <= feature.snapshot.as_of:
                values.append(current.feature)
        values.sort(key=lambda item: item.snapshot.timeframe.value)
        return CommittedMarketContextBundle(
            instrument_id=feature.snapshot.instrument_id,
            evaluation_as_of=feature.snapshot.as_of,
            features=tuple(values),
        )
