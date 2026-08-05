from __future__ import annotations

import json

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, InstrumentId

from markeitech.system.control import SystemHealthState, SystemHealthStateMachine
from markeitech.system.messages import SYSTEM_HEALTH_SIGNAL
from markeitech.system.persistence import PERSISTENCE_FAILURE_SIGNAL

_INITIAL_EVALUATION_ALERT = "system-control-initial-evaluation"
_INITIAL_EVALUATION_DELAY_NS = 1_000_000


class SystemControlActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_ids: list[str],
        operational_persistence_ready: bool = False,
        actor_id: str | ActorId = "SYSTEM-CONTROL",
    ) -> SystemControlActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.instrument_ids = tuple(instrument_ids)
        obj.operational_persistence_ready = operational_persistence_ready
        return obj


class SystemControlActor(DataActor):
    def __init__(self, config: SystemControlActorConfig) -> None:
        super().__init__(config)
        self._expected = {InstrumentId.from_str(value) for value in config.instrument_ids}
        self._available: set[InstrumentId] = set()
        self._health = SystemHealthStateMachine()
        self._evaluation_started = False
        self._persistence_ready = config.operational_persistence_ready

    def on_start(self) -> None:
        self.subscribe_signal(PERSISTENCE_FAILURE_SIGNAL)
        for instrument_id in sorted(self._expected, key=str):
            instrument = self.cache.instrument(instrument_id)
            if instrument is not None:
                self._available.add(instrument_id)
            else:
                self.request_instrument(instrument_id)
        self.clock.set_time_alert_ns(
            _INITIAL_EVALUATION_ALERT,
            self.clock.timestamp_ns() + _INITIAL_EVALUATION_DELAY_NS,
            callback=self._begin_evaluation,
        )

    def on_instrument(self, instrument) -> None:  # noqa: ANN001
        instrument_id = instrument.id
        if instrument_id in self._expected:
            self._available.add(instrument_id)
            self.log.info(f"INSTRUMENT_READY | instrument_id={instrument_id}")
            self._publish_ready_if_complete()

    def on_stop(self) -> None:
        self._publish_transition(
            SystemHealthState.STOPPING,
            reason="system control actor is stopping",
            evidence=self._instrument_evidence(),
        )
        self.unsubscribe_signal(PERSISTENCE_FAILURE_SIGNAL)

    def on_signal(self, signal: Signal) -> None:
        if signal.name != PERSISTENCE_FAILURE_SIGNAL:
            return
        try:
            failure = json.loads(signal.value)
            reason = str(failure["reason"])
            error_code = str(failure["error_code"])
        except (KeyError, TypeError, json.JSONDecodeError):
            reason = "invalid persistence failure event"
            error_code = "invalid_payload"
        startup_failure = self._health.state in {None, SystemHealthState.STARTING}
        self._publish_transition(
            SystemHealthState.FAILED if startup_failure else SystemHealthState.DEGRADED,
            reason=(
                "operational persistence failed during startup"
                if startup_failure
                else "operational persistence is unavailable"
            ),
            evidence={
                **self._instrument_evidence(),
                "persistence_reason": reason,
                "persistence_error": error_code,
            },
        )

    def on_fault(self) -> None:
        self._publish_transition(
            SystemHealthState.FAILED,
            reason="system control actor entered fault state",
            evidence=self._instrument_evidence(),
        )

    def _begin_evaluation(self, _event) -> None:  # noqa: ANN001
        if self._evaluation_started:
            return
        self._evaluation_started = True
        self._publish_transition(
            SystemHealthState.STARTING,
            reason="evaluating runtime prerequisites",
            evidence=self._instrument_evidence(),
        )
        self._publish_ready_if_complete()

    def _publish_ready_if_complete(self) -> None:
        if (
            not self._evaluation_started
            or not self._persistence_ready
            or self._available != self._expected
        ):
            return
        self._publish_transition(
            SystemHealthState.READY,
            reason="configured instrument definitions are available",
            evidence=self._instrument_evidence(),
        )

    def _publish_transition(
        self,
        target: SystemHealthState,
        *,
        reason: str,
        evidence: dict[str, str | int],
    ) -> None:
        event = self._health.transition(
            target,
            reason=reason,
            source=str(self.actor_id),
            evidence=evidence,
        )
        if event is None:
            return
        self.publish_signal(SYSTEM_HEALTH_SIGNAL, event.to_signal_value())
        self.log.info(
            f"SYSTEM_HEALTH | state={event.state} | reason={event.reason}"
            f" | available={len(self._available)}/{len(self._expected)}",
        )

    def _instrument_evidence(self) -> dict[str, str | int]:
        available = sorted(str(value) for value in self._available)
        expected = sorted(str(value) for value in self._expected)
        return {
            "available_instrument_count": len(available),
            "available_instruments": ",".join(available),
            "expected_instrument_count": len(expected),
            "expected_instruments": ",".join(expected),
            "operational_persistence_ready": self._persistence_ready,
        }
