from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = "1.0"


class DomainModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        use_enum_values=False,
    )


class VersionedDomainModel(DomainModel):
    schema_version: str = Field(default=SCHEMA_VERSION, min_length=1)


def require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware UTC")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamp must be UTC")
    return value.astimezone(UTC)


def require_iana_timezone(value: str) -> str:
    if value.upper().startswith("UTC") and value != "UTC":
        raise ValueError("fixed UTC offsets are not valid session timezones")
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("timezone must be a valid IANA timezone name") from exc
    return value


class InstrumentEvent(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    event_ts: datetime
    ts_init: datetime

    @field_validator("event_ts", "ts_init")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    def event_key_parts(self) -> tuple[Any, ...]:
        return (self.schema_version, self.instrument_id, self.event_ts.isoformat())
