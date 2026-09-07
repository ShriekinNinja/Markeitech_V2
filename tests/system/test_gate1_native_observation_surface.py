"""Characterize the pinned Python ingress limits without native lifecycle execution.

These tests verify the named public Python surfaces, not every possible native
integration. They do not publish Rust reports, measure adapter delivery, or prove
that a Python-originated message reaches the native report path. A changed pin or
new interface requires reviewing the Gate 1 decision, not changing expectations
silently to make this characterization pass.
"""

from __future__ import annotations

import importlib.metadata

import pytest
from nautilus_trader import execution
from nautilus_trader.adapters import interactive_brokers
from nautilus_trader.common import DataActor
from nautilus_trader.live import LiveNode, LiveNodeBuilder


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
    """The missing observation ingress does not reject native client composition."""
    assert callable(LiveNodeBuilder.add_exec_client)
    assert callable(LiveNodeBuilder.with_exec_engine_config)
    assert callable(LiveNode.add_actor)
