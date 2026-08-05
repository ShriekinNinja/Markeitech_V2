from __future__ import annotations

from nautilus_trader.common import DataActor, DataActorConfig
from nautilus_trader.model import ActorId, InstrumentId


class ReadinessActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_ids: list[str],
        actor_id: str | ActorId = "SYSTEM-READINESS",
    ) -> ReadinessActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.instrument_ids = tuple(instrument_ids)
        return obj


class ReadinessActor(DataActor):
    def __init__(self, config: ReadinessActorConfig) -> None:
        super().__init__(config)
        self._expected = {InstrumentId.from_str(value) for value in config.instrument_ids}
        self._available: set[InstrumentId] = set()
        self._ready = False

    def on_start(self) -> None:
        self.log.info(
            f"SYSTEM_STARTING | awaiting_instruments={len(self._expected)}",
        )
        for instrument_id in sorted(self._expected, key=str):
            instrument = self.cache.instrument(instrument_id)
            if instrument is not None:
                self._available.add(instrument_id)
            else:
                self.request_instrument(instrument_id)
        self._publish_ready_if_complete()

    def on_instrument(self, instrument) -> None:  # noqa: ANN001
        instrument_id = instrument.id
        if instrument_id in self._expected:
            self._available.add(instrument_id)
            self.log.info(f"INSTRUMENT_READY | instrument_id={instrument_id}")
            self._publish_ready_if_complete()

    def on_stop(self) -> None:
        self.log.info("SYSTEM_STOPPED")

    def _publish_ready_if_complete(self) -> None:
        if self._ready or self._available != self._expected:
            return
        self._ready = True
        instrument_ids = sorted(str(value) for value in self._available)
        self.publish_signal(
            "system.ready",
            {"instruments": instrument_ids},
        )
        self.log.info(f"SYSTEM_READY | instruments={','.join(instrument_ids)}")
