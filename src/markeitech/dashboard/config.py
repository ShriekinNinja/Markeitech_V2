from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True, slots=True)
class DashboardConfig:
    """Bound startup-only dashboard resources; durations are seconds or milliseconds.

    Policy version 1 exposes only loopback HTTP. History is transient per instrument,
    and the projection interval limits browser publication, not provider cadence.
    """

    policy_version: int = 1
    enabled: bool = False
    port: int = 8765
    maximum_instruments: int = 64
    candles_per_instrument: int = 720
    publish_interval_ms: int = 250
    acquisition_retry_interval_ms: int = 1000
    maximum_clients: int = 4
    shutdown_timeout_seconds: int = 5

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise ValueError("dashboard.enabled must be a boolean")
        bounds = {
            "policy_version": (1, 1),
            "port": (1024, 65535),
            "maximum_instruments": (1, 256),
            "candles_per_instrument": (2, 5000),
            "publish_interval_ms": (100, 5000),
            "acquisition_retry_interval_ms": (100, 10000),
            "maximum_clients": (1, 16),
            "shutdown_timeout_seconds": (1, 30),
        }
        for name, (minimum, maximum) in bounds.items():
            value = getattr(self, name)
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"dashboard.{name} must be an integer in {minimum}..{maximum}")

    @classmethod
    def from_mapping(cls, values: object) -> DashboardConfig:
        """Validate the optional dashboard policy without reading local configuration."""
        if not isinstance(values, dict) or values.keys() - {f.name for f in fields(cls)}:
            raise ValueError("dashboard must be a table with known policy fields")
        return cls(**values)
