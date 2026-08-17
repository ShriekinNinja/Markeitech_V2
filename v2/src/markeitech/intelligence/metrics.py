from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from math import isfinite
from types import MappingProxyType

from markeitech.acquisition import (
    CapabilityDeclaration,
    CapabilityFeedRequirement,
    CapabilityHistoricalRequirement,
)

type MetricParameterValue = str | int | float | Decimal | bool
type MetricScalarValue = str | int | float | Decimal | bool
type MetricKey = tuple[str, int]


class MetricValueKind(StrEnum):
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    TEXT = "text"


class MetricCadence(StrEnum):
    OBSERVATION = "observation"
    COMPLETED_BAR = "completed_bar"
    TIMER = "timer"
    SESSION_TRANSITION = "session_transition"
    DEPENDENCY_READY = "dependency_ready"


class MetricRetainedState(StrEnum):
    NONE = "none"
    LATEST = "latest"
    ROLLING_WINDOW = "rolling_window"
    SESSION = "session"


class MetricFailureBehavior(StrEnum):
    EMIT_NULL = "emit_null"
    HOLD_LAST_STALE = "hold_last_stale"
    SUPPRESS_OUTPUT = "suppress_output"


class MetricHealth(StrEnum):
    READY = "READY"
    WARMING = "WARMING"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"


class MetricFidelity(StrEnum):
    REPORTED = "REPORTED"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


class ParameterMutability(StrEnum):
    STARTUP_ONLY = "startup_only"
    POLICY_CONTROLLED_RUNTIME = "policy_controlled_runtime"


@dataclass(frozen=True, slots=True)
class MetricParameterDefinition:
    parameter_id: str
    meaning: str
    value_kind: MetricValueKind
    unit: str
    default: MetricParameterValue
    scope: str
    dynamic: bool
    mutability: ParameterMutability
    source: str
    minimum: int | float | None = None
    maximum: int | float | None = None
    step: int | float | None = None
    allowed_values: tuple[MetricParameterValue, ...] = ()

    def __post_init__(self) -> None:
        for field in ("parameter_id", "meaning", "unit", "scope", "source"):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        if not isinstance(self.value_kind, MetricValueKind):
            raise ValueError("value_kind must be a MetricValueKind")
        if not isinstance(self.mutability, ParameterMutability):
            raise ValueError("mutability must be a ParameterMutability")
        if not isinstance(self.dynamic, bool):
            raise ValueError("dynamic must be a boolean")
        if self.dynamic and self.mutability is not ParameterMutability.POLICY_CONTROLLED_RUNTIME:
            raise ValueError("dynamic parameters require policy-controlled runtime mutability")
        if not self.dynamic and self.mutability is not ParameterMutability.STARTUP_ONLY:
            raise ValueError("static parameters must be startup-only")
        if not isinstance(self.allowed_values, tuple):
            raise ValueError("allowed_values must be a tuple")
        _validate_parameter_envelope(self)
        self.validate(self.default)

    def validate(self, value: MetricParameterValue) -> None:
        _validate_value_kind(value, self.value_kind, self.parameter_id)
        if self.allowed_values and value not in self.allowed_values:
            raise ValueError(f"{self.parameter_id} is outside its allowed values")
        if _is_number(value):
            if self.minimum is not None and value < self.minimum:
                raise ValueError(f"{self.parameter_id} is below its minimum")
            if self.maximum is not None and value > self.maximum:
                raise ValueError(f"{self.parameter_id} is above its maximum")


@dataclass(frozen=True, slots=True)
class MetricParameterSet:
    metric_id: str
    metric_version: int
    parameter_version: int
    effective_from_ns: int
    source: str
    values: Mapping[str, MetricParameterValue]
    supersedes_parameter_version: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric_id", _required_text(self.metric_id, "metric_id"))
        object.__setattr__(self, "source", _required_text(self.source, "source"))
        _positive_int(self.metric_version, "metric_version")
        _positive_int(self.parameter_version, "parameter_version")
        _timestamp(self.effective_from_ns, "effective_from_ns")
        if self.supersedes_parameter_version is not None:
            _positive_int(self.supersedes_parameter_version, "supersedes_parameter_version")
            if self.supersedes_parameter_version >= self.parameter_version:
                raise ValueError("superseded parameter version must be older")
        object.__setattr__(self, "values", MappingProxyType(_parameter_values(self.values)))


@dataclass(frozen=True, slots=True)
class MetricDependency:
    metric_id: str
    version: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric_id", _required_text(self.metric_id, "metric_id"))
        _positive_int(self.version, "version")

    @property
    def key(self) -> MetricKey:
        return (self.metric_id, self.version)


@dataclass(frozen=True, slots=True)
class MetricWarmupPolicy:
    minimum_observations: int
    minimum_elapsed_ns: int
    require_all_dependencies: bool

    def __post_init__(self) -> None:
        _non_negative_int(self.minimum_observations, "minimum_observations")
        _timestamp(self.minimum_elapsed_ns, "minimum_elapsed_ns")
        if not isinstance(self.require_all_dependencies, bool):
            raise ValueError("require_all_dependencies must be a boolean")


@dataclass(frozen=True, slots=True)
class MetricResourcePolicy:
    maximum_retained_observations: int
    minimum_update_interval_ms: int
    maximum_output_age_ms: int

    def __post_init__(self) -> None:
        _non_negative_int(self.maximum_retained_observations, "maximum_retained_observations")
        _non_negative_int(self.minimum_update_interval_ms, "minimum_update_interval_ms")
        _positive_int(self.maximum_output_age_ms, "maximum_output_age_ms")


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric_id: str
    version: int
    decision_question: str
    implementation_id: str
    value_kind: MetricValueKind
    unit: str
    cadence: MetricCadence
    horizon: str
    nullable: bool
    retained_state: MetricRetainedState
    fidelity: MetricFidelity
    failure_behavior: MetricFailureBehavior
    warmup: MetricWarmupPolicy
    resources: MetricResourcePolicy
    live_inputs: tuple[CapabilityFeedRequirement, ...] = ()
    historical_inputs: tuple[CapabilityHistoricalRequirement, ...] = ()
    metric_inputs: tuple[MetricDependency, ...] = ()
    parameters: tuple[MetricParameterDefinition, ...] = ()
    event_uses: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field in ("metric_id", "decision_question", "implementation_id", "unit", "horizon"):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        _positive_int(self.version, "version")
        if not isinstance(self.value_kind, MetricValueKind):
            raise ValueError("value_kind must be a MetricValueKind")
        if not isinstance(self.cadence, MetricCadence):
            raise ValueError("cadence must be a MetricCadence")
        if not isinstance(self.retained_state, MetricRetainedState):
            raise ValueError("retained_state must be a MetricRetainedState")
        if not isinstance(self.fidelity, MetricFidelity):
            raise ValueError("fidelity must be a MetricFidelity")
        if not isinstance(self.failure_behavior, MetricFailureBehavior):
            raise ValueError("failure_behavior must be a MetricFailureBehavior")
        if not isinstance(self.nullable, bool):
            raise ValueError("nullable must be a boolean")
        if self.failure_behavior is MetricFailureBehavior.EMIT_NULL and not self.nullable:
            raise ValueError("emit-null failure behavior requires a nullable metric")
        if not isinstance(self.warmup, MetricWarmupPolicy):
            raise ValueError("warmup must be a MetricWarmupPolicy")
        if not isinstance(self.resources, MetricResourcePolicy):
            raise ValueError("resources must be a MetricResourcePolicy")
        _typed_tuple(self.live_inputs, CapabilityFeedRequirement, "live_inputs")
        _typed_tuple(self.historical_inputs, CapabilityHistoricalRequirement, "historical_inputs")
        _typed_tuple(self.metric_inputs, MetricDependency, "metric_inputs")
        _typed_tuple(self.parameters, MetricParameterDefinition, "parameters")
        _unique((item.requirement_key for item in self.live_inputs), "live input")
        _unique((item.key for item in self.metric_inputs), "metric input")
        _unique((item.parameter_id for item in self.parameters), "parameter")
        if not self.live_inputs and not self.historical_inputs and not self.metric_inputs:
            raise ValueError("a metric must declare at least one input")
        if self.key in {item.key for item in self.metric_inputs}:
            raise ValueError("a metric cannot depend on itself")
        if self.retained_state is MetricRetainedState.NONE:
            if self.resources.maximum_retained_observations != 0:
                raise ValueError("stateless metrics cannot retain observations")
        elif self.resources.maximum_retained_observations == 0:
            raise ValueError("stateful metrics require a positive retention bound")
        if not isinstance(self.event_uses, tuple):
            raise ValueError("event_uses must be a tuple")
        normalized_uses = tuple(_required_text(item, "event use") for item in self.event_uses)
        if len(normalized_uses) != len(set(normalized_uses)):
            raise ValueError("event uses must be unique")
        object.__setattr__(self, "event_uses", normalized_uses)

    @property
    def key(self) -> MetricKey:
        return (self.metric_id, self.version)

    def acquisition_capability(self) -> CapabilityDeclaration | None:
        if not self.live_inputs and not self.historical_inputs:
            return None
        return CapabilityDeclaration(
            capability_id=f"metric:{self.metric_id}",
            version=self.version,
            live_feeds=self.live_inputs,
            historical_requirements=self.historical_inputs,
        )


@dataclass(frozen=True, slots=True)
class MetricValue:
    metric_id: str
    metric_version: int
    parameter_version: int
    instrument_id: str
    session_id: str | None
    value: MetricScalarValue | None
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
    def key(self) -> MetricKey:
        return (self.metric_id, self.metric_version)


class MetricRegistry:
    def __init__(self, definitions: tuple[MetricDefinition, ...]) -> None:
        _typed_tuple(definitions, MetricDefinition, "definitions")
        by_key: dict[MetricKey, MetricDefinition] = {}
        for definition in definitions:
            if definition.key in by_key:
                raise ValueError(f"duplicate metric definition: {definition.key!r}")
            by_key[definition.key] = definition
        for definition in definitions:
            missing = tuple(item.key for item in definition.metric_inputs if item.key not in by_key)
            if missing:
                raise ValueError(f"metric dependencies are not registered: {missing!r}")
        self._definitions = MappingProxyType(dict(sorted(by_key.items())))

    @property
    def definitions(self) -> tuple[MetricDefinition, ...]:
        return tuple(self._definitions.values())

    def get(self, metric_id: str, version: int) -> MetricDefinition:
        key = (_required_text(metric_id, "metric_id"), version)
        _positive_int(version, "version")
        try:
            return self._definitions[key]
        except KeyError as exc:
            raise KeyError(f"metric definition is not registered: {key!r}") from exc

    def latest(self, metric_id: str) -> MetricDefinition:
        normalized = _required_text(metric_id, "metric_id")
        matches = [item for key, item in self._definitions.items() if key[0] == normalized]
        if not matches:
            raise KeyError(f"metric definition is not registered: {normalized!r}")
        return max(matches, key=lambda item: item.version)

    def validate_parameters(self, parameters: MetricParameterSet) -> None:
        if not isinstance(parameters, MetricParameterSet):
            raise ValueError("parameters must be a MetricParameterSet")
        definition = self.get(parameters.metric_id, parameters.metric_version)
        declared = {item.parameter_id: item for item in definition.parameters}
        if set(parameters.values) != set(declared):
            raise ValueError("parameter set must provide every declared parameter exactly once")
        for parameter_id, value in parameters.values.items():
            declared[parameter_id].validate(value)

    def validate_value(self, value: MetricValue) -> None:
        if not isinstance(value, MetricValue):
            raise ValueError("value must be a MetricValue")
        definition = self.get(value.metric_id, value.metric_version)
        if value.unit != definition.unit:
            raise ValueError("metric value unit does not match its definition")
        if value.fidelity is not definition.fidelity and value.fidelity not in {
            MetricFidelity.PARTIAL,
            MetricFidelity.UNAVAILABLE,
        }:
            raise ValueError("metric value fidelity is incompatible with its definition")
        if value.value is None:
            if not definition.nullable:
                raise ValueError("metric definition does not permit null values")
            return
        _validate_value_kind(value.value, definition.value_kind, definition.metric_id)


def _validate_parameter_envelope(definition: MetricParameterDefinition) -> None:
    numeric = definition.value_kind in {MetricValueKind.NUMBER, MetricValueKind.INTEGER}
    if numeric:
        if definition.minimum is None or definition.maximum is None:
            raise ValueError("numeric parameters require minimum and maximum bounds")
        if not _is_number(definition.minimum) or not _is_number(definition.maximum):
            raise ValueError("numeric parameter bounds must be finite numbers")
        if definition.minimum > definition.maximum:
            raise ValueError("parameter minimum cannot exceed maximum")
        if definition.dynamic:
            if not _is_number(definition.step) or definition.step <= 0:
                raise ValueError("dynamic numeric parameters require a positive step")
        elif definition.step is not None and (
            not _is_number(definition.step) or definition.step <= 0
        ):
            raise ValueError("parameter step must be a positive number")
        if definition.allowed_values:
            raise ValueError("numeric parameters use bounds instead of allowed_values")
        return
    numeric_envelope = (definition.minimum, definition.maximum, definition.step)
    if any(value is not None for value in numeric_envelope):
        raise ValueError("non-numeric parameters cannot declare numeric bounds")
    if not definition.allowed_values:
        raise ValueError("non-numeric parameters require allowed_values")
    for value in definition.allowed_values:
        _validate_value_kind(value, definition.value_kind, definition.parameter_id)


def _validate_value_kind(value: MetricParameterValue, kind: MetricValueKind, label: str) -> None:
    valid = {
        MetricValueKind.NUMBER: _is_number(value),
        MetricValueKind.INTEGER: isinstance(value, int) and not isinstance(value, bool),
        MetricValueKind.BOOLEAN: isinstance(value, bool),
        MetricValueKind.TEXT: isinstance(value, str) and bool(value.strip()),
    }[kind]
    if not valid:
        raise ValueError(f"{label} must be a {kind.value} value")


def _parameter_values(
    values: Mapping[str, MetricParameterValue],
) -> dict[str, MetricParameterValue]:
    if not isinstance(values, Mapping):
        raise ValueError("values must be a mapping")
    result: dict[str, MetricParameterValue] = {}
    for key, value in values.items():
        normalized = _required_text(key, "parameter key")
        if not isinstance(value, str | int | float | Decimal | bool):
            raise ValueError(f"unsupported parameter value for {normalized!r}")
        if isinstance(value, float) and not isfinite(value):
            raise ValueError(f"non-finite parameter value for {normalized!r}")
        if isinstance(value, Decimal) and not value.is_finite():
            raise ValueError(f"non-finite parameter value for {normalized!r}")
        result[normalized] = value
    return dict(sorted(result.items()))


def _is_number(value: object) -> bool:
    return (
        isinstance(value, int | float | Decimal)
        and not isinstance(value, bool)
        and (not isinstance(value, float) or isfinite(value))
        and (not isinstance(value, Decimal) or value.is_finite())
    )


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _non_negative_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _timestamp(value: object, label: str) -> None:
    _non_negative_int(value, label)


def _typed_tuple(value: object, kind: type[object], label: str) -> None:
    if not isinstance(value, tuple) or any(not isinstance(item, kind) for item in value):
        raise ValueError(f"{label} must be a tuple of {kind.__name__} values")


def _unique(values: object, label: str) -> None:
    materialized = tuple(values)  # type: ignore[arg-type]
    if len(materialized) != len(set(materialized)):
        raise ValueError(f"duplicate {label} declaration")


def _text_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ValueError(f"{label}s must be a tuple")
    normalized = tuple(_required_text(item, label) for item in value)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label}s must be unique")
    return normalized
