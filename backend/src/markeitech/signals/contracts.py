from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from markeitech.analytics import AnalyticsTimeframe
from markeitech.domain.base import VersionedDomainModel, require_utc

_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class SignalFamily(StrEnum):
    DIRECTION_LOCATION_AGGRESSION = "direction_location_aggression"


class SignalDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


class SignalStatus(StrEnum):
    CANDIDATE = "candidate"
    ARMED = "armed"
    TRIGGERED = "triggered"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"


_ALLOWED_STATUS_TRANSITIONS = {
    SignalStatus.CANDIDATE: frozenset(
        {SignalStatus.ARMED, SignalStatus.INVALIDATED, SignalStatus.EXPIRED}
    ),
    SignalStatus.ARMED: frozenset(
        {SignalStatus.TRIGGERED, SignalStatus.INVALIDATED, SignalStatus.EXPIRED}
    ),
    SignalStatus.TRIGGERED: frozenset({SignalStatus.INVALIDATED, SignalStatus.EXPIRED}),
    SignalStatus.INVALIDATED: frozenset(),
    SignalStatus.EXPIRED: frozenset(),
}


class SignalEvidenceStage(StrEnum):
    DIRECTION = "direction"
    LOCATION = "location"
    AGGRESSION = "aggression"
    FOLLOW_THROUGH = "follow_through"


class SignalEvidenceType(StrEnum):
    MARKET_CONTEXT_FEATURE = "market_context_feature"
    MARKET_DATA_WINDOW = "market_data_window"


class SignalEvidenceFidelity(StrEnum):
    REPORTED = "reported"
    INFERRED = "inferred"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class SignalConfirmationMethod(StrEnum):
    TICK_AGGRESSION = "tick_aggression"
    BAR_IMPULSE_PROXY = "bar_impulse_proxy"


class LocationSourceKind(StrEnum):
    STRUCTURAL_LEVEL = "structural_level"
    FAIR_VALUE_GAP = "fair_value_gap"
    VALUE_AREA_EDGE = "value_area_edge"
    SESSION_VWAP = "session_vwap"


class SignalLocationZoneKind(StrEnum):
    SUPPORT = "support"
    RESISTANCE = "resistance"
    BULLISH_FVG = "bullish_fvg"
    BEARISH_FVG = "bearish_fvg"
    VALUE_AREA_LOW = "value_area_low"
    VALUE_AREA_HIGH = "value_area_high"
    SESSION_VWAP = "session_vwap"


class LocationQualificationStatus(StrEnum):
    QUALIFIED = "qualified"
    NOT_AT_LOCATION = "not_at_location"
    MISSING_EVIDENCE = "missing_evidence"
    INSUFFICIENT_CONFLUENCE = "insufficient_confluence"


_ZONE_SOURCE_KINDS = {
    SignalLocationZoneKind.SUPPORT: LocationSourceKind.STRUCTURAL_LEVEL,
    SignalLocationZoneKind.RESISTANCE: LocationSourceKind.STRUCTURAL_LEVEL,
    SignalLocationZoneKind.BULLISH_FVG: LocationSourceKind.FAIR_VALUE_GAP,
    SignalLocationZoneKind.BEARISH_FVG: LocationSourceKind.FAIR_VALUE_GAP,
    SignalLocationZoneKind.VALUE_AREA_LOW: LocationSourceKind.VALUE_AREA_EDGE,
    SignalLocationZoneKind.VALUE_AREA_HIGH: LocationSourceKind.VALUE_AREA_EDGE,
    SignalLocationZoneKind.SESSION_VWAP: LocationSourceKind.SESSION_VWAP,
}

_LONG_LOCATION_KINDS = {
    SignalLocationZoneKind.SUPPORT,
    SignalLocationZoneKind.BULLISH_FVG,
    SignalLocationZoneKind.VALUE_AREA_LOW,
    SignalLocationZoneKind.SESSION_VWAP,
}


class SignalLocationZone(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    direction: SignalDirection
    source_kind: LocationSourceKind
    zone_kind: SignalLocationZoneKind
    timeframe: AnalyticsTimeframe
    zone_anchor: str = Field(min_length=1)
    source_feature_id: str = Field(pattern=_SHA256_PATTERN)
    observed_ts: datetime
    lower_price: Decimal = Field(gt=0)
    upper_price: Decimal = Field(gt=0)
    fidelity: SignalEvidenceFidelity
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("observed_ts")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _zone_must_be_semantically_consistent(self) -> SignalLocationZone:
        if self.zone_anchor != self.zone_anchor.strip():
            raise ValueError("location zone anchor must be trimmed")
        if self.lower_price > self.upper_price:
            raise ValueError("location zone lower price cannot exceed upper price")
        if _ZONE_SOURCE_KINDS[self.zone_kind] != self.source_kind:
            raise ValueError("location zone kind must match source kind")
        if self.fidelity == SignalEvidenceFidelity.UNAVAILABLE:
            raise ValueError("location zone requires available evidence")
        long_aligned = self.zone_kind in _LONG_LOCATION_KINDS
        if self.zone_kind != SignalLocationZoneKind.SESSION_VWAP and (
            long_aligned != (self.direction == SignalDirection.LONG)
        ):
            raise ValueError("location zone kind must align with signal direction")
        return self

    @property
    def zone_id(self) -> str:
        return _canonical_hash(
            {
                "schema_version": self.schema_version,
                "instrument_id": self.instrument_id,
                "direction": self.direction.value,
                "source_kind": self.source_kind.value,
                "zone_kind": self.zone_kind.value,
                "timeframe": self.timeframe.value,
                "zone_anchor": self.zone_anchor,
            }
        )


class SignalLocationMatch(VersionedDomainModel):
    zone: SignalLocationZone
    evaluation_feature_id: str = Field(pattern=_SHA256_PATTERN)
    observed_ts: datetime
    observed_price: Decimal = Field(gt=0)
    distance: Decimal = Field(ge=0)
    tolerance: Decimal = Field(ge=0)
    fidelity: SignalEvidenceFidelity
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("observed_ts")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _match_must_touch_the_zone(self) -> SignalLocationMatch:
        if self.observed_ts < self.zone.observed_ts:
            raise ValueError("location match cannot precede zone evidence")
        if self.distance > self.tolerance:
            raise ValueError("location match distance cannot exceed tolerance")
        if self.fidelity == SignalEvidenceFidelity.UNAVAILABLE:
            raise ValueError("location match requires available evidence")
        return self


class LocationQualification(VersionedDomainModel):
    status: LocationQualificationStatus
    matches: tuple[SignalLocationMatch, ...] = ()
    is_degraded: bool = False
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _status_must_match_evidence(self) -> LocationQualification:
        if self.status == LocationQualificationStatus.QUALIFIED and not self.matches:
            raise ValueError("qualified location requires at least one match")
        if self.status == LocationQualificationStatus.NOT_AT_LOCATION and self.matches:
            raise ValueError("not-at-location result cannot contain matches")
        zone_ids = [item.zone.zone_id for item in self.matches]
        if len(zone_ids) != len(set(zone_ids)):
            raise ValueError("location qualification cannot repeat a semantic zone")
        return self


class SignalEvidenceReference(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    stage: SignalEvidenceStage
    evidence_type: SignalEvidenceType
    evidence_id: str = Field(pattern=_SHA256_PATTERN)
    observed_ts: datetime
    source: str = Field(min_length=1)
    fidelity: SignalEvidenceFidelity
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("observed_ts")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _feature_evidence_must_match_stage(self) -> SignalEvidenceReference:
        if self.stage in {SignalEvidenceStage.DIRECTION, SignalEvidenceStage.LOCATION}:
            if self.evidence_type != SignalEvidenceType.MARKET_CONTEXT_FEATURE:
                raise ValueError("direction and location require market-context feature evidence")
        return self

    @property
    def evidence_key(self) -> tuple[SignalEvidenceStage, SignalEvidenceType, str]:
        return self.stage, self.evidence_type, self.evidence_id


class SignalSnapshot(VersionedDomainModel):
    family: SignalFamily = SignalFamily.DIRECTION_LOCATION_AGGRESSION
    definition_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    algorithm_version: str = Field(min_length=1)
    configuration_hash: str = Field(pattern=_SHA256_PATTERN)
    setup_key: str = Field(pattern=_SHA256_PATTERN)
    instrument_id: str = Field(min_length=1)
    direction: SignalDirection
    status: SignalStatus = SignalStatus.CANDIDATE
    created_ts: datetime
    updated_ts: datetime
    direction_regime_anchor: str | None = Field(default=None, min_length=1)
    location_episode_id: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    location_matches: tuple[SignalLocationMatch, ...] = ()
    evidence: tuple[SignalEvidenceReference, ...] = Field(min_length=1)
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("created_ts", "updated_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _state_must_be_consistent(self) -> SignalSnapshot:
        if self.updated_ts < self.created_ts:
            raise ValueError("signal update cannot precede creation")
        if any(item.instrument_id != self.instrument_id for item in self.evidence):
            raise ValueError("signal evidence instrument must match signal")
        if any(item.observed_ts > self.updated_ts for item in self.evidence):
            raise ValueError("signal evidence cannot be newer than signal state")
        if self.direction_regime_anchor is not None and (
            self.direction_regime_anchor != self.direction_regime_anchor.strip()
        ):
            raise ValueError("signal direction regime anchor must be trimmed")
        if (self.location_episode_id is None) != (self.direction_regime_anchor is None):
            raise ValueError("signal location episode and direction regime must coexist")
        if self.location_matches and self.location_episode_id is None:
            raise ValueError("signal location matches require episode identity")
        if any(item.zone.instrument_id != self.instrument_id for item in self.location_matches):
            raise ValueError("signal location matches must use signal instrument")
        if any(item.zone.direction != self.direction for item in self.location_matches):
            raise ValueError("signal location matches must align with signal direction")
        if any(item.observed_ts > self.updated_ts for item in self.location_matches):
            raise ValueError("signal location matches cannot be newer than signal state")
        evidence_keys = [item.evidence_key for item in self.evidence]
        if len(evidence_keys) != len(set(evidence_keys)):
            raise ValueError("signal evidence references must be unique")
        available_stages = {
            item.stage
            for item in self.evidence
            if item.fidelity != SignalEvidenceFidelity.UNAVAILABLE
        }
        if SignalEvidenceStage.DIRECTION not in available_stages:
            raise ValueError("signals require available direction evidence")
        if self.status in {
            SignalStatus.ARMED,
            SignalStatus.TRIGGERED,
        }:
            if not {
                SignalEvidenceStage.DIRECTION,
                SignalEvidenceStage.LOCATION,
            }.issubset(available_stages):
                raise ValueError("armed signals require available direction and location evidence")
            if self.location_episode_id is None or not self.location_matches:
                raise ValueError("armed signals require a durable location episode")
            location_feature_ids = {
                item.evidence_id
                for item in self.evidence
                if item.stage == SignalEvidenceStage.LOCATION
                and item.fidelity != SignalEvidenceFidelity.UNAVAILABLE
            }
            required_location_feature_ids = {
                feature_id
                for item in self.location_matches
                for feature_id in (
                    item.zone.source_feature_id,
                    item.evaluation_feature_id,
                )
            }
            if not required_location_feature_ids.issubset(location_feature_ids):
                raise ValueError("armed signal evidence must cover location match features")
        if self.status == SignalStatus.TRIGGERED:
            if SignalEvidenceStage.AGGRESSION not in available_stages:
                raise ValueError("triggered signals require available aggression evidence")
        return self

    @property
    def signal_id(self) -> str:
        return _canonical_hash(
            {
                "schema_version": self.schema_version,
                "family": self.family.value,
                "definition_id": self.definition_id,
                "algorithm_version": self.algorithm_version,
                "configuration_hash": self.configuration_hash,
                "setup_key": self.setup_key,
                "instrument_id": self.instrument_id,
                "direction": self.direction.value,
            }
        )

    @property
    def content_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))

    @property
    def feature_ids(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                item.evidence_id
                for item in self.evidence
                if item.evidence_type == SignalEvidenceType.MARKET_CONTEXT_FEATURE
            )
        )


class SignalTransitionEvent(VersionedDomainModel):
    signal_id: str = Field(pattern=_SHA256_PATTERN)
    from_status: SignalStatus
    to_status: SignalStatus
    occurred_ts: datetime
    previous_content_hash: str = Field(pattern=_SHA256_PATTERN)
    current: SignalSnapshot
    appended_evidence: tuple[SignalEvidenceReference, ...] = ()
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("occurred_ts")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _transition_must_match_snapshot(self) -> SignalTransitionEvent:
        if self.to_status not in _ALLOWED_STATUS_TRANSITIONS[self.from_status]:
            raise ValueError(
                "signal status cannot move from "
                f"{self.from_status.value} to {self.to_status.value}"
            )
        if self.signal_id != self.current.signal_id:
            raise ValueError("transition signal id must match current snapshot")
        if self.to_status != self.current.status:
            raise ValueError("transition target must match current signal status")
        if self.occurred_ts != self.current.updated_ts:
            raise ValueError("transition timestamp must match current signal update")
        current_keys = {item.evidence_key for item in self.current.evidence}
        if any(item.evidence_key not in current_keys for item in self.appended_evidence):
            raise ValueError("appended transition evidence must exist in current signal")
        return self

    @property
    def transition_id(self) -> str:
        return _canonical_hash(
            {
                "schema_version": self.schema_version,
                "signal_id": self.signal_id,
                "from_status": self.from_status.value,
                "to_status": self.to_status.value,
                "occurred_ts": self.occurred_ts.isoformat(),
                "previous_content_hash": self.previous_content_hash,
                "current_content_hash": self.current.content_hash,
            }
        )


def signal_setup_key(
    *,
    family: SignalFamily,
    definition_id: str,
    instrument_id: str,
    direction: SignalDirection,
    anchor: str,
) -> str:
    if (
        not definition_id.strip()
        or definition_id != definition_id.strip()
        or not instrument_id.strip()
        or instrument_id != instrument_id.strip()
        or not anchor.strip()
        or anchor != anchor.strip()
    ):
        raise ValueError("signal setup identity requires definition, instrument, and anchor")
    return _canonical_hash(
        {
            "family": family.value,
            "definition_id": definition_id,
            "instrument_id": instrument_id,
            "direction": direction.value,
            "anchor": anchor,
        }
    )


def allowed_signal_statuses(status: SignalStatus) -> frozenset[SignalStatus]:
    return _ALLOWED_STATUS_TRANSITIONS[status]


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()
