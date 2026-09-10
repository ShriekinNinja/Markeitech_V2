from __future__ import annotations

from dataclasses import replace

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId

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

    def on_start(self) -> None:
        self._active = True
        if self._membership_received:
            self._display.set_members([])
        self.subscribe_signal(WATCHLIST_MEMBERSHIP_SIGNAL)
        self.subscribe_signal(ACQUISITION_STREAM_SIGNAL)
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
                if ids.intersection(self._demands):
                    self._display.feed_state(event.instrument_id, event.feed_kind, event.state)
        except (ValueError, KeyError):
            self.log.error("DASHBOARD_EVENT_REJECTED | invalid display event")

    def on_quote(self, quote) -> None:  # noqa: ANN001
        if self._active:
            self._display.observe_quote(quote)

    def on_bar(self, bar) -> None:  # noqa: ANN001
        if self._active:
            self._display.observe_bar(bar)

    def _publish(self, _event) -> None:  # noqa: ANN001
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
        if not self._server.stop():
            self.log.error("DASHBOARD_STOP_INCOMPLETE | server thread exceeded deadline")

    def on_dispose(self) -> None:
        self.on_stop()

    def on_fault(self) -> None:
        self.on_stop()
