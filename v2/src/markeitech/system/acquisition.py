from __future__ import annotations

from collections import Counter

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, CustomData, DataType, InstrumentId

from markeitech.acquisition import (
    HISTORICAL_BATCH_TYPE_NAME,
    HISTORICAL_EXECUTION_SIGNAL,
    HISTORICAL_READINESS_SIGNAL,
    HISTORICAL_REQUEST_PLAN_TYPE_NAME,
    AcquisitionCoordinator,
    AcquisitionLifecycleEvent,
    DemandOwner,
    DemandOwnerKind,
    FeedKind,
    FeedRequirement,
    HistoricalExecutionCoordinator,
    HistoricalExecutionEventMessage,
    HistoricalExecutionPolicy,
    HistoricalExecutionUpdate,
    HistoricalReadinessEvent,
    HistoricalRequest,
    HistoricalRequestPlan,
    NautilusHistoricalPort,
    NautilusSubscriptionPort,
    ObservationDemand,
)
from markeitech.acquisition.historical_native import (
    HistoricalResponseMismatch,
    validate_historical_bars,
)
from markeitech.system.messages import (
    ACQUISITION_STATUS_REQUEST_SIGNAL,
    ACQUISITION_STATUS_SIGNAL,
    ACQUISITION_STREAM_SIGNAL,
    ANALYTICAL_DEMAND_SIGNAL,
    COMPONENT_FAILURE_SIGNAL,
    INSTRUMENTS_READY,
    INSTRUMENTS_RESOLVING,
    PERSISTENCE_READY_REQUEST_SIGNAL,
    PERSISTENCE_READY_SIGNAL,
    WATCHLIST_DEMAND_SIGNAL,
    AcquisitionStatusEvent,
    AcquisitionStatusRequest,
    AcquisitionStreamEvent,
    AnalyticalDemandEvent,
    ComponentFailureEvent,
    PersistenceReadyEvent,
    PersistenceReadyRequest,
    WatchlistDemandEvent,
)

_HISTORICAL_TIMER = "historical-execution"


class InstrumentDefinitionTracker:
    def __init__(self, instrument_ids: list[str] | tuple[str, ...]) -> None:
        expected = {InstrumentId.from_str(value) for value in instrument_ids}
        if not expected:
            raise ValueError("instrument acquisition requires at least one instrument")
        if len(expected) != len(instrument_ids):
            raise ValueError("instrument acquisition does not allow duplicate instruments")
        self._expected = frozenset(expected)
        self._available: set[InstrumentId] = set()
        self._requested: set[InstrumentId] = set()

    @property
    def expected(self) -> frozenset[InstrumentId]:
        return self._expected

    @property
    def available(self) -> frozenset[InstrumentId]:
        return frozenset(self._available)

    @property
    def missing(self) -> frozenset[InstrumentId]:
        return self._expected - self._available

    def observe(self, instrument_id: InstrumentId) -> bool:
        if instrument_id not in self._expected or instrument_id in self._available:
            return False
        self._available.add(instrument_id)
        return True

    def take_unrequested(self) -> tuple[InstrumentId, ...]:
        pending = tuple(sorted(self.missing - self._requested, key=str))
        self._requested.update(pending)
        return pending

    def status(self, source: str) -> AcquisitionStatusEvent:
        complete = not self.missing
        return AcquisitionStatusEvent(
            state=INSTRUMENTS_READY if complete else INSTRUMENTS_RESOLVING,
            reason=(
                "configured instrument definitions are available"
                if complete
                else "resolving configured instrument definitions"
            ),
            source=source,
            expected_instrument_ids=tuple(sorted(str(value) for value in self._expected)),
            available_instrument_ids=tuple(sorted(str(value) for value in self._available)),
        )


class DataAcquisitionActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_ids: list[str],
        historical: dict[str, int],
        actor_id: str | ActorId = "DATA-ACQUISITION",
    ) -> DataAcquisitionActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.instrument_ids = tuple(instrument_ids)
        obj.historical = dict(historical)
        return obj


class DataAcquisitionActor(DataActor):
    def __init__(self, config: DataAcquisitionActorConfig) -> None:
        super().__init__(config)
        self._tracker = InstrumentDefinitionTracker(config.instrument_ids)
        self._expected_instrument_ids = frozenset(config.instrument_ids)
        self._pending_demands: dict[str, ObservationDemand] = {}
        self._managed_stream_keys: set[tuple[str, str, str]] = set()
        self._coordinator = AcquisitionCoordinator(NautilusSubscriptionPort(self))
        historical = config.historical
        self._historical = HistoricalExecutionCoordinator(
            NautilusHistoricalPort(self),
            HistoricalExecutionPolicy(
                maximum_queued_requests=historical["maximum_outstanding_requests"],
                maximum_in_flight_requests=historical["maximum_in_flight_requests"],
                timeout_ns=historical["timeout_seconds"] * 1_000_000_000,
                maximum_attempts=historical["maximum_attempts"],
                retry_backoff_ns=historical["retry_backoff_ms"] * 1_000_000,
            ),
        )
        self._historical_poll_interval_ns = historical["poll_interval_ms"] * 1_000_000
        self._maximum_historical_observations_per_request = historical[
            "maximum_observations_per_request"
        ]
        self._maximum_historical_observations_outstanding = historical[
            "maximum_total_observations"
        ]
        self._historical_plan_type = DataType(HISTORICAL_REQUEST_PLAN_TYPE_NAME)
        self._historical_requests: dict[str, HistoricalRequest] = {}
        self._pending_historical_plans: dict[str, HistoricalRequestPlan] = {}
        self._historical_counts: Counter[str] = Counter()
        self._observation_counts: Counter[tuple[str, str, str]] = Counter()
        self._lifecycle_counts: Counter[str] = Counter()
        self._instrument_requests = 0
        self._instruments_received = 0
        self._duplicate_instruments = 0
        self._status_requests = 0
        self._malformed_status_requests = 0
        self._statuses_published = 0
        self._failure_published = False
        self._startup_released = False

    def on_start(self) -> None:
        self.subscribe_signal(ACQUISITION_STATUS_REQUEST_SIGNAL)
        self.subscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.subscribe_signal(WATCHLIST_DEMAND_SIGNAL)
        self.subscribe_signal(ANALYTICAL_DEMAND_SIGNAL)
        self.subscribe_data(self._historical_plan_type)
        self.publish_signal(
            PERSISTENCE_READY_REQUEST_SIGNAL,
            PersistenceReadyRequest(requester=str(self.actor_id)).to_signal_value(),
        )

    def _release_startup(self) -> None:
        if self._startup_released:
            return
        self._startup_released = True
        for instrument_id in sorted(self._tracker.expected, key=str):
            if self.cache.instrument(instrument_id) is not None:
                self._tracker.observe(instrument_id)
        for instrument_id in self._tracker.take_unrequested():
            self.request_instrument(instrument_id)
            self._instrument_requests += 1
        self._publish_status()
        self._start_pending_demands_if_ready()
        self.clock.set_timer_ns(
            _HISTORICAL_TIMER,
            self._historical_poll_interval_ns,
            callback=self._advance_historical,
        )

    def on_instrument(self, instrument) -> None:  # noqa: ANN001
        if not self._startup_released:
            return
        if self._tracker.observe(instrument.id):
            self._instruments_received += 1
            self.log.info(f"INSTRUMENT_ACQUIRED | instrument_id={instrument.id}")
            self._publish_status()
            self._start_pending_demands_if_ready()
        elif instrument.id in self._tracker.expected:
            self._duplicate_instruments += 1

    def on_signal(self, signal: Signal) -> None:
        if signal.name == WATCHLIST_DEMAND_SIGNAL:
            self._handle_watchlist_demand(signal.value)
            return
        if signal.name == ANALYTICAL_DEMAND_SIGNAL:
            self._handle_analytical_demand(signal.value)
            return
        if signal.name == PERSISTENCE_READY_SIGNAL:
            try:
                PersistenceReadyEvent.from_signal_value(signal.value)
            except ValueError as exc:
                self.log.error(
                    "PERSISTENCE_READY_REJECTED"
                    f" | reason=invalid_event | error={type(exc).__name__}",
                )
                return
            self._release_startup()
            return
        if signal.name != ACQUISITION_STATUS_REQUEST_SIGNAL:
            return
        if not self._startup_released:
            return
        self._status_requests += 1
        try:
            AcquisitionStatusRequest.from_signal_value(signal.value)
        except ValueError as exc:
            self._malformed_status_requests += 1
            self.log.error(
                "ACQUISITION_STATUS_REQUEST_REJECTED"
                f" | reason=invalid_request | error={type(exc).__name__}",
            )
            return
        self._publish_status()

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if not isinstance(payload, HistoricalRequestPlan):
            return
        if payload.request.instrument_id not in self._expected_instrument_ids:
            self.log.error(
                "HISTORICAL_PLAN_REJECTED | reason=instrument_outside_acquisition_scope",
            )
            return
        self._pending_historical_plans[payload.demand_id] = payload
        self._start_pending_demands_if_ready()

    def on_quote(self, quote) -> None:  # noqa: ANN001
        self._observe(str(quote.instrument_id), FeedKind.QUOTES)

    def on_trade(self, trade) -> None:  # noqa: ANN001
        self._observe(str(trade.instrument_id), FeedKind.TRADES)

    def on_bar(self, bar) -> None:  # noqa: ANN001
        instrument_id = str(bar.bar_type.instrument_id)
        selector = str(bar.bar_type).removeprefix(f"{instrument_id}-")
        self._observe(instrument_id, FeedKind.BARS, selector)

    def on_historical_bars(self, bars) -> None:  # noqa: ANN001
        active = self._historical.active_request_ids
        if not active:
            self._historical_counts["late_callbacks"] += 1
            self.log.warning(
                "HISTORICAL_RESPONSE_IGNORED | reason=no_active_request"
                f" | observations={len(bars)}",
            )
            return
        request_id = active[0]
        observations = tuple(bars)
        request = self._historical_requests[request_id]
        try:
            validate_historical_bars(request, observations)
        except HistoricalResponseMismatch as exc:
            self.log.error(
                f"HISTORICAL_RESPONSE_REJECTED | request_id={request_id} | reason={exc}",
            )
            self._publish_historical_update(
                self._historical.fail(
                    request_id,
                    str(exc),
                    now_ns=self.clock.timestamp_ns(),
                    retryable=False,
                ),
            )
            return
        first_ts_event = observations[0].ts_event if observations else "n/a"
        last_ts_event = observations[-1].ts_event if observations else "n/a"
        self.log.info(
            f"HISTORICAL_RESPONSE_ACCEPTED | request_id={request_id}"
            f" | bar_type={request.instrument_id}-{request.selector}"
            f" | observations={len(observations)}/{request.limit}"
            f" | first_ts_event={first_ts_event} | last_ts_event={last_ts_event}",
        )
        self._publish_historical_update(
            self._historical.complete(
                request_id,
                observations,
                now_ns=self.clock.timestamp_ns(),
            ),
        )

    def on_instrument_status(self, status) -> None:  # noqa: ANN001
        self._observe(str(status.instrument_id), FeedKind.INSTRUMENT_STATUS)

    def on_stop(self) -> None:
        if self._startup_released:
            for demand in tuple(self._coordinator.demands):
                self._publish_lifecycle_events(
                    self._coordinator.cancel(demand.demand_id, now=self.clock.utc_now()),
                )
        self.unsubscribe_signal(ACQUISITION_STATUS_REQUEST_SIGNAL)
        self.unsubscribe_signal(PERSISTENCE_READY_SIGNAL)
        self.unsubscribe_signal(WATCHLIST_DEMAND_SIGNAL)
        self.unsubscribe_signal(ANALYTICAL_DEMAND_SIGNAL)
        self.unsubscribe_data(self._historical_plan_type)
        if _HISTORICAL_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_HISTORICAL_TIMER)
        now_ns = self.clock.timestamp_ns()
        for request_id in (
            self._historical.pending_request_ids + self._historical.active_request_ids
        ):
            self._publish_historical_update(self._historical.cancel(request_id, now_ns=now_ns))
        self.log.info(
            "DATA_ACQUISITION_SUMMARY"
            f" | instrument_requests={self._instrument_requests}"
            f" | instruments_received={self._instruments_received}"
            f" | duplicate_instruments={self._duplicate_instruments}"
            f" | status_requests={self._status_requests}"
            f" | malformed_status_requests={self._malformed_status_requests}"
            f" | statuses_published={self._statuses_published}"
            f" | streams_subscribed={self._lifecycle_counts['SUBSCRIBED']}"
            f" | streams_active={self._lifecycle_counts['ACTIVE']}"
            f" | observations={sum(self._observation_counts.values())}"
            f" | historical_completed={self._historical_counts['COMPLETED']}"
            f" | historical_ready={self._historical_counts['READY']}"
            f" | historical_degraded={self._historical_counts['DEGRADED']}"
            f" | historical_late_callbacks={self._historical_counts['late_callbacks']}",
        )

    def on_fault(self) -> None:
        if self._failure_published:
            return
        self._failure_published = True
        self.publish_signal(
            COMPONENT_FAILURE_SIGNAL,
            ComponentFailureEvent(
                component="data_acquisition",
                code="actor_faulted",
                reason="data acquisition actor entered fault state",
                evidence={
                    "available_instrument_count": len(self._tracker.available),
                    "expected_instrument_count": len(self._tracker.expected),
                },
            ).to_signal_value(),
        )

    def _publish_status(self) -> None:
        status = self._tracker.status(str(self.actor_id))
        self.publish_signal(ACQUISITION_STATUS_SIGNAL, status.to_signal_value())
        self._statuses_published += 1
        self.log.info(
            f"ACQUISITION_STATUS | state={status.state}"
            f" | available={len(status.available_instrument_ids)}"
            f"/{len(status.expected_instrument_ids)}",
        )

    def _handle_watchlist_demand(self, value: str) -> None:
        try:
            event = WatchlistDemandEvent.from_signal_value(value)
            if event.instrument_id not in self._expected_instrument_ids:
                raise ValueError("demand instrument is outside configured acquisition scope")
            demand = _watchlist_observation_demand(event)
        except ValueError as exc:
            self.log.error(
                f"WATCHLIST_DEMAND_REJECTED | reason=invalid_event | error={type(exc).__name__}",
            )
            return
        if event.action == "RELEASE":
            self._pending_demands.pop(event.demand_id, None)
            self._publish_lifecycle_events(
                self._coordinator.cancel(event.demand_id, now=self.clock.utc_now()),
            )
            return
        self._pending_demands[event.demand_id] = demand
        self._start_pending_demands_if_ready()

    def _handle_analytical_demand(self, value: str) -> None:
        try:
            event = AnalyticalDemandEvent.from_signal_value(value)
            if event.instrument_id not in self._expected_instrument_ids:
                raise ValueError("demand instrument is outside configured acquisition scope")
            demand = _analytical_observation_demand(event)
        except ValueError as exc:
            self.log.error(
                f"ANALYTICAL_DEMAND_REJECTED | reason=invalid_event | error={type(exc).__name__}",
            )
            return
        if event.action == "RELEASE":
            self._pending_demands.pop(event.demand_id, None)
            self._publish_lifecycle_events(
                self._coordinator.cancel(event.demand_id, now=self.clock.utc_now()),
            )
            return
        self._pending_demands[event.demand_id] = demand
        self._start_pending_demands_if_ready()

    def _start_pending_demands_if_ready(self) -> None:
        if not self._startup_released or self._tracker.missing:
            return
        for demand_id in sorted(tuple(self._pending_demands)):
            demand = self._pending_demands.pop(demand_id)
            self._managed_stream_keys.add(demand.requirement.stream_key)
            self._publish_lifecycle_events(
                self._coordinator.request(demand, now=self.clock.utc_now()),
            )
        for demand_id in sorted(tuple(self._pending_historical_plans)):
            plan = self._pending_historical_plans.pop(demand_id)
            self._start_historical_plan(plan)

    def _start_historical_plan(self, plan: HistoricalRequestPlan) -> None:
        now_ns = self.clock.timestamp_ns()
        try:
            request = plan.request
            outstanding = tuple(
                candidate
                for request_id in (
                    self._historical.pending_request_ids + self._historical.active_request_ids
                )
                if (candidate := self._historical.request_for(request_id)) is not None
            )
            validate_historical_plan_limits(
                request,
                outstanding_requests=outstanding,
                maximum_observations_per_request=(
                    self._maximum_historical_observations_per_request
                ),
                maximum_observations_outstanding=(
                    self._maximum_historical_observations_outstanding
                ),
            )
            update = self._historical.enqueue((request,), now_ns=now_ns)
            current = self._historical.request_for(request.request_id)
            if current is None:
                raise RuntimeError("historical coordinator lost an enqueued request")
            self._historical_requests[request.request_id] = current
            self._publish_historical_update(update)
        except ValueError as exc:
            self.log.error(
                "HISTORICAL_PLAN_REJECTED"
                f" | demand_id={plan.demand_id} | error={type(exc).__name__}",
            )

    def _advance_historical(self, _event) -> None:  # noqa: ANN001
        self._publish_historical_update(
            self._historical.advance(now_ns=self.clock.timestamp_ns()),
        )

    def _publish_historical_update(self, update: HistoricalExecutionUpdate) -> None:
        for event in update.events:
            request = self._historical_requests[event.request_id]
            self._historical_counts[event.state.value] += 1
            message = HistoricalExecutionEventMessage(
                event_id=(
                    f"{event.request_id}:{event.state.value}:{event.attempt}:{event.occurred_at_ns}"
                ),
                request_id=event.request_id,
                state=event.state.value,
                attempt=event.attempt,
                instrument_id=request.instrument_id,
                selector=request.selector,
                window=request.window.value,
                start_ns=request.start_ns,
                end_ns=request.end_ns,
                limit=request.limit,
                consumer_ids=tuple(item.consumer_id for item in request.dependencies),
                occurred_at_ns=event.occurred_at_ns,
                source=str(self.actor_id),
                detail=event.detail,
            )
            self.publish_signal(HISTORICAL_EXECUTION_SIGNAL, message.to_signal_value())
            self.log.info(
                f"HISTORICAL_EXECUTION | state={message.state}"
                f" | request_id={message.request_id} | attempt={message.attempt}"
                f" | instrument_id={message.instrument_id} | selector={message.selector}"
                f" | detail={message.detail}",
            )
        batch_type = DataType(HISTORICAL_BATCH_TYPE_NAME)
        for batch in update.batches:
            self.publish_data(batch_type, CustomData(batch_type, batch))
        for result in update.results:
            request = self._historical_requests[result.request_id]
            self._historical_counts[result.state.value] += 1
            message = HistoricalReadinessEvent(
                event_id=(
                    f"{result.request_id}:{result.dependency.consumer_id}:"
                    f"{result.state.value}:{result.completed_at_ns}"
                ),
                request_id=result.request_id,
                consumer_id=result.dependency.consumer_id,
                capability_id=result.dependency.capability_id,
                capability_version=result.dependency.capability_version,
                state=result.state.value,
                instrument_id=request.instrument_id,
                selector=request.selector,
                window=request.window.value,
                minimum_observations=result.dependency.minimum_observations,
                observed_count=result.observed_count,
                completed_at_ns=result.completed_at_ns,
                source=str(self.actor_id),
                reason=result.reason,
            )
            self.publish_signal(HISTORICAL_READINESS_SIGNAL, message.to_signal_value())
            self.log.info(
                f"HISTORICAL_READINESS | state={message.state}"
                f" | consumer_id={message.consumer_id} | request_id={message.request_id}"
                f" | observations={message.observed_count}/{message.minimum_observations}",
            )

    def _observe(
        self,
        instrument_id: str,
        kind: FeedKind,
        selector: str = "default",
    ) -> None:
        stream_key = (instrument_id, kind.value, selector)
        if stream_key not in self._managed_stream_keys:
            return
        self._observation_counts[stream_key] += 1
        event = self._coordinator.observe(stream_key)
        if event is not None:
            self._publish_lifecycle_events((event,))

    def _publish_lifecycle_events(
        self,
        events: tuple[AcquisitionLifecycleEvent, ...],
    ) -> None:
        for event in events:
            self._lifecycle_counts[event.state.value] += 1
            instrument_id, feed_kind, selector = event.stream_key
            message = AcquisitionStreamEvent(
                state=event.state.value,
                instrument_id=instrument_id,
                feed_kind=feed_kind,
                selector=selector,
                source=str(self.actor_id),
                demand_id=event.demand_id,
                consumer_ids=event.consumer_ids,
                detail=event.detail,
            )
            self.publish_signal(ACQUISITION_STREAM_SIGNAL, message.to_signal_value())
            self.log.info(
                f"ACQUISITION_STREAM | state={message.state}"
                f" | instrument_id={message.instrument_id}"
                f" | feed={message.feed_kind}/{message.selector}"
                f" | consumers={len(message.consumer_ids)}"
                f" | detail={message.detail}",
            )


def validate_historical_plan_limits(
    request: HistoricalRequest,
    *,
    outstanding_requests: tuple[HistoricalRequest, ...],
    maximum_observations_per_request: int,
    maximum_observations_outstanding: int,
) -> None:
    """Enforce provider resource limits without interpreting temporal meaning."""

    if request.kind is not FeedKind.BARS:
        raise ValueError("historical acquisition currently executes bar requests only")
    if request.limit > maximum_observations_per_request:
        raise ValueError("historical plan exceeds per-request observation limit")
    if any(item.request_id == request.request_id for item in outstanding_requests):
        return
    outstanding_observations = sum(item.limit for item in outstanding_requests)
    if outstanding_observations + request.limit > maximum_observations_outstanding:
        raise ValueError("historical plan exceeds outstanding observation limit")


def _watchlist_observation_demand(event: WatchlistDemandEvent) -> ObservationDemand:
    return ObservationDemand(
        demand_id=event.demand_id,
        owner=DemandOwner(DemandOwnerKind.WATCHLIST, event.owner_id),
        requirement=FeedRequirement(
            instrument_id=event.instrument_id,
            kind=FeedKind(event.feed_kind),
            selector=event.selector,
        ),
        priority=event.priority,
        purpose=event.purpose,
    )


def _analytical_observation_demand(event: AnalyticalDemandEvent) -> ObservationDemand:
    return ObservationDemand(
        demand_id=event.demand_id,
        owner=DemandOwner(DemandOwnerKind.ANALYZER, event.owner_id),
        requirement=FeedRequirement(
            instrument_id=event.instrument_id,
            kind=FeedKind(event.feed_kind),
            selector=event.selector,
        ),
        priority=event.priority,
        purpose=event.purpose,
    )
