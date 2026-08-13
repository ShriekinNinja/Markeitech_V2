from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType

SYSTEM_HEALTH_SIGNAL = "markeitech.system.health"
SYSTEM_HEALTH_SCHEMA_VERSION = 1
COMPONENT_FAILURE_SIGNAL = "markeitech.component.failure"
COMPONENT_FAILURE_SCHEMA_VERSION = 1
ACQUISITION_STATUS_SIGNAL = "markeitech.acquisition.status"
ACQUISITION_STATUS_REQUEST_SIGNAL = "markeitech.acquisition.status.request"
ACQUISITION_STATUS_SCHEMA_VERSION = 1
ACQUISITION_STATUS_REQUEST_SCHEMA_VERSION = 1
ACQUISITION_STREAM_SIGNAL = "markeitech.acquisition.stream"
ACQUISITION_STREAM_SCHEMA_VERSION = 1

INSTRUMENTS_RESOLVING = "INSTRUMENTS_RESOLVING"
INSTRUMENTS_READY = "INSTRUMENTS_READY"
_ACQUISITION_STATES = {INSTRUMENTS_RESOLVING, INSTRUMENTS_READY}
_ACQUISITION_STREAM_STATES = {
    "REQUESTED",
    "ACCEPTED",
    "SUBSCRIBED",
    "ACTIVE",
    "COMPLETED",
    "REJECTED",
    "FAILED",
    "CANCELED",
    "EXPIRED",
}

type EvidenceValue = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class AcquisitionStreamEvent:
    state: str
    instrument_id: str
    feed_kind: str
    selector: str
    source: str
    demand_id: str | None
    consumer_ids: tuple[str, ...]
    detail: str
    schema_version: int = ACQUISITION_STREAM_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            not isinstance(self.schema_version, int)
            or isinstance(self.schema_version, bool)
            or self.schema_version != ACQUISITION_STREAM_SCHEMA_VERSION
        ):
            raise ValueError(f"unsupported acquisition stream schema: {self.schema_version}")
        for field_name in (
            "instrument_id",
            "feed_kind",
            "selector",
            "source",
            "detail",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())
        if not isinstance(self.state, str) or self.state.strip() not in _ACQUISITION_STREAM_STATES:
            raise ValueError(f"unsupported acquisition stream state: {self.state!r}")
        object.__setattr__(self, "state", self.state.strip())
        consumers = _normalize_text_values(self.consumer_ids, "consumer_ids")
        object.__setattr__(self, "consumer_ids", consumers)
        if self.demand_id is not None:
            if not isinstance(self.demand_id, str) or not self.demand_id.strip():
                raise ValueError("demand_id must be None or a non-empty string")
            object.__setattr__(self, "demand_id", self.demand_id.strip())

    def to_signal_value(self) -> str:
        return json.dumps(
            {
                "schema_version": self.schema_version,
                "state": self.state,
                "instrument_id": self.instrument_id,
                "feed_kind": self.feed_kind,
                "selector": self.selector,
                "source": self.source,
                "demand_id": self.demand_id,
                "consumer_ids": self.consumer_ids,
                "detail": self.detail,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_signal_value(cls, value: str) -> AcquisitionStreamEvent:
        payload = _load_exact_json_object(
            value,
            label="acquisition stream",
            expected={
                "schema_version",
                "state",
                "instrument_id",
                "feed_kind",
                "selector",
                "source",
                "demand_id",
                "consumer_ids",
                "detail",
            },
        )
        return cls(**payload)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class AcquisitionStatusRequest:
    requester: str
    schema_version: int = ACQUISITION_STATUS_REQUEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            not isinstance(self.schema_version, int)
            or isinstance(self.schema_version, bool)
            or self.schema_version != ACQUISITION_STATUS_REQUEST_SCHEMA_VERSION
        ):
            raise ValueError(
                f"unsupported acquisition status request schema: {self.schema_version}",
            )
        if not isinstance(self.requester, str) or not self.requester.strip():
            raise ValueError("requester must be a non-empty string")
        object.__setattr__(self, "requester", self.requester.strip())

    def to_signal_value(self) -> str:
        return json.dumps(
            {
                "schema_version": self.schema_version,
                "requester": self.requester,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_signal_value(cls, value: str) -> AcquisitionStatusRequest:
        payload = _load_exact_json_object(
            value,
            label="acquisition status request",
            expected={"schema_version", "requester"},
        )
        return cls(
            schema_version=payload["schema_version"],
            requester=payload["requester"],
        )


@dataclass(frozen=True, slots=True)
class AcquisitionStatusEvent:
    state: str
    reason: str
    source: str
    expected_instrument_ids: tuple[str, ...]
    available_instrument_ids: tuple[str, ...]
    schema_version: int = ACQUISITION_STATUS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            not isinstance(self.schema_version, int)
            or isinstance(self.schema_version, bool)
            or self.schema_version != ACQUISITION_STATUS_SCHEMA_VERSION
        ):
            raise ValueError(f"unsupported acquisition status schema: {self.schema_version}")
        for field_name in ("state", "reason", "source"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        state = self.state.strip()
        if state not in _ACQUISITION_STATES:
            raise ValueError(f"unsupported acquisition state: {state!r}")
        expected = _normalize_instrument_ids(
            self.expected_instrument_ids,
            "expected_instrument_ids",
            require_values=True,
        )
        available = _normalize_instrument_ids(
            self.available_instrument_ids,
            "available_instrument_ids",
            require_values=False,
        )
        if not set(available).issubset(expected):
            raise ValueError("available instruments must be a subset of expected instruments")
        complete = available == expected
        if state == INSTRUMENTS_READY and not complete:
            raise ValueError("INSTRUMENTS_READY requires every expected instrument")
        if state == INSTRUMENTS_RESOLVING and complete:
            raise ValueError("INSTRUMENTS_RESOLVING requires at least one missing instrument")
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "reason", self.reason.strip())
        object.__setattr__(self, "source", self.source.strip())
        object.__setattr__(self, "expected_instrument_ids", expected)
        object.__setattr__(self, "available_instrument_ids", available)

    @property
    def missing_instrument_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.expected_instrument_ids) - set(self.available_instrument_ids)))

    def to_signal_value(self) -> str:
        return json.dumps(
            {
                "schema_version": self.schema_version,
                "state": self.state,
                "reason": self.reason,
                "source": self.source,
                "expected_instrument_ids": self.expected_instrument_ids,
                "available_instrument_ids": self.available_instrument_ids,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_signal_value(cls, value: str) -> AcquisitionStatusEvent:
        payload = _load_exact_json_object(
            value,
            label="acquisition status",
            expected={
                "schema_version",
                "state",
                "reason",
                "source",
                "expected_instrument_ids",
                "available_instrument_ids",
            },
        )
        return cls(
            schema_version=payload["schema_version"],
            state=payload["state"],
            reason=payload["reason"],
            source=payload["source"],
            expected_instrument_ids=payload["expected_instrument_ids"],
            available_instrument_ids=payload["available_instrument_ids"],
        )


@dataclass(frozen=True, slots=True)
class ComponentFailureEvent:
    component: str
    code: str
    reason: str
    evidence: Mapping[str, EvidenceValue]
    schema_version: int = COMPONENT_FAILURE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            not isinstance(self.schema_version, int)
            or isinstance(self.schema_version, bool)
            or self.schema_version != COMPONENT_FAILURE_SCHEMA_VERSION
        ):
            raise ValueError(f"unsupported component failure schema: {self.schema_version}")
        for field_name in ("component", "code", "reason"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        _validate_evidence(self.evidence)
        object.__setattr__(self, "component", self.component.strip())
        object.__setattr__(self, "code", self.code.strip())
        object.__setattr__(self, "reason", self.reason.strip())
        object.__setattr__(self, "evidence", MappingProxyType(dict(self.evidence)))

    def to_signal_value(self) -> str:
        return json.dumps(
            {
                "schema_version": self.schema_version,
                "component": self.component,
                "code": self.code,
                "reason": self.reason,
                "evidence": dict(self.evidence),
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_signal_value(cls, value: str) -> ComponentFailureEvent:
        payload = _load_exact_json_object(
            value,
            label="component failure",
            expected={"schema_version", "component", "code", "reason", "evidence"},
        )
        return cls(
            schema_version=payload["schema_version"],
            component=payload["component"],
            code=payload["code"],
            reason=payload["reason"],
            evidence=payload["evidence"],
        )


@dataclass(frozen=True, slots=True)
class SystemHealthEvent:
    state: str
    reason: str
    source: str
    evidence: Mapping[str, EvidenceValue]
    schema_version: int = SYSTEM_HEALTH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            not isinstance(self.schema_version, int)
            or isinstance(self.schema_version, bool)
            or self.schema_version != SYSTEM_HEALTH_SCHEMA_VERSION
        ):
            raise ValueError(f"unsupported system health schema: {self.schema_version}")
        for field_name in ("state", "reason", "source"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        _validate_evidence(self.evidence)

        object.__setattr__(self, "state", self.state.strip())
        object.__setattr__(self, "reason", self.reason.strip())
        object.__setattr__(self, "source", self.source.strip())
        object.__setattr__(self, "evidence", MappingProxyType(dict(self.evidence)))

    def to_signal_value(self) -> str:
        return json.dumps(
            {
                "schema_version": self.schema_version,
                "state": self.state,
                "reason": self.reason,
                "source": self.source,
                "evidence": dict(self.evidence),
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_signal_value(cls, value: str) -> SystemHealthEvent:
        payload = _load_exact_json_object(
            value,
            label="system health",
            expected={"schema_version", "state", "reason", "source", "evidence"},
        )

        return cls(
            schema_version=payload["schema_version"],
            state=payload["state"],
            reason=payload["reason"],
            source=payload["source"],
            evidence=payload["evidence"],
        )


def _validate_evidence(evidence: Mapping[str, EvidenceValue]) -> None:
    if not isinstance(evidence, Mapping):
        raise ValueError("evidence must be a mapping")
    for key, value in evidence.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("evidence keys must be non-empty strings")
        if value is not None and not isinstance(value, str | int | float | bool):
            raise ValueError(f"unsupported evidence value for {key!r}")
        if isinstance(value, float) and not isfinite(value):
            raise ValueError(f"non-finite evidence value for {key!r}")


def _normalize_instrument_ids(
    values: object,
    label: str,
    *,
    require_values: bool,
) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{label} must be a list or tuple")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must contain non-empty strings")
        normalized.append(value.strip())
    if require_values and not normalized:
        raise ValueError(f"{label} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label} must not contain duplicates")
    return tuple(sorted(normalized))


def _normalize_text_values(values: object, label: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{label} must be a list or tuple")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must contain non-empty strings")
        normalized.append(value.strip())
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label} must not contain duplicates")
    return tuple(sorted(normalized))


def _load_exact_json_object(
    value: str,
    *,
    label: str,
    expected: set[str],
) -> dict[str, object]:
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} signal must contain valid JSON text") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} signal must contain a JSON object")
    actual = set(payload)
    if actual != expected:
        missing = expected - actual
        unknown = actual - expected
        details: list[str] = []
        if missing:
            details.append(f"missing: {', '.join(sorted(missing))}")
        if unknown:
            details.append(f"unknown: {', '.join(sorted(unknown))}")
        raise ValueError(f"invalid {label} fields ({'; '.join(details)})")
    return payload
