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
PERSISTENCE_READY_REQUEST_SIGNAL = "markeitech.persistence.ready.request"
PERSISTENCE_READY_SIGNAL = "markeitech.persistence.ready"
PERSISTENCE_READY_SCHEMA_VERSION = 1
ACQUISITION_STATUS_SIGNAL = "markeitech.acquisition.status"
ACQUISITION_STATUS_REQUEST_SIGNAL = "markeitech.acquisition.status.request"
ACQUISITION_STATUS_SCHEMA_VERSION = 1
ACQUISITION_STATUS_REQUEST_SCHEMA_VERSION = 1
ACQUISITION_STREAM_SIGNAL = "markeitech.acquisition.stream"
ACQUISITION_STREAM_SCHEMA_VERSION = 1
WATCHLIST_MEMBERSHIP_SIGNAL = "markeitech.watchlist.membership"
WATCHLIST_MEMBERSHIP_SCHEMA_VERSION = 1
WATCHLIST_LIFECYCLE_SIGNAL = "markeitech.watchlist.lifecycle"
WATCHLIST_LIFECYCLE_SCHEMA_VERSION = 1

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
_WATCHLIST_LIFECYCLE_STATES = {
    "CONFIGURED",
    "CONSUMERS_REGISTERED",
    "INSTRUMENT_OBSERVED",
    "OBSERVATION_DEGRADED",
    "CONSUMERS_DETACHED",
}

type EvidenceValue = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class PersistenceReadyRequest:
    requester: str
    schema_version: int = PERSISTENCE_READY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_schema_version(
            self.schema_version,
            PERSISTENCE_READY_SCHEMA_VERSION,
            "persistence readiness request",
        )
        object.__setattr__(self, "requester", _required_text(self.requester, "requester"))

    def to_signal_value(self) -> str:
        return json.dumps(
            {"schema_version": self.schema_version, "requester": self.requester},
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_signal_value(cls, value: str) -> PersistenceReadyRequest:
        payload = _load_exact_json_object(
            value,
            label="persistence readiness request",
            expected={"schema_version", "requester"},
        )
        return cls(**payload)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class PersistenceReadyEvent:
    source: str
    run_id: str
    schema_version: int = PERSISTENCE_READY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_schema_version(
            self.schema_version,
            PERSISTENCE_READY_SCHEMA_VERSION,
            "persistence readiness",
        )
        object.__setattr__(self, "source", _required_text(self.source, "source"))
        object.__setattr__(self, "run_id", _required_text(self.run_id, "run_id"))

    def to_signal_value(self) -> str:
        return json.dumps(
            {
                "schema_version": self.schema_version,
                "source": self.source,
                "run_id": self.run_id,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_signal_value(cls, value: str) -> PersistenceReadyEvent:
        payload = _load_exact_json_object(
            value,
            label="persistence readiness",
            expected={"schema_version", "source", "run_id"},
        )
        return cls(**payload)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class WatchlistMember:
    instrument_id: str
    capabilities: tuple[str, ...]
    owner_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "instrument_id",
            _required_text(self.instrument_id, "instrument_id"),
        )
        object.__setattr__(
            self,
            "capabilities",
            _normalize_required_text_values(self.capabilities, "capabilities"),
        )
        object.__setattr__(
            self,
            "owner_ids",
            _normalize_required_text_values(self.owner_ids, "owner_ids"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "instrument_id": self.instrument_id,
            "capabilities": self.capabilities,
            "owner_ids": self.owner_ids,
        }

    @classmethod
    def from_dict(cls, value: object) -> WatchlistMember:
        payload = _exact_object(
            value,
            label="watchlist member",
            expected={"instrument_id", "capabilities", "owner_ids"},
        )
        return cls(**payload)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class WatchlistMembershipEvent:
    event_id: str
    membership_revision: int
    source: str
    reason: str
    members: tuple[WatchlistMember, ...]
    schema_version: int = WATCHLIST_MEMBERSHIP_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_schema_version(
            self.schema_version,
            WATCHLIST_MEMBERSHIP_SCHEMA_VERSION,
            "watchlist membership",
        )
        object.__setattr__(self, "event_id", _required_text(self.event_id, "event_id"))
        object.__setattr__(self, "source", _required_text(self.source, "source"))
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))
        _validate_positive_int(self.membership_revision, "membership_revision")
        if not isinstance(self.members, (list, tuple)) or not self.members:
            raise ValueError("members must contain at least one WatchlistMember")
        members = tuple(
            member if isinstance(member, WatchlistMember) else WatchlistMember.from_dict(member)
            for member in self.members
        )
        instrument_ids = [member.instrument_id for member in members]
        if len(instrument_ids) != len(set(instrument_ids)):
            raise ValueError("members must not contain duplicate instruments")
        object.__setattr__(
            self,
            "members",
            tuple(sorted(members, key=lambda item: item.instrument_id)),
        )

    def to_signal_value(self) -> str:
        return json.dumps(
            {
                "schema_version": self.schema_version,
                "event_id": self.event_id,
                "membership_revision": self.membership_revision,
                "source": self.source,
                "reason": self.reason,
                "members": [member.to_dict() for member in self.members],
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_signal_value(cls, value: str) -> WatchlistMembershipEvent:
        payload = _load_exact_json_object(
            value,
            label="watchlist membership",
            expected={
                "schema_version",
                "event_id",
                "membership_revision",
                "source",
                "reason",
                "members",
            },
        )
        return cls(**payload)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class WatchlistLifecycleEvent:
    event_id: str
    membership_revision: int
    state: str
    source: str
    reason: str
    instrument_id: str | None = None
    owner_id: str | None = None
    correlation_id: str | None = None
    schema_version: int = WATCHLIST_LIFECYCLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_schema_version(
            self.schema_version,
            WATCHLIST_LIFECYCLE_SCHEMA_VERSION,
            "watchlist lifecycle",
        )
        object.__setattr__(self, "event_id", _required_text(self.event_id, "event_id"))
        object.__setattr__(self, "source", _required_text(self.source, "source"))
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))
        _validate_positive_int(self.membership_revision, "membership_revision")
        state = _required_text(self.state, "state")
        if state not in _WATCHLIST_LIFECYCLE_STATES:
            raise ValueError(f"unsupported watchlist lifecycle state: {state!r}")
        object.__setattr__(self, "state", state)
        for field_name in ("instrument_id", "owner_id", "correlation_id"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _required_text(value, field_name))
        if state == "INSTRUMENT_OBSERVED" and self.instrument_id is None:
            raise ValueError("INSTRUMENT_OBSERVED requires instrument_id")

    def to_signal_value(self) -> str:
        return json.dumps(
            {
                "schema_version": self.schema_version,
                "event_id": self.event_id,
                "membership_revision": self.membership_revision,
                "state": self.state,
                "source": self.source,
                "reason": self.reason,
                "instrument_id": self.instrument_id,
                "owner_id": self.owner_id,
                "correlation_id": self.correlation_id,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_signal_value(cls, value: str) -> WatchlistLifecycleEvent:
        payload = _load_exact_json_object(
            value,
            label="watchlist lifecycle",
            expected={
                "schema_version",
                "event_id",
                "membership_revision",
                "state",
                "source",
                "reason",
                "instrument_id",
                "owner_id",
                "correlation_id",
            },
        )
        return cls(**payload)  # type: ignore[arg-type]


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


def _normalize_required_text_values(values: object, label: str) -> tuple[str, ...]:
    normalized = _normalize_text_values(values, label)
    if not normalized:
        raise ValueError(f"{label} must not be empty")
    return normalized


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _validate_positive_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _validate_schema_version(value: object, expected: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value != expected:
        raise ValueError(f"unsupported {label} schema: {value}")


def _exact_object(value: object, *, label: str, expected: set[str]) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        missing = expected - actual
        unknown = actual - expected
        details: list[str] = []
        if missing:
            details.append(f"missing: {', '.join(sorted(missing))}")
        if unknown:
            details.append(f"unknown: {', '.join(sorted(unknown))}")
        raise ValueError(f"invalid {label} fields ({'; '.join(details)})")
    return value


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
