from __future__ import annotations

from pydantic import Field, model_validator

from markeitech.domain.base import VersionedDomainModel


class DiscordRouteConfig(VersionedDomainModel):
    destination_key: str = Field(min_length=1)
    environment_variable: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")


class DiscordDeliveryConfig(VersionedDomainModel):
    enabled: bool = False
    routes: tuple[DiscordRouteConfig, ...] = ()
    poll_interval_seconds: float = Field(default=1.0, gt=0)
    batch_size: int = Field(default=10, ge=1, le=100)
    request_timeout_seconds: float = Field(default=10.0, gt=0)
    base_retry_seconds: float = Field(default=2.0, gt=0)
    max_retry_seconds: float = Field(default=300.0, gt=0)

    @model_validator(mode="after")
    def _routes_must_be_usable(self) -> DiscordDeliveryConfig:
        if self.enabled and not self.routes:
            raise ValueError("enabled Discord delivery requires at least one route")
        keys = [route.destination_key for route in self.routes]
        if len(keys) != len(set(keys)):
            raise ValueError("Discord destination keys must be unique")
        variables = [route.environment_variable for route in self.routes]
        if len(variables) != len(set(variables)):
            raise ValueError("Discord route environment variables must be unique")
        if self.max_retry_seconds < self.base_retry_seconds:
            raise ValueError("maximum Discord retry must not precede base retry")
        return self
