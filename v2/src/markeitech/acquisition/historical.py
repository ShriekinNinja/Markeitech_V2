from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType

from markeitech.acquisition.demand import (
    CapabilityDeclaration,
    CapabilityHistoricalRequirement,
    FeedKind,
    HistoricalWindow,
    RequirementParameter,
)

type HistoricalRequestKey = tuple[str, str, str, int, int, int, tuple[tuple[str, object], ...]]


@dataclass(frozen=True, slots=True)
class HistoricalWindowBounds:
    """Resolve one symbolic historical window to an inclusive nanosecond range."""

    window: HistoricalWindow
    start_ns: int
    end_ns: int

    def __post_init__(self) -> None:
        if not isinstance(self.window, HistoricalWindow):
            raise ValueError("window must be a HistoricalWindow")
        _non_negative_int(self.start_ns, "start_ns")
        _non_negative_int(self.end_ns, "end_ns")
        if self.end_ns <= self.start_ns:
            raise ValueError("end_ns must be after start_ns")


@dataclass(frozen=True, slots=True)
class HistoricalCapabilityBinding:
    """Bind a capability's historical evidence needs to one consumer and instrument."""

    consumer_id: str
    instrument_id: str
    capability: CapabilityDeclaration
    purpose: str
    priority: int = 50

    def __post_init__(self) -> None:
        object.__setattr__(self, "consumer_id", _required_text(self.consumer_id, "consumer_id"))
        object.__setattr__(
            self,
            "instrument_id",
            _required_text(self.instrument_id, "instrument_id"),
        )
        if not isinstance(self.capability, CapabilityDeclaration):
            raise ValueError("capability must be a CapabilityDeclaration")
        object.__setattr__(self, "purpose", _required_text(self.purpose, "purpose"))
        if (
            not isinstance(self.priority, int)
            or isinstance(self.priority, bool)
            or not 0 <= self.priority <= 100
        ):
            raise ValueError("priority must be an integer from 0 through 100")


@dataclass(frozen=True, slots=True)
class HistoricalDependencyRef:
    """Retain the consumer lineage attached to a shared historical request."""

    consumer_id: str
    capability_id: str
    capability_version: int
    requirement_index: int
    minimum_observations: int
    purpose: str


@dataclass(frozen=True, slots=True)
class HistoricalRequest:
    """Describe one bounded, provider-facing historical bar request.

    ``start_ns`` and ``end_ns`` are UTC Unix nanoseconds. Dependencies preserve
    every consumer whose readiness depends on the shared request.
    """

    request_id: str
    instrument_id: str
    kind: FeedKind
    selector: str
    window: HistoricalWindow
    start_ns: int
    end_ns: int
    limit: int
    priority: int
    parameters: Mapping[str, RequirementParameter]
    dependencies: tuple[HistoricalDependencyRef, ...]

    @property
    def request_key(self) -> HistoricalRequestKey:
        return (
            self.instrument_id,
            self.kind.value,
            self.selector,
            self.start_ns,
            self.end_ns,
            self.limit,
            tuple(self.parameters.items()),
        )


@dataclass(frozen=True, slots=True)
class HistoricalResourcePolicy:
    """Bound compiled request count and observation budgets."""

    maximum_requests: int
    maximum_observations_per_request: int
    maximum_total_observations: int

    def __post_init__(self) -> None:
        _positive_int(self.maximum_requests, "maximum_requests")
        _positive_int(
            self.maximum_observations_per_request,
            "maximum_observations_per_request",
        )
        _positive_int(self.maximum_total_observations, "maximum_total_observations")


class HistoricalPlanningError(ValueError):
    """Report an unresolved window or historical resource-policy violation."""


class HistoricalDependencyCompiler:
    """Compiles capability needs into deterministic, shared provider requests."""

    def __init__(self, policy: HistoricalResourcePolicy) -> None:
        self._policy = policy

    def compile(
        self,
        bindings: tuple[HistoricalCapabilityBinding, ...],
        bounds: Mapping[tuple[str, HistoricalWindow], HistoricalWindowBounds],
    ) -> tuple[HistoricalRequest, ...]:
        grouped: dict[
            HistoricalRequestKey,
            tuple[dict[str, object], list[HistoricalDependencyRef]],
        ] = {}
        for binding in sorted(
            bindings,
            key=lambda item: (
                item.instrument_id,
                item.capability.capability_id,
                item.capability.version,
                item.consumer_id,
            ),
        ):
            for index, requirement in enumerate(binding.capability.historical_requirements):
                item = self._candidate(binding, requirement, index, bounds)
                metadata, dependencies = grouped.setdefault(item[0], (item[1], []))
                dependencies.append(item[2])
                metadata["priority"] = max(int(metadata["priority"]), binding.priority)

        if len(grouped) > self._policy.maximum_requests:
            raise HistoricalPlanningError(
                "historical request count exceeds policy: "
                f"requests={len(grouped)}, maximum={self._policy.maximum_requests}",
            )
        total = sum(int(metadata["limit"]) for metadata, _ in grouped.values())
        if total > self._policy.maximum_total_observations:
            raise HistoricalPlanningError(
                "historical observation budget exceeds policy: "
                f"observations={total}, maximum={self._policy.maximum_total_observations}",
            )

        requests = []
        for key in sorted(grouped):
            metadata, dependencies = grouped[key]
            request_id = f"historical:{sha256(repr(key).encode()).hexdigest()[:20]}"
            requests.append(
                HistoricalRequest(
                    request_id=request_id,
                    instrument_id=str(metadata["instrument_id"]),
                    kind=FeedKind(str(metadata["kind"])),
                    selector=str(metadata["selector"]),
                    window=HistoricalWindow(str(metadata["window"])),
                    start_ns=int(metadata["start_ns"]),
                    end_ns=int(metadata["end_ns"]),
                    limit=int(metadata["limit"]),
                    priority=int(metadata["priority"]),
                    parameters=MappingProxyType(dict(metadata["parameters"])),  # type: ignore[arg-type]
                    dependencies=tuple(
                        sorted(
                            dependencies,
                            key=lambda item: (
                                item.consumer_id,
                                item.capability_id,
                                item.capability_version,
                                item.requirement_index,
                            ),
                        ),
                    ),
                ),
            )
        return tuple(sorted(requests, key=lambda item: (-item.priority, item.request_id)))

    def _candidate(
        self,
        binding: HistoricalCapabilityBinding,
        requirement: CapabilityHistoricalRequirement,
        index: int,
        bounds: Mapping[tuple[str, HistoricalWindow], HistoricalWindowBounds],
    ) -> tuple[HistoricalRequestKey, dict[str, object], HistoricalDependencyRef]:
        if requirement.maximum_observations > self._policy.maximum_observations_per_request:
            raise HistoricalPlanningError(
                "historical request exceeds per-request policy: "
                f"capability={binding.capability.capability_id}, "
                f"requested={requirement.maximum_observations}, "
                f"maximum={self._policy.maximum_observations_per_request}",
            )
        bound = bounds.get((binding.instrument_id, requirement.window))
        if bound is None:
            raise HistoricalPlanningError(
                "historical window is unresolved: "
                f"instrument={binding.instrument_id}, window={requirement.window.value}",
            )
        parameters = tuple(requirement.parameters.items())
        key: HistoricalRequestKey = (
            binding.instrument_id,
            requirement.kind.value,
            requirement.selector,
            bound.start_ns,
            bound.end_ns,
            requirement.maximum_observations,
            parameters,
        )
        metadata: dict[str, object] = {
            "instrument_id": binding.instrument_id,
            "kind": requirement.kind.value,
            "selector": requirement.selector,
            "window": requirement.window.value,
            "start_ns": bound.start_ns,
            "end_ns": bound.end_ns,
            "limit": requirement.maximum_observations,
            "priority": binding.priority,
            "parameters": parameters,
        }
        dependency = HistoricalDependencyRef(
            consumer_id=binding.consumer_id,
            capability_id=binding.capability.capability_id,
            capability_version=binding.capability.version,
            requirement_index=index,
            minimum_observations=requirement.minimum_observations,
            purpose=binding.purpose,
        )
        return key, metadata, dependency


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
