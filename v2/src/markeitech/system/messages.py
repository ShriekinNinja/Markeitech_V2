from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType

SYSTEM_HEALTH_SIGNAL = "markeitech.system.health"
SYSTEM_HEALTH_SCHEMA_VERSION = 1

type EvidenceValue = str | int | float | bool | None


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
        if not isinstance(self.evidence, Mapping):
            raise ValueError("evidence must be a mapping")
        for key, value in self.evidence.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("evidence keys must be non-empty strings")
            if value is not None and not isinstance(value, str | int | float | bool):
                raise ValueError(f"unsupported evidence value for {key!r}")
            if isinstance(value, float) and not isfinite(value):
                raise ValueError(f"non-finite evidence value for {key!r}")

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
        try:
            payload = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("system health signal must contain valid JSON text") from exc
        if not isinstance(payload, dict):
            raise ValueError("system health signal must contain a JSON object")

        expected = {"schema_version", "state", "reason", "source", "evidence"}
        actual = set(payload)
        if actual != expected:
            missing = expected - actual
            unknown = actual - expected
            details: list[str] = []
            if missing:
                details.append(f"missing: {', '.join(sorted(missing))}")
            if unknown:
                details.append(f"unknown: {', '.join(sorted(unknown))}")
            raise ValueError(f"invalid system health fields ({'; '.join(details)})")

        return cls(
            schema_version=payload["schema_version"],
            state=payload["state"],
            reason=payload["reason"],
            source=payload["source"],
            evidence=payload["evidence"],
        )
