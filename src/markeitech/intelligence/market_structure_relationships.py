from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
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
from markeitech.intelligence.entity_measurements import SwingKind
from markeitech.intelligence.market_structure_entities import (
    CONFIRMED_SWING_ENTITY_TYPE,
    ConfirmedSwingPayload,
)
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth

SWING_LEG_ENTITY_TYPE = "swing_leg"
"""Canonical entity type for relationships between alternating confirmed pivots."""
PIVOT_STRUCTURE_ENTITY_TYPE = "pivot_structure_state"
"""Canonical entity type for revisable confirmed-pivot structure state."""

_SWING_LEG_DIMENSIONS = (
    "bar_specification",
    "chain_policy_id",
    "chain_policy_version",
    "definition_id",
    "destination_entity_id",
    "horizon",
    "origin_entity_id",
)
_PIVOT_STRUCTURE_DIMENSIONS = (
    "bar_specification",
    "chain_policy_id",
    "chain_policy_version",
    "definition_id",
    "detector_id",
    "detector_version",
    "horizon",
)


class SameKindPivotPolicy(StrEnum):
    """Policies for resolving successive confirmed pivots of the same kind."""

    MORE_EXTREME_TERMINAL = "MORE_EXTREME_TERMINAL"
    LATEST_TERMINAL = "LATEST_TERMINAL"
    UNRESOLVED_UNTIL_OPPOSITE = "UNRESOLVED_UNTIL_OPPOSITE"


class ResolvedRunSelection(StrEnum):
    """Policies for selecting one alternating run from resolved pivots."""

    MORE_EXTREME = "MORE_EXTREME"
    EARLIEST = "EARLIEST"
    LATEST = "LATEST"


class ResolvedRunTieBreak(StrEnum):
    """Deterministic tie-breaks for equal candidate pivot runs."""

    EARLIEST = "EARLIEST"
    LATEST = "LATEST"


class PivotRelationship(StrEnum):
    """Price relationships between two confirmed pivots of the same kind."""

    HIGHER = "HIGHER"
    LOWER = "LOWER"
    EQUAL = "EQUAL"


class LegScaleRelationship(StrEnum):
    """Magnitude relationships between two consecutive swing legs."""

    EXPANDING = "EXPANDING"
    CONTRACTING = "CONTRACTING"
    EQUAL = "EQUAL"


class PivotGeometryState(StrEnum):
    """Bounded geometric state inferred from same-kind pivot comparisons."""

    UPWARD = "UPWARD"
    DOWNWARD = "DOWNWARD"
    ROTATIONAL = "ROTATIONAL"
    MIXED = "MIXED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class PivotRevisionReference:
    """Cite the exact confirmed-swing revision used as a pivot."""

    entity_id: str
    revision: int
    kind: SwingKind
    pivot_price: Decimal
    pivot_ts_ns: int
    confirmation_ts_ns: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_id", _required_text(self.entity_id, "entity_id"))
        _positive_int(self.revision, "revision")
        if not isinstance(self.kind, SwingKind):
            raise ValueError("kind must be SwingKind")
        _positive_decimal(self.pivot_price, "pivot_price")
        _timestamp(self.pivot_ts_ns, "pivot_ts_ns")
        _timestamp(self.confirmation_ts_ns, "confirmation_ts_ns")


@dataclass(frozen=True, slots=True)
class SwingLegReference:
    """Cite the exact swing-leg revision used by pivot-structure state."""

    entity_id: str
    revision: int
    absolute_price_change: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_id", _required_text(self.entity_id, "entity_id"))
        _positive_int(self.revision, "revision")
        _non_negative_decimal(self.absolute_price_change, "absolute_price_change")


@dataclass(frozen=True, slots=True)
class PivotComparisonEvidence:
    """Describe one same-kind pivot price comparison and tolerance outcome."""

    previous: PivotRevisionReference
    current: PivotRevisionReference
    relationship: PivotRelationship
    price_change: Decimal
    percentage_change: Decimal
    duration_ns: int
    elapsed_bars: int
    slope_per_bar: Decimal
    slope_per_hour: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.previous, PivotRevisionReference):
            raise ValueError("previous must be PivotRevisionReference")
        if not isinstance(self.current, PivotRevisionReference):
            raise ValueError("current must be PivotRevisionReference")
        if self.previous.kind is not self.current.kind:
            raise ValueError("pivot comparisons require the same swing kind")
        if not isinstance(self.relationship, PivotRelationship):
            raise ValueError("relationship must be PivotRelationship")
        for field in ("price_change", "percentage_change", "slope_per_bar", "slope_per_hour"):
            _finite_decimal(getattr(self, field), field)
        _positive_int(self.duration_ns, "duration_ns")
        _positive_int(self.elapsed_bars, "elapsed_bars")


@dataclass(frozen=True, slots=True)
class LegScaleComparison:
    """Describe one adjacent-leg magnitude ratio and bounded relationship."""

    previous_leg: SwingLegReference
    current_leg: SwingLegReference
    ratio: Decimal
    relationship: LegScaleRelationship

    def __post_init__(self) -> None:
        if not isinstance(self.previous_leg, SwingLegReference):
            raise ValueError("previous_leg must be SwingLegReference")
        if not isinstance(self.current_leg, SwingLegReference):
            raise ValueError("current_leg must be SwingLegReference")
        _positive_decimal(self.ratio, "ratio")
        if not isinstance(self.relationship, LegScaleRelationship):
            raise ValueError("relationship must be LegScaleRelationship")


@dataclass(frozen=True, slots=True)
class SwingLegPayload(EntityPayload):
    """Preserve one alternating-pivot leg's geometry and optional path evidence."""

    definition_id: str
    chain_policy_id: str
    chain_policy_version: int
    horizon: str
    bar_specification: str
    origin: PivotRevisionReference
    destination: PivotRevisionReference
    price_change: Decimal
    percentage_change: Decimal
    duration_ns: int
    elapsed_bars: int
    slope_per_bar: Decimal
    slope_per_hour: Decimal
    volatility_normalization_id: str | None
    volatility_unit: Decimal | None
    volatility_normalized_displacement: Decimal | None
    volatility_normalized_slope_per_bar: Decimal | None
    path_efficiency: Decimal | None
    favorable_excursion: Decimal | None
    adverse_excursion: Decimal | None
    path_volume: Decimal | None
    path_bar_refs: tuple[str, ...]
    missing_context: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in ("definition_id", "chain_policy_id", "horizon", "bar_specification"):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        _positive_int(self.chain_policy_version, "chain_policy_version")
        if not isinstance(self.origin, PivotRevisionReference):
            raise ValueError("origin must be PivotRevisionReference")
        if not isinstance(self.destination, PivotRevisionReference):
            raise ValueError("destination must be PivotRevisionReference")
        if self.origin.kind is self.destination.kind:
            raise ValueError("swing legs require alternating pivot kinds")
        for field in ("price_change", "percentage_change", "slope_per_bar", "slope_per_hour"):
            _finite_decimal(getattr(self, field), field)
        _positive_int(self.duration_ns, "duration_ns")
        _positive_int(self.elapsed_bars, "elapsed_bars")
        optional_non_negative_decimals = (
            "volatility_unit",
            "path_efficiency",
            "favorable_excursion",
            "adverse_excursion",
            "path_volume",
        )
        for field in optional_non_negative_decimals:
            value = getattr(self, field)
            if value is not None:
                _non_negative_decimal(value, field)
        if self.volatility_unit is not None:
            _positive_decimal(self.volatility_unit, "volatility_unit")
        if self.path_efficiency is not None and self.path_efficiency > 1:
            raise ValueError("path_efficiency cannot exceed one")
        if self.volatility_normalized_displacement is not None:
            _finite_decimal(
                self.volatility_normalized_displacement,
                "volatility_normalized_displacement",
            )
        if self.volatility_normalized_slope_per_bar is not None:
            _finite_decimal(
                self.volatility_normalized_slope_per_bar,
                "volatility_normalized_slope_per_bar",
            )
        if self.volatility_normalization_id is not None:
            object.__setattr__(
                self,
                "volatility_normalization_id",
                _required_text(self.volatility_normalization_id, "volatility_normalization_id"),
            )
        object.__setattr__(
            self,
            "path_bar_refs",
            _text_tuple(self.path_bar_refs, "path_bar_refs"),
        )
        object.__setattr__(
            self,
            "missing_context",
            _text_tuple(self.missing_context, "missing_context"),
        )


@dataclass(frozen=True, slots=True)
class PivotStructurePayload(EntityPayload):
    """Preserve selected pivots, legs, comparisons, conflicts, and structure bounds."""

    definition_id: str
    chain_policy_id: str
    chain_policy_version: int
    detector_id: str
    detector_version: int
    horizon: str
    bar_specification: str
    selected_pivots: tuple[PivotRevisionReference, ...]
    selected_legs: tuple[SwingLegReference, ...]
    same_kind_comparisons: tuple[PivotComparisonEvidence, ...]
    leg_scale_comparisons: tuple[LegScaleComparison, ...]
    lower_bound: Decimal | None
    upper_bound: Decimal | None
    geometry_state: PivotGeometryState
    superseded_pivot_entity_ids: tuple[str, ...]
    unresolved_pivot_entity_ids: tuple[str, ...]
    relationship_conflicts: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in (
            "definition_id",
            "chain_policy_id",
            "detector_id",
            "horizon",
            "bar_specification",
        ):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))
        _positive_int(self.chain_policy_version, "chain_policy_version")
        _positive_int(self.detector_version, "detector_version")
        object.__setattr__(
            self,
            "selected_pivots",
            _typed_tuple(self.selected_pivots, PivotRevisionReference, "selected_pivots"),
        )
        if len({item.entity_id for item in self.selected_pivots}) != len(self.selected_pivots):
            raise ValueError("selected_pivots must contain unique entities")
        if any(
            previous.pivot_ts_ns >= current.pivot_ts_ns
            for previous, current in zip(
                self.selected_pivots,
                self.selected_pivots[1:],
                strict=False,
            )
        ):
            raise ValueError("selected_pivots must be strictly chronological")
        if any(
            previous.kind is current.kind
            for previous, current in zip(
                self.selected_pivots,
                self.selected_pivots[1:],
                strict=False,
            )
        ):
            raise ValueError("selected_pivots must alternate swing kinds")
        object.__setattr__(
            self,
            "selected_legs",
            _typed_tuple(self.selected_legs, SwingLegReference, "selected_legs"),
        )
        if len({item.entity_id for item in self.selected_legs}) != len(self.selected_legs):
            raise ValueError("selected_legs must contain unique entities")
        object.__setattr__(
            self,
            "same_kind_comparisons",
            _typed_tuple(
                self.same_kind_comparisons,
                PivotComparisonEvidence,
                "same_kind_comparisons",
            ),
        )
        object.__setattr__(
            self,
            "leg_scale_comparisons",
            _typed_tuple(
                self.leg_scale_comparisons,
                LegScaleComparison,
                "leg_scale_comparisons",
            ),
        )
        if (self.lower_bound is None) is not (self.upper_bound is None):
            raise ValueError("structure bounds must be both present or both absent")
        if self.lower_bound is not None and self.upper_bound is not None:
            _positive_decimal(self.lower_bound, "lower_bound")
            _positive_decimal(self.upper_bound, "upper_bound")
            if self.lower_bound > self.upper_bound:
                raise ValueError("lower_bound cannot exceed upper_bound")
        if not isinstance(self.geometry_state, PivotGeometryState):
            raise ValueError("geometry_state must be PivotGeometryState")
        for field in (
            "superseded_pivot_entity_ids",
            "unresolved_pivot_entity_ids",
            "relationship_conflicts",
        ):
            object.__setattr__(self, field, _text_tuple(getattr(self, field), field))


@dataclass(frozen=True, slots=True)
class PivotChainPolicy:
    """Configure pivot resolution, geometric tolerances, and retained evidence bounds."""

    policy_id: str
    version: int
    source_interval_ns: int
    same_kind_policy: SameKindPivotPolicy
    resolved_run_selection: ResolvedRunSelection
    resolved_run_tie_break: ResolvedRunTieBreak
    equality_tolerance: Decimal
    equality_tolerance_floor: Decimal
    equality_tolerance_ceiling: Decimal
    equality_tolerance_step: Decimal
    equality_tolerance_dynamic: bool
    minimum_leg_displacement: Decimal
    minimum_leg_displacement_floor: Decimal
    minimum_leg_displacement_ceiling: Decimal
    minimum_leg_displacement_step: Decimal
    minimum_leg_displacement_dynamic: bool
    leg_scale_ratio_tolerance: Decimal
    leg_scale_ratio_tolerance_floor: Decimal
    leg_scale_ratio_tolerance_ceiling: Decimal
    leg_scale_ratio_tolerance_step: Decimal
    leg_scale_ratio_tolerance_dynamic: bool
    maximum_retained_pivots: int
    maximum_retained_bars: int
    maximum_retained_normalizations: int
    maximum_selected_pivots: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _required_text(self.policy_id, "policy_id"))
        _positive_int(self.version, "version")
        _positive_int(self.source_interval_ns, "source_interval_ns")
        if not isinstance(self.same_kind_policy, SameKindPivotPolicy):
            raise ValueError("same_kind_policy must be SameKindPivotPolicy")
        if not isinstance(self.resolved_run_selection, ResolvedRunSelection):
            raise ValueError("resolved_run_selection must be ResolvedRunSelection")
        if not isinstance(self.resolved_run_tie_break, ResolvedRunTieBreak):
            raise ValueError("resolved_run_tie_break must be ResolvedRunTieBreak")
        _decimal_envelope(
            self.equality_tolerance,
            self.equality_tolerance_floor,
            self.equality_tolerance_ceiling,
            self.equality_tolerance_step,
            "equality_tolerance",
        )
        _decimal_envelope(
            self.minimum_leg_displacement,
            self.minimum_leg_displacement_floor,
            self.minimum_leg_displacement_ceiling,
            self.minimum_leg_displacement_step,
            "minimum_leg_displacement",
        )
        _decimal_envelope(
            self.leg_scale_ratio_tolerance,
            self.leg_scale_ratio_tolerance_floor,
            self.leg_scale_ratio_tolerance_ceiling,
            self.leg_scale_ratio_tolerance_step,
            "leg_scale_ratio_tolerance",
        )
        if self.leg_scale_ratio_tolerance_ceiling > 1:
            raise ValueError("leg_scale_ratio_tolerance_ceiling cannot exceed one")
        for field in (
            "equality_tolerance_dynamic",
            "minimum_leg_displacement_dynamic",
            "leg_scale_ratio_tolerance_dynamic",
        ):
            if not isinstance(getattr(self, field), bool):
                raise ValueError(f"{field} must be a boolean")
        for field in (
            "maximum_retained_pivots",
            "maximum_retained_bars",
            "maximum_retained_normalizations",
            "maximum_selected_pivots",
        ):
            _positive_int(getattr(self, field), field)
        if self.maximum_selected_pivots > self.maximum_retained_pivots:
            raise ValueError("maximum_selected_pivots cannot exceed retained pivots")


@dataclass(frozen=True, slots=True)
class PivotStructureApplication:
    """Scope pivot relationships to exact swing definitions, detectors, and horizons."""

    application_id: str
    analytical_profile_ids: tuple[str, ...]
    instrument_ids: tuple[str, ...]
    confirmed_swing_definition_ids: tuple[str, ...]
    detector_ids: tuple[str, ...]
    horizons: tuple[str, ...]
    bar_specifications: tuple[str, ...]
    parameter_version: int
    policy: PivotChainPolicy
    volatility_metric_id: str | None = None
    volatility_metric_version: int | None = None
    volatility_max_age_ns: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "application_id",
            _required_text(self.application_id, "application_id"),
        )
        for field in (
            "analytical_profile_ids",
            "confirmed_swing_definition_ids",
            "detector_ids",
            "horizons",
            "bar_specifications",
        ):
            object.__setattr__(self, field, _text_tuple(getattr(self, field), field, required=True))
        object.__setattr__(
            self,
            "instrument_ids",
            _text_tuple(self.instrument_ids, "instrument_ids"),
        )
        _positive_int(self.parameter_version, "parameter_version")
        if not isinstance(self.policy, PivotChainPolicy):
            raise ValueError("policy must be PivotChainPolicy")
        optional = (
            self.volatility_metric_id,
            self.volatility_metric_version,
            self.volatility_max_age_ns,
        )
        if any(item is not None for item in optional) and not all(
            item is not None for item in optional
        ):
            raise ValueError("volatility normalization fields must be configured together")
        if self.volatility_metric_id is not None:
            object.__setattr__(
                self,
                "volatility_metric_id",
                _required_text(self.volatility_metric_id, "volatility_metric_id"),
            )
            _positive_int(self.volatility_metric_version, "volatility_metric_version")
            _positive_int(self.volatility_max_age_ns, "volatility_max_age_ns")

    def matches(self, revision: EntityRevision) -> bool:
        payload = revision.payload
        return (
            isinstance(payload, ConfirmedSwingPayload)
            and revision.identity.analytical_profile_id in self.analytical_profile_ids
            and (not self.instrument_ids or revision.identity.instrument_id in self.instrument_ids)
            and payload.definition_id in self.confirmed_swing_definition_ids
            and payload.detector_id in self.detector_ids
            and payload.horizon in self.horizons
            and payload.bar_specification in self.bar_specifications
        )


@dataclass(frozen=True, slots=True)
class SwingNormalizationEvidence:
    """Carry optional versioned volatility evidence for one swing-leg subject."""

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
class MarketStructureRelationshipDefinition:
    """Bind confirmed swings to validated swing-leg and pivot-structure definitions."""

    definition_id: str
    confirmed_swing_definition: EntityDefinition
    swing_leg_definition: EntityDefinition
    pivot_structure_definition: EntityDefinition
    applications: tuple[PivotStructureApplication, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "definition_id",
            _required_text(self.definition_id, "definition_id"),
        )
        definitions = (
            self.confirmed_swing_definition,
            self.swing_leg_definition,
            self.pivot_structure_definition,
        )
        if any(not isinstance(item, EntityDefinition) for item in definitions):
            raise ValueError("relationship definitions must be EntityDefinition values")
        if self.confirmed_swing_definition.entity_type != CONFIRMED_SWING_ENTITY_TYPE:
            raise ValueError("confirmed-swing dependency must use confirmed_swing")
        if self.confirmed_swing_definition.payload_type is not ConfirmedSwingPayload:
            raise ValueError("confirmed-swing dependency must use ConfirmedSwingPayload")
        if self.swing_leg_definition.entity_type != SWING_LEG_ENTITY_TYPE:
            raise ValueError("swing-leg definition must use swing_leg")
        if self.swing_leg_definition.payload_type is not SwingLegPayload:
            raise ValueError("swing-leg definition must use SwingLegPayload")
        if self.swing_leg_definition.identity_dimensions != tuple(sorted(_SWING_LEG_DIMENSIONS)):
            raise ValueError("swing-leg identity dimensions do not match the contract")
        if self.pivot_structure_definition.entity_type != PIVOT_STRUCTURE_ENTITY_TYPE:
            raise ValueError("pivot-structure definition must use pivot_structure_state")
        if self.pivot_structure_definition.payload_type is not PivotStructurePayload:
            raise ValueError("pivot-structure definition must use PivotStructurePayload")
        if self.pivot_structure_definition.identity_dimensions != tuple(
            sorted(_PIVOT_STRUCTURE_DIMENSIONS)
        ):
            raise ValueError("pivot-structure identity dimensions do not match the contract")
        if any(item.durability is not EntityDurability.TRANSIENT for item in definitions[1:]):
            raise ValueError("market-structure relationships remain transient")
        swing_key = self.confirmed_swing_definition.key
        if swing_key not in {item.key for item in self.swing_leg_definition.entity_inputs}:
            raise ValueError("swing-leg definition must depend on confirmed swings")
        structure_dependencies = {
            item.key for item in self.pivot_structure_definition.entity_inputs
        }
        if swing_key not in structure_dependencies:
            raise ValueError("pivot structure must depend on confirmed swings")
        if self.swing_leg_definition.key not in structure_dependencies:
            raise ValueError("pivot structure must declare swing-leg evidence")
        object.__setattr__(
            self,
            "applications",
            _typed_tuple(
                self.applications,
                PivotStructureApplication,
                "applications",
                required=True,
            ),
        )
        application_ids = tuple(item.application_id for item in self.applications)
        if len(application_ids) != len(set(application_ids)):
            raise ValueError("relationship application IDs must be unique")
        declared_metrics = {item.key for item in self.swing_leg_definition.metric_inputs}
        for application in self.applications:
            if application.volatility_metric_id is None:
                continue
            metric_key = (
                application.volatility_metric_id,
                application.volatility_metric_version,
            )
            if metric_key not in declared_metrics:
                raise ValueError("application volatility metric must be declared by swing leg")
            dependency = next(
                item for item in self.swing_leg_definition.metric_inputs if item.key == metric_key
            )
            if dependency.required:
                raise ValueError("volatility normalization must remain optional evidence")


@dataclass(frozen=True, slots=True)
class MarketStructureRelationshipCounts:
    """Snapshot bounded relationship-owner admissions, publications, and evictions."""

    swings_accepted: int
    swings_duplicate: int
    swings_conflict: int
    bars_accepted: int
    bars_duplicate: int
    bars_conflict: int
    normalizations_accepted: int
    normalizations_duplicate: int
    normalizations_conflict: int
    revisions_published: int
    revisions_duplicate: int
    revisions_rejected: int
    entities_evicted: int
    publications_deferred: int


type _Subject = tuple[str, str, str, str, int, str, int, str, str]
type _BarSubject = tuple[str, str, int, str]
type _NormalizationSubject = tuple[str, int, str, str, int, str, str]


class MarketStructureRelationshipOwner:
    """Pure bounded relationship owner over immutable confirmed swings."""

    def __init__(
        self,
        *,
        definitions: tuple[MarketStructureRelationshipDefinition, ...],
        limits: EntityStateBookLimits,
        maximum_publications_per_cycle: int,
        source: str,
        schema_version: int,
    ) -> None:
        specs = _typed_tuple(
            definitions,
            MarketStructureRelationshipDefinition,
            "definitions",
            required=True,
        )
        _positive_int(maximum_publications_per_cycle, "maximum_publications_per_cycle")
        self._source = _required_text(source, "source")
        _positive_int(schema_version, "schema_version")
        self._schema_version = schema_version
        entity_definitions = tuple(
            definition
            for spec in specs
            for definition in (
                spec.confirmed_swing_definition,
                spec.swing_leg_definition,
                spec.pivot_structure_definition,
            )
        )
        unique_definitions: dict[tuple[str, int], EntityDefinition] = {}
        for definition in entity_definitions:
            current = unique_definitions.get(definition.key)
            if current is not None and current != definition:
                raise ValueError(f"conflicting relationship entity definition: {definition.key!r}")
            unique_definitions[definition.key] = definition
        metric_keys = {
            item.key
            for definition in unique_definitions.values()
            for item in definition.metric_inputs
        }
        registry = EntityRegistry(
            tuple(unique_definitions.values()),
            metric_keys=metric_keys,
        )
        self._definitions = specs
        self._book = EntityStateBook(registry, limits)
        self._maximum_publications = maximum_publications_per_cycle
        self._swings: dict[_Subject, dict[str, EntityRevision]] = {}
        self._bar_ledgers: dict[_BarSubject, CompletedBarLedger] = {}
        self._normalizations: dict[
            _NormalizationSubject,
            dict[tuple[str, int], SwingNormalizationEvidence],
        ] = {}
        self._pending: deque[EntityRevision] = deque()
        self._swings_accepted = 0
        self._swings_duplicate = 0
        self._swings_conflict = 0
        self._bars_accepted = 0
        self._bars_duplicate = 0
        self._bars_conflict = 0
        self._normalizations_accepted = 0
        self._normalizations_duplicate = 0
        self._normalizations_conflict = 0
        self._revisions_published = 0
        self._revisions_duplicate = 0
        self._revisions_rejected = 0
        self._entities_evicted = 0
        self._publications_deferred = 0

    def ingest_swing(self, revision: EntityRevision, *, now_ns: int) -> tuple[EntityRevision, ...]:
        payload = _confirmed_swing(revision)
        _timestamp(now_ns, "now_ns")
        for spec in self._definitions:
            if revision.identity.key != spec.confirmed_swing_definition.key:
                continue
            for application in spec.applications:
                if not application.matches(revision):
                    continue
                subject = _subject(spec, application, revision, payload)
                retained = self._swings.setdefault(subject, {})
                current = retained.get(revision.entity_id)
                if current is not None:
                    if current == revision:
                        self._swings_duplicate += 1
                    else:
                        self._swings_conflict += 1
                    continue
                retained[revision.entity_id] = revision
                self._swings_accepted += 1
                self._prune_swings(retained, application.policy.maximum_retained_pivots)
                self._reproject(spec, application, subject, now_ns=now_ns)
        return self._drain()

    def ingest_bar(self, bar: CompletedBarInput, *, now_ns: int) -> tuple[EntityRevision, ...]:
        if not isinstance(bar, CompletedBarInput) or not bar.complete:
            raise ValueError("relationship bar input must be a completed bar")
        _timestamp(now_ns, "now_ns")
        applications = self._applications_for_bar(bar)
        if not applications:
            return self._drain()
        key = _bar_subject(bar)
        maximum = max(item.policy.maximum_retained_bars for _, item in applications)
        ledger = self._bar_ledgers.setdefault(
            key,
            CompletedBarLedger(maximum_observations=maximum),
        )
        admission = ledger.admit(bar)
        if admission.status is BarAdmissionStatus.DUPLICATE:
            self._bars_duplicate += 1
            return self._drain()
        if admission.status is BarAdmissionStatus.CONFLICT:
            self._bars_conflict += 1
            return self._drain()
        self._bars_accepted += 1
        for spec, application, subject in self._matching_subjects_for_bar(bar):
            self._reproject(spec, application, subject, now_ns=now_ns)
        return self._drain()

    def ingest_normalization(
        self,
        evidence: SwingNormalizationEvidence,
        *,
        now_ns: int,
    ) -> tuple[EntityRevision, ...]:
        if not isinstance(evidence, SwingNormalizationEvidence):
            raise ValueError("normalization must be SwingNormalizationEvidence")
        _timestamp(now_ns, "now_ns")
        applications = self._applications_for_normalization(evidence)
        if not applications:
            return self._drain()
        subject_key = _normalization_subject(evidence)
        retained = self._normalizations.setdefault(subject_key, {})
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
        maximum = max(item.policy.maximum_retained_normalizations for _, item in applications)
        ordered = sorted(
            retained.values(),
            key=lambda item: (item.effective_ts_ns, item.reference_id, item.revision),
        )
        for stale in ordered[:-maximum]:
            retained.pop((stale.reference_id, stale.revision), None)
        for spec, application, subject in self._matching_subjects_for_normalization(evidence):
            self._reproject(spec, application, subject, now_ns=now_ns)
        return self._drain()

    def snapshot(
        self,
        generated_ts_ns: int,
        *,
        instrument_id: str | None = None,
        entity_type: str | None = None,
        dimensions: Mapping[str, str] | None = None,
    ) -> EntitySnapshot:
        if entity_type not in {None, SWING_LEG_ENTITY_TYPE, PIVOT_STRUCTURE_ENTITY_TYPE}:
            raise ValueError("relationship snapshot entity_type is not supported")
        return self._book.snapshot(
            generated_ts_ns,
            instrument_id=instrument_id,
            entity_type=entity_type,
            dimensions=dimensions,
        )

    @property
    def retained_swings(self) -> int:
        return sum(len(item) for item in self._swings.values())

    @property
    def retained_bars(self) -> int:
        return sum(len(item.bars) for item in self._bar_ledgers.values())

    @property
    def retained_normalizations(self) -> int:
        return sum(len(item) for item in self._normalizations.values())

    @property
    def retained_entities(self) -> int:
        return len(self._book)

    @property
    def counts(self) -> MarketStructureRelationshipCounts:
        return MarketStructureRelationshipCounts(
            self._swings_accepted,
            self._swings_duplicate,
            self._swings_conflict,
            self._bars_accepted,
            self._bars_duplicate,
            self._bars_conflict,
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
        spec: MarketStructureRelationshipDefinition,
        application: PivotStructureApplication,
        subject: _Subject,
        *,
        now_ns: int,
    ) -> None:
        swings = tuple(sorted(self._swings.get(subject, {}).values(), key=_swing_order))
        if not swings:
            return
        selected, superseded, unresolved = _select_chain(swings, application.policy)
        selected = selected[-application.policy.maximum_selected_pivots :]
        legs: list[EntityRevision] = []
        relationship_conflicts: list[str] = []
        for origin, destination in zip(selected, selected[1:], strict=False):
            origin_payload = _confirmed_swing(origin)
            destination_payload = _confirmed_swing(destination)
            if origin_payload.kind is destination_payload.kind:
                relationship_conflicts.append("selected_chain_is_not_alternating")
                continue
            if abs(destination_payload.pivot_price - origin_payload.pivot_price) < (
                application.policy.minimum_leg_displacement
            ):
                relationship_conflicts.append(
                    f"minimum_leg_displacement:{origin.entity_id}:{destination.entity_id}"
                )
                continue
            candidate = self._project_leg(
                spec,
                application,
                origin,
                destination,
                now_ns=now_ns,
            )
            leg = self._admit(candidate)
            if leg is not None:
                legs.append(leg)
        structure = _project_structure_revision(
            spec,
            application,
            swings,
            selected,
            tuple(legs),
            superseded,
            unresolved,
            tuple(sorted(set(relationship_conflicts))),
            current=self._current_structure(spec, application, swings[0]),
            now_ns=now_ns,
            source=self._source,
            schema_version=self._schema_version,
        )
        self._admit(structure)

    def _project_leg(
        self,
        spec: MarketStructureRelationshipDefinition,
        application: PivotStructureApplication,
        origin: EntityRevision,
        destination: EntityRevision,
        *,
        now_ns: int,
    ) -> EntityRevision:
        identity = _leg_identity(spec, application, origin, destination)
        current = self._book.get(identity.entity_id)
        origin_payload = _confirmed_swing(origin)
        path = _path_evidence(
            self._bar_ledgers.get(_bar_subject_from_revision(origin, origin_payload)),
            origin_payload,
            _confirmed_swing(destination),
            application.policy.source_interval_ns,
        )
        normalization_values: Iterable[SwingNormalizationEvidence] = ()
        if application.volatility_metric_id is not None:
            normalization_key = _normalization_subject_from_revision(
                application,
                destination,
                _confirmed_swing(destination),
            )
            normalization_values = self._normalizations.get(normalization_key, {}).values()
        normalization = _select_normalization(
            normalization_values,
            application,
            _confirmed_swing(destination).pivot_ts_ns,
        )
        return _project_leg_revision(
            spec,
            application,
            identity,
            origin,
            destination,
            path,
            normalization,
            current=current,
            now_ns=now_ns,
            source=self._source,
            schema_version=self._schema_version,
        )

    def _current_structure(
        self,
        spec: MarketStructureRelationshipDefinition,
        application: PivotStructureApplication,
        first: EntityRevision,
    ) -> EntityRevision | None:
        payload = _confirmed_swing(first)
        identity = _structure_identity(spec, application, first, payload)
        return self._book.get(identity.entity_id)

    def _matching_subjects_for_bar(
        self,
        bar: CompletedBarInput,
    ) -> tuple[
        tuple[MarketStructureRelationshipDefinition, PivotStructureApplication, _Subject],
        ...,
    ]:
        matches = []
        for subject in self._swings:
            spec, application = self._spec_application(subject)
            if (
                subject[2] == bar.instrument_id
                and subject[3] == bar.analytical_profile_id
                and subject[4] == bar.analytical_profile_version
                and subject[8] == bar.bar_specification
            ):
                matches.append((spec, application, subject))
        return tuple(matches)

    def _applications_for_bar(
        self,
        bar: CompletedBarInput,
    ) -> tuple[tuple[MarketStructureRelationshipDefinition, PivotStructureApplication], ...]:
        return tuple(
            (spec, application)
            for spec in self._definitions
            for application in spec.applications
            if bar.analytical_profile_id in application.analytical_profile_ids
            and (not application.instrument_ids or bar.instrument_id in application.instrument_ids)
            and bar.bar_specification in application.bar_specifications
        )

    def _matching_subjects_for_normalization(
        self,
        evidence: SwingNormalizationEvidence,
    ) -> tuple[
        tuple[MarketStructureRelationshipDefinition, PivotStructureApplication, _Subject],
        ...,
    ]:
        matches = []
        for subject in self._swings:
            spec, application = self._spec_application(subject)
            if (
                application.volatility_metric_id == evidence.metric_id
                and application.volatility_metric_version == evidence.metric_version
                and subject[2] == evidence.instrument_id
                and subject[3] == evidence.analytical_profile_id
                and subject[4] == evidence.analytical_profile_version
                and subject[7] == evidence.horizon
                and subject[8] == evidence.bar_specification
            ):
                matches.append((spec, application, subject))
        return tuple(matches)

    def _applications_for_normalization(
        self,
        evidence: SwingNormalizationEvidence,
    ) -> tuple[tuple[MarketStructureRelationshipDefinition, PivotStructureApplication], ...]:
        return tuple(
            (spec, application)
            for spec in self._definitions
            for application in spec.applications
            if application.volatility_metric_id == evidence.metric_id
            and application.volatility_metric_version == evidence.metric_version
            and evidence.analytical_profile_id in application.analytical_profile_ids
            and (
                not application.instrument_ids
                or evidence.instrument_id in application.instrument_ids
            )
            and evidence.horizon in application.horizons
            and evidence.bar_specification in application.bar_specifications
        )

    def _spec_application(
        self,
        subject: _Subject,
    ) -> tuple[MarketStructureRelationshipDefinition, PivotStructureApplication]:
        for spec in self._definitions:
            if spec.definition_id != subject[0]:
                continue
            for application in spec.applications:
                if application.application_id == subject[1]:
                    return spec, application
        raise RuntimeError("relationship subject lost its registered application")

    @staticmethod
    def _prune_swings(retained: dict[str, EntityRevision], maximum: int) -> None:
        ordered = sorted(retained.values(), key=_swing_order)
        for stale in ordered[:-maximum]:
            retained.pop(stale.entity_id, None)

    def _admit(self, revision: EntityRevision) -> EntityRevision | None:
        admission = self._book.admit(revision)
        if admission.status in {EntityAdmissionStatus.ADDED, EntityAdmissionStatus.UPDATED}:
            self._entities_evicted += len(admission.evicted_entity_ids)
            self._pending.append(revision)
            return revision
        elif admission.status is EntityAdmissionStatus.DUPLICATE:
            self._revisions_duplicate += 1
            return admission.current
        else:
            self._revisions_rejected += 1
            return admission.current

    def _drain(self) -> tuple[EntityRevision, ...]:
        revisions: list[EntityRevision] = []
        while self._pending and len(revisions) < self._maximum_publications:
            revisions.append(self._pending.popleft())
        self._revisions_published += len(revisions)
        if self._pending:
            self._publications_deferred += len(self._pending)
        return tuple(revisions)


@dataclass(frozen=True, slots=True)
class _PathEvidence:
    bars: tuple[CompletedBarInput, ...]
    complete: bool
    missing_reasons: tuple[str, ...]


def _subject(
    spec: MarketStructureRelationshipDefinition,
    application: PivotStructureApplication,
    revision: EntityRevision,
    payload: ConfirmedSwingPayload,
) -> _Subject:
    return (
        spec.definition_id,
        application.application_id,
        revision.identity.instrument_id,
        revision.identity.analytical_profile_id,
        revision.identity.analytical_profile_version,
        payload.detector_id,
        payload.detector_version,
        payload.horizon,
        payload.bar_specification,
    )


def _bar_subject(bar: CompletedBarInput) -> _BarSubject:
    return (
        bar.instrument_id,
        bar.analytical_profile_id,
        bar.analytical_profile_version,
        bar.bar_specification,
    )


def _bar_subject_from_revision(
    revision: EntityRevision,
    payload: ConfirmedSwingPayload,
) -> _BarSubject:
    return (
        revision.identity.instrument_id,
        revision.identity.analytical_profile_id,
        revision.identity.analytical_profile_version,
        payload.bar_specification,
    )


def _normalization_subject(evidence: SwingNormalizationEvidence) -> _NormalizationSubject:
    return (
        evidence.metric_id,
        evidence.metric_version,
        evidence.instrument_id,
        evidence.analytical_profile_id,
        evidence.analytical_profile_version,
        evidence.bar_specification,
        evidence.horizon,
    )


def _normalization_subject_from_revision(
    application: PivotStructureApplication,
    revision: EntityRevision,
    payload: ConfirmedSwingPayload,
) -> _NormalizationSubject:
    if application.volatility_metric_id is None or application.volatility_metric_version is None:
        raise ValueError("volatility normalization is not configured")
    return (
        application.volatility_metric_id,
        application.volatility_metric_version,
        revision.identity.instrument_id,
        revision.identity.analytical_profile_id,
        revision.identity.analytical_profile_version,
        payload.bar_specification,
        payload.horizon,
    )


def _select_chain(
    swings: tuple[EntityRevision, ...],
    policy: PivotChainPolicy,
) -> tuple[tuple[EntityRevision, ...], tuple[str, ...], tuple[str, ...]]:
    by_timestamp: list[tuple[EntityRevision, ...]] = []
    for swing in swings:
        payload = _confirmed_swing(swing)
        if (
            by_timestamp
            and _confirmed_swing(by_timestamp[-1][0]).pivot_ts_ns == payload.pivot_ts_ns
        ):
            by_timestamp[-1] = (*by_timestamp[-1], swing)
        else:
            by_timestamp.append((swing,))
    ordered: list[EntityRevision] = []
    unresolved: list[str] = []
    for timestamp_group in by_timestamp:
        kinds = {_confirmed_swing(item).kind for item in timestamp_group}
        if len(kinds) > 1:
            unresolved.extend(item.entity_id for item in timestamp_group)
            continue
        ordered.extend(timestamp_group)
    runs: list[list[EntityRevision]] = []
    for swing in ordered:
        if runs and _confirmed_swing(runs[-1][0]).kind is _confirmed_swing(swing).kind:
            runs[-1].append(swing)
        else:
            runs.append([swing])
    selected: list[EntityRevision] = []
    superseded: list[str] = []
    for index, run in enumerate(runs):
        terminal = index == len(runs) - 1
        if len(run) == 1:
            selected.append(run[0])
            continue
        if terminal and policy.same_kind_policy is SameKindPivotPolicy.UNRESOLVED_UNTIL_OPPOSITE:
            unresolved.extend(item.entity_id for item in run)
            continue
        if terminal and policy.same_kind_policy is SameKindPivotPolicy.LATEST_TERMINAL:
            chosen = run[-1]
        elif terminal and policy.same_kind_policy is SameKindPivotPolicy.MORE_EXTREME_TERMINAL:
            chosen = _select_run(
                run,
                ResolvedRunSelection.MORE_EXTREME,
                policy.resolved_run_tie_break,
            )
        else:
            chosen = _select_run(
                run,
                policy.resolved_run_selection,
                policy.resolved_run_tie_break,
            )
        selected.append(chosen)
        superseded.extend(item.entity_id for item in run if item.entity_id != chosen.entity_id)
    return tuple(selected), tuple(sorted(superseded)), tuple(sorted(set(unresolved)))


def _select_run(
    run: list[EntityRevision],
    selection: ResolvedRunSelection,
    tie_break: ResolvedRunTieBreak,
) -> EntityRevision:
    if selection is ResolvedRunSelection.EARLIEST:
        return run[0]
    if selection is ResolvedRunSelection.LATEST:
        return run[-1]
    kind = _confirmed_swing(run[0]).kind

    extreme_price = (
        max(_confirmed_swing(item).pivot_price for item in run)
        if kind is SwingKind.HIGH
        else min(_confirmed_swing(item).pivot_price for item in run)
    )
    tied = tuple(item for item in run if _confirmed_swing(item).pivot_price == extreme_price)
    return tied[0] if tie_break is ResolvedRunTieBreak.EARLIEST else tied[-1]


def _path_evidence(
    ledger: CompletedBarLedger | None,
    origin: ConfirmedSwingPayload,
    destination: ConfirmedSwingPayload,
    source_interval_ns: int,
) -> _PathEvidence:
    if ledger is None:
        return _PathEvidence((), False, ("path_bars_unavailable",))
    lower = min(origin.pivot_ts_ns, destination.pivot_ts_ns)
    upper = max(origin.pivot_ts_ns, destination.pivot_ts_ns)
    bars = tuple(item for item in ledger.bars if lower <= item.interval_end_ns <= upper)
    if not bars or bars[0].interval_end_ns != lower or bars[-1].interval_end_ns != upper:
        return _PathEvidence(bars, False, ("path_endpoint_bars_missing",))
    if any(item.interval_end_ns - item.interval_start_ns != source_interval_ns for item in bars):
        return _PathEvidence(bars, False, ("path_bar_interval_mismatch",))
    if any(
        previous.interval_end_ns != current.interval_start_ns
        for previous, current in zip(bars, bars[1:], strict=False)
    ):
        return _PathEvidence(bars, False, ("path_bars_non_contiguous",))
    return _PathEvidence(bars, True, ())


def _select_normalization(
    evidence: Iterable[SwingNormalizationEvidence],
    application: PivotStructureApplication,
    destination_ts_ns: int,
) -> SwingNormalizationEvidence | None:
    if application.volatility_metric_id is None:
        return None
    candidates = tuple(
        item
        for item in evidence
        if item.effective_ts_ns <= destination_ts_ns
        and destination_ts_ns - item.effective_ts_ns <= application.volatility_max_age_ns
    )
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (item.effective_ts_ns, item.revision, item.reference_id),
    )


def _project_leg_revision(
    spec: MarketStructureRelationshipDefinition,
    application: PivotStructureApplication,
    identity: EntityIdentity,
    origin: EntityRevision,
    destination: EntityRevision,
    path: _PathEvidence,
    normalization: SwingNormalizationEvidence | None,
    *,
    current: EntityRevision | None,
    now_ns: int,
    source: str,
    schema_version: int,
) -> EntityRevision:
    origin_payload = _confirmed_swing(origin)
    destination_payload = _confirmed_swing(destination)
    price_change = destination_payload.pivot_price - origin_payload.pivot_price
    percentage_change = price_change / origin_payload.pivot_price * Decimal("100")
    duration_ns = destination_payload.pivot_ts_ns - origin_payload.pivot_ts_ns
    elapsed_bars = duration_ns // application.policy.source_interval_ns
    if elapsed_bars <= 0 or duration_ns % application.policy.source_interval_ns:
        raise ValueError("pivot duration must align with configured source_interval_ns")
    slope_per_bar = price_change / Decimal(elapsed_bars)
    slope_per_hour = price_change / (Decimal(duration_ns) / Decimal(3_600_000_000_000))
    efficiency, favorable, adverse, volume = _path_metrics(
        origin_payload,
        destination_payload,
        path,
    )
    missing = list(path.missing_reasons)
    if path.complete and volume is None:
        missing.append("path_volume_incomplete")
    normalized_displacement = None
    normalized_slope = None
    normalization_id = None
    normalization_unit = None
    if application.volatility_metric_id is None:
        missing.append("volatility_normalization_not_configured")
    elif normalization is None:
        missing.append("volatility_normalization_unavailable")
    else:
        normalization_id = normalization.metric_id
        normalization_unit = normalization.value
        normalized_displacement = price_change / normalization.value
        normalized_slope = normalized_displacement / Decimal(elapsed_bars)
    payload = SwingLegPayload(
        definition_id=spec.definition_id,
        chain_policy_id=application.policy.policy_id,
        chain_policy_version=application.policy.version,
        horizon=origin_payload.horizon,
        bar_specification=origin_payload.bar_specification,
        origin=_pivot_ref(origin),
        destination=_pivot_ref(destination),
        price_change=price_change,
        percentage_change=percentage_change,
        duration_ns=duration_ns,
        elapsed_bars=elapsed_bars,
        slope_per_bar=slope_per_bar,
        slope_per_hour=slope_per_hour,
        volatility_normalization_id=normalization_id,
        volatility_unit=normalization_unit,
        volatility_normalized_displacement=normalized_displacement,
        volatility_normalized_slope_per_bar=normalized_slope,
        path_efficiency=efficiency,
        favorable_excursion=favorable,
        adverse_excursion=adverse,
        path_volume=volume,
        path_bar_refs=tuple(_bar_reference(item) for item in path.bars),
        missing_context=tuple(sorted(set(missing))),
    )
    evidence_refs = [_entity_evidence(origin), _entity_evidence(destination)]
    if normalization is not None:
        evidence_refs.append(_normalization_evidence(normalization))
    health = _least_healthy(
        (
            origin.health,
            destination.health,
            *(item.health for item in path.bars),
            *((normalization.health,) if normalization is not None else ()),
        )
    )
    fidelity = _least_fidelity(
        (
            origin.fidelity,
            destination.fidelity,
            *(item.fidelity for item in path.bars),
            *((normalization.fidelity,) if normalization is not None else ()),
        )
    )
    if payload.missing_context:
        fidelity = _least_fidelity((fidelity, MetricFidelity.PARTIAL))
    revision_number = 1 if current is None else current.revision + 1
    observed_ns = max(
        origin.observed_ts_ns,
        destination.observed_ts_ns,
        *(item.observed_ts_ns for item in path.bars),
    )
    published_ns = max(
        now_ns,
        origin.published_ts_ns,
        destination.published_ts_ns,
        *(item.normalized_ts_ns for item in path.bars),
    )
    return EntityRevision(
        identity=identity,
        revision=revision_number,
        previous_revision=None if current is None else current.revision,
        parameter_version=application.parameter_version,
        payload=payload,
        lifecycle=EntityLifecycle.COMPLETE,
        effective_ts_ns=destination_payload.confirmation_ts_ns,
        observed_ts_ns=observed_ns,
        calculated_ts_ns=max(now_ns, observed_ns),
        published_ts_ns=published_ns,
        health=health,
        fidelity=fidelity,
        evidence_refs=tuple(evidence_refs),
        missing_reasons=payload.missing_context,
        conflict_reasons=(),
        source=source,
        schema_version=schema_version,
    )


def _project_structure_revision(
    spec: MarketStructureRelationshipDefinition,
    application: PivotStructureApplication,
    all_swings: tuple[EntityRevision, ...],
    selected: tuple[EntityRevision, ...],
    legs: tuple[EntityRevision, ...],
    superseded: tuple[str, ...],
    unresolved: tuple[str, ...],
    conflicts: tuple[str, ...],
    *,
    current: EntityRevision | None,
    now_ns: int,
    source: str,
    schema_version: int,
) -> EntityRevision:
    first = all_swings[0]
    first_payload = _confirmed_swing(first)
    identity = _structure_identity(spec, application, first, first_payload)
    comparisons = _same_kind_comparisons(all_swings, application.policy)
    selected_entity_ids = {item.entity_id for item in selected}
    selected_comparisons = tuple(
        item
        for item in comparisons
        if item.previous.entity_id in selected_entity_ids
        and item.current.entity_id in selected_entity_ids
    )
    leg_refs = tuple(_leg_ref(item) for item in legs)
    leg_scale = _leg_scale_comparisons(leg_refs, application.policy)
    prices = tuple(_confirmed_swing(item).pivot_price for item in selected)
    lower_bound = min(prices) if prices else None
    upper_bound = max(prices) if prices else None
    payload = PivotStructurePayload(
        definition_id=spec.definition_id,
        chain_policy_id=application.policy.policy_id,
        chain_policy_version=application.policy.version,
        detector_id=first_payload.detector_id,
        detector_version=first_payload.detector_version,
        horizon=first_payload.horizon,
        bar_specification=first_payload.bar_specification,
        selected_pivots=tuple(_pivot_ref(item) for item in selected),
        selected_legs=leg_refs,
        same_kind_comparisons=comparisons,
        leg_scale_comparisons=leg_scale,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        geometry_state=_geometry_state(selected_comparisons),
        superseded_pivot_entity_ids=superseded,
        unresolved_pivot_entity_ids=unresolved,
        relationship_conflicts=conflicts,
    )
    evidence_refs = tuple(
        [
            *(_entity_evidence(item) for item in all_swings),
            *(_entity_evidence(item) for item in legs),
        ]
    )
    revision_number = 1 if current is None else current.revision + 1
    observed_ns = max(item.observed_ts_ns for item in all_swings)
    effective_ns = max(_confirmed_swing(item).confirmation_ts_ns for item in all_swings)
    health = _least_healthy(tuple(item.health for item in (*selected, *legs)) or (first.health,))
    fidelity = _least_fidelity(
        tuple(item.fidelity for item in (*selected, *legs)) or (first.fidelity,)
    )
    return EntityRevision(
        identity=identity,
        revision=revision_number,
        previous_revision=None if current is None else current.revision,
        parameter_version=application.parameter_version,
        payload=payload,
        lifecycle=EntityLifecycle.ACTIVE,
        effective_ts_ns=effective_ns,
        observed_ts_ns=observed_ns,
        calculated_ts_ns=max(now_ns, observed_ns),
        published_ts_ns=max(now_ns, *(item.published_ts_ns for item in all_swings)),
        health=health,
        fidelity=fidelity,
        evidence_refs=evidence_refs,
        missing_reasons=(),
        conflict_reasons=tuple(sorted((*unresolved, *conflicts))),
        source=source,
        schema_version=schema_version,
    )


def _same_kind_comparisons(
    selected: tuple[EntityRevision, ...],
    policy: PivotChainPolicy,
) -> tuple[PivotComparisonEvidence, ...]:
    comparisons = []
    prior: dict[SwingKind, EntityRevision] = {}
    for current in selected:
        current_payload = _confirmed_swing(current)
        previous = prior.get(current_payload.kind)
        prior[current_payload.kind] = current
        if previous is None:
            continue
        previous_payload = _confirmed_swing(previous)
        change = current_payload.pivot_price - previous_payload.pivot_price
        duration_ns = current_payload.pivot_ts_ns - previous_payload.pivot_ts_ns
        elapsed_bars = duration_ns // policy.source_interval_ns
        if elapsed_bars <= 0 or duration_ns % policy.source_interval_ns:
            raise ValueError("same-kind pivot duration must align with source interval")
        comparisons.append(
            PivotComparisonEvidence(
                previous=_pivot_ref(previous),
                current=_pivot_ref(current),
                relationship=_pivot_relationship(change, policy.equality_tolerance),
                price_change=change,
                percentage_change=change / previous_payload.pivot_price * Decimal("100"),
                duration_ns=duration_ns,
                elapsed_bars=elapsed_bars,
                slope_per_bar=change / Decimal(elapsed_bars),
                slope_per_hour=change / (Decimal(duration_ns) / Decimal(3_600_000_000_000)),
            )
        )
    return tuple(comparisons)


def _leg_scale_comparisons(
    legs: tuple[SwingLegReference, ...],
    policy: PivotChainPolicy,
) -> tuple[LegScaleComparison, ...]:
    comparisons = []
    for previous, current in zip(legs, legs[1:], strict=False):
        if previous.absolute_price_change == 0:
            continue
        ratio = current.absolute_price_change / previous.absolute_price_change
        upper = Decimal("1") + policy.leg_scale_ratio_tolerance
        lower = Decimal("1") - policy.leg_scale_ratio_tolerance
        if ratio > upper:
            relationship = LegScaleRelationship.EXPANDING
        elif ratio < lower:
            relationship = LegScaleRelationship.CONTRACTING
        else:
            relationship = LegScaleRelationship.EQUAL
        comparisons.append(LegScaleComparison(previous, current, ratio, relationship))
    return tuple(comparisons)


def _geometry_state(comparisons: tuple[PivotComparisonEvidence, ...]) -> PivotGeometryState:
    latest = {item.current.kind: item.relationship for item in comparisons}
    if SwingKind.HIGH not in latest or SwingKind.LOW not in latest:
        return PivotGeometryState.INSUFFICIENT
    high = latest[SwingKind.HIGH]
    low = latest[SwingKind.LOW]
    if high is PivotRelationship.HIGHER and low is PivotRelationship.HIGHER:
        return PivotGeometryState.UPWARD
    if high is PivotRelationship.LOWER and low is PivotRelationship.LOWER:
        return PivotGeometryState.DOWNWARD
    if high in {PivotRelationship.LOWER, PivotRelationship.EQUAL} and low in {
        PivotRelationship.HIGHER,
        PivotRelationship.EQUAL,
    }:
        return PivotGeometryState.ROTATIONAL
    return PivotGeometryState.MIXED


def _path_metrics(
    origin: ConfirmedSwingPayload,
    destination: ConfirmedSwingPayload,
    path: _PathEvidence,
) -> tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None]:
    if not path.complete:
        return None, None, None, None
    price_change = destination.pivot_price - origin.pivot_price
    closes = (
        origin.pivot_price,
        *(item.close for item in path.bars[1:-1]),
        destination.pivot_price,
    )
    path_distance = sum(
        (abs(current - previous) for previous, current in zip(closes, closes[1:], strict=False)),
        Decimal("0"),
    )
    efficiency = Decimal("1") if path_distance == 0 else abs(price_change) / path_distance
    highest = max(item.high for item in path.bars)
    lowest = min(item.low for item in path.bars)
    if price_change >= 0:
        favorable = max(highest - origin.pivot_price, Decimal("0"))
        adverse = max(origin.pivot_price - lowest, Decimal("0"))
    else:
        favorable = max(origin.pivot_price - lowest, Decimal("0"))
        adverse = max(highest - origin.pivot_price, Decimal("0"))
    volume = (
        sum((item.volume for item in path.bars if item.volume is not None), Decimal("0"))
        if all(item.volume is not None for item in path.bars)
        else None
    )
    return efficiency, favorable, adverse, volume


def _leg_identity(
    spec: MarketStructureRelationshipDefinition,
    application: PivotStructureApplication,
    origin: EntityRevision,
    destination: EntityRevision,
) -> EntityIdentity:
    payload = _confirmed_swing(origin)
    return EntityIdentity(
        entity_type=spec.swing_leg_definition.entity_type,
        entity_version=spec.swing_leg_definition.version,
        instrument_id=origin.identity.instrument_id,
        analytical_profile_id=origin.identity.analytical_profile_id,
        analytical_profile_version=origin.identity.analytical_profile_version,
        dimensions=(
            EntityIdentityDimension("bar_specification", payload.bar_specification),
            EntityIdentityDimension("chain_policy_id", application.policy.policy_id),
            EntityIdentityDimension("chain_policy_version", str(application.policy.version)),
            EntityIdentityDimension("definition_id", spec.definition_id),
            EntityIdentityDimension("destination_entity_id", destination.entity_id),
            EntityIdentityDimension("horizon", payload.horizon),
            EntityIdentityDimension("origin_entity_id", origin.entity_id),
        ),
    )


def _structure_identity(
    spec: MarketStructureRelationshipDefinition,
    application: PivotStructureApplication,
    first: EntityRevision,
    payload: ConfirmedSwingPayload,
) -> EntityIdentity:
    return EntityIdentity(
        entity_type=spec.pivot_structure_definition.entity_type,
        entity_version=spec.pivot_structure_definition.version,
        instrument_id=first.identity.instrument_id,
        analytical_profile_id=first.identity.analytical_profile_id,
        analytical_profile_version=first.identity.analytical_profile_version,
        dimensions=(
            EntityIdentityDimension("bar_specification", payload.bar_specification),
            EntityIdentityDimension("chain_policy_id", application.policy.policy_id),
            EntityIdentityDimension("chain_policy_version", str(application.policy.version)),
            EntityIdentityDimension("definition_id", spec.definition_id),
            EntityIdentityDimension("detector_id", payload.detector_id),
            EntityIdentityDimension("detector_version", str(payload.detector_version)),
            EntityIdentityDimension("horizon", payload.horizon),
        ),
    )


def _pivot_ref(revision: EntityRevision) -> PivotRevisionReference:
    payload = _confirmed_swing(revision)
    return PivotRevisionReference(
        revision.entity_id,
        revision.revision,
        payload.kind,
        payload.pivot_price,
        payload.pivot_ts_ns,
        payload.confirmation_ts_ns,
    )


def _leg_ref(revision: EntityRevision) -> SwingLegReference:
    payload = revision.payload
    if not isinstance(payload, SwingLegPayload):
        raise ValueError("swing-leg reference requires SwingLegPayload")
    return SwingLegReference(revision.entity_id, revision.revision, abs(payload.price_change))


def _entity_evidence(revision: EntityRevision) -> EntityEvidenceReference:
    return EntityEvidenceReference(
        EntityEvidenceKind.ENTITY,
        revision.identity.entity_type,
        revision.entity_id,
        revision.identity.entity_version,
        revision.revision,
        revision.effective_ts_ns,
        revision.health,
        revision.fidelity,
    )


def _normalization_evidence(
    evidence: SwingNormalizationEvidence,
) -> EntityEvidenceReference:
    return EntityEvidenceReference(
        EntityEvidenceKind.METRIC,
        evidence.metric_id,
        evidence.reference_id,
        evidence.metric_version,
        evidence.revision,
        evidence.effective_ts_ns,
        evidence.health,
        evidence.fidelity,
    )


def _confirmed_swing(revision: EntityRevision) -> ConfirmedSwingPayload:
    if not isinstance(revision, EntityRevision):
        raise ValueError("confirmed swing must be EntityRevision")
    if revision.identity.entity_type != CONFIRMED_SWING_ENTITY_TYPE:
        raise ValueError("relationship input must be a confirmed_swing entity")
    if revision.lifecycle is not EntityLifecycle.COMPLETE:
        raise ValueError("relationship input must be a complete confirmed swing")
    if not isinstance(revision.payload, ConfirmedSwingPayload):
        raise ValueError("relationship input payload must be ConfirmedSwingPayload")
    return revision.payload


def _swing_order(revision: EntityRevision) -> tuple[int, str, str]:
    payload = _confirmed_swing(revision)
    return (payload.pivot_ts_ns, payload.kind.value, revision.entity_id)


def _pivot_relationship(change: Decimal, tolerance: Decimal) -> PivotRelationship:
    if abs(change) <= tolerance:
        return PivotRelationship.EQUAL
    return PivotRelationship.HIGHER if change > 0 else PivotRelationship.LOWER


def _bar_reference(bar: CompletedBarInput) -> str:
    return (
        f"completed_bar:{bar.instrument_id}:{bar.bar_specification}:"
        f"{bar.interval_end_ns}:{bar.revision}"
    )


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


def _positive_decimal(value: object, field: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ValueError(f"{field} must be a positive finite Decimal")
    return value


def _non_negative_decimal(value: object, field: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError(f"{field} must be a non-negative finite Decimal")
    return value


def _decimal_envelope(
    value: Decimal,
    minimum: Decimal,
    maximum: Decimal,
    step: Decimal,
    field: str,
) -> None:
    for candidate in (value, minimum, maximum, step):
        if not isinstance(candidate, Decimal) or not candidate.is_finite():
            raise ValueError(f"{field} envelope values must be finite Decimal values")
    if minimum < 0 or maximum < minimum or step <= 0:
        raise ValueError(f"{field} envelope is invalid")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field} is outside its configured envelope")
    if (value - minimum) % step:
        raise ValueError(f"{field} does not align to its configured step")


def _finite_decimal(value: object, field: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{field} must be a finite Decimal")
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
