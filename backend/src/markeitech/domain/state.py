from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from markeitech.domain.base import VersionedDomainModel, require_utc


class ReadinessStatus(StrEnum):
    NOT_READY = "not_ready"
    DEGRADED = "degraded"
    READY = "ready"


class SourceStatus(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class GapSeverity(StrEnum):
    NONE = "none"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class ReadinessState(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    status: ReadinessStatus
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    required_sessions: int = Field(default=5, ge=0)
    complete_sessions: int = Field(default=0, ge=0)
    updated_ts: datetime

    @field_validator("updated_ts")
    @classmethod
    def _updated_ts_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _readiness_must_match_counts(self) -> ReadinessState:
        if self.complete_sessions > self.required_sessions:
            raise ValueError("complete sessions cannot exceed required sessions")
        if self.status == ReadinessStatus.READY and self.reason_codes:
            raise ValueError("ready state cannot carry degradation reason codes")
        if self.status != ReadinessStatus.READY and not self.reason_codes:
            raise ValueError("non-ready readiness state requires reason codes")
        return self


class GapState(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    severity: GapSeverity
    open_ts: datetime | None = None
    close_ts: datetime | None = None
    missing_intervals: int = Field(default=0, ge=0)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    updated_ts: datetime

    @field_validator("open_ts", "close_ts", "updated_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _gap_state_must_be_consistent(self) -> GapState:
        if self.open_ts and self.close_ts and self.close_ts <= self.open_ts:
            raise ValueError("gap close timestamp must be after open timestamp")
        if self.severity == GapSeverity.NONE and self.missing_intervals != 0:
            raise ValueError("gap severity none cannot have missing intervals")
        if self.severity != GapSeverity.NONE and not self.reason_codes:
            raise ValueError("active gap state requires reason codes")
        return self


class SourceHealth(VersionedDomainModel):
    source: str = Field(min_length=1)
    status: SourceStatus
    last_event_ts: datetime | None = None
    last_heartbeat_ts: datetime | None = None
    lag_ms: int | None = Field(default=None, ge=0)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    updated_ts: datetime

    @field_validator("last_event_ts", "last_heartbeat_ts", "updated_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _source_health_must_have_reasons_when_bad(self) -> SourceHealth:
        if self.status in {SourceStatus.DEGRADED, SourceStatus.FAILED} and not self.reason_codes:
            raise ValueError("degraded or failed source health requires reason codes")
        return self
