from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from nautilus_trader.indicators import AverageTrueRange, ExponentialMovingAverage

from markeitech.analytics.contracts import (
    AnalysisBar,
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    ContextLevel,
    ContextRange,
    FairValueGap,
    FairValueGapDirection,
    LevelKind,
    MarketContextSnapshot,
    ProfileLocation,
    TrendState,
    VolumeProfileSnapshot,
    VwapPosition,
)
from markeitech.analytics.normalization import (
    analysis_bar_from_nautilus,
    analysis_bar_from_one_minute,
)
from markeitech.domain.market_data import OneMinuteBar

_LIVE_AGGREGATE_TIMEFRAMES = (
    AnalyticsTimeframe.FIVE_MINUTES,
    AnalyticsTimeframe.FIFTEEN_MINUTES,
    AnalyticsTimeframe.THIRTY_MINUTES,
    AnalyticsTimeframe.ONE_HOUR,
)


class SessionWindowResolver(Protocol):
    def session_window(
        self, instrument_id: str, timestamp: datetime
    ) -> tuple[datetime, datetime]: ...


class MarketContextEngine:
    def __init__(
        self,
        session_windows: SessionWindowResolver,
        *,
        maximum_bars_per_timeframe: int = 10_000,
        profile_bin_sizes: Mapping[str, Decimal] | None = None,
    ) -> None:
        if maximum_bars_per_timeframe < 200:
            raise ValueError("analytics history must retain at least 200 bars")
        self._session_windows = session_windows
        self._maximum_bars = maximum_bars_per_timeframe
        self._profile_bin_sizes = dict(profile_bin_sizes or {})
        if any(value <= 0 for value in self._profile_bin_sizes.values()):
            raise ValueError("volume profile bin sizes must be positive")
        self._bars: dict[tuple[str, AnalyticsTimeframe], list[AnalysisBar]] = defaultdict(list)
        self._configured: dict[str, set[AnalyticsTimeframe]] = defaultdict(set)
        self._aggregators: dict[tuple[str, AnalyticsTimeframe], _BarAggregator] = {}
        self._snapshots: dict[tuple[str, AnalyticsTimeframe], MarketContextSnapshot] = {}

    @property
    def snapshots(self) -> tuple[MarketContextSnapshot, ...]:
        return tuple(
            self._snapshots[key]
            for key in sorted(self._snapshots, key=lambda item: (item[0], item[1].duration))
        )

    def initialize(
        self,
        data_by_bar_type: Mapping[str, Sequence[Any]],
    ) -> tuple[MarketContextSnapshot, ...]:
        normalized = tuple(
            analysis_bar_from_nautilus(value)
            for values in data_by_bar_type.values()
            for value in values
        )
        return self.initialize_bars(normalized)

    def initialize_bars(
        self,
        bars: Sequence[AnalysisBar],
    ) -> tuple[MarketContextSnapshot, ...]:
        if self._snapshots:
            raise RuntimeError("market context engine can only initialize once")
        for bar in bars:
            self._configured[bar.instrument_id].add(bar.timeframe)
            self._append(bar)
        if not self._bars:
            raise RuntimeError("market context warmup contains no analyzable bars")
        for instrument_id, timeframes in self._configured.items():
            for timeframe in timeframes & set(_LIVE_AGGREGATE_TIMEFRAMES):
                self._aggregators[(instrument_id, timeframe)] = _BarAggregator(
                    timeframe,
                    self._session_windows,
                )
        initialized: list[MarketContextSnapshot] = []
        for key in sorted(self._bars, key=lambda item: (item[0], item[1].duration)):
            snapshot = self._calculate(key)
            self._snapshots[key] = snapshot
            initialized.append(snapshot)
        return tuple(initialized)

    def update_one_minute(self, bar: OneMinuteBar) -> tuple[MarketContextSnapshot, ...]:
        canonical = analysis_bar_from_one_minute(bar)
        instrument_id = canonical.instrument_id
        if instrument_id not in self._configured:
            raise ValueError(f"analytics received unconfigured instrument {instrument_id!r}")
        updated_keys = [(instrument_id, AnalyticsTimeframe.ONE_MINUTE)]
        self._configured[instrument_id].add(AnalyticsTimeframe.ONE_MINUTE)
        self._append(canonical)

        for timeframe in _LIVE_AGGREGATE_TIMEFRAMES:
            if timeframe not in self._configured[instrument_id]:
                continue
            aggregator = self._aggregators.setdefault(
                (instrument_id, timeframe),
                _BarAggregator(timeframe, self._session_windows),
            )
            completed = aggregator.update(canonical)
            if completed is not None:
                self._append(completed)
                updated_keys.append((instrument_id, timeframe))

        updates: list[MarketContextSnapshot] = []
        for key in updated_keys:
            snapshot = self._calculate(key)
            self._snapshots[key] = snapshot
            updates.append(snapshot)
        return tuple(updates)

    def _append(self, bar: AnalysisBar) -> None:
        key = (bar.instrument_id, bar.timeframe)
        history = self._bars[key]
        by_open = {item.open_ts: item for item in history}
        by_open[bar.open_ts] = bar
        ordered = sorted(by_open.values(), key=lambda item: item.open_ts)
        self._bars[key] = ordered[-self._maximum_bars :]

    def _calculate(
        self,
        key: tuple[str, AnalyticsTimeframe],
    ) -> MarketContextSnapshot:
        bars = self._bars[key]
        latest = bars[-1]
        if latest.timeframe == AnalyticsTimeframe.DAILY:
            session_bars = [latest]
        else:
            session_open_ts, session_close_ts = self._session_windows.session_window(
                latest.instrument_id,
                latest.open_ts,
            )
            session_bars = [
                bar for bar in bars if session_open_ts <= bar.open_ts < session_close_ts
            ]
        if not session_bars:
            raise RuntimeError(f"no bars belong to resolved session for {latest.instrument_id}")

        closes = [bar.close for bar in bars]
        ema_20_values = _ema_values(closes, 20)
        ema_50_values = _ema_values(closes, 50)
        ema_200_values = _ema_values(closes, 200)
        ema_20 = ema_20_values[-1] if len(closes) >= 20 else None
        ema_50 = ema_50_values[-1] if len(closes) >= 50 else None
        ema_200 = ema_200_values[-1] if len(closes) >= 200 else None
        atr_14 = _atr(bars, 14)
        trend, reasons = _trend(latest.close, ema_20_values, ema_50_values, len(closes))
        session_high = max(bar.high for bar in session_bars)
        session_low = min(bar.low for bar in session_bars)
        session_vwap = _vwap(session_bars)
        session_span = session_high - session_low
        range_position = (
            Decimal("0.5")
            if session_span == 0
            else min(Decimal("1"), max(Decimal("0"), (latest.close - session_low) / session_span))
        )
        support, resistance = _nearest_levels(bars, session_bars, latest.close)
        structure_bars = self._bars.get(
            (latest.instrument_id, AnalyticsTimeframe.ONE_MINUTE),
            bars,
        )
        structure_reference = _latest_bar_at_or_before(structure_bars, latest.close_ts)
        structure_session_bars = _resolved_session_bars(
            structure_bars,
            structure_reference,
            self._session_windows,
            as_of=latest.close_ts,
        )
        prior_session_bars = _prior_session_bars(
            structure_bars,
            structure_session_bars[0].open_ts,
            self._session_windows,
        )
        prior_high = max(bar.high for bar in prior_session_bars) if prior_session_bars else None
        prior_low = min(bar.low for bar in prior_session_bars) if prior_session_bars else None
        named_ranges = _named_session_ranges(structure_bars, latest.close_ts)
        bin_size = self._profile_bin_sizes.get(latest.instrument_id, Decimal("1"))
        profile = _volume_profile(
            structure_session_bars,
            bin_size,
        )
        prior_profile = _volume_profile(prior_session_bars, bin_size)
        london_profile = _range_volume_profile(
            structure_bars,
            named_ranges["london"],
            latest.close_ts,
            bin_size,
        )
        new_york_profile = _range_volume_profile(
            structure_bars,
            named_ranges["new_york"],
            latest.close_ts,
            bin_size,
        )
        profile_location, location_reasons = _profile_location(latest.close, profile)
        gaps = _fair_value_gaps(bars[-500:])
        direction_score, direction_location_reasons = _direction_location_summary(
            trend=trend,
            vwap_position=_vwap_position(latest.close, session_vwap),
            session_range_position=range_position,
            profile_location=profile_location,
            close=latest.close,
            atr=atr_14,
            support=support,
            resistance=resistance,
            gaps=gaps,
        )
        return MarketContextSnapshot(
            instrument_id=latest.instrument_id,
            timeframe=latest.timeframe,
            as_of=latest.close_ts,
            source=latest.source,
            input_fidelity=latest.input_fidelity,
            bar_count=len(bars),
            close=latest.close,
            ema_20=ema_20,
            ema_50=ema_50,
            ema_200=ema_200,
            atr_14=atr_14,
            session_open=session_bars[0].open,
            session_high=session_high,
            session_low=session_low,
            session_vwap=session_vwap,
            session_range_position=range_position,
            vwap_position=_vwap_position(latest.close, session_vwap),
            trend=trend,
            trend_reason_codes=reasons,
            nearest_support=support,
            nearest_resistance=resistance,
            prior_session_high=prior_high,
            prior_session_low=prior_low,
            london_range=named_ranges["london"],
            new_york_range=named_ranges["new_york"],
            london_opening_range_15=named_ranges["london_or_15"],
            london_opening_range_30=named_ranges["london_or_30"],
            new_york_opening_range_15=named_ranges["new_york_or_15"],
            new_york_opening_range_30=named_ranges["new_york_or_30"],
            fair_value_gaps=gaps,
            volume_profile=profile,
            prior_volume_profile=prior_profile,
            london_volume_profile=london_profile,
            new_york_volume_profile=new_york_profile,
            profile_location=profile_location,
            location_reason_codes=location_reasons,
            direction_score=direction_score,
            direction_location_reason_codes=direction_location_reasons,
        )


class _BarAggregator:
    def __init__(
        self,
        timeframe: AnalyticsTimeframe,
        session_windows: SessionWindowResolver,
    ) -> None:
        self._timeframe = timeframe
        self._session_windows = session_windows
        self._current: list[AnalysisBar] = []
        self._bucket_start: datetime | None = None

    def update(self, bar: AnalysisBar) -> AnalysisBar | None:
        session_open, _ = self._session_windows.session_window(
            bar.instrument_id,
            bar.open_ts,
        )
        bucket_start = _floor_timestamp(
            bar.open_ts,
            self._timeframe.duration,
            anchor=session_open,
        )
        completed = None
        if self._bucket_start is not None and bucket_start < self._bucket_start:
            raise ValueError("live analytics bars cannot move backward across aggregate buckets")
        if self._bucket_start is not None and bucket_start > self._bucket_start:
            if _complete_minute_bucket(self._current, self._timeframe, self._bucket_start):
                completed = _aggregate(self._current, self._timeframe, self._bucket_start)
            self._current = []
        if self._bucket_start is None or bucket_start != self._bucket_start:
            self._bucket_start = bucket_start
        by_open = {item.open_ts: item for item in self._current}
        by_open[bar.open_ts] = bar
        self._current = sorted(by_open.values(), key=lambda item: item.open_ts)
        return completed


def _ema_values(values: Sequence[Decimal], period: int) -> list[Decimal]:
    indicator = ExponentialMovingAverage(period)
    outputs: list[Decimal] = []
    for value in values:
        indicator.update_raw(float(value))
        outputs.append(Decimal(str(indicator.value)))
    return outputs


def _atr(bars: Sequence[AnalysisBar], period: int) -> Decimal | None:
    if len(bars) < period:
        return None
    indicator = AverageTrueRange(period)
    for bar in bars:
        indicator.update_raw(float(bar.high), float(bar.low), float(bar.close))
    return Decimal(str(indicator.value))


def _trend(
    close: Decimal,
    ema_20: Sequence[Decimal],
    ema_50: Sequence[Decimal],
    count: int,
) -> tuple[TrendState, tuple[str, ...]]:
    if count < 50:
        return TrendState.INSUFFICIENT_DATA, ("fewer_than_50_bars",)
    slope_lookback = min(5, count - 1)
    ema_20_rising = ema_20[-1] > ema_20[-1 - slope_lookback]
    ema_20_falling = ema_20[-1] < ema_20[-1 - slope_lookback]
    if close > ema_20[-1] > ema_50[-1] and ema_20_rising:
        return TrendState.BULLISH, ("close_above_ema_stack", "ema20_rising")
    if close < ema_20[-1] < ema_50[-1] and ema_20_falling:
        return TrendState.BEARISH, ("close_below_ema_stack", "ema20_falling")
    return TrendState.RANGE, ("ema_stack_not_directional",)


def _vwap(bars: Sequence[AnalysisBar]) -> Decimal | None:
    total_volume = sum((bar.volume for bar in bars), Decimal("0"))
    if total_volume == 0:
        return None
    weighted = sum(
        (((bar.high + bar.low + bar.close) / Decimal("3")) * bar.volume for bar in bars),
        Decimal("0"),
    )
    return weighted / total_volume


def _vwap_position(close: Decimal, vwap: Decimal | None) -> VwapPosition:
    if vwap is None:
        return VwapPosition.UNAVAILABLE
    if close > vwap:
        return VwapPosition.ABOVE
    if close < vwap:
        return VwapPosition.BELOW
    return VwapPosition.AT


def _latest_bar_at_or_before(
    bars: Sequence[AnalysisBar],
    timestamp: datetime,
) -> AnalysisBar:
    eligible = [bar for bar in bars if bar.open_ts < timestamp]
    if not eligible:
        raise RuntimeError("no structure bar exists at or before context timestamp")
    return eligible[-1]


def _resolved_session_bars(
    bars: Sequence[AnalysisBar],
    reference: AnalysisBar,
    session_windows: SessionWindowResolver,
    *,
    as_of: datetime | None = None,
) -> list[AnalysisBar]:
    if reference.timeframe == AnalyticsTimeframe.DAILY:
        return [reference]
    open_ts, close_ts = session_windows.session_window(
        reference.instrument_id,
        reference.open_ts,
    )
    resolved = [
        bar
        for bar in bars
        if open_ts <= bar.open_ts < close_ts and (as_of is None or bar.close_ts <= as_of)
    ]
    if not resolved:
        raise RuntimeError("no structure bars belong to the current resolved session")
    return resolved


def _prior_session_bars(
    bars: Sequence[AnalysisBar],
    current_session_open: datetime,
    session_windows: SessionWindowResolver,
) -> list[AnalysisBar]:
    prior = [bar for bar in bars if bar.open_ts < current_session_open]
    if not prior:
        return []
    reference = prior[-1]
    try:
        return _resolved_session_bars(bars, reference, session_windows)
    except RuntimeError:
        return []


def _named_session_ranges(
    bars: Sequence[AnalysisBar],
    as_of: datetime,
) -> dict[str, ContextRange | None]:
    definitions = (
        ("london", "Europe/London", time(8), time(11, 30)),
        ("new_york", "America/New_York", time(9, 30), time(16)),
    )
    result: dict[str, ContextRange | None] = {}
    for label, timezone_name, start_time, end_time in definitions:
        zone = ZoneInfo(timezone_name)
        local_date = as_of.astimezone(zone).date()
        start = datetime.combine(local_date, start_time, zone).astimezone(UTC)
        end = datetime.combine(local_date, end_time, zone).astimezone(UTC)
        result[label] = _context_range(label, bars, start, end, as_of)
        for minutes in (15, 30):
            opening_end = start + timedelta(minutes=minutes)
            result[f"{label}_or_{minutes}"] = _context_range(
                f"{label}_or_{minutes}",
                bars,
                start,
                opening_end,
                as_of,
            )
    return result


def _context_range(
    label: str,
    bars: Sequence[AnalysisBar],
    start: datetime,
    end: datetime,
    as_of: datetime,
) -> ContextRange | None:
    observed_end = min(end, as_of)
    selected = [bar for bar in bars if start <= bar.open_ts < observed_end]
    if not selected:
        return None
    return ContextRange(
        label=label,
        start_ts=start,
        end_ts=end,
        high=max(bar.high for bar in selected),
        low=min(bar.low for bar in selected),
        is_complete=as_of >= end,
    )


def _fair_value_gaps(bars: Sequence[AnalysisBar]) -> tuple[FairValueGap, ...]:
    detected: list[tuple[int, FairValueGap]] = []
    for index in range(2, len(bars)):
        first = bars[index - 2]
        third = bars[index]
        if third.low > first.high:
            detected.append(
                (
                    index,
                    FairValueGap(
                        direction=FairValueGapDirection.BULLISH,
                        timeframe=third.timeframe,
                        lower=first.high,
                        upper=third.low,
                        detected_ts=third.close_ts,
                    ),
                )
            )
        if third.high < first.low:
            detected.append(
                (
                    index,
                    FairValueGap(
                        direction=FairValueGapDirection.BEARISH,
                        timeframe=third.timeframe,
                        lower=third.high,
                        upper=first.low,
                        detected_ts=third.close_ts,
                    ),
                )
            )
    active: list[FairValueGap] = []
    for index, gap in detected:
        subsequent = bars[index + 1 :]
        filled = (
            any(bar.low <= gap.lower for bar in subsequent)
            if gap.direction == FairValueGapDirection.BULLISH
            else any(bar.high >= gap.upper for bar in subsequent)
        )
        if not filled:
            active.append(gap)
    return tuple(active[-10:])


def _volume_profile(
    bars: Sequence[AnalysisBar],
    bin_size: Decimal,
) -> VolumeProfileSnapshot | None:
    volumes: dict[Decimal, Decimal] = defaultdict(lambda: Decimal("0"))
    for bar in bars:
        if bar.volume <= 0:
            continue
        typical = (bar.high + bar.low + bar.close) / Decimal("3")
        price_bin = (typical / bin_size).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        volumes[price_bin * bin_size] += bar.volume
    total = sum(volumes.values(), Decimal("0"))
    if total <= 0:
        return None
    prices = sorted(volumes)
    poc = max(prices, key=lambda price: (volumes[price], price))
    left = right = prices.index(poc)
    included = volumes[poc]
    target = total * Decimal("0.70")
    while included < target and (left > 0 or right < len(prices) - 1):
        left_volume = volumes[prices[left - 1]] if left > 0 else Decimal("-1")
        right_volume = volumes[prices[right + 1]] if right < len(prices) - 1 else Decimal("-1")
        if right_volume > left_volume:
            right += 1
            included += volumes[prices[right]]
        else:
            left -= 1
            included += volumes[prices[left]]
    return VolumeProfileSnapshot(
        bin_size=bin_size,
        value_area_fraction=Decimal("0.70"),
        poc=poc,
        value_area_low=prices[left],
        value_area_high=prices[right],
        total_volume=total,
        input_fidelity=AnalyticsInputFidelity.INFERRED,
        methodology="bar_typical_price_volume",
    )


def _range_volume_profile(
    bars: Sequence[AnalysisBar],
    context_range: ContextRange | None,
    as_of: datetime,
    bin_size: Decimal,
) -> VolumeProfileSnapshot | None:
    if context_range is None:
        return None
    end = min(context_range.end_ts, as_of)
    selected = [bar for bar in bars if context_range.start_ts <= bar.open_ts < end]
    return _volume_profile(selected, bin_size)


def _profile_location(
    close: Decimal,
    profile: VolumeProfileSnapshot | None,
) -> tuple[ProfileLocation, tuple[str, ...]]:
    if profile is None:
        return ProfileLocation.UNAVAILABLE, ("volume_profile_unavailable",)
    if close < profile.value_area_low:
        return ProfileLocation.BELOW_VALUE, ("close_below_value_area",)
    if close > profile.value_area_high:
        return ProfileLocation.ABOVE_VALUE, ("close_above_value_area",)
    half_bin = profile.bin_size / Decimal("2")
    if abs(close - profile.poc) <= half_bin:
        return ProfileLocation.AT_POC, ("close_at_poc",)
    if close < profile.poc:
        return ProfileLocation.LOWER_VALUE, ("close_in_lower_value",)
    return ProfileLocation.UPPER_VALUE, ("close_in_upper_value",)


def _direction_location_summary(
    *,
    trend: TrendState,
    vwap_position: VwapPosition,
    session_range_position: Decimal,
    profile_location: ProfileLocation,
    close: Decimal,
    atr: Decimal | None,
    support: ContextLevel | None,
    resistance: ContextLevel | None,
    gaps: Sequence[FairValueGap],
) -> tuple[int, tuple[str, ...]]:
    score = 0
    reasons: list[str] = []
    if trend == TrendState.BULLISH:
        score += 1
        reasons.append("bullish_ema_context")
    elif trend == TrendState.BEARISH:
        score -= 1
        reasons.append("bearish_ema_context")
    else:
        reasons.append(f"trend_{trend.value}")
    if vwap_position == VwapPosition.ABOVE:
        score += 1
        reasons.append("above_session_vwap")
    elif vwap_position == VwapPosition.BELOW:
        score -= 1
        reasons.append("below_session_vwap")
    else:
        reasons.append(f"vwap_{vwap_position.value}")
    reasons.append(f"profile_{profile_location.value}")
    if session_range_position >= Decimal("0.75"):
        reasons.append("upper_session_quartile")
    elif session_range_position <= Decimal("0.25"):
        reasons.append("lower_session_quartile")
    else:
        reasons.append("middle_session_range")
    if atr is not None and atr > 0:
        proximity = atr / Decimal("4")
        if support is not None and close - support.price <= proximity:
            reasons.append("near_support")
        if resistance is not None and resistance.price - close <= proximity:
            reasons.append("near_resistance")
    if any(gap.lower <= close <= gap.upper for gap in gaps):
        reasons.append("inside_active_fvg")
    return score, tuple(reasons)


def _nearest_levels(
    bars: Sequence[AnalysisBar],
    session_bars: Sequence[AnalysisBar],
    close: Decimal,
) -> tuple[ContextLevel | None, ContextLevel | None]:
    candidates = [
        ContextLevel(
            kind=LevelKind.SESSION_LOW,
            price=min(bar.low for bar in session_bars),
            observed_ts=session_bars[-1].close_ts,
        ),
        ContextLevel(
            kind=LevelKind.SESSION_HIGH,
            price=max(bar.high for bar in session_bars),
            observed_ts=session_bars[-1].close_ts,
        ),
        *_swing_levels(bars[-500:]),
    ]
    supports = [
        level
        for level in candidates
        if level.kind in {LevelKind.SESSION_LOW, LevelKind.SWING_SUPPORT} and level.price <= close
    ]
    resistances = [
        level
        for level in candidates
        if level.kind in {LevelKind.SESSION_HIGH, LevelKind.SWING_RESISTANCE}
        and level.price >= close
    ]
    support = max(supports, key=lambda level: level.price, default=None)
    resistance = min(resistances, key=lambda level: level.price, default=None)
    return support, resistance


def _swing_levels(bars: Sequence[AnalysisBar]) -> tuple[ContextLevel, ...]:
    if len(bars) < 5:
        return ()
    raw: list[tuple[LevelKind, Decimal, datetime]] = []
    for index in range(2, len(bars) - 2):
        bar = bars[index]
        neighbors = (*bars[index - 2 : index], *bars[index + 1 : index + 3])
        if all(bar.low <= neighbor.low for neighbor in neighbors) and any(
            bar.low < neighbor.low for neighbor in neighbors
        ):
            raw.append((LevelKind.SWING_SUPPORT, bar.low, bar.close_ts))
        if all(bar.high >= neighbor.high for neighbor in neighbors) and any(
            bar.high > neighbor.high for neighbor in neighbors
        ):
            raw.append((LevelKind.SWING_RESISTANCE, bar.high, bar.close_ts))
    touches = Counter((kind, price) for kind, price, _ in raw)
    latest = {(kind, price): observed for kind, price, observed in raw}
    return tuple(
        ContextLevel(
            kind=kind,
            price=price,
            observed_ts=latest[(kind, price)],
            touches=count,
        )
        for (kind, price), count in touches.items()
    )


def _floor_timestamp(
    timestamp: datetime,
    duration: timedelta,
    *,
    anchor: datetime,
) -> datetime:
    seconds = int(duration.total_seconds())
    elapsed_seconds = int((timestamp - anchor).total_seconds())
    return anchor + timedelta(seconds=elapsed_seconds - elapsed_seconds % seconds)


def _aggregate(
    bars: Sequence[AnalysisBar],
    timeframe: AnalyticsTimeframe,
    bucket_start: datetime,
) -> AnalysisBar:
    if not bars:
        raise ValueError("cannot aggregate an empty bar bucket")
    sources = {bar.source for bar in bars}
    fidelities = {bar.input_fidelity for bar in bars}
    return AnalysisBar(
        instrument_id=bars[0].instrument_id,
        timeframe=timeframe,
        open_ts=bucket_start,
        close_ts=bucket_start + timeframe.duration,
        open=bars[0].open,
        high=max(bar.high for bar in bars),
        low=min(bar.low for bar in bars),
        close=bars[-1].close,
        volume=sum((bar.volume for bar in bars), Decimal("0")),
        source=next(iter(sources)) if len(sources) == 1 else "mixed",
        input_fidelity=(
            next(iter(fidelities)) if len(fidelities) == 1 else AnalyticsInputFidelity.MIXED
        ),
    )


def _complete_minute_bucket(
    bars: Sequence[AnalysisBar],
    timeframe: AnalyticsTimeframe,
    bucket_start: datetime,
) -> bool:
    expected_count = int(timeframe.duration / timedelta(minutes=1))
    if len(bars) != expected_count:
        return False
    return all(
        bar.timeframe == AnalyticsTimeframe.ONE_MINUTE
        and bar.open_ts == bucket_start + timedelta(minutes=index)
        for index, bar in enumerate(bars)
    )
