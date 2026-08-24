from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from markeitech.intelligence import (
    SWING_PIVOT_PRICE_METRIC_ID,
    SWING_PROMINENCE_METRIC_ID,
    CompletedBarInput,
    CompletedBarSource,
    ConfirmedSwingApplication,
    ConfirmedSwingDefinition,
    ConfirmedSwingPayload,
    ConfirmedSwingProjectionOwner,
    EntityDefinition,
    EntityDurability,
    EntityLifecycle,
    EntityMetricDependency,
    EntityStateBookLimits,
    MetricFidelity,
    MetricHealth,
    SwingGeometryPolicy,
    SwingKind,
)

MINUTE_NS = 60_000_000_000


def _policy(**changes: object) -> SwingGeometryPolicy:
    values = {
        "left_span_bars": 1,
        "minimum_left_span_bars": 1,
        "maximum_left_span_bars": 5,
        "left_span_step": 1,
        "left_span_dynamic": True,
        "right_span_bars": 1,
        "minimum_right_span_bars": 1,
        "maximum_right_span_bars": 5,
        "right_span_step": 1,
        "right_span_dynamic": True,
        "minimum_prominence": Decimal("0.5"),
        "minimum_prominence_floor": Decimal("0.25"),
        "minimum_prominence_ceiling": Decimal("5"),
        "minimum_prominence_step": Decimal("0.25"),
        "minimum_prominence_dynamic": True,
        "tie_policy": "reject_ties",
    }
    values.update(changes)
    return SwingGeometryPolicy(**values)  # type: ignore[arg-type]


def _definition(
    *,
    detector_id: str = "tactical",
    horizon: str = "intraday_5m",
    maximum_retained_bars: int = 20,
) -> ConfirmedSwingDefinition:
    permitted_health = (MetricHealth.READY, MetricHealth.DEGRADED, MetricHealth.STALE)
    permitted_fidelity = (MetricFidelity.DERIVED, MetricFidelity.PARTIAL)
    return ConfirmedSwingDefinition(
        definition_id="confirmed-swing-v1",
        definition=EntityDefinition(
            entity_type="confirmed_swing",
            version=1,
            decision_question="Which strict pivots are confirmed without look-ahead?",
            implementation_id="markeitech.entities.confirmed_swing",
            payload_type=ConfirmedSwingPayload,
            identity_dimensions=(
                "definition_id",
                "detector_id",
                "detector_version",
                "horizon",
                "bar_specification",
                "pivot_timestamp",
                "swing_kind",
            ),
            metric_inputs=tuple(
                EntityMetricDependency(
                    metric_id,
                    1,
                    True,
                    permitted_health,
                    permitted_fidelity,
                )
                for metric_id in (
                    SWING_PIVOT_PRICE_METRIC_ID,
                    SWING_PROMINENCE_METRIC_ID,
                )
            ),
            entity_inputs=(),
            permitted_health=permitted_health,
            permitted_fidelities=permitted_fidelity,
            durability=EntityDurability.TRANSIENT,
            completion_rule="configured right-span evidence confirms the strict pivot",
            invalidation_rule="accepted bar conflict or detector identity conflict",
            expiry_rule="bounded confirmed-swing retention removes the oldest complete entity",
        ),
        applications=(
            ConfirmedSwingApplication(
                application_id=f"{detector_id}-application",
                detector_id=detector_id,
                detector_version=1,
                analytical_profile_ids=("cme_equity_primary",),
                instrument_ids=(),
                bar_specifications=("5-MINUTE-LAST-EXTERNAL",),
                horizon=horizon,
                parameter_version=1,
                policy=_policy(),
                maximum_retained_bars=maximum_retained_bars,
            ),
        ),
    )


def _owner(
    *definitions: ConfirmedSwingDefinition,
    maximum_entities: int = 20,
    maximum_publications: int = 20,
) -> ConfirmedSwingProjectionOwner:
    return ConfirmedSwingProjectionOwner(
        definitions=definitions or (_definition(),),
        limits=EntityStateBookLimits(
            maximum_entities,
            maximum_entities,
            maximum_entities,
        ),
        maximum_publications_per_cycle=maximum_publications,
        source="TEST-MARKET-STRUCTURE",
        schema_version=1,
    )


def _bar(
    index: int,
    *,
    high: str,
    low: str,
    close: str,
    volume: str | None = "10",
    source: CompletedBarSource = CompletedBarSource.LIVE_AGGREGATE,
    health: MetricHealth = MetricHealth.READY,
) -> CompletedBarInput:
    start_ns = index * 5 * MINUTE_NS
    close_value = Decimal(close)
    return CompletedBarInput(
        instrument_id="ESU6.CME",
        bar_specification="5-MINUTE-LAST-EXTERNAL",
        calendar_id="cme_equity",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        trade_date=date(2026, 8, 24),
        session_id="cme_equity:2026-08-24:OPEN",
        window_id="primary",
        interval_start_ns=start_ns,
        interval_end_ns=start_ns + 5 * MINUTE_NS,
        open=close_value,
        high=Decimal(high),
        low=Decimal(low),
        close=close_value,
        volume=None if volume is None else Decimal(volume),
        source=source,
        observed_ts_ns=start_ns + 5 * MINUTE_NS,
        received_ts_ns=start_ns + 5 * MINUTE_NS + 1,
        normalized_ts_ns=start_ns + 5 * MINUTE_NS + 2,
        health=health,
        fidelity=MetricFidelity.REPORTED,
        evidence_refs=(f"bar:{index}",),
        complete=True,
        missing_reasons=() if volume is not None else ("volume_unsupported",),
    )


def _high_sequence() -> tuple[CompletedBarInput, ...]:
    return (
        _bar(0, high="101", low="99", close="100"),
        _bar(1, high="105", low="100", close="104", volume="25"),
        _bar(2, high="103", low="98", close="99"),
    )


def test_confirmed_swing_is_not_published_before_right_span() -> None:
    owner = _owner()
    first, pivot, confirmation = _high_sequence()

    assert owner.ingest(first, now_ns=first.normalized_ts_ns) == ()
    assert owner.ingest(pivot, now_ns=pivot.normalized_ts_ns) == ()
    revisions = owner.ingest(confirmation, now_ns=confirmation.normalized_ts_ns)

    assert len(revisions) == 1
    revision = revisions[0]
    assert revision.lifecycle is EntityLifecycle.COMPLETE
    assert revision.effective_ts_ns == confirmation.interval_end_ns
    payload = revision.payload
    assert isinstance(payload, ConfirmedSwingPayload)
    assert payload.kind is SwingKind.HIGH
    assert payload.pivot_price == Decimal("105")
    assert payload.prominence == Decimal("2")
    assert payload.confirmation_close == Decimal("99")
    assert payload.confirmation_displacement == Decimal("-6")
    assert payload.pivot_bar_volume == Decimal("25")
    assert payload.evidence_bar_refs == tuple(
        f"completed_bar:ESU6.CME:5-MINUTE-LAST-EXTERNAL:{index * 5 * MINUTE_NS + 5 * MINUTE_NS}:1"
        for index in range(3)
    )


def test_tied_pivot_is_rejected_and_duplicate_transport_does_not_republish() -> None:
    owner = _owner()
    tied = (
        _bar(0, high="105", low="99", close="100"),
        _bar(1, high="105", low="100", close="104"),
        _bar(2, high="103", low="98", close="99"),
    )
    for bar in tied:
        assert owner.ingest(bar, now_ns=bar.normalized_ts_ns) == ()

    first, pivot, confirmation = _high_sequence()
    second_owner = _owner()
    for bar in (first, pivot):
        second_owner.ingest(bar, now_ns=bar.normalized_ts_ns)
    assert len(second_owner.ingest(confirmation, now_ns=confirmation.normalized_ts_ns)) == 1
    historical_copy = replace(
        confirmation,
        source=CompletedBarSource.HISTORICAL_PROVIDER,
        received_ts_ns=confirmation.received_ts_ns + 10,
        normalized_ts_ns=confirmation.normalized_ts_ns + 10,
    )
    assert second_owner.ingest(historical_copy, now_ns=historical_copy.normalized_ts_ns) == ()
    assert second_owner.counts.bars_duplicate == 1
    assert second_owner.retained_entities == 1


def test_late_bar_completes_contiguous_evidence_without_look_ahead() -> None:
    owner = _owner()
    first, pivot, confirmation = _high_sequence()

    owner.ingest(first, now_ns=first.normalized_ts_ns)
    owner.ingest(confirmation, now_ns=confirmation.normalized_ts_ns)
    assert owner.retained_entities == 0

    revisions = owner.ingest(pivot, now_ns=confirmation.normalized_ts_ns + 100)

    assert len(revisions) == 1
    assert revisions[0].effective_ts_ns == confirmation.interval_end_ns
    assert revisions[0].published_ts_ns == confirmation.normalized_ts_ns + 100


def test_detector_and_horizon_are_part_of_identity() -> None:
    tactical = _definition(detector_id="tactical", horizon="intraday_5m")
    structural = replace(
        tactical,
        applications=(
            replace(
                tactical.applications[0],
                application_id="structural-application",
                detector_id="structural",
                horizon="structural_5m",
            ),
        ),
    )
    combined = replace(tactical, applications=(*tactical.applications, *structural.applications))
    owner = _owner(combined)

    revisions = ()
    for bar in _high_sequence():
        revisions += owner.ingest(bar, now_ns=bar.normalized_ts_ns)

    assert len(revisions) == 2
    assert len({item.entity_id for item in revisions}) == 2
    assert {
        (item.payload.detector_id, item.payload.horizon)
        for item in revisions
        if isinstance(item.payload, ConfirmedSwingPayload)
    } == {("tactical", "intraday_5m"), ("structural", "structural_5m")}


def test_health_fidelity_and_missing_volume_remain_explicit() -> None:
    owner = _owner()
    first, pivot, confirmation = _high_sequence()
    pivot = replace(
        pivot,
        volume=None,
        health=MetricHealth.DEGRADED,
        missing_reasons=("volume_unsupported",),
    )
    for bar in (first, pivot):
        owner.ingest(bar, now_ns=bar.normalized_ts_ns)
    revision = owner.ingest(confirmation, now_ns=confirmation.normalized_ts_ns)[0]

    assert revision.health is MetricHealth.DEGRADED
    assert revision.fidelity is MetricFidelity.PARTIAL
    assert isinstance(revision.payload, ConfirmedSwingPayload)
    assert revision.payload.pivot_bar_volume is None
    assert {item.definition_id for item in revision.evidence_refs} == {
        SWING_PIVOT_PRICE_METRIC_ID,
        SWING_PROMINENCE_METRIC_ID,
    }


def test_bar_and_confirmed_entity_retention_are_bounded() -> None:
    owner = _owner(_definition(maximum_retained_bars=3), maximum_entities=1)
    bars = (
        _bar(0, high="101", low="99", close="100"),
        _bar(1, high="105", low="100", close="104"),
        _bar(2, high="103", low="98", close="99"),
        _bar(3, high="106", low="100", close="105"),
        _bar(4, high="102", low="97", close="98"),
    )
    published = ()
    for bar in bars:
        published += owner.ingest(bar, now_ns=bar.normalized_ts_ns)

    assert len(published) == 3
    assert owner.retained_bars == 3
    assert owner.retained_entities == 1
    assert owner.counts.entities_evicted == 2


def test_definition_rejects_hidden_or_incomplete_detector_contracts() -> None:
    valid = _definition()
    with pytest.raises(ValueError, match="smaller than the detector span"):
        replace(valid.applications[0], maximum_retained_bars=2)
    with pytest.raises(ValueError, match="identity dimensions"):
        replace(
            valid,
            definition=replace(valid.definition, identity_dimensions=("pivot_timestamp",)),
        )
