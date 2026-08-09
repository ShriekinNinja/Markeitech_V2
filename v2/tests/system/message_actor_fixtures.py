from __future__ import annotations

from threading import Event

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId

from markeitech.system.messages import (
    ACQUISITION_STATUS_REQUEST_SIGNAL,
    ACQUISITION_STATUS_SIGNAL,
    INSTRUMENTS_READY,
    SYSTEM_HEALTH_SIGNAL,
    AcquisitionStatusEvent,
    AcquisitionStatusRequest,
    SystemHealthEvent,
)

received = Event()
ready_received = Event()
received_events: list[SystemHealthEvent] = []


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
