from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from markeitech.analytics import ProfileLocation, TrendState
from markeitech.context_events.contracts import (
    ContextEventKind,
    ContextTransitionEvent,
    ValueAreaRegion,
)
from markeitech.persistence import CommittedFeatureRevision


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


class MarketContextTransitionDetector:
    """Compares ordered durable feature revisions without inventing gap transitions."""

    def __init__(self) -> None:
        self._latest: dict[tuple[str, str], CommittedFeatureRevision] = {}

    def apply(self, revision: CommittedFeatureRevision) -> ContextDetectionResult:
        snapshot = revision.feature.snapshot
        key = (snapshot.instrument_id, snapshot.timeframe.value)
        previous = self._latest.get(key)
        if previous is None:
            self._latest[key] = revision
            return ContextDetectionResult(
                ContextDetectionStatus.SEEDED,
                (),
                ("initial_feature_seeded",),
            )
        if previous == revision:
            return ContextDetectionResult(
                ContextDetectionStatus.DUPLICATE,
                (),
                ("committed_revision_duplicate",),
            )
        if previous.commit_sequence == revision.commit_sequence:
            raise ValueError("commit sequence identifies conflicting feature revisions")
        if previous.feature.feature_id == revision.feature.feature_id:
            raise ValueError("feature identity has conflicting durable revision metadata")
        if revision.commit_sequence < previous.commit_sequence:
            return ContextDetectionResult(
                ContextDetectionStatus.STALE,
                (),
                ("feature_commit_sequence_precedes_current_state",),
            )
        previous_order = (previous.feature.snapshot.as_of, previous.commit_sequence)
        current_order = (snapshot.as_of, revision.commit_sequence)
        if current_order < previous_order:
            return ContextDetectionResult(
                ContextDetectionStatus.STALE,
                (),
                ("feature_revision_precedes_current_state",),
            )
        self._latest[key] = revision
        if snapshot.as_of == previous.feature.snapshot.as_of:
            return ContextDetectionResult(
                ContextDetectionStatus.CORRECTION,
                (),
                ("same_timestamp_feature_correction",),
            )

        events = _detect_transitions(previous, revision)
        return ContextDetectionResult(
            ContextDetectionStatus.APPLIED,
            events,
            ("context_transitions_detected",) if events else ("no_context_transition",),
        )


def _detect_transitions(
    previous: CommittedFeatureRevision,
    current: CommittedFeatureRevision,
) -> tuple[ContextTransitionEvent, ...]:
    events: list[ContextTransitionEvent] = []
    previous_snapshot = previous.feature.snapshot
    current_snapshot = current.feature.snapshot
    if (
        previous_snapshot.trend != TrendState.INSUFFICIENT_DATA
        and current_snapshot.trend != TrendState.INSUFFICIENT_DATA
        and previous_snapshot.trend != current_snapshot.trend
    ):
        events.append(
            _event(
                ContextEventKind.TREND_CHANGED,
                previous,
                current,
                previous_snapshot.trend.value,
                current_snapshot.trend.value,
                "trend_state_changed",
            )
        )
    previous_region = _value_area_region(previous_snapshot.profile_location)
    current_region = _value_area_region(current_snapshot.profile_location)
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
    previous: CommittedFeatureRevision,
    current: CommittedFeatureRevision,
    previous_value: str,
    current_value: str,
    reason_code: str,
) -> ContextTransitionEvent:
    snapshot = current.feature.snapshot
    return ContextTransitionEvent(
        kind=kind,
        instrument_id=snapshot.instrument_id,
        timeframe=snapshot.timeframe,
        occurred_ts=snapshot.as_of,
        detected_ts=current.committed_ts,
        previous_value=previous_value,
        current_value=current_value,
        previous_feature_id=previous.feature.feature_id,
        current_feature_id=current.feature.feature_id,
        previous_commit_sequence=previous.commit_sequence,
        current_commit_sequence=current.commit_sequence,
        previous_input_fidelity=previous.feature.snapshot.input_fidelity,
        current_input_fidelity=snapshot.input_fidelity,
        reason_codes=(reason_code,),
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
