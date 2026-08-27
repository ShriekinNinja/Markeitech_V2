from __future__ import annotations

from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Thread
from typing import Any

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, CustomData, DataType

from markeitech.acquisition.historical_messages import (
    HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
    HISTORICAL_READINESS_SIGNAL,
    HistoricalDependencyDemandEvent,
    HistoricalReadinessEvent,
)
from markeitech.intelligence.completed_bars import (
    COMPLETED_BAR_INPUT_TYPE_NAME,
    CompletedBarInput,
    CompletedBarSource,
)
from markeitech.intelligence.entities import ENTITY_REVISION_TYPE_NAME, EntityRevision
from markeitech.intelligence.live_evidence_review import (
    ProjectionCollector,
    build_projection_payload,
    publish_projection_payload,
    review_inventory_from_json,
)
from markeitech.intelligence.metrics import METRIC_VALUE_TYPE_NAME, MetricValue
from markeitech.system.discord import OperationalReadinessProjection, OperationalReadinessSnapshot
from markeitech.system.messages import (
    SYSTEM_HEALTH_SIGNAL,
    WATCHLIST_LIFECYCLE_SIGNAL,
    WATCHLIST_MEMBERSHIP_SIGNAL,
    SystemHealthEvent,
    WatchlistLifecycleEvent,
    WatchlistMembershipEvent,
)

_READINESS_DEADLINE = "live-evidence-review-readiness-deadline"
_LIVE_BAR_DEADLINE = "live-evidence-review-live-bar-deadline"
_TRIGGER_INTERVAL_END = "live-evidence-review-trigger-interval-end"
_FREEZE_ALERT = "live-evidence-review-freeze"
_RESULT_TIMER = "live-evidence-review-output-result"
_RESULT_INTERVAL_NS = 250_000_000
_STOP = object()


class ProjectionWriter:
    def __init__(self, output_directory: Path) -> None:
        self._output_directory = output_directory
        self._jobs: Queue[dict[str, Any] | object] = Queue(maxsize=1)
        self.results: Queue[tuple[str, str]] = Queue(maxsize=1)
        self._cancel = Event()
        self._started = False
        self._closed = False
        self._thread = Thread(target=self._run, name="markeitech-live-evidence-capture")

    def start(self) -> None:
        if self._started:
            raise RuntimeError("projection writer already started")
        self._started = True
        self._thread.start()

    def submit(self, payload: dict[str, Any]) -> bool:
        if not self._started or self._closed or self._cancel.is_set():
            return False
        try:
            self._jobs.put_nowait(payload)
        except Full:
            return False
        self._closed = True
        return True

    def close(self, timeout_seconds: float) -> bool:
        if not self._started:
            return True
        if self._thread.is_alive() and not self._closed:
            self._closed = True
            try:
                self._jobs.put_nowait(_STOP)
            except Full:
                pass
        self._thread.join(timeout=timeout_seconds)
        if self._thread.is_alive():
            self._cancel.set()
            return False
        return True

    def _run(self) -> None:
        item = self._jobs.get()
        try:
            if item is _STOP or self._cancel.is_set():
                return
            assert isinstance(item, dict)
            try:
                path = publish_projection_payload(item, self._output_directory)
            except Exception as exc:
                self.results.put(("OUTPUT_FAILED", type(exc).__name__))
            else:
                if self._cancel.is_set():
                    self.results.put(("OUTPUT_UNFINISHED", "canceled_after_write"))
                else:
                    self.results.put(("OUTPUT_PUBLISHED", str(path)))
        finally:
            self._jobs.task_done()


class LiveEvidenceReviewActorConfig(DataActorConfig):
    def __new__(
        cls,
        *,
        run_id: str,
        inventory: dict[str, Any],
        instrument_id: str,
        analytical_profile_id: str,
        analytical_profile_version: int,
        bar_specification: str,
        output_directory: str,
        capture_policy_version: int,
        coalescing_interval_ms: int,
        readiness_deadline_ms: int,
        live_bar_deadline_ms: int,
        output_drain_timeout_ms: int,
        visible_window_ms: int,
        image_width: int,
        image_height: int,
        maximum_bars_per_series: int,
        maximum_metric_subjects: int,
        maximum_entity_subjects: int,
        contextual_bar_specifications: list[str],
        actor_id: str | ActorId = "LIVE-EVIDENCE-REVIEW",
    ) -> LiveEvidenceReviewActorConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        for name, value in locals().copy().items():
            if name not in {"cls", "actor_id", "resolved", "obj"}:
                setattr(obj, name, value)
        return obj


class LiveEvidenceReviewActor(DataActor):
    def __init__(self, config: LiveEvidenceReviewActorConfig) -> None:
        super().__init__(config)
        self._run_id = config.run_id
        self._inventory = review_inventory_from_json(config.inventory)
        self._instrument_id = config.instrument_id
        self._profile_id = config.analytical_profile_id
        self._profile_version = config.analytical_profile_version
        self._bar_specification = config.bar_specification
        self._coalescing_ns = config.coalescing_interval_ms * 1_000_000
        self._readiness_deadline_ns = config.readiness_deadline_ms * 1_000_000
        self._live_bar_deadline_ns = config.live_bar_deadline_ms * 1_000_000
        self._drain_timeout_seconds = config.output_drain_timeout_ms / 1000
        self._capture_policy = {
            "capture_policy_version": config.capture_policy_version,
            "coalescing_interval_ms": config.coalescing_interval_ms,
            "readiness_deadline_ms": config.readiness_deadline_ms,
            "live_bar_deadline_ms": config.live_bar_deadline_ms,
            "output_drain_timeout_ms": config.output_drain_timeout_ms,
            "visible_window_ms": config.visible_window_ms,
            "image_width": config.image_width,
            "image_height": config.image_height,
        }
        self._collector = ProjectionCollector(
            instrument_id=self._instrument_id,
            bar_specifications=tuple(config.contextual_bar_specifications),
            maximum_bars_per_series=config.maximum_bars_per_series,
            maximum_metric_subjects=config.maximum_metric_subjects,
            maximum_entity_subjects=config.maximum_entity_subjects,
        )
        self._readiness_projection = OperationalReadinessProjection()
        self._readiness: OperationalReadinessSnapshot | None = None
        self._trigger_bar: CompletedBarInput | None = None
        self._trigger_received_at_ns: int | None = None
        self._coalescing_started_ns: int | None = None
        self._expected_freeze_ns: int | None = None
        self._trigger_temporal_disposition: str | None = None
        self._state = "STARTING"
        self._terminal_reason: str | None = None
        self._writer = ProjectionWriter(Path(config.output_directory))
        self._completed_bar_type = DataType(COMPLETED_BAR_INPUT_TYPE_NAME)
        self._metric_type = DataType(METRIC_VALUE_TYPE_NAME)
        self._entity_type = DataType(ENTITY_REVISION_TYPE_NAME)

    def on_start(self) -> None:
        self.subscribe_data(self._completed_bar_type)
        self.subscribe_data(self._metric_type)
        self.subscribe_data(self._entity_type)
        for name in _READINESS_SIGNALS:
            self.subscribe_signal(name)
        self._writer.start()
        now = self.clock.timestamp_ns()
        self.clock.set_time_alert_ns(
            _READINESS_DEADLINE,
            now + self._readiness_deadline_ns,
            callback=self._on_readiness_deadline,
        )
        self.clock.set_timer_ns(_RESULT_TIMER, _RESULT_INTERVAL_NS, callback=self._drain_result)
        self._state = "WAITING_FOR_OPERATIONAL_COMPLETION"
        self.log.info(
            "LIVE_EVIDENCE_REVIEW_ARMED"
            f" | instrument={self._instrument_id}"
            f" | inventory={len(self._inventory.items)}"
            f" | inventory_digest={self._inventory.digest}",
        )

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if not isinstance(payload, CompletedBarInput | MetricValue | EntityRevision):
            return
        accepted = self._collector.accept(payload)
        if not accepted or not isinstance(payload, CompletedBarInput):
            return
        if self._trigger_revision_changed(payload):
            self._cancel_capture_timers()
            self._fail("TRIGGER_REVISION_CHANGED", f"revision={payload.revision}")
            return
        if self._state != "WAITING_FOR_LIVE_ES_5M" or not self._qualifies(payload):
            return
        self._trigger_bar = payload
        self._cancel_timer(_LIVE_BAR_DEADLINE)
        now_ns = self.clock.timestamp_ns()
        self._trigger_received_at_ns = now_ns
        disposition, eligible_at_ns, _ = _capture_schedule(
            now_ns,
            payload.interval_end_ns,
            self._coalescing_ns,
        )
        self._trigger_temporal_disposition = disposition
        if eligible_at_ns > now_ns:
            self._state = "WAITING_FOR_TRIGGER_INTERVAL_END"
            self.clock.set_time_alert_ns(
                _TRIGGER_INTERVAL_END,
                eligible_at_ns,
                callback=self._on_trigger_interval_end,
                allow_past=False,
            )
        else:
            self._start_coalescing(now_ns)
        self.log.info(
            "LIVE_EVIDENCE_REVIEW_CAPTURE_TRIGGERED"
            f" | received_at_ns={now_ns} | interval_end_ns={payload.interval_end_ns}"
            f" | disposition={self._trigger_temporal_disposition}"
            f" | revision={payload.revision}",
        )

    def on_signal(self, signal: Signal) -> None:
        if signal.name not in _READINESS_SIGNALS:
            return
        if signal.name == SYSTEM_HEALTH_SIGNAL:
            try:
                health = SystemHealthEvent.from_signal_value(signal.value)
            except ValueError as exc:
                self._fail("READINESS_CONFLICT", type(exc).__name__)
                return
            if health.state in {"FAILED", "STOPPING"} and self._state in {
                "WAITING_FOR_OPERATIONAL_COMPLETION",
                "WAITING_FOR_LIVE_ES_5M",
                "WAITING_FOR_TRIGGER_INTERVAL_END",
                "COALESCING",
            }:
                self._cancel_capture_timers()
                self._fail("SYSTEM_FAILED", health.state)
                return
        if self._state not in {
            "WAITING_FOR_OPERATIONAL_COMPLETION", "WAITING_FOR_LIVE_ES_5M",
        }:
            return
        try:
            snapshot = _accept_readiness(self._readiness_projection, signal)
        except ValueError as exc:
            self._fail("READINESS_CONFLICT", type(exc).__name__)
            return
        if snapshot is None or self._state != "WAITING_FOR_OPERATIONAL_COMPLETION":
            return
        self._readiness = snapshot
        if snapshot.system_state in {"FAILED", "STOPPING"}:
            self._fail("SYSTEM_FAILED", snapshot.system_state)
            return
        self._state = "WAITING_FOR_LIVE_ES_5M"
        self._cancel_timer(_READINESS_DEADLINE)
        self.clock.set_time_alert_ns(
            _LIVE_BAR_DEADLINE,
            self.clock.timestamp_ns() + self._live_bar_deadline_ns,
            callback=self._on_live_bar_deadline,
        )

    def on_stop(self) -> None:
        unfinished_states = {
            "WAITING_FOR_OPERATIONAL_COMPLETION",
            "WAITING_FOR_LIVE_ES_5M",
            "WAITING_FOR_TRIGGER_INTERVAL_END",
            "COALESCING",
        }
        if self._state in unfinished_states:
            self._terminal_reason = "STOPPED_BEFORE_FREEZE"
            self._state = "INCOMPLETE"
        for name in _READINESS_SIGNALS:
            self.unsubscribe_signal(name)
        self.unsubscribe_data(self._completed_bar_type)
        self.unsubscribe_data(self._metric_type)
        self.unsubscribe_data(self._entity_type)
        for name in (
            _READINESS_DEADLINE,
            _LIVE_BAR_DEADLINE,
            _TRIGGER_INTERVAL_END,
            _FREEZE_ALERT,
            _RESULT_TIMER,
        ):
            self._cancel_timer(name)
        if not self._writer.close(self._drain_timeout_seconds):
            self._state = "OUTPUT_UNFINISHED"
            self._terminal_reason = "writer_timeout"
        self._drain_result(None)
        self.log.info(
            "LIVE_EVIDENCE_REVIEW_STOPPED"
            f" | state={self._state} | reason={self._terminal_reason or 'none'}"
            f" | counters={self._collector.counters}",
        )

    def on_dispose(self) -> None:
        self._writer.close(0.0)

    def _qualifies(self, bar: CompletedBarInput) -> bool:
        return (
            bar.instrument_id == self._instrument_id
            and bar.analytical_profile_id == self._profile_id
            and bar.analytical_profile_version == self._profile_version
            and bar.bar_specification == self._bar_specification
            and bar.complete
            and bar.source in {CompletedBarSource.LIVE_NATIVE, CompletedBarSource.LIVE_AGGREGATE}
        )

    def _freeze(self, _event) -> None:  # noqa: ANN001
        if self._state != "COALESCING" or self._trigger_bar is None or self._readiness is None:
            return
        frozen_at_ns = self.clock.timestamp_ns()
        if self._expected_freeze_ns is None or frozen_at_ns < self._expected_freeze_ns:
            self._cancel_capture_timers()
            self._fail("CAPTURE_CLOCK_INVARIANT_VIOLATION", "freeze_before_expected_time")
            return
        self._collector.freeze()
        if self._collector.has_conflicts:
            self._fail("CANONICAL_CONFLICT", "collector_conflict")
            return
        payload = build_projection_payload(
            run_id=self._run_id,
            frozen_at_ns=frozen_at_ns,
            trigger_bar=self._trigger_bar,
            readiness={
                "system_state": self._readiness.system_state,
                "observed_watchlist_count": self._readiness.observed_watchlist_count,
                "expected_watchlist_count": self._readiness.expected_watchlist_count,
                "historical_state_counts": dict(self._readiness.historical_state_counts),
                "completed_at_ns": self._readiness.completed_at_ns,
                "is_ready": self._readiness.is_ready,
            },
            inventory=self._inventory,
            collector=self._collector,
            capture_policy=self._capture_policy,
            capture_timing={
                "trigger_received_at_ns": self._trigger_received_at_ns,
                "trigger_interval_end_ns": self._trigger_bar.interval_end_ns,
                "temporal_disposition": self._trigger_temporal_disposition,
                "coalescing_started_ns": self._coalescing_started_ns,
                "expected_freeze_ns": self._expected_freeze_ns,
                "actual_frozen_at_ns": frozen_at_ns,
                "freeze_lateness_ns": frozen_at_ns - self._expected_freeze_ns,
            },
        )
        self._state = "FROZEN"
        if not self._writer.submit(payload):
            self._fail("OUTPUT_FAILED", "writer_rejected")
            return
        self._state = "OUTPUT_PENDING"
        self.log.info(
            "LIVE_EVIDENCE_REVIEW_CAPTURE_FROZEN"
            f" | capture_id={payload['capture_id']} | frozen_at_ns={frozen_at_ns}",
        )

    def _drain_result(self, _event) -> None:  # noqa: ANN001
        try:
            state, detail = self._writer.results.get_nowait()
        except Empty:
            return
        self._state = state
        self._terminal_reason = detail
        self.log.info(f"LIVE_EVIDENCE_REVIEW_{state} | detail={detail}")

    def _on_readiness_deadline(self, _event) -> None:  # noqa: ANN001
        if self._state == "WAITING_FOR_OPERATIONAL_COMPLETION":
            self._fail("READINESS_NOT_OBSERVED", "deadline")

    def _on_live_bar_deadline(self, _event) -> None:  # noqa: ANN001
        if self._state == "WAITING_FOR_LIVE_ES_5M":
            self._fail("NO_QUALIFYING_LIVE_BAR", "deadline")

    def _on_trigger_interval_end(self, _event) -> None:  # noqa: ANN001
        if self._state != "WAITING_FOR_TRIGGER_INTERVAL_END" or self._trigger_bar is None:
            return
        now_ns = self.clock.timestamp_ns()
        if now_ns < self._trigger_bar.interval_end_ns:
            self._cancel_capture_timers()
            self._fail("CAPTURE_CLOCK_INVARIANT_VIOLATION", "interval_end_callback_was_early")
            return
        self._start_coalescing(now_ns)

    def _start_coalescing(self, now_ns: int) -> None:
        if self._trigger_bar is None or self._state not in {
            "WAITING_FOR_LIVE_ES_5M",
            "WAITING_FOR_TRIGGER_INTERVAL_END",
        }:
            return
        if now_ns < self._trigger_bar.interval_end_ns:
            self._fail("CAPTURE_CLOCK_INVARIANT_VIOLATION", "coalescing_before_interval_end")
            return
        self._state = "COALESCING"
        self._coalescing_started_ns = now_ns
        self._expected_freeze_ns = now_ns + self._coalescing_ns
        self.clock.set_time_alert_ns(
            _FREEZE_ALERT,
            self._expected_freeze_ns,
            callback=self._freeze,
            allow_past=False,
        )

    def _trigger_revision_changed(self, bar: CompletedBarInput) -> bool:
        trigger = self._trigger_bar
        return bool(
            trigger is not None
            and self._state in {"WAITING_FOR_TRIGGER_INTERVAL_END", "COALESCING"}
            and self._qualifies(bar)
            and bar.interval_end_ns == trigger.interval_end_ns
            and bar.revision != trigger.revision
        )

    def _cancel_capture_timers(self) -> None:
        self._cancel_timer(_TRIGGER_INTERVAL_END)
        self._cancel_timer(_FREEZE_ALERT)

    def _fail(self, state: str, detail: str) -> None:
        for timer_name in (
            _READINESS_DEADLINE,
            _LIVE_BAR_DEADLINE,
            _TRIGGER_INTERVAL_END,
            _FREEZE_ALERT,
        ):
            self._cancel_timer(timer_name)
        self._state = state
        self._terminal_reason = detail
        self.log.error(f"LIVE_EVIDENCE_REVIEW_{state} | detail={detail}")

    def _cancel_timer(self, name: str) -> None:
        if name in self.clock.timer_names():
            self.clock.cancel_timer(name)


_READINESS_SIGNALS = (
    SYSTEM_HEALTH_SIGNAL,
    WATCHLIST_MEMBERSHIP_SIGNAL,
    WATCHLIST_LIFECYCLE_SIGNAL,
    HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
    HISTORICAL_READINESS_SIGNAL,
)


def _accept_readiness(
    projection: OperationalReadinessProjection,
    signal: Signal,
) -> OperationalReadinessSnapshot | None:
    if signal.name == SYSTEM_HEALTH_SIGNAL:
        return projection.accept_system_health(SystemHealthEvent.from_signal_value(signal.value))
    if signal.name == WATCHLIST_MEMBERSHIP_SIGNAL:
        event = WatchlistMembershipEvent.from_signal_value(signal.value)
        return projection.accept_membership(event)
    if signal.name == WATCHLIST_LIFECYCLE_SIGNAL:
        return projection.accept_lifecycle(WatchlistLifecycleEvent.from_signal_value(signal.value))
    if signal.name == HISTORICAL_DEPENDENCY_DEMAND_SIGNAL:
        event = HistoricalDependencyDemandEvent.from_signal_value(signal.value)
        return projection.accept_demand(event)
    return projection.accept_readiness(HistoricalReadinessEvent.from_signal_value(signal.value))


def _capture_schedule(
    received_at_ns: int,
    interval_end_ns: int,
    coalescing_ns: int,
) -> tuple[str, int, int]:
    if min(received_at_ns, interval_end_ns, coalescing_ns) < 0:
        raise ValueError("capture timing values must be non-negative")
    eligible_at_ns = max(received_at_ns, interval_end_ns)
    disposition = (
        "DEFERRED_TO_INTERVAL_END"
        if received_at_ns < interval_end_ns
        else "IMMEDIATE_AT_OR_AFTER_INTERVAL_END"
    )
    return disposition, eligible_at_ns, eligible_at_ns + coalescing_ns
