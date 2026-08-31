from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, BarType, CustomData, DataType

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
from markeitech.intelligence.calendar_delivery import (
    ProjectionRequestPhase,
    ProjectionRequestState,
    ProjectionRetryPolicy,
    begin_projection_retry,
    classify_projection_response,
    ready_projection_state,
    retain_pending_calendars,
    schedule_projection_retry,
    start_projection_cycle,
    stop_projection_state,
    terminal_projection_state,
)
from markeitech.intelligence.calendar_messages import (
    CALENDAR_PROJECTION_REQUEST_TYPE_NAME,
    CALENDAR_PROJECTION_RESPONSE_TYPE_NAME,
    CALENDAR_TRANSITION_TYPE_NAME,
    CalendarProjectionRequest,
    CalendarProjectionResponse,
    CalendarTransition,
)
from markeitech.intelligence.completed_bars import (
    COMPLETED_BAR_INPUT_TYPE_NAME,
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
    EvidenceHealthEvent,
    EvidenceHealthSnapshot,
    EvidenceHealthSnapshotRequest,
)
from markeitech.intelligence.metrics import (
    METRIC_VALUE_TYPE_NAME,
    MetricFidelity,
    MetricHealth,
    MetricRegistry,
)
from markeitech.intelligence.rolling_measurements import (
    RollingBaselinePolicy,
    RollingCandidatePolicy,
    RollingCandidateResult,
    RollingFamilyPolicy,
    RollingMeasurementPolicy,
    calculate_rolling_projection,
    rolling_metric_definitions,
    rolling_metric_values,
)
from markeitech.intelligence.session import CalendarProjectionView
from markeitech.intelligence.session_measurements import (
    CompletedBarCatalogPolicy,
    calculate_completed_bar_metrics,
    completed_bar_metric_definitions,
)
from markeitech.intelligence.session_references import (
    SessionReferenceBook,
    SessionReferenceCatalogPolicy,
    SessionReferenceRole,
    SessionWindowSpec,
    calculate_session_reference_metrics,
    metric_value_signature,
    session_reference_metric_definitions,
)
from markeitech.intelligence.session_windows import (
    AnalyticalWindowBook,
    AnalyticalWindowPolicy,
    analytical_window_metric_definitions,
    analytical_window_value_signature,
    calculate_analytical_window_metrics,
    resolve_analytical_window,
    resolve_historical_analytical_window,
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
_ACTIVE_REFERENCE_RETRY_ALERT = "session-metrics-active-reference-retry"
_ACTIVE_REFERENCE_RETRY_DELAY_NS = 1_000_000
_CALENDAR_PROJECTION_RETRY_ALERT = "session-metrics-calendar-projection-retry"


def _active_reference_attempt_ns(
    calendar: CalendarProjectionView,
    phase: str,
    timestamp_ns: int,
    selector_interval_ns: int,
) -> int | None:
    if selector_interval_ns <= 0:
        raise ValueError("selector interval must be positive")
    snapshot = calendar.evaluate(timestamp_ns)
    if phase not in snapshot.phase_memberships or snapshot.phase_open_ns is None:
        return None
    completed_boundary_ns = timestamp_ns - (timestamp_ns % selector_interval_ns)
    if snapshot.phase_open_ns < completed_boundary_ns:
        return timestamp_ns
    return completed_boundary_ns + selector_interval_ns + _ACTIVE_REFERENCE_RETRY_DELAY_NS


def _completed_bar_foundation_historical_demand(
    *,
    demand_id: str,
    consumer_id: str,
    instrument_id: str,
    selector: str,
    window: str,
    minimum_observations: int,
    maximum_observations: int,
    priority: int,
    as_of_ns: int,
    calculation_interval_seconds: int,
    parameter_version: int,
) -> HistoricalDependencyDemandEvent:
    parameters: dict[str, str | int | float | bool] = {
        "calculation_interval_seconds": calculation_interval_seconds,
        "parameter_version": parameter_version,
    }
    return HistoricalDependencyDemandEvent(
        demand_id=demand_id,
        consumer_id=consumer_id,
        capability_id="metric:completed-bar-foundation",
        capability_version=1,
        instrument_id=instrument_id,
        selector=selector,
        window=window,
        minimum_observations=minimum_observations,
        maximum_observations=maximum_observations,
        priority=priority,
        purpose="warm completed-bar foundation metrics",
        as_of_ns=as_of_ns,
        parameters=parameters,
    )


class SessionMetricsActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_ids: list[str],
        instrument_calendars: dict[str, str],
        expected_calendar_digests: dict[str, str],
        projection_lookback_days: int,
        projection_lookahead_days: int,
        calendar_source: str,
        calendar_source_epoch: str,
        projection_retry: dict[str, int],
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
        session_references: dict[str, object],
        session_windows: dict[str, object],
        rolling_measurements: dict[str, object],
        actor_id: str | ActorId = "SESSION-METRICS",
    ) -> SessionMetricsActorConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.instrument_ids = tuple(instrument_ids)
        obj.instrument_calendars = dict(instrument_calendars)
        obj.expected_calendar_digests = dict(expected_calendar_digests)
        obj.projection_lookback_days = projection_lookback_days
        obj.projection_lookahead_days = projection_lookahead_days
        obj.calendar_source = calendar_source
        obj.calendar_source_epoch = calendar_source_epoch
        obj.projection_retry = dict(projection_retry)
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
        obj.session_references = dict(session_references)
        obj.session_windows = dict(session_windows)
        obj.rolling_measurements = dict(rolling_measurements)
        return obj


class SessionMetricsActor(DataActor):
    """Converges bounded historical and live bars into foundation metrics.

    Markeitech Metadata:
        architecture.component.id: actor.session-metrics
        architecture.component.label: Session Metrics
        architecture.component.kind: markeitech_actor
        architecture.component.boundary: boundary.intelligence
        architecture.component.responsibilities:
            - Converge bounded historical and live bars into completed-bar, session, window, and
              rolling measurements.
            - Consume immutable calendar projections and transitions without instantiating mcal.
            - Publish live and historical evidence demands for configured metric capabilities.
    """

    def __init__(self, config: SessionMetricsActorConfig) -> None:
        super().__init__(config)
        if not config.instrument_ids or len(set(config.instrument_ids)) != len(
            config.instrument_ids,
        ):
            raise ValueError("session metrics require unique configured instruments")
        self._instrument_ids = tuple(sorted(config.instrument_ids))
        self._instrument_set = frozenset(self._instrument_ids)
        self._instrument_calendars = dict(config.instrument_calendars)
        self._expected_calendar_digests = dict(config.expected_calendar_digests)
        self._calendar_ids = tuple(sorted(set(self._instrument_calendars.values())))
        self._calendars: dict[str, CalendarProjectionView] = {}
        self._calendar_refresh_ids: set[str] = set()
        self._projection_lookback_ns = config.projection_lookback_days * 86_400_000_000_000
        self._projection_lookahead_ns = config.projection_lookahead_days * 86_400_000_000_000
        self._projection_policy = ProjectionRetryPolicy.from_config(config.projection_retry)
        self._projection_state = ProjectionRequestState.idle(
            requester=str(self.actor_id),
            expected_source=config.calendar_source,
            expected_source_epoch=config.calendar_source_epoch,
        )
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
        references = config.session_references
        self._references_enabled = bool(references["enabled"])
        self._reference_historical_selector = str(references["historical_selector"])
        self._reference_interval_ns = BarType.from_str(
            f"{self._instrument_ids[0]}-{self._reference_historical_selector}",
        ).spec.get_interval_ns()
        self._reference_active_window = HistoricalWindow(str(references["active_window"]))
        self._reference_previous_window = HistoricalWindow(str(references["previous_window"]))
        self._reference_overnight_window = HistoricalWindow(str(references["overnight_window"]))
        self._reference_minimum_history = int(references["minimum_historical_observations"])
        self._reference_maximum_history = int(references["maximum_historical_observations"])
        self._reference_price_basis = str(references["vwap_price_basis"])
        self._deferred_active_references: set[str] = set()
        reference_policy = SessionReferenceCatalogPolicy(
            live_selector=self._live_selector,
            historical_selector=self._reference_historical_selector,
            active_window=self._reference_active_window,
            previous_window=self._reference_previous_window,
            overnight_window=self._reference_overnight_window,
            minimum_historical_observations=self._reference_minimum_history,
            maximum_historical_observations=self._reference_maximum_history,
            vwap_price_basis=self._reference_price_basis,
            vwap_price_basis_dynamic=bool(references["vwap_price_basis_dynamic"]),
            minimum_coverage_ratio=float(references["minimum_coverage_ratio"]),
            minimum_coverage_ratio_floor=float(references["minimum_coverage_ratio_floor"]),
            minimum_coverage_ratio_ceiling=float(references["minimum_coverage_ratio_ceiling"]),
            minimum_coverage_ratio_step=float(references["minimum_coverage_ratio_step"]),
            minimum_coverage_ratio_dynamic=bool(references["minimum_coverage_ratio_dynamic"]),
            parameter_source=self._parameter_source,
            priority=self._priority,
            maximum_retained_sessions=int(references["maximum_retained_sessions"]),
            maximum_output_age_ms=int(references["maximum_output_age_ms"]),
        )
        session_windows = config.session_windows
        self._windows_enabled = bool(session_windows["enabled"])
        self._window_policies: dict[tuple[str, str], AnalyticalWindowPolicy] = {}
        if self._windows_enabled:
            for profile_id, profile in self._profiles.items():
                for raw_window in profile.get("windows", []):
                    window = dict(raw_window)
                    policy_key = (profile_id, str(window["window_id"]))
                    self._window_policies[policy_key] = AnalyticalWindowPolicy(
                        profile_id=profile_id,
                        profile_version=int(profile["version"]),
                        window_id=str(window["window_id"]),
                        purpose=str(window["purpose"]),
                        anchor_phase=str(window["anchor_phase"]),
                        anchor_boundary=str(window["anchor_boundary"]),
                        offset_seconds=int(window["offset_seconds"]),
                        duration_seconds=int(window["duration_seconds"]),
                        minimum_duration_seconds=int(window["minimum_duration_seconds"]),
                        maximum_duration_seconds=int(window["maximum_duration_seconds"]),
                        duration_step_seconds=int(window["duration_step_seconds"]),
                        duration_dynamic=bool(window["dynamic"]),
                        live_selector=self._live_selector,
                        historical_selector=str(window["historical_selector"]),
                        minimum_historical_observations=int(
                            window["minimum_historical_observations"],
                        ),
                        maximum_historical_observations=int(
                            window["maximum_historical_observations"],
                        ),
                        price_basis=str(session_windows["price_basis"]),
                        price_basis_dynamic=bool(session_windows["price_basis_dynamic"]),
                        minimum_coverage_ratio=float(
                            session_windows["minimum_coverage_ratio"],
                        ),
                        minimum_coverage_ratio_floor=float(
                            session_windows["minimum_coverage_ratio_floor"],
                        ),
                        minimum_coverage_ratio_ceiling=float(
                            session_windows["minimum_coverage_ratio_ceiling"],
                        ),
                        minimum_coverage_ratio_step=float(
                            session_windows["minimum_coverage_ratio_step"],
                        ),
                        minimum_coverage_ratio_dynamic=bool(
                            session_windows["minimum_coverage_ratio_dynamic"],
                        ),
                        parameter_source=self._parameter_source,
                        priority=self._priority,
                        maximum_retained_sessions=int(
                            session_windows["maximum_retained_sessions"],
                        ),
                        maximum_output_age_ms=int(session_windows["maximum_output_age_ms"]),
                    )
        rolling = config.rolling_measurements
        self._rolling_policy = _rolling_policy(
            rolling,
            parameter_source=self._parameter_source,
            priority=self._priority,
        )
        self._rolling_enabled = self._rolling_policy.enabled
        definitions = completed_bar_metric_definitions(policy)
        if self._references_enabled:
            definitions += session_reference_metric_definitions(reference_policy)
        if self._windows_enabled:
            definitions += analytical_window_metric_definitions(
                tuple(self._window_policies.values()),
            )
        if self._rolling_enabled:
            definitions += rolling_metric_definitions(self._rolling_policy)
        self._registry = MetricRegistry(definitions)
        self._port = NautilusSubscriptionPort(self)
        self._metric_type = DataType(METRIC_VALUE_TYPE_NAME)
        self._completed_bar_type = DataType(COMPLETED_BAR_INPUT_TYPE_NAME)
        self._batch_type = DataType(HISTORICAL_BATCH_TYPE_NAME)
        self._calendar_request_type = DataType(CALENDAR_PROJECTION_REQUEST_TYPE_NAME)
        self._calendar_response_type = DataType(CALENDAR_PROJECTION_RESPONSE_TYPE_NAME)
        self._calendar_transition_type = DataType(CALENDAR_TRANSITION_TYPE_NAME)
        self._demand_retry_interval_ns = config.demand_retry_interval_ms * 1_000_000
        self._evidence_retry_interval_ns = config.evidence_snapshot_retry_interval_ms * 1_000_000
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
        self._session_states: dict[str, CalendarTransition] = {}
        self._evidence: dict[str, EvidenceHealthEvent] = {}
        self._attached: set[str] = set()
        self._acknowledged_demands: set[str] = set()
        self._historical_readiness: dict[str, str] = {}
        self._foundation_history_requested: set[str] = set()
        self._revisions: defaultdict[str, int] = defaultdict(int)
        self._counts: defaultdict[str, int] = defaultdict(int)
        self._reference_books = {
            instrument_id: SessionReferenceBook(
                instrument_id=instrument_id,
                price_basis=reference_policy.vwap_price_basis,
                minimum_coverage_ratio=reference_policy.minimum_coverage_ratio,
                maximum_retained_sessions=reference_policy.maximum_retained_sessions,
                maximum_observations_per_session=max(
                    self._maximum_retained,
                    reference_policy.maximum_historical_observations,
                ),
            )
            for instrument_id in self._instrument_ids
        }
        self._reference_signatures: dict[tuple[str, str], tuple[object, ...]] = {}
        self._window_books = {
            (instrument_id, window_id): AnalyticalWindowBook(
                instrument_id=instrument_id,
                policy=self._window_policies[(profile_id, window_id)],
                maximum_observations_per_session=max(
                    self._maximum_retained,
                    self._window_policies[(profile_id, window_id)].maximum_historical_observations,
                ),
            )
            for instrument_id in self._instrument_ids
            for profile_id in (self._profile_bindings[instrument_id],)
            for candidate_profile_id, window_id in self._window_policies
            if candidate_profile_id == profile_id
        }
        self._window_signatures: dict[tuple[str, str], tuple[object, ...]] = {}
        self._rolling_signatures: dict[tuple[str, str], tuple[object, ...]] = {}
        self._rolling_bar_ledgers: dict[tuple[str, str], CompletedBarLedger] = {}
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
        self._reference_demand_ids = {
            (instrument_id, role): f"metric:session:{instrument_id}:reference:{role.value}"
            for instrument_id in self._instrument_ids
            for role in SessionReferenceRole
            if role is not SessionReferenceRole.OVERNIGHT
            or bool(self._profiles[self._profile_bindings[instrument_id]]["overnight_enabled"])
        }
        self._window_demand_ids = {
            (instrument_id, window_id): f"metric:session:{instrument_id}:window:{window_id}"
            for instrument_id, window_id in self._window_books
        }

    def on_start(self) -> None:
        for signal_name in (
            ACQUISITION_STREAM_SIGNAL,
            HISTORICAL_READINESS_SIGNAL,
            EVIDENCE_HEALTH_SIGNAL,
            EVIDENCE_HEALTH_SNAPSHOT_SIGNAL,
        ):
            self.subscribe_signal(signal_name)
        self.subscribe_data(self._batch_type)
        self.subscribe_data(self._calendar_response_type)
        self.subscribe_data(self._calendar_transition_type)
        self._begin_calendar_projection_cycle()
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
        elif signal.name == EVIDENCE_HEALTH_SIGNAL:
            self._observe_evidence(signal.value)
        elif signal.name == EVIDENCE_HEALTH_SNAPSHOT_SIGNAL:
            self._observe_evidence_snapshot(signal.value)

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, CalendarTransition):
            self._observe_session_state(payload)
            return
        if isinstance(payload, CalendarProjectionResponse):
            self._observe_calendar_projection(payload)
            return
        if not isinstance(payload, HistoricalBatch):
            return
        dependencies = {dependency.consumer_id for dependency in payload.request.dependencies}
        if str(self.actor_id) not in dependencies:
            return
        if payload.request.instrument_id not in self._instrument_set:
            return
        if payload.request.kind is not FeedKind.BARS:
            return
        capabilities = {
            dependency.capability_id
            for dependency in payload.request.dependencies
            if dependency.consumer_id == str(self.actor_id)
        }
        if "metric:completed-bar-foundation" in capabilities:
            self._counts["historical_batches"] += 1
            for observation in payload.observations:
                self._process_provider_bar(
                    observation,
                    source=CompletedBarSource.HISTORICAL_PROVIDER,
                    received_ns=payload.received_at_ns,
                    evidence_ref=f"historical:{payload.request.request_id}",
                )
            if self._rolling_enabled:
                self._publish_rolling_metrics(payload.request.instrument_id)
        if (
            self._references_enabled
            and payload.request.selector == self._reference_historical_selector
        ):
            self._process_reference_batch(payload)
        if self._windows_enabled:
            self._process_window_batch(payload)

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
        self._projection_state = stop_projection_state(self._projection_state)
        for timer_name in (
            _DEMAND_RETRY_TIMER,
            _EVIDENCE_RETRY_TIMER,
            _HISTORICAL_DEMAND_ALERT,
            _ACTIVE_REFERENCE_RETRY_ALERT,
            _CALENDAR_PROJECTION_RETRY_ALERT,
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
            EVIDENCE_HEALTH_SIGNAL,
            EVIDENCE_HEALTH_SNAPSHOT_SIGNAL,
        ):
            self.unsubscribe_signal(signal_name)
        self.unsubscribe_data(self._batch_type)
        self.unsubscribe_data(self._calendar_response_type)
        self.unsubscribe_data(self._calendar_transition_type)
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
            f" | reference_batches={self._counts['reference_batches']}"
            f" | reference_values={self._counts['reference_values']}"
            f" | window_batches={self._counts['window_batches']}"
            f" | window_values={self._counts['window_values']}"
            f" | rolling_batches={self._counts['rolling_batches']}"
            f" | rolling_values={self._counts['rolling_values']}"
            f" | derived_completed_bars={self._counts['derived_completed_bars']}"
            f" | derived_bar_duplicates={self._counts['derived_bar_duplicates']}"
            f" | derived_bar_conflicts={self._counts['derived_bar_conflicts']}"
            f" | failures={self._counts['failures']}"
            f" | historical_completed_bars={self._counts['historical_completed_bars']}"
            f" | live_aggregate_completed_bars="
            f"{self._counts['live_aggregate_completed_bars']}"
            f" | foundation_history_demands={self._counts['foundation_history_demands']}"
            f" | projection_state={self._projection_state.phase.value}"
            f" | projection_requests={self._counts['projection_requests']}"
            f" | projection_timeouts={self._counts['projection_timeouts']}"
            f" | projection_terminal={self._counts['projection_terminal']}",
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
        primary_phase = str(profile["primary_phase"])
        session_phase = (
            primary_phase
            if primary_phase in snapshot.phase_memberships
            else snapshot.phase
        )
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
            session_id=f"{calendar_id}:{snapshot.trade_date.isoformat()}:{session_phase}",
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
        del use_current
        if calendar_id not in self._calendars:
            raise ValueError(f"calendar projection is unavailable: {calendar_id}")
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
        if bar.source is CompletedBarSource.HISTORICAL_PROVIDER:
            self._counts["historical_completed_bars"] += 1
        elif bar.source is CompletedBarSource.LIVE_AGGREGATE:
            self._counts["live_aggregate_completed_bars"] += 1
        self.publish_data(
            self._completed_bar_type,
            CustomData(self._completed_bar_type, admission.accepted),
        )
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
        if self._references_enabled and bar.source in {
            CompletedBarSource.LIVE_NATIVE,
            CompletedBarSource.LIVE_AGGREGATE,
        }:
            self._ingest_live_reference(bar)
        if self._windows_enabled and bar.source in {
            CompletedBarSource.LIVE_NATIVE,
            CompletedBarSource.LIVE_AGGREGATE,
        }:
            self._ingest_live_windows(bar)
        if self._rolling_enabled and bar.source in {
            CompletedBarSource.LIVE_NATIVE,
            CompletedBarSource.LIVE_AGGREGATE,
        }:
            self._publish_rolling_metrics(bar.instrument_id)

    def _publish_rolling_metrics(self, instrument_id: str) -> None:
        bars = self._ledgers[instrument_id].bars
        if not bars:
            return
        try:
            calendar = self._calendars[self._instrument_calendars[instrument_id]]
            latest_date = bars[-1].trade_date
            phase_windows = calendar.windows(latest_date - timedelta(days=45), latest_date)
            projection = calculate_rolling_projection(
                bars,
                phase_windows=phase_windows,
                policy=self._rolling_policy,
            )
            self._publish_derived_completed_bars(projection.completed_bars)
            pending: list[tuple[RollingCandidateResult, tuple[object, ...]]] = []
            for result in projection.candidates:
                signature = _rolling_result_signature(result)
                key = (instrument_id, f"{result.family_id}:{result.candidate_id}")
                if self._rolling_signatures.get(key) == signature:
                    continue
                pending.append((result, signature))
            if not pending:
                return
            self._revisions[instrument_id] += 1
            now_ns = max(self.clock.timestamp_ns(), bars[-1].normalized_ts_ns)
            for result, signature in pending:
                values = rolling_metric_values(
                    result,
                    registry=self._registry,
                    parameter_version=self._parameter_version,
                    calculated_ts_ns=now_ns,
                    published_ts_ns=now_ns,
                    source=str(self.actor_id),
                    revision=self._revisions[instrument_id],
                )
                for value in values:
                    self.publish_data(self._metric_type, CustomData(self._metric_type, value))
                self._rolling_signatures[
                    (instrument_id, f"{result.family_id}:{result.candidate_id}")
                ] = signature
                self._counts["rolling_values"] += len(values)
            self._counts["rolling_batches"] += 1
        except (ValueError, ArithmeticError, InvalidOperation) as exc:
            self._counts["failures"] += 1
            self.log.error(
                "ROLLING_MEASUREMENT_REJECTED"
                f" | instrument_id={instrument_id}"
                f" | error={type(exc).__name__} | reason={exc}",
            )

    def _publish_derived_completed_bars(
        self,
        bars: tuple[CompletedBarInput, ...],
    ) -> None:
        for bar in bars:
            if bar.bar_specification == self._historical_selector:
                continue
            key = (bar.instrument_id, bar.bar_specification)
            ledger = self._rolling_bar_ledgers.setdefault(
                key,
                CompletedBarLedger(
                    maximum_observations=self._maximum_retained,
                    conflict_policy=BarConflictPolicy.REJECT_CONFLICT,
                ),
            )
            admission = ledger.admit(bar)
            if admission.status is BarAdmissionStatus.DUPLICATE:
                self._counts["derived_bar_duplicates"] += 1
                continue
            if admission.status is BarAdmissionStatus.CONFLICT:
                self._counts["derived_bar_conflicts"] += 1
                self.log.error(
                    "ROLLING_COMPLETED_BAR_CONFLICT"
                    f" | instrument_id={bar.instrument_id}"
                    f" | bar_specification={bar.bar_specification}"
                    f" | interval_end_ns={bar.interval_end_ns}",
                )
                continue
            self.publish_data(
                self._completed_bar_type,
                CustomData(self._completed_bar_type, admission.accepted),
            )
            self._counts["derived_completed_bars"] += 1

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

    def _begin_calendar_projection_cycle(self) -> None:
        requested = tuple(
            calendar_id
            for calendar_id in self._calendar_ids
            if calendar_id not in self._calendars or calendar_id in self._calendar_refresh_ids
        )
        if not requested:
            return
        now_ns = self.clock.timestamp_ns()
        self._projection_state = start_projection_cycle(
            self._projection_state,
            calendar_ids=requested,
            start_ns=max(0, now_ns - self._projection_lookback_ns),
            end_ns=now_ns + self._projection_lookahead_ns,
            now_ns=now_ns,
            policy=self._projection_policy,
        )
        if self._projection_state.phase is ProjectionRequestPhase.WAITING:
            self._publish_calendar_projection_request()

    def _publish_calendar_projection_request(self) -> None:
        state = self._projection_state
        if (
            state.phase is not ProjectionRequestPhase.WAITING
            or state.request_id is None
            or state.start_ns is None
            or state.end_ns is None
        ):
            return
        self._set_calendar_projection_alert()
        request = CalendarProjectionRequest(
            request_id=state.request_id,
            requester=state.requester,
            calendar_ids=state.pending_calendar_ids,
            start_ns=state.start_ns,
            end_ns=state.end_ns,
            requested_ts_ns=self.clock.timestamp_ns(),
        )
        self._counts["projection_requests"] += 1
        self.publish_data(
            self._calendar_request_type,
            CustomData(self._calendar_request_type, request),
        )

    def _observe_calendar_projection(self, response: CalendarProjectionResponse) -> None:
        disposition = classify_projection_response(self._projection_state, response)
        if disposition != "ACCEPT":
            self._counts[f"projection_{disposition.lower()}"] += 1
            return
        self._cancel_calendar_projection_alert()
        state = self._projection_state
        accepted_ids: set[str] = set()
        for projection in response.projections:
            expected = self._expected_calendar_digests.get(projection.calendar_id)
            if (
                expected is None
                or projection.definition_digest != expected
                or state.start_ns is None
                or state.end_ns is None
                or projection.coverage_start_ns > state.start_ns
                or projection.coverage_end_ns < state.end_ns
            ):
                self._counts["failures"] += 1
                self._counts["projection_conflicts"] += 1
                self._projection_state = terminal_projection_state(
                    state,
                    "projection_identity_conflict",
                )
                self._counts["projection_terminal"] += 1
                self.log.error(
                    "SESSION_METRIC_CALENDAR_PROJECTION_CONFLICT"
                    f" | calendar_id={projection.calendar_id}",
                )
                return
            self._calendars[projection.calendar_id] = CalendarProjectionView(projection)
            self._calendar_refresh_ids.discard(projection.calendar_id)
            accepted_ids.add(projection.calendar_id)
        remaining = tuple(
            item for item in state.pending_calendar_ids if item not in accepted_ids
        )
        if not remaining:
            self._projection_state = ready_projection_state(state)
            self._publish_historical_demands(None)
            self._begin_calendar_projection_cycle()
            return
        failures = {item.calendar_id: item for item in response.failures}
        retryable = bool(remaining) and all(
            calendar_id in failures and failures[calendar_id].retryable
            for calendar_id in remaining
        )
        if response.status == "NOT_READY" or retryable:
            self._projection_state = retain_pending_calendars(state, remaining)
            self._projection_state = schedule_projection_retry(
                self._projection_state,
                now_ns=self.clock.timestamp_ns(),
                policy=self._projection_policy,
                retry_at_ns=response.retry_at_ns,
            )
            self._finish_calendar_projection_transition()
            return
        self._projection_state = terminal_projection_state(
            state,
            "projection_rejected" if response.status == "REJECTED" else "projection_unavailable",
            rejected=response.status == "REJECTED",
        )
        self._counts["projection_terminal"] += 1
        self.log.error(
            f"SESSION_METRIC_CALENDAR_PROJECTION_TERMINAL | status={response.status}"
            f" | pending={','.join(remaining)}",
        )

    def _on_calendar_projection_alert(self, _event) -> None:  # noqa: ANN001
        state = self._projection_state
        if state.phase is ProjectionRequestPhase.STOPPED:
            return
        now_ns = self.clock.timestamp_ns()
        if state.alert_at_ns is None or now_ns < state.alert_at_ns:
            return
        if state.phase is ProjectionRequestPhase.WAITING:
            self._counts["projection_timeouts"] += 1
            self._projection_state = schedule_projection_retry(
                state,
                now_ns=now_ns,
                policy=self._projection_policy,
                retry_at_ns=None,
            )
            self._finish_calendar_projection_transition()
            return
        if state.phase is ProjectionRequestPhase.BACKOFF:
            self._projection_state = begin_projection_retry(
                state,
                now_ns=now_ns,
                policy=self._projection_policy,
            )
            self._publish_calendar_projection_request()

    def _finish_calendar_projection_transition(self) -> None:
        if self._projection_state.phase is ProjectionRequestPhase.BACKOFF:
            self._counts["projection_retries"] += 1
            self._set_calendar_projection_alert()
            return
        if self._projection_state.phase in {
            ProjectionRequestPhase.FAILED,
            ProjectionRequestPhase.REJECTED,
        }:
            self._counts["projection_terminal"] += 1
            self.log.error(
                "SESSION_METRIC_CALENDAR_PROJECTION_EXHAUSTED"
                f" | code={self._projection_state.terminal_code}",
            )

    def _set_calendar_projection_alert(self) -> None:
        self._cancel_calendar_projection_alert()
        alert_at_ns = self._projection_state.alert_at_ns
        if alert_at_ns is not None:
            self.clock.set_time_alert_ns(
                _CALENDAR_PROJECTION_RETRY_ALERT,
                alert_at_ns,
                callback=self._on_calendar_projection_alert,
            )

    def _cancel_calendar_projection_alert(self) -> None:
        if _CALENDAR_PROJECTION_RETRY_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_CALENDAR_PROJECTION_RETRY_ALERT)

    def _publish_historical_demands(self, _event) -> None:  # noqa: ANN001
        if set(self._calendar_ids) - set(self._calendars):
            return
        now_ns = self.clock.timestamp_ns()
        active_retry_ns: int | None = None
        for instrument_id in self._instrument_ids:
            self._publish_foundation_historical_demand(
                instrument_id,
                as_of_ns=now_ns,
            )
            if self._references_enabled:
                for role in SessionReferenceRole:
                    if (instrument_id, role) not in self._reference_demand_ids:
                        continue
                    if role is SessionReferenceRole.ACTIVE:
                        retry_ns = self._request_active_reference(instrument_id, now_ns)
                        if retry_ns is not None:
                            active_retry_ns = (
                                retry_ns
                                if active_retry_ns is None
                                else min(active_retry_ns, retry_ns)
                            )
                        continue
                    self.publish_signal(
                        HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
                        self._reference_demand(instrument_id, role, now_ns).to_signal_value(),
                    )
            if self._windows_enabled:
                for candidate_instrument, window_id in self._window_demand_ids:
                    if candidate_instrument != instrument_id:
                        continue
                    self.publish_signal(
                        HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
                        self._window_demand(instrument_id, window_id, now_ns).to_signal_value(),
                    )
        if active_retry_ns is not None:
            self._schedule_active_reference_retry(active_retry_ns)

    def _publish_foundation_historical_demand(
        self,
        instrument_id: str,
        *,
        as_of_ns: int,
    ) -> None:
        if instrument_id in self._foundation_history_requested:
            return
        self._foundation_history_requested.add(instrument_id)
        demand = _completed_bar_foundation_historical_demand(
            demand_id=self._historical_demand_ids[instrument_id],
            consumer_id=str(self.actor_id),
            instrument_id=instrument_id,
            selector=self._historical_selector,
            window=self._historical_window,
            minimum_observations=self._minimum_historical_observations,
            maximum_observations=self._maximum_historical_observations,
            priority=self._priority,
            as_of_ns=as_of_ns,
            calculation_interval_seconds=self._target_interval_seconds,
            parameter_version=self._parameter_version,
        )
        try:
            self.publish_signal(
                HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
                demand.to_signal_value(),
            )
        except Exception:
            self._foundation_history_requested.discard(instrument_id)
            raise
        self._counts["foundation_history_demands"] += 1

    def _request_active_reference(self, instrument_id: str, now_ns: int) -> int | None:
        capability_id = f"metric:session-reference:{SessionReferenceRole.ACTIVE.value}"
        if self._historical_readiness.get(f"{instrument_id}:{capability_id}") == "READY":
            self._deferred_active_references.discard(instrument_id)
            return None
        profile = self._profiles[self._profile_bindings[instrument_id]]
        calendar = self._calendars[str(profile["calendar_id"])]
        attempt_ns = _active_reference_attempt_ns(
            calendar,
            str(profile["primary_phase"]),
            now_ns,
            self._reference_interval_ns,
        )
        if attempt_ns is None:
            self._deferred_active_references.discard(instrument_id)
            return None
        if attempt_ns > now_ns:
            self._deferred_active_references.add(instrument_id)
            return attempt_ns
        self._deferred_active_references.discard(instrument_id)
        self.publish_signal(
            HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
            self._reference_demand(
                instrument_id,
                SessionReferenceRole.ACTIVE,
                now_ns,
            ).to_signal_value(),
        )
        return None

    def _schedule_active_reference_retry(self, retry_at_ns: int) -> None:
        if _ACTIVE_REFERENCE_RETRY_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_ACTIVE_REFERENCE_RETRY_ALERT)
        self.clock.set_time_alert_ns(
            _ACTIVE_REFERENCE_RETRY_ALERT,
            retry_at_ns,
            callback=self._retry_active_references,
        )
        self.log.info(
            "SESSION_REFERENCE_RETRY_SCHEDULED"
            f" | pending={len(self._deferred_active_references)}"
            f" | retry_at_ns={retry_at_ns}",
        )

    def _retry_active_references(self, _event) -> None:  # noqa: ANN001
        now_ns = self.clock.timestamp_ns()
        pending = tuple(sorted(self._deferred_active_references))
        self._deferred_active_references.clear()
        next_retry_ns: int | None = None
        for instrument_id in pending:
            retry_ns = self._request_active_reference(instrument_id, now_ns)
            if retry_ns is not None:
                next_retry_ns = (
                    retry_ns if next_retry_ns is None else min(next_retry_ns, retry_ns)
                )
        if next_retry_ns is not None:
            self._schedule_active_reference_retry(next_retry_ns)

    def _process_reference_batch(self, batch: HistoricalBatch) -> None:
        role = self._reference_role(batch)
        if role is None or (batch.request.instrument_id, role) not in self._reference_demand_ids:
            return
        grouped: defaultdict[str, list[CompletedBarInput]] = defaultdict(list)
        for observation in batch.observations:
            try:
                bar = self._normalize(
                    observation,
                    CompletedBarSource.HISTORICAL_PROVIDER,
                    batch.received_at_ns,
                    f"historical:{batch.request.request_id}",
                )
            except (ValueError, ArithmeticError, InvalidOperation) as exc:
                self._counts["failures"] += 1
                self.log.error(
                    "SESSION_REFERENCE_BAR_REJECTED"
                    f" | instrument_id={batch.request.instrument_id}"
                    f" | role={role.value} | error={type(exc).__name__} | reason={exc}",
                )
                continue
            grouped[bar.session_id].append(bar)
        for session_id, bars in grouped.items():
            try:
                spec = SessionWindowSpec(
                    role=role,
                    session_id=session_id,
                    start_ns=batch.request.start_ns,
                    end_ns=batch.request.end_ns + 1,
                    complete=role is SessionReferenceRole.PREVIOUS,
                )
                self._reference_books[batch.request.instrument_id].ingest_historical(
                    spec,
                    tuple(bars),
                    cutoff_ns=max(bar.interval_end_ns for bar in bars),
                )
            except ValueError as exc:
                self._counts["failures"] += 1
                self.log.error(
                    "SESSION_REFERENCE_BATCH_REJECTED"
                    f" | instrument_id={batch.request.instrument_id}"
                    f" | role={role.value} | reason={exc}",
                )
        self._counts["reference_batches"] += 1
        self._publish_reference_metrics(batch.request.instrument_id)

    def _ingest_live_reference(self, bar: CompletedBarInput) -> None:
        profile = self._profiles[bar.analytical_profile_id]
        phase = bar.session_id.rsplit(":", 1)[-1]
        roles: list[SessionReferenceRole] = []
        if phase == str(profile["primary_phase"]):
            roles.append(SessionReferenceRole.ACTIVE)
        if bool(profile["overnight_enabled"]) and phase == str(profile["overnight_phase"]):
            roles.append(SessionReferenceRole.OVERNIGHT)
        for role in roles:
            spec = self._live_window_spec(bar, role, phase)
            if spec is None:
                continue
            try:
                self._reference_books[bar.instrument_id].ingest_live(spec, bar)
            except ValueError as exc:
                self._counts["failures"] += 1
                self.log.error(
                    "SESSION_REFERENCE_LIVE_REJECTED"
                    f" | instrument_id={bar.instrument_id}"
                    f" | role={role.value} | reason={exc}",
                )
        if roles:
            self._publish_reference_metrics(bar.instrument_id)

    def _live_window_spec(
        self,
        bar: CompletedBarInput,
        role: SessionReferenceRole,
        phase: str,
    ) -> SessionWindowSpec | None:
        windows = self._calendars[bar.calendar_id].windows(bar.trade_date, bar.trade_date)
        window = next((item for item in windows if item.phase == phase), None)
        if window is None:
            self._counts["failures"] += 1
            self.log.error(
                "SESSION_REFERENCE_WINDOW_MISSING"
                f" | instrument_id={bar.instrument_id}"
                f" | trade_date={bar.trade_date.isoformat()} | phase={phase}",
            )
            return None
        return SessionWindowSpec(
            role=role,
            session_id=bar.session_id,
            start_ns=window.start_ns,
            end_ns=window.end_ns,
            complete=bar.interval_end_ns >= window.end_ns,
        )

    def _reference_demand(
        self,
        instrument_id: str,
        role: SessionReferenceRole,
        now_ns: int,
    ) -> HistoricalDependencyDemandEvent:
        profile = self._profiles[self._profile_bindings[instrument_id]]
        if role is SessionReferenceRole.ACTIVE:
            window = self._reference_active_window
            phase = str(profile["primary_phase"])
            window_parameters: dict[str, str | int] = {"phase": phase}
        elif role is SessionReferenceRole.PREVIOUS:
            window = self._reference_previous_window
            phase = str(profile["primary_phase"])
            window_parameters = {"phase": phase}
            if window is HistoricalWindow.PREVIOUS_SESSIONS:
                window_parameters["session_count"] = 1
        else:
            window = self._reference_overnight_window
            phase = str(profile["overnight_phase"])
            window_parameters = {"phase": phase}
        return HistoricalDependencyDemandEvent(
            demand_id=self._reference_demand_ids[(instrument_id, role)],
            consumer_id=str(self.actor_id),
            capability_id=f"metric:session-reference:{role.value}",
            capability_version=1,
            instrument_id=instrument_id,
            selector=self._reference_historical_selector,
            window=window.value,
            minimum_observations=self._reference_minimum_history,
            maximum_observations=self._reference_maximum_history,
            priority=self._priority,
            purpose=f"warm {role.value} session-reference measurements",
            as_of_ns=now_ns,
            window_parameters=window_parameters,
            parameters={
                "parameter_version": self._parameter_version,
                "vwap_price_basis": self._reference_price_basis,
            },
        )

    def _reference_role(self, batch: HistoricalBatch) -> SessionReferenceRole | None:
        capabilities = {
            dependency.capability_id
            for dependency in batch.request.dependencies
            if dependency.consumer_id == str(self.actor_id)
        }
        for role in SessionReferenceRole:
            if f"metric:session-reference:{role.value}" in capabilities:
                return role
        return None

    def _publish_reference_metrics(self, instrument_id: str) -> None:
        if instrument_id not in self._reference_books:
            return
        profile = self._profiles[self._profile_bindings[instrument_id]]
        book = self._reference_books[instrument_id]
        snapshot = book.snapshot(
            overnight_missing_reason=(
                self._reference_missing_reason(instrument_id, SessionReferenceRole.OVERNIGHT)
                if bool(profile["overnight_enabled"])
                else "overnight_not_configured"
            ),
        )
        snapshot = snapshot.__class__(
            instrument_id=snapshot.instrument_id,
            active=snapshot.active,
            previous=snapshot.previous,
            overnight=snapshot.overnight,
            active_missing_reason=self._reference_missing_reason(
                instrument_id,
                SessionReferenceRole.ACTIVE,
            ),
            previous_missing_reason=self._reference_missing_reason(
                instrument_id,
                SessionReferenceRole.PREVIOUS,
            ),
            overnight_missing_reason=snapshot.overnight_missing_reason,
        )
        self._revisions[f"reference:{instrument_id}"] += 1
        now_ns = self.clock.timestamp_ns()
        values = calculate_session_reference_metrics(
            snapshot,
            registry=self._registry,
            parameter_version=self._parameter_version,
            calculated_ts_ns=now_ns,
            published_ts_ns=now_ns,
            source=str(self.actor_id),
            revision=self._revisions[f"reference:{instrument_id}"],
        )
        for value in values:
            key = (instrument_id, value.metric_id)
            signature = metric_value_signature(value)
            if self._reference_signatures.get(key) == signature:
                continue
            self.publish_data(self._metric_type, CustomData(self._metric_type, value))
            self._reference_signatures[key] = signature
            self._counts["reference_values"] += 1

    def _reference_missing_reason(
        self,
        instrument_id: str,
        role: SessionReferenceRole,
    ) -> str:
        capability_id = f"metric:session-reference:{role.value}"
        state = self._historical_readiness.get(f"{instrument_id}:{capability_id}")
        return (
            f"{role.value}_session_history_{state.lower()}"
            if state is not None
            else f"{role.value}_session_history_pending"
        )

    def _process_window_batch(self, batch: HistoricalBatch) -> None:
        policies = self._window_policies_for_batch(batch)
        if not policies:
            return
        for policy in policies:
            bars: list[CompletedBarInput] = []
            for observation in batch.observations:
                try:
                    bar = self._normalize(
                        observation,
                        CompletedBarSource.HISTORICAL_PROVIDER,
                        batch.received_at_ns,
                        f"historical:{batch.request.request_id}",
                    )
                except (ValueError, ArithmeticError, InvalidOperation) as exc:
                    self._counts["failures"] += 1
                    self.log.error(
                        "SESSION_WINDOW_BAR_REJECTED"
                        f" | instrument_id={batch.request.instrument_id}"
                        f" | window_id={policy.window_id}"
                        f" | error={type(exc).__name__} | reason={exc}",
                    )
                    continue
                bars.append(bar)
            if bars:
                try:
                    trade_date, spec = resolve_historical_analytical_window(
                        policy,
                        self._calendars[self._instrument_calendars[batch.request.instrument_id]],
                        calendar_id=self._instrument_calendars[batch.request.instrument_id],
                        request_start_ns=batch.request.start_ns,
                    )
                    aligned = tuple(
                        replace(
                            bar,
                            trade_date=trade_date,
                            session_id=spec.session_id,
                        )
                        for bar in bars
                        if bar.interval_end_ns > spec.start_ns
                        and bar.interval_start_ns < spec.end_ns
                    )
                    if not aligned:
                        raise ValueError("historical batch does not overlap analytical window")
                    self._window_books[
                        (batch.request.instrument_id, policy.window_id)
                    ].ingest_historical(
                        spec,
                        aligned,
                        cutoff_ns=max(bar.interval_end_ns for bar in aligned),
                    )
                except ValueError as exc:
                    self._counts["failures"] += 1
                    self.log.error(
                        "SESSION_WINDOW_BATCH_REJECTED"
                        f" | instrument_id={batch.request.instrument_id}"
                        f" | window_id={policy.window_id} | reason={exc}",
                    )
            self._counts["window_batches"] += 1
            self._publish_window_metrics(batch.request.instrument_id, policy)

    def _ingest_live_windows(self, bar: CompletedBarInput) -> None:
        for (profile_id, _), policy in self._window_policies.items():
            if profile_id != bar.analytical_profile_id:
                continue
            try:
                spec = self._window_spec(policy, bar)
                if (
                    bar.interval_end_ns <= spec.start_ns
                    or bar.interval_start_ns >= spec.end_ns
                ):
                    continue
                aligned_bar = replace(bar, session_id=spec.session_id)
                self._window_books[(bar.instrument_id, policy.window_id)].ingest_live(
                    spec,
                    aligned_bar,
                )
            except ValueError as exc:
                self._counts["failures"] += 1
                self.log.error(
                    "SESSION_WINDOW_LIVE_REJECTED"
                    f" | instrument_id={bar.instrument_id}"
                    f" | window_id={policy.window_id} | reason={exc}",
                )
                continue
            self._publish_window_metrics(bar.instrument_id, policy)

    def _window_spec(
        self,
        policy: AnalyticalWindowPolicy,
        bar: CompletedBarInput,
    ):  # noqa: ANN202
        windows = self._calendars[bar.calendar_id].windows(bar.trade_date, bar.trade_date)
        session = next((item for item in windows if item.phase == policy.anchor_phase), None)
        if session is None:
            raise ValueError("calendar did not provide the configured anchor phase")
        session_id = f"{bar.calendar_id}:{bar.trade_date.isoformat()}:{policy.anchor_phase}"
        return resolve_analytical_window(policy, session, session_id=session_id)

    def _window_demand(
        self,
        instrument_id: str,
        window_id: str,
        now_ns: int,
    ) -> HistoricalDependencyDemandEvent:
        profile_id = self._profile_bindings[instrument_id]
        policy = self._window_policies[(profile_id, window_id)]
        window_parameters: dict[str, str | int | bool] = {
            "phase": policy.anchor_phase,
            "anchor_boundary": policy.anchor_boundary,
            "offset_seconds": policy.offset_seconds,
            "duration_seconds": policy.duration_seconds,
        }
        if policy.purpose == "power_hour":
            window_parameters["fallback_to_previous"] = True
        return HistoricalDependencyDemandEvent(
            demand_id=self._window_demand_ids[(instrument_id, window_id)],
            consumer_id=str(self.actor_id),
            capability_id=self._window_capability_id(policy),
            capability_version=1,
            instrument_id=instrument_id,
            selector=policy.historical_selector,
            window=policy.historical_window.value,
            minimum_observations=policy.minimum_historical_observations,
            maximum_observations=policy.maximum_historical_observations,
            priority=self._priority,
            purpose=f"warm {policy.purpose} window {policy.window_id}",
            as_of_ns=now_ns,
            window_parameters=window_parameters,
            parameters={
                "parameter_version": self._parameter_version,
                "window_id": policy.window_id,
                "price_basis": policy.price_basis,
            },
        )

    def _window_policies_for_batch(
        self,
        batch: HistoricalBatch,
    ) -> tuple[AnalyticalWindowPolicy, ...]:
        capabilities = {
            dependency.capability_id
            for dependency in batch.request.dependencies
            if dependency.consumer_id == str(self.actor_id)
        }
        instrument_id = batch.request.instrument_id
        profile_id = self._profile_bindings[instrument_id]
        return tuple(
            policy
            for (candidate_profile, window_id), policy in self._window_policies.items()
            if candidate_profile == profile_id
            and (instrument_id, window_id) in self._window_books
            and self._window_capability_id(policy) in capabilities
        )

    def _publish_window_metrics(
        self,
        instrument_id: str,
        policy: AnalyticalWindowPolicy,
    ) -> None:
        book = self._window_books.get((instrument_id, policy.window_id))
        if book is None:
            return
        now_ns = self.clock.timestamp_ns()
        summary = book.summary(as_of_ns=now_ns)
        revision_key = f"window:{instrument_id}:{policy.window_id}"
        self._revisions[revision_key] += 1
        values = calculate_analytical_window_metrics(
            instrument_id,
            policy,
            summary,
            registry=self._registry,
            parameter_version=self._parameter_version,
            calculated_ts_ns=now_ns,
            published_ts_ns=now_ns,
            source=str(self.actor_id),
            revision=self._revisions[revision_key],
            missing_reason=self._window_missing_reason(instrument_id, policy),
        )
        for value in values:
            key = (instrument_id, value.metric_id)
            signature = analytical_window_value_signature(value)
            if self._window_signatures.get(key) == signature:
                continue
            self.publish_data(self._metric_type, CustomData(self._metric_type, value))
            self._window_signatures[key] = signature
            self._counts["window_values"] += 1

    def _window_missing_reason(
        self,
        instrument_id: str,
        policy: AnalyticalWindowPolicy,
    ) -> str:
        capability_id = self._window_capability_id(policy)
        state = self._historical_readiness.get(f"{instrument_id}:{capability_id}")
        return (
            f"{policy.window_id}_history_{state.lower()}"
            if state is not None
            else f"{policy.window_id}_not_started_or_history_pending"
        )

    @staticmethod
    def _window_capability_id(policy: AnalyticalWindowPolicy) -> str:
        return f"metric:session-window:{policy.profile_id}:{policy.window_id}"

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
        if event.consumer_id != str(self.actor_id):
            return
        self._historical_readiness[f"{event.instrument_id}:{event.capability_id}"] = event.state
        if self._references_enabled and event.capability_id.startswith("metric:session-reference:"):
            self._publish_reference_metrics(event.instrument_id)
        if self._windows_enabled and event.capability_id.startswith("metric:session-window:"):
            profile_id = self._profile_bindings.get(event.instrument_id)
            if profile_id is None:
                return
            for (candidate_profile, _), policy in self._window_policies.items():
                if (
                    candidate_profile == profile_id
                    and self._window_capability_id(policy) == event.capability_id
                ):
                    self._publish_window_metrics(event.instrument_id, policy)

    def _observe_session_state(self, event: CalendarTransition) -> None:
        if event.calendar_id in self._expected_calendar_digests:
            if (
                event.definition_digest != self._expected_calendar_digests[event.calendar_id]
                or event.source != self._projection_state.expected_source
                or event.source_epoch != self._projection_state.expected_source_epoch
            ):
                self._counts["failures"] += 1
                self.log.error(
                    "SESSION_METRIC_CALENDAR_DEFINITION_CONFLICT"
                    f" | calendar_id={event.calendar_id}",
                )
                return
            self._calendar_refresh_ids.add(event.calendar_id)
            self._begin_calendar_projection_cycle()
            previous = self._session_states.get(event.calendar_id)
            self._session_states[event.calendar_id] = event
            if (
                previous is None
                or previous.phase_memberships == event.phase_memberships
            ):
                return
            self._request_open_session_references(event)

    def _primary_phase_is_open(self, instrument_id: str, timestamp_ns: int) -> bool:
        profile = self._profiles[self._profile_bindings[instrument_id]]
        calendar_id = str(profile["calendar_id"])
        current = self._session_states.get(calendar_id)
        if current is not None:
            phase_memberships = current.phase_memberships
        elif calendar_id in self._calendars:
            phase_memberships = self._calendars[calendar_id].evaluate(
                timestamp_ns,
            ).phase_memberships
        else:
            return False
        return str(profile["primary_phase"]) in phase_memberships

    def _request_open_session_references(self, event: CalendarTransition) -> None:
        if not self._references_enabled or not event.is_open:
            return
        now_ns = self.clock.timestamp_ns()
        active_retry_ns: int | None = None
        for instrument_id in self._instrument_ids:
            profile = self._profiles[self._profile_bindings[instrument_id]]
            if (
                str(profile["calendar_id"]) != event.calendar_id
                or str(profile["primary_phase"]) not in event.phase_memberships
            ):
                continue
            retry_ns = self._request_active_reference(instrument_id, now_ns)
            if retry_ns is not None:
                active_retry_ns = (
                    retry_ns if active_retry_ns is None else min(active_retry_ns, retry_ns)
                )
        if active_retry_ns is not None:
            self._schedule_active_reference_retry(active_retry_ns)

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


def _rolling_policy(
    raw: dict[str, object],
    *,
    parameter_source: str,
    priority: int,
) -> RollingMeasurementPolicy:
    baseline = dict(raw["baseline"])  # type: ignore[arg-type]
    families = tuple(
        RollingFamilyPolicy(
            family_id=str(family["family_id"]),
            source_selector=str(family["source_selector"]),
            input_selector=str(family["input_selector"]),
            input_interval_seconds=int(family["input_interval_seconds"]),
            aggregation_policy=str(family["aggregation_policy"]),
            selected_context_candidate_id=str(family["selected_context_candidate_id"]),
            candidates=tuple(
                RollingCandidatePolicy(
                    candidate_id=str(candidate["candidate_id"]),
                    purpose=str(candidate["purpose"]),
                    duration_seconds=int(candidate["duration_seconds"]),
                    minimum_duration_seconds=int(candidate["minimum_duration_seconds"]),
                    maximum_duration_seconds=int(candidate["maximum_duration_seconds"]),
                    duration_step_seconds=int(candidate["duration_step_seconds"]),
                    dynamic=bool(candidate["dynamic"]),
                    active=bool(candidate["active"]),
                )
                for candidate in family["candidates"]  # type: ignore[union-attr]
            ),
        )
        for family in raw["families"]  # type: ignore[union-attr]
    )
    return RollingMeasurementPolicy(
        enabled=bool(raw["enabled"]),
        minimum_coverage_ratio=float(raw["minimum_coverage_ratio"]),
        minimum_coverage_ratio_floor=float(raw["minimum_coverage_ratio_floor"]),
        minimum_coverage_ratio_ceiling=float(raw["minimum_coverage_ratio_ceiling"]),
        minimum_coverage_ratio_step=float(raw["minimum_coverage_ratio_step"]),
        minimum_coverage_ratio_dynamic=bool(raw["minimum_coverage_ratio_dynamic"]),
        maximum_retained_observations=int(raw["maximum_retained_observations"]),
        maximum_output_age_ms=int(raw["maximum_output_age_ms"]),
        baseline=RollingBaselinePolicy(
            eligible_reference_health=tuple(
                MetricHealth(str(value)) for value in baseline["eligible_reference_health"]
            ),
            eligible_reference_fidelities=tuple(
                MetricFidelity(str(value))
                for value in baseline["eligible_reference_fidelities"]
            ),
            recent_reference_count=int(baseline["recent_reference_count"]),
            recent_reference_count_minimum=int(baseline["recent_reference_count_minimum"]),
            recent_reference_count_maximum=int(baseline["recent_reference_count_maximum"]),
            recent_reference_count_step=int(baseline["recent_reference_count_step"]),
            recent_reference_count_dynamic=bool(baseline["recent_reference_count_dynamic"]),
            minimum_recent_references=int(baseline["minimum_recent_references"]),
            phase_reference_count=int(baseline["phase_reference_count"]),
            phase_reference_count_minimum=int(baseline["phase_reference_count_minimum"]),
            phase_reference_count_maximum=int(baseline["phase_reference_count_maximum"]),
            phase_reference_count_step=int(baseline["phase_reference_count_step"]),
            phase_reference_count_dynamic=bool(baseline["phase_reference_count_dynamic"]),
            minimum_phase_references=int(baseline["minimum_phase_references"]),
        ),
        families=families,
        parameter_source=parameter_source,
        priority=priority,
    )


def _rolling_result_signature(result: RollingCandidateResult) -> tuple[object, ...]:
    return (
        result.effective_ts_ns,
        result.price_range,
        result.realized_log_return_magnitude,
        result.average_true_range,
        result.directional_efficiency,
        result.coverage_ratio,
        result.expansion_ratio_recent,
        result.range_percentile_recent,
        result.recent_reference_count,
        result.expansion_ratio_phase,
        result.range_percentile_phase,
        result.phase_reference_count,
        result.current_health,
        result.recent_health,
        result.phase_health,
        result.fidelity,
        result.current_missing_reasons,
        result.recent_missing_reasons,
        result.phase_missing_reasons,
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
    return tuple((bars[target], bars[target - 1] if target > 0 else None) for target in targets)
