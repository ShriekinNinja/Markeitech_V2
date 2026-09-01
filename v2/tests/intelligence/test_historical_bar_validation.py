from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from markeitech.intelligence import (
    BarCompletionState,
    CompletedBarLineageEntry,
    CompletedBarSeriesIdentity,
    MetricFidelity,
    MetricHealth,
    VolumeState,
)
from markeitech.intelligence.historical_bar_validation import (
    _bounded_calculation_observations,
    _canonical_admission_observations,
    _HistoricalBarObservation,
    _HistoricalUsage,
    _HistoricalValidationDisposition,
    _HistoricalValidationReason,
    _HistoricalValidationRequest,
    _validate_historical_batch,
)

SECOND_NS = 1_000_000_000
MINUTE_NS = 60 * SECOND_NS
CONFIGURATION_EPOCH = UUID("11111111-1111-1111-1111-111111111111")


def _series() -> CompletedBarSeriesIdentity:
    return CompletedBarSeriesIdentity(
        instrument_id="ESU6.CME",
        venue="CME",
        provider_id="IB",
        adapter_id="nautilus-ib",
        source_stream_id="historical-bars",
        source_selector="ESU6.CME-1-MINUTE-LAST-EXTERNAL",
        canonical_bar_specification="ESU6.CME-1-MINUTE-LAST-EXTERNAL",
        interval_ns=MINUTE_NS,
        aggregation_policy="direct-provider-completed-bar",
        timestamp_policy="interval_end",
        completion_policy="closed-interval-complete-or-partial",
        revision_policy="reject",
        calendar_id="cme_equity",
        calendar_definition_version=4,
        calendar_definition_digest="a" * 64,
        calendar_definition_effective_from_ns=SECOND_NS,
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        configuration_epoch=CONFIGURATION_EPOCH,
        configuration_digest="b" * 64,
        canonical_producer_id="COMPLETED-BARS-1",
        output_schema_version=1,
        series_id="es_1m",
    )


def _lineage(index: int, *, suffix: str = "primary") -> CompletedBarLineageEntry:
    interval_end = (index + 2) * MINUTE_NS
    return CompletedBarLineageEntry(
        source_class="HISTORICAL",
        provider_observation_ref=f"ib:historical:{index}:{suffix}",
        evidence_refs=(f"request-evidence:{suffix}",),
        source_observed_ts_ns=interval_end,
        source_received_ts_ns=interval_end + 1,
        normalized_ts_ns=interval_end + 2,
        transformation_chain=("native-fixed-point-copy",),
    )


def _observation(index: int, *, close: Decimal | None = None) -> _HistoricalBarObservation:
    start = (index + 1) * MINUTE_NS
    base = Decimal("100") + index
    return _HistoricalBarObservation(
        series_identity=_series(),
        interval_start_ns=start,
        interval_end_ns=start + MINUTE_NS,
        completion_state=BarCompletionState.COMPLETE,
        expected_constituent_count=1,
        received_constituent_count=1,
        missing_subintervals=(),
        open=base,
        high=base + 1,
        low=base - 1,
        close=base + Decimal("0.5") if close is None else close,
        volume=Decimal("10"),
        volume_state=VolumeState.OBSERVED,
        source_revision=1,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.REPORTED,
        lineage=(_lineage(index),),
        evidence_refs=(f"bar:{index}",),
    )


def _partial_observation(index: int) -> _HistoricalBarObservation:
    interval_end = (index + 2) * MINUTE_NS
    return replace(
        _observation(index),
        completion_state=BarCompletionState.PARTIAL,
        expected_constituent_count=12,
        received_constituent_count=11,
        missing_subintervals=((interval_end - 5 * SECOND_NS, interval_end),),
        health=MetricHealth.DEGRADED,
        fidelity=MetricFidelity.PARTIAL,
    )


def _request(
    usage: _HistoricalUsage = _HistoricalUsage.CANONICAL_SERIES_BOOTSTRAP,
    *,
    maximum_raw_observations: int = 8,
) -> _HistoricalValidationRequest:
    return _HistoricalValidationRequest.build(
        request_id="history-es-1m-001",
        usage=usage,
        series_identity=_series(),
        requested_start_ns=MINUTE_NS,
        requested_end_ns=4 * MINUTE_NS,
        maximum_raw_observations=maximum_raw_observations,
    )


def test_complete_batch_collapses_exact_duplicate_and_merges_lineage_once() -> None:
    duplicate = replace(
        _observation(1),
        lineage=(_lineage(1, suffix="overlap"),),
        evidence_refs=("bar:1:overlap",),
    )

    result = _validate_historical_batch(
        _request(),
        (_observation(0), _observation(1), duplicate, _observation(2)),
    )

    assert result.disposition is _HistoricalValidationDisposition.COMPLETE
    assert result.raw_count == 4
    assert result.accepted_unique_count == 3
    assert result.duplicate_count == 1
    assert result.conflict_count == 0
    assert result.gap_count == 0
    assert len(result.observations[1].lineage) == 2
    assert _canonical_admission_observations(result) == result.observations
    assert (
        result.to_bytes()
        == _validate_historical_batch(
            _request(),
            (_observation(0), _observation(1), duplicate, _observation(2)),
        ).to_bytes()
    )


def test_historical_observation_preserves_finite_negative_prices() -> None:
    observation = replace(
        _observation(0),
        open=Decimal("-2.0"),
        high=Decimal("-1.0"),
        low=Decimal("-3.0"),
        close=Decimal("-1.5"),
    )

    result = _validate_historical_batch(
        _request(),
        (observation, _observation(1), _observation(2)),
    )

    assert result.disposition is _HistoricalValidationDisposition.COMPLETE
    assert result.observations[0].close == Decimal("-1.5")


def test_missing_interval_returns_partial_with_usable_ordered_evidence_and_reasons() -> None:
    result = _validate_historical_batch(
        _request(_HistoricalUsage.BOUNDED_BATCH_CALCULATION),
        (_observation(0), _observation(2)),
    )

    assert result.disposition is _HistoricalValidationDisposition.PARTIAL
    assert result.missing_intervals == ((2 * MINUTE_NS, 3 * MINUTE_NS),)
    assert result.reasons == (_HistoricalValidationReason.MISSING_INTERVALS,)
    assert result.health is MetricHealth.DEGRADED
    assert result.fidelity is MetricFidelity.PARTIAL
    assert _bounded_calculation_observations(result) == result.observations
    with pytest.raises(ValueError, match="cannot enter canonical"):
        _canonical_admission_observations(result)


def test_partial_historical_observation_preserves_honest_partial_result() -> None:
    result = _validate_historical_batch(
        _request(),
        (_observation(0), _partial_observation(1), _observation(2)),
    )

    assert result.disposition is _HistoricalValidationDisposition.PARTIAL
    assert result.health is MetricHealth.DEGRADED
    assert result.fidelity is MetricFidelity.PARTIAL
    assert result.reasons == (_HistoricalValidationReason.PARTIAL_OBSERVATION,)


def test_historical_completion_and_slot_evidence_fail_closed() -> None:
    with pytest.raises(ValueError, match="COMPLETE historical observations require READY"):
        replace(_observation(0), health=MetricHealth.UNAVAILABLE)
    with pytest.raises(ValueError, match="COMPLETE historical observations require READY"):
        replace(_observation(0), fidelity=MetricFidelity.UNAVAILABLE)

    partial = _partial_observation(0)
    with pytest.raises(ValueError, match="exact constituent slots"):
        replace(
            partial,
            missing_subintervals=(
                (2 * MINUTE_NS - 10 * SECOND_NS + 1, 2 * MINUTE_NS - 5 * SECOND_NS + 1),
            ),
        )
    with pytest.raises(ValueError, match="exact constituent slots"):
        replace(
            partial,
            missing_subintervals=((2 * MINUTE_NS - 5 * SECOND_NS, 2 * MINUTE_NS - SECOND_NS),),
        )


def test_unequal_same_interval_is_rejected_and_exposes_no_usable_bars() -> None:
    conflict = replace(_observation(0), close=Decimal("100.75"))

    result = _validate_historical_batch(_request(), (_observation(0), conflict))

    assert result.disposition is _HistoricalValidationDisposition.REJECTED
    assert result.raw_count == 2
    assert result.accepted_unique_count == 1
    assert result.conflict_count == 1
    assert result.observations == ()
    assert _HistoricalValidationReason.UNEQUAL_INTERVAL_CONFLICT in result.reasons
    assert _canonical_admission_observations(result) == ()


def test_out_of_order_identity_mismatch_and_revision_are_rejected() -> None:
    wrong_identity = replace(
        _observation(0),
        series_identity=replace(_series(), instrument_id="NQU6.CME"),
    )
    revised = replace(_observation(1), source_revision=2)

    result = _validate_historical_batch(
        _request(),
        (_observation(2), wrong_identity, revised),
    )

    assert result.disposition is _HistoricalValidationDisposition.REJECTED
    assert result.observations == ()
    assert _HistoricalValidationReason.IDENTITY_MISMATCH in result.reasons
    assert _HistoricalValidationReason.ORDERING_INVALID in result.reasons
    assert _HistoricalValidationReason.REVISION_REJECTED in result.reasons


def test_empty_batch_is_partial_data_state_not_an_exception() -> None:
    result = _validate_historical_batch(_request(), ())

    assert result.disposition is _HistoricalValidationDisposition.PARTIAL
    assert result.raw_count == 0
    assert result.accepted_unique_count == 0
    assert result.gap_count == 3
    assert result.observations == ()
    assert result.health is MetricHealth.UNAVAILABLE
    assert result.reasons == (
        _HistoricalValidationReason.MISSING_INTERVALS,
        _HistoricalValidationReason.EMPTY_BATCH,
    )


def test_raw_batch_bound_and_usage_isolation_fail_before_any_canonical_leak() -> None:
    request = _request(maximum_raw_observations=3)
    with pytest.raises(ValueError, match="hard bound"):
        _validate_historical_batch(
            request,
            (_observation(0), _observation(1), _observation(2), _observation(2)),
        )


def test_historical_request_range_and_raw_allocation_ceiling_are_explicit() -> None:
    with pytest.raises(ValueError, match="15-interval"):
        _HistoricalValidationRequest.build(
            request_id="history-too-wide",
            usage=_HistoricalUsage.CANONICAL_SERIES_BOOTSTRAP,
            series_identity=_series(),
            requested_start_ns=MINUTE_NS,
            requested_end_ns=17 * MINUTE_NS,
            maximum_raw_observations=16,
        )
    with pytest.raises(ValueError, match="16-observation"):
        _request(maximum_raw_observations=17)

    complete = _validate_historical_batch(
        _request(_HistoricalUsage.BOUNDED_BATCH_CALCULATION),
        (_observation(0), _observation(1), _observation(2)),
    )
    with pytest.raises(ValueError, match="cannot enter canonical"):
        _canonical_admission_observations(complete)
    with pytest.raises(ValueError, match="cannot use the local"):
        _bounded_calculation_observations(
            _validate_historical_batch(
                _request(),
                (_observation(0), _observation(1), _observation(2)),
            ),
        )


def test_request_digest_is_deterministic_and_usage_sensitive() -> None:
    canonical = _request()
    bounded = _request(_HistoricalUsage.BOUNDED_BATCH_CALCULATION)

    assert canonical.request_digest == _request().request_digest
    assert canonical.request_digest != bounded.request_digest
    with pytest.raises(ValueError, match="does not match"):
        replace(canonical, request_digest="f" * 64)


def test_result_envelope_rejects_untyped_reasons_and_unordered_usable_bars() -> None:
    result = _validate_historical_batch(
        _request(),
        (_observation(0), _observation(1), _observation(2)),
    )

    with pytest.raises(ValueError, match="reasons must be typed"):
        replace(result, reasons=("MISSING_INTERVALS",))
    with pytest.raises(ValueError, match="unique and ordered"):
        replace(result, observations=tuple(reversed(result.observations)))
    with pytest.raises(ValueError, match="exact valid requested evidence"):
        replace(result, health=MetricHealth.UNAVAILABLE, fidelity=MetricFidelity.UNAVAILABLE)
