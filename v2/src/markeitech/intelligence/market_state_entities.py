from __future__ import annotations

import re
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType

from markeitech.intelligence.entities import (
    EntityAdmissionStatus,
    EntityDefinition,
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
from markeitech.intelligence.market_states import (
    CompressionExpansionStatePayload,
    DirectionalStatePayload,
    ReferenceStatePayload,
    ScalarStateEvidence,
    StateClassification,
    StateClassificationMemory,
    StateClassificationPolicy,
    VolatilityStatePayload,
    classify_state,
)
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth, MetricValue

VOLATILITY_STATE_GROUP = "volatility_compression_expansion"
DIRECTION_STATE_GROUP = "direction_trend_rotation_reference"
MARKET_STATE_GROUPS = frozenset({VOLATILITY_STATE_GROUP, DIRECTION_STATE_GROUP})

_TRADE_DATE_PATTERN = re.compile(r"(?:^|:)(\d{4}-\d{2}-\d{2})(?::|$)")
_SUPPORTED_ENTITY_TYPES = {
    "compression_expansion_state": CompressionExpansionStatePayload,
    "directional_state": DirectionalStatePayload,
    "volatility_state": VolatilityStatePayload,
}
_HEALTH_ORDER = {
    MetricHealth.READY: 0,
    MetricHealth.WARMING: 1,
    MetricHealth.DEGRADED: 2,
    MetricHealth.STALE: 3,
    MetricHealth.UNAVAILABLE: 4,
    MetricHealth.UNSUPPORTED: 5,
    MetricHealth.FAILED: 6,
}
_FIDELITY_ORDER = {
    MetricFidelity.REPORTED: 0,
    MetricFidelity.DERIVED: 1,
    MetricFidelity.INFERRED: 2,
    MetricFidelity.PARTIAL: 3,
    MetricFidelity.UNAVAILABLE: 4,
}


@dataclass(frozen=True, slots=True)
class MarketStateApplication:
    application_id: str
    analytical_profile_ids: tuple[str, ...]
    instrument_ids: tuple[str, ...]
    session_phases: tuple[str, ...]
    horizon: str

    def __post_init__(self) -> None:
        for field in ("application_id", "horizon"):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        object.__setattr__(
            self,
            "analytical_profile_ids",
            _text_tuple(self.analytical_profile_ids, "analytical_profile_ids", required=True),
        )
        object.__setattr__(
            self,
            "instrument_ids",
            _text_tuple(self.instrument_ids, "instrument_ids"),
        )
        object.__setattr__(
            self,
            "session_phases",
            _text_tuple(self.session_phases, "session_phases", required=True),
        )


@dataclass(frozen=True, slots=True)
class MarketStatePolicyBinding:
    axis: str
    measure_role: str
    coverage_role: str
    policy: StateClassificationPolicy

    def __post_init__(self) -> None:
        for field in ("axis", "measure_role", "coverage_role"):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        if not isinstance(self.policy, StateClassificationPolicy):
            raise ValueError("policy must be StateClassificationPolicy")


@dataclass(frozen=True, slots=True)
class MarketStateDefinition:
    definition_id: str
    group: str
    definition: EntityDefinition
    metric_roles: Mapping[tuple[str, int], str]
    parameter_set_id: str
    parameter_version: int
    policy_bindings: tuple[MarketStatePolicyBinding, ...]
    applications: tuple[MarketStateApplication, ...]
    normalization: str | None = None
    reference_id: str | None = None
    reference_kind: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "definition_id",
            _required_text(self.definition_id, "definition_id"),
        )
        object.__setattr__(self, "group", _required_text(self.group, "group"))
        if self.group not in MARKET_STATE_GROUPS:
            raise ValueError(f"unsupported market-state group: {self.group}")
        if not isinstance(self.definition, EntityDefinition):
            raise ValueError("definition must be EntityDefinition")
        if self.definition.entity_inputs:
            raise ValueError("9D.4B market-state definitions cannot consume entity revisions")
        _positive_int(self.parameter_version, "parameter_version")
        object.__setattr__(
            self,
            "parameter_set_id",
            _required_text(self.parameter_set_id, "parameter_set_id"),
        )
        roles = {
            key: _required_text(role, "metric role") for key, role in self.metric_roles.items()
        }
        if set(roles) != {item.key for item in self.definition.metric_inputs}:
            raise ValueError("metric_roles must bind every declared metric dependency exactly once")
        normalized_roles = tuple(roles.values())
        if len(normalized_roles) != len(set(normalized_roles)):
            raise ValueError("market-state metric roles must be unique")
        object.__setattr__(self, "metric_roles", MappingProxyType(roles))
        _typed_tuple(self.policy_bindings, MarketStatePolicyBinding, "policy_bindings")
        _typed_tuple(self.applications, MarketStateApplication, "applications")
        if not self.policy_bindings or not self.applications:
            raise ValueError("market-state definitions require policies and applications")
        axes = tuple(item.axis for item in self.policy_bindings)
        if len(axes) != len(set(axes)):
            raise ValueError("market-state policy axes must be unique")
        role_to_key = {role: key for key, role in roles.items()}
        required_roles = {
            roles[item.key] for item in self.definition.metric_inputs if item.required
        }
        for binding in self.policy_bindings:
            if binding.measure_role not in role_to_key:
                raise ValueError(f"unknown policy measure role: {binding.measure_role}")
            if binding.coverage_role not in role_to_key:
                raise ValueError(f"unknown policy coverage role: {binding.coverage_role}")
            measure_key = role_to_key[binding.measure_role]
            if binding.policy.measure_id != measure_key[0]:
                raise ValueError("policy measure_id must match its bound metric role")
            if binding.policy.parameter_version != self.parameter_version:
                raise ValueError("policy and entity parameter versions must match")
            if binding.measure_role not in required_roles:
                raise ValueError("policy measure role must be a required metric dependency")
            if binding.coverage_role not in required_roles:
                raise ValueError("policy coverage role must be a required metric dependency")
        required_output_health = {
            MetricHealth.WARMING,
            MetricHealth.DEGRADED,
            MetricHealth.STALE,
            MetricHealth.UNAVAILABLE,
            *(
                health
                for binding in self.policy_bindings
                for health in binding.policy.permitted_health
            ),
        }
        if not required_output_health <= set(self.definition.permitted_health):
            raise ValueError(
                "market-state entity health envelope cannot represent every policy outcome",
            )
        required_output_fidelities = {
            MetricFidelity.PARTIAL,
            *(
                fidelity
                for binding in self.policy_bindings
                for fidelity in binding.policy.permitted_fidelities
            ),
        }
        if not required_output_fidelities <= set(self.definition.permitted_fidelities):
            raise ValueError(
                "market-state entity fidelity envelope cannot represent every policy outcome",
            )
        _validate_family_contract(self, set(normalized_roles), set(axes))

    def matching_applications(
        self,
        instrument_id: str,
        profile_id: str,
        session_phase: str,
    ) -> tuple[MarketStateApplication, ...]:
        return tuple(
            application
            for application in self.applications
            if profile_id in application.analytical_profile_ids
            and (not application.instrument_ids or instrument_id in application.instrument_ids)
            and session_phase in application.session_phases
        )


@dataclass(frozen=True, slots=True)
class MarketStateOwnerCounts:
    metrics_accepted: int
    metrics_duplicate: int
    metrics_stale: int
    metrics_conflict: int
    revisions_published: int
    revisions_duplicate: int
    revisions_rejected: int
    publications_deferred: int
    staleness_reconciliations: int


@dataclass(frozen=True, slots=True)
class _ClassificationRecord:
    signature: tuple[object, ...]
    classification: StateClassification
    memory: StateClassificationMemory


@dataclass(frozen=True, slots=True)
class _ProjectionSubject:
    spec: MarketStateDefinition
    application: MarketStateApplication
    instrument_id: str
    session_id: str


class MarketStateProjectionOwner:
    """Bounded, actor-independent owner for metric-driven Stage 9D.4 state."""

    def __init__(
        self,
        *,
        definitions: tuple[MarketStateDefinition, ...],
        instrument_profiles: Mapping[str, tuple[str, int]],
        limits: EntityStateBookLimits,
        maximum_metric_values: int,
        maximum_publications_per_cycle: int,
        source: str,
        schema_version: int,
    ) -> None:
        _typed_tuple(definitions, MarketStateDefinition, "definitions")
        if not definitions:
            raise ValueError("market-state owner requires definitions")
        _positive_int(maximum_metric_values, "maximum_metric_values")
        _positive_int(maximum_publications_per_cycle, "maximum_publications_per_cycle")
        self._definitions = definitions
        self._profiles = MappingProxyType(dict(instrument_profiles))
        registry = EntityRegistry(
            tuple(item.definition for item in definitions),
            metric_keys={
                dependency.key
                for item in definitions
                for dependency in item.definition.metric_inputs
            },
        )
        self._book = EntityStateBook(registry, limits)
        self._maximum_metric_values = maximum_metric_values
        self._maximum_publications = maximum_publications_per_cycle
        self._source = _required_text(source, "source")
        self._schema_version = _positive_int(schema_version, "schema_version")
        self._metrics: dict[tuple[str, str, str, int, int], MetricValue] = {}
        self._classification: dict[tuple[str, str], _ClassificationRecord] = {}
        self._subjects: dict[str, _ProjectionSubject] = {}
        self._pending: deque[EntityRevision] = deque()
        self._metrics_accepted = 0
        self._metrics_duplicate = 0
        self._metrics_stale = 0
        self._metrics_conflict = 0
        self._revisions_published = 0
        self._revisions_duplicate = 0
        self._revisions_rejected = 0
        self._publications_deferred = 0
        self._staleness_reconciliations = 0

    def ingest(self, value: MetricValue, *, now_ns: int) -> tuple[EntityRevision, ...]:
        if not isinstance(value, MetricValue):
            raise ValueError("market-state input must be MetricValue")
        _non_negative_int(now_ns, "now_ns")
        if value.instrument_id not in self._profiles or value.session_id is None:
            return self._drain()
        session_phase = _session_phase(value.session_id)
        profile_id = self._profiles[value.instrument_id][0]
        relevant = tuple(
            (spec, application)
            for spec in self._definitions
            if value.key in spec.metric_roles and value.parameter_version == spec.parameter_version
            for application in spec.matching_applications(
                value.instrument_id,
                profile_id,
                session_phase,
            )
        )
        if not relevant:
            return self._drain()
        key = _metric_key(value)
        current = self._metrics.get(key)
        if current is not None:
            if value.revision < current.revision or value.published_ts_ns < current.published_ts_ns:
                self._metrics_stale += 1
                return self._drain()
            if value.revision == current.revision:
                if value == current:
                    self._metrics_duplicate += 1
                else:
                    self._metrics_conflict += 1
                return self._drain()
        self._metrics[key] = value
        self._metrics_accepted += 1
        self._trim_metrics()

        for spec, application in relevant:
            revision = self._project(
                spec,
                application,
                value.instrument_id,
                value.session_id,
                now_ns=now_ns,
            )
            if revision is not None:
                self._admit(revision)
        return self._drain()

    def reconcile(self, *, now_ns: int) -> tuple[EntityRevision, ...]:
        _non_negative_int(now_ns, "now_ns")
        for entity_id, subject in tuple(self._subjects.items()):
            current = self._book.get(entity_id)
            if current is None or current.lifecycle is EntityLifecycle.STALE:
                continue
            values = self._subject_values(
                subject.spec,
                subject.instrument_id,
                subject.session_id,
            )
            if not _has_stale_policy_evidence(subject.spec, values, now_ns):
                continue
            revision = self._project(
                subject.spec,
                subject.application,
                subject.instrument_id,
                subject.session_id,
                now_ns=now_ns,
                force_stale=True,
            )
            if revision is not None:
                self._staleness_reconciliations += 1
                self._admit(revision)
        return self._drain()

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
        return self._book.snapshot(
            generated_ts_ns,
            instrument_id=instrument_id,
            entity_type=entity_type,
            analytical_profile_id=analytical_profile_id,
            analytical_profile_version=analytical_profile_version,
            dimensions=dimensions,
            lifecycles=lifecycles,
        )

    @property
    def counts(self) -> MarketStateOwnerCounts:
        return MarketStateOwnerCounts(
            self._metrics_accepted,
            self._metrics_duplicate,
            self._metrics_stale,
            self._metrics_conflict,
            self._revisions_published,
            self._revisions_duplicate,
            self._revisions_rejected,
            self._publications_deferred,
            self._staleness_reconciliations,
        )

    @property
    def retained_metric_values(self) -> int:
        return len(self._metrics)

    @property
    def pending_publications(self) -> int:
        return len(self._pending)

    def _project(
        self,
        spec: MarketStateDefinition,
        application: MarketStateApplication,
        instrument_id: str,
        session_id: str,
        *,
        now_ns: int,
        force_stale: bool = False,
    ) -> EntityRevision | None:
        values = self._subject_values(spec, instrument_id, session_id)
        context = _identity_context(spec, application, session_id)
        profile_id, profile_version = self._profiles[instrument_id]
        try:
            identity = EntityIdentity(
                entity_type=spec.definition.entity_type,
                entity_version=spec.definition.version,
                instrument_id=instrument_id,
                analytical_profile_id=profile_id,
                analytical_profile_version=profile_version,
                dimensions=tuple(
                    EntityIdentityDimension(name, context[name])
                    for name in spec.definition.identity_dimensions
                ),
            )
        except KeyError as exc:
            raise ValueError(
                f"unsupported identity dimension for {spec.definition_id}: {exc.args[0]}",
            ) from exc
        self._subjects[identity.entity_id] = _ProjectionSubject(
            spec,
            application,
            instrument_id,
            session_id,
        )
        usable, missing = _usable_evidence(spec, values)
        current = self._book.get(identity.entity_id)
        classifications: dict[str, StateClassification] = {}
        payload: EntityPayload | None = None
        if not missing:
            for binding in spec.policy_bindings:
                classifications[binding.axis] = self._classify(
                    identity.entity_id,
                    binding,
                    usable,
                    now_ns=now_ns,
                    force_stale=force_stale,
                )
            payload = _payload(spec, application, usable, classifications)
        health = _entity_health(usable, missing, tuple(classifications.values()))
        fidelity = _entity_fidelity(usable, missing)
        lifecycle = _entity_lifecycle(payload, health, tuple(classifications.values()))
        evidence = tuple(_evidence_reference(item) for item in usable.values())
        observed_ns = max((item.observed_ts_ns for item in usable.values()), default=now_ns)
        calculated_ns = max(
            now_ns,
            observed_ns,
            *(item.calculated_ts_ns for item in usable.values()),
        )
        published_ns = max(
            calculated_ns,
            *(item.published_ts_ns for item in usable.values()),
        )
        effective_ns = max((item.effective_ts_ns for item in usable.values()), default=now_ns)
        return EntityRevision(
            identity=identity,
            revision=1 if current is None else current.revision + 1,
            parameter_version=spec.parameter_version,
            payload=payload,
            lifecycle=lifecycle,
            effective_ts_ns=effective_ns,
            observed_ts_ns=observed_ns,
            calculated_ts_ns=calculated_ns,
            published_ts_ns=published_ns,
            health=health,
            fidelity=fidelity,
            evidence_refs=evidence,
            missing_reasons=tuple(missing),
            conflict_reasons=(),
            source=self._source,
            schema_version=self._schema_version,
            previous_revision=None if current is None else current.revision,
        )

    def _classify(
        self,
        entity_id: str,
        binding: MarketStatePolicyBinding,
        values: Mapping[str, MetricValue],
        *,
        now_ns: int,
        force_stale: bool,
    ) -> StateClassification:
        measure = values[binding.measure_role]
        coverage = values[binding.coverage_role]
        evidence = _scalar_evidence(measure, coverage)
        key = (entity_id, binding.axis)
        signature = (
            measure.metric_id,
            measure.metric_version,
            measure.parameter_version,
            measure.revision,
            measure.value,
            coverage.metric_id,
            coverage.metric_version,
            coverage.parameter_version,
            coverage.revision,
            coverage.value,
        )
        prior = self._classification.get(key)
        if prior is not None and prior.signature == signature and not force_stale:
            return prior.classification
        prior_memory = None if prior is None else prior.memory
        if force_stale or (
            prior_memory is not None
            and prior_memory.last_evidence_ts_ns is not None
            and evidence.effective_ts_ns <= prior_memory.last_evidence_ts_ns
        ):
            prior_memory = None
        classification, memory = classify_state(
            evidence,
            binding.policy,
            prior_memory,
            now_ns=now_ns,
        )
        self._classification[key] = _ClassificationRecord(signature, classification, memory)
        return classification

    def _subject_values(
        self,
        spec: MarketStateDefinition,
        instrument_id: str,
        session_id: str,
    ) -> dict[str, MetricValue]:
        result: dict[str, MetricValue] = {}
        for dependency in spec.definition.metric_inputs:
            candidate = self._metrics.get(
                (
                    instrument_id,
                    session_id,
                    dependency.metric_id,
                    dependency.metric_version,
                    spec.parameter_version,
                ),
            )
            if candidate is not None:
                result[spec.metric_roles[dependency.key]] = candidate
        return result

    def _trim_metrics(self) -> None:
        while len(self._metrics) > self._maximum_metric_values:
            oldest = min(
                self._metrics,
                key=lambda key: (
                    self._metrics[key].published_ts_ns,
                    self._metrics[key].effective_ts_ns,
                    key,
                ),
            )
            del self._metrics[oldest]

    def _admit(self, revision: EntityRevision) -> None:
        if len(self._pending) >= self._maximum_metric_values:
            self._revisions_rejected += 1
            return
        admission = self._book.admit(revision)
        if admission.status in {EntityAdmissionStatus.ADDED, EntityAdmissionStatus.UPDATED}:
            for entity_id in admission.evicted_entity_ids:
                self._discard_entity_runtime(entity_id)
            self._pending.append(revision)
        elif admission.status is EntityAdmissionStatus.DUPLICATE:
            self._revisions_duplicate += 1
        else:
            self._revisions_rejected += 1
            if admission.current is None:
                self._discard_entity_runtime(revision.entity_id)

    def _discard_entity_runtime(self, entity_id: str) -> None:
        self._subjects.pop(entity_id, None)
        for key in tuple(self._classification):
            if key[0] == entity_id:
                del self._classification[key]

    def _drain(self) -> tuple[EntityRevision, ...]:
        published: list[EntityRevision] = []
        while self._pending and len(published) < self._maximum_publications:
            published.append(self._pending.popleft())
        self._revisions_published += len(published)
        if self._pending:
            self._publications_deferred += len(self._pending)
        return tuple(published)


def payload_type_for_market_state(entity_type: str) -> type[EntityPayload]:
    normalized = _required_text(entity_type, "entity_type")
    if normalized.startswith("reference_state."):
        return ReferenceStatePayload
    try:
        return _SUPPORTED_ENTITY_TYPES[normalized]
    except KeyError as exc:
        if normalized == "trend_rotation_state":
            raise ValueError(
                "trend_rotation_state requires the later cross-entity reconciliation batch",
            ) from exc
        raise ValueError(f"unsupported Stage 9D.4B entity type: {normalized}") from exc


def _validate_family_contract(
    spec: MarketStateDefinition,
    roles: set[str],
    axes: set[str],
) -> None:
    entity_type = spec.definition.entity_type
    expected_payload = payload_type_for_market_state(entity_type)
    if spec.definition.payload_type is not expected_payload:
        raise ValueError("market-state payload type does not match entity family")
    expected_axes = (
        {"slope", "separation"}
        if entity_type.startswith("reference_state.")
        else {"primary"}
    )
    if axes != expected_axes:
        raise ValueError(f"{entity_type} requires policy axes {sorted(expected_axes)!r}")
    required_roles = {"coverage_ratio"}
    if entity_type == "compression_expansion_state":
        required_roles.update(
            {
                "phase_duration_observations",
                "phase_reference_count",
                "recent_reference_count",
            },
        )
    missing_roles = required_roles - roles
    if missing_roles:
        raise ValueError(f"{entity_type} lacks required roles: {sorted(missing_roles)!r}")
    if entity_type == "volatility_state":
        object.__setattr__(
            spec,
            "normalization",
            _required_text(spec.normalization, "normalization"),
        )
    elif entity_type.startswith("reference_state."):
        object.__setattr__(spec, "reference_id", _required_text(spec.reference_id, "reference_id"))
        object.__setattr__(
            spec,
            "reference_kind",
            _required_text(spec.reference_kind, "reference_kind"),
        )


def _payload(
    spec: MarketStateDefinition,
    application: MarketStateApplication,
    values: Mapping[str, MetricValue],
    classifications: Mapping[str, StateClassification],
) -> EntityPayload:
    entity_type = spec.definition.entity_type
    primary = classifications.get("primary")
    if entity_type == "volatility_state":
        assert primary is not None and spec.normalization is not None
        return VolatilityStatePayload(
            application.horizon,
            _optional_decimal(values, "average_true_range"),
            _optional_decimal(values, "realized_range"),
            _optional_decimal(values, "realized_return_magnitude"),
            primary.measure_value,
            spec.normalization,
            _decimal(values, "coverage_ratio"),
            primary,
        )
    if entity_type == "compression_expansion_state":
        assert primary is not None
        return CompressionExpansionStatePayload(
            application.horizon,
            _optional_decimal(values, "expansion_ratio_recent"),
            _optional_decimal(values, "expansion_ratio_phase"),
            _optional_decimal(values, "range_percentile_recent"),
            _optional_decimal(values, "range_percentile_phase"),
            _integer(values, "recent_reference_count"),
            _integer(values, "phase_reference_count"),
            _decimal(values, "coverage_ratio"),
            _integer(values, "phase_duration_observations"),
            primary,
        )
    if entity_type == "directional_state":
        assert primary is not None
        return DirectionalStatePayload(
            application.horizon,
            _optional_decimal(values, "signed_displacement"),
            _optional_decimal(values, "signed_simple_return"),
            _optional_decimal(values, "signed_path_efficiency"),
            _decimal(values, "coverage_ratio"),
            primary,
        )
    if entity_type.startswith("reference_state."):
        assert spec.reference_id is not None and spec.reference_kind is not None
        return ReferenceStatePayload(
            application.horizon,
            spec.reference_id,
            spec.reference_kind,
            _optional_decimal(values, "reference_value"),
            _optional_decimal(values, "slope_per_bar"),
            _optional_decimal(values, "price_separation"),
            classifications["slope"],
            classifications["separation"],
        )
    raise ValueError(f"unsupported Stage 9D.4B entity type: {entity_type}")


def _usable_evidence(
    spec: MarketStateDefinition,
    values: Mapping[str, MetricValue],
) -> tuple[dict[str, MetricValue], list[str]]:
    usable: dict[str, MetricValue] = {}
    missing: list[str] = []
    for dependency in spec.definition.metric_inputs:
        role = spec.metric_roles[dependency.key]
        value = values.get(role)
        valid = (
            value is not None
            and value.value is not None
            and value.health in dependency.permitted_health
            and value.fidelity in dependency.permitted_fidelities
        )
        if valid:
            usable[role] = value
        elif dependency.required:
            missing.append(f"required_metric_unavailable:{role}")
    return usable, missing


def _scalar_evidence(measure: MetricValue, coverage: MetricValue) -> ScalarStateEvidence:
    return ScalarStateEvidence(
        value=_metric_decimal(measure),
        coverage_ratio=_metric_decimal(coverage),
        effective_ts_ns=max(measure.effective_ts_ns, coverage.effective_ts_ns),
        health=_worst_health((measure.health, coverage.health)),
        fidelity=_worst_fidelity((measure.fidelity, coverage.fidelity)),
        evidence_refs=tuple(
            sorted(
                {
                    _metric_reference_id(measure),
                    _metric_reference_id(coverage),
                    *measure.evidence_refs,
                    *coverage.evidence_refs,
                },
            ),
        ),
        missing_reasons=tuple(sorted({*measure.missing_reasons, *coverage.missing_reasons})),
    )


def _entity_health(
    values: Mapping[str, MetricValue],
    missing: list[str],
    classifications: tuple[StateClassification, ...],
) -> MetricHealth:
    if missing:
        return MetricHealth.WARMING
    return _worst_health(
        (
            *(item.health for item in values.values()),
            *(item.health for item in classifications),
        ),
    )


def _entity_fidelity(values: Mapping[str, MetricValue], missing: list[str]) -> MetricFidelity:
    if missing:
        return MetricFidelity.PARTIAL
    return _worst_fidelity(tuple(item.fidelity for item in values.values()))


def _entity_lifecycle(
    payload: EntityPayload | None,
    health: MetricHealth,
    classifications: tuple[StateClassification, ...],
) -> EntityLifecycle:
    if payload is None:
        return EntityLifecycle.WARMING
    if health is MetricHealth.STALE:
        return EntityLifecycle.STALE
    if any(not item.confirmed for item in classifications):
        return EntityLifecycle.WARMING
    if health is not MetricHealth.READY:
        return EntityLifecycle.DEGRADED
    return EntityLifecycle.ACTIVE


def _evidence_reference(value: MetricValue) -> EntityEvidenceReference:
    return EntityEvidenceReference(
        kind=EntityEvidenceKind.METRIC,
        definition_id=value.metric_id,
        reference_id=_metric_reference_id(value),
        version=value.metric_version,
        revision=value.revision,
        effective_ts_ns=value.effective_ts_ns,
        health=value.health,
        fidelity=value.fidelity,
    )


def _metric_reference_id(value: MetricValue) -> str:
    return (
        f"metric:{value.metric_id}:{value.instrument_id}:{value.session_id or 'none'}:"
        f"{value.parameter_version}:{value.revision}"
    )


def _metric_key(value: MetricValue) -> tuple[str, str, str, int, int]:
    assert value.session_id is not None
    return (
        value.instrument_id,
        value.session_id,
        value.metric_id,
        value.metric_version,
        value.parameter_version,
    )


def _identity_context(
    spec: MarketStateDefinition,
    application: MarketStateApplication,
    session_id: str,
) -> dict[str, str]:
    return {
        "definition_id": spec.definition_id,
        "horizon": application.horizon,
        "parameter_set_id": spec.parameter_set_id,
        "reference_id": spec.reference_id or "none",
        "session_phase": _session_phase(session_id),
        "trade_date": _trade_date(session_id),
    }


def _session_phase(session_id: str) -> str:
    trade_date = _trade_date(session_id)
    suffix = session_id.split(f":{trade_date}:", 1)
    if len(suffix) != 2 or not suffix[1]:
        raise ValueError(f"session identity does not contain a phase: {session_id}")
    return suffix[1].split(":", 1)[0]


def _trade_date(session_id: str) -> str:
    match = _TRADE_DATE_PATTERN.search(session_id)
    if match is None:
        raise ValueError(f"session identity does not contain a trade date: {session_id}")
    return match.group(1)


def _has_stale_policy_evidence(
    spec: MarketStateDefinition,
    values: Mapping[str, MetricValue],
    now_ns: int,
) -> bool:
    for binding in spec.policy_bindings:
        measure = values.get(binding.measure_role)
        coverage = values.get(binding.coverage_role)
        if measure is None or coverage is None:
            continue
        effective_ns = max(measure.effective_ts_ns, coverage.effective_ts_ns)
        if (
            now_ns >= effective_ns
            and now_ns - effective_ns > binding.policy.maximum_evidence_age_ns
        ):
            return True
    return False


def _metric_decimal(value: MetricValue) -> Decimal:
    raw = value.value
    if isinstance(raw, bool) or not isinstance(raw, Decimal | int | float):
        raise ValueError(f"metric {value.metric_id} must be numeric")
    return raw if isinstance(raw, Decimal) else Decimal(str(raw))


def _decimal(values: Mapping[str, MetricValue], role: str) -> Decimal:
    return _metric_decimal(values[role])


def _optional_decimal(values: Mapping[str, MetricValue], role: str) -> Decimal | None:
    return _decimal(values, role) if role in values else None


def _integer(values: Mapping[str, MetricValue], role: str) -> int:
    raw = values[role].value
    if not isinstance(raw, int) or isinstance(raw, bool):
        raise ValueError(f"{role} must be an integer")
    return raw


def _worst_health(values: tuple[MetricHealth, ...]) -> MetricHealth:
    if not values:
        return MetricHealth.UNAVAILABLE
    return max(values, key=_HEALTH_ORDER.__getitem__)


def _worst_fidelity(values: tuple[MetricFidelity, ...]) -> MetricFidelity:
    if not values:
        return MetricFidelity.UNAVAILABLE
    return max(values, key=_FIDELITY_ORDER.__getitem__)


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _typed_tuple(values: object, expected_type: type[object], field: str) -> None:
    if not isinstance(values, tuple) or not all(isinstance(item, expected_type) for item in values):
        raise ValueError(f"{field} must be a tuple of {expected_type.__name__}")


def _text_tuple(values: object, field: str, *, required: bool = False) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{field} must be a tuple")
    normalized = tuple(_required_text(item, field) for item in values)
    if required and not normalized:
        raise ValueError(f"{field} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field} must not contain duplicates")
    return normalized
