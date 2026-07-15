from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, model_validator

from markeitech.analytics import AnalyticsTimeframe
from markeitech.domain.base import VersionedDomainModel
from markeitech.signals.contracts import (
    LocationSourceKind,
    SignalConfirmationMethod,
    SignalFamily,
)


class OpposingContextPolicy(StrEnum):
    IGNORE = "ignore"
    DEGRADE = "degrade"
    VETO = "veto"


class LocationSourcePolicyConfig(VersionedDomainModel):
    source_kind: LocationSourceKind
    timeframes: tuple[AnalyticsTimeframe, ...] = Field(min_length=1)
    proximity_atr_fraction: Decimal = Field(default=Decimal("0.15"), ge=0, le=2)

    @model_validator(mode="after")
    def _timeframes_must_be_unique(self) -> LocationSourcePolicyConfig:
        if len(self.timeframes) != len(set(self.timeframes)):
            raise ValueError("location source timeframes must be unique")
        return self


class LocationPolicyConfig(VersionedDomainModel):
    sources: tuple[LocationSourcePolicyConfig, ...] = Field(min_length=1)
    minimum_distinct_sources: int = Field(default=1, ge=1)
    exit_confirmation_bars: int = Field(default=2, ge=1, le=20)

    @model_validator(mode="after")
    def _sources_must_be_consistent(self) -> LocationPolicyConfig:
        source_kinds = [item.source_kind for item in self.sources]
        if len(source_kinds) != len(set(source_kinds)):
            raise ValueError("location policy source kinds must be unique")
        if self.minimum_distinct_sources > len(self.sources):
            raise ValueError("minimum location sources cannot exceed configured sources")
        return self

    @property
    def timeframes(self) -> frozenset[AnalyticsTimeframe]:
        return frozenset(timeframe for source in self.sources for timeframe in source.timeframes)


class AggressionPolicyConfig(VersionedDomainModel):
    observation_timeframe: AnalyticsTimeframe = AnalyticsTimeframe.ONE_MINUTE
    active_confirmation_method: SignalConfirmationMethod = SignalConfirmationMethod.TICK_AGGRESSION
    background_confirmation_method: SignalConfirmationMethod = (
        SignalConfirmationMethod.BAR_IMPULSE_PROXY
    )
    window_bars: int = Field(default=3, ge=1, le=30)
    expiry_observation_bars: int = Field(default=5, ge=1, le=120)
    minimum_classified_volume_ratio: Decimal = Field(
        default=Decimal("0.70"),
        ge=0,
        le=1,
    )
    minimum_directional_delta_ratio: Decimal = Field(
        default=Decimal("0.10"),
        ge=0,
        le=1,
    )
    minimum_follow_through_atr_fraction: Decimal = Field(
        default=Decimal("0.10"),
        ge=0,
        le=5,
    )
    maximum_adverse_atr_fraction: Decimal = Field(
        default=Decimal("0.30"),
        ge=0,
        le=5,
    )
    minimum_pace_ratio: Decimal | None = Field(default=None, gt=0, le=20)
    minimum_pace_baseline_bars: int = Field(default=10, ge=3, le=120)
    bar_proxy_minimum_directional_bar_ratio: Decimal = Field(
        default=Decimal("0.66"),
        ge=0,
        le=1,
    )
    bar_proxy_minimum_close_location: Decimal = Field(
        default=Decimal("0.65"),
        ge=0,
        le=1,
    )
    bar_proxy_minimum_follow_through_atr_fraction: Decimal = Field(
        default=Decimal("0.15"),
        ge=0,
        le=5,
    )
    bar_proxy_minimum_pace_ratio: Decimal = Field(
        default=Decimal("1.10"),
        gt=0,
        le=20,
    )

    @model_validator(mode="after")
    def _window_must_fit_expiry(self) -> AggressionPolicyConfig:
        if self.observation_timeframe != AnalyticsTimeframe.ONE_MINUTE:
            raise ValueError("initial aggression policy requires one-minute observations")
        if self.window_bars > self.expiry_observation_bars:
            raise ValueError("aggression window cannot exceed armed expiry observations")
        return self


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
    location_policy: LocationPolicyConfig | None = None
    aggression_policy: AggressionPolicyConfig | None = None

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
        if payload["aggression_policy"] is None:
            del payload["aggression_policy"]
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
                *(() if self.location_policy is None else self.location_policy.timeframes),
            )
        )


class SignalRuntimeConfig(VersionedDomainModel):
    definitions: tuple[SignalDefinitionConfig, ...] = ()
    enabled_definition_ids_by_instrument: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    feature_handoff_queue_size: int = Field(default=2_048, ge=1)
    evaluation_batch_size: int = Field(default=128, ge=1)
    evaluation_poll_seconds: float = Field(default=0.05, gt=0, le=5)
    operator_projection_queue_size: int = Field(default=256, ge=1)
    operator_projection_dedupe_size: int = Field(default=4_096, ge=1)
    operator_heartbeat_interval_seconds: int = Field(default=60, ge=10, le=3_600)

    @model_validator(mode="after")
    def _references_must_be_consistent(self) -> SignalRuntimeConfig:
        definitions = {item.definition_id: item for item in self.definitions}
        if self.evaluation_batch_size > self.feature_handoff_queue_size:
            raise ValueError("signal evaluation batch cannot exceed handoff queue size")
        if self.operator_projection_dedupe_size < self.operator_projection_queue_size:
            raise ValueError("signal projection dedupe size cannot be smaller than queue")
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
        location_policy=LocationPolicyConfig(
            sources=(
                LocationSourcePolicyConfig(
                    source_kind=LocationSourceKind.STRUCTURAL_LEVEL,
                    timeframes=(
                        AnalyticsTimeframe.FIFTEEN_MINUTES,
                        AnalyticsTimeframe.FIVE_MINUTES,
                    ),
                    proximity_atr_fraction=Decimal("0.15"),
                ),
                LocationSourcePolicyConfig(
                    source_kind=LocationSourceKind.FAIR_VALUE_GAP,
                    timeframes=(
                        AnalyticsTimeframe.FIFTEEN_MINUTES,
                        AnalyticsTimeframe.FIVE_MINUTES,
                    ),
                    proximity_atr_fraction=Decimal("0"),
                ),
                LocationSourcePolicyConfig(
                    source_kind=LocationSourceKind.VALUE_AREA_EDGE,
                    timeframes=(AnalyticsTimeframe.ONE_MINUTE,),
                    proximity_atr_fraction=Decimal("0.10"),
                ),
                LocationSourcePolicyConfig(
                    source_kind=LocationSourceKind.SESSION_VWAP,
                    timeframes=(AnalyticsTimeframe.ONE_MINUTE,),
                    proximity_atr_fraction=Decimal("0.10"),
                ),
            ),
            minimum_distinct_sources=1,
        ),
    )
