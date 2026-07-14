from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

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
    algorithm_version: str = Field(min_length=1)
    configuration_hash: str = Field(pattern=_SHA256_PATTERN)
    setup_key: str = Field(pattern=_SHA256_PATTERN)
    instrument_id: str = Field(min_length=1)
    direction: SignalDirection
    status: SignalStatus = SignalStatus.CANDIDATE
    created_ts: datetime
    updated_ts: datetime
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
        } and not {
            SignalEvidenceStage.DIRECTION,
            SignalEvidenceStage.LOCATION,
        }.issubset(available_stages):
            raise ValueError("armed signals require available direction and location evidence")
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
    instrument_id: str,
    direction: SignalDirection,
    anchor: str,
) -> str:
    if (
        not instrument_id.strip()
        or instrument_id != instrument_id.strip()
        or not anchor.strip()
        or anchor != anchor.strip()
    ):
        raise ValueError("signal setup identity requires instrument and anchor")
    return _canonical_hash(
        {
            "family": family.value,
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
