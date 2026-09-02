from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from markeitech.intelligence.completed_bars import (
    BarAdmissionStatus,
    CompletedBarInput,
    CompletedBarLedger,
)
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
from markeitech.intelligence.entity_measurements import (
    FVG_FILL_RATIO_METRIC_ID,
    FVG_LOWER_BOUND_METRIC_ID,
    FVG_UPPER_BOUND_METRIC_ID,
    FVG_WIDTH_METRIC_ID,
    FvgDirection,
    FvgGeometryPolicy,
    detect_fvg_geometries,
)
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth

FVG_ENTITY_TYPE = "fair_value_gap"
"""Canonical entity type for fair-value-gap lifecycle revisions."""

_FVG_METRIC_IDS = frozenset(
    {
        FVG_LOWER_BOUND_METRIC_ID,
        FVG_UPPER_BOUND_METRIC_ID,
        FVG_WIDTH_METRIC_ID,
        FVG_FILL_RATIO_METRIC_ID,
    }
)
_FVG_DIMENSIONS = (
    "bar_specification",
    "definition_id",
    "direction",
    "formation_timestamp",
    "horizon",
    "lifecycle_policy_id",
    "lifecycle_policy_version",
)


class FvgTerminalOutcome(StrEnum):
    """Configured terminal lifecycle outcome for a filled or aged FVG."""

    COMPLETE = "COMPLETE"
    INVALIDATED = "INVALIDATED"


@dataclass(frozen=True, slots=True)
class FvgPayload(EntityPayload):
    """Preserve FVG formation geometry, fill state, timing, and bar lineage."""

    definition_id: str
    lifecycle_policy_id: str
    lifecycle_policy_version: int
    horizon: str
    bar_specification: str
    direction: FvgDirection
    lower_bound: Decimal
    upper_bound: Decimal
    width: Decimal
    normalized_width: Decimal | None
    normalization_id: str | None
    normalization_unit: Decimal | None
    fill_ratio: Decimal
    remaining_lower: Decimal
    remaining_upper: Decimal
    formation_start_ts_ns: int
    formation_middle_ts_ns: int
    formation_ts_ns: int
    first_fill_ts_ns: int | None
    terminal_ts_ns: int | None
    elapsed_bars: int
    formation_bar_refs: tuple[str, ...]
    lifecycle_bar_refs: tuple[str, ...]
    missing_context: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in (
            "definition_id",
            "lifecycle_policy_id",
            "horizon",
            "bar_specification",
        ):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        _positive_int(self.lifecycle_policy_version, "lifecycle_policy_version")
        if not isinstance(self.direction, FvgDirection):
            raise ValueError("direction must be FvgDirection")
        for field in ("lower_bound", "upper_bound", "width"):
            _positive_decimal(getattr(self, field), field)
        if self.lower_bound >= self.upper_bound:
            raise ValueError("lower_bound must be smaller than upper_bound")
        if self.width != self.upper_bound - self.lower_bound:
            raise ValueError("width must equal upper_bound minus lower_bound")
        if self.normalized_width is not None:
            _positive_decimal(self.normalized_width, "normalized_width")
        if self.normalization_unit is not None:
            _positive_decimal(self.normalization_unit, "normalization_unit")
        if (self.normalization_id is None) is not (self.normalization_unit is None):
            raise ValueError("normalization identity and unit must be present together")
        if self.normalization_id is not None:
            object.__setattr__(
                self,
                "normalization_id",
                _required_text(self.normalization_id, "normalization_id"),
            )
            if self.normalized_width != self.width / self.normalization_unit:
                raise ValueError("normalized_width must equal width divided by normalization_unit")
        elif self.normalized_width is not None:
            raise ValueError("normalized_width requires normalization evidence")
        _ratio(self.fill_ratio, "fill_ratio")
        for field in ("remaining_lower", "remaining_upper"):
            _positive_decimal(getattr(self, field), field)
        if not self.lower_bound <= self.remaining_lower <= self.remaining_upper <= self.upper_bound:
            raise ValueError("remaining interval must stay inside the formation bounds")
        for field in (
            "formation_start_ts_ns",
            "formation_middle_ts_ns",
            "formation_ts_ns",
        ):
            _timestamp(getattr(self, field), field)
        if not (self.formation_start_ts_ns < self.formation_middle_ts_ns < self.formation_ts_ns):
            raise ValueError("formation timestamps must be strictly chronological")
        for field in ("first_fill_ts_ns", "terminal_ts_ns"):
            value = getattr(self, field)
            if value is not None:
                _timestamp(value, field)
                if value <= self.formation_ts_ns:
                    raise ValueError(f"{field} must follow formation")
        if self.terminal_ts_ns is not None and self.first_fill_ts_ns is not None:
            if self.terminal_ts_ns < self.first_fill_ts_ns:
                raise ValueError("terminal_ts_ns cannot precede first_fill_ts_ns")
        _non_negative_int(self.elapsed_bars, "elapsed_bars")
        object.__setattr__(
            self,
            "formation_bar_refs",
            _text_tuple(self.formation_bar_refs, "formation_bar_refs", required=True),
        )
        if len(self.formation_bar_refs) != 3:
            raise ValueError("the first FVG entity requires exactly three formation bars")
        object.__setattr__(
            self,
            "lifecycle_bar_refs",
            _text_tuple(self.lifecycle_bar_refs, "lifecycle_bar_refs"),
        )
        object.__setattr__(
            self,
            "missing_context",
            _text_tuple(self.missing_context, "missing_context"),
        )


@dataclass(frozen=True, slots=True)
class FvgNormalizationEvidence:
    """Carry optional, versioned width-normalization evidence for one FVG subject."""

    metric_id: str
    metric_version: int
    revision: int
    instrument_id: str
    analytical_profile_id: str
    analytical_profile_version: int
    bar_specification: str
    horizon: str
    effective_ts_ns: int
    value: Decimal
    health: MetricHealth
    fidelity: MetricFidelity
    reference_id: str

    def __post_init__(self) -> None:
        for field in (
            "metric_id",
            "instrument_id",
            "analytical_profile_id",
            "bar_specification",
            "horizon",
            "reference_id",
        ):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        for field in ("metric_version", "revision", "analytical_profile_version"):
            _positive_int(getattr(self, field), field)
        _timestamp(self.effective_ts_ns, "effective_ts_ns")
        _positive_decimal(self.value, "value")
        if not isinstance(self.health, MetricHealth):
            raise ValueError("health must be MetricHealth")
        if not isinstance(self.fidelity, MetricFidelity):
            raise ValueError("fidelity must be MetricFidelity")


@dataclass(frozen=True, slots=True)
class FvgLifecyclePolicy:
    """Configure FVG geometry, aging outcome, and bounded retained evidence."""

    policy_id: str
    version: int
    source_interval_ns: int
    geometry: FvgGeometryPolicy
    terminal_outcome: FvgTerminalOutcome
    maximum_age_bars: int
    minimum_age_bars: int
    maximum_age_bars_ceiling: int
    age_step_bars: int
    maximum_age_dynamic: bool
    maximum_retained_bars: int
    maximum_retained_normalizations: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _required_text(self.policy_id, "policy_id"))
        _positive_int(self.version, "version")
        _positive_int(self.source_interval_ns, "source_interval_ns")
        if not isinstance(self.geometry, FvgGeometryPolicy):
            raise ValueError("geometry must be FvgGeometryPolicy")
        if not isinstance(self.terminal_outcome, FvgTerminalOutcome):
            raise ValueError("terminal_outcome must be FvgTerminalOutcome")
        _integer_envelope(
            self.maximum_age_bars,
            self.minimum_age_bars,
            self.maximum_age_bars_ceiling,
            self.age_step_bars,
            "maximum FVG age",
        )
        if not isinstance(self.maximum_age_dynamic, bool):
            raise ValueError("maximum_age_dynamic must be a boolean")
        _positive_int(self.maximum_retained_bars, "maximum_retained_bars")
        _positive_int(
            self.maximum_retained_normalizations,
            "maximum_retained_normalizations",
        )
        minimum_retention = self.geometry.pattern_length + self.maximum_age_bars
        if self.maximum_retained_bars < minimum_retention:
            raise ValueError("maximum_retained_bars cannot discard a live FVG lifecycle")


@dataclass(frozen=True, slots=True)
class FvgApplication:
    """Scope one FVG lifecycle policy to profiles, instruments, bars, and horizon."""

    application_id: str
    analytical_profile_ids: tuple[str, ...]
    instrument_ids: tuple[str, ...]
    bar_specifications: tuple[str, ...]
    horizon: str
    parameter_version: int
    policy: FvgLifecyclePolicy
    normalization_metric_id: str | None = None
    normalization_metric_version: int | None = None
    normalization_max_age_ns: int | None = None

    def __post_init__(self) -> None:
        for field in ("application_id", "horizon"):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        for field in ("analytical_profile_ids", "bar_specifications"):
            object.__setattr__(
                self,
                field,
                _text_tuple(getattr(self, field), field, required=True),
            )
        object.__setattr__(
            self,
            "instrument_ids",
            _text_tuple(self.instrument_ids, "instrument_ids"),
        )
        _positive_int(self.parameter_version, "parameter_version")
        if not isinstance(self.policy, FvgLifecyclePolicy):
            raise ValueError("policy must be FvgLifecyclePolicy")
        optional = (
            self.normalization_metric_id,
            self.normalization_metric_version,
            self.normalization_max_age_ns,
        )
        if any(item is not None for item in optional) and not all(
            item is not None for item in optional
        ):
            raise ValueError("normalization fields must be configured together")
        if self.normalization_metric_id is not None:
            object.__setattr__(
                self,
                "normalization_metric_id",
                _required_text(self.normalization_metric_id, "normalization_metric_id"),
            )
            _positive_int(self.normalization_metric_version, "normalization_metric_version")
            _positive_int(self.normalization_max_age_ns, "normalization_max_age_ns")

    def matches_bar(self, bar: CompletedBarInput) -> bool:
        return (
            bar.analytical_profile_id in self.analytical_profile_ids
            and (not self.instrument_ids or bar.instrument_id in self.instrument_ids)
            and bar.bar_specification in self.bar_specifications
        )


@dataclass(frozen=True, slots=True)
class FvgEntityDefinition:
    """Bind a generic entity definition to validated FVG applications."""

    definition_id: str
    definition: EntityDefinition
    applications: tuple[FvgApplication, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "definition_id",
            _required_text(self.definition_id, "definition_id"),
        )
        if not isinstance(self.definition, EntityDefinition):
            raise ValueError("definition must be EntityDefinition")
        if self.definition.entity_type != FVG_ENTITY_TYPE:
            raise ValueError("FVG definition must use fair_value_gap")
        if self.definition.payload_type is not FvgPayload:
            raise ValueError("FVG definition must use FvgPayload")
        if self.definition.identity_dimensions != tuple(sorted(_FVG_DIMENSIONS)):
            raise ValueError("FVG identity dimensions do not match the contract")
        if self.definition.durability is not EntityDurability.TRANSIENT:
            raise ValueError("the first FVG projection remains transient")
        declared_metrics = {item.key for item in self.definition.metric_inputs}
        if not all((metric_id, 1) in declared_metrics for metric_id in _FVG_METRIC_IDS):
            raise ValueError("FVG definition must declare all geometry metrics")
        object.__setattr__(
            self,
            "applications",
            _typed_tuple(self.applications, FvgApplication, "applications", required=True),
        )
        ids = tuple(item.application_id for item in self.applications)
        if len(ids) != len(set(ids)):
            raise ValueError("FVG application IDs must be unique")
        for application in self.applications:
            if application.normalization_metric_id is None:
                continue
            key = (application.normalization_metric_id, application.normalization_metric_version)
            if key not in declared_metrics:
                raise ValueError("FVG normalization metric must be declared")
            dependency = next(item for item in self.definition.metric_inputs if item.key == key)
            if dependency.required:
                raise ValueError("FVG normalization must remain optional evidence")


@dataclass(frozen=True, slots=True)
class FvgEntityCounts:
    """Snapshot bounded FVG owner admission, publication, and eviction counters."""

    bar_applications_accepted: int
    bar_applications_duplicate: int
    bar_applications_conflict: int
    normalizations_accepted: int
    normalizations_duplicate: int
    normalizations_conflict: int
    revisions_published: int
    revisions_duplicate: int
    revisions_rejected: int
    entities_evicted: int
    publications_deferred: int


type _ApplicationKey = tuple[str, str, str, str, int, str]
type _NormalizationKey = tuple[str, int, str, str, int, str, str]


class FvgEntityProjectionOwner:
    """Pure bounded FVG formation and lifecycle projection over completed bars."""

    def __init__(
        self,
        *,
        definitions: tuple[FvgEntityDefinition, ...],
        limits: EntityStateBookLimits,
        maximum_publications_per_cycle: int,
        source: str,
        schema_version: int,
    ) -> None:
        specs = _typed_tuple(definitions, FvgEntityDefinition, "definitions", required=True)
        _positive_int(maximum_publications_per_cycle, "maximum_publications_per_cycle")
        self._source = _required_text(source, "source")
        _positive_int(schema_version, "schema_version")
        self._schema_version = schema_version
        registry = EntityRegistry(
            tuple(item.definition for item in specs),
            metric_keys={
                dependency.key for item in specs for dependency in item.definition.metric_inputs
            },
        )
        self._definitions = specs
        self._book = EntityStateBook(registry, limits)
        self._maximum_publications = maximum_publications_per_cycle
        self._ledgers: dict[_ApplicationKey, CompletedBarLedger] = {}
        self._normalizations: dict[
            _NormalizationKey,
            dict[tuple[str, int], FvgNormalizationEvidence],
        ] = {}
        self._pending: deque[EntityRevision] = deque()
        self._bar_applications_accepted = 0
        self._bar_applications_duplicate = 0
        self._bar_applications_conflict = 0
        self._normalizations_accepted = 0
        self._normalizations_duplicate = 0
        self._normalizations_conflict = 0
        self._revisions_published = 0
        self._revisions_duplicate = 0
        self._revisions_rejected = 0
        self._entities_evicted = 0
        self._publications_deferred = 0

    def ingest_bar(self, bar: CompletedBarInput, *, now_ns: int) -> tuple[EntityRevision, ...]:
        if not isinstance(bar, CompletedBarInput) or not bar.complete:
            raise ValueError("FVG input must be a completed bar")
        _timestamp(now_ns, "now_ns")
        for spec in self._definitions:
            for application in spec.applications:
                if not application.matches_bar(bar):
                    continue
                key = _application_key(spec, application, bar)
                ledger = self._ledgers.setdefault(
                    key,
                    CompletedBarLedger(
                        maximum_observations=application.policy.maximum_retained_bars,
                    ),
                )
                admission = ledger.admit(bar)
                if admission.status is BarAdmissionStatus.DUPLICATE:
                    self._bar_applications_duplicate += 1
                    continue
                if admission.status is BarAdmissionStatus.CONFLICT:
                    self._bar_applications_conflict += 1
                    continue
                self._bar_applications_accepted += 1
                self._reproject(spec, application, ledger.bars, now_ns=now_ns)
        return self._drain()

    def ingest_normalization(
        self,
        evidence: FvgNormalizationEvidence,
        *,
        now_ns: int,
    ) -> tuple[EntityRevision, ...]:
        if not isinstance(evidence, FvgNormalizationEvidence):
            raise ValueError("normalization must be FvgNormalizationEvidence")
        _timestamp(now_ns, "now_ns")
        applications = tuple(
            (spec, application)
            for spec in self._definitions
            for application in spec.applications
            if _normalization_application_matches(evidence, application)
        )
        if not applications:
            return self._drain()
        normalization_key = _normalization_key(evidence)
        retained = self._normalizations.setdefault(normalization_key, {})
        evidence_key = (evidence.reference_id, evidence.revision)
        current = retained.get(evidence_key)
        if current is not None:
            if current == evidence:
                self._normalizations_duplicate += 1
            else:
                self._normalizations_conflict += 1
            return self._drain()
        retained[evidence_key] = evidence
        self._normalizations_accepted += 1
        maximum = max(
            application.policy.maximum_retained_normalizations for _, application in applications
        )
        ordered = sorted(
            retained.values(),
            key=lambda item: (item.effective_ts_ns, item.reference_id, item.revision),
        )
        for stale in ordered[:-maximum]:
            retained.pop((stale.reference_id, stale.revision), None)
        for key, ledger in self._ledgers.items():
            spec, application = self._spec_application(key)
            if _normalization_matches(evidence, application, key):
                self._reproject(spec, application, ledger.bars, now_ns=now_ns)
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
            entity_type=FVG_ENTITY_TYPE,
            dimensions=dimensions,
        )

    @property
    def retained_bars(self) -> int:
        return sum(len(item.bars) for item in self._ledgers.values())

    @property
    def retained_normalizations(self) -> int:
        return sum(len(item) for item in self._normalizations.values())

    @property
    def retained_entities(self) -> int:
        return len(self._book)

    @property
    def counts(self) -> FvgEntityCounts:
        return FvgEntityCounts(
            self._bar_applications_accepted,
            self._bar_applications_duplicate,
            self._bar_applications_conflict,
            self._normalizations_accepted,
            self._normalizations_duplicate,
            self._normalizations_conflict,
            self._revisions_published,
            self._revisions_duplicate,
            self._revisions_rejected,
            self._entities_evicted,
            self._publications_deferred,
        )

    def _reproject(
        self,
        spec: FvgEntityDefinition,
        application: FvgApplication,
        bars: tuple[CompletedBarInput, ...],
        *,
        now_ns: int,
    ) -> None:
        if len(bars) < application.policy.geometry.pattern_length:
            return
        for index in range(2, len(bars)):
            formation = bars[index - 2 : index + 1]
            if not _contiguous(formation, application.policy.source_interval_ns):
                continue
            geometries = detect_fvg_geometries(formation, application.policy.geometry)
            for geometry in geometries:
                later = bars[index + 1 : index + 1 + application.policy.maximum_age_bars]
                identity = _identity(spec, application, formation, geometry.direction)
                current = self._book.get(identity.entity_id)
                candidate = _project_revision(
                    spec,
                    application,
                    identity,
                    formation,
                    later,
                    normalization=self._select_normalization(application, formation[-1]),
                    current=current,
                    now_ns=now_ns,
                    source=self._source,
                    schema_version=self._schema_version,
                )
                self._admit(candidate)

    def _select_normalization(
        self,
        application: FvgApplication,
        formation_bar: CompletedBarInput,
    ) -> FvgNormalizationEvidence | None:
        if application.normalization_metric_id is None:
            return None
        key = (
            application.normalization_metric_id,
            application.normalization_metric_version,
            formation_bar.instrument_id,
            formation_bar.analytical_profile_id,
            formation_bar.analytical_profile_version,
            formation_bar.bar_specification,
            application.horizon,
        )
        candidates = tuple(
            item
            for item in self._normalizations.get(key, {}).values()
            if item.effective_ts_ns <= formation_bar.interval_end_ns
            and formation_bar.interval_end_ns - item.effective_ts_ns
            <= application.normalization_max_age_ns
        )
        return (
            max(
                candidates,
                key=lambda item: (item.effective_ts_ns, item.revision, item.reference_id),
            )
            if candidates
            else None
        )

    def _spec_application(
        self,
        key: _ApplicationKey,
    ) -> tuple[FvgEntityDefinition, FvgApplication]:
        for spec in self._definitions:
            if spec.definition_id != key[0]:
                continue
            for application in spec.applications:
                if application.application_id == key[1]:
                    return spec, application
        raise RuntimeError("FVG ledger lost its registered application")

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


def _project_revision(
    spec: FvgEntityDefinition,
    application: FvgApplication,
    identity: EntityIdentity,
    formation: tuple[CompletedBarInput, ...],
    later: tuple[CompletedBarInput, ...],
    *,
    normalization: FvgNormalizationEvidence | None,
    current: EntityRevision | None,
    now_ns: int,
    source: str,
    schema_version: int,
) -> EntityRevision:
    geometry = detect_fvg_geometries(formation, application.policy.geometry)[0]
    lower = geometry.lower_bound
    upper = geometry.upper_bound
    width = geometry.width
    fill_ratio, remaining_lower, remaining_upper, first_fill, full_fill = _fill_state(
        geometry.direction,
        lower,
        upper,
        later,
    )
    terminal_ts = full_fill
    if full_fill is not None:
        lifecycle = (
            EntityLifecycle.COMPLETE
            if application.policy.terminal_outcome is FvgTerminalOutcome.COMPLETE
            else EntityLifecycle.INVALIDATED
        )
        lifecycle_bars = tuple(item for item in later if item.interval_end_ns <= full_fill)
    elif len(later) >= application.policy.maximum_age_bars:
        lifecycle = EntityLifecycle.EXPIRED
        terminal_ts = later[application.policy.maximum_age_bars - 1].interval_end_ns
        lifecycle_bars = later[: application.policy.maximum_age_bars]
    else:
        lifecycle = EntityLifecycle.ACTIVE
        lifecycle_bars = later
    missing = []
    if application.normalization_metric_id is None:
        missing.append("width_normalization_not_configured")
    elif normalization is None:
        missing.append("width_normalization_unavailable")
    payload = FvgPayload(
        definition_id=spec.definition_id,
        lifecycle_policy_id=application.policy.policy_id,
        lifecycle_policy_version=application.policy.version,
        horizon=application.horizon,
        bar_specification=formation[0].bar_specification,
        direction=geometry.direction,
        lower_bound=lower,
        upper_bound=upper,
        width=width,
        normalized_width=None if normalization is None else width / normalization.value,
        normalization_id=None if normalization is None else normalization.metric_id,
        normalization_unit=None if normalization is None else normalization.value,
        fill_ratio=fill_ratio,
        remaining_lower=remaining_lower,
        remaining_upper=remaining_upper,
        formation_start_ts_ns=formation[0].interval_start_ns,
        formation_middle_ts_ns=formation[1].interval_end_ns,
        formation_ts_ns=formation[2].interval_end_ns,
        first_fill_ts_ns=first_fill,
        terminal_ts_ns=terminal_ts,
        elapsed_bars=len(lifecycle_bars),
        formation_bar_refs=tuple(_bar_reference(item) for item in formation),
        lifecycle_bar_refs=tuple(_bar_reference(item) for item in lifecycle_bars),
        missing_context=tuple(missing),
    )
    evidence_bars = (*formation, *lifecycle_bars)
    health = _least_healthy(
        (
            *(item.health for item in evidence_bars),
            *((normalization.health,) if normalization is not None else ()),
        )
    )
    fidelity = _least_fidelity(
        (
            *(item.fidelity for item in evidence_bars),
            *((normalization.fidelity,) if normalization is not None else ()),
        )
    )
    if missing:
        fidelity = _least_fidelity((fidelity, MetricFidelity.PARTIAL))
    dependencies = {item.metric_id: item for item in spec.definition.metric_inputs}
    evidence_refs = [
        EntityEvidenceReference(
            EntityEvidenceKind.METRIC,
            metric_id,
            (
                f"metric:{metric_id}:{formation[0].instrument_id}:"
                f"{formation[0].bar_specification}:{geometry.direction.value}:"
                f"{geometry.formation_ts_ns}:{application.parameter_version}"
            ),
            dependencies[metric_id].metric_version,
            max(item.revision for item in evidence_bars),
            terminal_ts or evidence_bars[-1].interval_end_ns,
            health,
            fidelity,
        )
        for metric_id in sorted(_FVG_METRIC_IDS)
    ]
    if normalization is not None:
        evidence_refs.append(
            EntityEvidenceReference(
                EntityEvidenceKind.METRIC,
                normalization.metric_id,
                normalization.reference_id,
                normalization.metric_version,
                normalization.revision,
                normalization.effective_ts_ns,
                normalization.health,
                normalization.fidelity,
            )
        )
    observed_ns = max(item.observed_ts_ns for item in evidence_bars)
    revision = 1 if current is None else current.revision + 1
    return EntityRevision(
        identity=identity,
        revision=revision,
        previous_revision=None if current is None else current.revision,
        parameter_version=application.parameter_version,
        payload=payload,
        lifecycle=lifecycle,
        effective_ts_ns=terminal_ts or evidence_bars[-1].interval_end_ns,
        observed_ts_ns=observed_ns,
        calculated_ts_ns=max(now_ns, observed_ns),
        published_ts_ns=max(
            now_ns,
            observed_ns,
            *(item.normalized_ts_ns for item in evidence_bars),
        ),
        health=health,
        fidelity=fidelity,
        evidence_refs=tuple(evidence_refs),
        missing_reasons=tuple(missing),
        conflict_reasons=(),
        source=source,
        schema_version=schema_version,
    )


def _fill_state(
    direction: FvgDirection,
    lower: Decimal,
    upper: Decimal,
    later: tuple[CompletedBarInput, ...],
) -> tuple[Decimal, Decimal, Decimal, int | None, int | None]:
    width = upper - lower
    first_fill = None
    full_fill = None
    if direction is FvgDirection.BULLISH:
        deepest = upper
        for bar in later:
            if bar.low < upper and first_fill is None:
                first_fill = bar.interval_end_ns
            deepest = min(deepest, bar.low)
            if bar.low <= lower:
                full_fill = bar.interval_end_ns
                break
        remaining_upper = max(lower, min(upper, deepest))
        fill = (upper - remaining_upper) / width
        return fill, lower, remaining_upper, first_fill, full_fill
    highest = lower
    for bar in later:
        if bar.high > lower and first_fill is None:
            first_fill = bar.interval_end_ns
        highest = max(highest, bar.high)
        if bar.high >= upper:
            full_fill = bar.interval_end_ns
            break
    remaining_lower = min(upper, max(lower, highest))
    fill = (remaining_lower - lower) / width
    return fill, remaining_lower, upper, first_fill, full_fill


def _identity(
    spec: FvgEntityDefinition,
    application: FvgApplication,
    formation: tuple[CompletedBarInput, ...],
    direction: FvgDirection,
) -> EntityIdentity:
    first = formation[0]
    return EntityIdentity(
        entity_type=FVG_ENTITY_TYPE,
        entity_version=spec.definition.version,
        instrument_id=first.instrument_id,
        analytical_profile_id=first.analytical_profile_id,
        analytical_profile_version=first.analytical_profile_version,
        dimensions=(
            EntityIdentityDimension("bar_specification", first.bar_specification),
            EntityIdentityDimension("definition_id", spec.definition_id),
            EntityIdentityDimension("direction", direction.value),
            EntityIdentityDimension("formation_timestamp", str(formation[-1].interval_end_ns)),
            EntityIdentityDimension("horizon", application.horizon),
            EntityIdentityDimension("lifecycle_policy_id", application.policy.policy_id),
            EntityIdentityDimension(
                "lifecycle_policy_version",
                str(application.policy.version),
            ),
        ),
    )


def _application_key(
    spec: FvgEntityDefinition,
    application: FvgApplication,
    bar: CompletedBarInput,
) -> _ApplicationKey:
    return (
        spec.definition_id,
        application.application_id,
        bar.instrument_id,
        bar.analytical_profile_id,
        bar.analytical_profile_version,
        bar.bar_specification,
    )


def _normalization_key(evidence: FvgNormalizationEvidence) -> _NormalizationKey:
    return (
        evidence.metric_id,
        evidence.metric_version,
        evidence.instrument_id,
        evidence.analytical_profile_id,
        evidence.analytical_profile_version,
        evidence.bar_specification,
        evidence.horizon,
    )


def _normalization_matches(
    evidence: FvgNormalizationEvidence,
    application: FvgApplication,
    key: _ApplicationKey,
) -> bool:
    return (
        application.normalization_metric_id == evidence.metric_id
        and application.normalization_metric_version == evidence.metric_version
        and key[2] == evidence.instrument_id
        and key[3] == evidence.analytical_profile_id
        and key[4] == evidence.analytical_profile_version
        and key[5] == evidence.bar_specification
        and application.horizon == evidence.horizon
    )


def _normalization_application_matches(
    evidence: FvgNormalizationEvidence,
    application: FvgApplication,
) -> bool:
    return (
        application.normalization_metric_id == evidence.metric_id
        and application.normalization_metric_version == evidence.metric_version
        and evidence.analytical_profile_id in application.analytical_profile_ids
        and (not application.instrument_ids or evidence.instrument_id in application.instrument_ids)
        and evidence.bar_specification in application.bar_specifications
        and evidence.horizon == application.horizon
    )


def _contiguous(bars: tuple[CompletedBarInput, ...], interval_ns: int) -> bool:
    return all(
        item.interval_end_ns - item.interval_start_ns == interval_ns for item in bars
    ) and all(
        previous.interval_end_ns == current.interval_start_ns
        for previous, current in zip(bars, bars[1:], strict=False)
    )


def _bar_reference(bar: CompletedBarInput) -> str:
    return (
        f"completed_bar:{bar.instrument_id}:{bar.bar_specification}:"
        f"{bar.interval_end_ns}:{bar.revision}"
    )


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


def _non_negative_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _timestamp(value: object, field: str) -> int:
    return _non_negative_int(value, field)


def _positive_decimal(value: object, field: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ValueError(f"{field} must be a positive finite Decimal")
    return value


def _ratio(value: object, field: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or not 0 <= value <= 1:
        raise ValueError(f"{field} must be a finite Decimal between zero and one")
    return value


def _text_tuple(
    values: object,
    field: str,
    *,
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
    expected: type,
    field: str,
    *,
    required: bool = False,
) -> tuple:
    if not isinstance(values, tuple) or any(not isinstance(item, expected) for item in values):
        raise ValueError(f"{field} must contain only {expected.__name__} values")
    if required and not values:
        raise ValueError(f"{field} must not be empty")
    return values
