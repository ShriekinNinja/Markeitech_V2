from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import date
from decimal import Decimal
from functools import partial
from threading import Event
from types import MappingProxyType, SimpleNamespace
from uuid import UUID

import pytest
from nautilus_trader.common import (
    Clock,
    DataActor,
    DataActorConfig,
    Environment,
    ImportableActorConfig,
    Signal,
)
from nautilus_trader.live import LiveNode
from nautilus_trader.model import (
    ActorId,
    Bar,
    BarType,
    CustomData,
    DataType,
    Price,
    Quantity,
    TraderId,
)

from markeitech.acquisition import (
    HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
    FeedKind,
    HistoricalBatch,
    HistoricalDependencyDemandEvent,
    HistoricalDependencyRef,
    HistoricalRequest,
)
from markeitech.acquisition.demand import HistoricalWindow
from markeitech.acquisition.historical_execution import HistoricalExecutionPort
from markeitech.intelligence import (
    BarCompletionState,
    CompletedBarInputIdentity,
    CompletedBarLineageEntry,
    CompletedBarSeriesIdentity,
    CompletedBarV1,
    MetricFidelity,
    MetricHealth,
    VolumeState,
)
from markeitech.intelligence.calendar_delivery import ProjectionRequestPhase
from markeitech.intelligence.calendar_messages import (
    CALENDAR_PROJECTION_REQUEST_TYPE_NAME,
    CALENDAR_PROJECTION_RESPONSE_TYPE_NAME,
    CALENDAR_STATE_SNAPSHOT_REQUEST_TYPE_NAME,
    CALENDAR_STATE_SNAPSHOT_RESPONSE_TYPE_NAME,
    CALENDAR_TRANSITION_V2_TYPE_NAME,
    CalendarCurrentState,
    CalendarProjectionRequest,
    CalendarProjectionResponse,
    CalendarStateSnapshotRequest,
    CalendarStateSnapshotResponse,
    CalendarTransitionV2,
)
from markeitech.intelligence.completed_bar_foundation import (
    _FOUNDATION_SHUTDOWN_TYPE_NAME,
    _READINESS_TYPE_NAME,
    _candidate_from_historical,
    _CompletedBarFoundationActor,
    _CompletedBarFoundationActorConfig,
    _CompletedBarFoundationPolicy,
    _CompletedBarFoundationSeriesConfig,
    _constituent_from_native_bar,
    _FoundationSeriesState,
    _FoundationShutdownSummary,
    _HistoricalBootstrapBinding,
    _LiveConstituent,
    _NativeLiveInputAuthority,
    _next_cutoff_interval_end,
    _SeriesAdmission,
)
from markeitech.intelligence.completed_bar_messages import COMPLETED_BAR_V1_TYPE_NAME
from markeitech.intelligence.historical_bar_validation import (
    _HistoricalBarObservation,
    _HistoricalUsage,
    _HistoricalValidationRequest,
    _validate_historical_batch,
)
from markeitech.intelligence.metric_producer_manifest import (
    _ActivationDisposition,
    _BarSeriesProducerClaim,
    _StartupConsumerRequirement,
    _SubscriptionReadinessAcknowledgement,
    _SubscriptionReadinessStatus,
)
from markeitech.intelligence.session import (
    CalendarProjection,
    ExchangeSessionSegment,
    SessionWindow,
)
from markeitech.system.messages import ANALYTICAL_DEMAND_SIGNAL, AnalyticalDemandEvent

SECOND_NS = 1_000_000_000
MINUTE_NS = 60 * SECOND_NS
RUN_EPOCH = UUID("11111111-1111-1111-1111-111111111111")
STARTUP_EPOCH = UUID("22222222-2222-2222-2222-222222222222")
CONFIGURATION_EPOCH = UUID("33333333-3333-3333-3333-333333333333")
CALENDAR_DIGEST = "a" * 64
CONFIGURATION_DIGEST = "b" * 64
MANIFEST_DIGEST = "c" * 64
TRADE_DATE = date(2026, 9, 1)
_ROUTING_RECEIVED = Event()
_ROUTING_COUNTS: dict[str, int] = {}
_DEMAND_RECEIVED = Event()
_STARTUP_ORDER: list[str] = []
_CALENDAR_READY = Event()
_PROJECTION_REFRESH_READY = Event()
_REVISION_GAP_RECOVERED = Event()
_CALENDAR_REQUESTS: dict[str, list[object]] = {"projection": [], "snapshot": []}
_CALENDAR_PROTOCOL_STATE: dict[str, object] = {}
_LIFECYCLE_BAR_PUBLISHED = Event()
_LIFECYCLE_COUNTS: dict[str, object] = {}
_LIFECYCLE_CALLS: dict[str, list[object]] = {
    "subscribe_data": [],
    "unsubscribe_data": [],
    "subscribe_bars": [],
    "unsubscribe_bars": [],
    "signals": [],
}


class _HistoricalAuthorityPort:
    provider_id = "IB"
    adapter_id = "nautilus-ib"
    source_stream_id = "historical-bars"
    source_schema_id = "nautilus.bar.v1"

    def __init__(self, **overrides: str) -> None:
        for field_name, value in overrides.items():
            setattr(self, field_name, value)
        self.submitted: list[HistoricalRequest] = []

    def submit(self, request: HistoricalRequest) -> None:
        self.submitted.append(request)

    def cancel(self, _request: HistoricalRequest) -> None:
        return


def _series(
    *,
    series_id: str = "es_1m",
    instrument_id: str = "ESU6.CME",
) -> CompletedBarSeriesIdentity:
    return CompletedBarSeriesIdentity(
        instrument_id=instrument_id,
        venue="CME",
        canonical_bar_specification=f"{instrument_id}-1-MINUTE-LAST-EXTERNAL",
        interval_ns=MINUTE_NS,
        aggregation_policy="contiguous-fixed-interval",
        timestamp_policy="interval_end",
        completion_policy="closed-interval-complete-or-partial",
        revision_policy="reject",
        calendar_id="cme_equity",
        calendar_definition_version=4,
        calendar_definition_digest=CALENDAR_DIGEST,
        calendar_definition_effective_from_ns=SECOND_NS,
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        configuration_epoch=CONFIGURATION_EPOCH,
        configuration_digest=CONFIGURATION_DIGEST,
        canonical_producer_id="COMPLETED-BARS-1",
        output_schema_version=1,
        series_id=series_id,
    )


def _input_identity(
    source_class: str,
    *,
    instrument_id: str = "ESU6.CME",
) -> CompletedBarInputIdentity:
    historical = source_class == "HISTORICAL"
    return CompletedBarInputIdentity(
        provider_id="IB",
        adapter_id="nautilus-ib",
        source_stream_id="historical-bars" if historical else "watchlist-last-5s",
        source_selector=(
            f"{instrument_id}-1-MINUTE-LAST-EXTERNAL"
            if historical
            else f"{instrument_id}-5-SECOND-LAST-EXTERNAL"
        ),
        source_schema_id="nautilus.bar.v1",
    )


def _transport_request(
    *,
    start_ns: int,
    end_ns: int,
    limit: int,
    request_id: str = "history-es-1m-001",
    instrument_id: str = "ESU6.CME",
) -> HistoricalRequest:
    return HistoricalRequest(
        request_id=request_id,
        instrument_id=instrument_id,
        kind=FeedKind.BARS,
        selector="1-MINUTE-LAST-EXTERNAL",
        window=HistoricalWindow.RECENT_COMPLETED,
        start_ns=start_ns,
        end_ns=end_ns,
        limit=limit,
        priority=50,
        parameters=MappingProxyType({"usage": "canonical_series_bootstrap"}),
        dependencies=(
            HistoricalDependencyRef(
                consumer_id="COMPLETED-BARS-1",
                capability_id="metric:completed-bar-foundation",
                capability_version=1,
                requirement_index=0,
                minimum_observations=limit,
                purpose="canonical_series_bootstrap",
            ),
        ),
    )


def _config(
    *,
    start_ns: int = MINUTE_NS,
    count: int = 15,
    series_id: str = "es_1m",
    instrument_id: str = "ESU6.CME",
    request_id: str = "history-es-1m-001",
    historical_port: HistoricalExecutionPort | None = None,
    historical_identity_overrides: dict[str, str] | None = None,
) -> _CompletedBarFoundationSeriesConfig:
    identity = _series(series_id=series_id, instrument_id=instrument_id)
    end_ns = start_ns + count * MINUTE_NS
    historical_identity = _input_identity("HISTORICAL", instrument_id=instrument_id)
    if historical_identity_overrides:
        historical_identity = replace(historical_identity, **historical_identity_overrides)
    validation = _HistoricalValidationRequest.build(
        request_id=request_id,
        usage=_HistoricalUsage.CANONICAL_SERIES_BOOTSTRAP,
        series_identity=identity,
        expected_input_identity=historical_identity,
        requested_start_ns=start_ns,
        requested_end_ns=end_ns,
        maximum_raw_observations=max(16, count),
    )
    return _CompletedBarFoundationSeriesConfig(
        series_identity=identity,
        producer_claim=_BarSeriesProducerClaim(
            series_identity=identity,
            producer_actor_id="COMPLETED-BARS-1",
            producer_version=1,
            output_schema_version=1,
            dependencies=(),
            activation=_ActivationDisposition.ENABLED,
            maximum_retained_completed_bars=16,
            maximum_history_live_overlap_bars=1,
            maximum_buffered_live_completed_bars=2,
        ),
        live_input_identity=_input_identity("LIVE", instrument_id=instrument_id),
        historical_bootstrap=_HistoricalBootstrapBinding.from_execution_port(
            transport_request=_transport_request(
                start_ns=start_ns,
                end_ns=end_ns,
                limit=count,
                request_id=request_id,
                instrument_id=instrument_id,
            ),
            validation_request=validation,
            execution_port=historical_port or _HistoricalAuthorityPort(),
        ),
        live_selector="5-SECOND-LAST-EXTERNAL",
        required_consumers=(
            _StartupConsumerRequirement(
                consumer_actor_id="DIRECT-METRICS-1",
                series_id=series_id,
                producer_actor_id="COMPLETED-BARS-1",
            ),
        ),
        calendar_source="SESSION-STATE",
        calendar_source_epoch=str(RUN_EPOCH),
    )


def _state(*, start_ns: int = MINUTE_NS, count: int = 15) -> _FoundationSeriesState:
    state = _FoundationSeriesState(
        _config(start_ns=start_ns, count=count),
        _CompletedBarFoundationPolicy(),
        RUN_EPOCH,
    )
    assert state.accept_projection(_projection_response())
    return state


def _rebind_series_identity(
    config: _CompletedBarFoundationSeriesConfig,
    identity: CompletedBarSeriesIdentity,
) -> _CompletedBarFoundationSeriesConfig:
    validation = config.historical_bootstrap.validation_request
    rebound_validation = _HistoricalValidationRequest.build(
        request_id=validation.request_id,
        usage=validation.usage,
        series_identity=identity,
        expected_input_identity=validation.expected_input_identity,
        requested_start_ns=validation.requested_start_ns,
        requested_end_ns=validation.requested_end_ns,
        maximum_raw_observations=validation.maximum_raw_observations,
    )
    return replace(
        config,
        series_identity=identity,
        producer_claim=replace(config.producer_claim, series_identity=identity),
        historical_bootstrap=_HistoricalBootstrapBinding(
            config.historical_bootstrap.transport_request,
            rebound_validation,
            config.historical_bootstrap.execution_authority,
        ),
    )


def _projection_response() -> CalendarProjectionResponse:
    projection = CalendarProjection(
        calendar_id="cme_equity",
        calendar_engine="pandas_market_calendars",
        provider_calendar="CME_Equity",
        schedule_version="test-v1",
        definition_version=4,
        definition_digest=CALENDAR_DIGEST,
        definition_effective_from_ns=SECOND_NS,
        calendar_engine_version="5.1",
        exchange_timezone="America/Chicago",
        coverage_start_ns=SECOND_NS,
        coverage_end_ns=60 * MINUTE_NS,
        exchange_segments=(
            ExchangeSessionSegment(
                trade_date=TRADE_DATE,
                market_state="OPEN",
                start_ns=SECOND_NS,
                end_ns=60 * MINUTE_NS,
            ),
        ),
        phase_windows=(
            SessionWindow(
                trade_date=TRADE_DATE,
                phase="GLOBEX",
                start_ns=SECOND_NS,
                end_ns=60 * MINUTE_NS,
            ),
        ),
        correction_outcomes=(),
        normalization_outcomes=(),
    )
    return CalendarProjectionResponse(
        request_id="projection-1",
        requester="COMPLETED-BARS-1",
        source="SESSION-STATE",
        source_epoch=str(RUN_EPOCH),
        status="READY",
        requested_calendar_ids=("cme_equity",),
        projections=(projection,),
        unavailable_calendar_ids=(),
        failures=(),
        generated_ts_ns=2 * SECOND_NS,
    )


def _current_state_response() -> CalendarStateSnapshotResponse:
    current = CalendarCurrentState(
        calendar_id="cme_equity",
        schedule_version="test-v1",
        definition_version=4,
        definition_digest=CALENDAR_DIGEST,
        definition_effective_from_ns=SECOND_NS,
        trade_date=TRADE_DATE.isoformat(),
        phase_memberships=("GLOBEX",),
        market_state="OPEN",
        segment_open_ns=SECOND_NS,
        segment_close_ns=60 * MINUTE_NS,
        next_transition_ns=60 * MINUTE_NS,
        revision=1,
        previous_revision=None,
        last_transition_event_id="transition-1",
        source="SESSION-STATE",
        source_epoch=str(RUN_EPOCH),
        state_effective_from_ns=SECOND_NS,
        state_revision_evaluated_as_of_ns=2 * SECOND_NS,
        evaluated_as_of_ns=4 * SECOND_NS,
        state_revision_published_ts_ns=3 * SECOND_NS,
    )
    return CalendarStateSnapshotResponse(
        cycle_id="cycle-1",
        request_id="current-state-1",
        attempt=1,
        requester="COMPLETED-BARS-1",
        source="SESSION-STATE",
        source_epoch=str(RUN_EPOCH),
        status="READY",
        requested_calendar_ids=("cme_equity",),
        states=(current,),
        failures=(),
        requested_as_of_ns=SECOND_NS,
        requested_ts_ns=2 * SECOND_NS,
        deadline_ts_ns=10 * SECOND_NS,
        request_received_ts_ns=3 * SECOND_NS,
        evaluated_as_of_ns=4 * SECOND_NS,
        generated_ts_ns=5 * SECOND_NS,
        published_ts_ns=6 * SECOND_NS,
        delivery_policy_version=1,
    )


def _lineage(
    *,
    source_class: str,
    interval_end_ns: int,
    suffix: str,
) -> CompletedBarLineageEntry:
    return CompletedBarLineageEntry(
        source_class=source_class,  # type: ignore[arg-type]
        input_identity=_input_identity(source_class),
        provider_observation_ref=f"{source_class.lower()}:{interval_end_ns}:{suffix}",
        evidence_refs=(f"evidence:{suffix}",),
        source_observed_ts_ns=interval_end_ns,
        source_received_ts_ns=interval_end_ns + 1,
        normalized_ts_ns=interval_end_ns + 2,
        transformation_chain=("exact-decimal-copy",),
    )


def _historical_observation(index: int) -> _HistoricalBarObservation:
    start_ns = (index + 1) * MINUTE_NS
    end_ns = start_ns + MINUTE_NS
    base = Decimal(100 + index)
    return _HistoricalBarObservation(
        series_identity=_series(),
        interval_start_ns=start_ns,
        interval_end_ns=end_ns,
        completion_state=BarCompletionState.COMPLETE,
        expected_constituent_count=12,
        received_constituent_count=12,
        missing_subintervals=(),
        open=base,
        high=base + 1,
        low=base - 1,
        close=base + Decimal("0.5"),
        volume=Decimal("120"),
        volume_state=VolumeState.OBSERVED,
        source_revision=1,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.REPORTED,
        lineage=(_lineage(source_class="HISTORICAL", interval_end_ns=end_ns, suffix=str(index)),),
        evidence_refs=("calendar-projection:projection-1", f"history:{index}"),
    )


def _historical_result(count: int = 15):  # noqa: ANN202
    config = _config(count=count)
    return _validate_historical_batch(
        config.historical_bootstrap.validation_request,
        tuple(_historical_observation(index) for index in range(count)),
    )


def _constituent(
    interval_start_ns: int,
    *,
    suffix: str = "primary",
    price: Decimal = Decimal("100"),
    input_identity: CompletedBarInputIdentity | None = None,
) -> _LiveConstituent:
    interval_end_ns = interval_start_ns + 5 * SECOND_NS
    return _LiveConstituent(
        interval_start_ns=interval_start_ns,
        interval_end_ns=interval_end_ns,
        open=price,
        high=price + 1,
        low=price - 1,
        close=price + Decimal("0.5"),
        volume=Decimal("10"),
        volume_state=VolumeState.OBSERVED,
        lineage=_lineage(
            source_class="LIVE",
            interval_end_ns=interval_end_ns,
            suffix=suffix,
        )
        if input_identity is None
        else replace(
            _lineage(
                source_class="LIVE",
                interval_end_ns=interval_end_ns,
                suffix=suffix,
            ),
            input_identity=input_identity,
        ),
        evidence_refs=(f"live:{suffix}",),
    )


def _fill_live_minute(
    state: _FoundationSeriesState,
    start_ns: int,
    *,
    final_receipt_ns: int | None = None,
    price: Decimal = Decimal("100"),
) -> None:
    for slot in range(12):
        constituent = _constituent(
            start_ns + slot * 5 * SECOND_NS,
            suffix=str(slot),
            price=price,
        )
        receipt = constituent.interval_end_ns + 10
        if slot == 11 and final_receipt_ns is not None:
            receipt = final_receipt_ns
        assert state.accept_live(constituent, owner_received_at_ns=receipt) == (
            _SeriesAdmission.ACCEPTED
        )


@pytest.mark.parametrize("grace_ms", [0, 5_001, True])
def test_completion_grace_enforces_private_versioned_envelope(grace_ms: int) -> None:
    with pytest.raises(ValueError, match="completion_grace_ms"):
        _CompletedBarFoundationPolicy(completion_grace_ms=grace_ms)


def test_config_rejects_canonical_interval_and_native_authority_contradictions() -> None:
    config = _config()
    bad_canonical = replace(
        config.series_identity,
        canonical_bar_specification="ESU6.CME-15-MINUTE-LAST-EXTERNAL",
    )
    with pytest.raises(ValueError, match="canonical BarType"):
        _rebind_series_identity(config, bad_canonical)

    with pytest.raises(ValueError, match="native subscription authority"):
        replace(
            config,
            live_input_identity=replace(config.live_input_identity, provider_id="NOT-IB"),
        )

    with pytest.raises(ValueError, match="native subscription authority"):
        replace(
            config,
            live_authority=_NativeLiveInputAuthority(provider_id="NOT-IB"),
        )


@pytest.mark.parametrize(
    ("field_name", "contradictory_value"),
    [
        ("provider_id", "NOT-IB"),
        ("adapter_id", "other-adapter"),
        ("source_stream_id", "other-history"),
        ("source_schema_id", "other.schema.v1"),
    ],
)
def test_historical_execution_authority_fails_before_actor_or_demand(
    field_name: str,
    contradictory_value: str,
) -> None:
    port = _HistoricalAuthorityPort()
    actor_constructed = False

    def construct_actor() -> _CompletedBarFoundationActor:
        nonlocal actor_constructed
        config = _config(
            historical_port=port,
            historical_identity_overrides={field_name: contradictory_value},
        )
        actor_constructed = True
        return _CompletedBarFoundationActor(
            _CompletedBarFoundationActorConfig(
                series=(config,),
                startup_epoch=STARTUP_EPOCH,
                run_epoch=RUN_EPOCH,
                manifest_digest=MANIFEST_DIGEST,
            ),
        )

    with pytest.raises(ValueError, match="actual execution-port authority"):
        construct_actor()

    assert not actor_constructed
    assert port.submitted == []


def test_duplicate_live_bar_type_routes_fail_closed_at_actor_construction() -> None:
    first = _config(series_id="es_1m_a")
    second = _config(series_id="es_1m_b", request_id="history-es-1m-002")

    with pytest.raises(ValueError, match="one canonical series per live BarType"):
        _CompletedBarFoundationActor(
            _CompletedBarFoundationActorConfig(
                series=(first, second),
                startup_epoch=STARTUP_EPOCH,
                run_epoch=RUN_EPOCH,
                manifest_digest=MANIFEST_DIGEST,
            ),
        )


def test_historical_batch_source_authority_must_match_validated_input_identity() -> None:
    config = _config()
    actor = _CompletedBarFoundationActor(
        _CompletedBarFoundationActorConfig(
            series=(config,),
            startup_epoch=STARTUP_EPOCH,
            run_epoch=RUN_EPOCH,
            manifest_digest=MANIFEST_DIGEST,
        ),
    )
    state = actor.states[config.series_id]
    state.demand_started = True
    actor._active = True
    batch = HistoricalBatch(
        config.historical_bootstrap.transport_request,
        (),
        20 * MINUTE_NS,
        "NOT-IB",
        "nautilus-ib",
        "historical-bars",
        "nautilus.bar.v1",
    )

    actor._accept_historical_batch(batch, received_at_ns=20 * MINUTE_NS)

    assert state.counters["historical_source_authority_rejected"] == 1
    assert not state.history_terminal


def test_constituent_just_before_cutoff_is_admitted_but_exact_cutoff_is_late() -> None:
    state = _state()
    start_ns = 16 * MINUTE_NS
    cutoff_ns = 17 * MINUTE_NS + SECOND_NS
    before = _constituent(start_ns, suffix="before")
    at_cutoff = _constituent(start_ns + 5 * SECOND_NS, suffix="cutoff")

    assert state.accept_live(before, owner_received_at_ns=cutoff_ns - 1) == (
        _SeriesAdmission.ACCEPTED
    )
    assert state.accept_live(at_cutoff, owner_received_at_ns=cutoff_ns) == _SeriesAdmission.LATE
    assert len(state.buckets[17 * MINUTE_NS].slots) == 1
    assert state.counters["late_constituents"] == 1


def test_off_grid_constituent_is_rejected_before_bucket_or_sequence_mutation() -> None:
    state = _state()
    malformed = replace(
        _constituent(16 * MINUTE_NS),
        interval_start_ns=16 * MINUTE_NS + 1,
        interval_end_ns=16 * MINUTE_NS + 5 * SECOND_NS + 1,
    )

    assert state.accept_live(
        malformed,
        owner_received_at_ns=16 * MINUTE_NS + 6 * SECOND_NS,
    ) == _SeriesAdmission.CONFLICT
    assert state.buckets == {}
    assert state.sequence == 0
    assert tuple(state.retained) == ()
    assert state.counters["interval_rejected"] == 1


def test_candidate_batch_validation_is_atomic_before_sequence_and_retention() -> None:
    state = _state()
    context = state.calendar_context(_historical_observation(0).interval_end_ns)
    assert context is not None
    first = _candidate_from_historical(_historical_observation(0), context=context)
    malformed = replace(
        first,
        interval_start_ns=first.interval_start_ns + MINUTE_NS,
        interval_end_ns=first.interval_end_ns + MINUTE_NS,
        received_constituent_count=11,
    )

    with pytest.raises(ValueError, match="missing subinterval count"):
        state._publish_candidates([first, malformed], published_ts_ns=5 * MINUTE_NS)

    assert state.sequence == 0
    assert tuple(state.retained) == ()
    assert state.counters["published"] == 0


def test_live_provider_revision_is_rejected_before_canonical_normalization() -> None:
    revised = SimpleNamespace(is_revision=True)

    with pytest.raises(ValueError, match="revisions are rejected"):
        _constituent_from_native_bar(
            revised,
            input_identity=_input_identity("LIVE"),
            owner_received_at_ns=2 * MINUTE_NS,
        )


def test_timer_lateness_does_not_extend_cutoff_or_admit_late_mutation() -> None:
    state = _state(count=1)
    historical = state.accept_historical(_historical_result(count=1), published_ts_ns=3 * MINUTE_NS)
    assert historical == ()
    start_ns = 2 * MINUTE_NS
    first = _constituent(start_ns, suffix="first")
    cutoff_ns = 3 * MINUTE_NS + SECOND_NS
    assert state.accept_live(first, owner_received_at_ns=cutoff_ns - 1) == _SeriesAdmission.ACCEPTED

    published = state.finalize_live(3 * MINUTE_NS, now_ns=cutoff_ns + 9 * SECOND_NS)
    retained_before = tuple(state.retained)
    late = _constituent(start_ns + 5 * SECOND_NS, suffix="late")

    assert len(published) == 2
    assert published[-1].completion_state is BarCompletionState.PARTIAL
    assert state.accept_live(late, owner_received_at_ns=cutoff_ns + 1) == _SeriesAdmission.LATE
    assert tuple(state.retained) == retained_before
    assert state.sequence == 2


def test_multi_interval_timer_lateness_skips_in_constant_work_and_schedules_future() -> None:
    next_end_ns, skipped = _next_cutoff_interval_end(
        interval_end_ns=3 * MINUTE_NS,
        interval_ns=MINUTE_NS,
        grace_ns=SECOND_NS,
        now_ns=6 * MINUTE_NS + SECOND_NS,
    )

    assert skipped == 3
    assert next_end_ns == 7 * MINUTE_NS
    assert next_end_ns + SECOND_NS > 6 * MINUTE_NS + SECOND_NS


def test_partial_minute_has_exact_missing_slots_and_zero_minute_has_no_bar() -> None:
    state = _state(count=1)
    state.accept_historical(_historical_result(count=1), published_ts_ns=3 * MINUTE_NS)
    start_ns = 2 * MINUTE_NS
    assert state.accept_live(
        _constituent(start_ns, suffix="only"),
        owner_received_at_ns=start_ns + 5 * SECOND_NS + 1,
    ) == _SeriesAdmission.ACCEPTED

    partial = state.finalize_live(3 * MINUTE_NS, now_ns=3 * MINUTE_NS + SECOND_NS)
    empty = state.finalize_live(4 * MINUTE_NS, now_ns=4 * MINUTE_NS + SECOND_NS)

    assert len(partial) == 2
    assert partial[-1].received_constituent_count == 1
    assert partial[-1].missing_subintervals == tuple(
        (start, start + 5 * SECOND_NS)
        for start in range(start_ns + 5 * SECOND_NS, 3 * MINUTE_NS, 5 * SECOND_NS)
    )
    assert partial[-1].health is MetricHealth.DEGRADED
    assert empty == ()
    assert state.counters["empty_intervals"] == 1


def test_zero_interval_health_gap_does_not_stop_later_complete_publication() -> None:
    state = _state(count=1)
    state.accept_historical(_historical_result(count=1), published_ts_ns=3 * MINUTE_NS)
    start_ns = 2 * MINUTE_NS
    _fill_live_minute(state, start_ns)
    first = state.finalize_live(3 * MINUTE_NS, now_ns=3 * MINUTE_NS + SECOND_NS)
    assert len(first) == 2
    assert state.finalize_live(
        4 * MINUTE_NS,
        now_ns=4 * MINUTE_NS + SECOND_NS,
    ) == ()
    _fill_live_minute(state, 4 * MINUTE_NS)

    recovered = state.finalize_live(
        5 * MINUTE_NS,
        now_ns=5 * MINUTE_NS + SECOND_NS,
    )

    assert len(recovered) == 1
    assert recovered[0].completion_state is BarCompletionState.COMPLETE
    assert not state.terminal
    assert state.counters["publication_gaps"] == 1


def test_partial_historical_gap_remains_data_state_not_terminal_integrity_failure() -> None:
    state = _state()
    config = _config()
    result = _validate_historical_batch(
        config.historical_bootstrap.validation_request,
        tuple(_historical_observation(index) for index in range(15) if index != 7),
    )

    published = state.accept_historical(result, published_ts_ns=17 * MINUTE_NS)

    assert result.disposition.value == "PARTIAL"
    assert len(published) == 13
    assert state.overlap_hold is not None
    assert state.counters["publication_gaps"] == 1
    assert not state.terminal


def test_fifteen_history_plus_five_live_produces_twenty_unique_contiguous_bars() -> None:
    state = _state()
    history = state.accept_historical(_historical_result(), published_ts_ns=17 * MINUTE_NS)
    assert len(history) == 14
    published = list(history)
    for minute in range(16, 21):
        start_ns = minute * MINUTE_NS
        _fill_live_minute(state, start_ns)
        published.extend(
            state.finalize_live(
                start_ns + MINUTE_NS,
                now_ns=start_ns + MINUTE_NS + SECOND_NS,
            ),
        )

    assert len(published) == 20
    assert [item.publication_sequence for item in published] == list(range(1, 21))
    assert all(item.completion_state is BarCompletionState.COMPLETE for item in published)
    assert all(
        previous.interval_end_ns == current.interval_start_ns
        for previous, current in zip(published, published[1:], strict=False)
    )
    assert len(state.retained) == 16


def test_live_first_buffers_two_bars_then_converges_in_canonical_order() -> None:
    state = _state()
    for minute in (16, 17):
        start_ns = minute * MINUTE_NS
        _fill_live_minute(state, start_ns)
        assert state.finalize_live(
            start_ns + MINUTE_NS,
            now_ns=start_ns + MINUTE_NS + SECOND_NS,
        ) == ()

    published = state.accept_historical(_historical_result(), published_ts_ns=19 * MINUTE_NS)

    assert len(published) == 17
    assert [item.publication_sequence for item in published] == list(range(1, 18))
    assert published[-2].interval_start_ns == 16 * MINUTE_NS
    assert published[-1].interval_start_ns == 17 * MINUTE_NS
    assert state.converged


def test_equal_history_live_overlap_merges_both_input_lineages_once() -> None:
    state = _state()
    overlap_start_ns = 15 * MINUTE_NS
    _fill_live_minute(state, overlap_start_ns, price=Decimal("114"))
    assert state.finalize_live(
        16 * MINUTE_NS,
        now_ns=16 * MINUTE_NS + SECOND_NS,
    ) == ()
    refreshed_projection = replace(
        _projection_response().projections[0],
        coverage_end_ns=61 * MINUTE_NS,
    )
    assert state.accept_projection(
        replace(
            _projection_response(),
            request_id="projection-2",
            projections=(refreshed_projection,),
            generated_ts_ns=3 * SECOND_NS,
        ),
    )

    published = state.accept_historical(_historical_result(), published_ts_ns=17 * MINUTE_NS)

    assert len(published) == 15
    overlap = published[-1]
    assert overlap.interval_start_ns == overlap_start_ns
    assert {item.source_class for item in overlap.lineage} == {"HISTORICAL", "LIVE"}
    assert {item.input_identity for item in overlap.lineage} == {
        _input_identity("HISTORICAL"),
        _input_identity("LIVE"),
    }
    assert overlap.projection_evidence_refs == (
        "calendar-projection:projection-1",
        "calendar-projection:projection-2",
    )
    assert state.counters["overlap_duplicates"] == 1


def test_history_first_overlap_holds_one_boundary_and_merges_live_lineage() -> None:
    state = _state()
    history = state.accept_historical(_historical_result(), published_ts_ns=17 * MINUTE_NS)
    assert len(history) == 14
    assert state.overlap_hold is not None
    overlap_start_ns = 15 * MINUTE_NS
    _fill_live_minute(state, overlap_start_ns, price=Decimal("114"))

    overlap = state.finalize_live(
        16 * MINUTE_NS,
        now_ns=16 * MINUTE_NS + SECOND_NS,
    )

    assert len(overlap) == 1
    assert {item.source_class for item in overlap[0].lineage} == {"HISTORICAL", "LIVE"}
    assert state.overlap_hold is None
    assert state.converged


def test_unequal_history_live_overlap_is_terminal_integrity_conflict() -> None:
    state = _state()
    overlap_start_ns = 15 * MINUTE_NS
    for slot in range(12):
        value = _constituent(
            overlap_start_ns + slot * 5 * SECOND_NS,
            suffix=str(slot),
            price=Decimal("999"),
        )
        state.accept_live(value, owner_received_at_ns=value.interval_end_ns + 1)
    state.finalize_live(16 * MINUTE_NS, now_ns=16 * MINUTE_NS + SECOND_NS)

    published = state.accept_historical(_historical_result(), published_ts_ns=17 * MINUTE_NS)

    assert len(published) == 14
    assert state.terminal
    assert state.counters["overlap_conflicts"] == 1


def test_two_history_live_overlaps_exceed_exact_one_bar_bound() -> None:
    state = _state()
    for minute, price in ((14, Decimal("113")), (15, Decimal("114"))):
        start_ns = minute * MINUTE_NS
        _fill_live_minute(state, start_ns, price=price)
        assert state.finalize_live(
            start_ns + MINUTE_NS,
            now_ns=start_ns + MINUTE_NS + SECOND_NS,
        ) == ()

    assert state.accept_historical(
        _historical_result(),
        published_ts_ns=17 * MINUTE_NS,
    ) == ()
    assert state.terminal
    assert state.counters["overlap_overflow"] == 1


def test_evicted_observation_is_rejected_as_stale_without_sequence_mutation() -> None:
    state = _state()
    history = state.accept_historical(_historical_result(), published_ts_ns=17 * MINUTE_NS)
    for minute in (16, 17):
        start_ns = minute * MINUTE_NS
        _fill_live_minute(state, start_ns)
        state.finalize_live(
            start_ns + MINUTE_NS,
            now_ns=start_ns + MINUTE_NS + SECOND_NS,
        )
    sequence_before = state.sequence
    context = state.calendar_context(_historical_observation(0).interval_end_ns)
    assert context is not None
    evicted = _candidate_from_historical(_historical_observation(0), context=context)

    assert state._publish_candidates([evicted], published_ts_ns=20 * MINUTE_NS) == ()
    assert len(history) == 14
    assert state.sequence == sequence_before
    assert state.counters["stale"] == 1


def test_third_live_bar_before_history_is_terminal_bounded_overflow() -> None:
    state = _state()
    for minute in (16, 17):
        start_ns = minute * MINUTE_NS
        _fill_live_minute(state, start_ns)
        state.finalize_live(
            start_ns + MINUTE_NS,
            now_ns=start_ns + MINUTE_NS + SECOND_NS,
        )
    start_ns = 18 * MINUTE_NS
    _fill_live_minute(state, start_ns)

    assert state.finalize_live(
        19 * MINUTE_NS,
        now_ns=19 * MINUTE_NS + SECOND_NS,
    ) == ()
    assert state.terminal
    assert state.counters["pending_live_overflow"] == 1


def test_per_series_open_bucket_bound_rejects_third_unfinished_minute() -> None:
    state = _state()
    for minute in (16, 17):
        value = _constituent(minute * MINUTE_NS, suffix=str(minute))
        assert state.accept_live(value, owner_received_at_ns=value.interval_end_ns + 1) == (
            _SeriesAdmission.ACCEPTED
        )
    third = _constituent(18 * MINUTE_NS, suffix="overflow")

    assert state.accept_live(third, owner_received_at_ns=third.interval_end_ns + 1) == (
        _SeriesAdmission.OVERFLOW
    )
    assert len(state.buckets) == 2
    assert state.counters["bucket_overflow"] == 1


def test_instance_open_bucket_bound_stops_only_series_crossing_ceiling() -> None:
    first_config = _config(series_id="es_1m_a")
    second_config = _config(
        series_id="es_1m_b",
        instrument_id="NQU6.CME",
        request_id="history-es-1m-002",
    )
    policy = _CompletedBarFoundationPolicy(
        maximum_open_buckets_per_series=2,
        maximum_open_buckets_per_instance=2,
    )
    actor = _CompletedBarFoundationActor(
        _CompletedBarFoundationActorConfig(
            series=(first_config, second_config),
            startup_epoch=STARTUP_EPOCH,
            run_epoch=RUN_EPOCH,
            manifest_digest=MANIFEST_DIGEST,
            policy=policy,
        ),
    )
    first = actor.states["es_1m_a"]
    second = actor.states["es_1m_b"]
    for minute in (16, 17):
        value = _constituent(minute * MINUTE_NS, suffix=str(minute))
        assert actor._accept_live_constituent(
            first,
            value,
            owner_received_at_ns=value.interval_end_ns + 1,
        ) == _SeriesAdmission.ACCEPTED
    overflow = _constituent(
        18 * MINUTE_NS,
        suffix="aggregate",
        input_identity=second_config.live_input_identity,
    )

    assert actor._accept_live_constituent(
        second,
        overflow,
        owner_received_at_ns=overflow.interval_end_ns + 1,
    ) == _SeriesAdmission.OVERFLOW
    assert not first.terminal
    assert second.terminal
    assert second.counters["instance_bucket_overflow"] == 1


def test_equal_constituent_duplicate_drops_and_unequal_duplicate_stops_only_series() -> None:
    first = _state()
    second = _state()
    start_ns = 16 * MINUTE_NS
    value = _constituent(start_ns)

    assert first.accept_live(value, owner_received_at_ns=start_ns + 6 * SECOND_NS) == (
        _SeriesAdmission.ACCEPTED
    )
    assert first.accept_live(value, owner_received_at_ns=start_ns + 7 * SECOND_NS) == (
        _SeriesAdmission.DUPLICATE
    )
    conflict = replace(value, close=Decimal("101"), high=Decimal("102"))
    assert first.accept_live(conflict, owner_received_at_ns=start_ns + 8 * SECOND_NS) == (
        _SeriesAdmission.CONFLICT
    )

    assert first.terminal
    assert not second.terminal
    assert second.accept_live(value, owner_received_at_ns=start_ns + 6 * SECOND_NS) == (
        _SeriesAdmission.ACCEPTED
    )


def test_historical_source_class_is_rejected_from_live_admission() -> None:
    state = _state()
    value = _constituent(16 * MINUTE_NS)
    contradictory = replace(
        value,
        lineage=replace(value.lineage, source_class="HISTORICAL"),
    )

    assert state.accept_live(
        contradictory,
        owner_received_at_ns=16 * MINUTE_NS + 6 * SECOND_NS,
    ) == _SeriesAdmission.CONFLICT
    assert state.buckets == {}
    assert state.counters["identity_rejected"] == 1


def test_calendar_definition_mismatch_rejects_projection_without_replacing_current() -> None:
    state = _state()
    current = state.projection
    wrong_projection = replace(
        _projection_response().projections[0],
        definition_digest="d" * 64,
    )
    response = replace(_projection_response(), projections=(wrong_projection,))

    assert not state.accept_projection(response)
    assert state.projection is current


def test_projection_addressed_to_unrelated_requester_is_rejected() -> None:
    state = _state()
    current = state.projection

    assert not state.accept_projection(
        replace(_projection_response(), requester="UNRELATED-ACTOR"),
    )
    assert state.projection is current
    assert state.counters["projection_rejected"] == 1


def test_compatible_projection_refresh_replaces_bounded_view() -> None:
    state = _state()
    refreshed_projection = replace(
        _projection_response().projections[0],
        coverage_end_ns=61 * MINUTE_NS,
    )
    refreshed = replace(
        _projection_response(),
        request_id="projection-2",
        projections=(refreshed_projection,),
        generated_ts_ns=3 * SECOND_NS,
    )

    assert state.accept_projection(refreshed)
    assert state.projection is not None
    assert state.projection.projection.coverage_end_ns == 61 * MINUTE_NS
    assert state.projection_ref == "calendar-projection:projection-2"


def test_v3_02_current_state_is_identity_checked_and_cited_without_mcal() -> None:
    state = _state()

    assert state.install_current_state(_current_state_response().states[0])
    context = state.calendar_context(2 * MINUTE_NS)
    assert context is not None
    assert context.state_evidence_refs == ("calendar-current-state:transition-1",)
    wrong_state = replace(_current_state_response().states[0], source_epoch="wrong-run")
    assert not state.install_current_state(wrong_state)
    assert state.current_state == _current_state_response().states[0]


def test_stop_clears_transient_state_and_rejects_post_stop_work() -> None:
    state = _state()
    value = _constituent(16 * MINUTE_NS)
    state.accept_live(value, owner_received_at_ns=16 * MINUTE_NS + 6 * SECOND_NS)

    state.stop()

    assert state.buckets == {}
    assert state.pending_live == []
    assert state.accept_live(value, owner_received_at_ns=16 * MINUTE_NS + 7 * SECOND_NS) == (
        _SeriesAdmission.TERMINAL
    )
    assert state.finalize_live(17 * MINUTE_NS, now_ns=17 * MINUTE_NS + SECOND_NS) == ()


class _CalendarResponderConfig(DataActorConfig):
    def __new__(
        cls,
        actor_id: str | ActorId = "CALENDAR-RESPONDER",
    ) -> _CalendarResponderConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        return super().__new__(cls, actor_id=resolved)


class _CalendarResponder(DataActor):
    def on_start(self) -> None:
        self._projection_request_type = DataType(CALENDAR_PROJECTION_REQUEST_TYPE_NAME)
        self._projection_response_type = DataType(CALENDAR_PROJECTION_RESPONSE_TYPE_NAME)
        self._snapshot_request_type = DataType(CALENDAR_STATE_SNAPSHOT_REQUEST_TYPE_NAME)
        self._snapshot_response_type = DataType(CALENDAR_STATE_SNAPSHOT_RESPONSE_TYPE_NAME)
        self.subscribe_data(self._projection_request_type)
        self.subscribe_data(self._snapshot_request_type)

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, CalendarProjectionRequest):
            _CALENDAR_REQUESTS["projection"].append(payload)
            self.clock.set_time_alert_ns(
                f"calendar-responder-projection:{payload.request_id}",
                self.clock.timestamp_ns() + 1_000_000,
                callback=partial(self._respond_projection, payload),
            )
        elif isinstance(payload, CalendarStateSnapshotRequest):
            _CALENDAR_REQUESTS["snapshot"].append(payload)
            self.clock.set_time_alert_ns(
                f"calendar-responder-snapshot:{payload.request_id}",
                self.clock.timestamp_ns() + 1_000_000,
                callback=partial(self._respond_snapshot, payload),
            )

    def on_stop(self) -> None:
        self.unsubscribe_data(self._projection_request_type)
        self.unsubscribe_data(self._snapshot_request_type)

    def _respond_projection(
        self,
        request: CalendarProjectionRequest,
        _event: object,
    ) -> None:
        response = self._projection_response(request)
        unrelated = replace(response, requester="UNRELATED-ACTOR")
        self.publish_data(
            self._projection_response_type,
            CustomData(self._projection_response_type, unrelated),
        )
        self.publish_data(
            self._projection_response_type,
            CustomData(self._projection_response_type, response),
        )

    def _respond_snapshot(
        self,
        request: CalendarStateSnapshotRequest,
        _event: object,
    ) -> None:
        response = self._snapshot_response(request)
        stale = replace(response, request_id=f"stale:{request.request_id}")
        self.publish_data(
            self._snapshot_response_type,
            CustomData(self._snapshot_response_type, stale),
        )
        self.publish_data(
            self._snapshot_response_type,
            CustomData(self._snapshot_response_type, response),
        )

    def _projection_response(
        self,
        request: CalendarProjectionRequest,
    ) -> CalendarProjectionResponse:
        projection = CalendarProjection(
            calendar_id="cme_equity",
            calendar_engine="pandas_market_calendars",
            provider_calendar="CME_Equity",
            schedule_version="test-v1",
            definition_version=4,
            definition_digest=CALENDAR_DIGEST,
            definition_effective_from_ns=SECOND_NS,
            calendar_engine_version="5.1",
            exchange_timezone="America/Chicago",
            coverage_start_ns=request.start_ns,
            coverage_end_ns=request.end_ns,
            exchange_segments=(
                ExchangeSessionSegment(
                    trade_date=date(2026, 9, 2),
                    market_state="OPEN",
                    start_ns=request.start_ns,
                    end_ns=request.end_ns,
                ),
            ),
            phase_windows=(
                SessionWindow(
                    trade_date=date(2026, 9, 2),
                    phase="GLOBEX",
                    start_ns=request.start_ns,
                    end_ns=request.end_ns,
                ),
            ),
            correction_outcomes=(),
            normalization_outcomes=(),
        )
        return CalendarProjectionResponse(
            request_id=request.request_id,
            requester=request.requester,
            source="SESSION-STATE",
            source_epoch=str(RUN_EPOCH),
            status="READY",
            requested_calendar_ids=request.calendar_ids,
            projections=(projection,),
            unavailable_calendar_ids=(),
            failures=(),
            generated_ts_ns=self.clock.timestamp_ns(),
        )

    def _snapshot_response(
        self,
        request: CalendarStateSnapshotRequest,
    ) -> CalendarStateSnapshotResponse:
        observed_ns = self._snapshot_observed_ns(request)
        state_effective_ns = max(SECOND_NS, observed_ns - MINUTE_NS)
        next_transition_ns = observed_ns + 60 * MINUTE_NS
        current = CalendarCurrentState(
            calendar_id="cme_equity",
            schedule_version="test-v1",
            definition_version=4,
            definition_digest=CALENDAR_DIGEST,
            definition_effective_from_ns=SECOND_NS,
            trade_date=date(2026, 9, 2).isoformat(),
            phase_memberships=("GLOBEX",),
            market_state="OPEN",
            segment_open_ns=state_effective_ns,
            segment_close_ns=next_transition_ns,
            next_transition_ns=next_transition_ns,
            revision=1,
            previous_revision=None,
            last_transition_event_id="transition-1",
            source="SESSION-STATE",
            source_epoch=str(RUN_EPOCH),
            state_effective_from_ns=state_effective_ns,
            state_revision_evaluated_as_of_ns=observed_ns,
            evaluated_as_of_ns=observed_ns,
            state_revision_published_ts_ns=observed_ns,
        )
        return CalendarStateSnapshotResponse(
            cycle_id=request.cycle_id,
            request_id=request.request_id,
            attempt=request.attempt,
            requester=request.requester,
            source="SESSION-STATE",
            source_epoch=str(RUN_EPOCH),
            status="READY",
            requested_calendar_ids=request.calendar_ids,
            states=(current,),
            failures=(),
            requested_as_of_ns=request.requested_as_of_ns,
            requested_ts_ns=request.requested_ts_ns,
            deadline_ts_ns=request.deadline_ts_ns,
            request_received_ts_ns=observed_ns,
            evaluated_as_of_ns=observed_ns,
            generated_ts_ns=observed_ns,
            published_ts_ns=observed_ns,
            delivery_policy_version=request.delivery_policy_version,
        )

    def _snapshot_observed_ns(self, _request: CalendarStateSnapshotRequest) -> int:
        return self.clock.timestamp_ns()


class _InspectableFoundationActor(_CompletedBarFoundationActor):
    def on_data(self, data) -> None:  # noqa: ANN001
        super().on_data(data)
        state = self.states["es_1m"]
        _CALENDAR_PROTOCOL_STATE.update(
            {
                "projection_phase": self._projection_state.phase.value,
                "snapshot_phase": self._session_state.phase.value,
                "projection_stale": self._calendar_counts["projection_stale"],
                "projection_conflicts": self._calendar_counts["projection_conflicts"],
                "snapshot_stale": self._calendar_counts["snapshot_stale"],
                "snapshot_conflicts": self._calendar_counts["snapshot_conflict"],
                "projection_request_id": state.projection_ref,
                "current_revision": (
                    None if state.current_state is None else state.current_state.revision
                ),
            },
        )
        if state.projection is not None and state.current_state is not None:
            _CALENDAR_READY.set()


async def _run_calendar_fixture(node: LiveNode) -> None:
    handle = node.handle()
    run_task = asyncio.create_task(node.run_async())
    try:
        assert await asyncio.to_thread(_CALENDAR_READY.wait, 2), (
            _CALENDAR_REQUESTS,
            _CALENDAR_PROTOCOL_STATE,
        )
    finally:
        handle.stop()
        await run_task


def test_actual_foundation_owns_and_correlates_both_calendar_delivery_cycles() -> None:
    _CALENDAR_READY.clear()
    _CALENDAR_PROTOCOL_STATE.clear()
    _CALENDAR_REQUESTS["projection"].clear()
    _CALENDAR_REQUESTS["snapshot"].clear()
    node = LiveNode.builder(
        "MARKEITECH-V3-03-FOUNDATION-CALENDAR",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
    module = "tests.intelligence.test_completed_bar_foundation"
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=f"{module}:_CalendarResponder",
            config_path=f"{module}:_CalendarResponderConfig",
            config={"actor_id": "CALENDAR-RESPONDER"},
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=f"{module}:_InspectableFoundationActor",
            config_path=f"{module}:_RoutingFoundationConfig",
            config={"actor_id": "COMPLETED-BARS-1"},
        ),
    )

    asyncio.run(_run_calendar_fixture(node))

    projection_request = _CALENDAR_REQUESTS["projection"][0]
    snapshot_request = _CALENDAR_REQUESTS["snapshot"][0]
    assert isinstance(projection_request, CalendarProjectionRequest)
    assert projection_request.requester == "COMPLETED-BARS-1"
    assert projection_request.calendar_ids == ("cme_equity",)
    assert isinstance(snapshot_request, CalendarStateSnapshotRequest)
    assert snapshot_request.requester == "COMPLETED-BARS-1"
    assert snapshot_request.expected_source == "SESSION-STATE"
    assert snapshot_request.expected_source_epoch == str(RUN_EPOCH)
    assert snapshot_request.attempt == 1
    assert _CALENDAR_PROTOCOL_STATE == {
        "projection_phase": "READY",
        "snapshot_phase": "LIVE",
        "projection_stale": 1,
        "projection_conflicts": 0,
        "snapshot_stale": 1,
        "snapshot_conflicts": 0,
        "projection_request_id": f"calendar-projection:{projection_request.request_id}",
        "current_revision": 1,
    }


class _RefreshProjectionResponder(_CalendarResponder):
    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if not isinstance(payload, CalendarProjectionRequest):
            super().on_data(data)
            return
        _CALENDAR_REQUESTS["projection"].append(payload)
        self.clock.set_time_alert_ns(
            f"calendar-responder-projection:{payload.request_id}",
            self.clock.timestamp_ns() + 10_000_000,
            callback=partial(self._respond_projection, payload),
        )

    def _respond_projection(
        self,
        request: CalendarProjectionRequest,
        event: object,
    ) -> None:
        if len(_CALENDAR_REQUESTS["projection"]) == 1:
            observed_ns = self.clock.timestamp_ns()
            transition_type = DataType(CALENDAR_TRANSITION_V2_TYPE_NAME)
            transition = CalendarTransitionV2(
                event_id="transition-refresh-2",
                source="SESSION-STATE",
                source_epoch=str(RUN_EPOCH),
                calendar_id="cme_equity",
                schedule_version="test-v1",
                definition_version=4,
                definition_digest=CALENDAR_DIGEST,
                definition_effective_from_ns=SECOND_NS,
                trade_date=date(2026, 9, 2).isoformat(),
                previous_trade_date=date(2026, 9, 2).isoformat(),
                phase_memberships=("GLOBEX",),
                previous_phase_memberships=("GLOBEX",),
                market_state="OPEN",
                previous_market_state="OPEN",
                segment_open_ns=observed_ns - MINUTE_NS,
                segment_close_ns=observed_ns + 60 * MINUTE_NS,
                next_transition_ns=observed_ns + 60 * MINUTE_NS,
                state_effective_from_ns=observed_ns,
                evaluated_as_of_ns=observed_ns,
                published_ts_ns=observed_ns,
                revision=2,
                previous_revision=1,
                reason="refresh while projection request is waiting",
            )
            self.publish_data(
                transition_type,
                CustomData(transition_type, transition),
            )
        super()._respond_projection(request, event)


class _RefreshInspectableFoundationActor(_CompletedBarFoundationActor):
    def on_data(self, data) -> None:  # noqa: ANN001
        super().on_data(data)
        if (
            len(_CALENDAR_REQUESTS["projection"]) == 2
            and self._projection_state.phase is ProjectionRequestPhase.READY
        ):
            _CALENDAR_PROTOCOL_STATE.update(
                {
                    "projection_requests": self._calendar_counts["projection_requests"],
                    "projection_generation": self._projection_state.generation,
                    "refresh_pending": dict(self._calendar_refresh_generation),
                    "current_revision": self.states["es_1m"].current_state.revision,
                },
            )
            _PROJECTION_REFRESH_READY.set()


async def _run_projection_refresh_fixture(node: LiveNode) -> None:
    handle = node.handle()
    run_task = asyncio.create_task(node.run_async())
    try:
        assert await asyncio.to_thread(_PROJECTION_REFRESH_READY.wait, 2), (
            _CALENDAR_REQUESTS,
            _CALENDAR_PROTOCOL_STATE,
        )
    finally:
        handle.stop()
        await run_task


def test_transition_during_waiting_defers_exactly_one_fresh_projection_cycle() -> None:
    _PROJECTION_REFRESH_READY.clear()
    _CALENDAR_PROTOCOL_STATE.clear()
    _CALENDAR_REQUESTS["projection"].clear()
    _CALENDAR_REQUESTS["snapshot"].clear()
    node = LiveNode.builder(
        "MARKEITECH-V3-03-FOUNDATION-PROJECTION-REFRESH",
        TraderId.from_str("MARKEITECH-REFRESH-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
    module = "tests.intelligence.test_completed_bar_foundation"
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=f"{module}:_RefreshProjectionResponder",
            config_path=f"{module}:_CalendarResponderConfig",
            config={"actor_id": "CALENDAR-RESPONDER"},
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=f"{module}:_RefreshInspectableFoundationActor",
            config_path=f"{module}:_RoutingFoundationConfig",
            config={"actor_id": "COMPLETED-BARS-1"},
        ),
    )

    asyncio.run(_run_projection_refresh_fixture(node))

    requests = _CALENDAR_REQUESTS["projection"]
    assert len(requests) == 2
    assert requests[0].request_id != requests[1].request_id
    assert _CALENDAR_PROTOCOL_STATE == {
        "projection_requests": 2,
        "projection_generation": 2,
        "refresh_pending": {},
        "current_revision": 2,
    }


class _GapCalendarResponder(_CalendarResponder):
    def __init__(self, config: _CalendarResponderConfig) -> None:
        super().__init__(config)
        self._gap_sent = False

    def _respond_snapshot(
        self,
        request: CalendarStateSnapshotRequest,
        event: object,
    ) -> None:
        super()._respond_snapshot(request, event)
        if self._gap_sent:
            return
        self._gap_sent = True
        self.clock.set_time_alert_ns(
            "calendar-responder-revision-gap",
            self.clock.timestamp_ns() + 1_000_000,
            callback=self._publish_revision_gap,
        )

    def _publish_revision_gap(self, _event: object) -> None:
        observed_ns = self.clock.timestamp_ns()
        transition_type = DataType(CALENDAR_TRANSITION_V2_TYPE_NAME)
        transition = CalendarTransitionV2(
            event_id="transition-gap-3",
            source="SESSION-STATE",
            source_epoch=str(RUN_EPOCH),
            calendar_id="cme_equity",
            schedule_version="test-v1",
            definition_version=4,
            definition_digest=CALENDAR_DIGEST,
            definition_effective_from_ns=SECOND_NS,
            trade_date=date(2026, 9, 2).isoformat(),
            previous_trade_date=date(2026, 9, 2).isoformat(),
            phase_memberships=("GLOBEX",),
            previous_phase_memberships=("GLOBEX",),
            market_state="OPEN",
            previous_market_state="OPEN",
            segment_open_ns=observed_ns - MINUTE_NS,
            segment_close_ns=observed_ns + 60 * MINUTE_NS,
            next_transition_ns=observed_ns + 60 * MINUTE_NS,
            state_effective_from_ns=observed_ns,
            evaluated_as_of_ns=observed_ns,
            published_ts_ns=observed_ns,
            revision=3,
            previous_revision=2,
            reason="revision gap fixture",
        )
        self.publish_data(
            transition_type,
            CustomData(transition_type, transition),
        )


class _GapInspectableFoundationActor(_CompletedBarFoundationActor):
    def on_data(self, data) -> None:  # noqa: ANN001
        super().on_data(data)
        if (
            len(_CALENDAR_REQUESTS["snapshot"]) >= 2
            and self._session_state.phase.value == "LIVE"
            and self._calendar_counts["transition_gap"] == 1
        ):
            _CALENDAR_PROTOCOL_STATE.update(
                {
                    "snapshot_phase": self._session_state.phase.value,
                    "transition_gap": self._calendar_counts["transition_gap"],
                    "snapshot_requests": self._calendar_counts["snapshot_requests"],
                    "current_revision": self.states["es_1m"].current_state.revision,
                },
            )
            _REVISION_GAP_RECOVERED.set()


async def _run_revision_gap_fixture(node: LiveNode) -> None:
    handle = node.handle()
    run_task = asyncio.create_task(node.run_async())
    try:
        assert await asyncio.to_thread(_REVISION_GAP_RECOVERED.wait, 2)
    finally:
        handle.stop()
        await run_task


def test_actual_foundation_resynchronizes_a_transition_revision_gap() -> None:
    _REVISION_GAP_RECOVERED.clear()
    _CALENDAR_PROTOCOL_STATE.clear()
    _CALENDAR_REQUESTS["projection"].clear()
    _CALENDAR_REQUESTS["snapshot"].clear()
    node = LiveNode.builder(
        "MARKEITECH-V3-03-FOUNDATION-REVISION-GAP",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
    module = "tests.intelligence.test_completed_bar_foundation"
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=f"{module}:_GapCalendarResponder",
            config_path=f"{module}:_CalendarResponderConfig",
            config={"actor_id": "CALENDAR-RESPONDER"},
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=f"{module}:_GapInspectableFoundationActor",
            config_path=f"{module}:_RoutingFoundationConfig",
            config={"actor_id": "COMPLETED-BARS-1"},
        ),
    )

    asyncio.run(_run_revision_gap_fixture(node))

    first, second = _CALENDAR_REQUESTS["snapshot"]
    assert isinstance(first, CalendarStateSnapshotRequest)
    assert isinstance(second, CalendarStateSnapshotRequest)
    assert first.cycle_id != second.cycle_id
    assert first.attempt == second.attempt == 1
    assert _CALENDAR_PROTOCOL_STATE == {
        "snapshot_phase": "LIVE",
        "transition_gap": 1,
        "snapshot_requests": 2,
        "current_revision": 1,
    }


class _RoutingFoundationConfig(_CompletedBarFoundationActorConfig):
    def __new__(
        cls,
        actor_id: str | ActorId = "COMPLETED-BARS-1",
    ) -> _RoutingFoundationConfig:
        return super().__new__(
            cls,
            series=(_config(),),
            startup_epoch=STARTUP_EPOCH,
            run_epoch=RUN_EPOCH,
            manifest_digest=MANIFEST_DIGEST,
            actor_id=actor_id,
        )


class _ShortRetryFoundationConfig(_CompletedBarFoundationActorConfig):
    def __new__(
        cls,
        actor_id: str | ActorId = "COMPLETED-BARS-1",
    ) -> _ShortRetryFoundationConfig:
        return super().__new__(
            cls,
            series=(_config(),),
            startup_epoch=STARTUP_EPOCH,
            run_epoch=RUN_EPOCH,
            manifest_digest=MANIFEST_DIGEST,
            projection_retry={
                "response_timeout_ms": 10,
                "maximum_attempts": 2,
                "retry_backoff_ms": 5,
                "maximum_elapsed_ms": 100,
            },
            current_state_delivery={
                "policy_version": 1,
                "response_timeout_ms": 10,
                "maximum_attempts": 2,
                "retry_backoff_ms": 5,
                "maximum_elapsed_ms": 100,
                "maximum_buffered_transitions_per_calendar": 8,
                "maximum_total_buffered_transitions": 32,
                "boundary_delivery_grace_ms": 2,
            },
            actor_id=actor_id,
        )


class _RetryInspectableFoundationActor(_CompletedBarFoundationActor):
    def on_stop(self) -> None:
        super().on_stop()
        _LIFECYCLE_COUNTS.update(
            {
                "projection_phase": self._projection_state.phase.value,
                "snapshot_phase": self._session_state.phase.value,
                "actor_counters": dict(self._calendar_counts),
                "active": self._active,
                "terminal": self._terminal,
                "remaining_foundation_timers": tuple(
                    name
                    for name in self.clock.timer_names()
                    if name.startswith("completed-bar-")
                ),
            },
        )


async def _run_retry_fixture(node: LiveNode) -> None:
    handle = node.handle()
    run_task = asyncio.create_task(node.run_async())
    try:
        await asyncio.sleep(0.12)
    finally:
        handle.stop()
        await run_task


def test_actual_foundation_calendar_delivery_retries_are_bounded_and_stop_absorbs() -> None:
    _LIFECYCLE_COUNTS.clear()
    node = LiveNode.builder(
        "MARKEITECH-V3-03-FOUNDATION-CALENDAR-RETRY",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
    module = "tests.intelligence.test_completed_bar_foundation"
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=f"{module}:_RetryInspectableFoundationActor",
            config_path=f"{module}:_ShortRetryFoundationConfig",
            config={"actor_id": "COMPLETED-BARS-1"},
        ),
    )

    asyncio.run(_run_retry_fixture(node))

    counters = _LIFECYCLE_COUNTS["actor_counters"]
    assert isinstance(counters, dict)
    assert counters["projection_requests"] == 2
    assert counters["projection_timeouts"] == 2
    assert counters["projection_retries"] == 1
    assert counters["projection_terminal"] == 1
    assert counters["snapshot_requests"] == 2
    assert counters["snapshot_retry_scheduled"] == 1
    assert counters["snapshot_retry_started"] == 1
    assert counters["snapshot_exhausted"] == 1
    assert _LIFECYCLE_COUNTS["projection_phase"] == "STOPPED"
    assert _LIFECYCLE_COUNTS["snapshot_phase"] == "STOPPED"
    assert _LIFECYCLE_COUNTS["remaining_foundation_timers"] == ()
    assert _LIFECYCLE_COUNTS["active"] is False
    assert _LIFECYCLE_COUNTS["terminal"] is True


class _ControllableNativeClock:
    """Drive the pinned Nautilus test clock and expose scheduled callbacks deterministically."""

    def __init__(self, now_ns: int) -> None:
        self._clock = Clock.new_test()
        self._clock.set_time(now_ns)
        self._callbacks: dict[str, object] = {}
        self.fired: list[tuple[str, int]] = []

    def timestamp_ns(self) -> int:
        return self._clock.timestamp_ns()

    def set_time(self, now_ns: int) -> None:
        self._clock.set_time(now_ns)

    def timer_names(self) -> list[str]:
        return self._clock.timer_names()

    def next_time_ns(self, name: str) -> int | None:
        return self._clock.next_time_ns(name)

    def set_time_alert_ns(self, name: str, alert_time_ns: int, callback) -> None:  # noqa: ANN001
        self._callbacks[name] = callback
        self._clock.set_time_alert_ns(name, alert_time_ns, callback=callback)

    def cancel_timer(self, name: str) -> None:
        self._callbacks.pop(name, None)
        self._clock.cancel_timer(name)

    def fire(self, name: str, *, now_ns: int) -> None:
        alert_ns = self._clock.next_time_ns(name)
        if alert_ns is None or now_ns < alert_ns:
            raise AssertionError("test clock cannot fire an absent or premature alert")
        callback = self._callbacks.pop(name)
        self._clock.cancel_timer(name)
        self._clock.set_time(now_ns)
        self.fired.append((name, now_ns))
        callback(SimpleNamespace(name=name, ts_event=now_ns, ts_init=now_ns))


def _native_live_bar(interval_end_ns: int) -> Bar:
    return Bar(
        BarType.from_str("ESU6.CME-5-SECOND-LAST-EXTERNAL"),
        Price.from_str("100"),
        Price.from_str("101"),
        Price.from_str("99"),
        Price.from_str("100.5"),
        Quantity.from_str("10"),
        interval_end_ns,
        interval_end_ns,
    )


class _LifecycleCalendarResponder(_CalendarResponder):
    def _snapshot_observed_ns(self, request: CalendarStateSnapshotRequest) -> int:
        return request.requested_ts_ns + 1_000_000


class _LifecycleFoundationActor(_CompletedBarFoundationActor):
    def __init__(self, config: _CompletedBarFoundationActorConfig) -> None:
        self._fixture_clock = _ControllableNativeClock(120 * MINUTE_NS)
        super().__init__(config)
        self._lifecycle_injected = False

    @property
    def clock(self) -> _ControllableNativeClock:
        return self._fixture_clock

    def subscribe_data(self, data_type: DataType, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        _LIFECYCLE_CALLS["subscribe_data"].append(data_type)
        super().subscribe_data(data_type, *args, **kwargs)

    def unsubscribe_data(
        self,
        data_type: DataType,
        *args,
        **kwargs,
    ) -> None:  # noqa: ANN002, ANN003
        _LIFECYCLE_CALLS["unsubscribe_data"].append(data_type)
        super().unsubscribe_data(data_type, *args, **kwargs)

    def subscribe_bars(self, bar_type, *, client_id=None, params=None) -> None:  # noqa: ANN001
        _LIFECYCLE_CALLS["subscribe_bars"].append(
            (str(bar_type), str(client_id), params),
        )
        super().subscribe_bars(bar_type, client_id=client_id, params=params)

    def unsubscribe_bars(self, bar_type, *, client_id=None, params=None) -> None:  # noqa: ANN001
        _LIFECYCLE_CALLS["unsubscribe_bars"].append(
            (str(bar_type), str(client_id), params),
        )
        super().unsubscribe_bars(bar_type, client_id=client_id, params=params)

    def on_data(self, data) -> None:  # noqa: ANN001
        super().on_data(data)
        state = self.states["es_1m"]
        if (
            self._lifecycle_injected
            or not state.demand_started
            or state.projection is None
            or state.current_state is None
        ):
            return
        self._lifecycle_injected = True
        state.history_terminal = True
        state.converged = True
        interval_start_ns = 120 * MINUTE_NS
        interval_end_ns = interval_start_ns + MINUTE_NS
        cutoff_ns = interval_end_ns + self._policy.completion_grace_ns
        before = _native_live_bar(interval_start_ns + 5 * SECOND_NS)
        exact = _native_live_bar(interval_start_ns + 10 * SECOND_NS)

        self.clock.set_time(cutoff_ns - 1)
        self.on_bar(before)
        bucket = state.buckets[interval_end_ns]
        _LIFECYCLE_COUNTS["before_cutoff"] = (
            _SeriesAdmission.ACCEPTED if len(bucket.slots) == 1 else "NOT_ADMITTED"
        )

        timer_name = f"completed-bar-cutoff:{state.config.series_id}:{interval_end_ns}"
        _LIFECYCLE_COUNTS["scheduled_cutoff_ns"] = self.clock.next_time_ns(timer_name)
        late_before = state.counters["late_constituents"]
        self.clock.set_time(cutoff_ns)
        self.on_bar(exact)
        _LIFECYCLE_COUNTS["exact_before_timer"] = (
            _SeriesAdmission.LATE
            if state.counters["late_constituents"] == late_before + 1
            else "NOT_LATE"
        )

        self.clock.fire(timer_name, now_ns=cutoff_ns)
        late_before = state.counters["late_constituents"]
        self.on_bar(exact)
        _LIFECYCLE_COUNTS["exact_after_timer"] = (
            _SeriesAdmission.LATE
            if state.counters["late_constituents"] == late_before + 1
            else "NOT_LATE"
        )
        _LIFECYCLE_COUNTS["cutoff_fires"] = tuple(self.clock.fired)

    def on_stop(self) -> None:
        super().on_stop()
        state = self.states["es_1m"]
        _LIFECYCLE_COUNTS.update(
            {
                "active": self._active,
                "terminal": self._terminal,
                "state_terminal": state.terminal,
                "series_counters": dict(state.counters),
                "remaining_foundation_timers": tuple(
                    name
                    for name in self.clock.timer_names()
                    if name.startswith("completed-bar-")
                ),
            },
        )


class _LifecycleProbeConfig(DataActorConfig):
    def __new__(
        cls,
        actor_id: str | ActorId = "LIFECYCLE-PROBE",
    ) -> _LifecycleProbeConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        return super().__new__(cls, actor_id=resolved)


class _LifecycleProbe(DataActor):
    def on_start(self) -> None:
        self._bar_type = DataType(
            COMPLETED_BAR_V1_TYPE_NAME,
            metadata={"series_id": "es_1m"},
        )
        self._shutdown_type = DataType(_FOUNDATION_SHUTDOWN_TYPE_NAME)
        self.subscribe_data(self._bar_type)
        self.subscribe_data(self._shutdown_type)
        self.subscribe_signal(ANALYTICAL_DEMAND_SIGNAL)
        self.subscribe_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL)

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, CompletedBarV1):
            _LIFECYCLE_COUNTS.setdefault("bars", []).append(payload)
            _LIFECYCLE_BAR_PUBLISHED.set()
        elif isinstance(payload, _FoundationShutdownSummary):
            _LIFECYCLE_COUNTS["shutdown_summary"] = payload

    def on_signal(self, signal: Signal) -> None:
        if signal.name == ANALYTICAL_DEMAND_SIGNAL:
            event = AnalyticalDemandEvent.from_signal_value(signal.value)
            _LIFECYCLE_CALLS["signals"].append((signal.name, event.action, event.selector))
        elif signal.name == HISTORICAL_DEPENDENCY_DEMAND_SIGNAL:
            event = HistoricalDependencyDemandEvent.from_signal_value(signal.value)
            _LIFECYCLE_CALLS["signals"].append((signal.name, "REQUEST", event.selector))

    def on_stop(self) -> None:
        self.unsubscribe_data(self._bar_type)
        self.unsubscribe_data(self._shutdown_type)
        self.unsubscribe_signal(ANALYTICAL_DEMAND_SIGNAL)
        self.unsubscribe_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL)


async def _run_lifecycle_fixture(node: LiveNode) -> None:
    handle = node.handle()
    run_task = asyncio.create_task(node.run_async())
    try:
        assert await asyncio.to_thread(_LIFECYCLE_BAR_PUBLISHED.wait, 2)
        await asyncio.sleep(0.02)
    finally:
        handle.stop()
        await run_task


def test_production_actor_lifecycle_seals_once_and_stops_symmetrically() -> None:
    _CALENDAR_REQUESTS["projection"].clear()
    _CALENDAR_REQUESTS["snapshot"].clear()
    _LIFECYCLE_BAR_PUBLISHED.clear()
    _LIFECYCLE_COUNTS.clear()
    for values in _LIFECYCLE_CALLS.values():
        values.clear()
    node = LiveNode.builder(
        "MARKEITECH-V3-03-FOUNDATION-LIFECYCLE",
        TraderId.from_str("MARKEITECH-LIFECYCLE-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
    module = "tests.intelligence.test_completed_bar_foundation"
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=f"{module}:_LifecycleCalendarResponder",
            config_path=f"{module}:_CalendarResponderConfig",
            config={"actor_id": "CALENDAR-RESPONDER"},
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=f"{module}:_LifecycleFoundationActor",
            config_path=f"{module}:_RoutingFoundationConfig",
            config={"actor_id": "COMPLETED-BARS-1"},
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=f"{module}:_LifecycleProbe",
            config_path=f"{module}:_LifecycleProbeConfig",
            config={"actor_id": "LIFECYCLE-PROBE"},
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=f"{module}:_ReadinessPublisher",
            config_path=f"{module}:_ReadinessPublisherConfig",
            config={"actor_id": "READINESS-PUBLISHER"},
        ),
    )

    asyncio.run(_run_lifecycle_fixture(node))
    published_count = len(_LIFECYCLE_COUNTS["bars"])
    asyncio.run(asyncio.sleep(0.02))

    assert _LIFECYCLE_COUNTS["before_cutoff"] == _SeriesAdmission.ACCEPTED
    assert _LIFECYCLE_COUNTS["exact_before_timer"] == _SeriesAdmission.LATE
    assert _LIFECYCLE_COUNTS["exact_after_timer"] == _SeriesAdmission.LATE
    assert _LIFECYCLE_COUNTS["scheduled_cutoff_ns"] == 121 * MINUTE_NS + SECOND_NS
    assert _LIFECYCLE_COUNTS["cutoff_fires"] == (
        ("completed-bar-cutoff:es_1m:7260000000000", 121 * MINUTE_NS + SECOND_NS),
    )
    assert published_count == 1
    assert len(_LIFECYCLE_COUNTS["bars"]) == published_count
    bar = _LIFECYCLE_COUNTS["bars"][0]
    assert isinstance(bar, CompletedBarV1)
    assert bar.publication_sequence == 1
    assert bar.completion_state is BarCompletionState.PARTIAL
    counters = _LIFECYCLE_COUNTS["series_counters"]
    assert isinstance(counters, dict)
    assert counters["published"] == 1
    assert counters["late_constituents"] == 2
    assert counters["live_demand_request"] == 1
    assert counters["live_demand_release"] == 1
    assert counters["historical_demand_request"] == 1
    assert _LIFECYCLE_CALLS["subscribe_bars"] == _LIFECYCLE_CALLS["unsubscribe_bars"]
    assert _LIFECYCLE_CALLS["subscribe_bars"] == [
        ("ESU6.CME-5-SECOND-LAST-EXTERNAL", "IB", {}),
    ]
    assert _LIFECYCLE_CALLS["subscribe_data"] == _LIFECYCLE_CALLS["unsubscribe_data"]
    assert _LIFECYCLE_COUNTS["remaining_foundation_timers"] == ()
    assert _LIFECYCLE_COUNTS["active"] is False
    assert _LIFECYCLE_COUNTS["terminal"] is True
    assert _LIFECYCLE_COUNTS["state_terminal"] is True
    summary = _LIFECYCLE_COUNTS["shutdown_summary"]
    assert isinstance(summary, _FoundationShutdownSummary)
    assert dict(summary.series_counters[0][1])["published"] == 1
    assert (
        ANALYTICAL_DEMAND_SIGNAL,
        "RELEASE",
        "5-SECOND-LAST-EXTERNAL",
    ) in _LIFECYCLE_CALLS["signals"]


class _RoutingFoundationActor(_CompletedBarFoundationActor):
    def on_start(self) -> None:
        self._active = True
        state = self.states["es_1m"]
        assert state.accept_projection(_projection_response())
        context = state.calendar_context(_historical_observation(0).interval_end_ns)
        assert context is not None
        candidate = _candidate_from_historical(
            _historical_observation(0),
            context=context,
        )
        bar = candidate.publish(
            run_epoch=RUN_EPOCH,
            sequence=1,
            published_ts_ns=3 * MINUTE_NS,
        )
        self._publish_bars(state, (bar,))

    def on_stop(self) -> None:
        self._active = False
        self._terminal = True
        for state in self.states.values():
            state.stop()


class _RoutingSubscriberConfig(DataActorConfig):
    def __new__(
        cls,
        label: str,
        series_id: str | None,
        actor_id: str | ActorId,
    ) -> _RoutingSubscriberConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.label = label
        obj.series_id = series_id
        return obj


class _RoutingSubscriber(DataActor):
    def __init__(self, config: _RoutingSubscriberConfig) -> None:
        super().__init__(config)
        self._label = config.label
        self._data_type = (
            DataType(COMPLETED_BAR_V1_TYPE_NAME)
            if config.series_id is None
            else DataType(COMPLETED_BAR_V1_TYPE_NAME, metadata={"series_id": config.series_id})
        )

    def on_start(self) -> None:
        self.subscribe_data(self._data_type)

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if payload.series_id != "es_1m":
            return
        _ROUTING_COUNTS[self._label] = _ROUTING_COUNTS.get(self._label, 0) + 1
        if self._label == "A":
            _ROUTING_RECEIVED.set()

    def on_stop(self) -> None:
        self.unsubscribe_data(self._data_type)


async def _run_routing_fixture(node: LiveNode) -> None:
    handle = node.handle()
    run_task = asyncio.create_task(node.run_async())
    try:
        assert await asyncio.to_thread(_ROUTING_RECEIVED.wait, 2)
        await asyncio.sleep(0.05)
    finally:
        handle.stop()
        await run_task


def test_disabled_foundation_uses_exact_pinned_nautilus_metadata_routing() -> None:
    _ROUTING_RECEIVED.clear()
    _ROUTING_COUNTS.clear()
    node = LiveNode.builder(
        "MARKEITECH-V3-03-FOUNDATION-ROUTING",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
    module = "tests.intelligence.test_completed_bar_foundation"
    for label, series_id in (("A", "es_1m"), ("B", "es_1m_b"), ("TYPE", None)):
        node.add_actor_from_config(
            ImportableActorConfig(
                actor_path=f"{module}:_RoutingSubscriber",
                config_path=f"{module}:_RoutingSubscriberConfig",
                config={
                    "label": label,
                    "series_id": series_id,
                    "actor_id": f"ROUTING-SUBSCRIBER-{label}",
                },
            ),
        )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=f"{module}:_RoutingFoundationActor",
            config_path=f"{module}:_RoutingFoundationConfig",
            config={"actor_id": "COMPLETED-BARS-1"},
        ),
    )

    asyncio.run(_run_routing_fixture(node))

    assert _ROUTING_COUNTS == {"A": 1}


class _ReadinessPublisherConfig(DataActorConfig):
    def __new__(
        cls,
        actor_id: str | ActorId = "READINESS-PUBLISHER",
    ) -> _ReadinessPublisherConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        return super().__new__(cls, actor_id=resolved)


class _ReadinessPublisher(DataActor):
    def on_start(self) -> None:
        self._canonical_type = DataType(
            COMPLETED_BAR_V1_TYPE_NAME,
            metadata={"series_id": "es_1m"},
        )
        self.subscribe_data(self._canonical_type)
        _STARTUP_ORDER.append("subscribe:es_1m")
        _STARTUP_ORDER.append("ack")
        data_type = DataType(_READINESS_TYPE_NAME)
        value = _SubscriptionReadinessAcknowledgement(
            startup_epoch=STARTUP_EPOCH,
            consumer_actor_id="DIRECT-METRICS-1",
            series_id="es_1m",
            manifest_digest=MANIFEST_DIGEST,
            status=_SubscriptionReadinessStatus.SUBSCRIBED,
            acknowledged_ts_ns=self.clock.timestamp_ns(),
        )
        self.publish_data(data_type, CustomData(data_type, value))

    def on_stop(self) -> None:
        self.unsubscribe_data(self._canonical_type)


class _DemandProbeConfig(DataActorConfig):
    def __new__(
        cls,
        actor_id: str | ActorId = "DEMAND-PROBE",
    ) -> _DemandProbeConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        return super().__new__(cls, actor_id=resolved)


class _DemandProbe(DataActor):
    def on_start(self) -> None:
        self.subscribe_signal(ANALYTICAL_DEMAND_SIGNAL)
        self.subscribe_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL)

    def on_signal(self, signal: Signal) -> None:
        if signal.name == ANALYTICAL_DEMAND_SIGNAL:
            value = AnalyticalDemandEvent.from_signal_value(signal.value)
            if value.action != "REQUEST":
                return
            selector = value.selector
        elif signal.name == HISTORICAL_DEPENDENCY_DEMAND_SIGNAL:
            selector = HistoricalDependencyDemandEvent.from_signal_value(signal.value).selector
        else:
            return
        _STARTUP_ORDER.append(f"demand:{selector}")
        if len([item for item in _STARTUP_ORDER if item.startswith("demand:")]) == 2:
            _DEMAND_RECEIVED.set()

    def on_stop(self) -> None:
        self.unsubscribe_signal(ANALYTICAL_DEMAND_SIGNAL)
        self.unsubscribe_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL)


def test_actual_foundation_waits_for_readiness_before_both_logical_demands() -> None:
    _DEMAND_RECEIVED.clear()
    _STARTUP_ORDER.clear()
    node = LiveNode.builder(
        "MARKEITECH-V3-03-FOUNDATION-READINESS",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).with_delay_post_stop_secs(0).build()
    module = "tests.intelligence.test_completed_bar_foundation"
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=f"{module}:_DemandProbe",
            config_path=f"{module}:_DemandProbeConfig",
            config={"actor_id": "DEMAND-PROBE"},
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=(
                "markeitech.intelligence.completed_bar_foundation:"
                "_CompletedBarFoundationActor"
            ),
            config_path=f"{module}:_RoutingFoundationConfig",
            config={"actor_id": "COMPLETED-BARS-1"},
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path=f"{module}:_ReadinessPublisher",
            config_path=f"{module}:_ReadinessPublisherConfig",
            config={"actor_id": "READINESS-PUBLISHER"},
        ),
    )

    asyncio.run(_run_demand_fixture(node))

    assert _STARTUP_ORDER[:2] == ["subscribe:es_1m", "ack"]
    assert _STARTUP_ORDER[2:] == [
        "demand:5-SECOND-LAST-EXTERNAL",
        "demand:1-MINUTE-LAST-EXTERNAL",
    ]


async def _run_demand_fixture(node: LiveNode) -> None:
    handle = node.handle()
    run_task = asyncio.create_task(node.run_async())
    try:
        assert await asyncio.to_thread(_DEMAND_RECEIVED.wait, 2)
    finally:
        handle.stop()
        await run_task
