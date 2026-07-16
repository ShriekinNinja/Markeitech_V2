from __future__ import annotations

from asyncio import AbstractEventLoop
from collections.abc import Callable
from datetime import timedelta
from threading import Lock
from typing import Any, Protocol

from nautilus_trader.adapters.interactive_brokers.factories import (
    InteractiveBrokersLiveDataClientFactory,
)
from nautilus_trader.live.node import TradingNode
from pydantic import Field

from markeitech.analytics import (
    AnalyticsReadinessEvaluator,
    AnalyticsTimeframe,
    MarketContextCalculationConfig,
    MarketContextEngine,
)
from markeitech.domain.base import VersionedDomainModel
from markeitech.market_data.actions import build_livenode_action_plan
from markeitech.market_data.actor import MarkeitechMarketDataActor
from markeitech.market_data.config import MarketDataRuntimeConfig
from markeitech.market_data.coordinator import (
    WarmupReadyHandler,
    require_historical_coverage,
)
from markeitech.market_data.intents import build_nautilus_request_plan
from markeitech.market_data.nautilus import build_trading_node_config
from markeitech.market_data.planner import build_market_data_plan
from markeitech.persistence.calendar import PandasMarketSessionCalendar
from markeitech.persistence.feature_pipeline import (
    CommittedFeatureRevision,
    FeatureSubmissionStatus,
)
from markeitech.persistence.pipeline import PersistenceSubmissionStatus
from markeitech.persistence.runtime import PersistenceRuntime
from markeitech.persistence.startup_recovery import StartupRecoveryService
from markeitech.runtime import (
    BoundedEventLoopBridge,
    ContextEventCommitProcessor,
    FeatureCommitEventFanout,
)
from markeitech.runtime.actor import ContextEventProjectionActor, OperatorEventProjectionActor
from markeitech.signals import (
    BoundedAggressionObservationStore,
    BoundedFeatureCommitHandoff,
    BoundedSignalProjectionWriter,
    LiveSignalRuntime,
)

LIVE_NODE_START_CONFIRMATION = "I_UNDERSTAND_THIS_CONNECTS_TO_IB"


class LiveNodeLike(Protocol):
    def run(self) -> Any: ...


class LiveNodeTraderLike(Protocol):
    def add_actor(self, actor: Any) -> None: ...


class ConfigurableLiveNodeLike(LiveNodeLike, Protocol):
    trader: LiveNodeTraderLike

    def add_data_client_factory(self, name: str, factory: type[Any]) -> None: ...

    def build(self) -> None: ...

    def get_event_loop(self) -> AbstractEventLoop | None: ...


class LiveNodeBootstrapSummary(VersionedDomainModel):
    can_build_node: bool
    will_start_node: bool
    data_only: bool
    read_only_ib: bool
    execution_clients_enabled: bool
    data_client_name: str = Field(min_length=1)
    persistence_enabled: bool


class PersistenceManagedLiveNode:
    def __init__(
        self,
        node: ConfigurableLiveNodeLike,
        persistence: PersistenceRuntime,
        signal_runtime: LiveSignalRuntime | None = None,
        signal_projection_writer: BoundedSignalProjectionWriter | None = None,
        signal_observations: BoundedAggressionObservationStore | None = None,
        domain_event_bridge: BoundedEventLoopBridge | None = None,
        feature_event_fanout: FeatureCommitEventFanout | None = None,
        context_event_processor: ContextEventCommitProcessor | None = None,
    ) -> None:
        self._node = node
        self.persistence = persistence
        self.signal_runtime = signal_runtime
        self.signal_projection_writer = signal_projection_writer
        self.signal_observations = signal_observations
        self.domain_event_bridge = domain_event_bridge
        self.feature_event_fanout = feature_event_fanout
        self.context_event_processor = context_event_processor
        self._runtime_lifecycle_lock = Lock()
        self._runtimes_started = False
        self._runtimes_stop_started = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._node, name)

    def run(self) -> Any:
        self._start_runtimes()
        try:
            return self._node.run()
        finally:
            self._stop_runtimes()

    async def run_async(self) -> None:
        self._start_runtimes()
        try:
            await self._node.run_async()
        finally:
            self._stop_runtimes()

    async def stop_async(self) -> None:
        try:
            await self._node.stop_async()
        finally:
            self._stop_runtimes()

    def _start_runtimes(self) -> None:
        with self._runtime_lifecycle_lock:
            if self._runtimes_started:
                raise RuntimeError("managed LiveNode runtimes already started")
            self._runtimes_started = True
        self.persistence.start()
        if self.signal_projection_writer is not None:
            self.signal_projection_writer.start()
        if self.signal_runtime is not None:
            try:
                self.signal_runtime.start()
            except Exception:
                self.signal_runtime.stop(self.persistence.config.runtime_shutdown_timeout_seconds)
                if self.signal_projection_writer is not None:
                    self.signal_projection_writer.stop(
                        self.persistence.config.runtime_shutdown_timeout_seconds
                    )
                self.persistence.stop()
                raise

    def _stop_runtimes(self) -> None:
        with self._runtime_lifecycle_lock:
            if not self._runtimes_started or self._runtimes_stop_started:
                return
            self._runtimes_stop_started = True
        shutdown_error: RuntimeError | None = None
        if self.signal_runtime is not None:
            feature_writer = self.persistence.feature_writer
            if feature_writer is None:
                shutdown_error = RuntimeError("signal runtime requires feature writer")
            else:
                timeout = self.persistence.config.runtime_shutdown_timeout_seconds
                if not feature_writer.stop(timeout):
                    shutdown_error = RuntimeError("feature writer did not stop before signal drain")
                if not self.signal_runtime.stop(timeout) and shutdown_error is None:
                    shutdown_error = RuntimeError(
                        "signal runtime did not drain within shutdown timeout"
                    )
                if (
                    self.signal_projection_writer is not None
                    and not self.signal_projection_writer.stop(timeout)
                    and shutdown_error is None
                ):
                    shutdown_error = RuntimeError(
                        "signal projection writer did not drain within shutdown timeout"
                    )
        try:
            self.persistence.stop()
        except Exception as exc:
            if shutdown_error is None:
                raise
            raise shutdown_error from exc
        if shutdown_error is not None:
            raise shutdown_error


def build_livenode_bootstrap_summary(
    config: MarketDataRuntimeConfig,
) -> LiveNodeBootstrapSummary:
    node_config = build_trading_node_config(config)
    return LiveNodeBootstrapSummary(
        can_build_node=config.build_nautilus_node,
        will_start_node=config.run_live_node and config.manual_live_node_start,
        data_only=config.data_only,
        read_only_ib=config.ib.read_only,
        execution_clients_enabled=bool(node_config.exec_clients),
        data_client_name=config.data_client_name,
        persistence_enabled=config.persistence is not None,
    )


def build_live_node(
    config: MarketDataRuntimeConfig,
    *,
    node_factory: Callable[..., LiveNodeLike] = TradingNode,
) -> LiveNodeLike:
    if not config.build_nautilus_node:
        raise RuntimeError("Nautilus LiveNode construction is disabled by config")
    node_config = build_trading_node_config(config)
    return node_factory(config=node_config)


def build_prepared_market_data_live_node(
    config: MarketDataRuntimeConfig,
    *,
    node_factory: Callable[..., ConfigurableLiveNodeLike] = TradingNode,
    actor_factory: Callable[..., Any] = MarkeitechMarketDataActor,
    on_warmup_ready: WarmupReadyHandler = require_historical_coverage,
    data_client_factory: type[Any] = InteractiveBrokersLiveDataClientFactory,
    signal_projection_sink: Callable[[str], None] | None = None,
    signal_role_resolver: Callable[[str], str] | None = None,
) -> ConfigurableLiveNodeLike | PersistenceManagedLiveNode:
    node = build_live_node(config, node_factory=node_factory)
    runtime_plan = build_market_data_plan(config.instrument_registry)
    request_plan = build_nautilus_request_plan(
        runtime_plan,
        data_client_name=config.data_client_name,
    )
    action_plan = build_livenode_action_plan(request_plan)
    session_calendar = PandasMarketSessionCalendar.from_registry(
        config.instrument_registry,
        include_disabled=True,
    )
    signal_handoff = None
    signal_observations = None
    if config.signals is not None and config.signals.enabled_definition_ids_by_instrument:
        signal_handoff = BoundedFeatureCommitHandoff(config.signals.feature_handoff_queue_size)
        signal_observations = BoundedAggressionObservationStore(
            config.signals.aggression_observation_history_bars
        )
    domain_event_bridge = (
        BoundedEventLoopBridge(
            config.domain_events.queue_size,
            drain_batch_size=config.domain_events.drain_batch_size,
        )
        if config.persistence is not None and config.domain_events.enabled
        else None
    )
    persistence = (
        PersistenceRuntime.build(
            config.persistence,
            retention_calendar=session_calendar,
            market_data_commit_sink=(
                None if signal_observations is None else signal_observations.offer_committed
            ),
        )
        if config.persistence
        else None
    )
    context_event_processor = None
    feature_event_fanout = None
    if persistence is not None:
        try:
            if persistence.feature_catalog is None or persistence.feature_writer is None:
                raise RuntimeError("persistence runtime did not build feature storage")
            context_event_processor = ContextEventCommitProcessor(
                persistence.metadata,
                domain_event_bridge,
            )
            feature_history = tuple(
                feature
                for runtime in config.instrument_registry.instruments
                if runtime.enabled
                for feature in persistence.feature_catalog.query_history(
                    runtime.contract.instrument_id
                )
            )
            context_event_processor.reconcile(
                persistence.metadata.committed_feature_revisions(feature_history)
            )

            def critical_feature_sink(
                revisions: tuple[CommittedFeatureRevision, ...],
            ) -> bool:
                assert context_event_processor is not None
                if not context_event_processor.offer(revisions):
                    return False
                return signal_handoff is None or signal_handoff.offer(revisions)

            feature_event_fanout = (
                FeatureCommitEventFanout(domain_event_bridge, critical_sink=critical_feature_sink)
                if domain_event_bridge is not None
                else None
            )
            persistence.feature_writer.set_commit_sink(
                critical_feature_sink
                if feature_event_fanout is None
                else feature_event_fanout.offer
            )
        except Exception:
            persistence.stop()
            raise
    profile_bin_sizes = {
        runtime.contract.instrument_id: runtime.warmup.volume_profile_bin_size
        for runtime in config.instrument_registry.instruments
        if runtime.enabled and runtime.warmup is not None
    }
    profile_composite_sessions = {
        runtime.contract.instrument_id: runtime.warmup.volume_profile_composite_sessions
        for runtime in config.instrument_registry.instruments
        if runtime.enabled and runtime.warmup is not None
    }
    calculation_config = MarketContextCalculationConfig(
        profile_bin_sizes=profile_bin_sizes,
        profile_composite_sessions=profile_composite_sessions,
        session_policies={
            runtime.contract.instrument_id: "|".join(
                (
                    runtime.contract.calendar_id,
                    runtime.contract.session_profile.value,
                    runtime.contract.session_timezone,
                )
            )
            for runtime in config.instrument_registry.instruments
            if runtime.enabled
        },
    )
    market_context_engine = MarketContextEngine(
        session_calendar,
        profile_bin_sizes=profile_bin_sizes,
        profile_composite_sessions=profile_composite_sessions,
        calculation_config=calculation_config,
    )
    actor_kwargs: dict[str, Any] = {
        "on_warmup_ready": on_warmup_ready,
        "market_context_engine": market_context_engine,
        "analytics_readiness_evaluator": AnalyticsReadinessEvaluator(
            session_calendar,
            {
                runtime.contract.instrument_id: {
                    AnalyticsTimeframe(timeframe.value): runtime.warmup.lookback_for(timeframe)
                    for timeframe in runtime.warmup.timeframes
                }
                for runtime in config.instrument_registry.instruments
                if runtime.enabled and runtime.warmup is not None
            },
        ),
        "operator_context_report_interval": (
            timedelta(seconds=config.operator_context.interval_seconds)
            if config.operator_context.enabled
            else None
        ),
    }
    if persistence is not None:
        if persistence.feature_writer is None:
            raise RuntimeError("persistence runtime did not build a feature writer")
        startup_recovery = StartupRecoveryService(
            config.persistence,
            config.instrument_registry,
            persistence.catalog,
            persistence.metadata,
            session_calendar,
            flush_pending=lambda: persistence.writer.flush(
                config.persistence.runtime_startup_timeout_seconds
            ),
        )
        actor_kwargs.update(
            on_native_market_data_event=persistence.ingress.submit_native,
            on_market_data_event=persistence.ingress.submit_canonical,
            on_historical_bar=lambda bar: persistence.ingress.submit_canonical(bar)
            == PersistenceSubmissionStatus.ACCEPTED,
            startup_recovery=startup_recovery,
            on_market_context=lambda snapshot: persistence.feature_writer.submit(
                market_context_engine.feature_for(snapshot)
            )
            == FeatureSubmissionStatus.ACCEPTED,
        )
    try:
        actor = actor_factory(action_plan, **actor_kwargs)
        node.trader.add_actor(actor)
        if domain_event_bridge is not None:
            event_loop = node.get_event_loop()
            if event_loop is None:
                raise RuntimeError("domain event bridge requires a Nautilus event loop")
            node.trader.add_actor(
                OperatorEventProjectionActor(
                    domain_event_bridge,
                    event_loop.call_soon_threadsafe,
                    dedupe_size=config.domain_events.operator_dedupe_size,
                )
            )
            node.trader.add_actor(
                ContextEventProjectionActor(
                    dedupe_size=config.domain_events.operator_dedupe_size,
                )
            )
        node.add_data_client_factory(config.data_client_name, data_client_factory)
        node.build()
    except Exception:
        if persistence is not None:
            persistence.stop()
        raise
    if persistence is None:
        return node
    if signal_observations is not None and config.signals is not None:
        for instrument_id in config.signals.enabled_definition_ids_by_instrument:
            if not signal_observations.offer_committed(
                persistence.catalog.query_one_minute_bars(instrument_id)
            ):
                persistence.stop()
                raise RuntimeError("catalog contains conflicting aggression observation bars")
    signal_projection_writer = None
    signal_runtime = None
    if config.signals is not None and signal_handoff is not None:
        sink = signal_projection_sink
        colored_sink = None
        if sink is None:
            actor_log = getattr(actor, "log", None)
            if actor_log is None or not callable(getattr(actor_log, "info", None)):
                persistence.stop()
                raise RuntimeError("signal projection requires an actor INFO log sink")
            sink = actor_log.info
            colored_sink = actor_log.info
        role_resolver = signal_role_resolver
        if role_resolver is None:
            if not hasattr(actor, "active_switch"):
                persistence.stop()
                raise RuntimeError("signal projection requires active instrument state")

            def resolve_actor_role(instrument_id: str) -> str:
                return (
                    "ACTIVE"
                    if actor.active_switch.active_instrument_id == instrument_id
                    else "BACKGROUND"
                )

            role_resolver = resolve_actor_role
        signal_projection_writer = BoundedSignalProjectionWriter(
            sink,
            role_resolver,
            colored_sink=colored_sink,
            queue_size=config.signals.operator_projection_queue_size,
            dedupe_size=config.signals.operator_projection_dedupe_size,
        )
        signal_runtime = LiveSignalRuntime(
            config.signals,
            persistence.metadata,
            session_calendar,
            signal_handoff,
            observation_store=signal_observations,
            role_resolver=role_resolver,
            on_projection=signal_projection_writer.submit,
        )
    return PersistenceManagedLiveNode(
        node,
        persistence,
        signal_runtime,
        signal_projection_writer,
        signal_observations,
        domain_event_bridge,
        feature_event_fanout,
        context_event_processor,
    )


def start_live_node(
    config: MarketDataRuntimeConfig,
    node: LiveNodeLike,
    *,
    confirmation: str | None,
) -> Any:
    validate_live_node_start(config, confirmation=confirmation)
    return node.run()


def validate_live_node_start(
    config: MarketDataRuntimeConfig,
    *,
    confirmation: str | None,
) -> None:
    if not config.run_live_node:
        raise RuntimeError("Nautilus LiveNode start is disabled by config")
    if not config.manual_live_node_start:
        raise RuntimeError("Nautilus LiveNode start requires manual_live_node_start")
    if confirmation != LIVE_NODE_START_CONFIRMATION:
        raise RuntimeError(
            "Nautilus LiveNode start requires explicit confirmation token "
            f"{LIVE_NODE_START_CONFIRMATION!r}"
        )
