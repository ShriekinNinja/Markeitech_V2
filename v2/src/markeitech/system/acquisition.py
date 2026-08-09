from __future__ import annotations

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, InstrumentId

from markeitech.system.messages import (
    ACQUISITION_STATUS_REQUEST_SIGNAL,
    ACQUISITION_STATUS_SIGNAL,
    COMPONENT_FAILURE_SIGNAL,
    INSTRUMENTS_READY,
    INSTRUMENTS_RESOLVING,
    AcquisitionStatusEvent,
    AcquisitionStatusRequest,
    ComponentFailureEvent,
)


class InstrumentDefinitionTracker:
    def __init__(self, instrument_ids: list[str] | tuple[str, ...]) -> None:
        expected = {InstrumentId.from_str(value) for value in instrument_ids}
        if not expected:
            raise ValueError("instrument acquisition requires at least one instrument")
        if len(expected) != len(instrument_ids):
            raise ValueError("instrument acquisition does not allow duplicate instruments")
        self._expected = frozenset(expected)
        self._available: set[InstrumentId] = set()
        self._requested: set[InstrumentId] = set()

    @property
    def expected(self) -> frozenset[InstrumentId]:
        return self._expected

    @property
    def available(self) -> frozenset[InstrumentId]:
        return frozenset(self._available)

    @property
    def missing(self) -> frozenset[InstrumentId]:
        return self._expected - self._available

    def observe(self, instrument_id: InstrumentId) -> bool:
        if instrument_id not in self._expected or instrument_id in self._available:
            return False
        self._available.add(instrument_id)
        return True

    def take_unrequested(self) -> tuple[InstrumentId, ...]:
        pending = tuple(sorted(self.missing - self._requested, key=str))
        self._requested.update(pending)
        return pending

    def status(self, source: str) -> AcquisitionStatusEvent:
        complete = not self.missing
        return AcquisitionStatusEvent(
            state=INSTRUMENTS_READY if complete else INSTRUMENTS_RESOLVING,
            reason=(
                "configured instrument definitions are available"
                if complete
                else "resolving configured instrument definitions"
            ),
            source=source,
            expected_instrument_ids=tuple(sorted(str(value) for value in self._expected)),
            available_instrument_ids=tuple(sorted(str(value) for value in self._available)),
        )


class DataAcquisitionActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_ids: list[str],
        actor_id: str | ActorId = "DATA-ACQUISITION",
    ) -> DataAcquisitionActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.instrument_ids = tuple(instrument_ids)
        return obj


class DataAcquisitionActor(DataActor):
    def __init__(self, config: DataAcquisitionActorConfig) -> None:
        super().__init__(config)
        self._tracker = InstrumentDefinitionTracker(config.instrument_ids)
        self._instrument_requests = 0
        self._instruments_received = 0
        self._duplicate_instruments = 0
        self._status_requests = 0
        self._malformed_status_requests = 0
        self._statuses_published = 0
        self._failure_published = False

    def on_start(self) -> None:
        self.subscribe_signal(ACQUISITION_STATUS_REQUEST_SIGNAL)
        for instrument_id in sorted(self._tracker.expected, key=str):
            if self.cache.instrument(instrument_id) is not None:
                self._tracker.observe(instrument_id)
        for instrument_id in self._tracker.take_unrequested():
            self.request_instrument(instrument_id)
            self._instrument_requests += 1
        self._publish_status()

    def on_instrument(self, instrument) -> None:  # noqa: ANN001
        if self._tracker.observe(instrument.id):
            self._instruments_received += 1
            self.log.info(f"INSTRUMENT_ACQUIRED | instrument_id={instrument.id}")
            self._publish_status()
        elif instrument.id in self._tracker.expected:
            self._duplicate_instruments += 1

    def on_signal(self, signal: Signal) -> None:
        if signal.name != ACQUISITION_STATUS_REQUEST_SIGNAL:
            return
        self._status_requests += 1
        try:
            AcquisitionStatusRequest.from_signal_value(signal.value)
        except ValueError as exc:
            self._malformed_status_requests += 1
            self.log.error(
                "ACQUISITION_STATUS_REQUEST_REJECTED"
                f" | reason=invalid_request | error={type(exc).__name__}",
            )
            return
        self._publish_status()

    def on_stop(self) -> None:
        self.unsubscribe_signal(ACQUISITION_STATUS_REQUEST_SIGNAL)
        self.log.info(
            "DATA_ACQUISITION_SUMMARY"
            f" | instrument_requests={self._instrument_requests}"
            f" | instruments_received={self._instruments_received}"
            f" | duplicate_instruments={self._duplicate_instruments}"
            f" | status_requests={self._status_requests}"
            f" | malformed_status_requests={self._malformed_status_requests}"
            f" | statuses_published={self._statuses_published}",
        )

    def on_fault(self) -> None:
        if self._failure_published:
            return
        self._failure_published = True
        self.publish_signal(
            COMPONENT_FAILURE_SIGNAL,
            ComponentFailureEvent(
                component="data_acquisition",
                code="actor_faulted",
                reason="data acquisition actor entered fault state",
                evidence={
                    "available_instrument_count": len(self._tracker.available),
                    "expected_instrument_count": len(self._tracker.expected),
                },
            ).to_signal_value(),
        )

    def _publish_status(self) -> None:
        status = self._tracker.status(str(self.actor_id))
        self.publish_signal(ACQUISITION_STATUS_SIGNAL, status.to_signal_value())
        self._statuses_published += 1
        self.log.info(
            f"ACQUISITION_STATUS | state={status.state}"
            f" | available={len(status.available_instrument_ids)}"
            f"/{len(status.expected_instrument_ids)}",
        )
