from __future__ import annotations

from nautilus_trader.common import Environment, ImportableActorConfig
from nautilus_trader.live import LiveNode
from nautilus_trader.model import TraderId

from tests.system.message_actor_fixtures import received, received_events


def test_health_signal_delivers_between_actors_in_one_live_node() -> None:
    received.clear()
    received_events.clear()
    node = LiveNode.builder(
        "MARKEITECH-V2-MESSAGE-TEST",
        TraderId.from_str("MARKEITECH-TEST-001"),
        Environment.SANDBOX,
    ).build()
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:HealthSubscriber",
            config_path="tests.system.message_actor_fixtures:HealthSubscriberConfig",
            config={"actor_id": "HEALTH-SUBSCRIBER"},
        ),
    )
    node.add_actor_from_config(
        ImportableActorConfig(
            actor_path="tests.system.message_actor_fixtures:HealthPublisher",
            config_path="tests.system.message_actor_fixtures:HealthPublisherConfig",
            config={"actor_id": "HEALTH-PUBLISHER"},
        ),
    )

    try:
        node.start()
        assert received.wait(timeout=2)
    finally:
        node.stop()

    assert len(received_events) == 1
    assert received_events[0].state == "READY"
    assert received_events[0].evidence == {"probe": True}

