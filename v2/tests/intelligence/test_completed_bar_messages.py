from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from nautilus_trader.model import DataType

from markeitech.intelligence import (
    BarCompletionState,
    CompletedBarLineageEntry,
    CompletedBarSeriesIdentity,
    CompletedBarV1,
    MetricFidelity,
    MetricHealth,
    MetricReasonCode,
    VolumeState,
)
from markeitech.intelligence.completed_bar_messages import (
    _canonical_completed_bar_data_type,
    _validate_completed_bar_route,
)

SECOND_NS = 1_000_000_000
RUN_EPOCH = UUID("11111111-1111-1111-1111-111111111111")
CONFIGURATION_EPOCH = UUID("22222222-2222-2222-2222-222222222222")
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def _identity(*, series_id: str = "es_1m") -> CompletedBarSeriesIdentity:
    return CompletedBarSeriesIdentity(
        instrument_id="ESU6.CME",
        venue="CME",
        provider_id="IB",
        adapter_id="nautilus-ib",
        source_stream_id="watchlist-last-5s",
        source_selector="ESU6.CME-5-SECOND-LAST-EXTERNAL",
        canonical_bar_specification="ESU6.CME-1-MINUTE-LAST-EXTERNAL",
        interval_ns=60 * SECOND_NS,
        aggregation_policy="contiguous-fixed-interval",
        timestamp_policy="interval_end",
        completion_policy="closed-interval-complete-or-partial",
        revision_policy="reject",
        calendar_id="cme_equity",
        calendar_definition_version=4,
        calendar_definition_digest=DIGEST_A,
        calendar_definition_effective_from_ns=SECOND_NS,
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        configuration_epoch=CONFIGURATION_EPOCH,
        configuration_digest=DIGEST_B,
        canonical_producer_id="COMPLETED-BARS-1",
        output_schema_version=1,
        series_id=series_id,
    )


def _lineage(
    *,
    source_class: str = "LIVE",
    observation_ref: str = "ib:bar:1",
) -> CompletedBarLineageEntry:
    return CompletedBarLineageEntry(
        source_class=source_class,  # type: ignore[arg-type]
        provider_observation_ref=observation_ref,
        evidence_refs=(f"evidence:{observation_ref}",),
        source_observed_ts_ns=61 * SECOND_NS,
        source_received_ts_ns=61 * SECOND_NS + 1,
        normalized_ts_ns=61 * SECOND_NS + 2,
        transformation_chain=("native-fixed-point-copy", "five-second-to-one-minute"),
    )


def _bar(
    *,
    completion_state: BarCompletionState = BarCompletionState.COMPLETE,
    volume: Decimal | None = Decimal("0"),
    volume_state: VolumeState = VolumeState.OBSERVED,
) -> CompletedBarV1:
    partial = completion_state is BarCompletionState.PARTIAL
    return CompletedBarV1(
        series_id="es_1m",
        series_identity=_identity(),
        interval_start_ns=SECOND_NS,
        interval_end_ns=61 * SECOND_NS,
        run_epoch=RUN_EPOCH,
        publication_sequence=1,
        completion_state=completion_state,
        expected_constituent_count=12,
        received_constituent_count=11 if partial else 12,
        missing_subintervals=((56 * SECOND_NS, 61 * SECOND_NS),) if partial else (),
        completion_reasons=(
            (
                MetricReasonCode.PARTIAL_COMPLETED_BAR,
                MetricReasonCode.MISSING_SUBINTERVALS,
            )
            if partial
            else ()
        ),
        open=Decimal("100.000000001"),
        high=Decimal("101.000000002"),
        low=Decimal("99.000000003"),
        close=Decimal("100.500000004"),
        volume=volume,
        volume_state=volume_state,
        trade_date=date(2026, 9, 1),
        exchange_state="OPEN",
        product_phases=("GLOBEX", "NEW_YORK"),
        state_evidence_refs=("calendar-state:4",),
        projection_evidence_refs=("calendar-projection:4",),
        published_ts_ns=61 * SECOND_NS + 3,
        lineage=(_lineage(),),
        health=MetricHealth.DEGRADED if partial else MetricHealth.READY,
        fidelity=MetricFidelity.PARTIAL if partial else MetricFidelity.DERIVED,
        evidence_refs=("completed-bar:es_1m:1",),
    )


def test_series_identity_digest_is_deterministic_and_epoch_sensitive() -> None:
    first = _identity()
    second = _identity()

    assert first.identity_digest == second.identity_digest
    assert CompletedBarSeriesIdentity.from_dict(first.to_dict()) == first
    changed = replace(first, configuration_epoch=UUID("33333333-3333-3333-3333-333333333333"))
    assert changed.identity_digest != first.identity_digest


def test_completed_bar_round_trip_preserves_decimal_and_observed_zero_volume() -> None:
    bar = _bar()

    restored = CompletedBarV1.from_dict(bar.to_dict())

    assert restored == bar
    assert restored.to_bytes() == bar.to_bytes()
    assert restored.volume == Decimal("0")
    assert restored.volume_state is VolumeState.OBSERVED
    assert restored.ts_event == 61 * SECOND_NS
    assert restored.ts_init == 61 * SECOND_NS + 3


def test_completed_bar_deserialization_rejects_shape_type_and_decimal_coercion() -> None:
    canonical = _bar().to_dict()

    with pytest.raises(ValueError, match="keys are not exact"):
        CompletedBarV1.from_dict({**canonical, "unknown": None})
    missing = dict(canonical)
    missing.pop("lineage")
    with pytest.raises(ValueError, match="keys are not exact"):
        CompletedBarV1.from_dict(missing)
    with pytest.raises(ValueError, match="canonical Decimal string"):
        CompletedBarV1.from_dict({**canonical, "open": 100.0})
    with pytest.raises(ValueError, match="canonical Decimal string"):
        CompletedBarV1.from_dict({**canonical, "volume": 0.0})
    with pytest.raises(ValueError, match="publication_sequence must be an integer"):
        CompletedBarV1.from_dict({**canonical, "publication_sequence": "1"})
    with pytest.raises(ValueError, match="interval_start_ns must be an integer"):
        CompletedBarV1.from_dict({**canonical, "interval_start_ns": True})


def test_nested_completed_bar_identity_and_lineage_deserialization_fail_closed() -> None:
    identity = _identity().to_dict()
    lineage = _lineage().to_dict()

    with pytest.raises(ValueError, match="keys are not exact"):
        CompletedBarSeriesIdentity.from_dict({**identity, "unknown": "value"})
    with pytest.raises(ValueError, match="interval_ns must be an integer"):
        CompletedBarSeriesIdentity.from_dict({**identity, "interval_ns": "60000000000"})
    with pytest.raises(ValueError, match="keys are not exact"):
        CompletedBarLineageEntry.from_dict({**lineage, "unknown": "value"})
    with pytest.raises(ValueError, match="source_observed_ts_ns must be an integer"):
        CompletedBarLineageEntry.from_dict({**lineage, "source_observed_ts_ns": True})


def test_completed_bar_preserves_finite_negative_prices_without_global_clipping() -> None:
    bar = replace(
        _bar(),
        open=Decimal("-2.0"),
        high=Decimal("-1.0"),
        low=Decimal("-3.0"),
        close=Decimal("-1.5"),
    )

    assert CompletedBarV1.from_dict(bar.to_dict()) == bar


def test_partial_bar_requires_exact_missing_intervals_and_typed_reasons() -> None:
    partial = _bar(completion_state=BarCompletionState.PARTIAL)

    assert partial.received_constituent_count == 11
    assert partial.health is MetricHealth.DEGRADED
    with pytest.raises(ValueError, match="typed partial"):
        replace(partial, completion_reasons=(MetricReasonCode.PARTIAL_COMPLETED_BAR,))
    with pytest.raises(ValueError, match="canonical"):
        replace(
            partial,
            completion_reasons=(
                MetricReasonCode.MISSING_SUBINTERVALS,
                MetricReasonCode.PARTIAL_COMPLETED_BAR,
            ),
        )
    with pytest.raises(ValueError, match="reconcile"):
        replace(partial, missing_subintervals=())
    with pytest.raises(ValueError, match="DEGRADED health"):
        replace(partial, health=MetricHealth.READY)
    with pytest.raises(ValueError, match="PARTIAL fidelity"):
        replace(partial, fidelity=MetricFidelity.DERIVED)


def test_missing_subintervals_require_exact_aligned_unique_constituent_slots() -> None:
    partial = _bar(completion_state=BarCompletionState.PARTIAL)

    with pytest.raises(ValueError, match="exact constituent slots"):
        replace(
            partial,
            missing_subintervals=((51 * SECOND_NS + 1, 56 * SECOND_NS + 1),),
        )
    with pytest.raises(ValueError, match="exact constituent slots"):
        replace(partial, missing_subintervals=((56 * SECOND_NS, 60 * SECOND_NS),))
    two_missing = replace(
        partial,
        received_constituent_count=10,
        missing_subintervals=((51 * SECOND_NS, 56 * SECOND_NS), (56 * SECOND_NS, 61 * SECOND_NS)),
    )
    with pytest.raises(ValueError, match="unique, ordered"):
        replace(
            two_missing,
            missing_subintervals=((56 * SECOND_NS, 61 * SECOND_NS),) * 2,
        )


def test_volume_truth_rejects_numeric_missingness_and_preserves_unsupported_null() -> None:
    unsupported = _bar(volume=None, volume_state=VolumeState.UNSUPPORTED)

    assert CompletedBarV1.from_dict(unsupported.to_dict()) == unsupported
    with pytest.raises(ValueError, match="null value"):
        _bar(volume=Decimal("0"), volume_state=VolumeState.UNSUPPORTED)
    with pytest.raises(ValueError, match="requires a value"):
        _bar(volume=None, volume_state=VolumeState.OBSERVED)


def test_metadata_qualified_route_is_exact_and_rejects_payload_mismatch() -> None:
    bar = _bar()
    route = _canonical_completed_bar_data_type("es_1m")
    other_route = _canonical_completed_bar_data_type("other_series")

    assert route.topic == "markeitech.completed_bar.canonical.v1.series_id=es_1m"
    assert route != other_route
    _validate_completed_bar_route(route, bar)
    with pytest.raises(ValueError, match="metadata"):
        _validate_completed_bar_route(other_route, bar)
    identifier_route = DataType(
        "markeitech.completed_bar.canonical.v1",
        metadata={"series_id": "es_1m"},
        identifier="unexpected",
    )
    with pytest.raises(ValueError, match="identifier must be None"):
        _validate_completed_bar_route(identifier_route, bar)


@pytest.mark.parametrize("series_id", ("es.1m", "es=1m", "es*", "é"))
def test_series_id_rejects_unsafe_topic_tokens(series_id: str) -> None:
    with pytest.raises(ValueError, match="series_id"):
        _identity(series_id=series_id)


def test_trade_date_rejects_datetime_subclasses() -> None:
    with pytest.raises(ValueError, match="trade_date"):
        replace(_bar(), trade_date=datetime(2026, 9, 1))


def test_payload_bounds_reject_overlong_lineage_and_evidence_without_truncation() -> None:
    bar = _bar()
    lineage = tuple(_lineage(observation_ref=f"ib:bar:{index}") for index in range(65))
    with pytest.raises(ValueError, match="1 through 64"):
        replace(bar, lineage=lineage)
    with pytest.raises(ValueError, match="at most 256"):
        replace(bar, evidence_refs=tuple(f"evidence:{index}" for index in range(257)))
