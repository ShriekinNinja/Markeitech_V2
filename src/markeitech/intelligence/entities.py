from __future__ import annotations

import json
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from math import isfinite
from types import MappingProxyType

from markeitech.intelligence.metrics import (
    MetricFidelity,
    MetricHealth,
    MetricParameterDefinition,
    MetricRegistry,
)

ENTITY_REVISION_TYPE_NAME = "markeitech.entity.revision"
"""Nautilus custom-data type name for analytical entity revisions."""
ENTITY_SNAPSHOT_REQUEST_TYPE_NAME = "markeitech.entity.snapshot.request"
"""Nautilus custom-data type name for analytical entity snapshot requests."""
ENTITY_SNAPSHOT_TYPE_NAME = "markeitech.entity.snapshot"
"""Nautilus custom-data type name for analytical entity snapshots."""

type EntityKey = tuple[str, int]
type EntityParameterValue = str | int | float | Decimal | bool


class EntityLifecycle(StrEnum):
    """Lifecycle states that qualify an analytical entity revision."""

    WARMING = "WARMING"
    ACTIVE = "ACTIVE"
    COMPLETE = "COMPLETE"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"


class EntityDurability(StrEnum):
    """Approved durability classes declared by analytical entity definitions."""

    TRANSIENT = "TRANSIENT"
    FINALIZED_SESSION = "FINALIZED_SESSION"
    CROSS_SESSION_CHECKPOINT = "CROSS_SESSION_CHECKPOINT"


class EntityEvidenceKind(StrEnum):
    """Canonical evidence-source categories referenced by an entity revision."""

    METRIC = "METRIC"
    ENTITY = "ENTITY"
    SESSION = "SESSION"


class EntityAdmissionStatus(StrEnum):
    """Deterministic outcomes from admitting an entity revision to state."""

    ADDED = "ADDED"
    UPDATED = "UPDATED"
    DUPLICATE = "DUPLICATE"
    REJECTED_STALE = "REJECTED_STALE"
    REJECTED_CONFLICT = "REJECTED_CONFLICT"
    REJECTED_REVISION_GAP = "REJECTED_REVISION_GAP"
    REJECTED_CAPACITY = "REJECTED_CAPACITY"


@dataclass(frozen=True, slots=True)
class EntityPayload:
    """Marker base for immutable entity-specific payload contracts."""


@dataclass(frozen=True, slots=True, order=True)
class EntityIdentityDimension:
    """Name one stable dimension participating in analytical entity identity."""

    name: str
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "dimension name"))
        object.__setattr__(self, "value", _required_text(self.value, "dimension value"))


@dataclass(frozen=True, slots=True)
class EntityIdentity:
    """Define the stable, hash-derived identity of one analytical entity."""

    entity_type: str
    entity_version: int
    instrument_id: str
    analytical_profile_id: str
    analytical_profile_version: int
    dimensions: tuple[EntityIdentityDimension, ...]

    def __post_init__(self) -> None:
        for field in ("entity_type", "instrument_id", "analytical_profile_id"):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        _positive_int(self.entity_version, "entity_version")
        _positive_int(self.analytical_profile_version, "analytical_profile_version")
        _typed_tuple(self.dimensions, EntityIdentityDimension, "dimensions")
        names = tuple(item.name for item in self.dimensions)
        if len(names) != len(set(names)):
            raise ValueError("entity identity dimension names must be unique")
        object.__setattr__(self, "dimensions", tuple(sorted(self.dimensions)))

    @property
    def key(self) -> EntityKey:
        return (self.entity_type, self.entity_version)

    @property
    def entity_id(self) -> str:
        canonical = json.dumps(
            {
                "analytical_profile_id": self.analytical_profile_id,
                "analytical_profile_version": self.analytical_profile_version,
                "dimensions": [[item.name, item.value] for item in self.dimensions],
                "entity_type": self.entity_type,
                "entity_version": self.entity_version,
                "instrument_id": self.instrument_id,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return f"entity:{sha256(canonical.encode('ascii')).hexdigest()}"


@dataclass(frozen=True, slots=True)
class EntityMetricDependency:
    """Reference one exact metric definition required by an entity."""

    metric_id: str
    metric_version: int
    required: bool
    permitted_health: tuple[MetricHealth, ...]
    permitted_fidelities: tuple[MetricFidelity, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric_id", _required_text(self.metric_id, "metric_id"))
        _positive_int(self.metric_version, "metric_version")
        if not isinstance(self.required, bool):
            raise ValueError("required must be a boolean")
        _evidence_envelope(self.permitted_health, self.permitted_fidelities)

    @property
    def key(self) -> tuple[str, int]:
        return (self.metric_id, self.metric_version)


@dataclass(frozen=True, slots=True)
class EntityDependency:
    """Reference one exact upstream entity definition."""

    entity_type: str
    entity_version: int
    required: bool
    permitted_health: tuple[MetricHealth, ...]
    permitted_fidelities: tuple[MetricFidelity, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_type", _required_text(self.entity_type, "entity_type"))
        _positive_int(self.entity_version, "entity_version")
        if not isinstance(self.required, bool):
            raise ValueError("required must be a boolean")
        _evidence_envelope(self.permitted_health, self.permitted_fidelities)

    @property
    def key(self) -> EntityKey:
        return (self.entity_type, self.entity_version)


@dataclass(frozen=True, slots=True)
class EntityDefinition:
    """Describe a versioned analytical entity and its evidence contract."""

    entity_type: str
    version: int
    decision_question: str
    implementation_id: str
    payload_type: type[EntityPayload]
    identity_dimensions: tuple[str, ...]
    metric_inputs: tuple[EntityMetricDependency, ...]
    entity_inputs: tuple[EntityDependency, ...]
    permitted_health: tuple[MetricHealth, ...]
    permitted_fidelities: tuple[MetricFidelity, ...]
    durability: EntityDurability
    completion_rule: str
    invalidation_rule: str
    expiry_rule: str
    parameters: tuple[MetricParameterDefinition, ...] = ()
    event_uses: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field in (
            "entity_type",
            "decision_question",
            "implementation_id",
            "completion_rule",
            "invalidation_rule",
            "expiry_rule",
        ):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        _positive_int(self.version, "version")
        if not isinstance(self.payload_type, type) or not issubclass(
            self.payload_type,
            EntityPayload,
        ):
            raise ValueError("payload_type must derive from EntityPayload")
        identity_dimensions = _text_tuple(self.identity_dimensions, "identity dimension")
        if not identity_dimensions:
            raise ValueError("identity_dimensions must not be empty")
        if len(identity_dimensions) != len(set(identity_dimensions)):
            raise ValueError("identity dimensions must be unique")
        object.__setattr__(self, "identity_dimensions", tuple(sorted(identity_dimensions)))
        _typed_tuple(self.metric_inputs, EntityMetricDependency, "metric_inputs")
        _typed_tuple(self.entity_inputs, EntityDependency, "entity_inputs")
        if not self.metric_inputs and not self.entity_inputs:
            raise ValueError("an entity definition must declare at least one dependency")
        _unique((item.key for item in self.metric_inputs), "metric input")
        _unique((item.key for item in self.entity_inputs), "entity input")
        if self.key in {item.key for item in self.entity_inputs}:
            raise ValueError("an entity definition cannot depend on itself")
        _typed_tuple(self.permitted_health, MetricHealth, "permitted_health")
        _typed_tuple(self.permitted_fidelities, MetricFidelity, "permitted_fidelities")
        if not self.permitted_health or not self.permitted_fidelities:
            raise ValueError("permitted health and fidelity must not be empty")
        _unique(self.permitted_health, "permitted health")
        _unique(self.permitted_fidelities, "permitted fidelity")
        if not isinstance(self.durability, EntityDurability):
            raise ValueError("durability must be EntityDurability")
        _typed_tuple(self.parameters, MetricParameterDefinition, "parameters")
        _unique((item.parameter_id for item in self.parameters), "parameter")
        object.__setattr__(self, "event_uses", _text_tuple(self.event_uses, "event use"))
        _unique(self.event_uses, "event use")

    @property
    def key(self) -> EntityKey:
        return (self.entity_type, self.version)


@dataclass(frozen=True, slots=True)
class EntityParameterSet:
    """Bind exact parameter values and effective time to one entity version.

    ``effective_from_ns`` is a UTC Unix nanosecond timestamp.
    """

    entity_type: str
    entity_version: int
    parameter_version: int
    effective_from_ns: int
    source: str
    values: Mapping[str, EntityParameterValue]
    supersedes_parameter_version: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_type", _required_text(self.entity_type, "entity_type"))
        object.__setattr__(self, "source", _required_text(self.source, "source"))
        _positive_int(self.entity_version, "entity_version")
        _positive_int(self.parameter_version, "parameter_version")
        _timestamp(self.effective_from_ns, "effective_from_ns")
        if self.supersedes_parameter_version is not None:
            _positive_int(self.supersedes_parameter_version, "supersedes_parameter_version")
            if self.supersedes_parameter_version >= self.parameter_version:
                raise ValueError("superseded parameter version must be older")
        object.__setattr__(self, "values", MappingProxyType(_parameter_values(self.values)))

    @property
    def key(self) -> EntityKey:
        return (self.entity_type, self.entity_version)


@dataclass(frozen=True, slots=True)
class EntityEvidenceReference:
    """Cite an exact metric, entity, or session evidence revision.

    ``effective_ts_ns`` is a UTC Unix nanosecond timestamp associated with the
    referenced evidence.
    """

    kind: EntityEvidenceKind
    definition_id: str
    reference_id: str
    version: int
    revision: int
    effective_ts_ns: int
    health: MetricHealth
    fidelity: MetricFidelity

    def __post_init__(self) -> None:
        if not isinstance(self.kind, EntityEvidenceKind):
            raise ValueError("kind must be EntityEvidenceKind")
        object.__setattr__(
            self,
            "definition_id",
            _required_text(self.definition_id, "definition_id"),
        )
        object.__setattr__(self, "reference_id", _required_text(self.reference_id, "reference_id"))
        _positive_int(self.version, "version")
        _positive_int(self.revision, "revision")
        _timestamp(self.effective_ts_ns, "effective_ts_ns")
        if not isinstance(self.health, MetricHealth):
            raise ValueError("health must be MetricHealth")
        if not isinstance(self.fidelity, MetricFidelity):
            raise ValueError("fidelity must be MetricFidelity")


@dataclass(frozen=True, slots=True)
class EntityRevision:
    """Carry one immutable revision of a typed analytical entity.

    UTC Unix nanosecond timestamps distinguish evidence effectiveness,
    observation, calculation, and publication. Missing payloads preserve explicit
    abstention reasons; revisions retain exact evidence and predecessor lineage.
    """

    identity: EntityIdentity
    revision: int
    parameter_version: int
    payload: EntityPayload | None
    lifecycle: EntityLifecycle
    effective_ts_ns: int
    observed_ts_ns: int
    calculated_ts_ns: int
    published_ts_ns: int
    health: MetricHealth
    fidelity: MetricFidelity
    evidence_refs: tuple[EntityEvidenceReference, ...]
    missing_reasons: tuple[str, ...]
    conflict_reasons: tuple[str, ...]
    source: str
    schema_version: int
    previous_revision: int | None = None
    restored: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.identity, EntityIdentity):
            raise ValueError("identity must be EntityIdentity")
        _positive_int(self.revision, "revision")
        _positive_int(self.parameter_version, "parameter_version")
        if self.payload is not None and not isinstance(self.payload, EntityPayload):
            raise ValueError("payload must derive from EntityPayload")
        if not isinstance(self.lifecycle, EntityLifecycle):
            raise ValueError("lifecycle must be EntityLifecycle")
        for field in (
            "effective_ts_ns",
            "observed_ts_ns",
            "calculated_ts_ns",
            "published_ts_ns",
        ):
            _timestamp(getattr(self, field), field)
        if not self.observed_ts_ns <= self.calculated_ts_ns <= self.published_ts_ns:
            raise ValueError("entity timestamps must satisfy observed <= calculated <= published")
        if self.effective_ts_ns > self.published_ts_ns:
            raise ValueError("entity effective timestamp cannot be after publication")
        if not isinstance(self.health, MetricHealth):
            raise ValueError("health must be MetricHealth")
        if not isinstance(self.fidelity, MetricFidelity):
            raise ValueError("fidelity must be MetricFidelity")
        _typed_tuple(self.evidence_refs, EntityEvidenceReference, "evidence_refs")
        _unique(
            (
                (
                    item.kind,
                    item.definition_id,
                    item.reference_id,
                    item.version,
                    item.revision,
                )
                for item in self.evidence_refs
            ),
            "evidence reference",
        )
        object.__setattr__(
            self,
            "missing_reasons",
            _text_tuple(self.missing_reasons, "missing reason"),
        )
        object.__setattr__(
            self,
            "conflict_reasons",
            _text_tuple(self.conflict_reasons, "conflict reason"),
        )
        object.__setattr__(self, "source", _required_text(self.source, "source"))
        _positive_int(self.schema_version, "schema_version")
        if self.previous_revision is not None:
            _positive_int(self.previous_revision, "previous_revision")
            if self.previous_revision >= self.revision:
                raise ValueError("previous_revision must be older than revision")
        if not isinstance(self.restored, bool):
            raise ValueError("restored must be a boolean")
        if self.payload is None and not self.missing_reasons:
            raise ValueError("a missing entity payload requires a missing reason")
        if (
            self.lifecycle in {EntityLifecycle.ACTIVE, EntityLifecycle.COMPLETE}
            and self.payload is None
        ):
            raise ValueError("active and complete entities require a payload")

    @property
    def entity_id(self) -> str:
        return self.identity.entity_id

    @property
    def ts_event(self) -> int:
        return self.effective_ts_ns

    @property
    def ts_init(self) -> int:
        return self.published_ts_ns

    def meaningful_signature(self) -> tuple[object, ...]:
        return (
            self.payload,
            self.lifecycle,
            self.parameter_version,
            self.health,
            self.fidelity,
            self.evidence_refs,
            self.missing_reasons,
            self.conflict_reasons,
            self.source,
            self.schema_version,
            self.restored,
        )


class EntityRegistry:
    """Validate definitions, dependencies, parameters, and entity revisions."""

    def __init__(
        self,
        definitions: tuple[EntityDefinition, ...],
        *,
        metric_registry: MetricRegistry | None = None,
        metric_keys: Collection[tuple[str, int]] | None = None,
    ) -> None:
        _typed_tuple(definitions, EntityDefinition, "definitions")
        by_key: dict[EntityKey, EntityDefinition] = {}
        for definition in definitions:
            if definition.key in by_key:
                raise ValueError(f"duplicate entity definition: {definition.key!r}")
            by_key[definition.key] = definition
        for definition in definitions:
            missing_entities = tuple(
                item.key for item in definition.entity_inputs if item.key not in by_key
            )
            if missing_entities:
                raise ValueError(
                    f"entity dependencies are not registered: {missing_entities!r}",
                )
            if definition.metric_inputs:
                if metric_registry is None and metric_keys is None:
                    raise ValueError(
                        "metric_registry or metric_keys is required for metric dependencies",
                    )
                known_metric_keys = frozenset(metric_keys or ())
                for dependency in definition.metric_inputs:
                    if metric_registry is not None:
                        try:
                            metric_registry.get(*dependency.key)
                        except KeyError as exc:
                            raise ValueError(
                                f"metric dependency is not registered: {dependency.key!r}",
                            ) from exc
                    elif dependency.key not in known_metric_keys:
                        raise ValueError(
                            f"metric dependency is not registered: {dependency.key!r}",
                        )
        _reject_entity_cycles(by_key)
        self._definitions = MappingProxyType(dict(sorted(by_key.items())))

    @property
    def definitions(self) -> tuple[EntityDefinition, ...]:
        return tuple(self._definitions.values())

    def get(self, entity_type: str, version: int) -> EntityDefinition:
        key = (_required_text(entity_type, "entity_type"), version)
        _positive_int(version, "version")
        try:
            return self._definitions[key]
        except KeyError as exc:
            raise KeyError(f"entity definition is not registered: {key!r}") from exc

    def latest(self, entity_type: str) -> EntityDefinition:
        normalized = _required_text(entity_type, "entity_type")
        matches = [item for key, item in self._definitions.items() if key[0] == normalized]
        if not matches:
            raise KeyError(f"entity definition is not registered: {normalized!r}")
        return max(matches, key=lambda item: item.version)

    def validate_parameters(self, parameters: EntityParameterSet) -> None:
        if not isinstance(parameters, EntityParameterSet):
            raise ValueError("parameters must be EntityParameterSet")
        definition = self.get(*parameters.key)
        declared = {item.parameter_id: item for item in definition.parameters}
        if set(parameters.values) != set(declared):
            raise ValueError("parameter set must provide every declared parameter exactly once")
        for parameter_id, value in parameters.values.items():
            declared[parameter_id].validate(value)

    def validate_revision(self, revision: EntityRevision) -> None:
        if not isinstance(revision, EntityRevision):
            raise ValueError("revision must be EntityRevision")
        definition = self.get(*revision.identity.key)
        dimension_names = tuple(item.name for item in revision.identity.dimensions)
        if dimension_names != definition.identity_dimensions:
            raise ValueError("entity identity dimensions do not match its definition")
        if revision.payload is not None and not isinstance(
            revision.payload,
            definition.payload_type,
        ):
            raise ValueError("entity payload does not match its definition")
        if revision.health not in definition.permitted_health:
            raise ValueError("entity health is incompatible with its definition")
        if revision.fidelity not in definition.permitted_fidelities:
            raise ValueError("entity fidelity is incompatible with its definition")
        if revision.restored:
            if definition.durability is EntityDurability.TRANSIENT:
                raise ValueError("transient entities cannot be restored")
            if (
                definition.durability is EntityDurability.CROSS_SESSION_CHECKPOINT
                and revision.lifecycle not in {EntityLifecycle.DEGRADED, EntityLifecycle.STALE}
            ):
                raise ValueError(
                    "restored cross-session checkpoints must remain degraded or stale",
                )
        _validate_dependency_evidence(
            EntityEvidenceKind.METRIC,
            definition.metric_inputs,
            revision.evidence_refs,
            require_all=revision.payload is not None,
        )
        _validate_dependency_evidence(
            EntityEvidenceKind.ENTITY,
            definition.entity_inputs,
            revision.evidence_refs,
            require_all=revision.payload is not None,
        )


@dataclass(frozen=True, slots=True)
class EntityStateBookLimits:
    """Bound global, per-instrument, and per-type retained entity state."""

    maximum_entities: int
    maximum_entities_per_instrument: int
    maximum_entities_per_type: int

    def __post_init__(self) -> None:
        for field in (
            "maximum_entities",
            "maximum_entities_per_instrument",
            "maximum_entities_per_type",
        ):
            _positive_int(getattr(self, field), field)
        if self.maximum_entities_per_instrument > self.maximum_entities:
            raise ValueError("per-instrument entity limit cannot exceed the global limit")
        if self.maximum_entities_per_type > self.maximum_entities:
            raise ValueError("per-type entity limit cannot exceed the global limit")


@dataclass(frozen=True, slots=True)
class EntityAdmission:
    """Report the accepted state and any deterministic capacity evictions."""

    status: EntityAdmissionStatus
    current: EntityRevision | None
    evicted_entity_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, EntityAdmissionStatus):
            raise ValueError("status must be EntityAdmissionStatus")
        if self.current is not None and not isinstance(self.current, EntityRevision):
            raise ValueError("current must be EntityRevision or None")
        object.__setattr__(
            self,
            "evicted_entity_ids",
            _text_tuple(self.evicted_entity_ids, "evicted entity ID"),
        )


@dataclass(frozen=True, slots=True)
class EntitySnapshot:
    """Carry an immutable point-in-time set of retained entity revisions."""

    generated_ts_ns: int
    revisions: tuple[EntityRevision, ...]

    def __post_init__(self) -> None:
        _timestamp(self.generated_ts_ns, "generated_ts_ns")
        _typed_tuple(self.revisions, EntityRevision, "revisions")

    @property
    def ts_event(self) -> int:
        return self.generated_ts_ns

    @property
    def ts_init(self) -> int:
        return self.generated_ts_ns


@dataclass(frozen=True, slots=True)
class EntitySnapshotRequest:
    """Request a filtered immutable entity snapshot at a UTC nanosecond time."""

    request_id: str
    requester: str
    requested_ts_ns: int
    instrument_id: str | None = None
    entity_type: str | None = None
    analytical_profile_id: str | None = None
    analytical_profile_version: int | None = None
    lifecycles: tuple[EntityLifecycle, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _required_text(self.request_id, "request_id"))
        object.__setattr__(self, "requester", _required_text(self.requester, "requester"))
        _timestamp(self.requested_ts_ns, "requested_ts_ns")
        if self.instrument_id is not None:
            object.__setattr__(
                self,
                "instrument_id",
                _required_text(self.instrument_id, "instrument_id"),
            )
        if self.entity_type is not None:
            object.__setattr__(
                self,
                "entity_type",
                _required_text(self.entity_type, "entity_type"),
            )
        if self.analytical_profile_id is not None:
            object.__setattr__(
                self,
                "analytical_profile_id",
                _required_text(self.analytical_profile_id, "analytical_profile_id"),
            )
        if self.analytical_profile_version is not None:
            _positive_int(self.analytical_profile_version, "analytical_profile_version")
        if self.lifecycles is not None:
            _typed_tuple(self.lifecycles, EntityLifecycle, "lifecycles")
            _unique(self.lifecycles, "lifecycle")

    @property
    def ts_event(self) -> int:
        return self.requested_ts_ns

    @property
    def ts_init(self) -> int:
        return self.requested_ts_ns


@dataclass(frozen=True, slots=True)
class EntitySnapshotResponse:
    """Correlate one entity snapshot with its requester and request identity."""

    request_id: str
    requester: str
    snapshot: EntitySnapshot

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _required_text(self.request_id, "request_id"))
        object.__setattr__(self, "requester", _required_text(self.requester, "requester"))
        if not isinstance(self.snapshot, EntitySnapshot):
            raise ValueError("snapshot must be EntitySnapshot")

    @property
    def ts_event(self) -> int:
        return self.snapshot.ts_event

    @property
    def ts_init(self) -> int:
        return self.snapshot.ts_init


_TERMINAL_LIFECYCLES = {
    EntityLifecycle.COMPLETE,
    EntityLifecycle.INVALIDATED,
    EntityLifecycle.EXPIRED,
}


class EntityStateBook:
    """Own bounded latest-revision state with deterministic admission semantics."""

    def __init__(self, registry: EntityRegistry, limits: EntityStateBookLimits) -> None:
        if not isinstance(registry, EntityRegistry):
            raise ValueError("registry must be EntityRegistry")
        if not isinstance(limits, EntityStateBookLimits):
            raise ValueError("limits must be EntityStateBookLimits")
        self._registry = registry
        self._limits = limits
        self._by_id: dict[str, EntityRevision] = {}

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, entity_id: str) -> EntityRevision | None:
        return self._by_id.get(_required_text(entity_id, "entity_id"))

    def admit(self, revision: EntityRevision) -> EntityAdmission:
        self._registry.validate_revision(revision)
        entity_id = revision.entity_id
        current = self._by_id.get(entity_id)
        if current is not None:
            return self._admit_revision(current, revision)

        if revision.restored:
            expected_previous = None if revision.revision == 1 else revision.revision - 1
            if revision.previous_revision != expected_previous:
                return EntityAdmission(EntityAdmissionStatus.REJECTED_REVISION_GAP, None)
        elif revision.revision != 1 or revision.previous_revision is not None:
            return EntityAdmission(EntityAdmissionStatus.REJECTED_REVISION_GAP, None)

        proposed = dict(self._by_id)
        proposed[entity_id] = revision
        evicted = _enforce_limits(proposed, self._limits, protected_entity_id=entity_id)
        if evicted is None:
            return EntityAdmission(EntityAdmissionStatus.REJECTED_CAPACITY, None)
        self._by_id = proposed
        return EntityAdmission(EntityAdmissionStatus.ADDED, revision, evicted)

    def snapshot(
        self,
        generated_ts_ns: int,
        *,
        instrument_id: str | None = None,
        entity_type: str | None = None,
        analytical_profile_id: str | None = None,
        analytical_profile_version: int | None = None,
        dimensions: Mapping[str, str] | None = None,
        lifecycles: tuple[EntityLifecycle, ...] | None = None,
    ) -> EntitySnapshot:
        _timestamp(generated_ts_ns, "generated_ts_ns")
        normalized_instrument = (
            None if instrument_id is None else _required_text(instrument_id, "instrument_id")
        )
        normalized_type = (
            None if entity_type is None else _required_text(entity_type, "entity_type")
        )
        normalized_profile = (
            None
            if analytical_profile_id is None
            else _required_text(analytical_profile_id, "analytical_profile_id")
        )
        if analytical_profile_version is not None:
            _positive_int(analytical_profile_version, "analytical_profile_version")
        normalized_dimensions = _dimension_filter(dimensions)
        if lifecycles is not None:
            _typed_tuple(lifecycles, EntityLifecycle, "lifecycles")
            _unique(lifecycles, "lifecycle")
        revisions = tuple(
            sorted(
                (
                    item
                    for item in self._by_id.values()
                    if normalized_instrument is None
                    or item.identity.instrument_id == normalized_instrument
                ),
                key=lambda item: item.entity_id,
            ),
        )
        if normalized_type is not None:
            revisions = tuple(
                item for item in revisions if item.identity.entity_type == normalized_type
            )
        if normalized_profile is not None:
            revisions = tuple(
                item
                for item in revisions
                if item.identity.analytical_profile_id == normalized_profile
            )
        if analytical_profile_version is not None:
            revisions = tuple(
                item
                for item in revisions
                if item.identity.analytical_profile_version == analytical_profile_version
            )
        if normalized_dimensions:
            required_dimensions = normalized_dimensions.items()
            revisions = tuple(
                item
                for item in revisions
                if required_dimensions
                <= {
                    dimension.name: dimension.value for dimension in item.identity.dimensions
                }.items()
            )
        if lifecycles is not None:
            allowed = set(lifecycles)
            revisions = tuple(item for item in revisions if item.lifecycle in allowed)
        return EntitySnapshot(generated_ts_ns, revisions)

    def prune_terminal(
        self,
        *,
        published_before_ns: int,
        maximum_removals: int,
    ) -> tuple[EntityRevision, ...]:
        _timestamp(published_before_ns, "published_before_ns")
        _non_negative_int(maximum_removals, "maximum_removals")
        candidates = sorted(
            (
                item
                for item in self._by_id.values()
                if item.lifecycle in _TERMINAL_LIFECYCLES
                and item.published_ts_ns < published_before_ns
            ),
            key=_eviction_key,
        )
        removed = tuple(candidates[:maximum_removals])
        for item in removed:
            del self._by_id[item.entity_id]
        return removed

    def _admit_revision(
        self,
        current: EntityRevision,
        revision: EntityRevision,
    ) -> EntityAdmission:
        if revision.revision < current.revision:
            return EntityAdmission(EntityAdmissionStatus.REJECTED_STALE, current)
        if revision.revision == current.revision:
            status = (
                EntityAdmissionStatus.DUPLICATE
                if revision == current
                else EntityAdmissionStatus.REJECTED_CONFLICT
            )
            return EntityAdmission(status, current)
        if (
            revision.revision != current.revision + 1
            or revision.previous_revision != current.revision
        ):
            return EntityAdmission(EntityAdmissionStatus.REJECTED_REVISION_GAP, current)
        if (
            revision.effective_ts_ns < current.effective_ts_ns
            or revision.published_ts_ns < current.published_ts_ns
        ):
            return EntityAdmission(EntityAdmissionStatus.REJECTED_STALE, current)
        if revision.meaningful_signature() == current.meaningful_signature():
            return EntityAdmission(EntityAdmissionStatus.DUPLICATE, current)
        self._by_id[revision.entity_id] = revision
        return EntityAdmission(EntityAdmissionStatus.UPDATED, revision)


def _enforce_limits(
    proposed: dict[str, EntityRevision],
    limits: EntityStateBookLimits,
    *,
    protected_entity_id: str,
) -> tuple[str, ...] | None:
    evicted: list[str] = []
    while True:
        violating_scope = _violating_scope(proposed, limits, protected_entity_id)
        if violating_scope is None:
            return tuple(evicted)
        candidates = sorted(
            (
                item
                for item in proposed.values()
                if item.entity_id != protected_entity_id
                and item.lifecycle in _TERMINAL_LIFECYCLES
                and violating_scope(item)
            ),
            key=_eviction_key,
        )
        if not candidates:
            return None
        victim = candidates[0]
        del proposed[victim.entity_id]
        evicted.append(victim.entity_id)


def _violating_scope(
    proposed: Mapping[str, EntityRevision],
    limits: EntityStateBookLimits,
    protected_entity_id: str,
) -> Callable[[EntityRevision], bool] | None:
    protected = proposed[protected_entity_id]
    instrument_count = sum(
        item.identity.instrument_id == protected.identity.instrument_id
        for item in proposed.values()
    )
    if instrument_count > limits.maximum_entities_per_instrument:
        return lambda item: item.identity.instrument_id == protected.identity.instrument_id
    type_count = sum(
        item.identity.instrument_id == protected.identity.instrument_id
        and item.identity.entity_type == protected.identity.entity_type
        for item in proposed.values()
    )
    if type_count > limits.maximum_entities_per_type:
        return lambda item: (
            item.identity.instrument_id == protected.identity.instrument_id
            and item.identity.entity_type == protected.identity.entity_type
        )
    if len(proposed) > limits.maximum_entities:
        return lambda _item: True
    return None


def _eviction_key(revision: EntityRevision) -> tuple[int, str]:
    return (revision.published_ts_ns, revision.entity_id)


def _reject_entity_cycles(definitions: Mapping[EntityKey, EntityDefinition]) -> None:
    visiting: set[EntityKey] = set()
    visited: set[EntityKey] = set()

    def visit(key: EntityKey) -> None:
        if key in visiting:
            raise ValueError(f"entity dependency cycle detected at {key!r}")
        if key in visited:
            return
        visiting.add(key)
        for dependency in definitions[key].entity_inputs:
            visit(dependency.key)
        visiting.remove(key)
        visited.add(key)

    for key in definitions:
        visit(key)


def _parameter_values(
    values: Mapping[str, EntityParameterValue],
) -> dict[str, EntityParameterValue]:
    if not isinstance(values, Mapping):
        raise ValueError("values must be a mapping")
    normalized: dict[str, EntityParameterValue] = {}
    for raw_key, value in values.items():
        key = _required_text(raw_key, "parameter key")
        if key in normalized:
            raise ValueError(f"duplicate parameter key: {key!r}")
        if not isinstance(value, (str, int, float, Decimal, bool)):
            raise ValueError(f"unsupported parameter value for {key!r}")
        if isinstance(value, float) and not isfinite(value):
            raise ValueError(f"parameter value for {key!r} must be finite")
        normalized[key] = value
    return normalized


def _dimension_filter(values: Mapping[str, str] | None) -> dict[str, str]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        raise ValueError("dimensions must be a mapping")
    normalized: dict[str, str] = {}
    for raw_name, raw_value in values.items():
        name = _required_text(raw_name, "dimension name")
        if name in normalized:
            raise ValueError(f"duplicate dimension name: {name!r}")
        normalized[name] = _required_text(raw_value, "dimension value")
    return normalized


def _evidence_envelope(
    permitted_health: tuple[MetricHealth, ...],
    permitted_fidelities: tuple[MetricFidelity, ...],
) -> None:
    _typed_tuple(permitted_health, MetricHealth, "permitted_health")
    _typed_tuple(permitted_fidelities, MetricFidelity, "permitted_fidelities")
    if not permitted_health or not permitted_fidelities:
        raise ValueError("permitted evidence health and fidelity must not be empty")
    _unique(permitted_health, "permitted evidence health")
    _unique(permitted_fidelities, "permitted evidence fidelity")


def _validate_dependency_evidence(
    kind: EntityEvidenceKind,
    dependencies: tuple[EntityMetricDependency, ...] | tuple[EntityDependency, ...],
    evidence_refs: tuple[EntityEvidenceReference, ...],
    *,
    require_all: bool,
) -> None:
    label = "metric" if kind is EntityEvidenceKind.METRIC else "entity"
    for dependency in dependencies:
        matches = tuple(
            item
            for item in evidence_refs
            if item.kind is kind and (item.definition_id, item.version) == dependency.key
        )
        if require_all and dependency.required and not matches:
            raise ValueError(f"required {label} evidence is missing: {dependency.key!r}")
        if matches and not any(
            item.health in dependency.permitted_health
            and item.fidelity in dependency.permitted_fidelities
            for item in matches
        ):
            raise ValueError(
                f"{label} evidence is outside its permitted health/fidelity envelope: "
                f"{dependency.key!r}",
            )


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _text_tuple(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{label} values must be a tuple")
    return tuple(_required_text(item, label) for item in values)


def _typed_tuple(values: tuple[object, ...], expected: type[object], label: str) -> None:
    if not isinstance(values, tuple) or any(not isinstance(item, expected) for item in values):
        raise ValueError(f"{label} must contain only {expected.__name__} values")


def _unique(values, label: str) -> None:
    items = tuple(values)
    if len(items) != len(set(items)):
        raise ValueError(f"{label} values must be unique")


def _positive_int(value: object, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _non_negative_int(value: object, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _timestamp(value: object, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer timestamp")
