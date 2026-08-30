from __future__ import annotations

from threading import Event
from uuid import uuid4

import pytest
from nautilus_trader.common import Signal

from markeitech.acquisition import (
    HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
    HISTORICAL_EXECUTION_SIGNAL,
    HISTORICAL_READINESS_SIGNAL,
    HistoricalDependencyDemandEvent,
    HistoricalExecutionEventMessage,
    HistoricalReadinessEvent,
)
from markeitech.intelligence.calendar_messages import CalendarTransition
from markeitech.intelligence.messages import (
    EVIDENCE_HEALTH_SIGNAL,
    EvidenceHealthEvent,
)
from markeitech.system.messages import (
    ACQUISITION_STATUS_REQUEST_SIGNAL,
    ACQUISITION_STREAM_SIGNAL,
    WATCHLIST_DEMAND_SIGNAL,
    WATCHLIST_LIFECYCLE_SIGNAL,
    WATCHLIST_MEMBERSHIP_SIGNAL,
    AcquisitionStatusRequest,
    AcquisitionStreamEvent,
    SystemHealthEvent,
    WatchlistDemandEvent,
    WatchlistLifecycleEvent,
    WatchlistMember,
    WatchlistMembershipEvent,
)
from markeitech.system.persistence import (
    HealthEventRecord,
    OperationalEventRecord,
    PersistenceWorker,
    _is_critical_record,
    _record_from_calendar_transition,
    _record_from_signal,
)
from markeitech.system.resource_contracts import (
    RUNTIME_RESOURCE_HEALTH_SIGNAL,
    RUNTIME_RESOURCE_SIGNAL,
    RuntimeResourceEvent,
    RuntimeResourceHealthEvent,
)


def test_operational_event_record_validates_durable_identity_and_timestamps() -> None:
    record = OperationalEventRecord(
        event_id=" watchlist-membership:1 ",
        run_id=uuid4(),
        sequence=1,
        signal_name=" markeitech.watchlist.membership ",
        event_type=" watchlist.membership ",
        source=" WATCHLIST ",
        correlation_id=" baseline:config ",
        causation_id=None,
        payload={"membership_revision": 1},
        ts_event_ns=10,
        ts_init_ns=11,
        schema_version=1,
    )

    assert record.event_id == "watchlist-membership:1"
    assert record.signal_name == "markeitech.watchlist.membership"
    assert record.correlation_id == "baseline:config"
    with pytest.raises(TypeError):
        record.payload["membership_revision"] = 2  # type: ignore[index]

    with pytest.raises(ValueError, match="sequence must be a positive integer"):
        OperationalEventRecord(
            event_id="watchlist-membership:2",
            run_id=uuid4(),
            sequence=0,
            signal_name="markeitech.watchlist.membership",
            event_type="watchlist.membership",
            source="WATCHLIST",
            payload={},
            ts_event_ns=10,
            ts_init_ns=11,
            schema_version=1,
        )


def test_runtime_resource_signal_converts_to_operational_audit_record() -> None:
    run_id = uuid4()
    event = RuntimeResourceEvent(
        event_id="runtime-resource:RUNTIME-RESOURCES:100",
        source="RUNTIME-RESOURCES",
        observed_ts_ns=100,
        sample_sequence=1,
        sample_interval_ms=10000,
        rss_bytes=500,
        peak_rss_bytes=500,
        vms_bytes=1000,
        cpu_user_seconds=1.0,
        cpu_system_seconds=0.5,
        cpu_percent=15.0,
        thread_count=8,
        open_fd_count=12,
        open_fd_soft_limit=1024,
        host_cpu_percent=30.0,
        host_memory_total_bytes=32_000,
        host_memory_available_bytes=16_000,
        host_memory_available_percent=50.0,
        host_swap_used_bytes=100,
        host_swap_percent=1.0,
        disk_path="/",
        disk_total_bytes=100_000,
        disk_free_bytes=50_000,
        disk_free_percent=50.0,
        cache_observed=True,
        cache_error=None,
        cache_instrument_count=2,
        cache_quote_tick_count=20,
        cache_trade_tick_count=10,
        cache_bar_type_count=3,
        cache_bar_count=30,
    )

    record = _record_from_signal(
        run_id,
        1,
        Signal(
            name=RUNTIME_RESOURCE_SIGNAL,
            value=event.to_signal_value(),
            ts_event=100,
            ts_init=101,
        ),
    )

    assert isinstance(record, OperationalEventRecord)
    assert record.event_id == event.event_id
    assert record.event_type == "runtime.resource"
    assert record.source == "RUNTIME-RESOURCES"
    assert record.correlation_id == "runtime-resource:RUNTIME-RESOURCES"
    assert record.payload["rss_bytes"] == 500


def test_runtime_resource_health_signal_is_durable_and_critical_when_required() -> None:
    run_id = uuid4()
    event = RuntimeResourceHealthEvent(
        event_id="runtime-resource-health:RESOURCE-HEALTH:100:CRITICAL",
        source="RESOURCE-HEALTH",
        observed_ts_ns=100,
        state="CRITICAL",
        previous_state="WARNING",
        reason_codes=("host_memory_available_percent",),
        observations={"host_memory_available_percent": 7.0},
        thresholds={"host_memory_available_percent": 8.0},
        notification_eligible=True,
        threshold_version="test-v1",
    )

    record = _record_from_signal(
        run_id,
        1,
        Signal(
            name=RUNTIME_RESOURCE_HEALTH_SIGNAL,
            value=event.to_signal_value(),
            ts_event=100,
            ts_init=101,
        ),
    )

    assert isinstance(record, OperationalEventRecord)
    assert record.event_type == "runtime.resource_health"
    assert record.payload["state"] == "CRITICAL"
    assert _is_critical_record(record) is True


def test_worker_preserves_order_across_health_and_generic_operational_records() -> None:
    run_id = uuid4()
    stored: list[tuple[int, str]] = []
    worker = PersistenceWorker(
        lambda records: stored.extend(
            (record.sequence, type(record).__name__) for record in records
        ),
        queue_capacity=4,
        critical_queue_reserve=0,
        write_batch_size=4,
        shutdown_timeout_seconds=1,
        write_max_attempts=1,
        write_retry_backoff_ms=0,
    )
    worker.start()

    assert worker.submit(_record(1, "STARTING"))
    assert worker.submit(
        OperationalEventRecord(
            event_id="watchlist-membership:1",
            run_id=run_id,
            sequence=2,
            signal_name=WATCHLIST_MEMBERSHIP_SIGNAL,
            event_type="watchlist.membership",
            source="WATCHLIST",
            payload={"membership_revision": 1},
            ts_event_ns=2,
            ts_init_ns=2,
            schema_version=1,
        ),
    )
    assert worker.close()

    assert stored == [
        (1, "HealthEventRecord"),
        (2, "OperationalEventRecord"),
    ]


def test_watchlist_signals_convert_to_auditable_records_without_market_payloads() -> None:
    run_id = uuid4()
    membership = WatchlistMembershipEvent(
        event_id="watchlist-membership:1",
        membership_revision=1,
        source="WATCHLIST",
        reason="static baseline",
        members=(
            WatchlistMember(
                instrument_id="ESU6.CME",
                calendar_id="cme_equity",
                capabilities=("top_of_book", "watchlist_last"),
                owner_ids=("config:system",),
            ),
        ),
    )
    membership_record = _record_from_signal(
        run_id,
        1,
        Signal(
            name=WATCHLIST_MEMBERSHIP_SIGNAL,
            value=membership.to_signal_value(),
            ts_event=10,
            ts_init=11,
        ),
    )
    lifecycle = WatchlistLifecycleEvent(
        event_id="watchlist-lifecycle:1",
        membership_revision=1,
        state="CONFIGURED",
        source="WATCHLIST",
        reason="static baseline",
        owner_id="config:system",
        correlation_id="watchlist-membership:1",
    )
    lifecycle_record = _record_from_signal(
        run_id,
        2,
        Signal(
            name=WATCHLIST_LIFECYCLE_SIGNAL,
            value=lifecycle.to_signal_value(),
            ts_event=12,
            ts_init=13,
        ),
    )
    demand = WatchlistDemandEvent(
        demand_id="watchlist:1:ESU6.CME/quotes/default",
        action="REQUEST",
        instrument_id="ESU6.CME",
        capability="top_of_book",
        feed_kind="quotes",
        selector="default",
        owner_id="config:system",
        purpose="static watchlist top_of_book",
    )
    demand_record = _record_from_signal(
        run_id,
        3,
        Signal(
            name=WATCHLIST_DEMAND_SIGNAL,
            value=demand.to_signal_value(),
            ts_event=14,
            ts_init=15,
        ),
    )

    assert isinstance(membership_record, OperationalEventRecord)
    assert membership_record.event_type == "watchlist.membership"
    assert membership_record.correlation_id == membership.event_id
    assert "best_bid" not in membership_record.payload
    assert isinstance(lifecycle_record, OperationalEventRecord)
    assert lifecycle_record.event_type == "watchlist.lifecycle"
    assert lifecycle_record.correlation_id == membership.event_id
    assert isinstance(demand_record, OperationalEventRecord)
    assert demand_record.event_type == "watchlist.demand"
    assert demand_record.correlation_id == demand.demand_id
    assert "best_bid" not in demand_record.payload


def test_existing_acquisition_intent_and_outcome_convert_to_audit_records() -> None:
    run_id = uuid4()
    request = AcquisitionStatusRequest(requester="SYSTEM-CONTROL")
    request_record = _record_from_signal(
        run_id,
        1,
        Signal(
            name=ACQUISITION_STATUS_REQUEST_SIGNAL,
            value=request.to_signal_value(),
            ts_event=10,
            ts_init=11,
        ),
    )
    stream = AcquisitionStreamEvent(
        state="SUBSCRIBED",
        instrument_id="ESU6.CME",
        feed_kind="quotes",
        selector="default",
        source="DATA-ACQUISITION",
        demand_id="watchlist:1:ESU6.CME/quotes/default",
        consumer_ids=("watchlist:1:ESU6.CME/quotes/default",),
        detail="native subscription command issued",
    )
    stream_record = _record_from_signal(
        run_id,
        2,
        Signal(
            name=ACQUISITION_STREAM_SIGNAL,
            value=stream.to_signal_value(),
            ts_event=12,
            ts_init=13,
        ),
    )

    assert isinstance(request_record, OperationalEventRecord)
    assert request_record.event_type == "acquisition.status_request"
    assert request_record.source == "SYSTEM-CONTROL"
    assert isinstance(stream_record, OperationalEventRecord)
    assert stream_record.event_type == "acquisition.stream"
    assert stream_record.correlation_id == stream.demand_id
    assert "bid_price" not in stream_record.payload


def test_historical_lifecycle_is_audited_without_raw_bars() -> None:
    run_id = uuid4()
    demand = HistoricalDependencyDemandEvent(
        demand_id="probe:ES",
        consumer_id="HISTORICAL-PROBE",
        capability_id="historical.acceptance_probe",
        capability_version=1,
        instrument_id="ESU6.CME",
        selector="1-MINUTE-LAST-EXTERNAL",
        window="recent_completed",
        minimum_observations=5,
        maximum_observations=10,
        priority=10,
        purpose="acceptance",
        as_of_ns=100,
    )
    execution = HistoricalExecutionEventMessage(
        event_id="request:SUBMITTED:1",
        request_id="request",
        state="SUBMITTED",
        attempt=1,
        instrument_id="ESU6.CME",
        selector="1-MINUTE-LAST-EXTERNAL",
        window="recent_completed",
        start_ns=10,
        end_ns=20,
        limit=10,
        consumer_ids=("HISTORICAL-PROBE",),
        occurred_at_ns=30,
        source="DATA-ACQUISITION",
        detail="provider request submitted",
    )
    readiness = HistoricalReadinessEvent(
        event_id="request:HISTORICAL-PROBE:READY",
        request_id="request",
        consumer_id="HISTORICAL-PROBE",
        capability_id="historical.acceptance_probe",
        capability_version=1,
        state="READY",
        instrument_id="ESU6.CME",
        selector="1-MINUTE-LAST-EXTERNAL",
        window="recent_completed",
        minimum_observations=5,
        observed_count=10,
        completed_at_ns=40,
        source="DATA-ACQUISITION",
        reason="minimum observations satisfied",
    )
    records = tuple(
        _record_from_signal(
            run_id,
            sequence,
            Signal(name=name, value=event.to_signal_value(), ts_event=50, ts_init=51),
        )
        for sequence, (name, event) in enumerate(
            (
                (HISTORICAL_DEPENDENCY_DEMAND_SIGNAL, demand),
                (HISTORICAL_EXECUTION_SIGNAL, execution),
                (HISTORICAL_READINESS_SIGNAL, readiness),
            ),
            start=1,
        )
    )

    assert tuple(record.event_type for record in records) == (
        "historical.dependency_demand",
        "historical.execution",
        "historical.readiness",
    )
    assert records[0].correlation_id == "probe:ES"
    assert records[1].correlation_id == "request"
    assert all("bars" not in record.payload for record in records)
    assert all("observations" not in record.payload for record in records)


def test_session_and_evidence_transitions_convert_to_audit_records() -> None:
    run_id = uuid4()
    session = CalendarTransition(
        event_id="calendar:run-1:cboe_spxw:1",
        calendar_id="cboe_spxw",
        schedule_version="cboe-spxw-v1",
        definition_version=1,
        definition_digest="d" * 64,
        effective_from_ns=1,
        trade_date="2026-08-17",
        previous_trade_date=None,
        phase_memberships=("GTH",),
        previous_phase_memberships=(),
        market_state="OPEN",
        previous_market_state="CLOSED",
        segment_open_ns=10,
        segment_close_ns=20,
        next_transition_ns=20,
        source="SESSION-STATE",
        source_epoch="run-1",
        effective_ts_ns=10,
        evaluated_ts_ns=10,
        published_ts_ns=11,
        reason="calendar state changed",
        revision=1,
        previous_revision=None,
    )
    evidence = EvidenceHealthEvent(
        event_id="evidence:SPX.CBOE/quotes/default:1",
        instrument_id="SPX.CBOE",
        calendar_id="cboe_spxw",
        feed_kind="quotes",
        selector="default",
        state="HEALTHY",
        previous_state="DEGRADED",
        reason="observation is fresh",
        fidelity="REPORTED",
        subscription_state="SUBSCRIBED",
        event_ts_ns=30,
        receive_ts_ns=31,
        evaluated_ts_ns=32,
        age_ms=1,
        session_phase="GTH",
        session_trade_date="2026-08-17",
        session_alignment="IN_SESSION",
        source="EVIDENCE-HEALTH",
        policy_version="quotes/default:2000-5000-15000ms",
        revision=1,
    )

    session_record = _record_from_calendar_transition(run_id, 1, session)
    evidence_record = _record_from_signal(
        run_id,
        2,
        Signal(
            name=EVIDENCE_HEALTH_SIGNAL,
            value=evidence.to_signal_value(),
            ts_event=42,
            ts_init=43,
        ),
    )

    assert session_record.event_type == "calendar.transition"
    assert session_record.correlation_id == "calendar:run-1:cboe_spxw:2026-08-17"
    assert evidence_record.event_type == "evidence.health"
    assert evidence_record.correlation_id == "evidence:SPX.CBOE:quotes:default"
    assert evidence_record.payload["state"] == "HEALTHY"


def _record(sequence: int, state: str = "READY") -> HealthEventRecord:
    return HealthEventRecord(
        run_id=uuid4(),
        sequence=sequence,
        event=SystemHealthEvent(
            state=state,
            reason="test transition",
            source="SYSTEM-CONTROL",
            evidence={"probe": True},
        ),
        ts_event_ns=sequence,
        ts_init_ns=sequence + 1,
    )


def test_persistence_worker_preserves_accepted_order_and_drains_on_close() -> None:
    stored: list[int] = []
    worker = PersistenceWorker(
        lambda records: stored.extend(record.sequence for record in records),
        queue_capacity=4,
        critical_queue_reserve=0,
        write_batch_size=4,
        shutdown_timeout_seconds=1,
        write_max_attempts=3,
        write_retry_backoff_ms=0,
    )
    worker.start()

    assert worker.submit(_record(1, "STARTING"))
    assert worker.submit(_record(2, "READY"))
    assert worker.close()

    assert stored == [1, 2]
    assert worker.results.get_nowait().stored is True
    assert worker.results.get_nowait().stored is True


def test_persistence_worker_reports_write_failure_without_dying() -> None:
    attempted: list[int] = []

    def write(records: tuple[HealthEventRecord, ...]) -> None:
        record = records[0]
        attempted.append(record.sequence)
        if record.sequence == 1:
            raise RuntimeError("database unavailable")

    worker = PersistenceWorker(
        write,
        queue_capacity=4,
        critical_queue_reserve=0,
        write_batch_size=1,
        shutdown_timeout_seconds=1,
        write_max_attempts=1,
        write_retry_backoff_ms=0,
    )
    worker.start()
    assert worker.submit(_record(1, "READY"))
    assert worker.submit(_record(2, "DEGRADED"))
    assert worker.close()

    first = worker.results.get_nowait()
    second = worker.results.get_nowait()
    assert attempted == [1, 2]
    assert first.stored is False and first.error_code == "RuntimeError"
    assert first.attempts == 1
    assert second.stored is True


def test_persistence_worker_retries_a_write_within_the_configured_bound() -> None:
    attempts = 0

    def eventually_write(_records: tuple[HealthEventRecord, ...]) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("temporary database failure")

    worker = PersistenceWorker(
        eventually_write,
        queue_capacity=1,
        critical_queue_reserve=0,
        write_batch_size=1,
        shutdown_timeout_seconds=1,
        write_max_attempts=3,
        write_retry_backoff_ms=0,
    )
    worker.start()
    assert worker.submit(_record(1))
    assert worker.close()

    result = worker.results.get_nowait()
    stats = worker.snapshot()
    assert result.stored is True and result.attempts == 3
    assert stats.accepted == 1
    assert stats.stored == 1
    assert stats.retry_attempts == 2
    assert stats.failed == 0
    assert stats.rejected == 0
    assert stats.pending == 0


def test_persistence_worker_rejects_without_blocking_when_bounded_queue_is_full() -> None:
    release = Event()
    entered = Event()

    def blocked_write(_records: tuple[HealthEventRecord, ...]) -> None:
        entered.set()
        release.wait(timeout=2)

    worker = PersistenceWorker(
        blocked_write,
        queue_capacity=1,
        critical_queue_reserve=0,
        write_batch_size=1,
        shutdown_timeout_seconds=2,
        write_max_attempts=1,
        write_retry_backoff_ms=0,
    )
    worker.start()
    assert worker.submit(_record(1))
    assert entered.wait(timeout=1)
    assert worker.submit(_record(2))
    assert worker.submit(_record(3)) is False

    saturated = worker.snapshot()
    assert saturated.accepted == 2
    assert saturated.rejected == 1
    assert saturated.pending == 2

    release.set()
    assert worker.close()
    stats = worker.snapshot()
    assert stats.accepted == 2
    assert stats.stored == 2
    assert stats.rejected == 1
    assert stats.pending == 0


def test_persistence_worker_can_finish_after_an_initial_close_timeout() -> None:
    release = Event()
    entered = Event()

    def blocked_write(_records: tuple[HealthEventRecord, ...]) -> None:
        entered.set()
        release.wait(timeout=2)

    worker = PersistenceWorker(
        blocked_write,
        queue_capacity=1,
        critical_queue_reserve=0,
        write_batch_size=1,
        shutdown_timeout_seconds=0.05,
        write_max_attempts=1,
        write_retry_backoff_ms=0,
    )
    worker.start()
    assert worker.submit(_record(1))
    assert entered.wait(timeout=1)

    assert worker.close() is False
    release.set()
    assert worker.close() is True
    assert worker.snapshot().pending == 0


def test_persistence_worker_reserves_capacity_for_critical_records() -> None:
    stored: list[int] = []
    worker = PersistenceWorker(
        lambda records: stored.extend(record.sequence for record in records),
        queue_capacity=3,
        critical_queue_reserve=1,
        write_batch_size=3,
        shutdown_timeout_seconds=1,
        write_max_attempts=1,
        write_retry_backoff_ms=0,
    )

    assert worker.submit(_record(1))
    assert worker.submit(_record(2))
    assert worker.submit(_record(3)) is False
    assert worker.submit(_record(4), critical=True)
    worker.start()
    assert worker.close()

    assert stored == [1, 2, 4]
