from __future__ import annotations

import hashlib
import json
from enum import StrEnum

from pydantic import Field, model_validator

from markeitech.analytics import AnalyticsTimeframe
from markeitech.domain.base import VersionedDomainModel
from markeitech.signals.contracts import SignalFamily


class OpposingContextPolicy(StrEnum):
    IGNORE = "ignore"
    DEGRADE = "degrade"
    VETO = "veto"


class SignalDefinitionConfig(VersionedDomainModel):
    definition_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    family: SignalFamily = SignalFamily.DIRECTION_LOCATION_AGGRESSION
    algorithm_version: str = Field(default="1.0", min_length=1)
    evaluation_timeframe: AnalyticsTimeframe = AnalyticsTimeframe.ONE_MINUTE
    primary_direction_timeframes: tuple[AnalyticsTimeframe, ...] = Field(min_length=1)
    confirmation_timeframes: tuple[AnalyticsTimeframe, ...] = ()
    minimum_confirmation_count: int = Field(default=0, ge=0)
    context_timeframes: tuple[AnalyticsTimeframe, ...] = ()
    opposing_context_policy: OpposingContextPolicy = OpposingContextPolicy.DEGRADE
    minimum_direction_score: int = Field(default=1, ge=1, le=2)

    @model_validator(mode="after")
    def _timeframe_roles_must_be_consistent(self) -> SignalDefinitionConfig:
        groups = (
            self.primary_direction_timeframes,
            self.confirmation_timeframes,
            self.context_timeframes,
        )
        if any(len(values) != len(set(values)) for values in groups):
            raise ValueError("signal definition timeframe roles must not contain duplicates")
        if set(self.primary_direction_timeframes) & set(self.confirmation_timeframes):
            raise ValueError("primary and confirmation timeframes must be disjoint")
        if set(self.primary_direction_timeframes) & set(self.context_timeframes):
            raise ValueError("primary and context timeframes must be disjoint")
        if set(self.confirmation_timeframes) & set(self.context_timeframes):
            raise ValueError("confirmation and context timeframes must be disjoint")
        if self.minimum_confirmation_count > len(self.confirmation_timeframes):
            raise ValueError("minimum confirmations cannot exceed configured timeframes")
        return self

    @property
    def configuration_hash(self) -> str:
        payload = self.model_dump(mode="json")
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()

    @property
    def analytical_timeframes(self) -> frozenset[AnalyticsTimeframe]:
        return frozenset(
            (
                self.evaluation_timeframe,
                *self.primary_direction_timeframes,
                *self.confirmation_timeframes,
                *self.context_timeframes,
            )
        )


class SignalRuntimeConfig(VersionedDomainModel):
    definitions: tuple[SignalDefinitionConfig, ...] = ()
    enabled_definition_ids_by_instrument: dict[str, tuple[str, ...]] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def _references_must_be_consistent(self) -> SignalRuntimeConfig:
        definitions = {item.definition_id: item for item in self.definitions}
        if len(definitions) != len(self.definitions):
            raise ValueError("signal definition ids must be unique")
        for instrument_id, definition_ids in self.enabled_definition_ids_by_instrument.items():
            if not instrument_id.strip() or instrument_id != instrument_id.strip():
                raise ValueError("signal instrument ids must be non-empty and trimmed")
            if len(definition_ids) != len(set(definition_ids)):
                raise ValueError("enabled signal definition ids must be unique per instrument")
            unknown = set(definition_ids) - definitions.keys()
            if unknown:
                raise ValueError(f"unknown enabled signal definitions: {sorted(unknown)}")
        return self

    def enabled_definitions(self, instrument_id: str) -> tuple[SignalDefinitionConfig, ...]:
        by_id = {item.definition_id: item for item in self.definitions}
        return tuple(
            by_id[definition_id]
            for definition_id in self.enabled_definition_ids_by_instrument.get(instrument_id, ())
        )


def intraday_context_definition() -> SignalDefinitionConfig:
    return SignalDefinitionConfig(
        definition_id="intraday_context",
        evaluation_timeframe=AnalyticsTimeframe.ONE_MINUTE,
        primary_direction_timeframes=(
            AnalyticsTimeframe.ONE_HOUR,
            AnalyticsTimeframe.FIFTEEN_MINUTES,
        ),
        confirmation_timeframes=(AnalyticsTimeframe.FIVE_MINUTES,),
        minimum_confirmation_count=1,
        context_timeframes=(AnalyticsTimeframe.DAILY,),
        opposing_context_policy=OpposingContextPolicy.DEGRADE,
        minimum_direction_score=1,
    )
