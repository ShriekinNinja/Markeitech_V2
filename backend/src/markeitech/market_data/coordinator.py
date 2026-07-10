from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from markeitech.market_data.actions import (
    LiveNodeAction,
    LiveNodeActionPhase,
    LiveNodeActionPlan,
    LiveNodeActionTarget,
    execute_livenode_action,
)


class WarmupState(StrEnum):
    IDLE = "idle"
    REQUESTING = "requesting"
    ANALYZING = "analyzing"
    SUBSCRIBING = "subscribing"
    LIVE = "live"
    FAILED = "failed"


@dataclass(frozen=True)
class WarmupSnapshot:
    active_instrument_id: str
    requested_bar_types: tuple[str, ...]
    data_by_bar_type: Mapping[str, tuple[Any, ...]]


WarmupReadyHandler = Callable[[WarmupSnapshot], None]


class WarmupCoordinator:
    def __init__(
        self,
        action_plan: LiveNodeActionPlan,
        target: LiveNodeActionTarget,
        *,
        on_warmup_ready: WarmupReadyHandler,
    ) -> None:
        self._action_plan = action_plan
        self._target = target
        self._on_warmup_ready = on_warmup_ready
        self._state = WarmupState.IDLE
        self._pending: set[tuple[str, str]] = set()
        self._historical_data: dict[str, list[Any]] = defaultdict(list)

    @property
    def state(self) -> WarmupState:
        return self._state

    def start(self) -> None:
        if self._state != WarmupState.IDLE:
            raise RuntimeError(f"warmup coordinator cannot start from {self._state}")

        warmups = self._actions_for_phase(LiveNodeActionPhase.WARMUP)
        self._pending = {_warmup_key(action) for action in warmups}
        self._state = WarmupState.REQUESTING

        try:
            for action in warmups:
                execute_livenode_action(
                    action,
                    self._target,
                    callback=lambda _request_id, completed=action: self._complete(completed),
                )
            if not self._pending:
                self._finish_warmup()
        except Exception:
            self._state = WarmupState.FAILED
            raise

    def record_historical_data(self, *, bar_type: str, data: Any) -> None:
        if self._state not in {WarmupState.REQUESTING, WarmupState.ANALYZING}:
            return
        self._historical_data[bar_type].append(data)

    def _complete(self, action: LiveNodeAction) -> None:
        if self._state != WarmupState.REQUESTING:
            return
        self._pending.discard(_warmup_key(action))
        if not self._pending:
            self._finish_warmup()

    def _finish_warmup(self) -> None:
        if self._state != WarmupState.REQUESTING:
            return

        try:
            self._state = WarmupState.ANALYZING
            self._on_warmup_ready(self._snapshot())
            self._state = WarmupState.SUBSCRIBING
            for action in self._actions_for_phase(LiveNodeActionPhase.LIVE_SUBSCRIPTION):
                execute_livenode_action(action, self._target)
            self._state = WarmupState.LIVE
        except Exception:
            self._state = WarmupState.FAILED
            raise

    def _snapshot(self) -> WarmupSnapshot:
        requested_bar_types = tuple(
            action.bar_type
            for action in self._actions_for_phase(LiveNodeActionPhase.WARMUP)
            if action.bar_type is not None
        )
        return WarmupSnapshot(
            active_instrument_id=self._action_plan.active_instrument_id,
            requested_bar_types=requested_bar_types,
            data_by_bar_type={
                bar_type: tuple(values) for bar_type, values in self._historical_data.items()
            },
        )

    def _actions_for_phase(self, phase: LiveNodeActionPhase) -> tuple[LiveNodeAction, ...]:
        return tuple(action for action in self._action_plan.actions if action.phase == phase)


def require_historical_coverage(snapshot: WarmupSnapshot) -> None:
    missing = [
        bar_type
        for bar_type in snapshot.requested_bar_types
        if not snapshot.data_by_bar_type.get(bar_type)
    ]
    if missing:
        raise RuntimeError(
            "historical warmup returned no data for required bar types: " + ", ".join(missing)
        )


def _warmup_key(action: LiveNodeAction) -> tuple[str, str]:
    if action.bar_type is None:
        raise RuntimeError("warmup action missing bar_type")
    return action.instrument_id, action.bar_type
