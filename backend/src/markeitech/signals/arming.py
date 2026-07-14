from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from markeitech.analytics import AnalyticsInputFidelity
from markeitech.signals.config import SignalDefinitionConfig
from markeitech.signals.contracts import (
    SignalEvidenceFidelity,
    SignalEvidenceReference,
    SignalEvidenceStage,
    SignalEvidenceType,
    SignalSnapshot,
    SignalStatus,
    SignalTransitionEvent,
    signal_setup_key,
)
from markeitech.signals.direction import (
    DirectionQualification,
    DirectionQualificationStatus,
)
from markeitech.signals.episode import (
    LocationEpisodeDecision,
    LocationEpisodeEventType,
    SignalLocationEpisode,
)
from markeitech.signals.lifecycle import transition_signal


@dataclass(frozen=True)
class ArmedLocationSignal:
    candidate: SignalSnapshot
    armed_transition: SignalTransitionEvent


def build_armed_location_signal(
    definition: SignalDefinitionConfig,
    episode: SignalLocationEpisode,
    direction: DirectionQualification,
) -> ArmedLocationSignal:
    if direction.status != DirectionQualificationStatus.QUALIFIED:
        raise ValueError("location signal requires qualified Direction")
    if direction.direction != episode.direction:
        raise ValueError("location episode must align with qualified Direction")
    direction_evidence = tuple(
        SignalEvidenceReference(
            instrument_id=episode.instrument_id,
            stage=SignalEvidenceStage.DIRECTION,
            evidence_type=SignalEvidenceType.MARKET_CONTEXT_FEATURE,
            evidence_id=feature.feature_id,
            observed_ts=feature.snapshot.as_of,
            source=feature.snapshot.source,
            fidelity=_signal_fidelity(feature.snapshot.input_fidelity),
            reason_codes=(
                f"{feature.snapshot.timeframe.value}_direction_score_"
                f"{feature.snapshot.direction_score}",
            ),
        )
        for feature in direction.evidence_features
    )
    candidate = SignalSnapshot(
        family=definition.family,
        definition_id=definition.definition_id,
        algorithm_version=definition.algorithm_version,
        configuration_hash=definition.configuration_hash,
        setup_key=signal_setup_key(
            family=definition.family,
            definition_id=definition.definition_id,
            instrument_id=episode.instrument_id,
            direction=episode.direction,
            anchor=f"location_episode:{episode.episode_id}",
        ),
        instrument_id=episode.instrument_id,
        direction=episode.direction,
        created_ts=episode.entry_ts,
        updated_ts=episode.entry_ts,
        direction_regime_anchor=episode.direction_regime_anchor,
        location_episode_id=episode.episode_id,
        evidence=direction_evidence,
        reason_codes=(*direction.reason_codes, "location_episode_entered"),
    )
    location_evidence = _location_evidence(episode)
    armed = transition_signal(
        candidate,
        SignalStatus.ARMED,
        occurred_ts=episode.entry_ts,
        reason_codes=("location_episode_armed",),
        evidence=location_evidence,
        location_matches=episode.entry_matches,
    )
    return ArmedLocationSignal(candidate, armed)


def restore_location_episode(signal: SignalSnapshot) -> SignalLocationEpisode:
    if signal.status not in {SignalStatus.ARMED, SignalStatus.TRIGGERED}:
        raise ValueError("only open Armed or Triggered signals restore location episodes")
    if signal.location_episode_id is None or signal.direction_regime_anchor is None:
        raise ValueError("open location signal is missing episode identity")
    episode = SignalLocationEpisode(
        definition_id=signal.definition_id,
        instrument_id=signal.instrument_id,
        direction=signal.direction,
        direction_regime_anchor=signal.direction_regime_anchor,
        entry_ts=signal.created_ts,
        entry_matches=signal.location_matches,
    )
    if episode.episode_id != signal.location_episode_id:
        raise ValueError("stored signal location episode identity is inconsistent")
    return episode


def invalidate_ended_location_signal(
    signal: SignalSnapshot,
    decision: LocationEpisodeDecision,
    *,
    occurred_ts: datetime,
    reason_codes: Sequence[str] = (),
) -> SignalTransitionEvent:
    if signal.status != SignalStatus.ARMED:
        raise ValueError("only Armed location signals can be invalidated by episode exit")
    if decision.event_type not in {
        LocationEpisodeEventType.EXITED,
        LocationEpisodeEventType.REPLACED,
    }:
        raise ValueError("location signal invalidation requires ended episode decision")
    if decision.ended_episode_id != signal.location_episode_id:
        raise ValueError("ended location episode does not match signal")
    reasons = tuple(reason_codes) or (f"location_episode_{decision.event_type.value}",)
    return transition_signal(
        signal,
        SignalStatus.INVALIDATED,
        occurred_ts=occurred_ts,
        reason_codes=reasons,
    )


def _location_evidence(
    episode: SignalLocationEpisode,
) -> tuple[SignalEvidenceReference, ...]:
    grouped: dict[str, list[tuple[SignalEvidenceFidelity, datetime, str]]] = {}
    for match in episode.entry_matches:
        grouped.setdefault(match.zone.source_feature_id, []).append(
            (
                match.zone.fidelity,
                match.zone.observed_ts,
                f"{match.zone.timeframe.value}_{match.zone.zone_kind.value}_zone",
            )
        )
        grouped.setdefault(match.evaluation_feature_id, []).append(
            (
                match.fidelity,
                match.observed_ts,
                f"{match.zone.timeframe.value}_{match.zone.zone_kind.value}_match",
            )
        )
    return tuple(
        SignalEvidenceReference(
            instrument_id=episode.instrument_id,
            stage=SignalEvidenceStage.LOCATION,
            evidence_type=SignalEvidenceType.MARKET_CONTEXT_FEATURE,
            evidence_id=feature_id,
            observed_ts=max(item[1] for item in values),
            source="market_context",
            fidelity=max(values, key=lambda item: _fidelity_rank(item[0]))[0],
            reason_codes=tuple(sorted({item[2] for item in values})),
        )
        for feature_id, values in sorted(grouped.items())
    )


def _signal_fidelity(value: AnalyticsInputFidelity) -> SignalEvidenceFidelity:
    return {
        AnalyticsInputFidelity.REPORTED: SignalEvidenceFidelity.REPORTED,
        AnalyticsInputFidelity.INFERRED: SignalEvidenceFidelity.INFERRED,
        AnalyticsInputFidelity.MIXED: SignalEvidenceFidelity.PARTIAL,
    }[value]


def _fidelity_rank(value: SignalEvidenceFidelity) -> int:
    return {
        SignalEvidenceFidelity.REPORTED: 0,
        SignalEvidenceFidelity.INFERRED: 1,
        SignalEvidenceFidelity.PARTIAL: 2,
        SignalEvidenceFidelity.UNAVAILABLE: 3,
    }[value]
