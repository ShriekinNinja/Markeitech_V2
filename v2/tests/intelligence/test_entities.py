from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

import pytest

from markeitech.acquisition import CapabilityFeedRequirement, FeedKind
from markeitech.intelligence import (
    EntityAdmissionStatus,
    EntityDefinition,
    EntityDependency,
    EntityDurability,
    EntityEvidenceKind,
    EntityEvidenceReference,
    EntityIdentity,
    EntityIdentityDimension,
    EntityLifecycle,
    EntityMetricDependency,
    EntityParameterSet,
    EntityPayload,
    EntityRegistry,
    EntityRevision,
    EntityStateBook,
    EntityStateBookLimits,
    MetricCadence,
    MetricDefinition,
    MetricFailureBehavior,
    MetricFidelity,
    MetricHealth,
    MetricParameterDefinition,
    MetricRegistry,
    MetricResourcePolicy,
    MetricRetainedState,
    MetricValueKind,
    MetricWarmupPolicy,
    ParameterMutability,
)


@dataclass(frozen=True, slots=True)
class _LevelPayload(EntityPayload):
    price: Decimal


@dataclass(frozen=True, slots=True)
class _ZonePayload(EntityPayload):
    lower: Decimal
    upper: Decimal


def _metric_definition() -> MetricDefinition:
    return MetricDefinition(
        metric_id="session.high",
        version=1,
        decision_question="What was the session high?",
        implementation_id="markeitech.metrics.session_high",
        formula="max(completed_bar.high)",
        normalization="native price",
        applicability="instruments with completed bars",
        value_kind=MetricValueKind.NUMBER,
        unit="price",
        cadence=MetricCadence.COMPLETED_BAR,
        horizon="configured session",
        nullable=True,
        retained_state=MetricRetainedState.SESSION,
        fidelity=MetricFidelity.DERIVED,
        allowed_fidelities=(MetricFidelity.DERIVED, MetricFidelity.PARTIAL),
        failure_behavior=MetricFailureBehavior.EMIT_NULL,
        failure_modes=("missing completed bars",),
        priority=50,
        warmup=MetricWarmupPolicy(1, 0, True),
        resources=MetricResourcePolicy(100, 0, 120_000),
        live_inputs=(CapabilityFeedRequirement(FeedKind.BARS, "1-minute-last-external"),),
    )


def _retention_parameter() -> MetricParameterDefinition:
    return MetricParameterDefinition(
        parameter_id="retention_sessions",
        meaning="Completed sessions retained by the entity family",
        value_kind=MetricValueKind.INTEGER,
        unit="sessions",
        default=2,
        scope="entity_type+instrument+analytical_profile",
        dynamic=False,
        mutability=ParameterMutability.STARTUP_ONLY,
        source="reviewed-config",
        minimum=1,
        maximum=10,
        step=1,
    )


def _level_definition(*, version: int = 1) -> EntityDefinition:
    return EntityDefinition(
        entity_type="objective_level",
        version=version,
        decision_question="Which finalized session-high level is current?",
        implementation_id="markeitech.entities.session_high_level",
        payload_type=_LevelPayload,
        identity_dimensions=("trade_date", "session_id"),
        metric_inputs=(
            EntityMetricDependency(
                "session.high",
                1,
                True,
                (MetricHealth.READY, MetricHealth.DEGRADED, MetricHealth.STALE),
                (MetricFidelity.DERIVED, MetricFidelity.PARTIAL),
            ),
        ),
        entity_inputs=(),
        permitted_health=(MetricHealth.READY, MetricHealth.DEGRADED, MetricHealth.STALE),
        permitted_fidelities=(MetricFidelity.DERIVED, MetricFidelity.PARTIAL),
        durability=EntityDurability.FINALIZED_SESSION,
        completion_rule="session metric is final and coverage is sufficient",
        invalidation_rule="identity or required evidence becomes inconsistent",
        expiry_rule="configured completed-session retention boundary passes",
        parameters=(_retention_parameter(),),
        event_uses=("future.level_interaction",),
    )


def _zone_definition() -> EntityDefinition:
    return EntityDefinition(
        entity_type="derived_zone",
        version=1,
        decision_question="Which objective levels form this zone?",
        implementation_id="markeitech.entities.derived_zone",
        payload_type=_ZonePayload,
        identity_dimensions=("zone_id",),
        metric_inputs=(),
        entity_inputs=(
            EntityDependency(
                "objective_level",
                1,
                True,
                (MetricHealth.READY, MetricHealth.DEGRADED, MetricHealth.STALE),
                (MetricFidelity.DERIVED, MetricFidelity.PARTIAL),
            ),
        ),
        permitted_health=(MetricHealth.READY, MetricHealth.DEGRADED, MetricHealth.STALE),
        permitted_fidelities=(MetricFidelity.DERIVED, MetricFidelity.PARTIAL),
        durability=EntityDurability.CROSS_SESSION_CHECKPOINT,
        completion_rule="all required constituents are confirmed",
        invalidation_rule="all constituents expire or the configured zone policy invalidates",
        expiry_rule="configured zone retention boundary passes",
    )


def _registry(*definitions: EntityDefinition) -> EntityRegistry:
    return EntityRegistry(
        definitions or (_level_definition(),),
        metric_registry=MetricRegistry((_metric_definition(),)),
    )


def _identity(
    *,
    session_id: str = "CME-2026-08-21-OPEN",
    trade_date: str = "2026-08-21",
    instrument_id: str = "ESU6.CME",
) -> EntityIdentity:
    return EntityIdentity(
        entity_type="objective_level",
        entity_version=1,
        instrument_id=instrument_id,
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        dimensions=(
            EntityIdentityDimension("session_id", session_id),
            EntityIdentityDimension("trade_date", trade_date),
        ),
    )


def _evidence() -> tuple[EntityEvidenceReference, ...]:
    return (
        EntityEvidenceReference(
            kind=EntityEvidenceKind.METRIC,
            definition_id="session.high",
            reference_id="metric:session.high:ESU6.CME:CME-2026-08-21-OPEN",
            version=1,
            revision=1,
            effective_ts_ns=10,
            health=MetricHealth.READY,
            fidelity=MetricFidelity.DERIVED,
        ),
    )


def _revision(
    *,
    identity: EntityIdentity | None = None,
    revision: int = 1,
    previous_revision: int | None = None,
    price: str = "6500.25",
    lifecycle: EntityLifecycle = EntityLifecycle.ACTIVE,
    effective_ts_ns: int = 10,
    published_ts_ns: int = 12,
) -> EntityRevision:
    return EntityRevision(
        identity=identity or _identity(),
        revision=revision,
        parameter_version=1,
        payload=_LevelPayload(Decimal(price)),
        lifecycle=lifecycle,
        effective_ts_ns=effective_ts_ns,
        observed_ts_ns=10,
        calculated_ts_ns=11,
        published_ts_ns=published_ts_ns,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.DERIVED,
        evidence_refs=_evidence(),
        missing_reasons=(),
        conflict_reasons=(),
        source="SESSION-REFERENCE-ENTITY",
        schema_version=1,
        previous_revision=previous_revision,
    )


def _book(*, maximum: int = 10, per_instrument: int = 10, per_type: int = 10) -> EntityStateBook:
    return EntityStateBook(
        _registry(),
        EntityStateBookLimits(maximum, per_instrument, per_type),
    )


def test_identity_is_stable_and_dimension_order_independent() -> None:
    first = _identity()
    second = EntityIdentity(
        entity_type=first.entity_type,
        entity_version=first.entity_version,
        instrument_id=first.instrument_id,
        analytical_profile_id=first.analytical_profile_id,
        analytical_profile_version=first.analytical_profile_version,
        dimensions=tuple(reversed(first.dimensions)),
    )

    assert first.dimensions == second.dimensions
    assert first.entity_id == second.entity_id
    assert first.entity_id.startswith("entity:")
    assert _identity(trade_date="2026-08-22").entity_id != first.entity_id


def test_registry_validates_dependencies_payloads_and_parameter_sets() -> None:
    registry = _registry(_level_definition(), _zone_definition())
    parameters = EntityParameterSet(
        entity_type="objective_level",
        entity_version=1,
        parameter_version=1,
        effective_from_ns=1,
        source="operator-reviewed-config",
        values={"retention_sessions": 2},
    )

    registry.validate_parameters(parameters)
    registry.validate_revision(_revision())
    with pytest.raises(ValueError, match="payload"):
        registry.validate_revision(
            replace(_revision(), payload=_ZonePayload(Decimal(1), Decimal(2))),
        )
    with pytest.raises(ValueError, match="parameter set"):
        registry.validate_parameters(replace(parameters, values={}))


def test_registry_rejects_missing_dependencies_and_entity_cycles() -> None:
    with pytest.raises(ValueError, match="metric dependency"):
        EntityRegistry(
            (_level_definition(),),
            metric_registry=MetricRegistry(()),
        )

    first = replace(
        _zone_definition(),
        entity_type="zone_a",
        entity_inputs=(
            EntityDependency(
                "zone_b",
                1,
                True,
                (MetricHealth.READY,),
                (MetricFidelity.DERIVED,),
            ),
        ),
    )
    second = replace(
        _zone_definition(),
        entity_type="zone_b",
        entity_inputs=(
            EntityDependency(
                "zone_a",
                1,
                True,
                (MetricHealth.READY,),
                (MetricFidelity.DERIVED,),
            ),
        ),
    )
    with pytest.raises(ValueError, match="cycle"):
        _registry(first, second)


def test_registry_requires_exact_identity_and_required_evidence() -> None:
    registry = _registry()
    wrong_dimensions = EntityIdentity(
        entity_type="objective_level",
        entity_version=1,
        instrument_id="ESU6.CME",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        dimensions=(EntityIdentityDimension("trade_date", "2026-08-21"),),
    )

    with pytest.raises(ValueError, match="dimensions"):
        registry.validate_revision(_revision(identity=wrong_dimensions))
    with pytest.raises(ValueError, match="required metric"):
        registry.validate_revision(replace(_revision(), evidence_refs=()))
    degraded_evidence = replace(_evidence()[0], health=MetricHealth.UNAVAILABLE)
    with pytest.raises(ValueError, match="health/fidelity"):
        registry.validate_revision(replace(_revision(), evidence_refs=(degraded_evidence,)))


def test_registry_enforces_restoration_fidelity_boundary() -> None:
    checkpoint = replace(
        _level_definition(),
        durability=EntityDurability.CROSS_SESSION_CHECKPOINT,
    )
    registry = _registry(checkpoint)

    with pytest.raises(ValueError, match="degraded or stale"):
        registry.validate_revision(replace(_revision(), restored=True))

    restored = replace(
        _revision(
            revision=4,
            previous_revision=3,
            lifecycle=EntityLifecycle.STALE,
        ),
        restored=True,
    )
    registry.validate_revision(restored)

    transient_registry = _registry(
        replace(_level_definition(), durability=EntityDurability.TRANSIENT),
    )
    with pytest.raises(ValueError, match="transient"):
        transient_registry.validate_revision(restored)


def test_state_book_admits_updates_and_rejects_bad_revision_sequences() -> None:
    book = _book()
    initial = _revision()

    assert book.admit(initial).status is EntityAdmissionStatus.ADDED
    assert book.admit(initial).status is EntityAdmissionStatus.DUPLICATE
    assert book.admit(replace(initial, payload=_LevelPayload(Decimal("6501.00")))).status is (
        EntityAdmissionStatus.REJECTED_CONFLICT
    )
    assert (
        book.admit(
            _revision(revision=3, previous_revision=2, price="6502.00", published_ts_ns=14),
        ).status
        is EntityAdmissionStatus.REJECTED_REVISION_GAP
    )

    unchanged = _revision(revision=2, previous_revision=1, published_ts_ns=13)
    assert book.admit(unchanged).status is EntityAdmissionStatus.DUPLICATE

    updated = _revision(
        revision=2,
        previous_revision=1,
        price="6502.00",
        effective_ts_ns=13,
        published_ts_ns=14,
    )
    assert book.admit(updated).status is EntityAdmissionStatus.UPDATED
    assert book.get(initial.entity_id) == updated
    assert book.admit(initial).status is EntityAdmissionStatus.REJECTED_STALE


def test_new_live_entities_start_at_revision_one_but_checkpoints_may_restore() -> None:
    book = _book()
    skipped_initial = _revision(revision=2, previous_revision=1, published_ts_ns=13)
    assert book.admit(skipped_initial).status is EntityAdmissionStatus.REJECTED_REVISION_GAP

    checkpoint = replace(
        _level_definition(),
        durability=EntityDurability.CROSS_SESSION_CHECKPOINT,
    )
    checkpoint_book = EntityStateBook(
        _registry(checkpoint),
        EntityStateBookLimits(10, 10, 10),
    )
    restored = replace(
        _revision(
            revision=4,
            previous_revision=3,
            lifecycle=EntityLifecycle.STALE,
            published_ts_ns=13,
        ),
        restored=True,
    )
    assert checkpoint_book.admit(restored).status is EntityAdmissionStatus.ADDED


def test_capacity_evicts_oldest_terminal_entity_but_never_active_state() -> None:
    book = _book(maximum=2, per_instrument=2, per_type=2)
    completed = _revision(
        identity=_identity(session_id="old", trade_date="2026-08-20"),
        lifecycle=EntityLifecycle.COMPLETE,
        published_ts_ns=12,
    )
    active = _revision(
        identity=_identity(session_id="current", trade_date="2026-08-21"),
        published_ts_ns=13,
    )
    incoming = _revision(
        identity=_identity(session_id="next", trade_date="2026-08-22"),
        published_ts_ns=14,
    )

    book.admit(completed)
    book.admit(active)
    result = book.admit(incoming)

    assert result.status is EntityAdmissionStatus.ADDED
    assert result.evicted_entity_ids == (completed.entity_id,)
    assert book.get(active.entity_id) == active
    assert book.get(incoming.entity_id) == incoming

    protected_book = _book(maximum=2, per_instrument=2, per_type=2)
    protected_book.admit(active)
    protected_book.admit(incoming)
    rejected = protected_book.admit(
        _revision(
            identity=_identity(session_id="later", trade_date="2026-08-23"),
            published_ts_ns=15,
        ),
    )
    assert rejected.status is EntityAdmissionStatus.REJECTED_CAPACITY
    assert len(protected_book) == 2


def test_snapshot_filters_are_immutable_and_terminal_pruning_is_bounded() -> None:
    book = _book()
    active = _revision()
    complete = _revision(
        identity=_identity(
            session_id="SPY-2026-08-20-RTH",
            trade_date="2026-08-20",
            instrument_id="SPY.ARCA",
        ),
        lifecycle=EntityLifecycle.COMPLETE,
        published_ts_ns=11,
    )
    book.admit(active)
    book.admit(complete)

    snapshot = book.snapshot(
        20,
        instrument_id="ESU6.CME",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        dimensions={"trade_date": "2026-08-21"},
        lifecycles=(EntityLifecycle.ACTIVE,),
    )
    assert snapshot.revisions == (active,)
    assert book.prune_terminal(published_before_ns=12, maximum_removals=1) == (complete,)
    assert snapshot.revisions == (active,)
    assert len(book) == 1
