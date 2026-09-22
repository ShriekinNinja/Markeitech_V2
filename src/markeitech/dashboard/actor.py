from __future__ import annotations

from dataclasses import asdict, replace

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, CustomData, DataType

from markeitech.acquisition import (
    HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
    HISTORICAL_EXECUTION_SIGNAL,
    HistoricalExecutionEventMessage,
)
from markeitech.acquisition.dashboard_history import (
    HISTORY_PAGE_TYPE_NAME,
    DashboardHistoryPage,
    DashboardHistoryRequest,
)
from markeitech.dashboard.config import DashboardConfig
from markeitech.dashboard.messages import (
    DASHBOARD_DEMAND_SIGNAL,
    DASHBOARD_READY_SIGNAL,
    WATCHLIST_MEMBERSHIP_REQUEST_SIGNAL,
    DashboardDemand,
    DashboardReadyEvent,
)
from markeitech.dashboard.server import DashboardServer
from markeitech.dashboard.state import DashboardState
from markeitech.system.messages import (
    ACQUISITION_STREAM_SIGNAL,
    WATCHLIST_MEMBERSHIP_SIGNAL,
    AcquisitionStreamEvent,
    WatchlistMembershipEvent,
)


class DashboardActorConfig(DataActorConfig):
    def __new__(
        cls,
        dashboard: dict,
        market_data_type: str = "unknown",
        watchlist_enabled: bool = True,
        actor_id: str = "DASHBOARD",
    ) -> DashboardActorConfig:
        obj = super().__new__(cls, actor_id=ActorId.from_str(actor_id))
        obj.dashboard = DashboardConfig.from_mapping(dashboard)
        obj.market_data_type = market_data_type
        obj.watchlist_enabled = watchlist_enabled
        return obj


class DashboardActor(DataActor):
    """Project admitted native observations and own the local web-server lifecycle.

    Market-data requests and native callback attachment/release are executed by
    DataAcquisitionActor. This actor never calls native subscription methods.

    Markeitech Metadata:
        architecture.component.id: actor.dashboard
        architecture.component.label: Dashboard
        architecture.component.kind: markeitech_actor
        architecture.component.boundary: boundary.system
        architecture.component.responsibilities:
            - Request configured display feeds through acquisition and receive native callbacks.
            - Retain bounded transient display state and own local web-server startup and shutdown.
            - Reconcile browser chart selections and project native provider revisions and history.
            - Announce the accepting dashboard address for operational Discord projection.
    """

    def __init__(self, config: DashboardActorConfig) -> None:
        super().__init__(config)
        self._policy = config.dashboard
        self._display = DashboardState(self._policy, config.market_data_type)
        self._server = DashboardServer(self._policy, self._display.snapshot())
        self._demands: dict[str, DashboardDemand] = {}
        self._membership_received = not config.watchlist_enabled
        self._published_sequence = -1
        self._active = False
        self._server_failure_reported = False
        self._ready_announced = False
        self._page_type = DataType(HISTORY_PAGE_TYPE_NAME)
        self._page_requests: dict[str, tuple[DashboardHistoryRequest, int, bool]] = {}

    def on_start(self) -> None:
        self._active = True
        if self._membership_received:
            self._display.set_members([])
        self.subscribe_signal(WATCHLIST_MEMBERSHIP_SIGNAL)
        self.subscribe_signal(ACQUISITION_STREAM_SIGNAL)
        self.subscribe_signal(HISTORICAL_EXECUTION_SIGNAL)
        self.subscribe_data(self._page_type)
        self._server.start()
        self.clock.set_timer_ns(
            "dashboard-projection",
            self._policy.publish_interval_ms * 1_000_000,
            callback=self._publish,
        )
        self.clock.set_timer_ns(
            "dashboard-membership",
            self._policy.acquisition_retry_interval_ms * 1_000_000,
            callback=self._request_membership,
        )
        self._request_membership(None)
        self.log.info(f"DASHBOARD_STARTING | url=http://127.0.0.1:{self._policy.port}")

    def _request_membership(self, _event) -> None:  # noqa: ANN001
        if self._active and not self._membership_received:
            self.publish_signal(WATCHLIST_MEMBERSHIP_REQUEST_SIGNAL, "DASHBOARD")
        if self._active:
            self._retry_pages()

    def on_signal(self, signal: Signal) -> None:
        if not self._active:
            return
        try:
            if signal.name == WATCHLIST_MEMBERSHIP_SIGNAL:
                membership = WatchlistMembershipEvent.from_signal_value(signal.value)
                if membership.source != "WATCHLIST":
                    return
                members = [m.to_dict() for m in membership.members]
                if self._membership_received:
                    return  # POC membership is immutable for this run.
                self._display.set_members(members)
                self._membership_received = True
                for member in members:
                    for capability in member["capabilities"]:
                        kind = {"top_of_book": "quotes", "watchlist_last": "bars"}[capability]
                        demand = DashboardDemand(member["instrument_id"], kind)
                        self._demands[demand.demand_id] = demand
                        self.publish_signal(DASHBOARD_DEMAND_SIGNAL, demand.to_signal_value())

            elif signal.name == ACQUISITION_STREAM_SIGNAL:
                event = AcquisitionStreamEvent.from_signal_value(signal.value)
                ids = {*event.consumer_ids, event.demand_id}
                for identity in ids.intersection(self._demands):
                    demand = self._demands[identity]
                    kind = f"chart:{demand.timeframe}" if demand.timeframe else event.feed_kind
                    self._display.feed_state(event.instrument_id, kind, event.state)
            elif signal.name == HISTORICAL_EXECUTION_SIGNAL:
                event = HistoricalExecutionEventMessage.from_signal_value(signal.value)
                for consumer_id in event.consumer_ids:
                    pending = self._page_requests.get(consumer_id)
                    if pending is not None:
                        command, started, _ = pending
                        if (
                            event.instrument_id == command.instrument_id
                            and event.start_ns == command.start * 1_000_000_000
                            and event.end_ns == command.end * 1_000_000_000 - 1
                            and event.selector == command.selector
                        ):
                            self._page_requests[consumer_id] = (command, started, True)
                            if event.state in {"FAILED", "REJECTED", "EXPIRED", "CANCELED"}:
                                self._finish_page(command, event.state)
        except (ValueError, KeyError):
            self.log.error("DASHBOARD_EVENT_REJECTED | invalid display event")

    def on_quote(self, quote) -> None:  # noqa: ANN001
        if self._active:
            self._display.observe_quote(quote)

    def on_bar(self, bar) -> None:  # noqa: ANN001
        if self._active:
            selector = str(bar.bar_type).removeprefix(f"{bar.bar_type.instrument_id}-")
            if selector != "5-SECOND-LAST-EXTERNAL" and not any(
                d.instrument_id == str(bar.bar_type.instrument_id) and d.selector == selector
                for d in self._demands.values()
            ):
                return
            self._display.observe_bar(bar)

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if self._active and isinstance(payload, DashboardHistoryPage):
            consumer_id = "DASHBOARD-HISTORY:" + payload.request_id
            pending = self._page_requests.get(consumer_id)
            if pending is not None:
                command = pending[0]
                if (
                    payload.source == "DATA-ACQUISITION"
                    and payload.schema_version == 1
                    and payload.instrument_id == command.instrument_id
                    and payload.timeframe == command.timeframe
                    and (payload.start, payload.end) == (command.start, command.end)
                ):
                    self._page_requests.pop(consumer_id)
                    self._server.finish_history(asdict(payload))

    def _finish_page(self, command: DashboardHistoryRequest, status: str) -> None:
        self._page_requests.pop(command.consumer_id, None)
        self._server.finish_history({**asdict(command), "status": status, "candles": []})

    def _retry_pages(self) -> None:
        now = self.clock.timestamp_ns()
        for command, started, acknowledged in tuple(self._page_requests.values()):
            if now - started >= self._policy.history_request_timeout_seconds * 1_000_000_000:
                self._finish_page(command, "EXPIRED")
            elif not acknowledged:
                self.publish_signal(
                    HISTORICAL_DEPENDENCY_DEMAND_SIGNAL, command.demand().to_signal_value()
                )

    def _accept_pages(self) -> None:
        for command in self._server.take_history_requests():
            item = self._display.instruments.get(command.instrument_id)
            if (
                item is None
                or "watchlist_last" not in item.capabilities
                or command.demand().maximum_observations > self._policy.history_page_candles
                or command.end * 1_000_000_000 > self.clock.timestamp_ns()
                or len(self._page_requests) >= self._policy.maximum_history_requests
            ):
                self._finish_page(command, "REJECTED")
                continue
            self._page_requests[command.consumer_id] = (command, self.clock.timestamp_ns(), False)

    def _accept_chart_selections(self) -> None:
        selections = self._server.take_chart_selections()
        if selections is None:
            return
        desired = {}
        for instrument, timeframe in selections:
            item = self._display.instruments.get(instrument)
            if item is not None and "watchlist_last" in item.capabilities:
                demand = DashboardDemand(instrument, "bars", timeframe=timeframe)
                desired[demand.demand_id] = demand
        for identity, demand in tuple(self._demands.items()):
            if demand.timeframe is not None and identity not in desired:
                self.publish_signal(
                    DASHBOARD_DEMAND_SIGNAL, replace(demand, action="RELEASE").to_signal_value()
                )
                del self._demands[identity]
                self._display.clear_chart(demand.instrument_id, demand.timeframe)
        for identity, demand in desired.items():
            if identity not in self._demands:
                self._demands[identity] = demand
                self.publish_signal(DASHBOARD_DEMAND_SIGNAL, demand.to_signal_value())

    def _publish(self, _event) -> None:  # noqa: ANN001
        if self._active:
            self._accept_chart_selections()
            self._accept_pages()
        if (
            self._active
            and not self._ready_announced
            and self._server.ready.is_set()
            and not self._server.stopping.is_set()
            and self._server.failure is None
        ):
            ready = DashboardReadyEvent(server_epoch=self._server.epoch, port=self._policy.port)
            self.publish_signal(DASHBOARD_READY_SIGNAL, ready.to_signal_value())
            self._ready_announced = True
            self.log.info(f"DASHBOARD_READY | url={ready.url}")
        if self._server.failure and not self._server_failure_reported:
            self._server_failure_reported = True
            self.log.error(f"DASHBOARD_SERVER_FAILED | error={self._server.failure}")
        if self._display.sequence != self._published_sequence:
            self._server.publish(self._display.snapshot())
            self._published_sequence = self._display.sequence

    def on_stop(self) -> None:
        if self._active:
            self._active = False
            for timer in ("dashboard-projection", "dashboard-membership"):
                if timer in self.clock.timer_names():
                    self.clock.cancel_timer(timer)
            for demand in self._demands.values():
                self.publish_signal(
                    DASHBOARD_DEMAND_SIGNAL,
                    replace(demand, action="RELEASE").to_signal_value(),
                )
            self.unsubscribe_signal(WATCHLIST_MEMBERSHIP_SIGNAL)
            self.unsubscribe_signal(ACQUISITION_STREAM_SIGNAL)
            self.unsubscribe_signal(HISTORICAL_EXECUTION_SIGNAL)
            self.unsubscribe_data(self._page_type)
            for command, _, _ in tuple(self._page_requests.values()):
                self._finish_page(command, "CANCELED")
        if not self._server.stop():
            self.log.error("DASHBOARD_STOP_INCOMPLETE | server thread exceeded deadline")

    def on_dispose(self) -> None:
        self.on_stop()

    def on_fault(self) -> None:
        self.on_stop()
