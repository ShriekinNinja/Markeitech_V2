"""System foundation for the Markeitech v2 runtime."""

# Temporary issue #34 fixture: this source change should make tracked API docs stale.

from markeitech.system.config import SystemConfig, load_system_config
from markeitech.system.node import build_system_node

__all__ = ["SystemConfig", "build_system_node", "load_system_config"]
