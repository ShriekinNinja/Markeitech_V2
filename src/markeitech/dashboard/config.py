from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True, slots=True)
class DashboardConfig:
    """Bound startup-only dashboard resources; durations are seconds or milliseconds.

    Policy version 4 exposes only loopback HTTP. History is transient per instrument,
    and the projection interval limits browser publication, not provider cadence.
    """

    policy_version: int = 4
    enabled: bool = False
    port: int = 8765
    maximum_instruments: int = 64
    candles_per_instrument: int = 720
    initial_history_minutes: int = 20
    initial_history_candles: int = 200
    history_page_candles: int = 200
    maximum_history_requests: int = 4
    maximum_history_requests_per_session: int = 256
    history_request_timeout_seconds: int = 120
    publish_interval_ms: int = 250
    acquisition_retry_interval_ms: int = 1000
    maximum_clients: int = 4
    shutdown_timeout_seconds: int = 5

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise ValueError("dashboard.enabled must be a boolean")
        bounds = {
            "policy_version": (4, 4),
            "port": (1024, 65535),
            "maximum_instruments": (1, 256),
            "candles_per_instrument": (2, 5000),
            "initial_history_minutes": (1, 120),
            "initial_history_candles": (1, 1000),
            "history_page_candles": (1, 1000),
            "maximum_history_requests": (1, 16),
            "maximum_history_requests_per_session": (1, 4096),
            "history_request_timeout_seconds": (10, 300),
            "publish_interval_ms": (100, 5000),
            "acquisition_retry_interval_ms": (100, 10000),
            "maximum_clients": (1, 16),
            "shutdown_timeout_seconds": (1, 30),
        }
        for name, (minimum, maximum) in bounds.items():
            value = getattr(self, name)
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"dashboard.{name} must be an integer in {minimum}..{maximum}")

    @property
    def source_history_count(self) -> int:
        """Retain enough five-second inputs to seed any supported forming interval."""
        return 12 * (max(60, min(self.initial_history_minutes, self.candles_per_instrument)) + 1)

    @classmethod
    def from_mapping(cls, values: object) -> DashboardConfig:
        """Validate the optional dashboard policy without reading local configuration."""
        if isinstance(values, dict) and values.get("policy_version") == 3:
            values = dict(values)
            values["policy_version"] = 4
            legacy_page = values.pop("history_page_minutes", 60)
            if type(legacy_page) is not int or not 1 <= legacy_page <= 120:
                raise ValueError("legacy dashboard.history_page_minutes must be 1..120")
            # Preserve the legacy one-minute page count, now at each selected interval.
            values.setdefault("history_page_candles", legacy_page)
        if not isinstance(values, dict) or values.keys() - {f.name for f in fields(cls)}:
            raise ValueError("dashboard must be a table with known policy fields")
        return cls(**values)
