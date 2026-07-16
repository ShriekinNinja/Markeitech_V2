from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum

from pydantic import Field, computed_field, field_validator, model_validator

from markeitech.analytics import AnalyticsInputFidelity, AnalyticsTimeframe, TrendState
from markeitech.domain.base import VersionedDomainModel, require_utc

_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class ContextEventKind(StrEnum):
    TREND_CHANGED = "trend_changed"
    VALUE_AREA_REGION_CHANGED = "value_area_region_changed"


class ValueAreaRegion(StrEnum):
    UNAVAILABLE = "unavailable"
    BELOW = "below"
    INSIDE = "inside"
    ABOVE = "above"


class ContextTransitionEvent(VersionedDomainModel):
    kind: ContextEventKind
    instrument_id: str = Field(min_length=1)
    timeframe: AnalyticsTimeframe
    occurred_ts: datetime
    detected_ts: datetime
    previous_value: str = Field(min_length=1)
    current_value: str = Field(min_length=1)
    previous_feature_id: str = Field(pattern=_SHA256_PATTERN)
    current_feature_id: str = Field(pattern=_SHA256_PATTERN)
    previous_commit_sequence: int = Field(ge=1)
    current_commit_sequence: int = Field(ge=1)
    previous_input_fidelity: AnalyticsInputFidelity
    current_input_fidelity: AnalyticsInputFidelity
    reason_codes: tuple[str, ...] = Field(min_length=1)

    @field_validator("occurred_ts", "detected_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _transition_must_be_consistent(self) -> ContextTransitionEvent:
        if self.detected_ts < self.occurred_ts:
            raise ValueError("context event cannot be detected before it occurs")
        if self.current_commit_sequence <= self.previous_commit_sequence:
            raise ValueError("context event commit order must advance")
        if self.current_feature_id == self.previous_feature_id:
            raise ValueError("context event requires distinct feature evidence")
        if self.current_value == self.previous_value:
            raise ValueError("context event requires a value transition")
        allowed = (
            {state.value for state in TrendState if state != TrendState.INSUFFICIENT_DATA}
            if self.kind == ContextEventKind.TREND_CHANGED
            else {
                region.value
                for region in ValueAreaRegion
                if region != ValueAreaRegion.UNAVAILABLE
            }
        )
        if self.previous_value not in allowed or self.current_value not in allowed:
            raise ValueError("context event values do not match its kind")
        return self

    @computed_field
    @property
    def event_id(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "kind": self.kind.value,
            "instrument_id": self.instrument_id,
            "timeframe": self.timeframe.value,
            "occurred_ts": self.occurred_ts.isoformat(),
            "previous_value": self.previous_value,
            "current_value": self.current_value,
            "previous_feature_id": self.previous_feature_id,
            "current_feature_id": self.current_feature_id,
        }
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()
