from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from markeitech.system.composition import StartupPrerequisites
from markeitech.system.config import load_system_config
from markeitech.system.node import build_system_node


def test_builds_v2_node_without_connecting() -> None:
    root = Path(__file__).parents[2]
    config = load_system_config(root / "config/system.toml")

    node = build_system_node(
        config,
        StartupPrerequisites(run_id=uuid4(), operational_persistence_ready=True),
    )

    assert str(node.trader_id) == config.runtime.trader_id
    assert node.is_running is False
