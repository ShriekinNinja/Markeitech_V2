from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock

from markeitech.persistence.feature_pipeline import CommittedFeatureRevision
from markeitech.runtime.event_bus import (
    BoundedEventLoopBridge,
    DomainEventOfferStatus,
)
from markeitech.runtime.events import CommittedDomainEvent, MarkeitechBusTopic

type CriticalFeatureCommitSink = Callable[[tuple[CommittedFeatureRevision, ...]], bool]


@dataclass(frozen=True)
class FeatureCommitEventSnapshot:
    offered_count: int
    rejected_count: int
    last_rejection: str | None


class FeatureCommitEventFanout:
    """Keeps critical signal handoff separate from recoverable bus notification."""

    def __init__(
        self,
        bridge: BoundedEventLoopBridge,
        *,
        critical_sink: CriticalFeatureCommitSink | None = None,
    ) -> None:
        self._bridge = bridge
        self._critical_sink = critical_sink
        self._offered_count = 0
        self._rejected_count = 0
        self._last_rejection: str | None = None
        self._lock = Lock()

    @property
    def snapshot(self) -> FeatureCommitEventSnapshot:
        with self._lock:
            return FeatureCommitEventSnapshot(
                offered_count=self._offered_count,
                rejected_count=self._rejected_count,
                last_rejection=self._last_rejection,
            )

    def offer(self, revisions: tuple[CommittedFeatureRevision, ...]) -> bool:
        if self._critical_sink is not None and not self._critical_sink(revisions):
            return False
        events = tuple(feature_committed_event(revision) for revision in revisions)
        result = self._bridge.offer_batch(events)
        with self._lock:
            self._offered_count += len(events)
            if result != DomainEventOfferStatus.ACCEPTED:
                self._rejected_count += len(events)
                self._last_rejection = result.value
        return True


def feature_committed_event(revision: CommittedFeatureRevision) -> CommittedDomainEvent:
    feature = revision.feature
    snapshot = feature.snapshot
    return CommittedDomainEvent(
        topic=MarkeitechBusTopic.FEATURE_COMMITTED,
        event_id=f"feature-committed:{revision.commit_sequence}:{feature.feature_id}",
        occurred_ts=revision.committed_ts,
        aggregate_id=(
            f"{snapshot.instrument_id}:{feature.feature_set}:{snapshot.timeframe.value}"
        ),
        payload_type=type(feature).__name__,
        payload_id=feature.feature_id,
        instrument_id=snapshot.instrument_id,
        commit_sequence=revision.commit_sequence,
    )
