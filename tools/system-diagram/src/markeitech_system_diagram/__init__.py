"""Offline Markeitech architecture-manifest tooling.

This package is intentionally independent from the Markeitech and NautilusTrader runtimes.
"""

from .diagnostics import ManifestError
from .loader import load_manifest
from .models import ArchitectureManifest

__version__ = "0.1.0"

__all__ = ["ArchitectureManifest", "ManifestError", "__version__", "load_manifest"]
