"""Characterize native Python alternatives without provider or node lifecycle execution.

These tests verify the named public Python surfaces, not every possible native
integration. They do not publish Rust reports, measure adapter delivery, or prove
that a Python-originated message reaches the native report path. A changed pin or
new interface requires reviewing the Gate 1 decision, not changing expectations
silently to make this characterization pass.
Strategy callbacks are a separate supported surface. Their presence and offline
construction do not establish native event dispatch or manual TWS delivery.
"""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys

import pytest
from nautilus_trader import execution
from nautilus_trader.adapters import interactive_brokers
from nautilus_trader.common import DataActor
from nautilus_trader.live import LiveNode, LiveNodeBuilder
from nautilus_trader.trading import Strategy, StrategyConfig


@pytest.mark.parametrize(
    ("surface", "missing_names"),
    [
        (
            DataActor,
            (
                "msgbus",
                "on_report",
                "on_order_status_report",
                "on_fill_report",
                "on_position_status_report",
                "on_order_event",
            ),
        ),
        (
            LiveNode,
            (
                "msgbus",
                "execution_engine",
                "get_execution_client",
                "generate_mass_status",
                "add_stream_processor",
            ),
        ),
        (LiveNodeBuilder, ("add_stream_processor",)),
        (interactive_brokers.InteractiveBrokersExecutionClientFactory, ("create",)),
        (interactive_brokers, ("InteractiveBrokersExecutionClient",)),
        (execution, ("ExecutionEngine",)),
    ],
    ids=["data-actor", "live-node", "builder", "execution-factory", "ib-exports", "engine"],
)
def test_gate1_pinned_python_ingress_limits(
    surface: object,
    missing_names: tuple[str, ...],
) -> None:
    assert importlib.metadata.version("nautilus_trader") == "2.0.0rc4", (
        "Gate 1 ingress evidence is bound to rc4; review the new native contract"
    )
    newly_available = [name for name in missing_names if hasattr(surface, name)]
    assert not newly_available, (
        "Gate 1's named Python ingress surface changed; reassess the documented "
        f"limitation before selecting a harness: {newly_available}"
    )


def test_gate1_native_composition_remains_available() -> None:
    """Limits on named raw-report interfaces do not reject native composition."""
    assert callable(LiveNodeBuilder.add_exec_client)
    assert callable(LiveNodeBuilder.with_exec_engine_config)
    assert callable(LiveNode.add_actor)
    assert callable(LiveNode.add_strategy)


def test_gate1_strategy_execution_callbacks_are_available() -> None:
    """Do not infer missing Python execution events from DataActor's surface."""
    for name in (
        "on_order_event",
        "on_order_accepted",
        "on_order_updated",
        "on_order_canceled",
        "on_order_filled",
        "on_position_event",
        "on_position_opened",
        "on_position_changed",
        "on_position_closed",
        "publish_signal",
    ):
        assert callable(getattr(Strategy, name))
    assert callable(DataActor.subscribe_signal)
    assert callable(DataActor.on_signal)


def test_gate1_strategy_management_defaults_are_disabled() -> None:
    """These flags are not a capability sandbox or proof of no native attempts."""
    config = StrategyConfig()
    assert config.manage_contingent_orders is False
    assert config.manage_gtd_expiry is False
    assert config.manage_stop is False
    assert not config.external_order_claims


def test_gate1_strategy_registers_offline_without_a_provider() -> None:
    """Exercise native registration, without a client, lifecycle, or order call."""
    source = """
from nautilus_trader.common import Environment, LoggerConfig
from nautilus_trader.live import LiveNode
from nautilus_trader.model import TraderId
from nautilus_trader.trading import Strategy, StrategyConfig

class ObservationCandidate(Strategy):
    def on_order_event(self, event):
        pass

    def on_position_event(self, event):
        pass

node = (
    LiveNode.builder("Gate1StrategyOffline", TraderId("GATE1-001"), Environment.SANDBOX)
    .with_logging(LoggerConfig(bypass_logging=True))
    .build()
)
observer = ObservationCandidate(StrategyConfig())
node.add_strategy(observer)
assert node.is_running is False
assert observer.is_running() is False
print("GATE1_STRATEGY_REGISTERED_OFFLINE")
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", source],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "GATE1_STRATEGY_REGISTERED_OFFLINE" in result.stdout


def test_gate1_strategy_signal_reaches_actor_through_native_dispatch() -> None:
    """Measure only scalar forwarding; this does not inject an execution event."""
    source = '''
from nautilus_trader.common import DataActor, Environment, LoggerConfig
from nautilus_trader.live import LiveNode
from nautilus_trader.model import TraderId
from nautilus_trader.trading import Strategy, StrategyConfig

seen = []
execution_events = []

class Sink(DataActor):
    # Direct component lifecycle needs no-op hooks in installed rc4.
    def on_start(self):
        pass

    def on_stop(self):
        pass

    def on_signal(self, signal):
        seen.append((type(signal).__name__, str(signal.value), signal.ts_event))

class Observer(Strategy):
    def on_start(self):
        pass

    def on_stop(self):
        pass

    def on_order_event(self, event):
        execution_events.append("order")

    def on_position_event(self, event):
        execution_events.append("position")

node = (
    LiveNode.builder("Gate1SignalOffline", TraderId("GATE1-001"), Environment.SANDBOX)
    .with_logging(LoggerConfig(bypass_logging=True))
    .build()
)
sink = Sink()
observer = Observer(StrategyConfig(
    manage_contingent_orders=False,
    manage_gtd_expiry=False,
    manage_stop=False,
    log_events=False,
    log_commands=False,
))
node.add_actor(sink)
node.add_strategy(observer)
# Subscribe after registration, outside on_start's native mutable borrow.
sink.subscribe_signal("gate1_offline")
sink.start()
observer.start()
try:
    assert sink.is_running() and observer.is_running()
    payload = '{"origin":"synthetic_offline","event":"signal_probe"}'
    observer.publish_signal("gate1_offline", payload, 123)
    assert seen == [("Signal", payload, 123)], seen
    assert execution_events == []
    assert node.is_running is False
finally:
    observer.stop()
    sink.stop()
assert not observer.is_running() and not sink.is_running()
print("GATE1_NATIVE_SIGNAL_FORWARDED_OFFLINE")
'''
    result = subprocess.run(
        [sys.executable, "-B", "-c", source],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "GATE1_NATIVE_SIGNAL_FORWARDED_OFFLINE" in result.stdout
