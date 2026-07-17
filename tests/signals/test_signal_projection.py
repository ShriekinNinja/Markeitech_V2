from datetime import UTC, datetime
from threading import Event

from markeitech.signals import (
    BoundedSignalProjectionWriter,
    SignalProjectionWriterStatus,
    SignalRuntimeProjection,
    SignalRuntimeProjectionKind,
    format_signal_operator_projection,
    signal_projection_color,
)
from nautilus_trader.common.enums import LogColor

NOW = datetime(2026, 7, 15, 6, 0, tzinfo=UTC)


def runtime_projection(
    kind: SignalRuntimeProjectionKind = SignalRuntimeProjectionKind.HEARTBEAT,
) -> SignalRuntimeProjection:
    return SignalRuntimeProjection(
        kind=kind,
        occurred_ts=NOW,
        status="running",
        startup_watermark=NOW,
        restored_open_signal_count=1,
        processed_revision_count=12,
        stale_evaluation_count=6,
        evaluation_count=4,
        lifecycle_write_count=2,
        open_signal_count=1,
        projection_rejected_count=0,
        projection_callback_error_count=0,
        handoff_capacity=16,
        handoff_pending_count=3,
        handoff_high_watermark=4,
        handoff_rejected_count=1,
    )


def test_runtime_projection_is_human_readable_and_machine_stable() -> None:
    line = format_signal_operator_projection(
        runtime_projection(),
        role_resolver=lambda _instrument_id: "ACTIVE",
    )

    assert line == (
        "SIGNAL_RUNTIME | event=HEARTBEAT | status=RUNNING "
        "| watermark=2026-07-15T06:00:00+00:00 | restored=1 | revisions=12 "
        "| stale=6 | evaluations=4 | writes=2 | open=1 "
        "| confirmations=0 | triggered=0 | expired=0 | observations=0 "
        "| retained=0 | observation_conflicts=0 "
        "| handoff=3/16 | handoff_high_water=4 | handoff_rejected=1 "
        "| handoff_closed=0 "
        "| projection_rejected=0 | projection_errors=0"
    )


def test_projection_writer_drains_without_blocking_signal_runtime() -> None:
    lines: list[str] = []
    writer = BoundedSignalProjectionWriter(
        lines.append,
        lambda _instrument_id: "ACTIVE",
        queue_size=4,
        dedupe_size=8,
        poll_seconds=0.01,
    )

    writer.start()
    assert writer.submit(runtime_projection())
    assert writer.stop(1)

    assert writer.snapshot.status == SignalProjectionWriterStatus.STOPPED
    assert writer.snapshot.accepted_count == 1
    assert writer.snapshot.rendered_count == 1
    assert lines == [
        format_signal_operator_projection(
            runtime_projection(),
            role_resolver=lambda _instrument_id: "ACTIVE",
        )
        + " | render_errors=0"
    ]


def test_projection_writer_passes_semantic_color_to_nautilus_sink() -> None:
    colored: list[tuple[str, LogColor]] = []
    projection = runtime_projection(SignalRuntimeProjectionKind.STARTED)
    writer = BoundedSignalProjectionWriter(
        lambda _line: None,
        lambda _instrument_id: "ACTIVE",
        colored_sink=lambda line, color: colored.append((line, color)),
        queue_size=4,
        dedupe_size=8,
        poll_seconds=0.01,
    )

    writer.start()
    assert writer.submit(projection)
    assert writer.stop(1)

    assert signal_projection_color(projection) == LogColor.GREEN
    assert len(colored) == 1
    assert colored[0][0].startswith("SIGNAL_RUNTIME | event=STARTED")
    assert colored[0][1] == LogColor.GREEN


def test_projection_sink_failure_is_recorded_and_does_not_fail_writer() -> None:
    attempts = 0

    def fail_once(_line: str) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("operator sink unavailable")

    writer = BoundedSignalProjectionWriter(
        fail_once,
        lambda _instrument_id: "ACTIVE",
        queue_size=4,
        dedupe_size=8,
        poll_seconds=0.01,
    )
    writer.start()
    assert writer.submit(runtime_projection(SignalRuntimeProjectionKind.STARTED))
    assert writer.submit(runtime_projection())
    assert writer.stop(1)

    snapshot = writer.snapshot
    assert snapshot.status == SignalProjectionWriterStatus.STOPPED
    assert snapshot.failed_count == 1
    assert snapshot.rendered_count == 1
    assert snapshot.last_error == "RuntimeError: operator sink unavailable"
    assert attempts == 2


def test_failed_runtime_projection_replaces_queued_heartbeat_at_capacity() -> None:
    lines: list[str] = []
    sink_entered = Event()
    release_sink = Event()

    def blocking_sink(line: str) -> None:
        if "event=STARTED" in line:
            sink_entered.set()
            assert release_sink.wait(1)
        lines.append(line)

    writer = BoundedSignalProjectionWriter(
        blocking_sink,
        lambda _instrument_id: "ACTIVE",
        queue_size=1,
        dedupe_size=1,
        poll_seconds=1,
    )
    writer.start()
    assert writer.submit(runtime_projection(SignalRuntimeProjectionKind.STARTED))
    assert sink_entered.wait(1)
    assert writer.submit(runtime_projection())
    failed = runtime_projection(SignalRuntimeProjectionKind.FAILED)
    failed = SignalRuntimeProjection(
        **{
            **failed.__dict__,
            "status": "failed",
            "last_error": "RuntimeError: calendar unavailable",
            "failure_phase": "feature_revision",
            "failure_input_identity": "commit_sequence=12;instrument=NQU6.CME",
            "last_successful_commit_sequence": 11,
            "error_traceback": "Traceback: calendar unavailable",
        }
    )

    assert writer.submit(failed)
    release_sink.set()
    assert writer.stop(2)

    assert len(lines) == 2
    assert "event=STARTED" in lines[0]
    assert "event=FAILED" in lines[1]
    assert "failure_phase=feature_revision" in lines[1]
    assert "last_successful_sequence=11" in lines[1]


def test_projection_writer_rejects_submission_outside_running_lifecycle() -> None:
    writer = BoundedSignalProjectionWriter(
        lambda _line: None,
        lambda _instrument_id: "ACTIVE",
        queue_size=1,
        dedupe_size=1,
    )

    assert not writer.submit(runtime_projection())
    assert writer.stop(1)
    assert writer.snapshot.rejected_count == 1
