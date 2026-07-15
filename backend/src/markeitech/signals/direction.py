from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from markeitech.analytics import (
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    MarketContextFeatureSnapshot,
)
from markeitech.domain.base import VersionedDomainModel, require_utc
from markeitech.signals.config import OpposingContextPolicy, SignalDefinitionConfig
from markeitech.signals.contracts import (
    SignalDirection,
    SignalEvidenceFidelity,
    SignalEvidenceReference,
    SignalEvidenceStage,
    SignalEvidenceType,
    SignalSnapshot,
    SignalStatus,
    signal_setup_key,
)


class DirectionQualificationStatus(StrEnum):
    QUALIFIED = "qualified"
    MISSING_EVIDENCE = "missing_evidence"
    NEUTRAL = "neutral"
    CONFLICTED = "conflicted"
    VETOED = "vetoed"


class CommittedMarketContextBundle(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    evaluation_as_of: datetime
    features: tuple[MarketContextFeatureSnapshot, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _features_must_form_one_point_in_time(self) -> CommittedMarketContextBundle:
        require_utc(self.evaluation_as_of)
        if any(item.snapshot.instrument_id != self.instrument_id for item in self.features):
            raise ValueError("committed feature bundle cannot cross instruments")
        if any(item.snapshot.as_of > self.evaluation_as_of for item in self.features):
            raise ValueError("committed feature bundle cannot contain future evidence")
        timeframes = [item.snapshot.timeframe for item in self.features]
        if len(timeframes) != len(set(timeframes)):
            raise ValueError("committed feature bundle requires one feature per timeframe")
        return self

    def feature(self, timeframe: AnalyticsTimeframe) -> MarketContextFeatureSnapshot | None:
        return next(
            (item for item in self.features if item.snapshot.timeframe == timeframe),
            None,
        )


@dataclass(frozen=True)
class DirectionQualification:
    status: DirectionQualificationStatus
    direction: SignalDirection | None
    is_degraded: bool
    reason_codes: tuple[str, ...]
    evidence_features: tuple[MarketContextFeatureSnapshot, ...]


@dataclass(frozen=True)
class DirectionCandidateDecision:
    qualification: DirectionQualification
    candidate: SignalSnapshot | None
    ended_signal_id: str | None
    regime_anchor: str | None


@dataclass(frozen=True)
class _DirectionRegime:
    direction: SignalDirection
    started_ts: datetime
    signal_id: str


class DirectionRegimeTracker:
    def __init__(self, definition: SignalDefinitionConfig) -> None:
        self._definition = definition
        self._regimes: dict[str, _DirectionRegime] = {}

    def seed_open_signals(
        self,
        signals: tuple[SignalSnapshot, ...],
        *,
        include_expired: bool = False,
    ) -> None:
        for signal in signals:
            if signal.status == SignalStatus.INVALIDATED or (
                signal.status == SignalStatus.EXPIRED and not include_expired
            ):
                continue
            if (
                signal.definition_id != self._definition.definition_id
                or signal.algorithm_version != self._definition.algorithm_version
                or signal.configuration_hash != self._definition.configuration_hash
            ):
                continue
            if signal.instrument_id in self._regimes:
                raise ValueError("multiple open direction regimes exist for one definition")
            if signal.direction_regime_anchor is None:
                started_ts = signal.created_ts
                expected_setup_key = signal_setup_key(
                    family=self._definition.family,
                    definition_id=self._definition.definition_id,
                    instrument_id=signal.instrument_id,
                    direction=signal.direction,
                    anchor=_regime_anchor(started_ts),
                )
                if signal.setup_key != expected_setup_key:
                    raise ValueError("restored signal setup key does not match direction regime")
            else:
                started_ts = _regime_started_ts(signal.direction_regime_anchor)
            self._regimes[signal.instrument_id] = _DirectionRegime(
                direction=signal.direction,
                started_ts=started_ts,
                signal_id=signal.signal_id,
            )

    def evaluate(self, bundle: CommittedMarketContextBundle) -> DirectionCandidateDecision:
        qualification = qualify_direction(bundle, self._definition)
        existing = self._regimes.get(bundle.instrument_id)
        if qualification.direction is None:
            anchor = None if existing is None else _regime_anchor(existing.started_ts)
            return DirectionCandidateDecision(qualification, None, None, anchor)
        if existing is not None and existing.direction == qualification.direction:
            return DirectionCandidateDecision(
                qualification,
                None,
                None,
                _regime_anchor(existing.started_ts),
            )

        candidate = _build_candidate(bundle, self._definition, qualification)
        ended = None if existing is None else existing.signal_id
        self._regimes[bundle.instrument_id] = _DirectionRegime(
            direction=candidate.direction,
            started_ts=candidate.created_ts,
            signal_id=candidate.signal_id,
        )
        return DirectionCandidateDecision(
            qualification,
            candidate,
            ended,
            _regime_anchor(candidate.created_ts),
        )


def qualify_direction(
    bundle: CommittedMarketContextBundle,
    definition: SignalDefinitionConfig,
) -> DirectionQualification:
    evaluation = bundle.feature(definition.evaluation_timeframe)
    if evaluation is None or evaluation.snapshot.as_of != bundle.evaluation_as_of:
        return _result(
            DirectionQualificationStatus.MISSING_EVIDENCE,
            None,
            False,
            (f"missing_current_{definition.evaluation_timeframe.value}_evaluation_feature",),
            bundle,
            definition,
        )

    primary: list[
        tuple[AnalyticsTimeframe, MarketContextFeatureSnapshot, SignalDirection | None]
    ] = []
    missing_primary: list[AnalyticsTimeframe] = []
    for timeframe in definition.primary_direction_timeframes:
        feature = bundle.feature(timeframe)
        if feature is None:
            missing_primary.append(timeframe)
        else:
            primary.append(
                (
                    timeframe,
                    feature,
                    _score_direction(feature.snapshot.direction_score, definition),
                )
            )
    if missing_primary:
        return _result(
            DirectionQualificationStatus.MISSING_EVIDENCE,
            None,
            False,
            tuple(f"missing_primary_{item.value}" for item in missing_primary),
            bundle,
            definition,
        )
    if any(direction is None for _, _, direction in primary):
        return _result(
            DirectionQualificationStatus.NEUTRAL,
            None,
            False,
            tuple(
                f"neutral_primary_{timeframe.value}"
                for timeframe, _, direction in primary
                if direction is None
            ),
            bundle,
            definition,
        )
    primary_directions = {direction for _, _, direction in primary}
    if len(primary_directions) != 1:
        return _result(
            DirectionQualificationStatus.CONFLICTED,
            None,
            False,
            ("primary_direction_disagreement",),
            bundle,
            definition,
        )
    direction = next(iter(primary_directions))
    assert direction is not None

    confirmation_count = 0
    confirmation_reasons: list[str] = []
    for timeframe in definition.confirmation_timeframes:
        feature = bundle.feature(timeframe)
        if feature is None:
            confirmation_reasons.append(f"missing_confirmation_{timeframe.value}")
            continue
        observed = _score_direction(feature.snapshot.direction_score, definition)
        if observed == direction:
            confirmation_count += 1
            confirmation_reasons.append(f"matching_confirmation_{timeframe.value}")
        elif observed is None:
            confirmation_reasons.append(f"neutral_confirmation_{timeframe.value}")
        else:
            confirmation_reasons.append(f"opposing_confirmation_{timeframe.value}")
    if confirmation_count < definition.minimum_confirmation_count:
        if any(reason.startswith("opposing_confirmation_") for reason in confirmation_reasons):
            status = DirectionQualificationStatus.CONFLICTED
        elif any(reason.startswith("neutral_confirmation_") for reason in confirmation_reasons):
            status = DirectionQualificationStatus.NEUTRAL
        else:
            status = DirectionQualificationStatus.MISSING_EVIDENCE
        return _result(
            status,
            None,
            False,
            (
                *confirmation_reasons,
                "insufficient_matching_confirmations",
            ),
            bundle,
            definition,
        )

    degraded = False
    context_reasons: list[str] = []
    for timeframe in definition.context_timeframes:
        feature = bundle.feature(timeframe)
        if feature is None:
            degraded = True
            context_reasons.append(f"missing_context_{timeframe.value}")
            continue
        observed = _score_direction(feature.snapshot.direction_score, definition)
        if observed is None:
            context_reasons.append(f"neutral_context_{timeframe.value}")
        elif observed == direction:
            context_reasons.append(f"supporting_context_{timeframe.value}")
        elif definition.opposing_context_policy == OpposingContextPolicy.VETO:
            return _result(
                DirectionQualificationStatus.VETOED,
                None,
                False,
                (f"opposing_context_veto_{timeframe.value}",),
                bundle,
                definition,
            )
        elif definition.opposing_context_policy == OpposingContextPolicy.DEGRADE:
            degraded = True
            context_reasons.append(f"opposing_context_degraded_{timeframe.value}")
        else:
            context_reasons.append(f"opposing_context_ignored_{timeframe.value}")

    return _result(
        DirectionQualificationStatus.QUALIFIED,
        direction,
        degraded,
        (
            *(f"matching_primary_{timeframe.value}" for timeframe, _, _ in primary),
            *confirmation_reasons,
            *context_reasons,
        ),
        bundle,
        definition,
    )


def _result(
    status: DirectionQualificationStatus,
    direction: SignalDirection | None,
    degraded: bool,
    reasons: tuple[str, ...],
    bundle: CommittedMarketContextBundle,
    definition: SignalDefinitionConfig,
) -> DirectionQualification:
    ordered: list[MarketContextFeatureSnapshot] = []
    for timeframe in (
        definition.evaluation_timeframe,
        *definition.primary_direction_timeframes,
        *definition.confirmation_timeframes,
        *definition.context_timeframes,
    ):
        feature = bundle.feature(timeframe)
        if feature is not None and feature not in ordered:
            ordered.append(feature)
    return DirectionQualification(status, direction, degraded, reasons, tuple(ordered))


def _score_direction(
    score: int,
    definition: SignalDefinitionConfig,
) -> SignalDirection | None:
    if score >= definition.minimum_direction_score:
        return SignalDirection.LONG
    if score <= -definition.minimum_direction_score:
        return SignalDirection.SHORT
    return None


def _build_candidate(
    bundle: CommittedMarketContextBundle,
    definition: SignalDefinitionConfig,
    qualification: DirectionQualification,
) -> SignalSnapshot:
    if qualification.direction is None:
        raise ValueError("cannot build candidate from unqualified direction")
    evidence = tuple(
        SignalEvidenceReference(
            instrument_id=bundle.instrument_id,
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
        for feature in qualification.evidence_features
    )
    return SignalSnapshot(
        family=definition.family,
        definition_id=definition.definition_id,
        algorithm_version=definition.algorithm_version,
        configuration_hash=definition.configuration_hash,
        setup_key=signal_setup_key(
            family=definition.family,
            definition_id=definition.definition_id,
            instrument_id=bundle.instrument_id,
            direction=qualification.direction,
            anchor=_regime_anchor(bundle.evaluation_as_of),
        ),
        instrument_id=bundle.instrument_id,
        direction=qualification.direction,
        created_ts=bundle.evaluation_as_of,
        updated_ts=bundle.evaluation_as_of,
        evidence=evidence,
        reason_codes=qualification.reason_codes,
    )


def _regime_anchor(started_ts: datetime) -> str:
    return f"direction_regime:{require_utc(started_ts).isoformat()}"


def _regime_started_ts(anchor: str) -> datetime:
    prefix = "direction_regime:"
    if not anchor.startswith(prefix):
        raise ValueError("restored signal has invalid direction regime anchor")
    try:
        started_ts = datetime.fromisoformat(anchor.removeprefix(prefix))
    except ValueError as error:
        raise ValueError("restored signal has invalid direction regime anchor") from error
    require_utc(started_ts)
    if _regime_anchor(started_ts) != anchor:
        raise ValueError("restored signal has noncanonical direction regime anchor")
    return started_ts


def _signal_fidelity(value: AnalyticsInputFidelity) -> SignalEvidenceFidelity:
    return {
        AnalyticsInputFidelity.REPORTED: SignalEvidenceFidelity.REPORTED,
        AnalyticsInputFidelity.INFERRED: SignalEvidenceFidelity.INFERRED,
        AnalyticsInputFidelity.MIXED: SignalEvidenceFidelity.PARTIAL,
    }[value]
