from __future__ import annotations

import json
from dataclasses import dataclass
from math import isfinite
from typing import Any

RUNTIME_RESOURCE_SIGNAL = "markeitech.runtime.resource"
RUNTIME_RESOURCE_HEALTH_SIGNAL = "markeitech.runtime.health"
RUNTIME_RESOURCE_SCHEMA_VERSION = 2
RUNTIME_RESOURCE_HEALTH_SCHEMA_VERSION = 1
RUNTIME_RESOURCE_HEALTH_STATES = frozenset({"NORMAL", "WARNING", "CRITICAL"})


@dataclass(frozen=True, slots=True)
class RuntimeResourceEvent:
    event_id: str
    source: str
    observed_ts_ns: int
    sample_sequence: int
    sample_interval_ms: int
    rss_bytes: int
    peak_rss_bytes: int
    vms_bytes: int
    cpu_user_seconds: float
    cpu_system_seconds: float
    cpu_percent: float
    thread_count: int
    open_fd_count: int | None
    open_fd_soft_limit: int | None
    host_cpu_percent: float
    host_memory_total_bytes: int
    host_memory_available_bytes: int
    host_memory_available_percent: float
    host_swap_used_bytes: int
    host_swap_percent: float
    disk_path: str
    disk_total_bytes: int
    disk_free_bytes: int
    disk_free_percent: float
    cache_observed: bool
    cache_error: str | None
    cache_instrument_count: int | None
    cache_quote_tick_count: int | None
    cache_trade_tick_count: int | None
    cache_bar_type_count: int | None
    cache_bar_count: int | None
    schema_version: int = RUNTIME_RESOURCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != RUNTIME_RESOURCE_SCHEMA_VERSION:
            raise ValueError(f"unsupported runtime resource schema: {self.schema_version}")
        for field_name in ("event_id", "source", "disk_path"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())
        for field_name in (
            "observed_ts_ns",
            "sample_sequence",
            "sample_interval_ms",
            "rss_bytes",
            "peak_rss_bytes",
            "vms_bytes",
            "thread_count",
            "host_memory_total_bytes",
            "host_memory_available_bytes",
            "host_swap_used_bytes",
            "disk_total_bytes",
            "disk_free_bytes",
        ):
            _require_non_negative_int(getattr(self, field_name), field_name)
        if self.sample_sequence == 0 or self.sample_interval_ms == 0:
            raise ValueError("sample_sequence and sample_interval_ms must be positive")
        for field_name in (
            "cpu_user_seconds",
            "cpu_system_seconds",
            "cpu_percent",
            "host_cpu_percent",
            "host_memory_available_percent",
            "host_swap_percent",
            "disk_free_percent",
        ):
            _require_non_negative_float(getattr(self, field_name), field_name)
        for field_name in (
            "host_memory_available_percent",
            "host_swap_percent",
            "disk_free_percent",
        ):
            if getattr(self, field_name) > 100:
                raise ValueError(f"{field_name} must not exceed 100")
        for field_name in (
            "open_fd_count",
            "open_fd_soft_limit",
            "cache_instrument_count",
            "cache_quote_tick_count",
            "cache_trade_tick_count",
            "cache_bar_type_count",
            "cache_bar_count",
        ):
            value = getattr(self, field_name)
            if value is not None:
                _require_non_negative_int(value, field_name)
        if self.open_fd_soft_limit == 0:
            raise ValueError("open_fd_soft_limit must be positive when available")
        if self.host_memory_available_bytes > self.host_memory_total_bytes:
            raise ValueError("host memory available cannot exceed total")
        if self.disk_free_bytes > self.disk_total_bytes:
            raise ValueError("disk free cannot exceed total")
        if not isinstance(self.cache_observed, bool):
            raise ValueError("cache_observed must be a boolean")
        if self.cache_error is not None:
            if not isinstance(self.cache_error, str) or not self.cache_error.strip():
                raise ValueError("cache_error must be null or a non-empty string")
            object.__setattr__(self, "cache_error", self.cache_error.strip())
        cache_counts = (
            self.cache_instrument_count,
            self.cache_quote_tick_count,
            self.cache_trade_tick_count,
            self.cache_bar_type_count,
            self.cache_bar_count,
        )
        if self.cache_observed and (self.cache_error is not None or None in cache_counts):
            raise ValueError("observed cache evidence requires all counts and no error")
        if not self.cache_observed and any(value is not None for value in cache_counts):
            raise ValueError("unobserved cache evidence cannot contain counts")

    def to_signal_value(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    def to_dict(self) -> dict[str, object]:
        return {field_name: getattr(self, field_name) for field_name in self.__dataclass_fields__}

    @classmethod
    def from_signal_value(cls, value: str) -> RuntimeResourceEvent:
        return cls(**_contract_payload(value, set(cls.__dataclass_fields__), "runtime resource"))


@dataclass(frozen=True, slots=True)
class RuntimeResourceHealthEvent:
    event_id: str
    source: str
    observed_ts_ns: int
    state: str
    previous_state: str
    reason_codes: tuple[str, ...]
    observations: dict[str, int | float | str | None]
    thresholds: dict[str, int | float]
    notification_eligible: bool
    threshold_version: str
    schema_version: int = RUNTIME_RESOURCE_HEALTH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != RUNTIME_RESOURCE_HEALTH_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported runtime resource health schema: {self.schema_version}",
            )
        for field_name in ("event_id", "source", "threshold_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
            object.__setattr__(self, field_name, value.strip())
        _require_non_negative_int(self.observed_ts_ns, "observed_ts_ns")
        if self.state not in RUNTIME_RESOURCE_HEALTH_STATES:
            raise ValueError(f"unsupported runtime resource health state: {self.state}")
        if self.previous_state not in RUNTIME_RESOURCE_HEALTH_STATES:
            raise ValueError(
                f"unsupported previous runtime resource health state: {self.previous_state}",
            )
        if not self.reason_codes or any(
            not isinstance(reason, str) or not reason.strip() for reason in self.reason_codes
        ):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(
            self,
            "reason_codes",
            tuple(reason.strip() for reason in self.reason_codes),
        )
        _validate_scalar_mapping(self.observations, "observations", allow_none=True)
        _validate_scalar_mapping(self.thresholds, "thresholds", allow_none=False)
        if not isinstance(self.notification_eligible, bool):
            raise ValueError("notification_eligible must be a boolean")

    def to_signal_value(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "source": self.source,
            "observed_ts_ns": self.observed_ts_ns,
            "state": self.state,
            "previous_state": self.previous_state,
            "reason_codes": list(self.reason_codes),
            "observations": self.observations,
            "thresholds": self.thresholds,
            "notification_eligible": self.notification_eligible,
            "threshold_version": self.threshold_version,
        }

    @classmethod
    def from_signal_value(cls, value: str) -> RuntimeResourceHealthEvent:
        payload = _contract_payload(
            value,
            set(cls.__dataclass_fields__),
            "runtime resource health",
        )
        payload["reason_codes"] = tuple(payload["reason_codes"])
        return cls(**payload)


def _contract_payload(value: str, expected: set[str], label: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} signal must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} signal must contain a JSON object")
    if set(payload) != expected:
        raise ValueError(f"{label} signal fields do not match the contract")
    return payload


def _validate_scalar_mapping(
    values: object,
    label: str,
    *,
    allow_none: bool,
) -> None:
    if not isinstance(values, dict) or not values:
        raise ValueError(f"{label} must be a non-empty mapping")
    for key, value in values.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{label} keys must be non-empty strings")
        if value is None and allow_none:
            continue
        if not isinstance(value, int | float | str) or isinstance(value, bool):
            raise ValueError(f"{label} values must be scalar")
        if isinstance(value, float) and not isfinite(value):
            raise ValueError(f"{label} values must be finite")


def _require_non_negative_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _require_non_negative_float(value: object, label: str) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{label} must be a finite non-negative number")
    if not isfinite(value) or value < 0:
        raise ValueError(f"{label} must be a finite non-negative number")
