from __future__ import annotations

from decimal import Decimal

from markeitech.intelligence import (
    AnalyticalSessionPayload,
    EntityDefinition,
    EntityDurability,
    EntityLifecycle,
    EntityMetricDependency,
    EntityStateBookLimits,
    MetricFidelity,
    MetricHealth,
    MetricValue,
    ObjectiveLevelPayload,
    SessionEntityApplication,
    SessionEntityDefinition,
    SessionEntityProjectionOwner,
    payload_type_for_entity,
)

SESSION_ID = "cme_equity:2026-08-21:OPEN"


def _spec(
    entity_type: str,
    roles: tuple[tuple[str, str, bool], ...],
    *,
    identity_dimensions: tuple[str, ...],
    horizon: str,
) -> SessionEntityDefinition:
    dependencies = tuple(
        EntityMetricDependency(
            metric_id,
            1,
            required,
            (MetricHealth.READY, MetricHealth.DEGRADED),
            (MetricFidelity.DERIVED, MetricFidelity.PARTIAL),
        )
        for role, metric_id, required in roles
    )
    return SessionEntityDefinition(
        definition_id=f"{entity_type}-v1",
        definition=EntityDefinition(
            entity_type=entity_type,
            version=1,
            decision_question="What objective state is available?",
            implementation_id=f"test.{entity_type}",
            payload_type=payload_type_for_entity(entity_type),
            identity_dimensions=identity_dimensions,
            metric_inputs=dependencies,
            entity_inputs=(),
            permitted_health=(
                MetricHealth.READY,
                MetricHealth.DEGRADED,
                MetricHealth.WARMING,
            ),
            permitted_fidelities=(MetricFidelity.DERIVED, MetricFidelity.PARTIAL),
            durability=EntityDurability.FINALIZED_SESSION,
            completion_rule="source completes",
            invalidation_rule="source conflict",
            expiry_rule="configured retention",
        ),
        metric_roles={
            dependency.key: role
            for (role, _, _), dependency in zip(roles, dependencies, strict=True)
        },
        parameter_version=1,
        applications=(
            SessionEntityApplication(
                "cme-open",
                ("cme_equity_primary",),
                (),
                ("OPEN",),
                horizon,
            ),
        ),
    )


def _analytical_session_spec() -> SessionEntityDefinition:
    return _spec(
        "analytical_session",
        (
            ("start_ns", "active_session.start_ns", True),
            ("end_ns", "active_session.end_ns", True),
            ("complete", "active_session.complete", True),
            ("open", "active_session.open", True),
            ("high", "active_session.high", True),
            ("low", "active_session.low", True),
            ("latest_close", "active_session.latest_close", True),
            ("range", "active_session.range", True),
            ("location", "active_session.location", False),
            ("volume", "active_session.volume", False),
            ("bar_vwap_estimate", "active_session.bar_vwap_estimate", False),
            ("coverage_ratio", "active_session.coverage_ratio", True),
        ),
        identity_dimensions=("definition_id", "session_id", "trade_date"),
        horizon="session",
    )


def _objective_spec(name: str, metric_id: str) -> SessionEntityDefinition:
    return _spec(
        f"objective_level.{name}",
        (("price", metric_id, True),),
        identity_dimensions=(
            "definition_id",
            "horizon",
            "session_id",
            "source_metric",
            "trade_date",
        ),
        horizon="previous_session",
    )


def _owner(
    *definitions: SessionEntityDefinition,
    maximum_metric_values: int = 100,
    maximum_publications: int = 100,
) -> SessionEntityProjectionOwner:
    return SessionEntityProjectionOwner(
        definitions=definitions,
        instrument_profiles={"ESU6.CME": ("cme_equity_primary", 1)},
        limits=EntityStateBookLimits(100, 50, 20),
        maximum_metric_values=maximum_metric_values,
        maximum_publications_per_cycle=maximum_publications,
        source="TEST-SESSION-ENTITIES",
        schema_version=1,
    )


def _metric(
    metric_id: str,
    value: object,
    *,
    revision: int = 1,
    session_id: str = SESSION_ID,
    parameter_version: int = 1,
) -> MetricValue:
    timestamp = 100 + revision
    return MetricValue(
        metric_id=metric_id,
        metric_version=1,
        parameter_version=parameter_version,
        instrument_id="ESU6.CME",
        session_id=session_id,
        value=value,
        unit="test",
        effective_ts_ns=timestamp,
        observed_ts_ns=timestamp,
        received_ts_ns=timestamp,
        calculated_ts_ns=timestamp,
        published_ts_ns=timestamp,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.DERIVED,
        source="TEST-METRICS",
        evidence_refs=(f"metric:{metric_id}:{revision}",),
        missing_reasons=(),
        revision=revision,
    )


def _analytical_values() -> tuple[MetricValue, ...]:
    raw = (
        ("active_session.start_ns", 1),
        ("active_session.end_ns", 10),
        ("active_session.complete", False),
        ("active_session.open", Decimal("100")),
        ("active_session.high", Decimal("105")),
        ("active_session.low", Decimal("98")),
        ("active_session.latest_close", Decimal("103")),
        ("active_session.range", Decimal("7")),
        ("active_session.location", Decimal("0.714285")),
        ("active_session.coverage_ratio", Decimal("1")),
    )
    return tuple(_metric(metric_id, value) for metric_id, value in raw)


def test_projection_is_order_independent_and_transitions_from_warming() -> None:
    forward = _owner(_analytical_session_spec())
    reverse = _owner(_analytical_session_spec())
    values = _analytical_values()

    first = forward.ingest(values[0], now_ns=1_000)
    assert first[0].lifecycle is EntityLifecycle.WARMING
    assert first[0].payload is None
    for value in values[1:]:
        forward.ingest(value, now_ns=1_000)
    for value in reversed(values):
        reverse.ingest(value, now_ns=1_000)

    forward_revision = forward.snapshot(2_000).revisions[0]
    reverse_revision = reverse.snapshot(2_000).revisions[0]
    assert isinstance(forward_revision.payload, AnalyticalSessionPayload)
    assert forward_revision.payload == reverse_revision.payload
    assert forward_revision.lifecycle is EntityLifecycle.ACTIVE
    assert forward_revision.payload.high == Decimal("105")
    assert forward_revision.payload.volume is None


def test_objective_levels_are_direction_neutral_and_phase_scoped() -> None:
    owner = _owner(_objective_spec("previous_session_high", "previous_session.high"))

    revisions = owner.ingest(_metric("previous_session.high", Decimal("6500.25")), now_ns=1_000)

    assert len(revisions) == 1
    payload = revisions[0].payload
    assert isinstance(payload, ObjectiveLevelPayload)
    assert payload.price == payload.lower == payload.upper == Decimal("6500.25")
    assert payload.role == "OBJECTIVE_REFERENCE"
    assert not hasattr(payload, "direction")

    closed = _metric(
        "previous_session.high",
        Decimal("6501"),
        session_id="cme_equity:2026-08-21:CLOSED",
    )
    assert owner.ingest(closed, now_ns=1_001) == ()


def test_parameter_version_mismatch_does_not_feed_entity_state() -> None:
    owner = _owner(_objective_spec("previous_session_high", "previous_session.high"))

    revisions = owner.ingest(
        _metric("previous_session.high", Decimal("6500.25"), parameter_version=2),
        now_ns=1_000,
    )

    assert revisions == ()
    assert owner.retained_metric_values == 0
    assert owner.snapshot(2_000).revisions == ()


def test_publication_overflow_is_deferred_not_discarded() -> None:
    owner = _owner(
        _objective_spec("previous_session_high", "previous_session.high"),
        _objective_spec("alternate_high", "previous_session.high"),
        maximum_publications=1,
    )

    first = owner.ingest(_metric("previous_session.high", Decimal("6500")), now_ns=1_000)
    second = owner.ingest(_metric("unrelated.metric", Decimal("1")), now_ns=1_001)

    assert len(first) == len(second) == 1
    assert first[0].entity_id != second[0].entity_id
    assert owner.pending_publications == 0
    assert owner.counts.publications_deferred == 1


def test_metric_retention_and_snapshot_filters_are_bounded() -> None:
    owner = _owner(
        _objective_spec("previous_session_high", "previous_session.high"),
        maximum_metric_values=1,
    )
    owner.ingest(_metric("previous_session.high", Decimal("6500")), now_ns=1_000)
    owner.ingest(
        _metric(
            "previous_session.high",
            Decimal("6510"),
            session_id="cme_equity:2026-08-22:OPEN",
        ),
        now_ns=1_001,
    )

    snapshot = owner.snapshot(
        2_000,
        instrument_id="ESU6.CME",
        entity_type="objective_level.previous_session_high",
        lifecycles=(EntityLifecycle.ACTIVE,),
    )
    assert len(snapshot.revisions) == 2
    assert owner.snapshot(2_000, entity_type="opening_range").revisions == ()
    assert owner.retained_metric_values == 1
