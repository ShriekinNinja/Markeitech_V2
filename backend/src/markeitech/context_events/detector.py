from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from markeitech.analytics import ProfileLocation, TrendState
from markeitech.context_events.contracts import (
    ContextDetectorCheckpoint,
    ContextEventKind,
    ContextTransitionEvent,
    ValueAreaRegion,
)
from markeitech.persistence.feature_pipeline import CommittedFeatureRevision


class ContextDetectionStatus(StrEnum):
    SEEDED = "seeded"
    APPLIED = "applied"
    CORRECTION = "correction"
    DUPLICATE = "duplicate"
    STALE = "stale"


@dataclass(frozen=True)
class ContextDetectionResult:
    status: ContextDetectionStatus
    events: tuple[ContextTransitionEvent, ...]
    reason_codes: tuple[str, ...]
    checkpoint: ContextDetectorCheckpoint | None


class MarketContextTransitionDetector:
    """Compares ordered durable feature revisions without inventing gap transitions."""

    def __init__(self) -> None:
        self._latest: dict[tuple[str, str], ContextDetectorCheckpoint] = {}

    def seed(self, checkpoints: tuple[ContextDetectorCheckpoint, ...]) -> None:
        for checkpoint in checkpoints:
            key = (checkpoint.instrument_id, checkpoint.timeframe.value)
            if key in self._latest:
                raise ValueError("multiple context checkpoints exist for one stream")
            self._latest[key] = checkpoint

    def apply(self, revision: CommittedFeatureRevision) -> ContextDetectionResult:
        current = _checkpoint(revision)
        key = (current.instrument_id, current.timeframe.value)
        previous = self._latest.get(key)
        if previous is None:
            self._latest[key] = current
            return ContextDetectionResult(
                ContextDetectionStatus.SEEDED,
                (),
                ("initial_feature_seeded",),
                current,
            )
        if previous == current:
            return ContextDetectionResult(
                ContextDetectionStatus.DUPLICATE,
                (),
                ("committed_revision_duplicate",),
                None,
            )
        if previous.commit_sequence == current.commit_sequence:
            raise ValueError("commit sequence identifies conflicting feature revisions")
        if previous.feature_id == current.feature_id:
            raise ValueError("feature identity has conflicting durable revision metadata")
        if current.commit_sequence < previous.commit_sequence:
            return ContextDetectionResult(
                ContextDetectionStatus.STALE,
                (),
                ("feature_commit_sequence_precedes_current_state",),
                None,
            )
        previous_order = (previous.as_of, previous.commit_sequence)
        current_order = (current.as_of, current.commit_sequence)
        if current_order < previous_order:
            return ContextDetectionResult(
                ContextDetectionStatus.STALE,
                (),
                ("feature_revision_precedes_current_state",),
                None,
            )
        self._latest[key] = current
        if current.as_of == previous.as_of:
            return ContextDetectionResult(
                ContextDetectionStatus.CORRECTION,
                (),
                ("same_timestamp_feature_correction",),
                current,
            )

        events = _detect_transitions(previous, current)
        return ContextDetectionResult(
            ContextDetectionStatus.APPLIED,
            events,
            ("context_transitions_detected",) if events else ("no_context_transition",),
            current,
        )


def _detect_transitions(
    previous: ContextDetectorCheckpoint,
    current: ContextDetectorCheckpoint,
) -> tuple[ContextTransitionEvent, ...]:
    events: list[ContextTransitionEvent] = []
    if (
        previous.trend != TrendState.INSUFFICIENT_DATA
        and current.trend != TrendState.INSUFFICIENT_DATA
        and previous.trend != current.trend
    ):
        events.append(
            _event(
                ContextEventKind.TREND_CHANGED,
                previous,
                current,
                previous.trend.value,
                current.trend.value,
                "trend_state_changed",
            )
        )
    previous_region = previous.value_area_region
    current_region = current.value_area_region
    if (
        previous_region != ValueAreaRegion.UNAVAILABLE
        and current_region != ValueAreaRegion.UNAVAILABLE
        and previous_region != current_region
    ):
        events.append(
            _event(
                ContextEventKind.VALUE_AREA_REGION_CHANGED,
                previous,
                current,
                previous_region.value,
                current_region.value,
                "value_area_region_changed",
            )
        )
    return tuple(events)


def _event(
    kind: ContextEventKind,
    previous: ContextDetectorCheckpoint,
    current: ContextDetectorCheckpoint,
    previous_value: str,
    current_value: str,
    reason_code: str,
) -> ContextTransitionEvent:
    return ContextTransitionEvent(
        kind=kind,
        instrument_id=current.instrument_id,
        timeframe=current.timeframe,
        occurred_ts=current.as_of,
        detected_ts=current.committed_ts,
        previous_value=previous_value,
        current_value=current_value,
        previous_feature_id=previous.feature_id,
        current_feature_id=current.feature_id,
        previous_commit_sequence=previous.commit_sequence,
        current_commit_sequence=current.commit_sequence,
        previous_input_fidelity=previous.input_fidelity,
        current_input_fidelity=current.input_fidelity,
        reason_codes=(reason_code,),
    )


def _checkpoint(revision: CommittedFeatureRevision) -> ContextDetectorCheckpoint:
    snapshot = revision.feature.snapshot
    return ContextDetectorCheckpoint(
        instrument_id=snapshot.instrument_id,
        timeframe=snapshot.timeframe,
        as_of=snapshot.as_of,
        committed_ts=revision.committed_ts,
        feature_id=revision.feature.feature_id,
        commit_sequence=revision.commit_sequence,
        trend=snapshot.trend,
        value_area_region=_value_area_region(snapshot.profile_location),
        input_fidelity=snapshot.input_fidelity,
    )


def _value_area_region(location: ProfileLocation) -> ValueAreaRegion:
    if location == ProfileLocation.BELOW_VALUE:
        return ValueAreaRegion.BELOW
    if location == ProfileLocation.ABOVE_VALUE:
        return ValueAreaRegion.ABOVE
    if location in {
        ProfileLocation.LOWER_VALUE,
        ProfileLocation.AT_POC,
        ProfileLocation.UPPER_VALUE,
    }:
        return ValueAreaRegion.INSIDE
    return ValueAreaRegion.UNAVAILABLE
