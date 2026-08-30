from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from markeitech.intelligence.session import CalendarProjection

CALENDAR_PROJECTION_REQUEST_TYPE_NAME = "markeitech.calendar.projection.request.v1"
CALENDAR_PROJECTION_RESPONSE_TYPE_NAME = "markeitech.calendar.projection.response.v2"
CALENDAR_TRANSITION_TYPE_NAME = "markeitech.calendar.transition.v1"
CALENDAR_PROJECTION_REQUEST_SCHEMA_VERSION = 1
CALENDAR_PROJECTION_RESPONSE_SCHEMA_VERSION = 2
CALENDAR_TRANSITION_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class CalendarProjectionRequest:
    request_id: str
    requester: str
    calendar_ids: tuple[str, ...]
    start_ns: int
    end_ns: int
    requested_ts_ns: int
    schema_version: int = CALENDAR_PROJECTION_REQUEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _text(self.request_id, "request_id")
        _text(self.requester, "requester")
        _schema(
            self.schema_version,
            CALENDAR_PROJECTION_REQUEST_SCHEMA_VERSION,
            "calendar projection request",
        )
        if not self.calendar_ids or len(self.calendar_ids) != len(set(self.calendar_ids)):
            raise ValueError("calendar_ids must be non-empty and unique")
        for calendar_id in self.calendar_ids:
            _text(calendar_id, "calendar_id")
        _timestamp(self.start_ns, "start_ns")
        _timestamp(self.end_ns, "end_ns")
        _timestamp(self.requested_ts_ns, "requested_ts_ns")
        if self.end_ns <= self.start_ns:
            raise ValueError("projection request end_ns must be after start_ns")

    @property
    def ts_event(self) -> int:
        return self.requested_ts_ns

    @property
    def ts_init(self) -> int:
        return self.requested_ts_ns


@dataclass(frozen=True, slots=True)
class CalendarProjectionFailure:
    calendar_id: str
    code: str
    reason: str
    retryable: bool

    def __post_init__(self) -> None:
        _text(self.calendar_id, "calendar_id")
        if (
            not isinstance(self.code, str)
            or re.fullmatch(r"[a-z][a-z0-9_]{0,63}", self.code) is None
        ):
            raise ValueError("calendar projection failure code must be stable snake_case")
        if (
            not isinstance(self.reason, str)
            or not self.reason.strip()
            or len(self.reason) > 160
            or "\n" in self.reason
            or "\r" in self.reason
        ):
            raise ValueError("calendar projection failure reason must be one bounded line")
        if not isinstance(self.retryable, bool):
            raise ValueError("calendar projection failure retryable must be a boolean")


@dataclass(frozen=True, slots=True)
class CalendarProjectionResponse:
    request_id: str
    requester: str
    source: str
    source_epoch: str
    status: str
    requested_calendar_ids: tuple[str, ...]
    projections: tuple[CalendarProjection, ...]
    unavailable_calendar_ids: tuple[str, ...]
    failures: tuple[CalendarProjectionFailure, ...]
    generated_ts_ns: int
    retry_at_ns: int | None = None
    schema_version: int = CALENDAR_PROJECTION_RESPONSE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in ("request_id", "requester", "source", "source_epoch"):
            _text(getattr(self, field), field)
        _schema(
            self.schema_version,
            CALENDAR_PROJECTION_RESPONSE_SCHEMA_VERSION,
            "calendar projection response",
        )
        if self.status not in {"READY", "NOT_READY", "REJECTED", "FAILED", "INCOMPLETE"}:
            raise ValueError("unsupported calendar projection response status")
        _unique_ids(self.requested_calendar_ids, "requested_calendar_ids")
        projected_ids = tuple(item.calendar_id for item in self.projections)
        failure_ids = tuple(item.calendar_id for item in self.failures)
        _unique_ids(projected_ids, "projected calendar ids", allow_empty=True)
        _unique_ids(self.unavailable_calendar_ids, "unavailable_calendar_ids", allow_empty=True)
        _unique_ids(failure_ids, "failure calendar ids", allow_empty=True)
        accounting = (
            set(projected_ids),
            set(self.unavailable_calendar_ids),
            set(failure_ids),
        )
        if any(
            accounting[index] & accounting[other]
            for index in range(3)
            for other in range(index + 1, 3)
        ):
            raise ValueError("calendar must have exactly one projection response outcome")
        if set().union(*accounting) != set(self.requested_calendar_ids):
            raise ValueError("projection response must account for every requested calendar")
        if self.status == "READY" and (self.unavailable_calendar_ids or self.failures):
            raise ValueError(
                "READY projection response cannot report unavailable or failed calendars",
            )
        if self.status == "NOT_READY" and (
            self.projections
            or self.failures
            or set(self.unavailable_calendar_ids) != set(self.requested_calendar_ids)
        ):
            raise ValueError("NOT_READY projection response must mark every calendar unavailable")
        if self.status == "REJECTED" and (
            self.projections
            or self.failures
            or set(self.unavailable_calendar_ids) != set(self.requested_calendar_ids)
        ):
            raise ValueError("REJECTED projection response must mark every calendar unavailable")
        if self.status == "FAILED" and (
            self.projections
            or self.unavailable_calendar_ids
            or set(failure_ids) != set(self.requested_calendar_ids)
        ):
            raise ValueError("FAILED projection response must fail every requested calendar")
        if self.status == "INCOMPLETE" and not (
            self.unavailable_calendar_ids or self.failures
        ):
            raise ValueError("INCOMPLETE projection response requires non-success outcomes")
        _timestamp(self.generated_ts_ns, "generated_ts_ns")
        if self.retry_at_ns is not None:
            _timestamp(self.retry_at_ns, "retry_at_ns")
            if self.retry_at_ns <= self.generated_ts_ns:
                raise ValueError("retry_at_ns must be after generated_ts_ns")
        retryable = self.status == "NOT_READY" or any(item.retryable for item in self.failures)
        if retryable != (self.retry_at_ns is not None):
            raise ValueError("retry_at_ns must be present exactly for retryable responses")

    @property
    def ts_event(self) -> int:
        return self.generated_ts_ns

    @property
    def ts_init(self) -> int:
        return self.generated_ts_ns


@dataclass(frozen=True, slots=True)
class CalendarTransition:
    event_id: str
    source: str
    source_epoch: str
    calendar_id: str
    schedule_version: str
    definition_version: int
    definition_digest: str
    effective_from_ns: int
    trade_date: str | None
    previous_trade_date: str | None
    phase_memberships: tuple[str, ...]
    previous_phase_memberships: tuple[str, ...]
    market_state: str
    previous_market_state: str | None
    segment_open_ns: int | None
    segment_close_ns: int | None
    next_transition_ns: int | None
    effective_ts_ns: int
    evaluated_ts_ns: int
    published_ts_ns: int
    revision: int
    previous_revision: int | None
    reason: str
    schema_version: int = CALENDAR_TRANSITION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "event_id",
            "source",
            "source_epoch",
            "calendar_id",
            "schedule_version",
            "definition_digest",
            "reason",
        ):
            _text(getattr(self, field), field)
        _schema(
            self.schema_version,
            CALENDAR_TRANSITION_SCHEMA_VERSION,
            "calendar transition",
        )
        if self.definition_version <= 0 or self.revision <= 0:
            raise ValueError("definition_version and revision must be positive")
        if re.fullmatch(r"[0-9a-f]{64}", self.definition_digest) is None:
            raise ValueError("definition_digest must be lowercase SHA-256")
        if self.previous_revision is not None and self.previous_revision != self.revision - 1:
            raise ValueError("previous_revision must immediately precede revision")
        if self.market_state not in {"OPEN", "BREAK", "CLOSED"}:
            raise ValueError("unsupported calendar market state")
        if self.previous_market_state is not None and self.previous_market_state not in {
            "OPEN",
            "BREAK",
            "CLOSED",
        }:
            raise ValueError("unsupported previous calendar market state")
        for field in ("phase_memberships", "previous_phase_memberships"):
            memberships = getattr(self, field)
            if len(memberships) != len(set(memberships)) or any(
                not isinstance(item, str) or not item.strip() for item in memberships
            ):
                raise ValueError(f"{field} must contain unique non-empty strings")
        for field in ("trade_date", "previous_trade_date"):
            value = getattr(self, field)
            if value is not None:
                try:
                    date.fromisoformat(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"{field} must be an ISO date") from exc
        for field in (
            "effective_from_ns",
            "effective_ts_ns",
            "evaluated_ts_ns",
            "published_ts_ns",
        ):
            _timestamp(getattr(self, field), field)
        for field in ("segment_open_ns", "segment_close_ns", "next_transition_ns"):
            value = getattr(self, field)
            if value is not None:
                _timestamp(value, field)
        if (self.segment_open_ns is None) != (self.segment_close_ns is None):
            raise ValueError("segment bounds must both be present or absent")
        if (
            self.segment_open_ns is not None
            and self.segment_close_ns is not None
            and self.segment_close_ns <= self.segment_open_ns
        ):
            raise ValueError("segment_close_ns must be after segment_open_ns")
        if self.evaluated_ts_ns < self.effective_ts_ns:
            raise ValueError("evaluated_ts_ns must not precede effective_ts_ns")
        if self.published_ts_ns < self.evaluated_ts_ns:
            raise ValueError("published_ts_ns must not precede evaluated_ts_ns")

    @property
    def phase(self) -> str:
        if self.phase_memberships:
            return "+".join(self.phase_memberships)
        return "CLOSED" if self.market_state == "CLOSED" else self.market_state

    @property
    def is_open(self) -> bool:
        return self.market_state == "OPEN"

    @property
    def phase_open_ns(self) -> int | None:
        return self.segment_open_ns

    @property
    def phase_close_ns(self) -> int | None:
        return self.segment_close_ns

    @property
    def ts_event(self) -> int:
        return self.effective_ts_ns

    @property
    def ts_init(self) -> int:
        return self.published_ts_ns


def _text(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def _timestamp(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _unique_ids(values: tuple[str, ...], label: str, *, allow_empty: bool = False) -> None:
    if (not values and not allow_empty) or len(values) != len(set(values)):
        raise ValueError(f"{label} must be {'unique' if allow_empty else 'non-empty and unique'}")
    for value in values:
        _text(value, label)


def _schema(value: object, expected: int, label: str) -> None:
    if value != expected:
        raise ValueError(f"unsupported {label} schema version: {value!r}")
