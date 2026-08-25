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
