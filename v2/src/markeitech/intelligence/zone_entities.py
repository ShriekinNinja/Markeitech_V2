from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256

from markeitech.intelligence.entities import (
    EntityAdmissionStatus,
    EntityDefinition,
    EntityDurability,
    EntityEvidenceKind,
    EntityEvidenceReference,
    EntityIdentity,
    EntityIdentityDimension,
    EntityLifecycle,
    EntityPayload,
    EntityRegistry,
    EntityRevision,
    EntitySnapshot,
    EntityStateBook,
    EntityStateBookLimits,
)
from markeitech.intelligence.fvg_entities import FvgPayload
from markeitech.intelligence.market_structure_entities import ConfirmedSwingPayload
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth
from markeitech.intelligence.session_entities import ObjectiveLevelPayload

DERIVED_ZONE_ENTITY_TYPE = "derived_zone"
"""Canonical entity type for deterministic constituent-preserving zones."""

_ZONE_DIMENSIONS = (
    "application_id",
    "constituent_set_id",
    "definition_id",
    "policy_id",
    "policy_version",
)
_TERMINAL_LIFECYCLES = (EntityLifecycle.INVALIDATED, EntityLifecycle.EXPIRED)


class ZoneHorizonPolicy(StrEnum):
    """Policies governing whether a derived zone may mix source horizons."""

    SAME_HORIZON = "SAME_HORIZON"
    ALLOW_MIXED = "ALLOW_MIXED"


class ZoneWeightingMethod(StrEnum):
    """Approved methods for weighting zone constituents."""

    EQUAL = "EQUAL"


class ZonePartitionMethod(StrEnum):
    """Approved methods for partitioning ordered eligible constituents."""

    ORDERED_CONNECTED = "ORDERED_CONNECTED"


@dataclass(frozen=True, slots=True)
class ZoneConstituentReference:
    """Cite one exact source entity revision contributing to a derived zone."""

    entity_type: str
    entity_version: int
    entity_id: str
    revision: int
    lifecycle: EntityLifecycle
    horizon: str
    lower: Decimal
    upper: Decimal
    effective_ts_ns: int
    health: MetricHealth
    fidelity: MetricFidelity

    def __post_init__(self) -> None:
        for field in ("entity_type", "entity_id", "horizon"):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        _positive_int(self.entity_version, "entity_version")
        _positive_int(self.revision, "revision")
        if not isinstance(self.lifecycle, EntityLifecycle):
            raise ValueError("lifecycle must be EntityLifecycle")
        _finite_decimal(self.lower, "lower")
        _finite_decimal(self.upper, "upper")
        if self.lower > self.upper:
            raise ValueError("constituent lower cannot exceed upper")
        _timestamp(self.effective_ts_ns, "effective_ts_ns")
        if not isinstance(self.health, MetricHealth):
            raise ValueError("health must be MetricHealth")
        if not isinstance(self.fidelity, MetricFidelity):
            raise ValueError("fidelity must be MetricFidelity")


@dataclass(frozen=True, slots=True)
class DerivedZonePayload(EntityPayload):
    """Preserve zone bounds, policy, timing, horizons, and exact constituents."""

    definition_id: str
    policy_id: str
    policy_version: int
    application_id: str
    partition_method: ZonePartitionMethod
    weighting_method: ZoneWeightingMethod
    lower: Decimal
    upper: Decimal
    width: Decimal
    center: Decimal
    horizons: tuple[str, ...]
    constituents: tuple[ZoneConstituentReference, ...]
    created_ts_ns: int
    updated_ts_ns: int
    terminal_ts_ns: int | None

    def __post_init__(self) -> None:
        for field in ("definition_id", "policy_id", "application_id"):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        _positive_int(self.policy_version, "policy_version")
        if not isinstance(self.partition_method, ZonePartitionMethod):
            raise ValueError("partition_method must be ZonePartitionMethod")
        if not isinstance(self.weighting_method, ZoneWeightingMethod):
            raise ValueError("weighting_method must be ZoneWeightingMethod")
        for field in ("lower", "upper", "width", "center"):
            _finite_decimal(getattr(self, field), field)
        if self.lower >= self.upper:
            raise ValueError("zone lower must be smaller than upper")
        if self.width != self.upper - self.lower:
            raise ValueError("zone width must equal upper minus lower")
        if not self.lower <= self.center <= self.upper:
            raise ValueError("zone center must be inside its bounds")
        object.__setattr__(self, "horizons", _text_tuple(self.horizons, "horizons", True))
        object.__setattr__(
            self,
            "constituents",
            _typed_tuple(
                self.constituents,
                ZoneConstituentReference,
                "constituents",
                required=True,
            ),
        )
        constituent_ids = tuple(item.entity_id for item in self.constituents)
        if constituent_ids != tuple(sorted(constituent_ids)):
            raise ValueError("zone constituents must be ordered by entity ID")
        if len(constituent_ids) != len(set(constituent_ids)):
            raise ValueError("zone constituents must be unique")
        if self.horizons != tuple(sorted({item.horizon for item in self.constituents})):
            raise ValueError("zone horizons must exactly describe its constituents")
        _timestamp(self.created_ts_ns, "created_ts_ns")
        _timestamp(self.updated_ts_ns, "updated_ts_ns")
        if self.updated_ts_ns < self.created_ts_ns:
            raise ValueError("updated_ts_ns cannot precede created_ts_ns")
        if self.terminal_ts_ns is not None:
            _timestamp(self.terminal_ts_ns, "terminal_ts_ns")
            if self.terminal_ts_ns < self.updated_ts_ns:
                raise ValueError("terminal_ts_ns cannot precede updated_ts_ns")


@dataclass(frozen=True, slots=True)
class ZoneSourcePolicy:
    """Define eligible source entity type, horizons, and lifecycle states."""

    entity_type: str
    entity_version: int
    horizons: tuple[str, ...]
    lifecycles: tuple[EntityLifecycle, ...]
    include_developing: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_type", _required_text(self.entity_type, "entity_type"))
        _positive_int(self.entity_version, "entity_version")
        object.__setattr__(self, "horizons", _text_tuple(self.horizons, "horizons", True))
        object.__setattr__(
            self,
            "lifecycles",
            _typed_tuple(self.lifecycles, EntityLifecycle, "lifecycles", required=True),
        )
        if len(self.lifecycles) != len(set(self.lifecycles)):
            raise ValueError("source lifecycles must be unique")
        if not isinstance(self.include_developing, bool):
            raise ValueError("include_developing must be a boolean")

    @property
    def key(self) -> tuple[str, int]:
        return (self.entity_type, self.entity_version)


@dataclass(frozen=True, slots=True)
class ZonePolicy:
    """Configure zone sources, partitioning, geometry, age, and resource bounds."""

    policy_id: str
    version: int
    sources: tuple[ZoneSourcePolicy, ...]
    horizon_policy: ZoneHorizonPolicy
    partition_method: ZonePartitionMethod
    weighting_method: ZoneWeightingMethod
    withdrawn_outcome: EntityLifecycle
    merge_distance: Decimal
    merge_distance_floor: Decimal
    merge_distance_ceiling: Decimal
    merge_distance_step: Decimal
    merge_distance_dynamic: bool
    padding: Decimal
    padding_floor: Decimal
    padding_ceiling: Decimal
    padding_step: Decimal
    padding_dynamic: bool
    maximum_width: Decimal
    maximum_width_floor: Decimal
    maximum_width_ceiling: Decimal
    maximum_width_step: Decimal
    maximum_width_dynamic: bool
    minimum_constituents: int
    minimum_constituents_floor: int
    minimum_constituents_ceiling: int
    minimum_constituents_step: int
    minimum_constituents_dynamic: bool
    maximum_constituent_age_ns: int
    maximum_constituent_age_floor_ns: int
    maximum_constituent_age_ceiling_ns: int
    maximum_constituent_age_step_ns: int
    maximum_constituent_age_dynamic: bool
    maximum_retained_sources: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _required_text(self.policy_id, "policy_id"))
        _positive_int(self.version, "version")
        object.__setattr__(
            self,
            "sources",
            _typed_tuple(self.sources, ZoneSourcePolicy, "sources", required=True),
        )
        if len({item.key for item in self.sources}) != len(self.sources):
            raise ValueError("zone source policies must be unique")
        if not isinstance(self.horizon_policy, ZoneHorizonPolicy):
            raise ValueError("horizon_policy must be ZoneHorizonPolicy")
        if not isinstance(self.partition_method, ZonePartitionMethod):
            raise ValueError("partition_method must be ZonePartitionMethod")
        if not isinstance(self.weighting_method, ZoneWeightingMethod):
            raise ValueError("weighting_method must be ZoneWeightingMethod")
        if self.withdrawn_outcome not in _TERMINAL_LIFECYCLES:
            raise ValueError("withdrawn_outcome must be INVALIDATED or EXPIRED")
        _decimal_envelope(
            self.merge_distance,
            self.merge_distance_floor,
            self.merge_distance_ceiling,
            self.merge_distance_step,
            "merge_distance",
        )
        _decimal_envelope(
            self.padding,
            self.padding_floor,
            self.padding_ceiling,
            self.padding_step,
            "padding",
        )
        _decimal_envelope(
            self.maximum_width,
            self.maximum_width_floor,
            self.maximum_width_ceiling,
            self.maximum_width_step,
            "maximum_width",
            positive=True,
        )
        _integer_envelope(
            self.minimum_constituents,
            self.minimum_constituents_floor,
            self.minimum_constituents_ceiling,
            self.minimum_constituents_step,
            "minimum_constituents",
        )
        _integer_envelope(
            self.maximum_constituent_age_ns,
            self.maximum_constituent_age_floor_ns,
            self.maximum_constituent_age_ceiling_ns,
            self.maximum_constituent_age_step_ns,
            "maximum_constituent_age_ns",
        )
        for field in (
            "merge_distance_dynamic",
            "padding_dynamic",
            "maximum_width_dynamic",
            "minimum_constituents_dynamic",
            "maximum_constituent_age_dynamic",
        ):
            if not isinstance(getattr(self, field), bool):
                raise ValueError(f"{field} must be a boolean")
        _positive_int(self.maximum_retained_sources, "maximum_retained_sources")


@dataclass(frozen=True, slots=True)
class ZoneApplication:
    """Scope one zone policy to analytical profiles and optional instruments."""

    application_id: str
    analytical_profile_ids: tuple[str, ...]
    instrument_ids: tuple[str, ...]
    parameter_version: int
    policy: ZonePolicy

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "application_id",
            _required_text(self.application_id, "application_id"),
        )
        object.__setattr__(
            self,
            "analytical_profile_ids",
            _text_tuple(self.analytical_profile_ids, "analytical_profile_ids", True),
        )
        object.__setattr__(
            self,
            "instrument_ids",
            _text_tuple(self.instrument_ids, "instrument_ids"),
        )
        _positive_int(self.parameter_version, "parameter_version")
        if not isinstance(self.policy, ZonePolicy):
            raise ValueError("policy must be ZonePolicy")

    def matches(self, revision: EntityRevision) -> bool:
        return (
            revision.identity.analytical_profile_id in self.analytical_profile_ids
            and (not self.instrument_ids or revision.identity.instrument_id in self.instrument_ids)
            and revision.identity.key in {item.key for item in self.policy.sources}
        )


@dataclass(frozen=True, slots=True)
class DerivedZoneDefinition:
    """Bind a generic derived-zone definition to exact source definitions."""

    definition_id: str
    definition: EntityDefinition
    source_definitions: tuple[EntityDefinition, ...]
    applications: tuple[ZoneApplication, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "definition_id",
            _required_text(self.definition_id, "definition_id"),
        )
        if not isinstance(self.definition, EntityDefinition):
            raise ValueError("definition must be EntityDefinition")
        if self.definition.entity_type != DERIVED_ZONE_ENTITY_TYPE:
            raise ValueError("zone definition must use entity_type derived_zone")
        if self.definition.payload_type is not DerivedZonePayload:
            raise ValueError("zone definition must use DerivedZonePayload")
        if self.definition.identity_dimensions != tuple(sorted(_ZONE_DIMENSIONS)):
            raise ValueError("zone identity dimensions do not match the contract")
        if self.definition.metric_inputs:
            raise ValueError("derived zones consume entity revisions, not metrics")
        if self.definition.durability is not EntityDurability.TRANSIENT:
            raise ValueError("derived zones remain transient until persistence is approved")
        object.__setattr__(
            self,
            "source_definitions",
            _typed_tuple(
                self.source_definitions,
                EntityDefinition,
                "source_definitions",
                required=True,
            ),
        )
        source_keys = {item.key for item in self.source_definitions}
        dependency_keys = {item.key for item in self.definition.entity_inputs}
        if source_keys != dependency_keys:
            raise ValueError("source definitions must exactly match zone dependencies")
        object.__setattr__(
            self,
            "applications",
            _typed_tuple(self.applications, ZoneApplication, "applications", required=True),
        )
        if len({item.application_id for item in self.applications}) != len(self.applications):
            raise ValueError("zone application IDs must be unique")
        for application in self.applications:
            if {item.key for item in application.policy.sources} != dependency_keys:
                raise ValueError("every application must configure every zone dependency")


@dataclass(frozen=True, slots=True)
class DerivedZoneCounts:
    """Snapshot bounded zone-source admission, publication, and eviction counters."""

    sources_accepted: int
    sources_duplicate: int
    sources_stale: int
    sources_conflict: int
    sources_ineligible: int
    sources_evicted: int
    revisions_published: int
    revisions_duplicate: int
    revisions_rejected: int
    entities_evicted: int
    publications_deferred: int


type _Subject = tuple[str, str, str, str, int]


class DerivedZoneProjectionOwner:
    """Pure bounded owner for deterministic constituent-preserving zones."""

    def __init__(
        self,
        *,
        definitions: tuple[DerivedZoneDefinition, ...],
        limits: EntityStateBookLimits,
        maximum_publications_per_cycle: int,
        source: str,
        schema_version: int,
    ) -> None:
        specs = _typed_tuple(definitions, DerivedZoneDefinition, "definitions", required=True)
        _positive_int(maximum_publications_per_cycle, "maximum_publications_per_cycle")
        self._source = _required_text(source, "source")
        _positive_int(schema_version, "schema_version")
        self._schema_version = schema_version
        registered: dict[tuple[str, int], EntityDefinition] = {}
        for spec in specs:
            for definition in (*spec.source_definitions, spec.definition):
                existing = registered.get(definition.key)
                if existing is not None and existing != definition:
                    raise ValueError("conflicting entity definitions were registered")
                registered[definition.key] = definition
        self._definitions = specs
        metric_keys = {
            dependency.key
            for definition in registered.values()
            for dependency in definition.metric_inputs
        }
        self._registry = EntityRegistry(tuple(registered.values()), metric_keys=metric_keys)
        self._source_keys = frozenset(
            dependency.key for spec in specs for dependency in spec.definition.entity_inputs
        )
        self._book = EntityStateBook(self._registry, limits)
        self._maximum_publications = maximum_publications_per_cycle
        self._sources: dict[_Subject, dict[str, EntityRevision]] = {}
        self._active_zone_ids: dict[_Subject, set[str]] = {}
        self._pending: deque[EntityRevision] = deque()
        self._sources_accepted = 0
        self._sources_duplicate = 0
        self._sources_stale = 0
        self._sources_conflict = 0
        self._sources_ineligible = 0
        self._sources_evicted = 0
        self._revisions_published = 0
        self._revisions_duplicate = 0
        self._revisions_rejected = 0
        self._entities_evicted = 0
        self._publications_deferred = 0

    def ingest(self, revision: EntityRevision, *, now_ns: int) -> tuple[EntityRevision, ...]:
        if not isinstance(revision, EntityRevision):
            raise ValueError("zone input must be EntityRevision")
        _timestamp(now_ns, "now_ns")
        if revision.identity.key not in self._source_keys:
            self._sources_ineligible += 1
            return self._drain()
        self._registry.validate_revision(revision)
        matched = False
        for spec in self._definitions:
            for application in spec.applications:
                if not application.matches(revision):
                    continue
                matched = True
                subject = _subject(spec, application, revision)
                retained = self._sources.setdefault(subject, {})
                current = retained.get(revision.entity_id)
                if current is not None:
                    if revision.revision < current.revision:
                        self._sources_stale += 1
                        continue
                    if revision.revision == current.revision:
                        if revision == current:
                            self._sources_duplicate += 1
                        else:
                            self._sources_conflict += 1
                        continue
                retained[revision.entity_id] = revision
                self._sources_accepted += 1
                self._enforce_source_limit(retained, application.policy)
                self._reproject(spec, application, subject, retained, now_ns=now_ns)
        if not matched:
            self._sources_ineligible += 1
        return self._drain()

    def snapshot(
        self,
        generated_ts_ns: int,
        *,
        instrument_id: str | None = None,
        dimensions: Mapping[str, str] | None = None,
    ) -> EntitySnapshot:
        return self._book.snapshot(
            generated_ts_ns,
            instrument_id=instrument_id,
            entity_type=DERIVED_ZONE_ENTITY_TYPE,
            dimensions=dimensions,
        )

    @property
    def retained_sources(self) -> int:
        return sum(len(item) for item in self._sources.values())

    @property
    def retained_entities(self) -> int:
        return len(self._book)

    @property
    def counts(self) -> DerivedZoneCounts:
        return DerivedZoneCounts(
            self._sources_accepted,
            self._sources_duplicate,
            self._sources_stale,
            self._sources_conflict,
            self._sources_ineligible,
            self._sources_evicted,
            self._revisions_published,
            self._revisions_duplicate,
            self._revisions_rejected,
            self._entities_evicted,
            self._publications_deferred,
        )

    def _enforce_source_limit(
        self,
        retained: dict[str, EntityRevision],
        policy: ZonePolicy,
    ) -> None:
        ordered = sorted(
            retained.values(),
            key=lambda item: (item.effective_ts_ns, item.published_ts_ns, item.entity_id),
            reverse=True,
        )
        for stale in ordered[policy.maximum_retained_sources :]:
            retained.pop(stale.entity_id, None)
            self._sources_evicted += 1

    def _reproject(
        self,
        spec: DerivedZoneDefinition,
        application: ZoneApplication,
        subject: _Subject,
        retained: dict[str, EntityRevision],
        *,
        now_ns: int,
    ) -> None:
        latest_ts = max(item.effective_ts_ns for item in retained.values())
        constituents = tuple(
            item
            for item in (
                _constituent(revision, application.policy)
                for revision in retained.values()
                if latest_ts - revision.effective_ts_ns
                <= application.policy.maximum_constituent_age_ns
            )
            if item is not None
        )
        clusters = _clusters(constituents, application.policy)
        desired: dict[str, tuple[ZoneConstituentReference, ...]] = {}
        for cluster in clusters:
            identity = _zone_identity(spec, application, subject, cluster)
            desired[identity.entity_id] = cluster

        previous = self._active_zone_ids.get(subject, set())
        for entity_id in sorted(previous - desired.keys()):
            current = self._book.get(entity_id)
            if current is not None and current.lifecycle is EntityLifecycle.ACTIVE:
                self._admit(
                    _withdrawn_revision(
                        current,
                        application.policy,
                        transition_ts_ns=latest_ts,
                        now_ns=now_ns,
                    )
                )

        for entity_id, cluster in sorted(desired.items()):
            current = self._book.get(entity_id)
            candidate = _zone_revision(
                spec,
                application,
                subject,
                cluster,
                current=current,
                projection_ts_ns=latest_ts,
                now_ns=now_ns,
                source=self._source,
                schema_version=self._schema_version,
            )
            self._admit(candidate)

        self._active_zone_ids[subject] = {
            entity_id
            for entity_id in desired
            if (current := self._book.get(entity_id)) is not None
            and current.lifecycle is EntityLifecycle.ACTIVE
        }

    def _admit(self, revision: EntityRevision) -> None:
        admission = self._book.admit(revision)
        if admission.status in {EntityAdmissionStatus.ADDED, EntityAdmissionStatus.UPDATED}:
            self._entities_evicted += len(admission.evicted_entity_ids)
            self._pending.append(revision)
        elif admission.status is EntityAdmissionStatus.DUPLICATE:
            self._revisions_duplicate += 1
        else:
            self._revisions_rejected += 1

    def _drain(self) -> tuple[EntityRevision, ...]:
        revisions: list[EntityRevision] = []
        while self._pending and len(revisions) < self._maximum_publications:
            revisions.append(self._pending.popleft())
        self._revisions_published += len(revisions)
        if self._pending:
            self._publications_deferred += len(self._pending)
        return tuple(revisions)


def _constituent(
    revision: EntityRevision,
    policy: ZonePolicy,
) -> ZoneConstituentReference | None:
    source_policy = next(
        (item for item in policy.sources if item.key == revision.identity.key),
        None,
    )
    if source_policy is None or revision.lifecycle not in source_policy.lifecycles:
        return None
    payload = revision.payload
    if isinstance(payload, ObjectiveLevelPayload):
        if payload.developing and not source_policy.include_developing:
            return None
        horizon, lower, upper = payload.horizon, payload.lower, payload.upper
    elif isinstance(payload, ConfirmedSwingPayload):
        horizon = payload.horizon
        lower = upper = payload.pivot_price
    elif isinstance(payload, FvgPayload):
        horizon = payload.horizon
        lower, upper = payload.remaining_lower, payload.remaining_upper
    else:
        return None
    if horizon not in source_policy.horizons:
        return None
    return ZoneConstituentReference(
        revision.identity.entity_type,
        revision.identity.entity_version,
        revision.entity_id,
        revision.revision,
        revision.lifecycle,
        horizon,
        lower,
        upper,
        revision.effective_ts_ns,
        revision.health,
        revision.fidelity,
    )


def _clusters(
    constituents: tuple[ZoneConstituentReference, ...],
    policy: ZonePolicy,
) -> tuple[tuple[ZoneConstituentReference, ...], ...]:
    ordered = sorted(constituents, key=lambda item: (item.lower, item.upper, item.entity_id))
    clusters: list[list[ZoneConstituentReference]] = []
    for item in ordered:
        if not clusters or not _can_merge(tuple(clusters[-1]), item, policy):
            clusters.append([item])
        else:
            clusters[-1].append(item)
    return tuple(
        tuple(sorted(cluster, key=lambda item: item.entity_id))
        for cluster in clusters
        if len(cluster) >= policy.minimum_constituents
        and _padded_width(tuple(cluster), policy.padding) <= policy.maximum_width
    )


def _can_merge(
    cluster: tuple[ZoneConstituentReference, ...],
    item: ZoneConstituentReference,
    policy: ZonePolicy,
) -> bool:
    if policy.horizon_policy is ZoneHorizonPolicy.SAME_HORIZON:
        if any(existing.horizon != item.horizon for existing in cluster):
            return False
    lower = min(existing.lower for existing in cluster)
    upper = max(existing.upper for existing in cluster)
    distance = max(Decimal(0), item.lower - upper, lower - item.upper)
    proposed = (*cluster, item)
    return (
        distance <= policy.merge_distance
        and _padded_width(proposed, policy.padding) <= policy.maximum_width
    )


def _padded_width(
    constituents: tuple[ZoneConstituentReference, ...],
    padding: Decimal,
) -> Decimal:
    lower = min(item.lower for item in constituents) - padding
    upper = max(item.upper for item in constituents) + padding
    return upper - lower


def _zone_identity(
    spec: DerivedZoneDefinition,
    application: ZoneApplication,
    subject: _Subject,
    constituents: tuple[ZoneConstituentReference, ...],
) -> EntityIdentity:
    constituent_set_id = sha256(
        "|".join(item.entity_id for item in constituents).encode("ascii")
    ).hexdigest()
    return EntityIdentity(
        entity_type=DERIVED_ZONE_ENTITY_TYPE,
        entity_version=spec.definition.version,
        instrument_id=subject[2],
        analytical_profile_id=subject[3],
        analytical_profile_version=subject[4],
        dimensions=(
            EntityIdentityDimension("application_id", application.application_id),
            EntityIdentityDimension("constituent_set_id", constituent_set_id),
            EntityIdentityDimension("definition_id", spec.definition_id),
            EntityIdentityDimension("policy_id", application.policy.policy_id),
            EntityIdentityDimension("policy_version", str(application.policy.version)),
        ),
    )


def _zone_revision(
    spec: DerivedZoneDefinition,
    application: ZoneApplication,
    subject: _Subject,
    constituents: tuple[ZoneConstituentReference, ...],
    *,
    current: EntityRevision | None,
    projection_ts_ns: int,
    now_ns: int,
    source: str,
    schema_version: int,
) -> EntityRevision:
    identity = _zone_identity(spec, application, subject, constituents)
    lower = min(item.lower for item in constituents) - application.policy.padding
    upper = max(item.upper for item in constituents) + application.policy.padding
    center = sum((item.lower + item.upper) / 2 for item in constituents) / len(constituents)
    constituent_ts_ns = max(item.effective_ts_ns for item in constituents)
    effective_ts_ns = (
        max(constituent_ts_ns, projection_ts_ns)
        if current is not None and current.lifecycle is not EntityLifecycle.ACTIVE
        else constituent_ts_ns
    )
    current_payload = current.payload if current is not None else None
    created_ts_ns = (
        current_payload.created_ts_ns
        if isinstance(current_payload, DerivedZonePayload)
        else effective_ts_ns
    )
    payload = DerivedZonePayload(
        spec.definition_id,
        application.policy.policy_id,
        application.policy.version,
        application.application_id,
        application.policy.partition_method,
        application.policy.weighting_method,
        lower,
        upper,
        upper - lower,
        center,
        tuple(sorted({item.horizon for item in constituents})),
        constituents,
        created_ts_ns,
        effective_ts_ns,
        None,
    )
    health = _least_healthy(tuple(item.health for item in constituents))
    fidelity = _least_fidelity(tuple(item.fidelity for item in constituents))
    published_ts_ns = max(now_ns, effective_ts_ns)
    return EntityRevision(
        identity,
        1 if current is None else current.revision + 1,
        application.parameter_version,
        payload,
        EntityLifecycle.ACTIVE,
        effective_ts_ns,
        effective_ts_ns,
        published_ts_ns,
        published_ts_ns,
        health,
        fidelity,
        tuple(
            EntityEvidenceReference(
                EntityEvidenceKind.ENTITY,
                item.entity_type,
                item.entity_id,
                item.entity_version,
                item.revision,
                item.effective_ts_ns,
                item.health,
                item.fidelity,
            )
            for item in constituents
        ),
        (),
        (),
        source,
        schema_version,
        None if current is None else current.revision,
    )


def _withdrawn_revision(
    current: EntityRevision,
    policy: ZonePolicy,
    *,
    transition_ts_ns: int,
    now_ns: int,
) -> EntityRevision:
    _timestamp(transition_ts_ns, "transition_ts_ns")
    payload = current.payload
    if not isinstance(payload, DerivedZonePayload):
        raise RuntimeError("active derived zone lost its payload")
    effective_ts_ns = max(current.effective_ts_ns, transition_ts_ns)
    published_ts_ns = max(now_ns, current.published_ts_ns, effective_ts_ns)
    terminal_payload = replace(
        payload,
        updated_ts_ns=max(payload.updated_ts_ns, effective_ts_ns),
        terminal_ts_ns=max(payload.updated_ts_ns, effective_ts_ns),
    )
    return EntityRevision(
        current.identity,
        current.revision + 1,
        current.parameter_version,
        terminal_payload,
        policy.withdrawn_outcome,
        effective_ts_ns,
        current.observed_ts_ns,
        published_ts_ns,
        published_ts_ns,
        current.health,
        current.fidelity,
        current.evidence_refs,
        current.missing_reasons,
        current.conflict_reasons,
        current.source,
        current.schema_version,
        current.revision,
    )


def _subject(
    spec: DerivedZoneDefinition,
    application: ZoneApplication,
    revision: EntityRevision,
) -> _Subject:
    return (
        spec.definition_id,
        application.application_id,
        revision.identity.instrument_id,
        revision.identity.analytical_profile_id,
        revision.identity.analytical_profile_version,
    )


def _decimal_envelope(
    value: Decimal,
    minimum: Decimal,
    maximum: Decimal,
    step: Decimal,
    field: str,
    *,
    positive: bool = False,
) -> None:
    for candidate in (value, minimum, maximum, step):
        _finite_decimal(candidate, field)
    if minimum < 0 or step <= 0 or (positive and minimum <= 0):
        raise ValueError(f"{field} envelope has invalid bounds")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field} is outside its configured envelope")
    if (value - minimum) % step:
        raise ValueError(f"{field} does not align to its configured step")


def _integer_envelope(value: int, minimum: int, maximum: int, step: int, field: str) -> None:
    for candidate in (value, minimum, maximum, step):
        _positive_int(candidate, field)
    if not minimum <= value <= maximum:
        raise ValueError(f"{field} is outside its configured envelope")
    if (value - minimum) % step:
        raise ValueError(f"{field} does not align to its configured step")


def _least_healthy(values: tuple[MetricHealth, ...]) -> MetricHealth:
    order = {
        MetricHealth.READY: 0,
        MetricHealth.WARMING: 1,
        MetricHealth.DEGRADED: 2,
        MetricHealth.STALE: 3,
        MetricHealth.UNAVAILABLE: 4,
        MetricHealth.UNSUPPORTED: 5,
        MetricHealth.FAILED: 6,
    }
    return max(values, key=order.__getitem__)


def _least_fidelity(values: tuple[MetricFidelity, ...]) -> MetricFidelity:
    order = {
        MetricFidelity.REPORTED: 0,
        MetricFidelity.DERIVED: 1,
        MetricFidelity.INFERRED: 2,
        MetricFidelity.PARTIAL: 3,
        MetricFidelity.UNAVAILABLE: 4,
    }
    return max(values, key=order.__getitem__)


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _timestamp(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _finite_decimal(value: object, field: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{field} must be a finite Decimal")
    return value


def _text_tuple(
    values: object,
    field: str,
    required: bool = False,
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{field} must be a tuple")
    normalized = tuple(_required_text(item, field) for item in values)
    if required and not normalized:
        raise ValueError(f"{field} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field} must contain unique values")
    return normalized


def _typed_tuple(
    values: object,
    item_type: type,
    field: str,
    *,
    required: bool = False,
) -> tuple:
    if not isinstance(values, tuple) or any(not isinstance(item, item_type) for item in values):
        raise ValueError(f"{field} must be a tuple of {item_type.__name__}")
    if required and not values:
        raise ValueError(f"{field} must not be empty")
    return values
