from __future__ import annotations

from datetime import date
from decimal import Decimal
from threading import Event

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, CustomData, DataType

from markeitech.intelligence import (
    COMPLETED_BAR_INPUT_TYPE_NAME,
    ENTITY_REVISION_TYPE_NAME,
    ENTITY_SNAPSHOT_REQUEST_TYPE_NAME,
    ENTITY_SNAPSHOT_TYPE_NAME,
    METRIC_VALUE_TYPE_NAME,
    CompletedBarInput,
    CompletedBarSource,
    EntityLifecycle,
    EntityRevision,
    EntitySnapshotRequest,
    EntitySnapshotResponse,
    MetricFidelity,
    MetricHealth,
    MetricValue,
)
from markeitech.intelligence.actors import SessionStateActor
from markeitech.intelligence.calendar_messages import (
    CALENDAR_PROJECTION_REQUEST_TYPE_NAME,
    CALENDAR_PROJECTION_RESPONSE_TYPE_NAME,
    CALENDAR_STATE_SNAPSHOT_REQUEST_TYPE_NAME,
    CALENDAR_STATE_SNAPSHOT_RESPONSE_TYPE_NAME,
    CALENDAR_TRANSITION_TYPE_NAME,
    CALENDAR_TRANSITION_V2_TYPE_NAME,
    CalendarDefinitionExpectation,
    CalendarProjectionRequest,
    CalendarProjectionResponse,
    CalendarStateSnapshotRequest,
    CalendarStateSnapshotResponse,
    CalendarTransition,
    CalendarTransitionV2,
)
from markeitech.system.messages import (
    ACQUISITION_STATUS_REQUEST_SIGNAL,
    ACQUISITION_STATUS_SIGNAL,
    INSTRUMENTS_READY,
    PERSISTENCE_READY_REQUEST_SIGNAL,
    PERSISTENCE_READY_SIGNAL,
    SYSTEM_HEALTH_SIGNAL,
    AcquisitionStatusEvent,
    AcquisitionStatusRequest,
    PersistenceReadyEvent,
    PersistenceReadyRequest,
    SystemHealthEvent,
)

received = Event()
ready_received = Event()
received_events: list[SystemHealthEvent] = []
entity_received = Event()
market_state_received = Event()
received_entity_revisions: list[EntityRevision] = []
snapshot_received = Event()
received_entity_snapshots: list[EntitySnapshotResponse] = []
calendar_received = Event()
received_calendar_transitions: list[CalendarTransition] = []
received_calendar_projections: list[CalendarProjectionResponse] = []
current_state_received = Event()
received_current_state_snapshots: list[CalendarStateSnapshotResponse] = []
received_calendar_transitions_v2: list[CalendarTransitionV2] = []
inspectable_session_state_actors: list[SessionStateActor] = []
projection_requests_complete = Event()
received_projection_requests: list[CalendarProjectionRequest] = []


class PersistenceReadyFixtureConfig(DataActorConfig):
    def __new__(
        cls,
        actor_id: str | ActorId = "PERSISTENCE-READY-FIXTURE",
    ) -> PersistenceReadyFixtureConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        return super().__new__(cls, actor_id=resolved)


class PersistenceReadyFixture(DataActor):
    def on_start(self) -> None:
        self.subscribe_signal(PERSISTENCE_READY_REQUEST_SIGNAL)
        self._publish_ready()

    def on_signal(self, signal: Signal) -> None:
        PersistenceReadyRequest.from_signal_value(signal.value)
        self._publish_ready()

    def _publish_ready(self) -> None:
        event = PersistenceReadyEvent(
            source=str(self.actor_id),
            run_id="36a468b3-df4b-49fa-809e-c60e8d19d9a0",
        )
        self.publish_signal(PERSISTENCE_READY_SIGNAL, event.to_signal_value())


class CalendarProjectionRequestCaptureConfig(DataActorConfig):
    def __new__(
        cls,
        expected_requesters: list[str],
        target_per_requester: int,
        actor_id: str | ActorId = "CALENDAR-PROJECTION-REQUEST-CAPTURE",
    ) -> CalendarProjectionRequestCaptureConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.expected_requesters = tuple(expected_requesters)
        obj.target_per_requester = target_per_requester
        return obj


class CalendarProjectionRequestCapture(DataActor):
    def __init__(self, config: CalendarProjectionRequestCaptureConfig) -> None:
        super().__init__(config)
        self._expected_requesters = config.expected_requesters
        self._target_per_requester = config.target_per_requester
        self._request_type = DataType(CALENDAR_PROJECTION_REQUEST_TYPE_NAME)

    def on_start(self) -> None:
        self.subscribe_data(self._request_type)

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if not isinstance(payload, CalendarProjectionRequest):
            return
        received_projection_requests.append(payload)
        counts = {
            requester: sum(
                item.requester == requester for item in received_projection_requests
            )
            for requester in self._expected_requesters
        }
        if all(value >= self._target_per_requester for value in counts.values()):
            projection_requests_complete.set()

    def on_stop(self) -> None:
        self.unsubscribe_data(self._request_type)


class HealthSubscriberConfig(DataActorConfig):
    def __new__(cls, actor_id: str | ActorId = "HEALTH-SUBSCRIBER") -> HealthSubscriberConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        return super().__new__(cls, actor_id=resolved)


class HealthSubscriber(DataActor):
    def on_start(self) -> None:
        self.subscribe_signal(SYSTEM_HEALTH_SIGNAL)

    def on_signal(self, signal: Signal) -> None:
        event = SystemHealthEvent.from_signal_value(signal.value)
        received_events.append(event)
        if event.state == "READY":
            ready_received.set()
        received.set()


class HealthPublisherConfig(DataActorConfig):
    def __new__(cls, actor_id: str | ActorId = "HEALTH-PUBLISHER") -> HealthPublisherConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        return super().__new__(cls, actor_id=resolved)


class HealthPublisher(DataActor):
    def on_start(self) -> None:
        event = SystemHealthEvent(
            state="READY",
            reason="contract probe",
            source=str(self.actor_id),
            evidence={"probe": True},
        )
        self.publish_signal(SYSTEM_HEALTH_SIGNAL, event.to_signal_value())


class AcquisitionReadyFixtureConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_ids: list[str],
        actor_id: str | ActorId = "ACQUISITION-READY-FIXTURE",
    ) -> AcquisitionReadyFixtureConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.instrument_ids = tuple(instrument_ids)
        return obj


class AcquisitionReadyFixture(DataActor):
    def __init__(self, config: AcquisitionReadyFixtureConfig) -> None:
        super().__init__(config)
        self._instrument_ids = tuple(config.instrument_ids)

    def on_start(self) -> None:
        self.subscribe_signal(ACQUISITION_STATUS_REQUEST_SIGNAL)
        self._publish_ready()

    def on_signal(self, signal: Signal) -> None:
        AcquisitionStatusRequest.from_signal_value(signal.value)
        self._publish_ready()

    def _publish_ready(self) -> None:
        event = AcquisitionStatusEvent(
            state=INSTRUMENTS_READY,
            reason="fixture definitions available",
            source=str(self.actor_id),
            expected_instrument_ids=self._instrument_ids,
            available_instrument_ids=self._instrument_ids,
        )
        self.publish_signal(ACQUISITION_STATUS_SIGNAL, event.to_signal_value())


class CalendarProjectionProbeConfig(DataActorConfig):
    def __new__(
        cls,
        calendar_id: str,
        projection_days: int = 1,
        actor_id: str | ActorId = "CALENDAR-PROJECTION-PROBE",
    ) -> CalendarProjectionProbeConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.calendar_id = calendar_id
        obj.projection_days = projection_days
        return obj


class CalendarProjectionProbe(DataActor):
    def __init__(self, config: CalendarProjectionProbeConfig) -> None:
        super().__init__(config)
        self._calendar_id = config.calendar_id
        self._projection_days = config.projection_days
        self._request_type = DataType(CALENDAR_PROJECTION_REQUEST_TYPE_NAME)
        self._response_type = DataType(CALENDAR_PROJECTION_RESPONSE_TYPE_NAME)
        self._transition_type = DataType(CALENDAR_TRANSITION_TYPE_NAME)
        self._requested = False

    def on_start(self) -> None:
        self.subscribe_data(self._response_type)
        self.subscribe_data(self._transition_type)

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, CalendarTransition):
            received_calendar_transitions.append(payload)
            if self._requested or payload.calendar_id != self._calendar_id:
                return
            self._requested = True
            now_ns = self.clock.timestamp_ns()
            request = CalendarProjectionRequest(
                request_id="calendar-projection-message-fixture",
                requester=str(self.actor_id),
                calendar_ids=(self._calendar_id,),
                start_ns=max(0, now_ns - self._projection_days * 86_400_000_000_000),
                end_ns=now_ns + self._projection_days * 86_400_000_000_000,
                requested_ts_ns=now_ns,
            )
            self.publish_data(
                self._request_type,
                CustomData(self._request_type, request),
            )
        elif isinstance(payload, CalendarProjectionResponse):
            if payload.requester != str(self.actor_id):
                return
            received_calendar_projections.append(payload)
            calendar_received.set()

    def on_stop(self) -> None:
        self.unsubscribe_data(self._response_type)
        self.unsubscribe_data(self._transition_type)


class CalendarCurrentStateProbeConfig(DataActorConfig):
    def __new__(
        cls,
        calendar_id: str,
        definition_version: int,
        definition_digest: str,
        definition_effective_from_ns: int,
        source_epoch: str,
        additional_expectations: list[dict[str, object]] | None = None,
        request_on_start: bool = False,
        actor_id: str | ActorId = "CURRENT-STATE-PROBE",
    ) -> CalendarCurrentStateProbeConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.calendar_id = calendar_id
        obj.definition_version = definition_version
        obj.definition_digest = definition_digest
        obj.definition_effective_from_ns = definition_effective_from_ns
        obj.source_epoch = source_epoch
        obj.additional_expectations = tuple(additional_expectations or ())
        obj.request_on_start = request_on_start
        return obj


class CalendarCurrentStateProbe(DataActor):
    def __init__(self, config: CalendarCurrentStateProbeConfig) -> None:
        super().__init__(config)
        self._expectations = (
            CalendarDefinitionExpectation(
                calendar_id=config.calendar_id,
                definition_version=config.definition_version,
                definition_digest=config.definition_digest,
                definition_effective_from_ns=config.definition_effective_from_ns,
            ),
            *(
                CalendarDefinitionExpectation(
                    calendar_id=str(item["calendar_id"]),
                    definition_version=int(item["definition_version"]),
                    definition_digest=str(item["definition_digest"]),
                    definition_effective_from_ns=int(item["definition_effective_from_ns"]),
                )
                for item in config.additional_expectations
            ),
        )
        self._source_epoch = config.source_epoch
        self._request_on_start = config.request_on_start
        self._request_type = DataType(CALENDAR_STATE_SNAPSHOT_REQUEST_TYPE_NAME)
        self._response_type = DataType(CALENDAR_STATE_SNAPSHOT_RESPONSE_TYPE_NAME)
        self._transition_type = DataType(CALENDAR_TRANSITION_TYPE_NAME)
        self._transition_v2_type = DataType(CALENDAR_TRANSITION_V2_TYPE_NAME)
        self._request: CalendarStateSnapshotRequest | None = None

    def on_start(self) -> None:
        self.subscribe_data(self._response_type)
        self.subscribe_data(self._transition_type)
        self.subscribe_data(self._transition_v2_type)
        if self._request_on_start:
            self.clock.set_time_alert_ns(
                "current-state-probe-request",
                self.clock.timestamp_ns() + 1_000_000,
                callback=self._request_timer,
            )

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, CalendarTransitionV2):
            received_calendar_transitions_v2.append(payload)
            return
        if isinstance(payload, CalendarTransition):
            received_calendar_transitions.append(payload)
            if self._request is not None or payload.calendar_id not in {
                item.calendar_id for item in self._expectations
            }:
                return
            self._create_and_publish_request()
            return
        if not isinstance(payload, CalendarStateSnapshotResponse):
            return
        if payload.requester != str(self.actor_id):
            return
        received_current_state_snapshots.append(payload)
        if len(received_current_state_snapshots) == 1:
            self._publish_request()
        else:
            current_state_received.set()

    def on_stop(self) -> None:
        if "current-state-probe-request" in self.clock.timer_names():
            self.clock.cancel_timer("current-state-probe-request")
        self.unsubscribe_data(self._response_type)
        self.unsubscribe_data(self._transition_type)
        self.unsubscribe_data(self._transition_v2_type)

    def _publish_request(self) -> None:
        if self._request is None:
            return
        self.publish_data(
            self._request_type,
            CustomData(self._request_type, self._request),
        )

    def _create_and_publish_request(self) -> None:
        now_ns = self.clock.timestamp_ns()
        self._request = CalendarStateSnapshotRequest(
            cycle_id="current-state-probe-cycle",
            request_id="current-state-probe-attempt-1",
            attempt=1,
            requester=str(self.actor_id),
            expected_source="SESSION-STATE",
            expected_source_epoch=self._source_epoch,
            calendar_expectations=self._expectations,
            requested_as_of_ns=now_ns,
            requested_ts_ns=now_ns,
            deadline_ts_ns=now_ns + 5_000_000_000,
            delivery_policy_version=1,
        )
        self._publish_request()

    def _request_timer(self, _event) -> None:  # noqa: ANN001
        if self._request is None:
            self._create_and_publish_request()


class MultiCalendarProjectionProbeConfig(DataActorConfig):
    def __new__(
        cls,
        calendar_ids: list[str],
        projection_days: int,
        actor_id: str | ActorId = "CALENDAR-PROJECTION-PROBE",
    ) -> MultiCalendarProjectionProbeConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.calendar_ids = tuple(calendar_ids)
        obj.projection_days = projection_days
        return obj


class MultiCalendarProjectionProbe(DataActor):
    def __init__(self, config: MultiCalendarProjectionProbeConfig) -> None:
        super().__init__(config)
        self._calendar_ids = config.calendar_ids
        self._projection_days = config.projection_days
        self._request_type = DataType(CALENDAR_PROJECTION_REQUEST_TYPE_NAME)
        self._response_type = DataType(CALENDAR_PROJECTION_RESPONSE_TYPE_NAME)
        self._transition_type = DataType(CALENDAR_TRANSITION_TYPE_NAME)
        self._requested = False

    def on_start(self) -> None:
        self.subscribe_data(self._response_type)
        self.subscribe_data(self._transition_type)

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, CalendarTransition):
            if self._requested or payload.calendar_id not in self._calendar_ids:
                return
            self._requested = True
            now_ns = self.clock.timestamp_ns()
            request = CalendarProjectionRequest(
                request_id="multi-calendar-projection-message-fixture",
                requester=str(self.actor_id),
                calendar_ids=self._calendar_ids,
                start_ns=max(0, now_ns - self._projection_days * 86_400_000_000_000),
                end_ns=now_ns + self._projection_days * 86_400_000_000_000,
                requested_ts_ns=now_ns,
            )
            self.publish_data(
                self._request_type,
                CustomData(self._request_type, request),
            )
        elif isinstance(payload, CalendarProjectionResponse):
            if payload.requester != str(self.actor_id):
                return
            received_calendar_projections.append(payload)
            calendar_received.set()

    def on_stop(self) -> None:
        self.unsubscribe_data(self._response_type)
        self.unsubscribe_data(self._transition_type)


class _LongRangeFailingProvider:
    def __init__(self, delegate) -> None:  # noqa: ANN001
        self._delegate = delegate

    def schedule(self, **kwargs):  # noqa: ANN003, ANN201
        start = date.fromisoformat(str(kwargs["start_date"]))
        end = date.fromisoformat(str(kwargs["end_date"]))
        if (end - start).days > 10:
            raise ValueError("injected projection construction failure")
        return self._delegate.schedule(**kwargs)


class FailingProjectionSessionStateActor(SessionStateActor):
    def __init__(self, config) -> None:  # noqa: ANN001
        super().__init__(config)
        calendar = self._calendars["cme_equity"]
        object.__setattr__(
            calendar,
            "_provider",
            _LongRangeFailingProvider(calendar._provider),
        )


class InspectableSessionStateActor(SessionStateActor):
    def __init__(self, config) -> None:  # noqa: ANN001
        super().__init__(config)
        inspectable_session_state_actors.append(self)


class EntityMetricPublisherConfig(DataActorConfig):
    def __new__(
        cls,
        actor_id: str | ActorId = "ENTITY-METRIC-PUBLISHER",
    ) -> EntityMetricPublisherConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        return super().__new__(cls, actor_id=resolved)


class EntityMetricPublisher(DataActor):
    def on_start(self) -> None:
        data_type = DataType(METRIC_VALUE_TYPE_NAME)
        value = MetricValue(
            metric_id="previous_session.high",
            metric_version=1,
            parameter_version=1,
            instrument_id="ESU6.CME",
            session_id="cme_equity:2026-08-21:OPEN",
            value=Decimal("6500.25"),
            unit="price",
            effective_ts_ns=100,
            observed_ts_ns=100,
            received_ts_ns=100,
            calculated_ts_ns=100,
            published_ts_ns=100,
            health=MetricHealth.READY,
            fidelity=MetricFidelity.DERIVED,
            source=str(self.actor_id),
            evidence_refs=("metric:previous_session.high:fixture",),
            missing_reasons=(),
            revision=1,
        )
        self.publish_data(data_type, CustomData(data_type, value))


class MarketStateMetricPublisherConfig(DataActorConfig):
    def __new__(
        cls,
        actor_id: str | ActorId = "MARKET-STATE-METRIC-PUBLISHER",
    ) -> MarketStateMetricPublisherConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        return super().__new__(cls, actor_id=resolved)


class MarketStateMetricPublisher(DataActor):
    def on_start(self) -> None:
        data_type = DataType(METRIC_VALUE_TYPE_NAME)
        timestamp = self.clock.timestamp_ns()
        for metric_id, value in (
            ("rolling.fast.context_45m.coverage_ratio", Decimal("1")),
            ("rolling.fast.context_45m.range_percentile_recent", Decimal("0.8")),
        ):
            metric = MetricValue(
                metric_id=metric_id,
                metric_version=1,
                parameter_version=1,
                instrument_id="ESU6.CME",
                session_id="cme_equity:2026-08-23:OPEN",
                value=value,
                unit="ratio",
                effective_ts_ns=timestamp,
                observed_ts_ns=timestamp,
                received_ts_ns=timestamp,
                calculated_ts_ns=timestamp,
                published_ts_ns=timestamp,
                health=MetricHealth.READY,
                fidelity=MetricFidelity.DERIVED,
                source=str(self.actor_id),
                evidence_refs=(f"metric:{metric_id}:fixture",),
                missing_reasons=(),
                revision=1,
            )
            self.publish_data(data_type, CustomData(data_type, metric))


class EntityRevisionSubscriberConfig(DataActorConfig):
    def __new__(
        cls,
        actor_id: str | ActorId = "ENTITY-REVISION-SUBSCRIBER",
    ) -> EntityRevisionSubscriberConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        return super().__new__(cls, actor_id=resolved)


class EntityRevisionSubscriber(DataActor):
    def __init__(self, config: EntityRevisionSubscriberConfig) -> None:
        super().__init__(config)
        self._data_type = DataType(ENTITY_REVISION_TYPE_NAME)
        self._snapshot_type = DataType(ENTITY_SNAPSHOT_TYPE_NAME)

    def on_start(self) -> None:
        self.subscribe_data(self._data_type)
        self.subscribe_data(self._snapshot_type)

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if isinstance(payload, EntityRevision):
            received_entity_revisions.append(payload)
            entity_received.set()
            if (
                payload.identity.entity_type == "volatility_state"
                and payload.lifecycle is EntityLifecycle.ACTIVE
            ):
                market_state_received.set()
        elif isinstance(payload, EntitySnapshotResponse):
            received_entity_snapshots.append(payload)
            snapshot_received.set()


class EntitySnapshotRequesterConfig(DataActorConfig):
    def __new__(
        cls,
        actor_id: str | ActorId = "ENTITY-SNAPSHOT-REQUESTER",
    ) -> EntitySnapshotRequesterConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        return super().__new__(cls, actor_id=resolved)


class EntitySnapshotRequester(DataActor):
    def on_start(self) -> None:
        data_type = DataType(ENTITY_SNAPSHOT_REQUEST_TYPE_NAME)
        request = EntitySnapshotRequest(
            request_id="market-structure-fixture-snapshot",
            requester=str(self.actor_id),
            requested_ts_ns=self.clock.timestamp_ns(),
            instrument_id="ESU6.CME",
            entity_type="confirmed_swing",
        )
        self.publish_data(data_type, CustomData(data_type, request))


class CompletedBarPublisherConfig(DataActorConfig):
    def __new__(
        cls,
        actor_id: str | ActorId = "COMPLETED-BAR-PUBLISHER",
    ) -> CompletedBarPublisherConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        return super().__new__(cls, actor_id=resolved)


class CompletedBarPublisher(DataActor):
    def on_start(self) -> None:
        data_type = DataType(COMPLETED_BAR_INPUT_TYPE_NAME)
        minute_ns = 60_000_000_000
        for index, (open_, high, low, close) in enumerate(
            (
                ("98", "100", "95", "99"),
                ("101", "106", "99", "104"),
                ("102", "103", "101", "102"),
                ("101", "102", "96", "97"),
                ("99", "104", "98", "103"),
                ("102", "103", "97", "98"),
            ),
        ):
            start_ns = (index + 1) * 5 * minute_ns
            value = CompletedBarInput(
                instrument_id="ESU6.CME",
                bar_specification="5-MINUTE-LAST-EXTERNAL",
                calendar_id="cme_equity",
                analytical_profile_id="cme_equity_primary",
                analytical_profile_version=1,
                trade_date=date(2026, 8, 24),
                session_id="cme_equity:2026-08-24:OPEN",
                window_id="primary",
                interval_start_ns=start_ns,
                interval_end_ns=start_ns + 5 * minute_ns,
                open=Decimal(open_),
                high=Decimal(high),
                low=Decimal(low),
                close=Decimal(close),
                volume=Decimal("100"),
                source=CompletedBarSource.LIVE_AGGREGATE,
                observed_ts_ns=start_ns + 5 * minute_ns,
                received_ts_ns=start_ns + 5 * minute_ns + 1,
                normalized_ts_ns=start_ns + 5 * minute_ns + 2,
                health=MetricHealth.READY,
                fidelity=MetricFidelity.REPORTED,
                evidence_refs=(f"bar:{index}",),
                complete=True,
                missing_reasons=(),
            )
            self.publish_data(data_type, CustomData(data_type, value))
