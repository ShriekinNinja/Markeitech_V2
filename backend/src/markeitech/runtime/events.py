from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, computed_field, field_validator, model_validator

from markeitech.domain.base import VersionedDomainModel, require_utc


class MarkeitechBusTopic(StrEnum):
    FEATURE_COMMITTED = "markeitech.analytics.feature.committed"
    MARKET_OBSERVATION_COMMITTED = "markeitech.market.observation.committed"
    CONTEXT_EVENT = "markeitech.context.event"
    SIGNAL_LIFECYCLE = "markeitech.signal.lifecycle"
    OPERATOR_PROJECTION = "markeitech.operator.projection"
    RUNTIME_HEALTH = "markeitech.runtime.health"


class CommittedDomainEvent(VersionedDomainModel):
    """Immutable notice that durable evidence is available to bus consumers."""

    topic: MarkeitechBusTopic
    event_id: str = Field(min_length=1)
    occurred_ts: datetime
    aggregate_id: str = Field(min_length=1)
    payload_type: str = Field(min_length=1)
    payload_id: str = Field(min_length=1)
    instrument_id: str | None = Field(default=None, min_length=1)
    commit_sequence: int | None = Field(default=None, ge=1)

    @field_validator("occurred_ts")
    @classmethod
    def _occurred_ts_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _committed_topics_require_sequence(self) -> CommittedDomainEvent:
        commit_coupled = {
            MarkeitechBusTopic.FEATURE_COMMITTED,
            MarkeitechBusTopic.MARKET_OBSERVATION_COMMITTED,
        }
        if self.topic in commit_coupled and self.commit_sequence is None:
            raise ValueError(f"{self.topic.value} requires a durable commit sequence")
        return self

    @computed_field
    @property
    def dedupe_key(self) -> str:
        return f"{self.topic.value}:{self.event_id}"
