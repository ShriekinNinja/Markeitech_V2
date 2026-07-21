from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol

from nautilus_trader.common.actor import Actor
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import ClientId, InstrumentId

from markeitech.analytics import (
    AnalyticsReadinessSnapshot,
    AnalyticsReadinessStatus,
    MarketContextSnapshot,
)
from markeitech.auction_pressure import (
    SessionAuctionPressureAccumulator,
    SessionAuctionPressureSnapshot,
)
from markeitech.domain.events import ActiveInstrumentChangedEvent
from markeitech.domain.market_data import ClassifiedTrade, OneMinuteBar
from markeitech.market_data.actions import (
    LiveNodeAction,
    LiveNodeActionKind,
    LiveNodeActionPhase,
    LiveNodeActionPlan,
)
from markeitech.market_data.coordinator import (
    WarmupCoordinator,
    WarmupReadyHandler,
    WarmupState,
)
from markeitech.market_data.health import (
    MarketDataHealthMonitor,
    MarketDataHealthSink,
    MarketDataHealthSnapshot,
    SessionOpenResolver,
)
from markeitech.market_data.normalization import normalize_one_minute_bar
from markeitech.market_data.operator_context import OperatorContextReporter
from markeitech.market_data.routing import (
    InstrumentMarketDataSnapshot,
    LiveMarketDataRouter,
    MarketDataEventSink,
)
from markeitech.market_data.switching import (
    ActiveInstrumentSwitchCoordinator,
    ActiveInstrumentSwitchRequest,
    ActiveSwitchSnapshot,
)


class NautilusActorApi(Protocol):
    def request_bars(self, bar_type: Any, start: datetime, **kwargs: Any) -> Any: ...

    def subscribe_trade_ticks(self, instrument_id: Any, **kwargs: Any) -> Any: ...

    def subscribe_quote_ticks(self, instrument_id: Any, **kwargs: Any) -> Any: ...

    def subscribe_bars(self, bar_type: Any, **kwargs: Any) -> Any: ...

    def unsubscribe_trade_ticks(self, instrument_id: Any, **kwargs: Any) -> Any: ...

    def unsubscribe_quote_ticks(self, instrument_id: Any, **kwargs: Any) -> Any: ...


WarmupStartResolver = Callable[[int, datetime], datetime]
NativeMarketDataSink = Callable[[object], None]
HistoricalBarSink = Callable[[OneMinuteBar], bool]
MarketContextSink = Callable[[MarketContextSnapshot], None]


class MarketContextEngineLike(Protocol):
    @property
    def snapshots(self) -> tuple[MarketContextSnapshot, ...]: ...

    def initialize(
        self,
        data_by_bar_type: dict[str, tuple[Any, ...]],
    ) -> tuple[MarketContextSnapshot, ...]: ...

    def update_one_minute(self, bar: OneMinuteBar) -> tuple[MarketContextSnapshot, ...]: ...


class AnalyticsReadinessEvaluatorLike(Protocol):
    def evaluate(
        self,
        data_by_bar_type: dict[str, tuple[Any, ...]],
        *,
        evaluated_ts: datetime,
    ) -> AnalyticsReadinessSnapshot: ...


class StartupRecoveryServiceLike(Protocol):
    @property
    def snapshot(self) -> Any: ...

    def observe_bar(self, bar: OneMinuteBar, *, accepted: bool) -> None: ...

    def prepare(self, now: datetime) -> tuple[Any, ...]: ...

    def finish(self, now: datetime) -> Any: ...


class ActorStartupRecoveryHook:
    def __init__(
        self,
        service: StartupRecoveryServiceLike,
        *,
        data_client_name: str,
        now: Callable[[], datetime],
    ) -> None:
        self._service = service
        self._data_client_name = data_client_name
        self._now = now

    def prepare(self) -> tuple[LiveNodeAction, ...]:
        return tuple(
            LiveNodeAction(
                instrument_id=request.instrument_id,
                kind=LiveNodeActionKind.REQUEST_HISTORICAL_BARS,
                phase=LiveNodeActionPhase.WARMUP,
                data_client_name=self._data_client_name,
                bar_type=f"{request.instrument_id}-1-MINUTE-LAST-EXTERNAL",
                request_start_ts=request.start_ts,
                request_end_ts=request.end_ts,
                recovery_request_id=request.request_id,
            )
            for request in self._service.prepare(self._now())
        )

    def finish(self) -> None:
        self._service.finish(self._now())


class NautilusActorActionTarget:
    def __init__(
        self,
        actor: NautilusActorApi,
        *,
        now: Callable[[], datetime],
        resolve_warmup_start: WarmupStartResolver | None = None,
    ) -> None:
        self._actor = actor
        self._now = now
        self._resolve_warmup_start = resolve_warmup_start or conservative_warmup_start

    def request_historical_bars(
        self,
        *,
        instrument_id: str,
        bar_type: str,
        lookback_sessions: int | None,
        request_start_ts: datetime | None = None,
        request_end_ts: datetime | None = None,
        data_client_name: str,
        callback: Callable[[Any], None] | None = None,
    ) -> Any:
        del instrument_id
        end = request_end_ts or self._now()
        start = request_start_ts
        if start is None:
            if lookback_sessions is None:
                raise ValueError("historical request requires lookback sessions or exact range")
            start = self._resolve_warmup_start(lookback_sessions, end)
        return self._actor.request_bars(
            BarType.from_str(bar_type),
            start=start,
            end=end,
            client_id=ClientId(data_client_name),
            callback=callback,
        )

    def subscribe_trade_ticks(
        self,
        *,
        instrument_id: str,
        data_client_name: str,
    ) -> Any:
        return self._actor.subscribe_trade_ticks(
            InstrumentId.from_str(instrument_id),
            client_id=ClientId(data_client_name),
        )

    def subscribe_quote_ticks(
        self,
        *,
        instrument_id: str,
        data_client_name: str,
    ) -> Any:
        return self._actor.subscribe_quote_ticks(
            InstrumentId.from_str(instrument_id),
            client_id=ClientId(data_client_name),
        )

    def subscribe_bars(
        self,
        *,
        instrument_id: str,
        bar_type: str,
        data_client_name: str,
    ) -> Any:
        del instrument_id
        return self._actor.subscribe_bars(
            BarType.from_str(bar_type),
            client_id=ClientId(data_client_name),
        )

    def unsubscribe_trade_ticks(
        self,
        *,
        instrument_id: str,
        data_client_name: str,
    ) -> Any:
        return self._actor.unsubscribe_trade_ticks(
            InstrumentId.from_str(instrument_id),
            client_id=ClientId(data_client_name),
        )

    def unsubscribe_quote_ticks(
        self,
        *,
        instrument_id: str,
        data_client_name: str,
    ) -> Any:
        return self._actor.unsubscribe_quote_ticks(
            InstrumentId.from_str(instrument_id),
            client_id=ClientId(data_client_name),
        )


class MarkeitechMarketDataActor(Actor):
    def __init__(
        self,
        action_plan: LiveNodeActionPlan,
        *,
        on_warmup_ready: WarmupReadyHandler,
        on_active_instrument_changed: Callable[[ActiveInstrumentChangedEvent], None] | None = None,
        on_market_data_event: MarketDataEventSink | None = None,
        on_native_market_data_event: NativeMarketDataSink | None = None,
        on_historical_bar: HistoricalBarSink | None = None,
        market_context_engine: MarketContextEngineLike | None = None,
        analytics_readiness_evaluator: AnalyticsReadinessEvaluatorLike | None = None,
        on_market_context: MarketContextSink | None = None,
        startup_recovery: StartupRecoveryServiceLike | None = None,
        on_market_data_health: MarketDataHealthSink | None = None,
        is_session_open: SessionOpenResolver | None = None,
        resolve_warmup_start: WarmupStartResolver | None = None,
        operator_context_report_interval: timedelta | None = timedelta(minutes=1),
        auction_pressure_accumulator: SessionAuctionPressureAccumulator | None = None,
        on_operator_context_report: (
            Callable[
                [
                    tuple[MarketContextSnapshot, ...],
                    str,
                    str,
                    SessionAuctionPressureSnapshot | None,
                ],
                None,
            ]
            | None
        ) = None,
        on_runtime_health: Callable[[str, str], None] | None = None,
    ) -> None:
        super().__init__()
        if (
            operator_context_report_interval is not None
            and operator_context_report_interval <= timedelta(0)
        ):
            raise ValueError("operator context report interval must be positive")
        target = NautilusActorActionTarget(
            self,
            now=lambda: self.clock.utc_now(),
            resolve_warmup_start=resolve_warmup_start,
        )
        if startup_recovery is not None and on_historical_bar is None:
            raise ValueError("startup recovery requires a historical bar persistence sink")
        data_client_names = {action.data_client_name for action in action_plan.actions}
        if len(data_client_names) != 1:
            raise ValueError("market-data actor requires exactly one data client")
        data_client_name = next(iter(data_client_names))
        recovery_hook = (
            ActorStartupRecoveryHook(
                startup_recovery,
                data_client_name=data_client_name,
                now=lambda: self.clock.utc_now(),
            )
            if startup_recovery is not None
            else None
        )
        self._warmup = WarmupCoordinator(
            action_plan,
            target,
            on_warmup_ready=self._analyze_warmup,
            startup_recovery=recovery_hook,
            on_warmup_retry=lambda action, attempt, maximum: self.log.warning(
                f"WARMUP_RETRY | {action.bar_type} | attempt={attempt}/{maximum} "
                "| reason=empty_or_timed_out_response"
            ),
            on_warmup_failure=lambda exc: self.log.error(
                f"WARMUP_FAILED | {type(exc).__name__}: {exc}"
            ),
        )
        enabled_instrument_ids = {
            action.instrument_id
            for action in action_plan.actions
            if action.phase == LiveNodeActionPhase.WARMUP
        }
        self._switch_timer_name: str | None = None
        self._last_active_instrument_changed_event: ActiveInstrumentChangedEvent | None = None
        self._on_active_instrument_changed = on_active_instrument_changed
        self._switch = ActiveInstrumentSwitchCoordinator(
            active_instrument_id=action_plan.active_instrument_id,
            enabled_instrument_ids=enabled_instrument_ids,
            data_client_name=data_client_name,
            target=target,
            now=lambda: self.clock.utc_now(),
            runtime_ready=lambda: self._warmup.state == WarmupState.LIVE,
            on_changed=self._handle_active_instrument_changed,
        )
        self._external_market_data_sink = on_market_data_event
        self._native_market_data_sink = on_native_market_data_event
        self._historical_bar_sink = on_historical_bar
        self._startup_recovery = startup_recovery
        self._market_context = market_context_engine
        self._analytics_readiness_evaluator = analytics_readiness_evaluator
        self._analytics_readiness_snapshot: AnalyticsReadinessSnapshot | None = None
        self._on_market_context = on_market_context
        self._operator_context = OperatorContextReporter()
        self._operator_context_report_interval = operator_context_report_interval
        self._operator_context_timer_started = False
        self._auction_pressure_accumulator = auction_pressure_accumulator
        self._auction_pressure_snapshot: SessionAuctionPressureSnapshot | None = None
        self._on_operator_context_report = on_operator_context_report
        self._on_runtime_health = on_runtime_health
        self._on_warmup_ready = on_warmup_ready
        self._health = MarketDataHealthMonitor(
            instrument_ids=enabled_instrument_ids,
            active_instrument_id=lambda: self._switch.snapshot.active_instrument_id,
            now=lambda: self.clock.utc_now(),
            is_session_open=is_session_open or (lambda _instrument_id, _now: True),
            on_change=on_market_data_health,
        )
        self._health_timer_started = False
        self._router = LiveMarketDataRouter(
            instrument_ids=enabled_instrument_ids,
            active_instrument_id=lambda: self._switch.snapshot.active_instrument_id,
            on_event=self._handle_market_data_event,
        )

    @property
    def warmup_state(self) -> WarmupState:
        return self._warmup.state

    @property
    def active_switch(self) -> ActiveSwitchSnapshot:
        return self._switch.snapshot

    @property
    def last_active_instrument_changed_event(self) -> ActiveInstrumentChangedEvent | None:
        return self._last_active_instrument_changed_event

    @property
    def market_data_snapshots(self) -> tuple[InstrumentMarketDataSnapshot, ...]:
        return self._router.snapshots()

    @property
    def market_data_health(self) -> MarketDataHealthSnapshot:
        return self._health.current

    @property
    def startup_recovery_snapshot(self) -> Any | None:
        return None if self._startup_recovery is None else self._startup_recovery.snapshot

    @property
    def market_context_snapshots(self) -> tuple[MarketContextSnapshot, ...]:
        return () if self._market_context is None else self._market_context.snapshots

    @property
    def analytics_readiness_snapshot(self) -> AnalyticsReadinessSnapshot | None:
        return self._analytics_readiness_snapshot

    def on_start(self) -> None:
        if self._on_runtime_health is not None:
            self._on_runtime_health("STARTED", "Market-data actor started; warmup is beginning.")
        self._warmup.start()
        self.clock.set_timer(
            name="market-data-health",
            interval=timedelta(seconds=1),
            callback=lambda _event: self._health.evaluate(),
        )
        self._health_timer_started = True

    def on_stop(self) -> None:
        if self._health_timer_started:
            self.clock.cancel_timer("market-data-health")
            self._health_timer_started = False
        if self._operator_context_timer_started:
            self.clock.cancel_timer("operator-context-report")
            self._operator_context_timer_started = False
        self._cancel_switch_timer()
        if self._on_runtime_health is not None:
            self._on_runtime_health("STOPPED", "Market-data actor stopped.")

    def on_historical_data(self, data: Any) -> None:
        bar_type = getattr(data, "bar_type", None)
        if bar_type is not None:
            self._warmup.record_historical_data(bar_type=str(bar_type), data=data)
            if self._startup_recovery is not None and data.bar_type.spec.timedelta == timedelta(
                minutes=1
            ):
                normalized = normalize_one_minute_bar(
                    data,
                    source="ib",
                    received_ts=self.clock.utc_now(),
                )
                accepted = self._historical_bar_sink(normalized)
                self._startup_recovery.observe_bar(normalized, accepted=accepted)

    def on_trade_tick(self, tick: Any) -> None:
        if self._router.handle_trade_tick(tick) is None:
            return
        if self._native_market_data_sink is not None:
            self._native_market_data_sink(tick)
        event = self._switch.observe_trade_tick(str(tick.instrument_id))
        if event is not None:
            self._cancel_switch_timer()

    def on_quote_tick(self, tick: Any) -> None:
        if self._router.handle_quote_tick(tick) is None:
            return
        if self._native_market_data_sink is not None:
            self._native_market_data_sink(tick)
        event = self._switch.observe_quote_tick(str(tick.instrument_id))
        if event is not None:
            self._cancel_switch_timer()

    def on_bar(self, bar: Any) -> None:
        self._router.handle_bar(bar)

    def request_active_instrument_switch(
        self,
        request: ActiveInstrumentSwitchRequest,
    ) -> ActiveSwitchSnapshot:
        snapshot = self._switch.request_switch(request)
        if snapshot.deadline is None:
            raise RuntimeError("active switch deadline is missing")
        timer_name = f"active-switch:{request.request_id}"
        self._switch_timer_name = timer_name
        self.clock.set_time_alert(
            name=timer_name,
            alert_time=snapshot.deadline,
            callback=lambda _event: self._handle_switch_timeout(),
        )
        return snapshot

    def _handle_switch_timeout(self) -> None:
        self._switch.check_timeout()
        self._switch_timer_name = None

    def _handle_active_instrument_changed(self, event: ActiveInstrumentChangedEvent) -> None:
        self._router.activate_instrument(event.active_instrument_id)
        self._health.evaluate()
        self._last_active_instrument_changed_event = event
        if self._on_active_instrument_changed is not None:
            self._on_active_instrument_changed(event)

    def _handle_market_data_event(self, event: Any) -> None:
        self._health.observe(event)
        if isinstance(event, ClassifiedTrade) and self._auction_pressure_accumulator is not None:
            self._auction_pressure_snapshot = self._auction_pressure_accumulator.observe(event)
        if self._external_market_data_sink is not None:
            self._external_market_data_sink(event)
        if (
            self._market_context is not None
            and isinstance(event, OneMinuteBar)
            and event.is_complete
            and should_update_market_context(
                event,
                active_instrument_id=self._switch.snapshot.active_instrument_id,
            )
        ):
            for snapshot in self._market_context.update_one_minute(event):
                self._emit_market_context(snapshot, phase="live")

    def _analyze_warmup(self, snapshot: Any) -> None:
        self._on_warmup_ready(snapshot)
        if self._analytics_readiness_evaluator is not None:
            readiness = self._analytics_readiness_evaluator.evaluate(
                snapshot.data_by_bar_type,
                evaluated_ts=self.clock.utc_now(),
            )
            self._analytics_readiness_snapshot = readiness
            for instrument in readiness.instruments:
                self.log.info(format_analytics_readiness(instrument))
            if readiness.status == AnalyticsReadinessStatus.BLOCKED:
                raise RuntimeError(
                    "analytics warmup readiness is blocked: " + ", ".join(readiness.reason_codes)
                )
            if self._on_runtime_health is not None:
                self._on_runtime_health(
                    f"ANALYTICS_{readiness.status.value.upper()}",
                    " | ".join(
                        f"{item.instrument_id}={item.status.value}"
                        for item in readiness.instruments
                    ),
                )
        if self._market_context is None:
            return
        contexts = self._market_context.initialize(snapshot.data_by_bar_type)
        for context in contexts:
            self._emit_market_context(context, phase="warmup")
        self._emit_operator_context(phase="warmup", force=True)
        self._start_operator_context_timer()

    def _emit_market_context(self, snapshot: MarketContextSnapshot, *, phase: str) -> None:
        self.log.debug(
            f"MARKET_CONTEXT_EVENT | phase={phase.upper()} | {snapshot.model_dump_json()}"
        )
        if self._on_market_context is not None:
            self._on_market_context(snapshot)

    def _start_operator_context_timer(self) -> None:
        if self._operator_context_report_interval is None or self._operator_context_timer_started:
            return
        self.clock.set_timer(
            name="operator-context-report",
            interval=self._operator_context_report_interval,
            callback=lambda _event: self._emit_operator_context(phase="live"),
        )
        self._operator_context_timer_started = True

    def _emit_operator_context(self, *, phase: str, force: bool = False) -> None:
        if self._market_context is None:
            return
        lines = self._operator_context.render(
            self._market_context.snapshots,
            active_instrument_id=self._switch.snapshot.active_instrument_id,
            phase=phase,
            force=force,
        )
        if not lines:
            return
        self.log.info(
            f"OPERATOR_CONTEXT_BEGIN | phase={phase.upper()} " f"| instruments={len(lines) // 3}"
        )
        for line in lines:
            self.log.info(line)
        self.log.info(
            format_classification_fidelity(
                self._router.snapshot(self._switch.snapshot.active_instrument_id)
            )
        )
        self.log.info(f"OPERATOR_CONTEXT_COMPLETE | phase={phase.upper()}")
        if self._on_operator_context_report is not None:
            changed_instruments = {
                fields[3]
                for line in lines
                if len(fields := [field.strip() for field in line.split("|")]) > 3
            }
            self._on_operator_context_report(
                tuple(
                    snapshot
                    for snapshot in self._market_context.snapshots
                    if snapshot.instrument_id in changed_instruments
                ),
                phase,
                self._switch.snapshot.active_instrument_id,
                self._auction_pressure_snapshot,
            )

    def _cancel_switch_timer(self) -> None:
        if self._switch_timer_name is not None:
            self.clock.cancel_timer(self._switch_timer_name)
            self._switch_timer_name = None


def conservative_warmup_start(lookback_sessions: int, end: datetime) -> datetime:
    # Over-fetch calendar days so weekends and common holiday closures do not reduce coverage.
    calendar_days = max(lookback_sessions * 2, lookback_sessions + 4)
    return end - timedelta(days=calendar_days)


def should_update_market_context(
    bar: OneMinuteBar,
    *,
    active_instrument_id: str,
) -> bool:
    if bar.instrument_id != active_instrument_id:
        return True
    return bar.source == "classified_ticks"


def format_market_context(
    snapshot: MarketContextSnapshot,
    *,
    phase: str = "live",
) -> str:
    if phase not in {"warmup", "live"}:
        raise ValueError(f"unsupported market context phase {phase!r}")
    vwap = _display_value(snapshot.session_vwap)
    ema_20 = _display_value(snapshot.ema_20)
    ema_50 = _display_value(snapshot.ema_50)
    ema_200 = _display_value(snapshot.ema_200)
    atr_14 = _display_value(snapshot.atr_14)
    support = _display_value(
        None if snapshot.nearest_support is None else snapshot.nearest_support.price
    )
    resistance = _display_value(
        None if snapshot.nearest_resistance is None else snapshot.nearest_resistance.price
    )
    session_position = f"{snapshot.session_range_position * 100:.1f}%"
    return (
        f"MARKET_CONTEXT | phase={phase.upper()} | {snapshot.instrument_id} "
        f"{snapshot.timeframe.value} "
        f"| trend={snapshot.trend.value.upper()} | price={snapshot.close} "
        f"| EMA[20={ema_20} 50={ema_50} 200={ema_200}] "
        f"| VWAP[{vwap} {snapshot.vwap_position.value}] | ATR14={atr_14} "
        f"| SESSION[low={snapshot.session_low} high={snapshot.session_high} "
        f"position={session_position}] | LEVELS[support={support} resistance={resistance}] "
        f"| D/L[score={snapshot.direction_score} location={snapshot.profile_location.value} "
        f"active_fvgs={len(snapshot.fair_value_gaps)}] "
        f"| input={snapshot.input_fidelity.value}:{snapshot.source} "
        f"| as_of={snapshot.as_of.isoformat()}"
    )


def format_analytics_readiness(value: Any) -> str:
    timeframes = " | ".join(
        f"{item.timeframe.value}={item.freshness.value}/"
        f"{item.depth.value}/bars:{item.bar_count}/lag:{item.lag_intervals}"
        for item in value.timeframes
    )
    return (
        f"ANALYTICS_READY | {value.instrument_id} | status={value.status.value.upper()} "
        f"| {timeframes} | reasons={','.join(value.reason_codes)}"
    )


def format_classification_fidelity(snapshot: InstrumentMarketDataSnapshot) -> str:
    total_volume = snapshot.classified_volume + snapshot.unknown_volume
    ratio = Decimal("0") if total_volume == 0 else snapshot.classified_volume / total_volume
    reasons = ",".join(
        f"{reason}:{count}"
        for reason, count in sorted(
            snapshot.classification_reason_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )
    return (
        f"OPERATOR_FLOW | role=ACTIVE | {snapshot.instrument_id} "
        f"| trades={snapshot.trade_tick_count} "
        f"| classified={snapshot.classified_trade_count} "
        f"| unknown={snapshot.unknown_trade_count} "
        f"| volume={total_volume} | classified_volume={snapshot.classified_volume} "
        f"| unknown_volume={snapshot.unknown_volume} | classified_ratio={ratio:.2%} "
        f"| reasons={reasons or 'none'}"
    )


def format_market_structure(
    snapshot: MarketContextSnapshot,
    *,
    phase: str = "live",
) -> str:
    if phase not in {"warmup", "live"}:
        raise ValueError(f"unsupported market context phase {phase!r}")
    prior = _display_price_pair(snapshot.prior_session_low, snapshot.prior_session_high)
    london = _display_context_range(snapshot.london_range)
    new_york = _display_context_range(snapshot.new_york_range)
    opening_ranges = " ".join(
        (
            f"L15={_display_context_range(snapshot.london_opening_range_15)}",
            f"L30={_display_context_range(snapshot.london_opening_range_30)}",
            f"NY15={_display_context_range(snapshot.new_york_opening_range_15)}",
            f"NY30={_display_context_range(snapshot.new_york_opening_range_30)}",
        )
    )
    return (
        f"MARKET_STRUCTURE | phase={phase.upper()} | {snapshot.instrument_id} "
        f"{snapshot.timeframe.value} | RANGES[prior={prior} london={london} "
        f"new_york={new_york}] | OR[{opening_ranges}] "
        f"| PROFILE[current={_display_profile(snapshot.volume_profile)} "
        f"prior={_display_profile(snapshot.prior_volume_profile)} "
        f"london={_display_profile(snapshot.london_volume_profile)} "
        f"new_york={_display_profile(snapshot.new_york_volume_profile)}] "
        f"| D/L[score={snapshot.direction_score} "
        f"reasons={','.join(snapshot.direction_location_reason_codes)}] "
        f"| FVG[active={_display_fvgs(snapshot.fair_value_gaps)}] "
        f"| as_of={snapshot.as_of.isoformat()}"
    )


def _display_value(value: Any | None) -> str:
    return "n/a" if value is None else str(value)


def _display_price_pair(low: Any | None, high: Any | None) -> str:
    if low is None or high is None:
        return "n/a"
    return f"{low}/{high}"


def _display_context_range(value: Any | None) -> str:
    if value is None:
        return "n/a"
    state = "complete" if value.is_complete else "developing"
    return f"{value.low}/{value.high}:{state}"


def _display_profile(value: Any | None) -> str:
    if value is None:
        return "n/a"
    return (
        f"{value.value_area_low}/{value.poc}/{value.value_area_high}:"
        f"{value.input_fidelity.value}"
    )


def _display_fvgs(values: Any) -> str:
    if not values:
        return "none"
    return ",".join(f"{gap.direction.value}:{gap.lower}-{gap.upper}" for gap in values[-3:])
