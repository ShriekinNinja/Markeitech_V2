from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from markeitech.analytics.contracts import (
    AnalysisBar,
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    MarketContextSnapshot,
)
from markeitech.domain.base import VersionedDomainModel, require_utc

MARKET_CONTEXT_FEATURE_SET = "market_context"
MARKET_CONTEXT_CALCULATION_VERSION = "1.0"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class MarketContextCalculationConfig(VersionedDomainModel):
    maximum_bars_per_timeframe: int = Field(default=10_000, ge=200)
    profile_bin_sizes: dict[str, Decimal] = Field(default_factory=dict)
    profile_composite_sessions: dict[str, tuple[int, ...]] = Field(default_factory=dict)
    session_policies: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _settings_must_be_consistent(self) -> MarketContextCalculationConfig:
        if any(value <= 0 for value in self.profile_bin_sizes.values()):
            raise ValueError("volume profile bin sizes must be positive")
        if any(
            sessions < 2 or sessions > 20
            for values in self.profile_composite_sessions.values()
            for sessions in values
        ):
            raise ValueError("composite volume profiles require between 2 and 20 sessions")
        if any(
            len(values) != len(set(values)) for values in self.profile_composite_sessions.values()
        ):
            raise ValueError("composite volume profile session counts must be unique")
        return self

    @property
    def configuration_hash(self) -> str:
        return configuration_fingerprint(self)


class FeatureInputLineage(VersionedDomainModel):
    """Exact input-stream evidence used by one feature calculation."""

    instrument_id: str = Field(min_length=1)
    timeframe: AnalyticsTimeframe
    source: str = Field(min_length=1)
    input_fidelity: AnalyticsInputFidelity
    start_ts: datetime
    end_ts: datetime
    event_count: int = Field(ge=1)
    identity_hash: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("start_ts", "end_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _window_must_be_consistent(self) -> FeatureInputLineage:
        if self.end_ts < self.start_ts:
            raise ValueError("feature input lineage end cannot precede start")
        return self

    @property
    def stream_key(self) -> str:
        return f"{self.source}:{self.instrument_id}:{self.timeframe.value}"


class MarketContextFeatureSnapshot(VersionedDomainModel):
    """Persistable deterministic feature envelope with reproducible identity."""

    feature_set: Literal["market_context"] = MARKET_CONTEXT_FEATURE_SET
    calculation_version: str = Field(
        default=MARKET_CONTEXT_CALCULATION_VERSION,
        min_length=1,
    )
    configuration_hash: str = Field(pattern=_SHA256_PATTERN)
    input_lineage: tuple[FeatureInputLineage, ...] = Field(min_length=1)
    snapshot: MarketContextSnapshot

    @model_validator(mode="after")
    def _lineage_must_match_snapshot(self) -> MarketContextFeatureSnapshot:
        if any(item.instrument_id != self.snapshot.instrument_id for item in self.input_lineage):
            raise ValueError("feature input lineage instrument must match snapshot")
        if not any(item.timeframe == self.snapshot.timeframe for item in self.input_lineage):
            raise ValueError("feature input lineage must include the snapshot timeframe")
        if any(item.end_ts > self.snapshot.as_of for item in self.input_lineage):
            raise ValueError("feature input lineage cannot extend beyond snapshot as_of")
        lineage_keys = [
            (item.stream_key, item.start_ts, item.end_ts, item.identity_hash)
            for item in self.input_lineage
        ]
        if len(lineage_keys) != len(set(lineage_keys)):
            raise ValueError("feature input lineage entries must be unique")
        return self

    @property
    def feature_id(self) -> str:
        lineage = sorted(
            (
                {
                    "schema_version": item.schema_version,
                    "instrument_id": item.instrument_id,
                    "timeframe": item.timeframe.value,
                    "source": item.source,
                    "input_fidelity": item.input_fidelity.value,
                    "start_ts": item.start_ts.isoformat(),
                    "end_ts": item.end_ts.isoformat(),
                    "event_count": item.event_count,
                    "identity_hash": item.identity_hash,
                }
                for item in self.input_lineage
            ),
            key=lambda value: (
                value["source"],
                value["timeframe"],
                value["start_ts"],
                value["end_ts"],
                value["identity_hash"],
            ),
        )
        return _canonical_hash(
            {
                "schema_version": self.schema_version,
                "feature_set": self.feature_set,
                "calculation_version": self.calculation_version,
                "configuration_hash": self.configuration_hash,
                "instrument_id": self.snapshot.instrument_id,
                "timeframe": self.snapshot.timeframe.value,
                "as_of": self.snapshot.as_of.isoformat(),
                "source": self.snapshot.source,
                "input_fidelity": self.snapshot.input_fidelity.value,
                "input_lineage": lineage,
            }
        )

    @property
    def content_hash(self) -> str:
        return _canonical_hash(self.snapshot.model_dump(mode="json"))


def configuration_fingerprint(configuration: BaseModel) -> str:
    """Hash a versioned calculation configuration without object repr leakage."""

    return _canonical_hash(configuration.model_dump(mode="json"))


def analysis_bar_lineages(bars: Sequence[AnalysisBar]) -> tuple[FeatureInputLineage, ...]:
    grouped: dict[
        tuple[str, AnalyticsTimeframe, str, AnalyticsInputFidelity],
        list[AnalysisBar],
    ] = defaultdict(list)
    for bar in bars:
        grouped[
            (
                bar.instrument_id,
                bar.timeframe,
                bar.source,
                bar.input_fidelity,
            )
        ].append(bar)
    lineages: list[FeatureInputLineage] = []
    for (instrument_id, timeframe, source, fidelity), values in sorted(
        grouped.items(),
        key=lambda item: (
            item[0][0],
            item[0][1].duration,
            item[0][2],
            item[0][3].value,
        ),
    ):
        ordered = sorted(values, key=lambda value: (value.open_ts, value.close_ts))
        lineages.append(
            FeatureInputLineage(
                instrument_id=instrument_id,
                timeframe=timeframe,
                source=source,
                input_fidelity=fidelity,
                start_ts=ordered[0].open_ts,
                end_ts=ordered[-1].close_ts,
                event_count=len(ordered),
                identity_hash=_canonical_hash([value.model_dump(mode="json") for value in ordered]),
            )
        )
    return tuple(lineages)


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()
