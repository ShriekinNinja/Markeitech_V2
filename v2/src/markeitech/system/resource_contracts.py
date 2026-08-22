from __future__ import annotations

import json
from dataclasses import dataclass
from math import isfinite

RUNTIME_RESOURCE_SIGNAL = "markeitech.runtime.resource"
RUNTIME_RESOURCE_SCHEMA_VERSION = 1


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
        for field_name in ("event_id", "source"):
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
        ):
            _require_non_negative_int(getattr(self, field_name), field_name)
        if self.sample_sequence == 0 or self.sample_interval_ms == 0:
            raise ValueError("sample_sequence and sample_interval_ms must be positive")
        for field_name in ("cpu_user_seconds", "cpu_system_seconds", "cpu_percent"):
            _require_non_negative_float(getattr(self, field_name), field_name)
        for field_name in (
            "open_fd_count",
            "cache_instrument_count",
            "cache_quote_tick_count",
            "cache_trade_tick_count",
            "cache_bar_type_count",
            "cache_bar_count",
        ):
            value = getattr(self, field_name)
            if value is not None:
                _require_non_negative_int(value, field_name)
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
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "source": self.source,
            "observed_ts_ns": self.observed_ts_ns,
            "sample_sequence": self.sample_sequence,
            "sample_interval_ms": self.sample_interval_ms,
            "rss_bytes": self.rss_bytes,
            "peak_rss_bytes": self.peak_rss_bytes,
            "vms_bytes": self.vms_bytes,
            "cpu_user_seconds": self.cpu_user_seconds,
            "cpu_system_seconds": self.cpu_system_seconds,
            "cpu_percent": self.cpu_percent,
            "thread_count": self.thread_count,
            "open_fd_count": self.open_fd_count,
            "cache_observed": self.cache_observed,
            "cache_error": self.cache_error,
            "cache_instrument_count": self.cache_instrument_count,
            "cache_quote_tick_count": self.cache_quote_tick_count,
            "cache_trade_tick_count": self.cache_trade_tick_count,
            "cache_bar_type_count": self.cache_bar_type_count,
            "cache_bar_count": self.cache_bar_count,
        }

    @classmethod
    def from_signal_value(cls, value: str) -> RuntimeResourceEvent:
        try:
            payload = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("runtime resource signal must contain valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("runtime resource signal must contain a JSON object")
        expected = set(cls.__dataclass_fields__)
        if set(payload) != expected:
            raise ValueError("runtime resource signal fields do not match the contract")
        return cls(**payload)


def _require_non_negative_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _require_non_negative_float(value: object, label: str) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{label} must be a finite non-negative number")
    if not isfinite(value) or value < 0:
        raise ValueError(f"{label} must be a finite non-negative number")
