from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

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
    SWING_PIVOT_PRICE_METRIC_ID,
    SWING_PROMINENCE_METRIC_ID,
    ConfirmedSwingGeometry,
    SwingGeometryPolicy,
    SwingKind,
    detect_confirmed_swings,
)

MARKET_STRUCTURE_ENTITY_GROUP = "swing_pivot_structure_fvg_zone"
CONFIRMED_SWING_ENTITY_TYPE = "confirmed_swing"

_CONFIRMED_SWING_DIMENSIONS = (
    "bar_specification",
    "definition_id",
    "detector_id",
    "detector_version",
    "horizon",
    "pivot_timestamp",
    "swing_kind",
)
_SWING_METRIC_IDS = frozenset(
    {
        SWING_PIVOT_PRICE_METRIC_ID,
        SWING_PROMINENCE_METRIC_ID,
    },
)


@dataclass(frozen=True, slots=True)
class ConfirmedSwingPayload(EntityPayload):
    definition_id: str
    detector_id: str
    detector_version: int
    horizon: str
    bar_specification: str
    kind: SwingKind
    pivot_price: Decimal
    prominence: Decimal
    confirmation_close: Decimal
    confirmation_displacement: Decimal
    pivot_bar_volume: Decimal | None
    pivot_ts_ns: int
    confirmation_ts_ns: int
    left_span_bars: int
    right_span_bars: int
    evidence_bar_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in ("definition_id", "detector_id", "horizon", "bar_specification"):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        _positive_int(self.detector_version, "detector_version")
        if not isinstance(self.kind, SwingKind):
            raise ValueError("kind must be SwingKind")
        for field in ("pivot_price", "prominence", "confirmation_close"):
            _positive_decimal(getattr(self, field), field)
        _finite_decimal(self.confirmation_displacement, "confirmation_displacement")
        if self.pivot_bar_volume is not None:
            _non_negative_decimal(self.pivot_bar_volume, "pivot_bar_volume")
        _timestamp(self.pivot_ts_ns, "pivot_ts_ns")
        _timestamp(self.confirmation_ts_ns, "confirmation_ts_ns")
        if self.confirmation_ts_ns < self.pivot_ts_ns:
            raise ValueError("confirmation_ts_ns cannot precede pivot_ts_ns")
        _positive_int(self.left_span_bars, "left_span_bars")
        _positive_int(self.right_span_bars, "right_span_bars")
        object.__setattr__(
            self,
            "evidence_bar_refs",
            _text_tuple(self.evidence_bar_refs, "evidence_bar_refs", required=True),
        )


@dataclass(frozen=True, slots=True)
class ConfirmedSwingApplication:
    application_id: str
    detector_id: str
    detector_version: int
    analytical_profile_ids: tuple[str, ...]
    instrument_ids: tuple[str, ...]
    bar_specifications: tuple[str, ...]
    horizon: str
    parameter_version: int
    policy: SwingGeometryPolicy
    maximum_retained_bars: int

    def __post_init__(self) -> None:
        for field in ("application_id", "detector_id", "horizon"):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        _positive_int(self.detector_version, "detector_version")
        _positive_int(self.parameter_version, "parameter_version")
        _positive_int(self.maximum_retained_bars, "maximum_retained_bars")
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
            "bar_specifications",
            _text_tuple(self.bar_specifications, "bar_specifications", required=True),
        )
        if not isinstance(self.policy, SwingGeometryPolicy):
            raise ValueError("policy must be SwingGeometryPolicy")
        minimum_required = self.policy.left_span_bars + self.policy.right_span_bars + 1
        if self.maximum_retained_bars < minimum_required:
            raise ValueError("maximum_retained_bars cannot be smaller than the detector span")

    def matches(self, bar: CompletedBarInput) -> bool:
        return (
            bar.analytical_profile_id in self.analytical_profile_ids
            and (not self.instrument_ids or bar.instrument_id in self.instrument_ids)
            and bar.bar_specification in self.bar_specifications
        )


@dataclass(frozen=True, slots=True)
class ConfirmedSwingDefinition:
    definition_id: str
    definition: EntityDefinition
    applications: tuple[ConfirmedSwingApplication, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "definition_id",
            _required_text(self.definition_id, "definition_id"),
        )
        if not isinstance(self.definition, EntityDefinition):
            raise ValueError("definition must be EntityDefinition")
        if self.definition.entity_type != CONFIRMED_SWING_ENTITY_TYPE:
            raise ValueError("confirmed-swing definition must use entity_type confirmed_swing")
        if self.definition.payload_type is not ConfirmedSwingPayload:
            raise ValueError("confirmed-swing definition must use ConfirmedSwingPayload")
        if self.definition.identity_dimensions != tuple(sorted(_CONFIRMED_SWING_DIMENSIONS)):
            raise ValueError("confirmed-swing identity dimensions do not match the contract")
        if self.definition.entity_inputs:
            raise ValueError("confirmed-swing definitions cannot consume entity revisions")
        if {item.metric_id for item in self.definition.metric_inputs} != _SWING_METRIC_IDS:
            raise ValueError(
                "confirmed-swing definitions require pivot-price and prominence metrics",
            )
        if any(not item.required for item in self.definition.metric_inputs):
            raise ValueError("confirmed-swing metric dependencies must be required")
        if self.definition.durability is not EntityDurability.TRANSIENT:
            raise ValueError("confirmed swings remain transient until persistence is approved")
        object.__setattr__(
            self,
            "applications",
            _typed_tuple(
                self.applications,
                ConfirmedSwingApplication,
                "applications",
                required=True,
            ),
        )
        identities = tuple(
            (
                item.application_id,
                item.detector_id,
                item.detector_version,
                item.horizon,
            )
            for item in self.applications
        )
        if len(identities) != len(set(identities)):
            raise ValueError("confirmed-swing application identities must be unique")


@dataclass(frozen=True, slots=True)
class ConfirmedSwingOwnerCounts:
    bars_accepted: int
    bars_duplicate: int
    bars_conflict: int
    revisions_published: int
    revisions_duplicate: int
    revisions_rejected: int
    entities_evicted: int
    publications_deferred: int


class ConfirmedSwingProjectionOwner:
    """Pure bounded owner for confirmed, detector-specific swing geometry."""

    def __init__(
        self,
        *,
        definitions: tuple[ConfirmedSwingDefinition, ...],
        limits: EntityStateBookLimits,
        maximum_publications_per_cycle: int,
        source: str,
        schema_version: int,
    ) -> None:
        specs = _typed_tuple(
            definitions,
            ConfirmedSwingDefinition,
            "definitions",
            required=True,
        )
        _positive_int(maximum_publications_per_cycle, "maximum_publications_per_cycle")
        self._source = _required_text(source, "source")
        _positive_int(schema_version, "schema_version")
        self._schema_version = schema_version
        registry = EntityRegistry(
            tuple(item.definition for item in specs),
            metric_keys={
                dependency.key
                for item in specs
                for dependency in item.definition.metric_inputs
            },
        )
        self._definitions = specs
        self._book = EntityStateBook(registry, limits)
        self._maximum_publications = maximum_publications_per_cycle
        self._ledgers: dict[tuple[str, str, str, str, int, str], CompletedBarLedger] = {}
        self._pending: deque[EntityRevision] = deque()
        self._bars_accepted = 0
        self._bars_duplicate = 0
        self._bars_conflict = 0
        self._revisions_published = 0
        self._revisions_duplicate = 0
        self._revisions_rejected = 0
        self._entities_evicted = 0
        self._publications_deferred = 0

    def ingest(self, bar: CompletedBarInput, *, now_ns: int) -> tuple[EntityRevision, ...]:
        if not isinstance(bar, CompletedBarInput):
            raise ValueError("confirmed-swing input must be CompletedBarInput")
        if not bar.complete:
            raise ValueError("confirmed-swing projection requires completed bars")
        _timestamp(now_ns, "now_ns")
        for spec in self._definitions:
            for application in spec.applications:
                if not application.matches(bar):
                    continue
                subject = (
                    spec.definition_id,
                    application.application_id,
                    bar.instrument_id,
                    bar.analytical_profile_id,
                    bar.analytical_profile_version,
                    bar.bar_specification,
                )
                ledger = self._ledgers.setdefault(
                    subject,
                    CompletedBarLedger(maximum_observations=application.maximum_retained_bars),
                )
                admission = ledger.admit(bar)
                if admission.status is BarAdmissionStatus.DUPLICATE:
                    self._bars_duplicate += 1
                    continue
                if admission.status is BarAdmissionStatus.CONFLICT:
                    self._bars_conflict += 1
                    continue
                self._bars_accepted += 1
                for contiguous in _contiguous_runs(ledger.bars):
                    if bar not in contiguous:
                        continue
                    for geometry in detect_confirmed_swings(contiguous, application.policy):
                        evidence = _geometry_evidence(contiguous, geometry, application.policy)
                        if bar not in evidence:
                            continue
                        candidate = _project_revision(
                            spec,
                            application,
                            geometry,
                            evidence,
                            now_ns=now_ns,
                            source=self._source,
                            schema_version=self._schema_version,
                        )
                        if self._book.get(candidate.entity_id) is not None:
                            self._revisions_duplicate += 1
                            continue
                        entity_admission = self._book.admit(candidate)
                        if entity_admission.status is EntityAdmissionStatus.ADDED:
                            self._entities_evicted += len(entity_admission.evicted_entity_ids)
                            self._pending.append(candidate)
                        elif entity_admission.status is EntityAdmissionStatus.DUPLICATE:
                            self._revisions_duplicate += 1
                        else:
                            self._revisions_rejected += 1
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
            entity_type=CONFIRMED_SWING_ENTITY_TYPE,
            dimensions=dimensions,
        )

    @property
    def retained_bars(self) -> int:
        return sum(len(item.bars) for item in self._ledgers.values())

    @property
    def retained_entities(self) -> int:
        return len(self._book)

    @property
    def pending_publications(self) -> int:
        return len(self._pending)

    @property
    def counts(self) -> ConfirmedSwingOwnerCounts:
        return ConfirmedSwingOwnerCounts(
            self._bars_accepted,
            self._bars_duplicate,
            self._bars_conflict,
            self._revisions_published,
            self._revisions_duplicate,
            self._revisions_rejected,
            self._entities_evicted,
            self._publications_deferred,
        )

    def _drain(self) -> tuple[EntityRevision, ...]:
        revisions: list[EntityRevision] = []
        while self._pending and len(revisions) < self._maximum_publications:
            revisions.append(self._pending.popleft())
        self._revisions_published += len(revisions)
        if self._pending:
            self._publications_deferred += len(self._pending)
        return tuple(revisions)


def _project_revision(
    spec: ConfirmedSwingDefinition,
    application: ConfirmedSwingApplication,
    geometry: ConfirmedSwingGeometry,
    evidence: tuple[CompletedBarInput, ...],
    *,
    now_ns: int,
    source: str,
    schema_version: int,
) -> EntityRevision:
    first = evidence[0]
    identity = EntityIdentity(
        entity_type=spec.definition.entity_type,
        entity_version=spec.definition.version,
        instrument_id=first.instrument_id,
        analytical_profile_id=first.analytical_profile_id,
        analytical_profile_version=first.analytical_profile_version,
        dimensions=(
            EntityIdentityDimension("bar_specification", first.bar_specification),
            EntityIdentityDimension("definition_id", spec.definition_id),
            EntityIdentityDimension("detector_id", application.detector_id),
            EntityIdentityDimension("detector_version", str(application.detector_version)),
            EntityIdentityDimension("horizon", application.horizon),
            EntityIdentityDimension("pivot_timestamp", str(geometry.pivot_ts_ns)),
            EntityIdentityDimension("swing_kind", geometry.kind.value),
        ),
    )
    payload = ConfirmedSwingPayload(
        definition_id=spec.definition_id,
        detector_id=application.detector_id,
        detector_version=application.detector_version,
        horizon=application.horizon,
        bar_specification=first.bar_specification,
        kind=geometry.kind,
        pivot_price=geometry.pivot_price,
        prominence=geometry.prominence,
        confirmation_close=geometry.confirmation_close,
        confirmation_displacement=geometry.confirmation_displacement,
        pivot_bar_volume=geometry.pivot_bar_volume,
        pivot_ts_ns=geometry.pivot_ts_ns,
        confirmation_ts_ns=geometry.confirmation_ts_ns,
        left_span_bars=geometry.left_span_bars,
        right_span_bars=geometry.right_span_bars,
        evidence_bar_refs=tuple(_bar_reference(item) for item in evidence),
    )
    observed_ns = max(item.observed_ts_ns for item in evidence)
    calculated_ns = max(now_ns, observed_ns)
    published_ns = max(calculated_ns, *(item.normalized_ts_ns for item in evidence))
    dependencies = {item.metric_id: item for item in spec.definition.metric_inputs}
    evidence_refs = tuple(
        EntityEvidenceReference(
            kind=EntityEvidenceKind.METRIC,
            definition_id=metric_id,
            reference_id=(
                f"metric:{metric_id}:{first.instrument_id}:{first.bar_specification}:"
                f"{application.detector_id}:{application.detector_version}:"
                f"{geometry.pivot_ts_ns}:{application.parameter_version}"
            ),
            version=dependencies[metric_id].metric_version,
            revision=max(item.revision for item in evidence),
            effective_ts_ns=geometry.confirmation_ts_ns,
            health=geometry.health,
            fidelity=geometry.fidelity,
        )
        for metric_id in sorted(_SWING_METRIC_IDS)
    )
    return EntityRevision(
        identity=identity,
        revision=1,
        parameter_version=application.parameter_version,
        payload=payload,
        lifecycle=EntityLifecycle.COMPLETE,
        effective_ts_ns=geometry.confirmation_ts_ns,
        observed_ts_ns=observed_ns,
        calculated_ts_ns=calculated_ns,
        published_ts_ns=published_ns,
        health=geometry.health,
        fidelity=geometry.fidelity,
        evidence_refs=evidence_refs,
        missing_reasons=(),
        conflict_reasons=(),
        source=source,
        schema_version=schema_version,
    )


def _contiguous_runs(
    bars: tuple[CompletedBarInput, ...],
) -> tuple[tuple[CompletedBarInput, ...], ...]:
    if not bars:
        return ()
    runs: list[list[CompletedBarInput]] = [[bars[0]]]
    for bar in bars[1:]:
        previous = runs[-1][-1]
        if previous.interval_end_ns == bar.interval_start_ns:
            runs[-1].append(bar)
        else:
            runs.append([bar])
    return tuple(tuple(run) for run in runs)


def _geometry_evidence(
    bars: tuple[CompletedBarInput, ...],
    geometry: ConfirmedSwingGeometry,
    policy: SwingGeometryPolicy,
) -> tuple[CompletedBarInput, ...]:
    pivot_index = next(
        index for index, bar in enumerate(bars) if bar.interval_end_ns == geometry.pivot_ts_ns
    )
    return bars[
        pivot_index - policy.left_span_bars : pivot_index + policy.right_span_bars + 1
    ]


def _bar_reference(bar: CompletedBarInput) -> str:
    return (
        f"completed_bar:{bar.instrument_id}:{bar.bar_specification}:"
        f"{bar.interval_end_ns}:{bar.revision}"
    )


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


def _positive_decimal(value: object, field: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ValueError(f"{field} must be a positive finite Decimal")
    return value


def _finite_decimal(value: object, field: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{field} must be a finite Decimal")
    return value


def _non_negative_decimal(value: object, field: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError(f"{field} must be a non-negative finite Decimal")
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
