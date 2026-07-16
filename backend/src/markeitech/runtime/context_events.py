from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from threading import Lock
from typing import Protocol

from markeitech.context_events import (
    ContextDetectionResult,
    ContextDetectorCheckpoint,
    ContextTransitionEvent,
    MarketContextTransitionDetector,
)
from markeitech.persistence import ContextEventCommitResult
from markeitech.persistence.feature_pipeline import CommittedFeatureRevision
from markeitech.runtime.event_bus import BoundedEventLoopBridge, DomainEventOfferStatus
from markeitech.runtime.events import (
    CommittedContextTransitionNotice,
    MarkeitechBusTopic,
)


class ContextEventProcessorStatus(StrEnum):
    CREATED = "created"
    READY = "ready"
    FAILED = "failed"


class ContextEventMetadata(Protocol):
    def load_context_checkpoints(self) -> tuple[ContextDetectorCheckpoint, ...]: ...

    def commit_context_detection(
        self,
        result: ContextDetectionResult,
    ) -> ContextEventCommitResult: ...


@dataclass(frozen=True)
class ContextEventProcessorSnapshot:
    status: ContextEventProcessorStatus
    reconciled_revision_count: int
    processed_revision_count: int
    checkpoint_advance_count: int
    committed_event_count: int
    duplicate_event_count: int
    projection_rejected_count: int
    last_error: str | None


class ContextEventCommitProcessor:
    """Advances durable context state on the ordered feature-writer thread."""

    def __init__(
        self,
        metadata: ContextEventMetadata,
        bridge: BoundedEventLoopBridge | None,
    ) -> None:
        self._metadata = metadata
        self._bridge = bridge
        self._detector = MarketContextTransitionDetector()
        self._status = ContextEventProcessorStatus.CREATED
        self._reconciled_revision_count = 0
        self._processed_revision_count = 0
        self._checkpoint_advance_count = 0
        self._committed_event_count = 0
        self._duplicate_event_count = 0
        self._projection_rejected_count = 0
        self._last_error: str | None = None
        self._lock = Lock()

    @property
    def snapshot(self) -> ContextEventProcessorSnapshot:
        with self._lock:
            return ContextEventProcessorSnapshot(
                status=self._status,
                reconciled_revision_count=self._reconciled_revision_count,
                processed_revision_count=self._processed_revision_count,
                checkpoint_advance_count=self._checkpoint_advance_count,
                committed_event_count=self._committed_event_count,
                duplicate_event_count=self._duplicate_event_count,
                projection_rejected_count=self._projection_rejected_count,
                last_error=self._last_error,
            )

    def reconcile(self, revisions: tuple[CommittedFeatureRevision, ...]) -> None:
        if self._status != ContextEventProcessorStatus.CREATED:
            raise RuntimeError("context event processor can only reconcile once")
        checkpoints = self._metadata.load_context_checkpoints()
        self._detector.seed(checkpoints)
        checkpoint_by_stream = {
            (item.instrument_id, item.timeframe.value): item for item in checkpoints
        }
        by_stream: dict[tuple[str, str], list[CommittedFeatureRevision]] = {}
        for revision in revisions:
            snapshot = revision.feature.snapshot
            key = (snapshot.instrument_id, snapshot.timeframe.value)
            by_stream.setdefault(key, []).append(revision)
        pending: list[CommittedFeatureRevision] = []
        for key, values in by_stream.items():
            ordered = sorted(values, key=lambda item: item.commit_sequence)
            checkpoint = checkpoint_by_stream.get(key)
            if checkpoint is None:
                pending.append(ordered[-1])
            else:
                pending.extend(
                    item for item in ordered if item.commit_sequence > checkpoint.commit_sequence
                )
        try:
            for revision in sorted(pending, key=lambda item: item.commit_sequence):
                self._process(revision, publish=False)
                with self._lock:
                    self._reconciled_revision_count += 1
        except Exception as exc:
            self._fail(exc)
            raise
        with self._lock:
            self._status = ContextEventProcessorStatus.READY

    def offer(self, revisions: tuple[CommittedFeatureRevision, ...]) -> bool:
        if self._status != ContextEventProcessorStatus.READY:
            return False
        try:
            for revision in sorted(revisions, key=lambda item: item.commit_sequence):
                self._process(revision, publish=True)
        except Exception as exc:
            self._fail(exc)
            raise
        return True

    def _process(self, revision: CommittedFeatureRevision, *, publish: bool) -> None:
        detection = self._detector.apply(revision)
        result = self._metadata.commit_context_detection(detection)
        committed_ids = set(result.committed_event_ids)
        committed_events = tuple(
            event for event in detection.events if event.event_id in committed_ids
        )
        projection_rejections = 0
        if publish and committed_events and self._bridge is not None:
            notices = tuple(context_transition_notice(event) for event in committed_events)
            if self._bridge.offer_batch(notices) != DomainEventOfferStatus.ACCEPTED:
                projection_rejections = len(notices)
        with self._lock:
            self._processed_revision_count += 1
            self._checkpoint_advance_count += int(result.checkpoint_advanced)
            self._committed_event_count += result.committed_event_count
            self._duplicate_event_count += result.duplicate_event_count
            self._projection_rejected_count += projection_rejections

    def _fail(self, exc: Exception) -> None:
        with self._lock:
            self._status = ContextEventProcessorStatus.FAILED
            self._last_error = f"{type(exc).__name__}: {exc}"


def context_transition_notice(
    event: ContextTransitionEvent,
) -> CommittedContextTransitionNotice:
    return CommittedContextTransitionNotice(
        topic=MarkeitechBusTopic.CONTEXT_EVENT,
        event_id=event.event_id,
        occurred_ts=event.occurred_ts,
        aggregate_id=f"{event.instrument_id}:market_context:{event.timeframe.value}",
        payload_type=type(event).__name__,
        payload_id=event.event_id,
        instrument_id=event.instrument_id,
        commit_sequence=event.current_commit_sequence,
        transition_kind=event.kind.value,
        timeframe=event.timeframe.value,
        previous_value=event.previous_value,
        current_value=event.current_value,
        previous_input_fidelity=event.previous_input_fidelity.value,
        current_input_fidelity=event.current_input_fidelity.value,
    )
