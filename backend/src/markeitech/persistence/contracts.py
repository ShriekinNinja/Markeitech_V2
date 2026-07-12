from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from markeitech.domain.base import (
    VersionedDomainModel,
    require_utc,
    utc_datetime_from_unix_ns,
)

FORBIDDEN_OUTBOX_PAYLOAD_KEYS = frozenset({"secret", "token", "webhook_token", "webhook_url"})


class DataFidelity(StrEnum):
    REPORTED = "reported"
    INFERRED = "inferred"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class PersistenceEventKind(StrEnum):
    TRADE_TICK = "trade_tick"
    QUOTE_TICK = "quote_tick"
    ONE_MINUTE_BAR = "one_minute_bar"


class RecoveryStatus(StrEnum):
    PENDING = "pending"
    RECOVERING = "recovering"
    COMPLETE = "complete"
    DEGRADED = "degraded"
    FAILED = "failed"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    LEASED = "leased"
    DELIVERED = "delivered"
    FAILED = "failed"


class PersistenceEventIdentity(VersionedDomainModel):
    event_kind: PersistenceEventKind
    instrument_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    fidelity: DataFidelity
    dedupe_key: str = Field(min_length=1)
    event_ts: datetime
    event_ts_ns: int | None = Field(default=None, ge=0)
    derivation_method: str | None = Field(default=None, min_length=1)

    @field_validator("event_ts")
    @classmethod
    def _event_ts_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _fidelity_must_match_derivation(self) -> PersistenceEventIdentity:
        if self.fidelity == DataFidelity.REPORTED and self.derivation_method is not None:
            raise ValueError("reported data cannot define a derivation method")
        if self.fidelity in {DataFidelity.INFERRED, DataFidelity.PARTIAL}:
            if self.derivation_method is None:
                raise ValueError("inferred or partial data requires a derivation method")
        if self.event_ts_ns is not None:
            if utc_datetime_from_unix_ns(self.event_ts_ns) != self.event_ts:
                raise ValueError("event_ts_ns must match event_ts at microsecond precision")
        return self


class StreamCheckpoint(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    event_kind: PersistenceEventKind
    source: str = Field(min_length=1)
    last_event_ts: datetime
    last_event_ts_ns: int | None = Field(default=None, ge=0)
    last_dedupe_key: str = Field(min_length=1)
    committed_ts: datetime

    @field_validator("last_event_ts", "committed_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @property
    def stream_key(self) -> str:
        return f"{self.source}:{self.instrument_id}:{self.event_kind}"

    @model_validator(mode="after")
    def _nanosecond_timestamp_must_match(self) -> StreamCheckpoint:
        if self.last_event_ts_ns is not None:
            if utc_datetime_from_unix_ns(self.last_event_ts_ns) != self.last_event_ts:
                raise ValueError(
                    "last_event_ts_ns must match last_event_ts at microsecond precision"
                )
        return self


class RecoveryRecord(VersionedDomainModel):
    recovery_id: UUID
    instrument_id: str = Field(min_length=1)
    event_kind: PersistenceEventKind
    source: str = Field(min_length=1)
    status: RecoveryStatus
    requested_start_ts: datetime
    requested_end_ts: datetime
    missing_intervals: int = Field(default=0, ge=0)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    started_ts: datetime
    updated_ts: datetime
    completed_ts: datetime | None = None

    @field_validator(
        "requested_start_ts",
        "requested_end_ts",
        "started_ts",
        "updated_ts",
        "completed_ts",
    )
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _recovery_state_must_be_consistent(self) -> RecoveryRecord:
        if self.requested_end_ts <= self.requested_start_ts:
            raise ValueError("recovery end must be after start")
        terminal = self.status in {
            RecoveryStatus.COMPLETE,
            RecoveryStatus.DEGRADED,
            RecoveryStatus.FAILED,
        }
        if terminal != (self.completed_ts is not None):
            raise ValueError("terminal recovery state must define completed_ts")
        if self.status in {RecoveryStatus.DEGRADED, RecoveryStatus.FAILED}:
            if not self.reason_codes:
                raise ValueError("degraded or failed recovery requires reason codes")
        if self.status == RecoveryStatus.COMPLETE and self.missing_intervals != 0:
            raise ValueError("complete recovery cannot retain missing intervals")
        return self


class NotificationOutboxRecord(VersionedDomainModel):
    outbox_id: UUID
    topic: str = Field(min_length=1)
    destination_key: str = Field(min_length=1)
    aggregate_key: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    event_schema_version: str = Field(min_length=1)
    payload: dict[str, Any]
    dedupe_key: str = Field(min_length=1)
    status: OutboxStatus = OutboxStatus.PENDING
    attempt_count: int = Field(default=0, ge=0)
    available_ts: datetime
    created_ts: datetime
    updated_ts: datetime
    lease_expires_ts: datetime | None = None
    delivered_ts: datetime | None = None
    last_error: str | None = Field(default=None, min_length=1)

    @field_validator(
        "available_ts",
        "created_ts",
        "updated_ts",
        "lease_expires_ts",
        "delivered_ts",
    )
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _delivery_state_must_be_consistent(self) -> NotificationOutboxRecord:
        if _contains_forbidden_payload_key(self.payload):
            raise ValueError("outbox payload cannot contain delivery secrets")
        if self.status == OutboxStatus.LEASED and self.lease_expires_ts is None:
            raise ValueError("leased outbox record requires lease expiry")
        if self.status != OutboxStatus.LEASED and self.lease_expires_ts is not None:
            raise ValueError("only leased outbox records can define lease expiry")
        if self.status == OutboxStatus.DELIVERED and self.delivered_ts is None:
            raise ValueError("delivered outbox record requires delivered_ts")
        if self.status != OutboxStatus.DELIVERED and self.delivered_ts is not None:
            raise ValueError("only delivered outbox records can define delivered_ts")
        if self.status == OutboxStatus.FAILED and self.last_error is None:
            raise ValueError("failed outbox record requires last_error")
        if self.updated_ts < self.created_ts:
            raise ValueError("outbox updated_ts cannot precede created_ts")
        if self.delivered_ts is not None and self.delivered_ts < self.created_ts:
            raise ValueError("outbox delivered_ts cannot precede created_ts")
        return self


def _contains_forbidden_payload_key(payload: Any) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key).lower() in FORBIDDEN_OUTBOX_PAYLOAD_KEYS:
                return True
            if _contains_forbidden_payload_key(value):
                return True
    elif isinstance(payload, list | tuple):
        return any(_contains_forbidden_payload_key(value) for value in payload)
    return False
