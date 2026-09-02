from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from markeitech.intelligence.entities import (
    EntityDefinition,
    EntityDependency,
    EntityDurability,
    EntityLifecycle,
    EntityMetricDependency,
)
from markeitech.intelligence.entity_measurements import (
    FvgGeometryPolicy,
    SwingGeometryPolicy,
)
from markeitech.intelligence.fvg_entities import (
    FVG_ENTITY_TYPE,
    FvgApplication,
    FvgEntityDefinition,
    FvgLifecyclePolicy,
    FvgPayload,
    FvgTerminalOutcome,
)
from markeitech.intelligence.market_structure_entities import (
    CONFIRMED_SWING_ENTITY_TYPE,
    ConfirmedSwingApplication,
    ConfirmedSwingDefinition,
    ConfirmedSwingPayload,
)
from markeitech.intelligence.market_structure_relationships import (
    PIVOT_STRUCTURE_ENTITY_TYPE,
    SWING_LEG_ENTITY_TYPE,
    MarketStructureRelationshipDefinition,
    PivotChainPolicy,
    PivotStructureApplication,
    PivotStructurePayload,
    ResolvedRunSelection,
    ResolvedRunTieBreak,
    SameKindPivotPolicy,
    SwingLegPayload,
)
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth
from markeitech.intelligence.session_entities import ObjectiveLevelPayload
from markeitech.intelligence.zone_entities import (
    DERIVED_ZONE_ENTITY_TYPE,
    DerivedZoneDefinition,
    DerivedZonePayload,
    ZoneApplication,
    ZoneHorizonPolicy,
    ZonePartitionMethod,
    ZonePolicy,
    ZoneSourcePolicy,
    ZoneWeightingMethod,
)


@dataclass(frozen=True, slots=True)
class MarketStructureRuntimeDefinitions:
    confirmed_swings: tuple[ConfirmedSwingDefinition, ...]
    relationships: tuple[MarketStructureRelationshipDefinition, ...]
    fvgs: tuple[FvgEntityDefinition, ...]
    zones: tuple[DerivedZoneDefinition, ...]

    @property
    def definition_count(self) -> int:
        return (
            len(self.confirmed_swings)
            + (2 * len(self.relationships))
            + len(self.fvgs)
            + len(self.zones)
        )


def resolve_market_structure_definitions(
    raw_definitions: Sequence[Mapping[str, object]],
    *,
    eligible_instrument_ids: tuple[str, ...],
) -> MarketStructureRuntimeDefinitions:
    """Resolve the reviewed generic catalog into exact runtime owner contracts."""

    raw_by_type = {_text(item["entity_type"], "entity_type"): item for item in raw_definitions}
    if len(raw_by_type) != len(raw_definitions):
        raise ValueError("market-structure runtime entity types must be unique")
    supported = {
        CONFIRMED_SWING_ENTITY_TYPE,
        SWING_LEG_ENTITY_TYPE,
        PIVOT_STRUCTURE_ENTITY_TYPE,
        FVG_ENTITY_TYPE,
        DERIVED_ZONE_ENTITY_TYPE,
    }
    unsupported = sorted(set(raw_by_type) - supported)
    if unsupported:
        raise ValueError(
            "market-structure runtime received unsupported entity types: " + ", ".join(unsupported),
        )

    typed_by_type = {
        entity_type: _entity_definition(raw) for entity_type, raw in raw_by_type.items()
    }
    confirmed = ()
    if CONFIRMED_SWING_ENTITY_TYPE in raw_by_type:
        raw = raw_by_type[CONFIRMED_SWING_ENTITY_TYPE]
        confirmed = (
            ConfirmedSwingDefinition(
                definition_id=_text(raw["definition_id"], "definition_id"),
                definition=typed_by_type[CONFIRMED_SWING_ENTITY_TYPE],
                applications=tuple(
                    _confirmed_swing_application(raw, item, eligible_instrument_ids)
                    for item in _mappings(raw["applications"], "applications")
                ),
            ),
        )

    fvgs = ()
    if FVG_ENTITY_TYPE in raw_by_type:
        raw = raw_by_type[FVG_ENTITY_TYPE]
        fvgs = (
            FvgEntityDefinition(
                definition_id=_text(raw["definition_id"], "definition_id"),
                definition=typed_by_type[FVG_ENTITY_TYPE],
                applications=tuple(
                    _fvg_application(raw, item, eligible_instrument_ids)
                    for item in _mappings(raw["applications"], "applications")
                ),
            ),
        )

    relationships = ()
    relationship_types = {SWING_LEG_ENTITY_TYPE, PIVOT_STRUCTURE_ENTITY_TYPE}
    present_relationship_types = relationship_types & set(raw_by_type)
    if present_relationship_types:
        required = relationship_types | {CONFIRMED_SWING_ENTITY_TYPE}
        missing = sorted(required - set(raw_by_type))
        if missing:
            raise ValueError(
                "market-structure relationships require entity definitions: " + ", ".join(missing),
            )
        _validate_relationship_companions(
            raw_by_type[SWING_LEG_ENTITY_TYPE],
            raw_by_type[PIVOT_STRUCTURE_ENTITY_TYPE],
        )
        raw = raw_by_type[PIVOT_STRUCTURE_ENTITY_TYPE]
        relationships = (
            MarketStructureRelationshipDefinition(
                definition_id=_text(raw["definition_id"], "definition_id"),
                confirmed_swing_definition=typed_by_type[CONFIRMED_SWING_ENTITY_TYPE],
                swing_leg_definition=typed_by_type[SWING_LEG_ENTITY_TYPE],
                pivot_structure_definition=typed_by_type[PIVOT_STRUCTURE_ENTITY_TYPE],
                applications=tuple(
                    _relationship_application(
                        raw,
                        item,
                        confirmed[0],
                        eligible_instrument_ids,
                    )
                    for item in _mappings(raw["applications"], "applications")
                ),
            ),
        )

    zones = ()
    if DERIVED_ZONE_ENTITY_TYPE in raw_by_type:
        raw = raw_by_type[DERIVED_ZONE_ENTITY_TYPE]
        source_keys = {
            (_text(item["entity_type"], "entity_input.entity_type"), int(item["entity_version"]))
            for item in _mappings(raw["entity_inputs"], "entity_inputs")
        }
        source_definitions = tuple(
            definition for definition in typed_by_type.values() if definition.key in source_keys
        )
        if {item.key for item in source_definitions} != source_keys:
            missing = sorted(source_keys - {item.key for item in source_definitions})
            raise ValueError(f"derived-zone source definitions are unavailable: {missing}")
        zones = (
            DerivedZoneDefinition(
                definition_id=_text(raw["definition_id"], "definition_id"),
                definition=typed_by_type[DERIVED_ZONE_ENTITY_TYPE],
                source_definitions=source_definitions,
                applications=tuple(
                    _zone_application(
                        raw,
                        item,
                        source_definitions,
                        raw_by_type,
                        eligible_instrument_ids,
                    )
                    for item in _mappings(raw["applications"], "applications")
                ),
            ),
        )

    if not any((confirmed, relationships, fvgs, zones)):
        raise ValueError("market-structure runtime requires at least one supported definition")
    return MarketStructureRuntimeDefinitions(confirmed, relationships, fvgs, zones)


def _entity_definition(raw: Mapping[str, object]) -> EntityDefinition:
    entity_type = _text(raw["entity_type"], "entity_type")
    payload_types = {
        CONFIRMED_SWING_ENTITY_TYPE: ConfirmedSwingPayload,
        SWING_LEG_ENTITY_TYPE: SwingLegPayload,
        PIVOT_STRUCTURE_ENTITY_TYPE: PivotStructurePayload,
        FVG_ENTITY_TYPE: FvgPayload,
        DERIVED_ZONE_ENTITY_TYPE: DerivedZonePayload,
    }
    if entity_type.startswith("objective_level."):
        payload_type = ObjectiveLevelPayload
    else:
        try:
            payload_type = payload_types[entity_type]
        except KeyError as exc:
            raise ValueError(f"unsupported runtime entity type: {entity_type}") from exc
    return EntityDefinition(
        entity_type=entity_type,
        version=int(raw["entity_version"]),
        decision_question=_text(raw["decision_question"], "decision_question"),
        implementation_id=_text(raw["implementation_id"], "implementation_id"),
        payload_type=payload_type,
        identity_dimensions=tuple(str(item) for item in raw["identity_dimensions"]),
        metric_inputs=tuple(
            EntityMetricDependency(
                _text(item["metric_id"], "metric_input.metric_id"),
                int(item["metric_version"]),
                bool(item["required"]),
                tuple(MetricHealth(str(value)) for value in item["permitted_health"]),
                tuple(MetricFidelity(str(value)) for value in item["permitted_fidelities"]),
            )
            for item in _mappings(raw["metric_inputs"], "metric_inputs")
        ),
        entity_inputs=tuple(
            EntityDependency(
                _text(item["entity_type"], "entity_input.entity_type"),
                int(item["entity_version"]),
                bool(item["required"]),
                tuple(MetricHealth(str(value)) for value in item["permitted_health"]),
                tuple(MetricFidelity(str(value)) for value in item["permitted_fidelities"]),
            )
            for item in _mappings(raw["entity_inputs"], "entity_inputs")
        ),
        permitted_health=tuple(MetricHealth(str(value)) for value in raw["permitted_health"]),
        permitted_fidelities=tuple(
            MetricFidelity(str(value)) for value in raw["permitted_fidelities"]
        ),
        durability=EntityDurability(str(raw["durability"])),
        completion_rule=_text(raw["completion_rule"], "completion_rule"),
        invalidation_rule=_text(raw["invalidation_rule"], "invalidation_rule"),
        expiry_rule=_text(raw["expiry_rule"], "expiry_rule"),
    )


def _confirmed_swing_application(
    raw: Mapping[str, object],
    application: Mapping[str, object],
    eligible_instrument_ids: tuple[str, ...],
) -> ConfirmedSwingApplication:
    binding = _ParameterBinding(raw, application)
    return ConfirmedSwingApplication(
        application_id=binding.application_id,
        detector_id=binding.text("detector_id"),
        detector_version=int(raw["formula_version"]),
        analytical_profile_ids=binding.profile_ids,
        instrument_ids=binding.instrument_ids(eligible_instrument_ids),
        bar_specifications=(binding.source_selector,),
        horizon=binding.horizon,
        parameter_version=binding.parameter_version,
        policy=SwingGeometryPolicy(
            left_span_bars=binding.integer("left_span_bars"),
            minimum_left_span_bars=binding.minimum_int("left_span_bars"),
            maximum_left_span_bars=binding.maximum_int("left_span_bars"),
            left_span_step=binding.step_int("left_span_bars"),
            left_span_dynamic=binding.dynamic("left_span_bars"),
            right_span_bars=binding.integer("right_span_bars"),
            minimum_right_span_bars=binding.minimum_int("right_span_bars"),
            maximum_right_span_bars=binding.maximum_int("right_span_bars"),
            right_span_step=binding.step_int("right_span_bars"),
            right_span_dynamic=binding.dynamic("right_span_bars"),
            minimum_prominence=binding.decimal("minimum_prominence"),
            minimum_prominence_floor=binding.minimum_decimal("minimum_prominence"),
            minimum_prominence_ceiling=binding.maximum_decimal("minimum_prominence"),
            minimum_prominence_step=binding.step_decimal("minimum_prominence"),
            minimum_prominence_dynamic=binding.dynamic("minimum_prominence"),
            tie_policy=binding.text("tie_policy"),
        ),
        maximum_retained_bars=binding.integer("maximum_retained_bars"),
    )


def _relationship_application(
    raw: Mapping[str, object],
    application: Mapping[str, object],
    confirmed: ConfirmedSwingDefinition,
    eligible_instrument_ids: tuple[str, ...],
) -> PivotStructureApplication:
    binding = _ParameterBinding(raw, application)
    target_instruments = binding.instrument_ids(eligible_instrument_ids)
    target_scope = _application_scope(target_instruments, binding.profile_ids)
    matching_swings = tuple(
        item
        for item in confirmed.applications
        if item.horizon == binding.horizon
        and binding.source_selector in item.bar_specifications
        and set(item.analytical_profile_ids) & set(binding.profile_ids)
    )
    covered_scope = {
        scope
        for item in matching_swings
        for scope in _application_scope(item.instrument_ids, item.analytical_profile_ids)
    }
    if not target_scope.issubset(covered_scope):
        uncovered = sorted(target_scope - covered_scope)
        raise ValueError(
            f"relationship application {binding.application_id} has uncovered swing scope: "
            f"{uncovered!r}",
        )
    return PivotStructureApplication(
        application_id=binding.application_id,
        analytical_profile_ids=binding.profile_ids,
        instrument_ids=target_instruments,
        confirmed_swing_definition_ids=(confirmed.definition_id,),
        detector_ids=tuple(sorted({item.detector_id for item in matching_swings})),
        horizons=(binding.horizon,),
        bar_specifications=(binding.source_selector,),
        parameter_version=binding.parameter_version,
        policy=PivotChainPolicy(
            policy_id=binding.text("policy_id"),
            version=int(raw["formula_version"]),
            source_interval_ns=binding.integer("source_interval_ms") * 1_000_000,
            same_kind_policy=SameKindPivotPolicy(binding.text("same_kind_policy")),
            resolved_run_selection=ResolvedRunSelection(
                binding.text("resolved_run_selection"),
            ),
            resolved_run_tie_break=ResolvedRunTieBreak(
                binding.text("resolved_run_tie_break"),
            ),
            equality_tolerance=binding.decimal("equality_tolerance"),
            equality_tolerance_floor=binding.minimum_decimal("equality_tolerance"),
            equality_tolerance_ceiling=binding.maximum_decimal("equality_tolerance"),
            equality_tolerance_step=binding.step_decimal("equality_tolerance"),
            equality_tolerance_dynamic=binding.dynamic("equality_tolerance"),
            minimum_leg_displacement=binding.decimal("minimum_leg_displacement"),
            minimum_leg_displacement_floor=binding.minimum_decimal(
                "minimum_leg_displacement",
            ),
            minimum_leg_displacement_ceiling=binding.maximum_decimal(
                "minimum_leg_displacement",
            ),
            minimum_leg_displacement_step=binding.step_decimal(
                "minimum_leg_displacement",
            ),
            minimum_leg_displacement_dynamic=binding.dynamic(
                "minimum_leg_displacement",
            ),
            leg_scale_ratio_tolerance=binding.decimal("leg_scale_ratio_tolerance"),
            leg_scale_ratio_tolerance_floor=binding.minimum_decimal(
                "leg_scale_ratio_tolerance",
            ),
            leg_scale_ratio_tolerance_ceiling=binding.maximum_decimal(
                "leg_scale_ratio_tolerance",
            ),
            leg_scale_ratio_tolerance_step=binding.step_decimal(
                "leg_scale_ratio_tolerance",
            ),
            leg_scale_ratio_tolerance_dynamic=binding.dynamic(
                "leg_scale_ratio_tolerance",
            ),
            maximum_retained_pivots=binding.integer("maximum_retained_pivots"),
            maximum_retained_bars=binding.integer("maximum_retained_bars"),
            maximum_retained_normalizations=binding.integer(
                "maximum_retained_normalizations",
            ),
            maximum_selected_pivots=binding.integer("maximum_selected_pivots"),
        ),
    )


def _fvg_application(
    raw: Mapping[str, object],
    application: Mapping[str, object],
    eligible_instrument_ids: tuple[str, ...],
) -> FvgApplication:
    binding = _ParameterBinding(raw, application)
    return FvgApplication(
        application_id=binding.application_id,
        analytical_profile_ids=binding.profile_ids,
        instrument_ids=binding.instrument_ids(eligible_instrument_ids),
        bar_specifications=(binding.source_selector,),
        horizon=binding.horizon,
        parameter_version=binding.parameter_version,
        policy=FvgLifecyclePolicy(
            policy_id=binding.text("policy_id"),
            version=int(raw["formula_version"]),
            source_interval_ns=binding.integer("source_interval_ms") * 1_000_000,
            geometry=FvgGeometryPolicy(
                pattern_length=binding.integer("pattern_length"),
                minimum_width=binding.decimal("minimum_width"),
                minimum_width_floor=binding.minimum_decimal("minimum_width"),
                minimum_width_ceiling=binding.maximum_decimal("minimum_width"),
                minimum_width_step=binding.step_decimal("minimum_width"),
                minimum_width_dynamic=binding.dynamic("minimum_width"),
                price_basis=binding.text("price_basis"),
                fill_method=binding.text("fill_method"),
            ),
            terminal_outcome=FvgTerminalOutcome(binding.text("terminal_outcome")),
            maximum_age_bars=binding.integer("maximum_age_bars"),
            minimum_age_bars=binding.minimum_int("maximum_age_bars"),
            maximum_age_bars_ceiling=binding.maximum_int("maximum_age_bars"),
            age_step_bars=binding.step_int("maximum_age_bars"),
            maximum_age_dynamic=binding.dynamic("maximum_age_bars"),
            maximum_retained_bars=binding.integer("maximum_retained_bars"),
            maximum_retained_normalizations=binding.integer(
                "maximum_retained_normalizations",
            ),
        ),
    )


def _zone_application(
    raw: Mapping[str, object],
    application: Mapping[str, object],
    sources: tuple[EntityDefinition, ...],
    source_catalog: Mapping[str, Mapping[str, object]],
    eligible_instrument_ids: tuple[str, ...],
) -> ZoneApplication:
    binding = _ParameterBinding(raw, application)
    target_instruments = binding.instrument_ids(eligible_instrument_ids)
    target_scope = _application_scope(target_instruments, binding.profile_ids)
    for source in sources:
        source_raw = source_catalog.get(source.entity_type)
        if source_raw is None:
            raise ValueError(f"derived-zone source application is unavailable: {source.key!r}")
        covered_scope = _compatible_source_scope(
            source_raw,
            horizon=binding.horizon,
            source_selector=binding.source_selector,
            eligible_instrument_ids=eligible_instrument_ids,
        )
        if not target_scope.issubset(covered_scope):
            uncovered = sorted(target_scope - covered_scope)
            raise ValueError(
                f"zone application {binding.application_id} has uncovered "
                f"{source.entity_type} scope: {uncovered!r}",
            )
    source_policies = tuple(
        ZoneSourcePolicy(
            entity_type=source.entity_type,
            entity_version=source.version,
            horizons=(binding.horizon,),
            lifecycles=_zone_source_lifecycles(source.entity_type),
            include_developing=False,
        )
        for source in sources
    )
    return ZoneApplication(
        application_id=binding.application_id,
        analytical_profile_ids=binding.profile_ids,
        instrument_ids=target_instruments,
        parameter_version=binding.parameter_version,
        policy=ZonePolicy(
            policy_id=binding.text("policy_id"),
            version=int(raw["formula_version"]),
            sources=source_policies,
            horizon_policy=ZoneHorizonPolicy(binding.text("horizon_policy")),
            partition_method=ZonePartitionMethod(binding.text("partition_method")),
            weighting_method=ZoneWeightingMethod(binding.text("weighting_method")),
            withdrawn_outcome=EntityLifecycle(binding.text("withdrawn_outcome")),
            merge_distance=binding.decimal("merge_distance"),
            merge_distance_floor=binding.minimum_decimal("merge_distance"),
            merge_distance_ceiling=binding.maximum_decimal("merge_distance"),
            merge_distance_step=binding.step_decimal("merge_distance"),
            merge_distance_dynamic=binding.dynamic("merge_distance"),
            padding=binding.decimal("padding"),
            padding_floor=binding.minimum_decimal("padding"),
            padding_ceiling=binding.maximum_decimal("padding"),
            padding_step=binding.step_decimal("padding"),
            padding_dynamic=binding.dynamic("padding"),
            maximum_width=binding.decimal("maximum_width"),
            maximum_width_floor=binding.minimum_decimal("maximum_width"),
            maximum_width_ceiling=binding.maximum_decimal("maximum_width"),
            maximum_width_step=binding.step_decimal("maximum_width"),
            maximum_width_dynamic=binding.dynamic("maximum_width"),
            minimum_constituents=binding.integer("minimum_constituents"),
            minimum_constituents_floor=binding.minimum_int("minimum_constituents"),
            minimum_constituents_ceiling=binding.maximum_int("minimum_constituents"),
            minimum_constituents_step=binding.step_int("minimum_constituents"),
            minimum_constituents_dynamic=binding.dynamic("minimum_constituents"),
            maximum_constituent_age_ns=(binding.integer("maximum_constituent_age_ms") * 1_000_000),
            maximum_constituent_age_floor_ns=(
                binding.minimum_int("maximum_constituent_age_ms") * 1_000_000
            ),
            maximum_constituent_age_ceiling_ns=(
                binding.maximum_int("maximum_constituent_age_ms") * 1_000_000
            ),
            maximum_constituent_age_step_ns=(
                binding.step_int("maximum_constituent_age_ms") * 1_000_000
            ),
            maximum_constituent_age_dynamic=binding.dynamic(
                "maximum_constituent_age_ms",
            ),
            maximum_retained_sources=binding.integer("maximum_retained_sources"),
        ),
    )


def _zone_source_lifecycles(entity_type: str) -> tuple[EntityLifecycle, ...]:
    if entity_type.startswith("objective_level."):
        return (EntityLifecycle.ACTIVE, EntityLifecycle.COMPLETE)
    if entity_type == CONFIRMED_SWING_ENTITY_TYPE:
        return (EntityLifecycle.COMPLETE,)
    if entity_type == FVG_ENTITY_TYPE:
        return (EntityLifecycle.ACTIVE,)
    raise ValueError(f"unsupported derived-zone source type: {entity_type}")


def _application_scope(
    instrument_ids: tuple[str, ...],
    profile_ids: tuple[str, ...],
) -> set[tuple[str, str]]:
    return {
        (instrument_id, profile_id)
        for instrument_id in instrument_ids
        for profile_id in profile_ids
    }


def _validate_relationship_companions(
    swing_leg: Mapping[str, object],
    pivot_structure: Mapping[str, object],
) -> None:
    if swing_leg["formula_version"] != pivot_structure["formula_version"]:
        raise ValueError("relationship companion formula versions must match")
    for field in ("parameters", "parameter_sets"):
        if swing_leg[field] != pivot_structure[field]:
            raise ValueError(f"relationship companion {field} must match exactly")
    swing_scopes = {
        _relationship_application_signature(item)
        for item in _mappings(swing_leg["applications"], "applications")
    }
    pivot_scopes = {
        _relationship_application_signature(item)
        for item in _mappings(pivot_structure["applications"], "applications")
    }
    if swing_scopes != pivot_scopes:
        raise ValueError("relationship companion application scopes must match exactly")


def _relationship_application_signature(application: Mapping[str, object]) -> tuple[object, ...]:
    return (
        _text(application["parameter_set_id"], "parameter_set_id"),
        tuple(str(item) for item in application["analytical_profile_ids"]),
        tuple(str(item) for item in application["instrument_ids"]),
        tuple(str(item) for item in application["instrument_classes"]),
        tuple(str(item) for item in application["session_phases"]),
        _text(application["horizon"], "horizon"),
        _text(application["source_selector"], "source_selector"),
        bool(application["requires_volume"]),
    )


def _compatible_source_scope(
    raw: Mapping[str, object],
    *,
    horizon: str,
    source_selector: str,
    eligible_instrument_ids: tuple[str, ...],
) -> set[tuple[str, str]]:
    covered: set[tuple[str, str]] = set()
    for application in _mappings(raw["applications"], "applications"):
        if _text(application["horizon"], "horizon") != horizon:
            continue
        if _text(application["source_selector"], "source_selector") != source_selector:
            continue
        configured = tuple(str(item) for item in application["instrument_ids"])
        instruments = configured or eligible_instrument_ids
        profiles = tuple(str(item) for item in application["analytical_profile_ids"])
        covered.update(_application_scope(instruments, profiles))
    return covered


class _ParameterBinding:
    def __init__(self, definition: Mapping[str, object], application: Mapping[str, object]) -> None:
        self._definition = definition
        self._application = application
        self.application_id = _text(application["application_id"], "application_id")
        self.horizon = _text(application["horizon"], "horizon")
        self.source_selector = _text(application["source_selector"], "source_selector")
        self.profile_ids = tuple(str(item) for item in application["analytical_profile_ids"])
        selected_id = _text(application["parameter_set_id"], "parameter_set_id")
        selected = next(
            (
                item
                for item in _mappings(definition["parameter_sets"], "parameter_sets")
                if str(item["parameter_set_id"]) == selected_id
            ),
            None,
        )
        if selected is None:
            raise ValueError(
                f"application {self.application_id} parameter set is unavailable: {selected_id}",
            )
        self.parameter_version = int(selected["parameter_version"])
        self._values = _mapping(selected["values"], "parameter_set.values")
        self._parameters = {
            _text(item["parameter_id"], "parameter.parameter_id"): item
            for item in _mappings(definition["parameters"], "parameters")
        }
        if set(self._values) != set(self._parameters):
            raise ValueError(
                f"application {self.application_id} parameter set is not exact",
            )

    def instrument_ids(self, eligible: tuple[str, ...]) -> tuple[str, ...]:
        configured = tuple(str(item) for item in self._application["instrument_ids"])
        return configured or eligible

    def integer(self, parameter_id: str) -> int:
        value = self._value(parameter_id)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"market-structure parameter must be integer: {parameter_id}")
        return value

    def decimal(self, parameter_id: str) -> Decimal:
        value = self._value(parameter_id)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"market-structure parameter must be numeric: {parameter_id}")
        return Decimal(str(value))

    def text(self, parameter_id: str) -> str:
        return _text(self._value(parameter_id), parameter_id)

    def minimum_int(self, parameter_id: str) -> int:
        return _integer_envelope_value(self._parameter(parameter_id), "minimum", parameter_id)

    def maximum_int(self, parameter_id: str) -> int:
        return _integer_envelope_value(self._parameter(parameter_id), "maximum", parameter_id)

    def step_int(self, parameter_id: str) -> int:
        return _integer_envelope_value(self._parameter(parameter_id), "step", parameter_id)

    def minimum_decimal(self, parameter_id: str) -> Decimal:
        return _decimal_envelope_value(self._parameter(parameter_id), "minimum", parameter_id)

    def maximum_decimal(self, parameter_id: str) -> Decimal:
        return _decimal_envelope_value(self._parameter(parameter_id), "maximum", parameter_id)

    def step_decimal(self, parameter_id: str) -> Decimal:
        return _decimal_envelope_value(self._parameter(parameter_id), "step", parameter_id)

    def dynamic(self, parameter_id: str) -> bool:
        value = self._parameter(parameter_id)["dynamic"]
        if not isinstance(value, bool):
            raise ValueError(f"parameter dynamic flag must be boolean: {parameter_id}")
        return value

    def _value(self, parameter_id: str) -> object:
        try:
            return self._values[parameter_id]
        except KeyError as exc:
            raise ValueError(f"market-structure parameter is missing: {parameter_id}") from exc

    def _parameter(self, parameter_id: str) -> Mapping[str, object]:
        try:
            return self._parameters[parameter_id]
        except KeyError as exc:
            raise ValueError(
                f"market-structure parameter declaration is missing: {parameter_id}",
            ) from exc


def _integer_envelope_value(
    parameter: Mapping[str, object],
    field: str,
    parameter_id: str,
) -> int:
    value = parameter[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{parameter_id}.{field} must be an integer")
    return value


def _decimal_envelope_value(
    parameter: Mapping[str, object],
    field: str,
    parameter_id: str,
) -> Decimal:
    value = parameter[field]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{parameter_id}.{field} must be numeric")
    return Decimal(str(value))


def _mappings(value: object, label: str) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{label} must be a sequence")
    return tuple(_mapping(item, f"{label}[]") for item in value)


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()
