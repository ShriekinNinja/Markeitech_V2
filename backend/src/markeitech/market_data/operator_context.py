from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from markeitech.analytics import AnalyticsTimeframe, MarketContextSnapshot

_TOP_DOWN_ORDER = (
    AnalyticsTimeframe.DAILY,
    AnalyticsTimeframe.ONE_HOUR,
    AnalyticsTimeframe.FIFTEEN_MINUTES,
    AnalyticsTimeframe.FIVE_MINUTES,
    AnalyticsTimeframe.THIRTY_MINUTES,
    AnalyticsTimeframe.ONE_MINUTE,
)
_LEVEL_TIMEFRAMES = (
    AnalyticsTimeframe.DAILY,
    AnalyticsTimeframe.ONE_HOUR,
    AnalyticsTimeframe.FIFTEEN_MINUTES,
    AnalyticsTimeframe.FIVE_MINUTES,
)


class OperatorContextReporter:
    """Renders bounded, change-aware operator views from canonical snapshots."""

    def __init__(self) -> None:
        self._last_signatures: dict[str, tuple[object, ...]] = {}

    def render(
        self,
        snapshots: Sequence[MarketContextSnapshot],
        *,
        active_instrument_id: str,
        phase: str,
        force: bool = False,
    ) -> tuple[str, ...]:
        if phase not in {"warmup", "live"}:
            raise ValueError(f"unsupported operator context phase {phase!r}")
        grouped: dict[str, list[MarketContextSnapshot]] = defaultdict(list)
        for snapshot in snapshots:
            grouped[snapshot.instrument_id].append(snapshot)

        lines: list[str] = []
        for instrument_id in sorted(
            grouped,
            key=lambda value: (value != active_instrument_id, value),
        ):
            values = sorted(
                grouped[instrument_id],
                key=lambda value: _TOP_DOWN_ORDER.index(value.timeframe),
            )
            role = "ACTIVE" if instrument_id == active_instrument_id else "BACKGROUND"
            signature = (role, *(value.model_dump_json() for value in values))
            if not force and self._last_signatures.get(instrument_id) == signature:
                continue
            self._last_signatures[instrument_id] = signature
            lines.extend(_instrument_lines(values, phase=phase, role=role))
        return tuple(lines)


def _instrument_lines(
    snapshots: Sequence[MarketContextSnapshot],
    *,
    phase: str,
    role: str,
) -> tuple[str, str, str]:
    by_timeframe = {snapshot.timeframe: snapshot for snapshot in snapshots}
    reference = by_timeframe.get(AnalyticsTimeframe.ONE_MINUTE, snapshots[-1])
    prefix = f"phase={phase.upper()} | role={role} | {reference.instrument_id}"
    trends = " ".join(
        f"{timeframe.value}={by_timeframe[timeframe].trend.value.upper()}"
        for timeframe in _TOP_DOWN_ORDER
        if timeframe in by_timeframe
    )
    levels = " ".join(
        f"{timeframe.value}=" f"{_support_resistance(by_timeframe[timeframe])}"
        for timeframe in _LEVEL_TIMEFRAMES
        if timeframe in by_timeframe
    )
    gaps = " ".join(
        f"{timeframe.value}={_fvg_summary(by_timeframe[timeframe])}"
        for timeframe in _LEVEL_TIMEFRAMES
        if timeframe in by_timeframe
    )
    return (
        f"OPERATOR_CONTEXT | {prefix} | price={reference.close} "
        f"| direction={reference.direction_score:+d} "
        f"| location={reference.profile_location.value} | TREND[{trends}] "
        f"| as_of={reference.as_of.isoformat()}",
        f"OPERATOR_LEVELS | {prefix} "
        f"| SESSION[{reference.session_low}/{reference.session_high} "
        f"@{reference.session_range_position * 100:.1f}%] "
        f"| PRIOR[{_price_pair(reference.prior_session_low, reference.prior_session_high)}] "
        f"| VWAP[{_value(reference.session_vwap)} {reference.vwap_position.value}] "
        f"| S/R[{levels}]",
        f"OPERATOR_AUCTION | {prefix} "
        f"| PROFILE[current={_profile(reference.volume_profile)} "
        f"prior={_profile(reference.prior_volume_profile)} "
        f"london={_profile(reference.london_volume_profile)} "
        f"new_york={_profile(reference.new_york_volume_profile)}] "
        f"| COMPOSITE[{_composite_profiles(reference.composite_volume_profiles)}] "
        f"| RANGES[london={_context_range(reference.london_range)} "
        f"new_york={_context_range(reference.new_york_range)}] "
        f"| OR[L15={_context_range(reference.london_opening_range_15)} "
        f"L30={_context_range(reference.london_opening_range_30)} "
        f"NY15={_context_range(reference.new_york_opening_range_15)} "
        f"NY30={_context_range(reference.new_york_opening_range_30)}] "
        f"| FVG[{gaps}] "
        f"| input={reference.input_fidelity.value}:{reference.source}",
    )


def _support_resistance(snapshot: MarketContextSnapshot) -> str:
    support = None if snapshot.nearest_support is None else snapshot.nearest_support.price
    resistance = None if snapshot.nearest_resistance is None else snapshot.nearest_resistance.price
    return f"{_value(support)}/{_value(resistance)}"


def _fvg_summary(snapshot: MarketContextSnapshot) -> str:
    if not snapshot.fair_value_gaps:
        return "none"
    nearest = sorted(
        snapshot.fair_value_gaps,
        key=lambda gap: min(abs(snapshot.close - gap.lower), abs(snapshot.close - gap.upper)),
    )[:2]
    return ",".join(f"{gap.direction.value}:{gap.lower}-{gap.upper}" for gap in nearest)


def _value(value: Any | None) -> str:
    return "n/a" if value is None else str(value)


def _price_pair(low: Any | None, high: Any | None) -> str:
    if low is None or high is None:
        return "n/a"
    return f"{low}/{high}"


def _context_range(value: Any | None) -> str:
    if value is None:
        return "n/a"
    state = "complete" if value.is_complete else "developing"
    return f"{value.low}/{value.high}:{state}"


def _profile(value: Any | None) -> str:
    if value is None:
        return "n/a"
    return (
        f"{value.value_area_low}/{value.poc}/{value.value_area_high}:"
        f"{value.input_fidelity.value}"
    )


def _composite_profiles(values: Any) -> str:
    if not values:
        return "none"
    return " ".join(
        f"{value.session_count}s={_profile(value.profile)}:"
        f"{'complete' if value.is_complete else 'developing'}"
        for value in values
    )
