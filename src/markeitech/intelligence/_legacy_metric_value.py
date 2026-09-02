from __future__ import annotations

from dataclasses import dataclass

from markeitech.intelligence.metric_messages import MetricFidelity, MetricHealth

LEGACY_METRIC_VALUE_TYPE_NAME = "markeitech.metric.value"
"""Temporary private v1 wire identity retained until the atomic v2 cutover."""

type LegacyMetricScalarValue = str | int | float | object | bool


@dataclass(frozen=True, slots=True)
class LegacyMetricValue:
    """Temporary private representation of the active v1 metric-value wire.

    This compatibility contract intentionally preserves the existing runtime
    payload and validation behavior. It must not be exported from the public
    intelligence package or used for the future v2 canonical wire.
    """

    metric_id: str
    metric_version: int
    parameter_version: int
    instrument_id: str
    session_id: str | None
    value: object | None
    unit: str
    effective_ts_ns: int
    observed_ts_ns: int
    received_ts_ns: int
    calculated_ts_ns: int
    published_ts_ns: int
    health: MetricHealth
    fidelity: MetricFidelity
    source: str
    evidence_refs: tuple[str, ...]
    missing_reasons: tuple[str, ...]
    revision: int

    def __post_init__(self) -> None:
        for field in ("metric_id", "instrument_id", "unit", "source"):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        if self.session_id is not None:
            object.__setattr__(self, "session_id", _required_text(self.session_id, "session_id"))
        _positive_int(self.metric_version, "metric_version")
        _positive_int(self.parameter_version, "parameter_version")
        _positive_int(self.revision, "revision")
        for field in (
            "effective_ts_ns",
            "observed_ts_ns",
            "received_ts_ns",
            "calculated_ts_ns",
            "published_ts_ns",
        ):
            _timestamp(getattr(self, field), field)
        if not (
            self.observed_ts_ns
            <= self.received_ts_ns
            <= self.calculated_ts_ns
            <= self.published_ts_ns
        ):
            raise ValueError(
                "metric timestamps must satisfy observed <= received <= calculated <= published",
            )
        if not isinstance(self.health, MetricHealth):
            raise ValueError("health must be a MetricHealth")
        if not isinstance(self.fidelity, MetricFidelity):
            raise ValueError("fidelity must be a MetricFidelity")
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence ref"))
        object.__setattr__(
            self,
            "missing_reasons",
            _text_tuple(self.missing_reasons, "missing reason"),
        )
        if self.value is None and not self.missing_reasons:
            raise ValueError("a null metric value requires a missing reason")
        if self.value is not None and self.health in {
            MetricHealth.UNAVAILABLE,
            MetricHealth.UNSUPPORTED,
            MetricHealth.FAILED,
        }:
            raise ValueError("unavailable, unsupported, or failed metrics cannot carry a value")

    @property
    def key(self) -> tuple[str, int]:
        return (self.metric_id, self.metric_version)

    @property
    def ts_event(self) -> int:
        return self.effective_ts_ns

    @property
    def ts_init(self) -> int:
        return self.published_ts_ns


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _timestamp(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _text_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ValueError(f"{label}s must be a tuple")
    normalized = tuple(_required_text(item, label) for item in value)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label}s must be unique")
    return normalized
