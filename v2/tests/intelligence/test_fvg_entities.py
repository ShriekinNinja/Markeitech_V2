from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from markeitech.intelligence.completed_bars import CompletedBarInput, CompletedBarSource
from markeitech.intelligence.entities import (
    EntityDefinition,
    EntityDurability,
    EntityLifecycle,
    EntityMetricDependency,
    EntityStateBookLimits,
)
from markeitech.intelligence.entity_measurements import (
    FVG_FILL_RATIO_METRIC_ID,
    FVG_LOWER_BOUND_METRIC_ID,
    FVG_UPPER_BOUND_METRIC_ID,
    FVG_WIDTH_METRIC_ID,
    FvgDirection,
    FvgGeometryPolicy,
)
from markeitech.intelligence.fvg_entities import (
    FVG_ENTITY_TYPE,
    FvgApplication,
    FvgEntityDefinition,
    FvgEntityProjectionOwner,
    FvgLifecyclePolicy,
    FvgNormalizationEvidence,
    FvgPayload,
    FvgTerminalOutcome,
)
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth

MINUTE_NS = 60_000_000_000
BAR_NS = 5 * MINUTE_NS
HEALTH = (MetricHealth.READY, MetricHealth.DEGRADED, MetricHealth.STALE)
FIDELITY = (MetricFidelity.DERIVED, MetricFidelity.PARTIAL, MetricFidelity.REPORTED)


def _definition(
    *,
    maximum_age_bars: int = 3,
    terminal_outcome: FvgTerminalOutcome = FvgTerminalOutcome.COMPLETE,
) -> FvgEntityDefinition:
    geometry_ids = (
        FVG_FILL_RATIO_METRIC_ID,
        FVG_LOWER_BOUND_METRIC_ID,
        FVG_UPPER_BOUND_METRIC_ID,
        FVG_WIDTH_METRIC_ID,
    )
    definition = EntityDefinition(
        entity_type=FVG_ENTITY_TYPE,
        version=1,
        decision_question="Which configured wick gaps currently exist?",
        implementation_id="markeitech.entities.fair_value_gap",
        payload_type=FvgPayload,
        identity_dimensions=(
            "bar_specification",
            "definition_id",
            "direction",
            "formation_timestamp",
            "horizon",
            "lifecycle_policy_id",
            "lifecycle_policy_version",
        ),
        metric_inputs=tuple(
            [
                *(
                    EntityMetricDependency(metric_id, 1, True, HEALTH, FIDELITY)
                    for metric_id in geometry_ids
                ),
                EntityMetricDependency("atr-normalization", 1, False, HEALTH, FIDELITY),
            ]
        ),
        entity_inputs=(),
        permitted_health=HEALTH,
        permitted_fidelities=FIDELITY,
        durability=EntityDurability.TRANSIENT,
        completion_rule="three contiguous completed bars confirm geometry",
        invalidation_rule="configured full-fill outcome",
        expiry_rule="configured completed-bar age boundary",
    )
    return FvgEntityDefinition(
        definition_id="wick-gap-v1",
        definition=definition,
        applications=(
            FvgApplication(
                application_id="cme-5m-fvg",
                analytical_profile_ids=("cme_equity_primary",),
                instrument_ids=(),
                bar_specifications=("5-MINUTE-LAST-EXTERNAL",),
                horizon="intraday_5m",
                parameter_version=1,
                policy=FvgLifecyclePolicy(
                    policy_id="wick-fill-v1",
                    version=1,
                    source_interval_ns=BAR_NS,
                    geometry=FvgGeometryPolicy(
                        pattern_length=3,
                        minimum_width=Decimal("1"),
                        minimum_width_floor=Decimal("0.25"),
                        minimum_width_ceiling=Decimal("10"),
                        minimum_width_step=Decimal("0.25"),
                        minimum_width_dynamic=True,
                        price_basis="wick",
                        fill_method="wick_penetration",
                    ),
                    terminal_outcome=terminal_outcome,
                    maximum_age_bars=maximum_age_bars,
                    minimum_age_bars=1,
                    maximum_age_bars_ceiling=10,
                    age_step_bars=1,
                    maximum_age_dynamic=True,
                    maximum_retained_bars=20,
                    maximum_retained_normalizations=10,
                ),
                normalization_metric_id="atr-normalization",
                normalization_metric_version=1,
                normalization_max_age_ns=10 * BAR_NS,
            ),
        ),
    )


def _owner(definition: FvgEntityDefinition | None = None) -> FvgEntityProjectionOwner:
    return FvgEntityProjectionOwner(
        definitions=(definition or _definition(),),
        limits=EntityStateBookLimits(100, 100, 100),
        maximum_publications_per_cycle=100,
        source="TEST-FVG",
        schema_version=1,
    )


def _bar(index: int, *, open: str, high: str, low: str, close: str) -> CompletedBarInput:
    end_ns = (index + 1) * BAR_NS
    return CompletedBarInput(
        instrument_id="ESU6.CME",
        bar_specification="5-MINUTE-LAST-EXTERNAL",
        calendar_id="cme_equity",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        trade_date=date(2026, 8, 24),
        session_id="cme_equity:2026-08-24:OPEN",
        window_id="primary",
        interval_start_ns=end_ns - BAR_NS,
        interval_end_ns=end_ns,
        open=Decimal(open),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("100"),
        source=CompletedBarSource.LIVE_AGGREGATE,
        observed_ts_ns=end_ns,
        received_ts_ns=end_ns + 1,
        normalized_ts_ns=end_ns + 2,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.REPORTED,
        evidence_refs=(f"bar:{index}",),
        complete=True,
        missing_reasons=(),
    )


def _formation() -> tuple[CompletedBarInput, ...]:
    return (
        _bar(0, open="98", high="100", low="95", close="99"),
        _bar(1, open="101", high="106", low="99", close="104"),
        _bar(2, open="106", high="110", low="105", close="108"),
    )


def _normalization() -> FvgNormalizationEvidence:
    return FvgNormalizationEvidence(
        metric_id="atr-normalization",
        metric_version=1,
        revision=1,
        instrument_id="ESU6.CME",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        bar_specification="5-MINUTE-LAST-EXTERNAL",
        horizon="intraday_5m",
        effective_ts_ns=BAR_NS,
        value=Decimal("2.5"),
        health=MetricHealth.READY,
        fidelity=MetricFidelity.DERIVED,
        reference_id="atr:es:1",
    )


def _current(owner: FvgEntityProjectionOwner):
    revisions = tuple(
        revision
        for revision in owner.snapshot(100 * BAR_NS).revisions
        if isinstance(revision.payload, FvgPayload)
        and revision.payload.formation_ts_ns == 3 * BAR_NS
    )
    assert len(revisions) == 1
    return revisions[0]


def test_fvg_policy_rejects_out_of_envelope_age_and_insufficient_retention() -> None:
    policy = _definition().applications[0].policy
    with pytest.raises(ValueError, match="outside its configured envelope"):
        replace(policy, maximum_age_bars=11)
    with pytest.raises(ValueError, match="cannot discard a live FVG lifecycle"):
        replace(policy, maximum_retained_bars=5)


def test_three_completed_bars_confirm_fvg_without_lookahead() -> None:
    owner = _owner()
    first, second, third = _formation()
    owner.ingest_bar(first, now_ns=first.normalized_ts_ns)
    owner.ingest_bar(second, now_ns=second.normalized_ts_ns)
    assert owner.snapshot(second.normalized_ts_ns).revisions == ()

    published = owner.ingest_bar(third, now_ns=third.normalized_ts_ns)
    assert len(published) == 1
    revision = _current(owner)
    payload = revision.payload
    assert isinstance(payload, FvgPayload)
    assert revision.lifecycle is EntityLifecycle.ACTIVE
    assert payload.direction is FvgDirection.BULLISH
    assert (payload.lower_bound, payload.upper_bound, payload.width) == (
        Decimal("100"),
        Decimal("105"),
        Decimal("5"),
    )
    assert payload.fill_ratio == 0
    assert payload.formation_bar_refs == (
        "completed_bar:ESU6.CME:5-MINUTE-LAST-EXTERNAL:300000000000:1",
        "completed_bar:ESU6.CME:5-MINUTE-LAST-EXTERNAL:600000000000:1",
        "completed_bar:ESU6.CME:5-MINUTE-LAST-EXTERNAL:900000000000:1",
    )


def test_partial_fill_then_full_fill_revises_one_entity_with_bounded_evidence() -> None:
    owner = _owner()
    for bar in _formation():
        owner.ingest_bar(bar, now_ns=bar.normalized_ts_ns)
    partial = _bar(3, open="107", high="108", low="103", close="104")
    owner.ingest_bar(partial, now_ns=partial.normalized_ts_ns)
    revision = _current(owner)
    payload = revision.payload
    assert isinstance(payload, FvgPayload)
    assert revision.revision == 2
    assert revision.lifecycle is EntityLifecycle.ACTIVE
    assert payload.fill_ratio == Decimal("0.4")
    assert (payload.remaining_lower, payload.remaining_upper) == (
        Decimal("100"),
        Decimal("103"),
    )
    assert payload.first_fill_ts_ns == partial.interval_end_ns

    filled = _bar(4, open="103", high="104", low="99", close="100")
    owner.ingest_bar(filled, now_ns=filled.normalized_ts_ns)
    revision = _current(owner)
    payload = revision.payload
    assert isinstance(payload, FvgPayload)
    assert revision.revision == 3
    assert revision.lifecycle is EntityLifecycle.COMPLETE
    assert payload.fill_ratio == 1
    assert payload.remaining_lower == payload.remaining_upper == Decimal("100")
    assert payload.terminal_ts_ns == filled.interval_end_ns

    later = _bar(5, open="100", high="102", low="98", close="101")
    owner.ingest_bar(later, now_ns=later.normalized_ts_ns)
    assert _current(owner).revision == 3


def test_unfilled_fvg_expires_at_configured_completed_bar_boundary() -> None:
    owner = _owner(_definition(maximum_age_bars=2))
    for bar in _formation():
        owner.ingest_bar(bar, now_ns=bar.normalized_ts_ns)
    first = _bar(3, open="108", high="111", low="106", close="109")
    second = _bar(4, open="109", high="112", low="106", close="110")
    owner.ingest_bar(first, now_ns=first.normalized_ts_ns)
    assert _current(owner).lifecycle is EntityLifecycle.ACTIVE
    owner.ingest_bar(second, now_ns=second.normalized_ts_ns)
    revision = _current(owner)
    assert revision.lifecycle is EntityLifecycle.EXPIRED
    assert isinstance(revision.payload, FvgPayload)
    assert revision.payload.terminal_ts_ns == second.interval_end_ns


def test_configured_full_fill_can_invalidate_instead_of_complete() -> None:
    owner = _owner(_definition(terminal_outcome=FvgTerminalOutcome.INVALIDATED))
    for bar in _formation():
        owner.ingest_bar(bar, now_ns=bar.normalized_ts_ns)
    filled = _bar(3, open="103", high="104", low="99", close="100")
    owner.ingest_bar(filled, now_ns=filled.normalized_ts_ns)
    assert _current(owner).lifecycle is EntityLifecycle.INVALIDATED


def test_fvg_bar_retention_is_bounded_by_policy() -> None:
    definition = _definition(maximum_age_bars=1)
    application = definition.applications[0]
    bounded = replace(
        definition,
        applications=(
            replace(
                application,
                policy=replace(application.policy, maximum_retained_bars=4),
            ),
        ),
    )
    owner = _owner(bounded)
    for index in range(10):
        bar = _bar(
            index,
            open=str(100 + index),
            high=str(102 + index),
            low=str(99 + index),
            close=str(101 + index),
        )
        owner.ingest_bar(bar, now_ns=bar.normalized_ts_ns)
    assert owner.retained_bars == 4


def test_normalization_before_bars_and_late_bar_arrival_converge() -> None:
    chronological = _owner()
    chronological.ingest_normalization(_normalization(), now_ns=BAR_NS)
    bars = (*_formation(), _bar(3, open="107", high="108", low="103", close="104"))
    for bar in bars:
        chronological.ingest_bar(bar, now_ns=bar.normalized_ts_ns)

    late = _owner()
    late.ingest_normalization(_normalization(), now_ns=BAR_NS)
    for bar in (bars[0], bars[2], bars[3], bars[1]):
        late.ingest_bar(bar, now_ns=bars[-1].normalized_ts_ns)

    expected = _current(chronological)
    actual = _current(late)
    assert actual.payload == expected.payload
    assert actual.lifecycle == expected.lifecycle
    assert isinstance(actual.payload, FvgPayload)
    assert actual.payload.normalized_width == Decimal("2")
    assert actual.payload.missing_context == ()
