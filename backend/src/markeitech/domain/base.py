from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    event_ts_ns: int | None = Field(default=None, ge=0)
    ts_init_ns: int | None = Field(default=None, ge=0)

    @field_validator("event_ts", "ts_init")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _nanosecond_timestamps_must_match_datetimes(self) -> InstrumentEvent:
        for field_name, ns_field_name in (
            ("event_ts", "event_ts_ns"),
            ("ts_init", "ts_init_ns"),
        ):
            timestamp_ns = getattr(self, ns_field_name)
            if timestamp_ns is None:
                continue
            if utc_datetime_from_unix_ns(timestamp_ns) != getattr(self, field_name):
                raise ValueError(
                    f"{ns_field_name} must match {field_name} at microsecond precision"
                )
        return self

    def event_key_parts(self) -> tuple[Any, ...]:
        event_time = self.event_ts_ns if self.event_ts_ns is not None else self.event_ts.isoformat()
        return (self.schema_version, self.instrument_id, event_time)


def utc_datetime_from_unix_ns(timestamp_ns: int) -> datetime:
    seconds, nanoseconds = divmod(timestamp_ns, 1_000_000_000)
    return datetime.fromtimestamp(seconds, tz=UTC).replace(microsecond=nanoseconds // 1_000)


def unix_ns_from_utc_datetime(value: datetime) -> int:
    value = require_utc(value)
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    elapsed = value - epoch
    return (
        elapsed.days * 86_400_000_000_000
        + elapsed.seconds * 1_000_000_000
        + elapsed.microseconds * 1_000
    )
