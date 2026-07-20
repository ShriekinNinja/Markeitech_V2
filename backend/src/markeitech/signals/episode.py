from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from markeitech.domain.base import VersionedDomainModel, require_utc
from markeitech.domain.market_data import OneMinuteBar
from markeitech.signals.config import SignalDefinitionConfig
from markeitech.signals.contracts import (
    LocationQualification,
    LocationQualificationStatus,
    SignalDirection,
    SignalLocationMatch,
)


class LocationEpisodeEventType(StrEnum):
    ENTERED = "entered"
    ACTIVE = "active"
    FAVORABLE_DEPARTURE = "favorable_departure"
    REJECTED = "rejected"
    DEPARTURE_UNRESOLVED = "departure_unresolved"
    EXIT_PENDING = "exit_pending"
    EXITED = "exited"
    REPLACED = "replaced"
    EVIDENCE_GAP = "evidence_gap"
    NO_EPISODE = "no_episode"


class LocationInteractionState(StrEnum):
    TOUCHED = "touched"
    ENGAGED = "engaged"
    DEPARTURE_PENDING = "departure_pending"
    REJECTED = "rejected"
    DEPARTURE_UNRESOLVED = "departure_unresolved"
    ACCEPTANCE_PENDING = "acceptance_pending"
    ACCEPTED_THROUGH = "accepted_through"
    REPLACED = "replaced"
    EVIDENCE_GAP = "evidence_gap"
    OUTSIDE = "outside"


class SignalLocationEpisode(VersionedDomainModel):
    definition_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    instrument_id: str = Field(min_length=1)
    direction: SignalDirection
    direction_regime_anchor: str = Field(min_length=1)
    entry_ts: datetime
    entry_matches: tuple[SignalLocationMatch, ...] = Field(min_length=1)

    @field_validator("entry_ts")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _entry_must_be_consistent(self) -> SignalLocationEpisode:
        if self.direction_regime_anchor != self.direction_regime_anchor.strip():
            raise ValueError("direction regime anchor must be trimmed")
        if any(item.zone.instrument_id != self.instrument_id for item in self.entry_matches):
            raise ValueError("location episode matches must use one instrument")
        if any(item.zone.direction != self.direction for item in self.entry_matches):
            raise ValueError("location episode matches must align with direction")
        if any(item.observed_ts != self.entry_ts for item in self.entry_matches):
            raise ValueError("location episode matches must share entry timestamp")
        if len(self.entry_zone_ids) != len(self.entry_matches):
            raise ValueError("location episode cannot repeat a semantic zone")
        return self

    @property
    def entry_zone_ids(self) -> tuple[str, ...]:
        return tuple(sorted({item.zone.zone_id for item in self.entry_matches}))

    @property
    def episode_id(self) -> str:
        return _canonical_hash(
            {
                "schema_version": self.schema_version,
                "definition_id": self.definition_id,
                "instrument_id": self.instrument_id,
                "direction": self.direction.value,
                "direction_regime_anchor": self.direction_regime_anchor,
                "entry_ts": self.entry_ts.isoformat(),
                "entry_zone_ids": self.entry_zone_ids,
            }
        )


class LocationEpisodeObservation(VersionedDomainModel):
    definition_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    instrument_id: str = Field(min_length=1)
    direction: SignalDirection
    direction_regime_anchor: str = Field(min_length=1)
    evaluation_ts: datetime
    observed_price: Decimal | None = Field(default=None, gt=0)
    observed_bar: OneMinuteBar | None = None
    qualification: LocationQualification

    @field_validator("evaluation_ts")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _observation_must_be_consistent(self) -> LocationEpisodeObservation:
        if self.direction_regime_anchor != self.direction_regime_anchor.strip():
            raise ValueError("direction regime anchor must be trimmed")
        if any(
            item.zone.instrument_id != self.instrument_id for item in self.qualification.matches
        ):
            raise ValueError("location observation matches must use one instrument")
        if any(item.zone.direction != self.direction for item in self.qualification.matches):
            raise ValueError("location observation matches must align with direction")
        if any(item.observed_ts != self.evaluation_ts for item in self.qualification.matches):
            raise ValueError("location observation matches must use evaluation timestamp")
        if (
            self.qualification.status != LocationQualificationStatus.MISSING_EVIDENCE
            and self.observed_price is None
        ):
            raise ValueError("observed location evidence requires an evaluation price")
        if self.observed_bar is not None:
            if self.observed_bar.instrument_id != self.instrument_id:
                raise ValueError("location observation bar must use one instrument")
            if self.observed_bar.close_ts != self.evaluation_ts:
                raise ValueError("location observation bar must close at evaluation time")
            if self.observed_price != self.observed_bar.close:
                raise ValueError("location observation price must equal bar close")
            if not self.observed_bar.is_complete or self.observed_bar.is_revision:
                raise ValueError("location observation requires a complete canonical bar")
        return self


@dataclass(frozen=True)
class LocationEpisodeDecision:
    event_type: LocationEpisodeEventType
    episode: SignalLocationEpisode | None
    ended_episode_id: str | None
    outside_confirmation_count: int
    reason_codes: tuple[str, ...] = ()

    @property
    def interaction_state(self) -> LocationInteractionState:
        return {
            LocationEpisodeEventType.ENTERED: LocationInteractionState.TOUCHED,
            LocationEpisodeEventType.ACTIVE: LocationInteractionState.ENGAGED,
            LocationEpisodeEventType.FAVORABLE_DEPARTURE: (
                LocationInteractionState.DEPARTURE_PENDING
            ),
            LocationEpisodeEventType.REJECTED: LocationInteractionState.REJECTED,
            LocationEpisodeEventType.DEPARTURE_UNRESOLVED: (
                LocationInteractionState.DEPARTURE_UNRESOLVED
            ),
            LocationEpisodeEventType.EXIT_PENDING: LocationInteractionState.ACCEPTANCE_PENDING,
            LocationEpisodeEventType.EXITED: LocationInteractionState.ACCEPTED_THROUGH,
            LocationEpisodeEventType.REPLACED: LocationInteractionState.REPLACED,
            LocationEpisodeEventType.EVIDENCE_GAP: LocationInteractionState.EVIDENCE_GAP,
            LocationEpisodeEventType.NO_EPISODE: LocationInteractionState.OUTSIDE,
        }[self.event_type]


@dataclass
class _InstrumentEpisodeState:
    active: SignalLocationEpisode | None = None
    outside_confirmation_count: int = 0
    favorable_confirmation_count: int = 0
    last_observation: LocationEpisodeObservation | None = None
    last_decision: LocationEpisodeDecision | None = None


class LocationEpisodeTracker:
    def __init__(self, definition: SignalDefinitionConfig) -> None:
        if definition.location_policy is None:
            raise ValueError("location episode tracker requires location policy")
        self._definition = definition
        self._exit_confirmation_bars = definition.location_policy.exit_confirmation_bars
        self._rejection_confirmation_bars = definition.location_policy.rejection_confirmation_bars
        self._states: dict[str, _InstrumentEpisodeState] = {}

    def seed_active_episodes(self, episodes: tuple[SignalLocationEpisode, ...]) -> None:
        if self._states:
            raise ValueError("location episode tracker can only seed before evaluation")
        for episode in episodes:
            if episode.definition_id != self._definition.definition_id:
                raise ValueError("restored location episode definition does not match tracker")
            if episode.instrument_id in self._states:
                raise ValueError("multiple active location episodes exist for one definition")
            self._states[episode.instrument_id] = _InstrumentEpisodeState(active=episode)

    def evaluate(self, observation: LocationEpisodeObservation) -> LocationEpisodeDecision:
        if observation.definition_id != self._definition.definition_id:
            raise ValueError("location observation definition does not match tracker")
        state = self._states.setdefault(
            observation.instrument_id,
            _InstrumentEpisodeState(),
        )
        if state.last_observation is not None:
            if observation.evaluation_ts < state.last_observation.evaluation_ts:
                raise ValueError("location observations cannot move backward")
            if observation.evaluation_ts == state.last_observation.evaluation_ts:
                if observation != state.last_observation:
                    raise ValueError("conflicting location observation at evaluation time")
                assert state.last_decision is not None
                return state.last_decision

        decision = self._evaluate_new(state, observation)
        state.last_observation = observation
        state.last_decision = decision
        return decision

    def _evaluate_new(
        self,
        state: _InstrumentEpisodeState,
        observation: LocationEpisodeObservation,
    ) -> LocationEpisodeDecision:
        active = state.active
        if active is not None and (
            active.direction != observation.direction
            or active.direction_regime_anchor != observation.direction_regime_anchor
        ):
            ended = active.episode_id
            state.active = None
            state.outside_confirmation_count = 0
            state.favorable_confirmation_count = 0
            if observation.qualification.status == LocationQualificationStatus.QUALIFIED:
                replacement = _new_episode(observation)
                state.active = replacement
                return LocationEpisodeDecision(
                    LocationEpisodeEventType.REPLACED,
                    replacement,
                    ended,
                    0,
                )
            return LocationEpisodeDecision(
                LocationEpisodeEventType.EXITED,
                None,
                ended,
                0,
            )

        if observation.qualification.status == LocationQualificationStatus.MISSING_EVIDENCE:
            state.outside_confirmation_count = 0
            state.favorable_confirmation_count = 0
            return LocationEpisodeDecision(
                LocationEpisodeEventType.EVIDENCE_GAP,
                state.active,
                None,
                0,
            )

        if observation.qualification.status == LocationQualificationStatus.QUALIFIED:
            if active is None:
                entered = _new_episode(observation)
                state.active = entered
                state.outside_confirmation_count = 0
                state.favorable_confirmation_count = 0
                return LocationEpisodeDecision(
                    LocationEpisodeEventType.ENTERED,
                    entered,
                    None,
                    0,
                )
            matched_zone_ids = {item.zone.zone_id for item in observation.qualification.matches}
            if matched_zone_ids & set(active.entry_zone_ids):
                assert observation.observed_price is not None
                return self._classify_active_close(
                    state,
                    active,
                    observation.observed_price,
                    is_engaged=True,
                )
            replacement = _new_episode(observation)
            state.active = replacement
            state.outside_confirmation_count = 0
            state.favorable_confirmation_count = 0
            return LocationEpisodeDecision(
                LocationEpisodeEventType.REPLACED,
                replacement,
                active.episode_id,
                0,
            )

        if active is None:
            state.outside_confirmation_count = 0
            state.favorable_confirmation_count = 0
            return LocationEpisodeDecision(
                LocationEpisodeEventType.NO_EPISODE,
                None,
                None,
                0,
            )

        assert observation.observed_price is not None
        return self._classify_active_close(
            state,
            active,
            observation.observed_price,
            is_engaged=False,
        )

    def _classify_active_close(
        self,
        state: _InstrumentEpisodeState,
        active: SignalLocationEpisode,
        observed_price: Decimal,
        *,
        is_engaged: bool,
    ) -> LocationEpisodeDecision:
        departure = _classify_departure(active, observed_price)
        if departure == LocationEpisodeEventType.FAVORABLE_DEPARTURE:
            state.outside_confirmation_count = 0
            state.favorable_confirmation_count += 1
            if state.favorable_confirmation_count >= self._rejection_confirmation_bars:
                state.favorable_confirmation_count = self._rejection_confirmation_bars
                return LocationEpisodeDecision(
                    LocationEpisodeEventType.REJECTED,
                    active,
                    None,
                    0,
                    ("location_rejection_confirmed",),
                )
            return LocationEpisodeDecision(
                LocationEpisodeEventType.FAVORABLE_DEPARTURE,
                active,
                None,
                0,
                ("location_rejection_pending",),
            )
        if departure == LocationEpisodeEventType.DEPARTURE_UNRESOLVED:
            state.outside_confirmation_count = 0
            state.favorable_confirmation_count = 0
            if is_engaged:
                return LocationEpisodeDecision(
                    LocationEpisodeEventType.ACTIVE,
                    active,
                    None,
                    0,
                    ("price_remains_engaged_with_entry_location",),
                )
            return LocationEpisodeDecision(
                LocationEpisodeEventType.DEPARTURE_UNRESOLVED,
                active,
                None,
                0,
                ("price_departure_did_not_breach_entry_thesis",),
            )

        state.favorable_confirmation_count = 0
        state.outside_confirmation_count += 1
        if state.outside_confirmation_count < self._exit_confirmation_bars:
            return LocationEpisodeDecision(
                LocationEpisodeEventType.EXIT_PENDING,
                active,
                None,
                state.outside_confirmation_count,
                ("location_acceptance_pending",),
            )
        state.active = None
        state.outside_confirmation_count = 0
        return LocationEpisodeDecision(
            LocationEpisodeEventType.EXITED,
            None,
            active.episode_id,
            self._exit_confirmation_bars,
            ("location_acceptance_confirmed",),
        )


def _classify_departure(
    active: SignalLocationEpisode,
    observed_price: Decimal,
) -> LocationEpisodeEventType:
    adverse_edges = tuple(
        (
            match.zone.lower_price - match.tolerance
            if active.direction == SignalDirection.LONG
            else match.zone.upper_price + match.tolerance
        )
        for match in active.entry_matches
    )
    favorable_edges = tuple(
        (
            match.zone.upper_price + match.tolerance
            if active.direction == SignalDirection.LONG
            else match.zone.lower_price - match.tolerance
        )
        for match in active.entry_matches
    )
    if active.direction == SignalDirection.LONG:
        if observed_price < min(adverse_edges):
            return LocationEpisodeEventType.EXIT_PENDING
        if observed_price > max(favorable_edges):
            return LocationEpisodeEventType.FAVORABLE_DEPARTURE
    else:
        if observed_price > max(adverse_edges):
            return LocationEpisodeEventType.EXIT_PENDING
        if observed_price < min(favorable_edges):
            return LocationEpisodeEventType.FAVORABLE_DEPARTURE
    return LocationEpisodeEventType.DEPARTURE_UNRESOLVED


def _new_episode(observation: LocationEpisodeObservation) -> SignalLocationEpisode:
    return SignalLocationEpisode(
        definition_id=observation.definition_id,
        instrument_id=observation.instrument_id,
        direction=observation.direction,
        direction_regime_anchor=observation.direction_regime_anchor,
        entry_ts=observation.evaluation_ts,
        entry_matches=observation.qualification.matches,
    )


def _canonical_hash(value: dict[str, object]) -> str:
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()
