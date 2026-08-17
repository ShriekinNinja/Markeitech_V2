from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite
from types import MappingProxyType

type RequirementParameter = str | int | float | bool
type StreamKey = tuple[str, str, str]


class FeedKind(StrEnum):
    INSTRUMENT = "instrument"
    TRADES = "trades"
    QUOTES = "quotes"
    BARS = "bars"
    BOOK = "book"
    INSTRUMENT_STATUS = "instrument_status"
    OPTION_GREEKS = "option_greeks"
    OPTION_CHAIN = "option_chain"


class HistoricalWindow(StrEnum):
    PREVIOUS_RTH = "previous_rth"
    PREVIOUS_GTH_OVERNIGHT = "previous_gth_overnight"
    CURRENT_OVERNIGHT = "current_overnight"
    CURRENT_RTH = "current_rth"
    CURRENT_GTH = "current_gth"
    CURB = "curb"
    PREMARKET = "premarket"
    POWER_HOUR = "power_hour"
    OVERNIGHT = "overnight"
    SESSION_TO_DATE = "session_to_date"
    OPENING_RANGE = "opening_range"
    NAMED_PHASE_SLICE = "named_phase_slice"
    PREVIOUS_SESSIONS = "previous_sessions"
    RECENT_COMPLETED = "recent_completed"
    ANCHORED_INTERVAL = "anchored_interval"
    SYNCHRONIZED_INTERVAL = "synchronized_interval"


class DemandOwnerKind(StrEnum):
    BOOTSTRAP = "bootstrap"
    WATCHLIST = "watchlist"
    OPERATOR = "operator"
    ANALYZER = "analyzer"
    AGENT = "agent"


class AcquisitionLifecycleState(StrEnum):
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    SUBSCRIBED = "SUBSCRIBED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class DemandOwner:
    kind: DemandOwnerKind
    owner_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, DemandOwnerKind):
            raise ValueError("kind must be a DemandOwnerKind")
        object.__setattr__(self, "owner_id", _required_text(self.owner_id, "owner_id"))


@dataclass(frozen=True, slots=True)
class FeedRequirement:
    instrument_id: str
    kind: FeedKind
    selector: str = "default"
    parameters: Mapping[str, RequirementParameter] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "instrument_id",
            _required_text(self.instrument_id, "instrument_id"),
        )
        if not isinstance(self.kind, FeedKind):
            raise ValueError("kind must be a FeedKind")
        object.__setattr__(self, "selector", _required_text(self.selector, "selector"))
        parameters = _validated_parameters(self.parameters or {})
        object.__setattr__(self, "parameters", MappingProxyType(parameters))

    @property
    def stream_key(self) -> StreamKey:
        return (self.instrument_id, self.kind.value, self.selector)


@dataclass(frozen=True, slots=True)
class CapabilityFeedRequirement:
    kind: FeedKind
    selector: str = "default"
    parameters: Mapping[str, RequirementParameter] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, FeedKind):
            raise ValueError("kind must be a FeedKind")
        object.__setattr__(self, "selector", _required_text(self.selector, "selector"))
        object.__setattr__(
            self,
            "parameters",
            MappingProxyType(_validated_parameters(self.parameters or {})),
        )

    @property
    def requirement_key(self) -> tuple[str, str]:
        return (self.kind.value, self.selector)

    def bind(self, instrument_id: str) -> FeedRequirement:
        return FeedRequirement(
            instrument_id=instrument_id,
            kind=self.kind,
            selector=self.selector,
            parameters=self.parameters,
        )


@dataclass(frozen=True, slots=True)
class CapabilityHistoricalRequirement:
    kind: FeedKind
    selector: str
    window: HistoricalWindow
    minimum_observations: int
    maximum_observations: int
    parameters: Mapping[str, RequirementParameter] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, FeedKind):
            raise ValueError("kind must be a FeedKind")
        if self.kind is not FeedKind.BARS:
            raise ValueError("Stage 9B supports historical bar requirements only")
        object.__setattr__(self, "selector", _required_text(self.selector, "selector"))
        if not isinstance(self.window, HistoricalWindow):
            raise ValueError("window must be a HistoricalWindow")
        if (
            not isinstance(self.minimum_observations, int)
            or isinstance(self.minimum_observations, bool)
            or self.minimum_observations <= 0
        ):
            raise ValueError("minimum_observations must be a positive integer")
        if (
            not isinstance(self.maximum_observations, int)
            or isinstance(self.maximum_observations, bool)
            or self.maximum_observations < self.minimum_observations
        ):
            raise ValueError(
                "maximum_observations must be an integer not below minimum_observations",
            )
        object.__setattr__(
            self,
            "parameters",
            MappingProxyType(_validated_parameters(self.parameters or {})),
        )


@dataclass(frozen=True, slots=True)
class CapabilityDeclaration:
    capability_id: str
    version: int
    live_feeds: tuple[CapabilityFeedRequirement, ...] = ()
    historical_requirements: tuple[CapabilityHistoricalRequirement, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capability_id",
            _required_text(self.capability_id, "capability_id"),
        )
        if not isinstance(self.version, int) or isinstance(self.version, bool) or self.version <= 0:
            raise ValueError("version must be a positive integer")
        if not isinstance(self.live_feeds, tuple) or any(
            not isinstance(requirement, CapabilityFeedRequirement)
            for requirement in self.live_feeds
        ):
            raise ValueError("live_feeds must contain CapabilityFeedRequirement values")
        if not self.live_feeds and not self.historical_requirements:
            raise ValueError("a capability must declare live or historical requirements")
        keys = [requirement.requirement_key for requirement in self.live_feeds]
        if len(keys) != len(set(keys)):
            raise ValueError("a capability cannot declare the same logical stream twice")
        if not isinstance(self.historical_requirements, tuple) or any(
            not isinstance(requirement, CapabilityHistoricalRequirement)
            for requirement in self.historical_requirements
        ):
            raise ValueError(
                "historical_requirements must contain CapabilityHistoricalRequirement values",
            )


@dataclass(frozen=True, slots=True)
class ObservationDemand:
    demand_id: str
    owner: DemandOwner
    requirement: FeedRequirement
    priority: int = 50
    expires_at: datetime | None = None
    purpose: str = "unspecified"

    def __post_init__(self) -> None:
        object.__setattr__(self, "demand_id", _required_text(self.demand_id, "demand_id"))
        if not isinstance(self.owner, DemandOwner):
            raise ValueError("owner must be a DemandOwner")
        if not isinstance(self.requirement, FeedRequirement):
            raise ValueError("requirement must be a FeedRequirement")
        if (
            not isinstance(self.priority, int)
            or isinstance(self.priority, bool)
            or not 0 <= self.priority <= 100
        ):
            raise ValueError("priority must be an integer from 0 through 100")
        object.__setattr__(self, "purpose", _required_text(self.purpose, "purpose"))
        if self.expires_at is not None:
            object.__setattr__(
                self,
                "expires_at",
                _utc_datetime(self.expires_at, "expires_at"),
            )

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and self.expires_at <= _utc_datetime(now, "now")


@dataclass(frozen=True, slots=True)
class ProviderDemand:
    requirement: FeedRequirement
    consumer_ids: tuple[str, ...]
    priority: int
    expires_at: datetime | None


class DemandConflictError(ValueError):
    pass


class DemandReconciler:
    def __init__(self) -> None:
        self._demands: dict[str, ObservationDemand] = {}

    @property
    def demands(self) -> tuple[ObservationDemand, ...]:
        return tuple(self._demands[key] for key in sorted(self._demands))

    def add(self, demand: ObservationDemand, *, now: datetime) -> bool:
        if not isinstance(demand, ObservationDemand):
            raise ValueError("demand must be an ObservationDemand")
        if demand.is_expired(now):
            raise ValueError("cannot add an expired demand")
        existing = self._demands.get(demand.demand_id)
        if existing is not None:
            if existing == demand:
                return False
            raise DemandConflictError(f"demand_id already exists: {demand.demand_id}")
        self._reject_stream_conflict(demand)
        self._demands[demand.demand_id] = demand
        return True

    def remove(self, demand_id: str) -> bool:
        return self._demands.pop(_required_text(demand_id, "demand_id"), None) is not None

    def expire(self, *, now: datetime) -> tuple[str, ...]:
        expired = tuple(
            demand_id
            for demand_id, demand in sorted(self._demands.items())
            if demand.is_expired(now)
        )
        for demand_id in expired:
            del self._demands[demand_id]
        return expired

    def provider_demands(self, *, now: datetime) -> tuple[ProviderDemand, ...]:
        current = [demand for demand in self._demands.values() if not demand.is_expired(now)]
        grouped: dict[StreamKey, list[ObservationDemand]] = {}
        for demand in current:
            grouped.setdefault(demand.requirement.stream_key, []).append(demand)

        reconciled: list[ProviderDemand] = []
        for key in sorted(grouped):
            consumers = grouped[key]
            requirement = consumers[0].requirement
            if any(candidate.requirement != requirement for candidate in consumers[1:]):
                raise DemandConflictError(f"incompatible parameters for logical stream: {key}")
            expirations = [demand.expires_at for demand in consumers]
            expires_at = None if None in expirations else max(expirations, default=None)
            reconciled.append(
                ProviderDemand(
                    requirement=requirement,
                    consumer_ids=tuple(sorted(demand.demand_id for demand in consumers)),
                    priority=max(demand.priority for demand in consumers),
                    expires_at=expires_at,
                ),
            )
        return tuple(reconciled)

    def _reject_stream_conflict(self, demand: ObservationDemand) -> None:
        for existing in self._demands.values():
            if existing.requirement.stream_key != demand.requirement.stream_key:
                continue
            if existing.requirement != demand.requirement:
                raise DemandConflictError(
                    f"incompatible parameters for logical stream: {demand.requirement.stream_key}",
                )


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _validated_parameters(
    parameters: Mapping[str, RequirementParameter],
) -> dict[str, RequirementParameter]:
    if not isinstance(parameters, Mapping):
        raise ValueError("parameters must be a mapping")
    validated: dict[str, RequirementParameter] = {}
    for key, value in parameters.items():
        normalized_key = _required_text(key, "parameter key")
        if not isinstance(value, str | int | float | bool):
            raise ValueError(f"unsupported parameter value for {normalized_key!r}")
        if isinstance(value, float) and not isfinite(value):
            raise ValueError(f"non-finite parameter value for {normalized_key!r}")
        validated[normalized_key] = value
    return dict(sorted(validated.items()))


def _utc_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")
    return value.astimezone(UTC)
