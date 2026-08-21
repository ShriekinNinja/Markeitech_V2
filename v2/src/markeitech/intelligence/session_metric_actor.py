from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, CustomData, DataType

from markeitech.acquisition import (
    HISTORICAL_BATCH_TYPE_NAME,
    HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
    HISTORICAL_READINESS_SIGNAL,
    FeedKind,
    FeedRequirement,
    HistoricalBatch,
    HistoricalDependencyDemandEvent,
    HistoricalReadinessEvent,
    HistoricalWindow,
    NautilusSubscriptionPort,
)
from markeitech.intelligence.completed_bars import (
    BarAdmissionStatus,
    BarConflictPolicy,
    CompletedBarInput,
    CompletedBarLedger,
    CompletedBarSource,
    aggregate_completed_bars,
)
from markeitech.intelligence.messages import (
    EVIDENCE_HEALTH_SIGNAL,
    EVIDENCE_HEALTH_SNAPSHOT_REQUEST_SIGNAL,
    EVIDENCE_HEALTH_SNAPSHOT_SIGNAL,
    SESSION_STATE_SIGNAL,
    EvidenceHealthEvent,
    EvidenceHealthSnapshot,
    EvidenceHealthSnapshotRequest,
    SessionStateEvent,
)
from markeitech.intelligence.metrics import (
    METRIC_VALUE_TYPE_NAME,
    MetricFidelity,
    MetricHealth,
    MetricRegistry,
)
from markeitech.intelligence.session import SessionCalendar, definition_from_config
from markeitech.intelligence.session_measurements import (
    CompletedBarCatalogPolicy,
    calculate_completed_bar_metrics,
    completed_bar_metric_definitions,
)
from markeitech.system.messages import (
    ACQUISITION_STREAM_SIGNAL,
    ANALYTICAL_DEMAND_SIGNAL,
    AcquisitionStreamEvent,
    AnalyticalDemandEvent,
)

_DEMAND_RETRY_TIMER = "session-metrics-demand-retry"
_EVIDENCE_RETRY_TIMER = "session-metrics-evidence-retry"
_HISTORICAL_DEMAND_DELAY_NS = 1_000_000
_HISTORICAL_DEMAND_ALERT = "session-metrics-historical-demand"


class SessionMetricsActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_ids: list[str],
        instrument_calendars: dict[str, str],
        calendars: list[dict[str, object]],
        profiles: list[dict[str, object]],
        profile_bindings: dict[str, str],
        parameter_version: int,
        parameter_source: str,
        parameter_effective_from_ns: int,
        conflict_policy: str,
        demand_retry_interval_ms: int,
        evidence_snapshot_retry_interval_ms: int,
        priority: int,
        completed_bars: dict[str, object],
        actor_id: str | ActorId = "SESSION-METRICS",
    ) -> SessionMetricsActorConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.instrument_ids = tuple(instrument_ids)
        obj.instrument_calendars = dict(instrument_calendars)
        obj.calendars = tuple(calendars)
        obj.profiles = tuple(profiles)
        obj.profile_bindings = dict(profile_bindings)
        obj.parameter_version = parameter_version
        obj.parameter_source = parameter_source
        obj.parameter_effective_from_ns = parameter_effective_from_ns
        obj.conflict_policy = conflict_policy
        obj.demand_retry_interval_ms = demand_retry_interval_ms
        obj.evidence_snapshot_retry_interval_ms = evidence_snapshot_retry_interval_ms
        obj.priority = priority
        obj.completed_bars = dict(completed_bars)
        return obj


class SessionMetricsActor(DataActor):
    """Converges bounded historical and live bars into foundation metrics."""

    def __init__(self, config: SessionMetricsActorConfig) -> None:
        super().__init__(config)
        if not config.instrument_ids or len(set(config.instrument_ids)) != len(
            config.instrument_ids,
        ):
            raise ValueError("session metrics require unique configured instruments")
        self._instrument_ids = tuple(sorted(config.instrument_ids))
        self._instrument_set = frozenset(self._instrument_ids)
        self._instrument_calendars = dict(config.instrument_calendars)
        self._calendars = {
            value["calendar_id"]: SessionCalendar(definition_from_config(dict(value)))
            for value in config.calendars
        }
        self._profiles = {value["profile_id"]: dict(value) for value in config.profiles}
        self._profile_bindings = dict(config.profile_bindings)
        self._parameter_version = config.parameter_version
        self._parameter_source = config.parameter_source
        self._parameter_effective_from_ns = config.parameter_effective_from_ns
        completed = config.completed_bars
        self._live_selector = str(completed["live_selector"])
        self._historical_selector = str(completed["historical_selector"])
        self._historical_window = str(completed["historical_window"])
        self._minimum_historical_observations = int(
            completed["minimum_historical_observations"],
        )
        self._maximum_historical_observations = int(
            completed["maximum_historical_observations"],
        )
        self._target_interval_seconds = int(completed["calculation_interval_seconds"])
        self._target_interval_ns = self._target_interval_seconds * 1_000_000_000
        self._timestamp_policy = str(completed["timestamp_policy"])
        self._maximum_retained = int(completed["maximum_retained_observations"])
        self._priority = config.priority
        policy = CompletedBarCatalogPolicy(
            live_selector=self._live_selector,
            historical_selector=self._historical_selector,
            historical_window=HistoricalWindow(self._historical_window),
            minimum_historical_observations=self._minimum_historical_observations,
            maximum_historical_observations=self._maximum_historical_observations,
            calculation_interval_seconds=self._target_interval_seconds,
            minimum_interval_seconds=int(completed["minimum_interval_seconds"]),
            maximum_interval_seconds=int(completed["maximum_interval_seconds"]),
            interval_step_seconds=int(completed["interval_step_seconds"]),
            interval_dynamic=bool(completed["interval_dynamic"]),
            aggregation_boundary_policy=str(completed["aggregation_boundary_policy"]),
            revision_policy=str(completed["revision_policy"]),
            parameter_source=self._parameter_source,
            priority=self._priority,
            maximum_retained_observations=self._maximum_retained,
            maximum_output_age_ms=int(completed["maximum_output_age_ms"]),
        )
        self._registry = MetricRegistry(completed_bar_metric_definitions(policy))
        self._port = NautilusSubscriptionPort(self)
        self._metric_type = DataType(METRIC_VALUE_TYPE_NAME)
        self._batch_type = DataType(HISTORICAL_BATCH_TYPE_NAME)
        self._demand_retry_interval_ns = config.demand_retry_interval_ms * 1_000_000
        self._evidence_retry_interval_ns = (
            config.evidence_snapshot_retry_interval_ms * 1_000_000
        )
        if config.conflict_policy != BarConflictPolicy.REJECT_CONFLICT.value:
            raise ValueError("session metrics support reject_conflict only")
        self._ledgers = {
            instrument_id: CompletedBarLedger(
                maximum_observations=self._maximum_retained,
                conflict_policy=BarConflictPolicy.REJECT_CONFLICT,
            )
            for instrument_id in self._instrument_ids
        }
        self._source_buckets: dict[tuple[str, int], dict[int, CompletedBarInput]] = {}
        self._session_states: dict[str, SessionStateEvent] = {}
        self._evidence: dict[str, EvidenceHealthEvent] = {}
        self._attached: set[str] = set()
        self._acknowledged_demands: set[str] = set()
        self._historical_readiness: dict[str, str] = {}
        self._revisions: defaultdict[str, int] = defaultdict(int)
        self._counts: defaultdict[str, int] = defaultdict(int)
        self._live_demand_ids = {
            instrument_id: f"metric:session:{instrument_id}:bars:{self._live_selector}"
            for instrument_id in self._instrument_ids
        }
        self._historical_demand_ids = {
            instrument_id: (
                f"metric:session:{instrument_id}:historical:{self._historical_selector}"
            )
            for instrument_id in self._instrument_ids
        }

    def on_start(self) -> None:
        for signal_name in (
            ACQUISITION_STREAM_SIGNAL,
            HISTORICAL_READINESS_SIGNAL,
            SESSION_STATE_SIGNAL,
            EVIDENCE_HEALTH_SIGNAL,
            EVIDENCE_HEALTH_SNAPSHOT_SIGNAL,
        ):
            self.subscribe_signal(signal_name)
        self.subscribe_data(self._batch_type)
        self._attach_consumers()
        self._publish_live_demands(None)
        self._request_evidence_snapshot(None)
        self.clock.set_time_alert_ns(
            _HISTORICAL_DEMAND_ALERT,
            self.clock.timestamp_ns() + _HISTORICAL_DEMAND_DELAY_NS,
            callback=self._publish_historical_demands,
        )
        self.clock.set_timer_ns(
            _DEMAND_RETRY_TIMER,
            self._demand_retry_interval_ns,
            callback=self._publish_live_demands,
        )
        self.clock.set_timer_ns(
            _EVIDENCE_RETRY_TIMER,
            self._evidence_retry_interval_ns,
            callback=self._request_evidence_snapshot,
        )

    def on_signal(self, signal: Signal) -> None:
        if signal.name == ACQUISITION_STREAM_SIGNAL:
            self._observe_acquisition(signal.value)
        elif signal.name == HISTORICAL_READINESS_SIGNAL:
            self._observe_historical_readiness(signal.value)
        elif signal.name == SESSION_STATE_SIGNAL:
            self._observe_session_state(signal.value)
        elif signal.name == EVIDENCE_HEALTH_SIGNAL:
            self._observe_evidence(signal.value)
        elif signal.name == EVIDENCE_HEALTH_SNAPSHOT_SIGNAL:
            self._observe_evidence_snapshot(signal.value)

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if not isinstance(payload, HistoricalBatch):
            return
        dependencies = {
            dependency.consumer_id for dependency in payload.request.dependencies
        }
        if str(self.actor_id) not in dependencies:
            return
        if payload.request.instrument_id not in self._instrument_set:
            return
        if (
            payload.request.kind is not FeedKind.BARS
            or payload.request.selector != self._historical_selector
        ):
            return
        self._counts["historical_batches"] += 1
        for observation in payload.observations:
            self._process_provider_bar(
                observation,
                source=CompletedBarSource.HISTORICAL_PROVIDER,
                received_ns=payload.received_at_ns,
                evidence_ref=f"historical:{payload.request.request_id}",
            )

    def on_bar(self, bar) -> None:  # noqa: ANN001
        instrument_id = str(bar.bar_type.instrument_id)
        selector = str(bar.bar_type).removeprefix(f"{instrument_id}-")
        if instrument_id not in self._instrument_set or selector != self._live_selector:
            return
        self._counts["live_bars"] += 1
        evidence = self._evidence.get(instrument_id)
        evidence_ref = (
            f"signal:{EVIDENCE_HEALTH_SIGNAL}:{evidence.event_id}"
            if evidence is not None
            else f"evidence:{instrument_id}:bars:{self._live_selector}:pending"
        )
        self._process_provider_bar(
            bar,
            source=CompletedBarSource.LIVE_NATIVE,
            received_ns=max(int(bar.ts_init), self.clock.timestamp_ns()),
            evidence_ref=evidence_ref,
        )

    def on_stop(self) -> None:
        for timer_name in (
            _DEMAND_RETRY_TIMER,
            _EVIDENCE_RETRY_TIMER,
            _HISTORICAL_DEMAND_ALERT,
        ):
            if timer_name in self.clock.timer_names():
                self.clock.cancel_timer(timer_name)
        for instrument_id in reversed(self._instrument_ids):
            self.publish_signal(
                ANALYTICAL_DEMAND_SIGNAL,
                self._live_demand(instrument_id, "RELEASE").to_signal_value(),
            )
            if instrument_id in self._attached:
                self._port.unsubscribe(
                    FeedRequirement(instrument_id, FeedKind.BARS, self._live_selector),
                )
        for signal_name in (
            ACQUISITION_STREAM_SIGNAL,
            HISTORICAL_READINESS_SIGNAL,
            SESSION_STATE_SIGNAL,
            EVIDENCE_HEALTH_SIGNAL,
            EVIDENCE_HEALTH_SNAPSHOT_SIGNAL,
        ):
            self.unsubscribe_signal(signal_name)
        self.unsubscribe_data(self._batch_type)
        self.log.info(
            "SESSION_METRICS_STOPPED"
            f" | instruments={len(self._instrument_ids)}"
            f" | live_bars={self._counts['live_bars']}"
            f" | historical_batches={self._counts['historical_batches']}"
            f" | accepted={self._counts['accepted']}"
            f" | duplicates={self._counts['duplicates']}"
            f" | conflicts={self._counts['conflicts']}"
            f" | expired_partial_buckets={self._counts['expired_partial_buckets']}"
            f" | values={self._counts['values']}"
            f" | failures={self._counts['failures']}",
        )

    def _process_provider_bar(
        self,
        bar: object,
        *,
        source: CompletedBarSource,
        received_ns: int,
        evidence_ref: str,
    ) -> None:
        try:
            normalized = self._normalize(bar, source, received_ns, evidence_ref)
            if normalized.interval_ns == self._target_interval_ns:
                target = normalized
            elif normalized.interval_ns < self._target_interval_ns:
                target = self._accumulate(normalized)
                if target is None:
                    return
            else:
                raise ValueError("source interval exceeds target interval")
            self._admit_and_publish(target)
        except (ValueError, ArithmeticError, InvalidOperation) as exc:
            self._counts["failures"] += 1
            self.log.error(
                "SESSION_METRIC_BAR_REJECTED"
                f" | source={source.value} | error={type(exc).__name__} | reason={exc}",
            )

    def _normalize(
        self,
        bar: object,
        source: CompletedBarSource,
        received_ns: int,
        evidence_ref: str,
    ) -> CompletedBarInput:
        bar_type = bar.bar_type
        instrument_id = str(bar_type.instrument_id)
        selector = str(bar_type).removeprefix(f"{instrument_id}-")
        interval_ns = int(bar_type.spec.get_interval_ns())
        ts_event = int(bar.ts_event)
        if self._timestamp_policy == "interval_start":
            interval_start_ns = ts_event
            interval_end_ns = ts_event + interval_ns
        elif self._timestamp_policy == "interval_end":
            interval_start_ns = ts_event - interval_ns
            interval_end_ns = ts_event
        else:
            raise ValueError("unsupported timestamp policy")
        calendar_id = self._instrument_calendars[instrument_id]
        snapshot = self._calendar_snapshot(
            calendar_id,
            interval_end_ns - 1,
            use_current=source is not CompletedBarSource.HISTORICAL_PROVIDER,
        )
        if snapshot.trade_date is None:
            raise ValueError("calendar did not assign a trade date")
        profile_id = self._profile_bindings[instrument_id]
        profile = self._profiles[profile_id]
        evidence = self._evidence.get(instrument_id)
        health, fidelity = _source_quality(source, evidence)
        volume_supported = bool(profile["volume_supported"])
        volume = _decimal(bar.volume) if volume_supported else None
        missing_reasons = () if volume_supported else ("volume_unsupported",)
        normalized_ns = max(received_ns, self.clock.timestamp_ns())
        return CompletedBarInput(
            instrument_id=instrument_id,
            bar_specification=selector,
            calendar_id=calendar_id,
            analytical_profile_id=profile_id,
            analytical_profile_version=int(profile["version"]),
            trade_date=snapshot.trade_date,
            session_id=f"{calendar_id}:{snapshot.trade_date.isoformat()}:{snapshot.phase}",
            window_id="primary",
            interval_start_ns=interval_start_ns,
            interval_end_ns=interval_end_ns,
            open=_decimal(bar.open),
            high=_decimal(bar.high),
            low=_decimal(bar.low),
            close=_decimal(bar.close),
            volume=volume,
            source=source,
            observed_ts_ns=interval_end_ns,
            received_ts_ns=max(received_ns, interval_end_ns),
            normalized_ts_ns=max(normalized_ns, interval_end_ns),
            health=health,
            fidelity=fidelity,
            evidence_refs=(evidence_ref,),
            complete=True,
            missing_reasons=missing_reasons,
        )

    def _calendar_snapshot(
        self,
        calendar_id: str,
        timestamp_ns: int,
        *,
        use_current: bool,
    ):  # noqa: ANN202
        current = self._session_states.get(calendar_id) if use_current else None
        if current is not None and current.trade_date is not None:
            if current.phase == "CLOSED" or (
                current.phase_open_ns is not None
                and current.phase_close_ns is not None
                and current.phase_open_ns <= timestamp_ns < current.phase_close_ns
            ):
                return _snapshot_from_event(current)
        return self._calendars[calendar_id].evaluate(timestamp_ns)

    def _accumulate(self, bar: CompletedBarInput) -> CompletedBarInput | None:
        bucket_start_ns = bar.interval_start_ns - bar.interval_start_ns % self._target_interval_ns
        key = (bar.instrument_id, bucket_start_ns)
        bucket = self._source_buckets.setdefault(key, {})
        existing = bucket.get(bar.interval_start_ns)
        if existing is not None:
            if existing.equivalence_key != bar.equivalence_key:
                self._counts["conflicts"] += 1
            else:
                self._counts["duplicates"] += 1
            return None
        bucket[bar.interval_start_ns] = bar
        while len(self._source_buckets) > self._maximum_retained:
            oldest_key = min(self._source_buckets, key=lambda item: item[1])
            del self._source_buckets[oldest_key]
            self._counts["expired_partial_buckets"] += 1
        expected = self._target_interval_ns // bar.interval_ns
        if len(bucket) < expected:
            return None
        values = tuple(bucket[index] for index in sorted(bucket))
        del self._source_buckets[key]
        return aggregate_completed_bars(
            values,
            target_bar_specification=self._historical_selector,
            target_interval_seconds=self._target_interval_seconds,
            normalized_ts_ns=max(item.normalized_ts_ns for item in values),
        )

    def _admit_and_publish(self, bar: CompletedBarInput) -> None:
        ledger = self._ledgers[bar.instrument_id]
        admission = ledger.admit(bar)
        if admission.status is BarAdmissionStatus.DUPLICATE:
            self._counts["duplicates"] += 1
            return
        if admission.status is BarAdmissionStatus.CONFLICT:
            self._counts["conflicts"] += 1
            self.log.error(
                "SESSION_METRIC_BAR_CONFLICT"
                f" | instrument_id={bar.instrument_id}"
                f" | bar_specification={bar.bar_specification}"
                f" | interval_end_ns={bar.interval_end_ns}",
            )
            return
        self._counts["accepted"] += 1
        for target, prior in _recalculation_contexts(ledger.bars, admission.accepted.key):
            self._revisions[bar.instrument_id] += 1
            now_ns = max(self.clock.timestamp_ns(), target.normalized_ts_ns)
            values = calculate_completed_bar_metrics(
                target,
                prior_bar=prior,
                registry=self._registry,
                parameter_version=self._parameter_version,
                calculated_ts_ns=now_ns,
                published_ts_ns=now_ns,
                source=str(self.actor_id),
                revision=self._revisions[bar.instrument_id],
            )
            for value in values:
                self.publish_data(self._metric_type, CustomData(self._metric_type, value))
            self._counts["values"] += len(values)

    def _attach_consumers(self) -> None:
        for instrument_id in self._instrument_ids:
            if instrument_id in self._attached:
                continue
            try:
                self._port.subscribe(
                    FeedRequirement(instrument_id, FeedKind.BARS, self._live_selector),
                )
            except Exception as exc:  # noqa: BLE001
                self.log.error(
                    "SESSION_METRIC_CONSUMER_REGISTRATION_FAILED"
                    f" | instrument_id={instrument_id} | error={type(exc).__name__}",
                )
                continue
            self._attached.add(instrument_id)

    def _publish_live_demands(self, _event) -> None:  # noqa: ANN001
        self._attach_consumers()
        pending = [
            instrument_id
            for instrument_id, demand_id in self._live_demand_ids.items()
            if demand_id not in self._acknowledged_demands
        ]
        for instrument_id in pending:
            self.publish_signal(
                ANALYTICAL_DEMAND_SIGNAL,
                self._live_demand(instrument_id, "REQUEST").to_signal_value(),
            )
        if (
            not pending
            and len(self._attached) == len(self._instrument_ids)
            and _DEMAND_RETRY_TIMER in self.clock.timer_names()
        ):
            self.clock.cancel_timer(_DEMAND_RETRY_TIMER)

    def _publish_historical_demands(self, _event) -> None:  # noqa: ANN001
        now_ns = self.clock.timestamp_ns()
        for instrument_id in self._instrument_ids:
            demand = HistoricalDependencyDemandEvent(
                demand_id=self._historical_demand_ids[instrument_id],
                consumer_id=str(self.actor_id),
                capability_id="metric:completed-bar-foundation",
                capability_version=1,
                instrument_id=instrument_id,
                selector=self._historical_selector,
                window=self._historical_window,
                minimum_observations=self._minimum_historical_observations,
                maximum_observations=self._maximum_historical_observations,
                priority=self._priority,
                purpose="warm completed-bar foundation metrics",
                as_of_ns=now_ns,
                parameters={
                    "calculation_interval_seconds": self._target_interval_seconds,
                    "parameter_version": self._parameter_version,
                },
            )
            self.publish_signal(
                HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
                demand.to_signal_value(),
            )

    def _request_evidence_snapshot(self, _event) -> None:  # noqa: ANN001
        missing = tuple(
            instrument_id
            for instrument_id in self._instrument_ids
            if instrument_id not in self._evidence
        )
        if not missing:
            if _EVIDENCE_RETRY_TIMER in self.clock.timer_names():
                self.clock.cancel_timer(_EVIDENCE_RETRY_TIMER)
            return
        self.publish_signal(
            EVIDENCE_HEALTH_SNAPSHOT_REQUEST_SIGNAL,
            EvidenceHealthSnapshotRequest(
                requester=str(self.actor_id),
                instrument_ids=missing,
                feed_kind="bars",
                selector=self._live_selector,
            ).to_signal_value(),
        )

    def _observe_acquisition(self, value: str) -> None:
        try:
            event = AcquisitionStreamEvent.from_signal_value(value)
        except ValueError:
            return
        if event.feed_kind != "bars" or event.selector != self._live_selector:
            return
        demand_id = self._live_demand_ids.get(event.instrument_id)
        if demand_id is not None and (
            event.demand_id == demand_id or demand_id in event.consumer_ids
        ):
            self._acknowledged_demands.add(demand_id)

    def _observe_historical_readiness(self, value: str) -> None:
        try:
            event = HistoricalReadinessEvent.from_signal_value(value)
        except ValueError:
            return
        if event.consumer_id == str(self.actor_id):
            self._historical_readiness[event.instrument_id] = event.state

    def _observe_session_state(self, value: str) -> None:
        try:
            event = SessionStateEvent.from_signal_value(value)
        except ValueError:
            return
        if event.calendar_id in self._calendars:
            self._session_states[event.calendar_id] = event

    def _observe_evidence(self, value: str) -> None:
        try:
            event = EvidenceHealthEvent.from_signal_value(value)
        except ValueError:
            return
        self._retain_evidence(event)

    def _observe_evidence_snapshot(self, value: str) -> None:
        try:
            snapshot = EvidenceHealthSnapshot.from_signal_value(value)
        except ValueError:
            return
        if snapshot.requester != str(self.actor_id):
            return
        for event in snapshot.events:
            self._retain_evidence(event)

    def _retain_evidence(self, event: EvidenceHealthEvent) -> None:
        if (
            event.instrument_id in self._instrument_set
            and event.feed_kind == "bars"
            and event.selector == self._live_selector
        ):
            self._evidence[event.instrument_id] = event

    def _live_demand(self, instrument_id: str, action: str) -> AnalyticalDemandEvent:
        return AnalyticalDemandEvent(
            demand_id=self._live_demand_ids[instrument_id],
            action=action,
            instrument_id=instrument_id,
            capability_id="metric:completed-bar-foundation",
            capability_version=1,
            feed_kind="bars",
            selector=self._live_selector,
            owner_id=str(self.actor_id),
            purpose="calculate completed-bar foundation metrics",
            priority=self._priority,
        )


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("bar value cannot be converted to Decimal") from exc


def _source_quality(
    source: CompletedBarSource,
    evidence: EvidenceHealthEvent | None,
) -> tuple[MetricHealth, MetricFidelity]:
    if source is CompletedBarSource.HISTORICAL_PROVIDER:
        return MetricHealth.READY, MetricFidelity.REPORTED
    if evidence is None:
        return MetricHealth.WARMING, MetricFidelity.PARTIAL
    health = {
        "HEALTHY": MetricHealth.READY,
        "DEGRADED": MetricHealth.DEGRADED,
        "STALE": MetricHealth.STALE,
        "UNAVAILABLE": MetricHealth.UNAVAILABLE,
        "UNSUPPORTED": MetricHealth.UNSUPPORTED,
        "DORMANT": MetricHealth.STALE,
        "NOT_EVALUATED": MetricHealth.WARMING,
    }.get(evidence.state, MetricHealth.FAILED)
    fidelity = MetricFidelity.DERIVED if health is MetricHealth.READY else MetricFidelity.PARTIAL
    return health, fidelity


def _recalculation_contexts(
    bars: tuple[CompletedBarInput, ...],
    admitted_key: tuple[str, str, int],
) -> tuple[tuple[CompletedBarInput, CompletedBarInput | None], ...]:
    """Return the admitted interval and any successor changed by its new prior close."""
    index = next((offset for offset, bar in enumerate(bars) if bar.key == admitted_key), None)
    if index is None:
        raise ValueError("admitted completed bar is absent from ledger")
    targets = (index, index + 1) if index + 1 < len(bars) else (index,)
    return tuple(
        (bars[target], bars[target - 1] if target > 0 else None)
        for target in targets
    )


class _EventSnapshot:
    def __init__(self, trade_date: date, phase: str) -> None:
        self.trade_date = trade_date
        self.phase = phase


def _snapshot_from_event(event: SessionStateEvent) -> _EventSnapshot:
    if event.trade_date is None:
        raise ValueError("session event does not carry a trade date")
    return _EventSnapshot(date.fromisoformat(event.trade_date), event.phase)
