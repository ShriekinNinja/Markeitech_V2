from __future__ import annotations

from threading import Event

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId

from markeitech.system.messages import SYSTEM_HEALTH_SIGNAL, SystemHealthEvent

received = Event()
received_events: list[SystemHealthEvent] = []


class HealthSubscriberConfig(DataActorConfig):
    def __new__(cls, actor_id: str | ActorId = "HEALTH-SUBSCRIBER") -> HealthSubscriberConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        return super().__new__(cls, actor_id=resolved)


class HealthSubscriber(DataActor):
    def on_start(self) -> None:
        self.subscribe_signal(SYSTEM_HEALTH_SIGNAL)

    def on_signal(self, signal: Signal) -> None:
        received_events.append(SystemHealthEvent.from_signal_value(signal.value))
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
