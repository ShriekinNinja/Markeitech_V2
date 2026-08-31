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
    FrozenVisualDebugCapture,
    VisualDebugCaptureCollector,
    frozen_capture_manifest,
)

_COMPLETION_DEADLINE = "visual-debug-completion-deadline"
_QUIET_ALERT = "visual-debug-quiet-alert"
_RESULT_TIMER = "visual-debug-result"
_RESULT_INTERVAL_NS = 100_000_000


@dataclass(frozen=True, slots=True)
class VisualDebugWriterResult:
    state: str
    detail: str


class VisualDebugCaptureWriter:
    def __init__(self, output_directory: Path, renderer_layout: dict[str, int]) -> None:
        self._output_directory = output_directory
        self._renderer_layout = dict(renderer_layout)
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

        html_text = render_visual_debug_html(capture, layout=self._renderer_layout)
        html_bytes = html_text.encode()
        html_digest = hashlib.sha256(html_bytes).hexdigest()
        manifest = frozen_capture_manifest(
            capture,
            html_sha256=html_digest,
            plotly_version=version("plotly"),
            renderer_layout=self._renderer_layout,
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
            state = (
                "OUTPUT_PUBLISHED"
                if capture.selection_state.startswith("COMPLETE")
                else "PARTIAL_OUTPUT_PUBLISHED"
            )
            self._result(state, str(final))
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
        target_historical_bars: int,
        target_live_bars: int,
        quiet_period_ms: int,
        completion_deadline_ms: int,
        output_drain_timeout_ms: int,
        candle_pane_height_px: int,
        volume_pane_height_px: int,
        metric_pane_height_px: int,
        pane_gap_px: int,
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
        obj.target_historical_bars = target_historical_bars
        obj.target_live_bars = target_live_bars
        obj.quiet_period_ms = quiet_period_ms
        obj.completion_deadline_ms = completion_deadline_ms
        obj.output_drain_timeout_ms = output_drain_timeout_ms
        obj.candle_pane_height_px = candle_pane_height_px
        obj.volume_pane_height_px = volume_pane_height_px
        obj.metric_pane_height_px = metric_pane_height_px
        obj.pane_gap_px = pane_gap_px
        return obj


class VisualDebugCaptureActor(DataActor):
    """Capture passive visual-debug projections.

    Markeitech Metadata:
        architecture.component.id: actor.visual-debug
        architecture.component.label: Visual Debug Capture
        architecture.component.kind: markeitech_actor
        architecture.component.boundary: boundary.intelligence
    """

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
        self._target_historical_bars = config.target_historical_bars
        self._quiet_ns = config.quiet_period_ms * 1_000_000
        self._deadline_ns = config.completion_deadline_ms * 1_000_000
        self._drain_seconds = config.output_drain_timeout_ms / 1000
        self._collector = VisualDebugCaptureCollector(
            instrument_id=config.instrument_id,
            analytical_profile_id=config.analytical_profile_id,
            analytical_profile_version=config.analytical_profile_version,
            bar_specification=config.bar_specification,
            parameter_version=config.parameter_version,
            target_historical_bars=config.target_historical_bars,
            target_live_bars=config.target_live_bars,
        )
        self._writer = VisualDebugCaptureWriter(
            Path(config.output_directory),
            {
                "candle_pane_height_px": config.candle_pane_height_px,
                "volume_pane_height_px": config.volume_pane_height_px,
                "metric_pane_height_px": config.metric_pane_height_px,
                "pane_gap_px": config.pane_gap_px,
            },
        )
        self._bar_type = DataType(COMPLETED_BAR_INPUT_TYPE_NAME)
        self._metric_type = DataType(METRIC_VALUE_TYPE_NAME)
        self._readiness: HistoricalReadinessEvent | None = None
        self._collection_started_ns = 0
        self._stopping = False
        self._frozen = False
        self._state = "STARTING"

    def on_start(self) -> None:
        self.subscribe_data(self._bar_type)
        self.subscribe_data(self._metric_type)
        self.subscribe_signal(HISTORICAL_READINESS_SIGNAL)
        self._writer.start()
        self._collection_started_ns = self.clock.timestamp_ns()
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
        ):
            self._readiness = event
            self._evaluate_completion()

    def on_stop(self) -> None:
        self._stopping = True
        if not self._frozen:
            self._state = "STOPPED_BEFORE_FREEZE"
        for name in (_COMPLETION_DEADLINE, _QUIET_ALERT, _RESULT_TIMER):
            if name in self.clock.timer_names():
                self.clock.cancel_timer(name)
        self.unsubscribe_signal(HISTORICAL_READINESS_SIGNAL)
        self.unsubscribe_data(self._bar_type)
        self.unsubscribe_data(self._metric_type)
        if not self._writer.close(self._drain_seconds):
            self._state = "OUTPUT_UNFINISHED"
        self._drain_result(None)
        self.log.info(f"VISUAL_DEBUG_CAPTURE_STOPPED | state={self._state}")

    def on_dispose(self) -> None:
        self._writer.close(0.0)

    def _evaluate_completion(self) -> None:
        if not self._collector.target_population_is_complete():
            if _QUIET_ALERT in self.clock.timer_names():
                self.clock.cancel_timer(_QUIET_ALERT)
            self._state = "COLLECTING"
            return
        if self._target_historical_bars and self._readiness is None:
            if _QUIET_ALERT in self.clock.timer_names():
                self.clock.cancel_timer(_QUIET_ALERT)
            self._state = "COLLECTING"
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
        if self._stopping or self._frozen:
            return
        try:
            capture = self._collector.freeze(
                run_id=self._run_id,
                configuration_identity=self._configuration_identity,
                capture_policy_version=self._capture_policy_version,
                collection_started_ns=self._collection_started_ns,
                frozen_at_ns=self.clock.timestamp_ns(),
                historical_readiness=self._readiness,
            )
        except ValueError as exc:
            self._fail(type(exc).__name__)
            return
        self._frozen = True
        if _COMPLETION_DEADLINE in self.clock.timer_names():
            self.clock.cancel_timer(_COMPLETION_DEADLINE)
        if not self._writer.submit(capture):
            self._fail("QUEUE_REJECTED")
            return
        self._state = "OUTPUT_PENDING"

    def _on_deadline(self, _event) -> None:  # noqa: ANN001
        if not self._frozen:
            self._freeze(_event)

    def _drain_result(self, _event) -> None:  # noqa: ANN001
        try:
            result = self._writer.results.get_nowait()
        except queue.Empty:
            return
        self._state = result.state
        if result.state == "OUTPUT_PUBLISHED":
            self.log.info(f"VISUAL_DEBUG_CAPTURE_OUTPUT_PUBLISHED | path={result.detail}")
        elif result.state == "PARTIAL_OUTPUT_PUBLISHED":
            self.log.warning(
                f"VISUAL_DEBUG_CAPTURE_PARTIAL_OUTPUT_PUBLISHED | path={result.detail}",
            )
        else:
            self.log.error(f"VISUAL_DEBUG_CAPTURE_{result.state} | detail={result.detail}")

    def _fail(self, reason: str) -> None:
        self._state = reason
        self._frozen = True
        for name in (_COMPLETION_DEADLINE, _QUIET_ALERT):
            if name in self.clock.timer_names():
                self.clock.cancel_timer(name)
        self.log.error(f"VISUAL_DEBUG_CAPTURE_FAILED | reason={reason}")
