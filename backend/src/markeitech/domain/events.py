from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from markeitech.domain.base import VersionedDomainModel, require_utc


class GatewayEventType(StrEnum):
    SNAPSHOT = "snapshot"
    BAR_ACTIVE = "bar.active"
    BAR_COMPLETED = "bar.completed"
    READINESS_UPDATE = "readiness.update"
    HEALTH_UPDATE = "health.update"
    GAP_UPDATE = "gap.update"
    LEVEL_UPSERT = "level.upsert"
    ZONE_UPSERT = "zone.upsert"
    SIGNAL_UPSERT = "signal.upsert"
    SIGNAL_TRANSITION = "signal.transition"
    STRATEGY_STATE = "strategy.state"
    ORDER_EXECUTION = "order.execution"


class StrategyState(StrEnum):
    REGISTERED = "registered"
    LOADING = "loading"
    WARMING_UP = "warming_up"
    PAPER = "paper"
    LIVE = "live"
    PAUSED = "paused"
    STOPPING = "stopping"
    FAILED = "failed"
    RETIRED = "retired"


class GatewayEvent(VersionedDomainModel):
    event_type: GatewayEventType
    instrument_id: str = Field(min_length=1)
    event_ts: datetime
    ts_init: datetime
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_ts", "ts_init")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)


class StrategyStateEvent(VersionedDomainModel):
    strategy_id: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    deployment_id: str = Field(min_length=1)
    state: StrategyState
    event_ts: datetime
    ts_init: datetime
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("event_ts", "ts_init")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)
