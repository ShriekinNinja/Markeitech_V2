from __future__ import annotations

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, CustomData, DataType

from markeitech.acquisition import (
    HISTORICAL_BATCH_TYPE_NAME,
    HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
    HISTORICAL_READINESS_SIGNAL,
    HistoricalBatch,
    HistoricalDependencyDemandEvent,
    HistoricalReadinessEvent,
)

_DEMAND_ALERT = "historical-dependency-probe-demand"
_DEMAND_DELAY_NS = 1_000_000


class HistoricalDependencyProbeActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_id: str,
        selector: str,
        window: str,
        minimum_observations: int,
        maximum_observations: int,
        priority: int,
        actor_id: str | ActorId = "HISTORICAL-DEPENDENCY-PROBE",
    ) -> HistoricalDependencyProbeActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.instrument_id = instrument_id
        obj.selector = selector
        obj.window = window
        obj.minimum_observations = minimum_observations
        obj.maximum_observations = maximum_observations
        obj.priority = priority
        return obj


class HistoricalDependencyProbeActor(DataActor):
    """Config-disabled acceptance consumer for the Stage 9B historical path."""

    def __init__(self, config: HistoricalDependencyProbeActorConfig) -> None:
        super().__init__(config)
        self._instrument_id = config.instrument_id
        self._selector = config.selector
        self._window = config.window
        self._minimum_observations = config.minimum_observations
        self._maximum_observations = config.maximum_observations
        self._priority = config.priority
        self._consumer_id = str(self.actor_id)
        self._demand_id = f"probe:{self._consumer_id}:{self._instrument_id}:{self._selector}"
        self._batch_type = DataType(HISTORICAL_BATCH_TYPE_NAME)
        self._batches = 0
        self._observations = 0
        self._readiness: str | None = None

    def on_start(self) -> None:
        self.subscribe_signal(HISTORICAL_READINESS_SIGNAL)
        self.subscribe_data(self._batch_type)
        self.clock.set_time_alert_ns(
            _DEMAND_ALERT,
            self.clock.timestamp_ns() + _DEMAND_DELAY_NS,
            callback=self._publish_demand,
        )

    def on_signal(self, signal: Signal) -> None:
        if signal.name != HISTORICAL_READINESS_SIGNAL:
            return
        try:
            event = HistoricalReadinessEvent.from_signal_value(signal.value)
        except ValueError:
            return
        if event.consumer_id != self._consumer_id:
            return
        self._readiness = event.state
        self.log.info(
            f"HISTORICAL_PROBE_READINESS | state={event.state}"
            f" | request_id={event.request_id}"
            f" | observations={event.observed_count}/{event.minimum_observations}",
        )

    def on_data(self, data) -> None:  # noqa: ANN001
        payload = data.data if isinstance(data, CustomData) else data
        if not isinstance(payload, HistoricalBatch):
            return
        if not any(
            dependency.consumer_id == self._consumer_id
            for dependency in payload.request.dependencies
        ):
            return
        self._batches += 1
        self._observations += payload.observation_count
        self.log.info(
            "HISTORICAL_PROBE_BATCH"
            f" | request_id={payload.request.request_id}"
            f" | instrument_id={payload.request.instrument_id}"
            f" | selector={payload.request.selector}"
            f" | observations={payload.observation_count}",
        )

    def on_stop(self) -> None:
        if _DEMAND_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_DEMAND_ALERT)
        self.unsubscribe_signal(HISTORICAL_READINESS_SIGNAL)
        self.unsubscribe_data(self._batch_type)
        self.log.info(
            "HISTORICAL_PROBE_SUMMARY"
            f" | batches={self._batches} | observations={self._observations}"
            f" | readiness={self._readiness or 'PENDING'}",
        )

    def _publish_demand(self, _event) -> None:  # noqa: ANN001
        demand = HistoricalDependencyDemandEvent(
            demand_id=self._demand_id,
            consumer_id=self._consumer_id,
            capability_id="historical.acceptance_probe",
            capability_version=1,
            instrument_id=self._instrument_id,
            selector=self._selector,
            window=self._window,
            minimum_observations=self._minimum_observations,
            maximum_observations=self._maximum_observations,
            priority=self._priority,
            purpose="Stage 9B end-to-end historical dependency acceptance",
            as_of_ns=self.clock.timestamp_ns(),
        )
        self.publish_signal(HISTORICAL_DEPENDENCY_DEMAND_SIGNAL, demand.to_signal_value())
        self.log.info(
            f"HISTORICAL_PROBE_DEMAND | demand_id={demand.demand_id}"
            f" | instrument_id={demand.instrument_id} | selector={demand.selector}"
            f" | observations={demand.minimum_observations}-{demand.maximum_observations}",
        )
