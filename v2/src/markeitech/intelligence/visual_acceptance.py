from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Thread
from time import monotonic
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
)
from markeitech.intelligence.entities import ENTITY_REVISION_TYPE_NAME, EntityRevision
from markeitech.intelligence.metrics import METRIC_VALUE_TYPE_NAME, MetricValue
from markeitech.system.discord import (
    OperationalReadinessProjection,
    OperationalReadinessSnapshot,
)
from markeitech.system.messages import (
    SYSTEM_HEALTH_SIGNAL,
    WATCHLIST_LIFECYCLE_SIGNAL,
    WATCHLIST_MEMBERSHIP_SIGNAL,
    SystemHealthEvent,
    WatchlistLifecycleEvent,
    WatchlistMembershipEvent,
)

_REFRESH_TIMER = "visual-acceptance-refresh"
_RESULT_TIMER = "visual-acceptance-results"
_RESULT_POLL_INTERVAL_NS = 1_000_000_000
_STOP = object()


@dataclass(frozen=True, slots=True)
class AnnotationExpectation:
    instrument_id: str
    horizon: str
    bar_specification: str | None
    entity_types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VisualAcceptanceSnapshot:
    runtime_name: str
    generated_at_ns: int
    refresh_interval_ms: int
    readiness: OperationalReadinessSnapshot
    instrument_ids: tuple[str, ...]
    bar_specifications: tuple[str, ...]
    view_windows_ms: tuple[tuple[str, int], ...]
    horizon_selectors: tuple[tuple[str, str], ...]
    selected_metric_prefixes: tuple[tuple[str, tuple[str, ...]], ...]
    annotation_expectations: tuple[AnnotationExpectation, ...]
    bars: tuple[CompletedBarInput, ...]
    metrics: tuple[MetricValue, ...]
    entity_revisions: tuple[EntityRevision, ...]


class VisualAcceptanceCollector:
    def __init__(
        self,
        *,
        instrument_ids: tuple[str, ...],
        bar_specifications: tuple[str, ...],
        maximum_bars_per_series: int,
        maximum_metric_values: int,
        maximum_entity_revisions: int,
    ) -> None:
        if not instrument_ids or not bar_specifications:
            raise ValueError("visual acceptance requires instruments and bar specifications")
        for value, label in (
            (maximum_bars_per_series, "maximum_bars_per_series"),
            (maximum_metric_values, "maximum_metric_values"),
            (maximum_entity_revisions, "maximum_entity_revisions"),
        ):
            if value <= 0:
                raise ValueError(f"{label} must be positive")
        self._instrument_ids = frozenset(instrument_ids)
        self._bar_specifications = frozenset(bar_specifications)
        self._maximum_bars_per_series = maximum_bars_per_series
        self._maximum_metric_values = maximum_metric_values
        self._maximum_entity_revisions = maximum_entity_revisions
        self._bars: dict[tuple[str, str], OrderedDict[int, CompletedBarInput]] = {}
        self._metrics: OrderedDict[tuple[object, ...], MetricValue] = OrderedDict()
        self._entity_revisions: deque[EntityRevision] = deque()
        self._entity_revision_keys: set[tuple[str, int]] = set()
        self.accepted_bars = 0
        self.accepted_metrics = 0
        self.accepted_entity_revisions = 0
        self.ignored = 0

    def accept_bar(self, bar: CompletedBarInput) -> bool:
        if (
            bar.instrument_id not in self._instrument_ids
            or bar.bar_specification not in self._bar_specifications
        ):
            self.ignored += 1
            return False
        series = self._bars.setdefault(
            (bar.instrument_id, bar.bar_specification),
            OrderedDict(),
        )
        existing = series.get(bar.interval_end_ns)
        if existing is not None:
            if bar.revision <= existing.revision:
                return False
            del series[bar.interval_end_ns]
        series[bar.interval_end_ns] = bar
        while len(series) > self._maximum_bars_per_series:
            series.popitem(last=False)
        self.accepted_bars += 1
        return True

    def accept_metric(self, metric: MetricValue) -> bool:
        if metric.instrument_id not in self._instrument_ids:
            self.ignored += 1
            return False
        key = (
            metric.instrument_id,
            metric.metric_id,
            metric.metric_version,
            metric.parameter_version,
            metric.session_id,
        )
        existing = self._metrics.get(key)
        if existing is not None and metric.revision <= existing.revision:
            return False
        if existing is not None:
            del self._metrics[key]
        self._metrics[key] = metric
        while len(self._metrics) > self._maximum_metric_values:
            self._metrics.popitem(last=False)
        self.accepted_metrics += 1
        return True

    def accept_entity_revision(self, revision: EntityRevision) -> bool:
        if revision.identity.instrument_id not in self._instrument_ids:
            self.ignored += 1
            return False
        key = (revision.entity_id, revision.revision)
        if key in self._entity_revision_keys:
            return False
        if len(self._entity_revisions) >= self._maximum_entity_revisions:
            removed = self._entity_revisions.popleft()
            self._entity_revision_keys.remove((removed.entity_id, removed.revision))
        self._entity_revisions.append(revision)
        self._entity_revision_keys.add(key)
        self.accepted_entity_revisions += 1
        return True

    def snapshot(
        self,
        *,
        runtime_name: str,
        generated_at_ns: int,
        refresh_interval_ms: int,
        readiness: OperationalReadinessSnapshot,
        instrument_ids: tuple[str, ...],
        bar_specifications: tuple[str, ...],
        view_windows_ms: tuple[tuple[str, int], ...],
        horizon_selectors: tuple[tuple[str, str], ...],
        selected_metric_prefixes: tuple[tuple[str, tuple[str, ...]], ...],
        annotation_expectations: tuple[AnnotationExpectation, ...],
    ) -> VisualAcceptanceSnapshot:
        bars = tuple(
            bar
            for key in sorted(self._bars)
            for bar in self._bars[key].values()
        )
        return VisualAcceptanceSnapshot(
            runtime_name=runtime_name,
            generated_at_ns=generated_at_ns,
            refresh_interval_ms=refresh_interval_ms,
            readiness=readiness,
            instrument_ids=instrument_ids,
            bar_specifications=bar_specifications,
            view_windows_ms=view_windows_ms,
            horizon_selectors=horizon_selectors,
            selected_metric_prefixes=selected_metric_prefixes,
            annotation_expectations=annotation_expectations,
            bars=bars,
            metrics=tuple(self._metrics.values()),
            entity_revisions=tuple(self._entity_revisions),
        )


@dataclass(frozen=True, slots=True)
class VisualRenderResult:
    rendered: bool
    generated_at_ns: int
    output_path: str | None = None
    artifact_count: int = 0
    error_code: str | None = None


class VisualRenderWorker:
    def __init__(self, output_directory: Path, *, queue_capacity: int = 2) -> None:
        if queue_capacity <= 0:
            raise ValueError("queue_capacity must be positive")
        self._output_directory = output_directory
        self._pending: Queue[VisualAcceptanceSnapshot | object] = Queue(
            maxsize=queue_capacity,
        )
        self.results: Queue[VisualRenderResult] = Queue()
        self._closed = False
        self._stopped = False
        self._thread = Thread(
            target=self._run,
            name="markeitech-visual-acceptance",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def submit(self, snapshot: VisualAcceptanceSnapshot) -> bool:
        if self._closed:
            return False
        try:
            self._pending.put_nowait(snapshot)
            return True
        except Full:
            try:
                discarded = self._pending.get_nowait()
            except Empty:
                return False
            else:
                self._pending.task_done()
                if discarded is _STOP:
                    return False
            try:
                self._pending.put_nowait(snapshot)
            except Full:
                return False
            return True

    def close(self, timeout_seconds: float = 30.0) -> bool:
        if self._stopped:
            return True
        self._closed = True
        deadline = monotonic() + timeout_seconds
        try:
            self._pending.put(_STOP, timeout=max(0.0, deadline - monotonic()))
        except Full:
            return False
        self._thread.join(timeout=max(0.0, deadline - monotonic()))
        self._stopped = not self._thread.is_alive()
        return self._stopped

    def _run(self) -> None:
        from markeitech.intelligence.visual_acceptance_plotly import render_visual_acceptance

        while True:
            item = self._pending.get()
            try:
                if item is _STOP:
                    return
                assert isinstance(item, VisualAcceptanceSnapshot)
                try:
                    artifact_paths = render_visual_acceptance(item, self._output_directory)
                except Exception as exc:  # Rendering must not affect the live runtime.
                    self.results.put(
                        VisualRenderResult(
                            rendered=False,
                            generated_at_ns=item.generated_at_ns,
                            error_code=type(exc).__name__,
                        ),
                    )
                else:
                    self.results.put(
                        VisualRenderResult(
                            rendered=True,
                            generated_at_ns=item.generated_at_ns,
                            output_path=str(self._output_directory),
                            artifact_count=len(artifact_paths),
                        ),
                    )
            finally:
                self._pending.task_done()


class VisualAcceptanceActorConfig(DataActorConfig):
    def __new__(
        cls,
        runtime_name: str,
        output_directory: str,
        refresh_interval_ms: int,
        maximum_bars_per_series: int,
        maximum_metric_values: int,
        maximum_entity_revisions: int,
        instrument_ids: list[str],
        bar_specifications: list[str],
        view_windows_ms: dict[str, int],
        horizon_selectors: dict[str, str],
        selected_metric_prefixes: dict[str, list[str]],
        annotation_expectations: list[dict[str, Any]],
        actor_id: str | ActorId = "VISUAL-ACCEPTANCE",
    ) -> VisualAcceptanceActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.runtime_name = runtime_name
        obj.output_directory = output_directory
        obj.refresh_interval_ms = refresh_interval_ms
        obj.maximum_bars_per_series = maximum_bars_per_series
        obj.maximum_metric_values = maximum_metric_values
        obj.maximum_entity_revisions = maximum_entity_revisions
        obj.instrument_ids = instrument_ids
        obj.bar_specifications = bar_specifications
        obj.view_windows_ms = view_windows_ms
        obj.horizon_selectors = horizon_selectors
        obj.selected_metric_prefixes = selected_metric_prefixes
        obj.annotation_expectations = annotation_expectations
        return obj


class VisualAcceptanceActor(DataActor):
    def __init__(self, config: VisualAcceptanceActorConfig) -> None:
        super().__init__(config)
        self._runtime_name = config.runtime_name
        self._output_directory = Path(config.output_directory)
        self._refresh_interval_ns = config.refresh_interval_ms * 1_000_000
        self._instrument_ids = tuple(config.instrument_ids)
        self._bar_specifications = tuple(config.bar_specifications)
        self._view_windows_ms = tuple(sorted(config.view_windows_ms.items()))
        self._horizon_selectors = tuple(sorted(config.horizon_selectors.items()))
        self._selected_metric_prefixes = tuple(
            sorted(
                (selector, tuple(prefixes))
                for selector, prefixes in config.selected_metric_prefixes.items()
            ),
        )
        self._annotation_expectations = tuple(
            AnnotationExpectation(
                instrument_id=item["instrument_id"],
                horizon=item["horizon"],
                bar_specification=item.get("bar_specification"),
                entity_types=tuple(item["entity_types"]),
            )
            for item in config.annotation_expectations
        )
        self._collector = VisualAcceptanceCollector(
            instrument_ids=self._instrument_ids,
            bar_specifications=self._bar_specifications,
            maximum_bars_per_series=config.maximum_bars_per_series,
            maximum_metric_values=config.maximum_metric_values,
            maximum_entity_revisions=config.maximum_entity_revisions,
        )
        self._readiness_projection = OperationalReadinessProjection()
        self._readiness: OperationalReadinessSnapshot | None = None
        self._worker = VisualRenderWorker(self._output_directory)
        self._completed_bar_type = DataType(COMPLETED_BAR_INPUT_TYPE_NAME)
        self._metric_type = DataType(METRIC_VALUE_TYPE_NAME)
        self._entity_revision_type = DataType(ENTITY_REVISION_TYPE_NAME)
        self._dirty = False
        self._submitted = 0
        self._rendered = 0
        self._failed = 0

    def on_start(self) -> None:
        self._worker.start()
        self.subscribe_data(self._completed_bar_type)
        self.subscribe_data(self._metric_type)
        self.subscribe_data(self._entity_revision_type)
        for signal_name in (
            SYSTEM_HEALTH_SIGNAL,
            WATCHLIST_MEMBERSHIP_SIGNAL,
            WATCHLIST_LIFECYCLE_SIGNAL,
            HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
            HISTORICAL_READINESS_SIGNAL,
        ):
            self.subscribe_signal(signal_name)
        self.clock.set_timer_ns(
            _RESULT_TIMER,
            _RESULT_POLL_INTERVAL_NS,
            callback=self._drain_results,
        )
        self.log.info(
            "VISUAL_ACCEPTANCE_READY"
            f" | instruments={len(self._instrument_ids)}"
            f" | horizons={len(self._bar_specifications)}"
            f" | output={self._output_directory}",
        )

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        accepted = False
        if isinstance(payload, CompletedBarInput):
            accepted = self._collector.accept_bar(payload)
        elif isinstance(payload, MetricValue):
            accepted = self._collector.accept_metric(payload)
        elif isinstance(payload, EntityRevision):
            accepted = self._collector.accept_entity_revision(payload)
        if accepted:
            self._dirty = True

    def on_signal(self, signal: Signal) -> None:
        try:
            if signal.name == SYSTEM_HEALTH_SIGNAL:
                snapshot = self._readiness_projection.accept_system_health(
                    SystemHealthEvent.from_signal_value(signal.value),
                )
            elif signal.name == WATCHLIST_MEMBERSHIP_SIGNAL:
                snapshot = self._readiness_projection.accept_membership(
                    WatchlistMembershipEvent.from_signal_value(signal.value),
                )
            elif signal.name == WATCHLIST_LIFECYCLE_SIGNAL:
                snapshot = self._readiness_projection.accept_lifecycle(
                    WatchlistLifecycleEvent.from_signal_value(signal.value),
                )
            elif signal.name == HISTORICAL_DEPENDENCY_DEMAND_SIGNAL:
                snapshot = self._readiness_projection.accept_demand(
                    HistoricalDependencyDemandEvent.from_signal_value(signal.value),
                )
            elif signal.name == HISTORICAL_READINESS_SIGNAL:
                snapshot = self._readiness_projection.accept_readiness(
                    HistoricalReadinessEvent.from_signal_value(signal.value),
                )
            else:
                return
        except ValueError as exc:
            self.log.error(
                "VISUAL_ACCEPTANCE_READINESS_REJECTED"
                f" | signal={signal.name} | error={type(exc).__name__}",
            )
            return
        if snapshot is None:
            return
        self._readiness = snapshot
        self._dirty = True
        self._submit_snapshot("operational_readiness")
        self.clock.set_timer_ns(
            _REFRESH_TIMER,
            self._refresh_interval_ns,
            callback=self._refresh,
        )

    def on_stop(self) -> None:
        if self._readiness is not None and self._dirty:
            self._submit_snapshot("shutdown")
        for signal_name in (
            SYSTEM_HEALTH_SIGNAL,
            WATCHLIST_MEMBERSHIP_SIGNAL,
            WATCHLIST_LIFECYCLE_SIGNAL,
            HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
            HISTORICAL_READINESS_SIGNAL,
        ):
            self.unsubscribe_signal(signal_name)
        self.unsubscribe_data(self._completed_bar_type)
        self.unsubscribe_data(self._metric_type)
        self.unsubscribe_data(self._entity_revision_type)
        for timer_name in (_REFRESH_TIMER, _RESULT_TIMER):
            if timer_name in self.clock.timer_names():
                self.clock.cancel_timer(timer_name)
        if not self._worker.close():
            self.log.error("VISUAL_ACCEPTANCE_WORKER_TIMEOUT")
        self._drain_results(None)
        self.log.info(
            "VISUAL_ACCEPTANCE_STOPPED"
            f" | bars={self._collector.accepted_bars}"
            f" | metrics={self._collector.accepted_metrics}"
            f" | entity_revisions={self._collector.accepted_entity_revisions}"
            f" | ignored={self._collector.ignored}"
            f" | submitted={self._submitted}"
            f" | rendered={self._rendered}"
            f" | failed={self._failed}",
        )

    def on_dispose(self) -> None:
        self._worker.close()

    def _refresh(self, _event) -> None:  # noqa: ANN001
        self._drain_results(None)
        if self._readiness is not None and self._dirty:
            self._submit_snapshot("evidence_refresh")

    def _submit_snapshot(self, reason: str) -> None:
        assert self._readiness is not None
        snapshot = self._collector.snapshot(
            runtime_name=self._runtime_name,
            generated_at_ns=max(self.clock.timestamp_ns(), self._readiness.completed_at_ns),
            refresh_interval_ms=self._refresh_interval_ns // 1_000_000,
            readiness=self._readiness,
            instrument_ids=self._instrument_ids,
            bar_specifications=self._bar_specifications,
            view_windows_ms=self._view_windows_ms,
            horizon_selectors=self._horizon_selectors,
            selected_metric_prefixes=self._selected_metric_prefixes,
            annotation_expectations=self._annotation_expectations,
        )
        if not self._worker.submit(snapshot):
            self.log.error(f"VISUAL_ACCEPTANCE_DROPPED | reason={reason}")
            return
        self._dirty = False
        self._submitted += 1
        self.log.info(
            "VISUAL_ACCEPTANCE_SUBMITTED"
            f" | reason={reason}"
            f" | bars={len(snapshot.bars)}"
            f" | metrics={len(snapshot.metrics)}"
            f" | entity_revisions={len(snapshot.entity_revisions)}",
        )

    def _drain_results(self, _event) -> None:  # noqa: ANN001
        while True:
            try:
                result = self._worker.results.get_nowait()
            except Empty:
                return
            if result.rendered:
                self._rendered += 1
                self.log.info(
                    "VISUAL_ACCEPTANCE_RENDERED"
                    f" | generated_at_ns={result.generated_at_ns}"
                    f" | output={result.output_path}"
                    f" | pngs={result.artifact_count}",
                )
            else:
                self._failed += 1
                self.log.error(
                    "VISUAL_ACCEPTANCE_RENDER_FAILED"
                    f" | generated_at_ns={result.generated_at_ns}"
                    f" | error={result.error_code}",
                )
