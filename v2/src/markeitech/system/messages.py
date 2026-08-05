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

type EvidenceValue = str | int | float | bool | None


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
