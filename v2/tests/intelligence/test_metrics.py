from __future__ import annotations

from types import MappingProxyType

import pytest

from markeitech.acquisition import (
    CapabilityFeedRequirement,
    CapabilityHistoricalRequirement,
    FeedKind,
    HistoricalWindow,
)
from markeitech.intelligence import (
    MetricCadence,
    MetricDefinition,
    MetricDependency,
    MetricFailureBehavior,
    MetricFidelity,
    MetricHealth,
    MetricParameterDefinition,
    MetricParameterSet,
    MetricRegistry,
    MetricResourcePolicy,
    MetricRetainedState,
    MetricValue,
    MetricValueKind,
    MetricWarmupPolicy,
    ParameterMutability,
)


def _lookback_parameter(*, dynamic: bool = True) -> MetricParameterDefinition:
    return MetricParameterDefinition(
        parameter_id="lookback_bars",
        meaning="Completed bars included in the calculation",
        value_kind=MetricValueKind.INTEGER,
        unit="bars",
        default=20,
        scope="instrument+bar_specification",
        dynamic=dynamic,
        mutability=(
            ParameterMutability.POLICY_CONTROLLED_RUNTIME
            if dynamic
            else ParameterMutability.STARTUP_ONLY
        ),
        source="reviewed-config",
        minimum=5,
        maximum=200,
        step=1,
    )


def _definition(
    metric_id: str = "normalized_return",
    version: int = 1,
    *,
    metric_inputs: tuple[MetricDependency, ...] = (),
) -> MetricDefinition:
    live_inputs = (
        ()
        if metric_inputs
        else (
            CapabilityFeedRequirement(
                kind=FeedKind.BARS,
                selector="5-minute-last-external",
            ),
        )
    )
    return MetricDefinition(
        metric_id=metric_id,
        version=version,
        decision_question="How far did the completed bar move on a normalized basis?",
        implementation_id="markeitech.metrics.normalized_return",
        formula="(close / prior_close) - 1",
        normalization="dimensionless simple return",
        applicability="instruments with validated completed bars",
        value_kind=MetricValueKind.NUMBER,
        unit="ratio",
        cadence=MetricCadence.COMPLETED_BAR,
        horizon="configured completed-bar lookback",
        nullable=True,
        retained_state=MetricRetainedState.ROLLING_WINDOW,
        fidelity=MetricFidelity.DERIVED,
        allowed_fidelities=(
            MetricFidelity.DERIVED,
            MetricFidelity.PARTIAL,
            MetricFidelity.UNAVAILABLE,
        ),
        failure_behavior=MetricFailureBehavior.EMIT_NULL,
        failure_modes=("missing compatible prior close",),
        priority=50,
        warmup=MetricWarmupPolicy(
            minimum_observations=5,
            minimum_elapsed_ns=0,
            require_all_dependencies=True,
        ),
        resources=MetricResourcePolicy(
            maximum_retained_observations=200,
            minimum_update_interval_ms=0,
            maximum_output_age_ms=310_000,
        ),
        live_inputs=live_inputs,
        metric_inputs=metric_inputs,
        parameters=(_lookback_parameter(),),
        event_uses=("future.compression_state",),
    )


def test_definition_reuses_acquisition_requirements() -> None:
    historical = CapabilityHistoricalRequirement(
        kind=FeedKind.BARS,
        selector="5-minute-last-external",
        window=HistoricalWindow.RECENT_COMPLETED,
        minimum_observations=20,
        maximum_observations=200,
        window_parameters={"duration_minutes": 5},
    )
    definition = _definition()
    definition = MetricDefinition(
        **{
            field: getattr(definition, field)
            for field in definition.__dataclass_fields__
            if field not in {"historical_inputs"}
        },
        historical_inputs=(historical,),
    )

    capability = definition.acquisition_capability()

    assert capability is not None
    assert capability.capability_id == "metric:normalized_return"
    assert capability.live_feeds == definition.live_inputs
    assert capability.historical_requirements == (historical,)


def test_metric_only_definition_has_no_acquisition_capability() -> None:
    dependency = MetricDependency("normalized_return", 1)
    definition = _definition("compression_state", metric_inputs=(dependency,))
    registry = MetricRegistry((_definition(), definition))

    assert registry.get("compression_state", 1).acquisition_capability() is None


def test_registry_is_deterministic_and_requires_registered_dependencies() -> None:
    first = _definition("z_metric")
    second = _definition("a_metric")
    registry = MetricRegistry((first, second))

    assert tuple(item.metric_id for item in registry.definitions) == ("a_metric", "z_metric")
    with pytest.raises(ValueError, match="not registered"):
        MetricRegistry((_definition("dependent", metric_inputs=(MetricDependency("missing", 1),)),))


def test_registry_rejects_duplicate_identity_and_supports_explicit_latest_lookup() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        MetricRegistry((_definition(), _definition()))

    registry = MetricRegistry((_definition(version=1), _definition(version=2)))

    assert registry.latest("normalized_return").version == 2
    assert registry.get("normalized_return", 1).version == 1


def test_dynamic_numeric_parameter_requires_bounded_policy_mutation() -> None:
    with pytest.raises(ValueError, match="policy-controlled"):
        MetricParameterDefinition(
            parameter_id="lookback",
            meaning="Window length",
            value_kind=MetricValueKind.INTEGER,
            unit="bars",
            default=20,
            scope="instrument",
            dynamic=True,
            mutability=ParameterMutability.STARTUP_ONLY,
            source="reviewed-config",
            minimum=5,
            maximum=200,
            step=1,
        )

    with pytest.raises(ValueError, match="positive step"):
        MetricParameterDefinition(
            parameter_id="lookback",
            meaning="Window length",
            value_kind=MetricValueKind.INTEGER,
            unit="bars",
            default=20,
            scope="instrument",
            dynamic=True,
            mutability=ParameterMutability.POLICY_CONTROLLED_RUNTIME,
            source="reviewed-config",
            minimum=5,
            maximum=200,
        )


def test_static_parameter_remains_reviewed_configurable() -> None:
    parameter = _lookback_parameter(dynamic=False)

    assert parameter.dynamic is False
    assert parameter.mutability is ParameterMutability.STARTUP_ONLY
    parameter.validate(50)


def test_parameter_set_is_immutable_versioned_and_validated_by_registry() -> None:
    values = {"lookback_bars": 50}
    parameters = MetricParameterSet(
        metric_id="normalized_return",
        metric_version=1,
        parameter_version=2,
        effective_from_ns=10,
        source="operator-reviewed-config",
        values=values,
        supersedes_parameter_version=1,
    )
    registry = MetricRegistry((_definition(),))

    values["lookback_bars"] = 100
    assert parameters.values == MappingProxyType({"lookback_bars": 50})
    registry.validate_parameters(parameters)

    invalid = MetricParameterSet(
        metric_id="normalized_return",
        metric_version=1,
        parameter_version=3,
        effective_from_ns=20,
        source="bounded-optimizer",
        values={"lookback_bars": 201},
        supersedes_parameter_version=2,
    )
    with pytest.raises(ValueError, match="above"):
        registry.validate_parameters(invalid)


def test_definition_rejects_unbounded_state_and_self_dependency() -> None:
    definition = _definition()
    fields = {
        field: getattr(definition, field)
        for field in definition.__dataclass_fields__
        if field not in {"resources"}
    }
    with pytest.raises(ValueError, match="positive retention"):
        MetricDefinition(
            **fields,
            resources=MetricResourcePolicy(0, 0, 310_000),
        )

    with pytest.raises(ValueError, match="depend on itself"):
        _definition(metric_inputs=(MetricDependency("normalized_return", 1),))


def test_metric_value_carries_temporal_health_and_lineage_truth() -> None:
    value = MetricValue(
        metric_id="normalized_return",
        metric_version=1,
        parameter_version=2,
        instrument_id="ESU6.CME",
        session_id="CME-2026-08-17-GTH",
        value=0.0025,
        unit="ratio",
        effective_ts_ns=100,
        observed_ts_ns=101,
        received_ts_ns=102,
        calculated_ts_ns=103,
        published_ts_ns=104,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.DERIVED,
        source="BASELINE-METRICS",
        evidence_refs=("bar:ESU6.CME:100",),
        missing_reasons=(),
        revision=1,
    )
    registry = MetricRegistry((_definition(),))

    registry.validate_value(value)
    assert value.key == ("normalized_return", 1)


def test_definition_exposes_specialist_contract_and_rejects_undeclared_fidelity() -> None:
    definition = _definition()

    assert definition.formula == "(close / prior_close) - 1"
    assert definition.normalization == "dimensionless simple return"
    assert definition.applicability == "instruments with validated completed bars"
    assert definition.failure_modes == ("missing compatible prior close",)
    assert definition.priority == 50

    value = MetricValue(
        metric_id="normalized_return",
        metric_version=1,
        parameter_version=1,
        instrument_id="ESU6.CME",
        session_id=None,
        value=0.1,
        unit="ratio",
        effective_ts_ns=100,
        observed_ts_ns=100,
        received_ts_ns=100,
        calculated_ts_ns=100,
        published_ts_ns=100,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.REPORTED,
        source="TEST",
        evidence_refs=("bar:1",),
        missing_reasons=(),
        revision=1,
    )

    with pytest.raises(ValueError, match="fidelity is incompatible"):
        MetricRegistry((definition,)).validate_value(value)


def test_null_value_requires_reason_and_definition_permission() -> None:
    with pytest.raises(ValueError, match="missing reason"):
        MetricValue(
            metric_id="normalized_return",
            metric_version=1,
            parameter_version=1,
            instrument_id="ESU6.CME",
            session_id=None,
            value=None,
            unit="ratio",
            effective_ts_ns=100,
            observed_ts_ns=100,
            received_ts_ns=100,
            calculated_ts_ns=100,
            published_ts_ns=100,
            health=MetricHealth.WARMING,
            fidelity=MetricFidelity.PARTIAL,
            source="BASELINE-METRICS",
            evidence_refs=(),
            missing_reasons=(),
            revision=1,
        )
