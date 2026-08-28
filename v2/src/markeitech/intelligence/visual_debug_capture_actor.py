from __future__ import annotations

import hashlib
import json
import queue
import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, CustomData, DataType

from markeitech.acquisition import HISTORICAL_READINESS_SIGNAL, HistoricalReadinessEvent
from markeitech.intelligence.completed_bars import COMPLETED_BAR_INPUT_TYPE_NAME, CompletedBarInput
from markeitech.intelligence.metrics import METRIC_VALUE_TYPE_NAME, MetricValue
from markeitech.intelligence.session_measurements import COMPLETED_BAR_METRIC_IDS
from markeitech.intelligence.visual_debug_capture import (
    VISUAL_DEBUG_SNAPSHOT_REQUEST_TYPE_NAME,
    VISUAL_DEBUG_SNAPSHOT_RESPONSE_TYPE_NAME,
    CompletedBarFoundationSnapshotRequest,
    CompletedBarFoundationSnapshotResponse,
    FrozenVisualDebugCapture,
    VisualDebugCaptureCollector,
    frozen_capture_manifest,
)

_SNAPSHOT_RETRY_TIMER = "visual-debug-snapshot-retry"
_COMPLETION_DEADLINE = "visual-debug-completion-deadline"
_QUIET_ALERT = "visual-debug-quiet-alert"
_RESULT_TIMER = "visual-debug-result"
_RESULT_INTERVAL_NS = 100_000_000


@dataclass(frozen=True, slots=True)
class VisualDebugWriterResult:
    state: str
    detail: str


class VisualDebugCaptureWriter:
    def __init__(self, output_directory: Path) -> None:
        self._output_directory = output_directory
        self._jobs: queue.Queue[FrozenVisualDebugCapture | None] = queue.Queue(maxsize=1)
        self.results: queue.Queue[VisualDebugWriterResult] = queue.Queue(maxsize=1)
        self._cancelled = threading.Event()
        self._commit_lock = threading.Lock()
        self._thread = threading.Thread(
            target=self._run,
            name="visual-debug-capture-writer",
            daemon=True,
        )
        self._started = False
        self._closed = False

    def start(self) -> None:
        if self._started:
            return
        self._output_directory.mkdir(parents=True, exist_ok=True)
        self._thread.start()
        self._started = True

    def submit(self, capture: FrozenVisualDebugCapture) -> bool:
        if not self._started or self._closed:
            return False
        try:
            self._jobs.put_nowait(capture)
        except queue.Full:
            return False
        return True

    def close(self, timeout_seconds: float) -> bool:
        if self._closed:
            return not self._thread.is_alive()
        self._closed = True
        if self._started:
            try:
                self._jobs.put_nowait(None)
            except queue.Full:
                pass
            self._thread.join(max(0.0, timeout_seconds))
        if self._thread.is_alive():
            with self._commit_lock:
                self._cancelled.set()
            return False
        return True

    def _run(self) -> None:
        try:
            capture = self._jobs.get()
            if capture is None:
                return
            self._render_and_publish(capture)
        except Exception as exc:  # noqa: BLE001
            self._result("OUTPUT_FAILED", type(exc).__name__)

    def _render_and_publish(self, capture: FrozenVisualDebugCapture) -> None:
        from importlib.metadata import version

        from markeitech.intelligence.visual_debug_capture_plotly import (
            render_visual_debug_html,
        )

        html_text = render_visual_debug_html(capture)
        html_bytes = html_text.encode()
        html_digest = hashlib.sha256(html_bytes).hexdigest()
        manifest = frozen_capture_manifest(
            capture,
            html_sha256=html_digest,
            plotly_version=version("plotly"),
        )
        staging = Path(
            tempfile.mkdtemp(
                prefix=f".{capture.capture_id}.",
                dir=self._output_directory,
            ),
        )
        try:
            (staging / "snapshot.html").write_bytes(html_bytes)
            (staging / "manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            if hashlib.sha256((staging / "snapshot.html").read_bytes()).hexdigest() != html_digest:
                raise ValueError("staged HTML digest mismatch")
            final = self._output_directory / capture.capture_id
            with self._commit_lock:
                if self._cancelled.is_set():
                    self._result("OUTPUT_CANCELLED", "commit_fence")
                    return
                if final.exists():
                    raise FileExistsError("capture output already exists")
                staging.rename(final)
            self._result("OUTPUT_PUBLISHED", str(final))
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    def _result(self, state: str, detail: str) -> None:
        try:
            self.results.put_nowait(VisualDebugWriterResult(state, detail))
        except queue.Full:
            pass


class VisualDebugCaptureActorConfig(DataActorConfig):
    def __new__(
        cls,
        run_id: str,
        configuration_identity: str,
        instrument_id: str,
        analytical_profile_id: str,
        analytical_profile_version: int,
        bar_specification: str,
        parameter_version: int,
        output_directory: str,
        capture_policy_version: int,
        historical_bar_count: int,
        live_bar_count: int,
        quiet_period_ms: int,
        snapshot_retry_interval_ms: int,
        completion_deadline_ms: int,
        output_drain_timeout_ms: int,
        actor_id: str | ActorId,
    ) -> VisualDebugCaptureActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.run_id = run_id
        obj.configuration_identity = configuration_identity
        obj.instrument_id = instrument_id
        obj.analytical_profile_id = analytical_profile_id
        obj.analytical_profile_version = analytical_profile_version
        obj.bar_specification = bar_specification
        obj.parameter_version = parameter_version
        obj.output_directory = output_directory
        obj.capture_policy_version = capture_policy_version
        obj.historical_bar_count = historical_bar_count
        obj.live_bar_count = live_bar_count
        obj.quiet_period_ms = quiet_period_ms
        obj.snapshot_retry_interval_ms = snapshot_retry_interval_ms
        obj.completion_deadline_ms = completion_deadline_ms
        obj.output_drain_timeout_ms = output_drain_timeout_ms
        return obj


class VisualDebugCaptureActor(DataActor):
    def __init__(self, config: VisualDebugCaptureActorConfig) -> None:
        super().__init__(config)
        self._run_id = config.run_id
        self._configuration_identity = config.configuration_identity
        self._instrument_id = config.instrument_id
        self._profile_id = config.analytical_profile_id
        self._profile_version = config.analytical_profile_version
        self._bar_specification = config.bar_specification
        self._parameter_version = config.parameter_version
        self._capture_policy_version = config.capture_policy_version
        self._historical_bar_count = config.historical_bar_count
        self._quiet_ns = config.quiet_period_ms * 1_000_000
        self._retry_ns = config.snapshot_retry_interval_ms * 1_000_000
        self._deadline_ns = config.completion_deadline_ms * 1_000_000
        self._drain_seconds = config.output_drain_timeout_ms / 1000
        self._collector = VisualDebugCaptureCollector(
            instrument_id=config.instrument_id,
            bar_specification=config.bar_specification,
            parameter_version=config.parameter_version,
            historical_bar_count=config.historical_bar_count,
            live_bar_count=config.live_bar_count,
        )
        self._writer = VisualDebugCaptureWriter(Path(config.output_directory))
        self._bar_type = DataType(COMPLETED_BAR_INPUT_TYPE_NAME)
        self._metric_type = DataType(METRIC_VALUE_TYPE_NAME)
        self._request_type = DataType(VISUAL_DEBUG_SNAPSHOT_REQUEST_TYPE_NAME)
        self._response_type = DataType(VISUAL_DEBUG_SNAPSHOT_RESPONSE_TYPE_NAME)
        self._request_id = hashlib.sha256(
            f"{self._run_id}:{self.actor_id}:foundation".encode(),
        ).hexdigest()
        self._readiness: HistoricalReadinessEvent | None = None
        self._stopping = False
        self._frozen = False
        self._state = "STARTING"

    def on_start(self) -> None:
        self.subscribe_data(self._bar_type)
        self.subscribe_data(self._metric_type)
        self.subscribe_data(self._response_type)
        self.subscribe_signal(HISTORICAL_READINESS_SIGNAL)
        self._writer.start()
        self._request_snapshot(None)
        self.clock.set_timer_ns(
            _SNAPSHOT_RETRY_TIMER, self._retry_ns, callback=self._request_snapshot
        )
        self.clock.set_time_alert_ns(
            _COMPLETION_DEADLINE,
            self.clock.timestamp_ns() + self._deadline_ns,
            callback=self._on_deadline,
        )
        self.clock.set_timer_ns(_RESULT_TIMER, _RESULT_INTERVAL_NS, callback=self._drain_result)
        self._state = "COLLECTING"

    def on_data(self, data) -> None:  # noqa: ANN001
        if self._stopping or self._frozen:
            return
        payload = data.data if isinstance(data, CustomData) else data
        accepted = False
        relevant = False
        if isinstance(payload, CompletedBarInput):
            relevant = (
                payload.instrument_id == self._instrument_id
                and payload.bar_specification == self._bar_specification
            )
            accepted = self._collector.accept_bar(payload)
        elif isinstance(payload, MetricValue):
            relevant = (
                payload.instrument_id == self._instrument_id
                and payload.parameter_version == self._parameter_version
                and payload.metric_id in COMPLETED_BAR_METRIC_IDS
            )
            accepted = self._collector.accept_metric(payload)
        elif (
            isinstance(payload, CompletedBarFoundationSnapshotResponse)
            and payload.request_id == self._request_id
            and payload.requester == str(self.actor_id)
        ):
            if _SNAPSHOT_RETRY_TIMER in self.clock.timer_names():
                self.clock.cancel_timer(_SNAPSHOT_RETRY_TIMER)
            self._collector.accept_snapshot(payload.snapshot)
            if payload.snapshot.historical_readiness is not None:
                self._accept_readiness(payload.snapshot.historical_readiness)
            accepted = True
            relevant = True
        if self._collector.conflict is not None:
            self._fail(self._collector.conflict)
        elif accepted or relevant:
            self._evaluate_completion()

    def on_signal(self, signal: Signal) -> None:
        if self._stopping or signal.name != HISTORICAL_READINESS_SIGNAL:
            return
        try:
            event = HistoricalReadinessEvent.from_signal_value(signal.value)
        except ValueError:
            return
        self._accept_readiness(event)

    def _accept_readiness(self, event: HistoricalReadinessEvent) -> None:
        if (
            event.consumer_id == "SESSION-METRICS"
            and event.capability_id == "metric:completed-bar-foundation"
            and event.instrument_id == self._instrument_id
            and event.selector == self._bar_specification
            and event.state == "READY"
            and event.observed_count == self._historical_bar_count
        ):
            self._readiness = event
            self._evaluate_completion()

    def on_stop(self) -> None:
        self._stopping = True
        if not self._frozen:
            self._state = "STOPPED_BEFORE_FREEZE"
        for name in (_SNAPSHOT_RETRY_TIMER, _COMPLETION_DEADLINE, _QUIET_ALERT, _RESULT_TIMER):
            if name in self.clock.timer_names():
                self.clock.cancel_timer(name)
        self.unsubscribe_signal(HISTORICAL_READINESS_SIGNAL)
        self.unsubscribe_data(self._bar_type)
        self.unsubscribe_data(self._metric_type)
        self.unsubscribe_data(self._response_type)
        if not self._writer.close(self._drain_seconds):
            self._state = "OUTPUT_UNFINISHED"
        self._drain_result(None)
        self.log.info(f"VISUAL_DEBUG_CAPTURE_STOPPED | state={self._state}")

    def on_dispose(self) -> None:
        self._writer.close(0.0)

    def _request_snapshot(self, _event) -> None:  # noqa: ANN001
        if self._stopping or self._frozen:
            return
        request = CompletedBarFoundationSnapshotRequest(
            request_id=self._request_id,
            requester=str(self.actor_id),
            requested_ts_ns=self.clock.timestamp_ns(),
            instrument_id=self._instrument_id,
            bar_specification=self._bar_specification,
            parameter_version=self._parameter_version,
            maximum_intervals=self._collector.maximum_intervals,
        )
        self.publish_data(self._request_type, CustomData(self._request_type, request))

    def _evaluate_completion(self) -> None:
        if self._readiness is None or self._collector.selected_records() is None:
            return
        if _QUIET_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_QUIET_ALERT)
        self.clock.set_time_alert_ns(
            _QUIET_ALERT,
            self.clock.timestamp_ns() + self._quiet_ns,
            callback=self._freeze,
        )
        self._state = "COALESCING"

    def _freeze(self, _event) -> None:  # noqa: ANN001
        if self._stopping or self._frozen or self._readiness is None:
            return
        try:
            capture = self._collector.freeze(
                run_id=self._run_id,
                configuration_identity=self._configuration_identity,
                capture_policy_version=self._capture_policy_version,
                frozen_at_ns=self.clock.timestamp_ns(),
                historical_readiness=self._readiness,
            )
        except ValueError as exc:
            self._fail(type(exc).__name__)
            return
        self._frozen = True
        if _SNAPSHOT_RETRY_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_SNAPSHOT_RETRY_TIMER)
        if _COMPLETION_DEADLINE in self.clock.timer_names():
            self.clock.cancel_timer(_COMPLETION_DEADLINE)
        if not self._writer.submit(capture):
            self._fail("QUEUE_REJECTED")
            return
        self._state = "OUTPUT_PENDING"

    def _on_deadline(self, _event) -> None:  # noqa: ANN001
        if not self._frozen:
            self._fail("CAPTURE_DEADLINE_EXPIRED")

    def _drain_result(self, _event) -> None:  # noqa: ANN001
        try:
            result = self._writer.results.get_nowait()
        except queue.Empty:
            return
        self._state = result.state
        if result.state == "OUTPUT_PUBLISHED":
            self.log.info(f"VISUAL_DEBUG_CAPTURE_OUTPUT_PUBLISHED | path={result.detail}")
        else:
            self.log.error(f"VISUAL_DEBUG_CAPTURE_{result.state} | detail={result.detail}")

    def _fail(self, reason: str) -> None:
        self._state = reason
        self._frozen = True
        for name in (_SNAPSHOT_RETRY_TIMER, _COMPLETION_DEADLINE, _QUIET_ALERT):
            if name in self.clock.timer_names():
                self.clock.cancel_timer(name)
        self.log.error(f"VISUAL_DEBUG_CAPTURE_FAILED | reason={reason}")
