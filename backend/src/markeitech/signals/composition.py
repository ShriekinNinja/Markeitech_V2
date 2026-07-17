from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from threading import Condition

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
    capacity: int
    pending_count: int
    high_watermark: int
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
        self._condition = Condition()
        self._queue: deque[CommittedFeatureRevision] = deque()
        self._high_watermark = 0
        self._accepted_count = 0
        self._drained_count = 0
        self._rejected_count = 0
        self._closed = False

    @property
    def snapshot(self) -> FeatureHandoffSnapshot:
        with self._condition:
            return FeatureHandoffSnapshot(
                capacity=self._capacity,
                pending_count=len(self._queue),
                high_watermark=self._high_watermark,
                accepted_count=self._accepted_count,
                drained_count=self._drained_count,
                rejected_count=self._rejected_count,
                is_closed=self._closed,
            )

    def publish(
        self,
        revisions: tuple[CommittedFeatureRevision, ...],
    ) -> FeatureHandoffStatus:
        with self._condition:
            if self._closed:
                self._rejected_count += len(revisions)
                return FeatureHandoffStatus.CLOSED
            if len(self._queue) + len(revisions) > self._capacity:
                self._rejected_count += len(revisions)
                return FeatureHandoffStatus.QUEUE_FULL
            self._queue.extend(revisions)
            self._high_watermark = max(self._high_watermark, len(self._queue))
            self._accepted_count += len(revisions)
            self._condition.notify_all()
            return FeatureHandoffStatus.ACCEPTED

    def offer(self, revisions: tuple[CommittedFeatureRevision, ...]) -> bool:
        return self.publish(revisions) == FeatureHandoffStatus.ACCEPTED

    def drain(self, limit: int) -> tuple[CommittedFeatureRevision, ...]:
        if limit < 1:
            raise ValueError("feature commit handoff drain limit must be positive")
        with self._condition:
            return self._drain_unlocked(limit)

    def wait_and_drain(
        self,
        limit: int,
        timeout: float,
    ) -> tuple[CommittedFeatureRevision, ...]:
        if limit < 1:
            raise ValueError("feature commit handoff drain limit must be positive")
        if timeout <= 0:
            raise ValueError("feature commit handoff wait timeout must be positive")
        with self._condition:
            if not self._queue and not self._closed:
                self._condition.wait(timeout)
            return self._drain_unlocked(limit)

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()

    def requeue_front(self, revisions: tuple[CommittedFeatureRevision, ...]) -> None:
        with self._condition:
            if len(revisions) > self._drained_count:
                raise RuntimeError("feature commit handoff cannot requeue undrained revisions")
            if len(self._queue) + len(revisions) > self._capacity:
                raise RuntimeError("feature commit handoff cannot restore drained batch")
            self._queue.extendleft(reversed(revisions))
            self._high_watermark = max(self._high_watermark, len(self._queue))
            self._drained_count -= len(revisions)
            self._condition.notify_all()

    def _drain_unlocked(self, limit: int) -> tuple[CommittedFeatureRevision, ...]:
        values = tuple(self._queue.popleft() for _ in range(min(limit, len(self._queue))))
        self._drained_count += len(values)
        return values


class CommittedFeatureState:
    """Latest durable revision per instrument and timeframe for live composition."""

    def __init__(self) -> None:
        self._latest: dict[tuple[str, AnalyticsTimeframe], CommittedFeatureRevision] = {}

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

    def latest_bundle(
        self,
        instrument_id: str,
        definition: SignalDefinitionConfig,
    ) -> CommittedMarketContextBundle | None:
        revision = self._latest.get((instrument_id, definition.evaluation_timeframe))
        if revision is None:
            return None
        return self.compose(revision, definition)
