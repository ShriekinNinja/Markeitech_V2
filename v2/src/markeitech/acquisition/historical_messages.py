from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, fields
from math import isfinite
from types import MappingProxyType

from markeitech.acquisition.demand import HistoricalWindow, RequirementParameter

HISTORICAL_DEPENDENCY_DEMAND_SIGNAL = "markeitech.historical.dependency_demand"
HISTORICAL_EXECUTION_SIGNAL = "markeitech.historical.execution"
HISTORICAL_READINESS_SIGNAL = "markeitech.historical.readiness"
HISTORICAL_SCHEMA_VERSION = 1
HISTORICAL_BATCH_TYPE_NAME = "MarkeitechHistoricalBatch"

_EXECUTION_STATES = {
    "QUEUED",
    "SHARED",
    "SUBMITTED",
    "RETRY_SCHEDULED",
    "COMPLETED",
    "FAILED",
    "CANCELED",
    "EXPIRED",
}
_READINESS_STATES = {"READY", "DEGRADED", "FAILED", "CANCELED", "EXPIRED"}


@dataclass(frozen=True, slots=True)
class HistoricalDependencyDemandEvent:
    demand_id: str
    consumer_id: str
    capability_id: str
    capability_version: int
    instrument_id: str
    selector: str
    window: str
    minimum_observations: int
    maximum_observations: int
    priority: int
    purpose: str
    as_of_ns: int
    window_parameters: Mapping[str, RequirementParameter] | None = None
    parameters: Mapping[str, RequirementParameter] | None = None
    schema_version: int = HISTORICAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _schema(self.schema_version)
        for field in (
            "demand_id",
            "consumer_id",
            "capability_id",
            "instrument_id",
            "selector",
            "purpose",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        _positive(self.capability_version, "capability_version")
        _positive(self.minimum_observations, "minimum_observations")
        if self.maximum_observations < self.minimum_observations:
            raise ValueError("maximum_observations must not be below minimum_observations")
        _positive(self.maximum_observations, "maximum_observations")
        if not 0 <= self.priority <= 100:
            raise ValueError("priority must be from 0 through 100")
        _non_negative(self.as_of_ns, "as_of_ns")
        HistoricalWindow(self.window)
        object.__setattr__(
            self,
            "window_parameters",
            MappingProxyType(_parameters(self.window_parameters or {})),
        )
        object.__setattr__(
            self,
            "parameters",
            MappingProxyType(_parameters(self.parameters or {})),
        )

    def to_signal_value(self) -> str:
        payload = _as_payload(self)
        payload["window_parameters"] = dict(self.window_parameters or {})
        payload["parameters"] = dict(self.parameters or {})
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_signal_value(cls, value: str) -> HistoricalDependencyDemandEvent:
        return cls(**_payload(value, set(cls.__dataclass_fields__)))


@dataclass(frozen=True, slots=True)
class HistoricalExecutionEventMessage:
    event_id: str
    request_id: str
    state: str
    attempt: int
    instrument_id: str
    selector: str
    window: str
    start_ns: int
    end_ns: int
    limit: int
    consumer_ids: tuple[str, ...]
    occurred_at_ns: int
    source: str
    detail: str
    schema_version: int = HISTORICAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _schema(self.schema_version)
        for field in (
            "event_id",
            "request_id",
            "instrument_id",
            "selector",
            "source",
            "detail",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        if self.state not in _EXECUTION_STATES:
            raise ValueError(f"unsupported historical execution state: {self.state!r}")
        HistoricalWindow(self.window)
        _positive(self.attempt, "attempt")
        _positive(self.limit, "limit")
        _non_negative(self.start_ns, "start_ns")
        _non_negative(self.end_ns, "end_ns")
        if self.end_ns <= self.start_ns:
            raise ValueError("end_ns must be after start_ns")
        _non_negative(self.occurred_at_ns, "occurred_at_ns")
        object.__setattr__(self, "consumer_ids", _texts(self.consumer_ids, "consumer_ids"))

    def to_signal_value(self) -> str:
        return json.dumps(_as_payload(self), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_signal_value(cls, value: str) -> HistoricalExecutionEventMessage:
        return cls(**_payload(value, set(cls.__dataclass_fields__)))


@dataclass(frozen=True, slots=True)
class HistoricalReadinessEvent:
    event_id: str
    request_id: str
    consumer_id: str
    capability_id: str
    capability_version: int
    state: str
    instrument_id: str
    selector: str
    window: str
    minimum_observations: int
    observed_count: int
    completed_at_ns: int
    source: str
    reason: str
    schema_version: int = HISTORICAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _schema(self.schema_version)
        for field in (
            "event_id",
            "request_id",
            "consumer_id",
            "capability_id",
            "instrument_id",
            "selector",
            "source",
            "reason",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        if self.state not in _READINESS_STATES:
            raise ValueError(f"unsupported historical readiness state: {self.state!r}")
        HistoricalWindow(self.window)
        _positive(self.capability_version, "capability_version")
        _positive(self.minimum_observations, "minimum_observations")
        _non_negative(self.observed_count, "observed_count")
        _non_negative(self.completed_at_ns, "completed_at_ns")

    def to_signal_value(self) -> str:
        return json.dumps(_as_payload(self), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_signal_value(cls, value: str) -> HistoricalReadinessEvent:
        return cls(**_payload(value, set(cls.__dataclass_fields__)))


def _payload(value: str, expected: set[str]) -> dict[str, object]:
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("historical signal value must be valid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != expected:
        raise ValueError("historical signal payload fields do not match the contract")
    return payload


def _as_payload(value: object) -> dict[str, object]:
    return {field.name: getattr(value, field.name) for field in fields(value)}


def _parameters(
    parameters: Mapping[str, RequirementParameter],
) -> dict[str, RequirementParameter]:
    if not isinstance(parameters, Mapping):
        raise ValueError("parameters must be a mapping")
    result: dict[str, RequirementParameter] = {}
    for key, value in parameters.items():
        normalized = _text(key, "parameter key")
        if not isinstance(value, str | int | float | bool):
            raise ValueError(f"unsupported parameter value for {normalized!r}")
        if isinstance(value, float) and not isfinite(value):
            raise ValueError(f"non-finite parameter value for {normalized!r}")
        result[normalized] = value
    return dict(sorted(result.items()))


def _texts(values: object, label: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError(f"{label} must contain at least one value")
    return tuple(sorted({_text(value, label) for value in values}))


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _schema(value: object) -> None:
    if value != HISTORICAL_SCHEMA_VERSION:
        raise ValueError(f"unsupported historical schema: {value!r}")


def _positive(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _non_negative(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
