from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from markeitech.domain import OneMinuteBar
from markeitech.persistence import (
    LivePersistenceIngress,
    PersistenceConfig,
    PersistenceIngressStatus,
    PersistenceRuntime,
    PersistenceRuntimeStatus,
    PersistenceSubmissionStatus,
    RetentionStatus,
)


class StubWriter:
    def __init__(self, result: PersistenceSubmissionStatus) -> None:
        self.result = result
        self.events: list[object] = []

    def submit(self, event: object) -> PersistenceSubmissionStatus:
        self.events.append(event)
        return self.result


class StubRetentionCalendar:
    def has_policy(self, instrument_id: str) -> bool:
        return True

    def retention_cutoff(
        self,
        instrument_id: str,
        completed_sessions: int,
        as_of: datetime,
    ) -> datetime:
        return as_of


def bar(*, complete: bool = True) -> OneMinuteBar:
    return OneMinuteBar(
        instrument_id="NQU6.CME",
        event_ts=datetime(2026, 8, 10, 11, 9, tzinfo=UTC),
        ts_init=datetime(2026, 8, 10, 11, 9, 0, 123456, tzinfo=UTC),
        event_ts_ns=1_786_360_140_000_000_000,
        ts_init_ns=1_786_360_140_123_456_789,
        open_ts=datetime(2026, 8, 10, 11, 8, tzinfo=UTC),
        close_ts=datetime(2026, 8, 10, 11, 9, tzinfo=UTC),
        open=Decimal("20000"),
        high=Decimal("20001"),
        low=Decimal("19999"),
        close=Decimal("20000.25"),
        volume=Decimal("1"),
        buy_volume=Decimal("0"),
        sell_volume=Decimal("0"),
        unknown_volume=Decimal("1"),
        source="ib",
        is_complete=complete,
    )


def test_ingress_accepts_native_and_only_completed_canonical_bars() -> None:
    writer = StubWriter(PersistenceSubmissionStatus.ACCEPTED)
    ingress = LivePersistenceIngress(writer)

    assert ingress.submit_native("native-tick") == PersistenceSubmissionStatus.ACCEPTED
    assert ingress.submit_canonical(object()) is None
    assert ingress.submit_canonical(bar(complete=False)) is None
    assert ingress.submit_canonical(bar()) == PersistenceSubmissionStatus.ACCEPTED

    assert writer.events == ["native-tick", bar()]
    assert ingress.snapshot.status == PersistenceIngressStatus.HEALTHY
    assert ingress.snapshot.accepted_native_count == 1
    assert ingress.snapshot.accepted_bar_count == 1
    assert ingress.snapshot.ignored_canonical_count == 2


def test_ingress_records_tick_damage_without_blocking_callback() -> None:
    writer = StubWriter(PersistenceSubmissionStatus.QUEUE_FULL)
    ingress = LivePersistenceIngress(writer)

    assert ingress.submit_native("native-tick") == PersistenceSubmissionStatus.QUEUE_FULL

    snapshot = ingress.snapshot
    assert snapshot.status == PersistenceIngressStatus.DEGRADED
    assert snapshot.rejected_count == 1
    assert snapshot.tick_gap_count == 1
    assert snapshot.bar_recovery_required_count == 0
    assert snapshot.reason_codes == ("persistence_queue_full",)


def test_ingress_marks_rejected_bar_for_historical_recovery() -> None:
    writer = StubWriter(PersistenceSubmissionStatus.QUEUE_FULL)
    ingress = LivePersistenceIngress(writer)

    assert ingress.submit_canonical(bar()) == PersistenceSubmissionStatus.QUEUE_FULL

    snapshot = ingress.snapshot
    assert snapshot.status == PersistenceIngressStatus.DEGRADED
    assert snapshot.tick_gap_count == 0
    assert snapshot.bar_recovery_required_count == 1


def test_ingress_fails_health_when_writer_is_not_running() -> None:
    writer = StubWriter(PersistenceSubmissionStatus.NOT_RUNNING)
    ingress = LivePersistenceIngress(writer)

    assert ingress.submit_native("native-tick") == PersistenceSubmissionStatus.NOT_RUNNING

    assert ingress.snapshot.status == PersistenceIngressStatus.FAILED
    assert ingress.snapshot.reason_codes == ("persistence_not_running",)


def test_runtime_runs_enabled_retention_before_accepting_work(tmp_path: Path) -> None:
    config = PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        journal_path=tmp_path / "journal",
        retention_maintenance_enabled=True,
    )
    runtime = PersistenceRuntime.build(
        config,
        retention_calendar=StubRetentionCalendar(),
    )

    runtime.start()
    try:
        assert runtime.status == PersistenceRuntimeStatus.RUNNING
        assert runtime.retention_report is not None
        assert runtime.retention_report.status == RetentionStatus.NOOP
    finally:
        runtime.stop()


def test_enabled_retention_requires_explicit_calendar(tmp_path: Path) -> None:
    config = PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        retention_maintenance_enabled=True,
    )

    with pytest.raises(ValueError, match="requires a session calendar"):
        PersistenceRuntime.build(config)
