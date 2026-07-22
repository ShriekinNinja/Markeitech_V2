from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from markeitech.domain.instruments import AggressionOutcomeConfig
from markeitech.domain.market_data import ClassifiedTrade, TradeSide
from markeitech.markeitect_model.contracts import (
    AggressionEpisode,
    AggressionOutcome,
)


class AggressionEpisodeTracker:
    def __init__(self, instrument_id: str, config: AggressionOutcomeConfig) -> None:
        self._instrument_id = instrument_id
        self._config = config
        self._open: dict[str, AggressionEpisode] = {}

    @property
    def open_episodes(self) -> tuple[AggressionEpisode, ...]:
        return tuple(self._open.values())

    def open(
        self,
        trade: ClassifiedTrade,
        *,
        cvd: Decimal,
        print_count: int,
        location: tuple[str, Decimal] | None,
    ) -> AggressionEpisode:
        if trade.instrument_id != self._instrument_id:
            raise ValueError("aggression observation does not match tracker instrument")
        if trade.side == TradeSide.UNKNOWN:
            raise ValueError("unknown aggression cannot open a participant episode")
        location_label, location_price = location or (None, None)
        episode = AggressionEpisode(
            origin_id=trade.trade.dedupe_key,
            instrument_id=trade.instrument_id,
            side=trade.side,
            anchor_price=trade.trade.price,
            observed_size=trade.trade.size,
            print_count=print_count,
            opened_ts=trade.event_ts,
            expires_ts=trade.event_ts
            + timedelta(seconds=self._config.observation_window_seconds),
            as_of=trade.event_ts,
            baseline_cvd=cvd,
            latest_cvd=cvd,
            latest_price=trade.trade.price,
            location_label=location_label,
            location_price=location_price,
            source=trade.trade.source,
            fidelity="inferred",
            reason_codes=("consequential_aggression_observed",),
        )
        while len(self._open) >= self._config.max_open_episodes:
            self._open.pop(next(iter(self._open)))
        self._open[episode.episode_id] = episode
        return episode

    def observe(
        self,
        trade: ClassifiedTrade,
        *,
        cvd: Decimal,
    ) -> tuple[AggressionEpisode, ...]:
        if trade.instrument_id != self._instrument_id:
            return ()
        completed: list[AggressionEpisode] = []
        for episode_id, episode in tuple(self._open.items()):
            if trade.event_ts <= episode.as_of:
                continue
            if trade.event_ts > episode.expires_ts:
                self._open.pop(episode_id, None)
                completed.append(self._expire(episode))
                continue
            updated = self._update(episode, trade, cvd)
            if updated.outcome == AggressionOutcome.PENDING:
                self._open[episode_id] = updated
                continue
            self._open.pop(episode_id, None)
            completed.append(updated)
        return tuple(completed)

    def _update(
        self,
        episode: AggressionEpisode,
        trade: ClassifiedTrade,
        cvd: Decimal,
    ) -> AggressionEpisode:
        direction = Decimal("1") if episode.side == TradeSide.BUY else Decimal("-1")
        directional_move = (trade.trade.price - episode.anchor_price) * direction
        favorable = max(episode.max_favorable_excursion, directional_move, Decimal("0"))
        adverse = max(episode.max_adverse_excursion, -directional_move, Decimal("0"))
        directional_cvd = (cvd - episode.baseline_cvd) * direction
        outcome = AggressionOutcome.PENDING
        reasons = ("outcome_observation_continues",)
        if (
            directional_move >= self._config.follow_through_points
            and directional_cvd > 0
        ):
            outcome = AggressionOutcome.WITH_FLOW
            reasons = ("price_follow_through", "cvd_confirmed_aggression")
        elif directional_move <= -self._config.trapped_points and directional_cvd < 0:
            outcome = AggressionOutcome.TRAPPED
            reasons = ("price_displaced_against_aggression", "cvd_reversed_against_aggression")
        elif trade.event_ts == episode.expires_ts:
            return self._expire(
                episode.model_copy(
                    update={
                        "as_of": trade.event_ts,
                        "latest_cvd": cvd,
                        "latest_price": trade.trade.price,
                        "max_favorable_excursion": favorable,
                        "max_adverse_excursion": adverse,
                        "observed_trade_count": episode.observed_trade_count + 1,
                    }
                )
            )
        return episode.model_copy(
            update={
                "as_of": trade.event_ts,
                "latest_cvd": cvd,
                "latest_price": trade.trade.price,
                "max_favorable_excursion": favorable,
                "max_adverse_excursion": adverse,
                "observed_trade_count": episode.observed_trade_count + 1,
                "outcome": outcome,
                "reason_codes": reasons,
            }
        )

    def _expire(self, episode: AggressionEpisode) -> AggressionEpisode:
        absorbed = (
            episode.max_favorable_excursion <= self._config.absorption_points
            and episode.max_adverse_excursion <= self._config.absorption_points
        )
        return episode.model_copy(
            update={
                "outcome": (
                    AggressionOutcome.ABSORBED
                    if absorbed
                    else AggressionOutcome.UNRESOLVED
                ),
                "reason_codes": (
                    ("observation_window_elapsed", "aggression_received_little_progress")
                    if absorbed
                    else ("observation_window_elapsed", "terminal_evidence_not_met")
                ),
            }
        )
