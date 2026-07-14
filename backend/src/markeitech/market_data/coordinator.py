from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

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
    RECOVERING = "recovering"
    SUBSCRIBING = "subscribing"
    LIVE = "live"
    FAILED = "failed"


@dataclass(frozen=True)
class WarmupSnapshot:
    active_instrument_id: str
    requested_bar_types: tuple[str, ...]
    data_by_bar_type: Mapping[str, tuple[Any, ...]]


WarmupReadyHandler = Callable[[WarmupSnapshot], None]
WarmupRetryHandler = Callable[[LiveNodeAction, int, int], None]


class StartupRecoveryHook(Protocol):
    def prepare(self) -> tuple[LiveNodeAction, ...]: ...

    def finish(self) -> None: ...


class WarmupCoordinator:
    def __init__(
        self,
        action_plan: LiveNodeActionPlan,
        target: LiveNodeActionTarget,
        *,
        on_warmup_ready: WarmupReadyHandler,
        startup_recovery: StartupRecoveryHook | None = None,
        max_warmup_attempts: int = 3,
        on_warmup_retry: WarmupRetryHandler | None = None,
    ) -> None:
        if max_warmup_attempts < 1:
            raise ValueError("maximum warmup attempts must be positive")
        self._action_plan = action_plan
        self._target = target
        self._on_warmup_ready = on_warmup_ready
        self._startup_recovery = startup_recovery
        self._max_warmup_attempts = max_warmup_attempts
        self._on_warmup_retry = on_warmup_retry
        self._state = WarmupState.IDLE
        self._historical_data: dict[str, list[Any]] = defaultdict(list)
        self._warmup_actions: deque[LiveNodeAction] = deque()
        self._recovery_actions: deque[LiveNodeAction] = deque()
        self._warmup_attempts: dict[tuple[str, str], int] = defaultdict(int)
        self._active_warmup_attempt: tuple[tuple[str, str], int] | None = None

    @property
    def state(self) -> WarmupState:
        return self._state

    def start(self) -> None:
        if self._state != WarmupState.IDLE:
            raise RuntimeError(f"warmup coordinator cannot start from {self._state}")

        warmups = self._actions_for_phase(LiveNodeActionPhase.WARMUP)
        self._warmup_actions.extend(warmups)
        self._state = WarmupState.REQUESTING

        try:
            self._execute_next_warmup()
        except Exception:
            self._state = WarmupState.FAILED
            raise

    def record_historical_data(self, *, bar_type: str, data: Any) -> None:
        if self._state not in {
            WarmupState.REQUESTING,
            WarmupState.RECOVERING,
            WarmupState.ANALYZING,
        }:
            return
        self._historical_data[bar_type].append(data)

    def _execute_next_warmup(self) -> None:
        if self._state != WarmupState.REQUESTING:
            return
        if not self._warmup_actions:
            self._active_warmup_attempt = None
            self._start_recovery()
            return

        action = self._warmup_actions.popleft()
        key = _warmup_key(action)
        self._warmup_attempts[key] += 1
        attempt = self._warmup_attempts[key]
        baseline = len(self._historical_data[action.bar_type or ""])
        self._active_warmup_attempt = key, attempt
        execute_livenode_action(
            action,
            self._target,
            callback=lambda _request_id: self._complete(action, attempt, baseline),
        )

    def _complete(self, action: LiveNodeAction, attempt: int, baseline: int) -> None:
        if self._state != WarmupState.REQUESTING:
            return
        key = _warmup_key(action)
        if self._active_warmup_attempt != (key, attempt):
            return
        bar_type = action.bar_type or ""
        if len(self._historical_data[bar_type]) <= baseline:
            if attempt >= self._max_warmup_attempts:
                self._state = WarmupState.FAILED
                raise RuntimeError(
                    f"historical warmup returned no data for {bar_type} after "
                    f"{attempt} attempts"
                )
            self._warmup_actions.appendleft(action)
            if self._on_warmup_retry is not None:
                self._on_warmup_retry(action, attempt + 1, self._max_warmup_attempts)
        self._active_warmup_attempt = None
        self._execute_next_warmup()

    def _start_recovery(self) -> None:
        if self._state != WarmupState.REQUESTING:
            return
        if self._startup_recovery is None:
            self._finish_warmup()
            return
        try:
            self._recovery_actions.extend(self._startup_recovery.prepare())
            if not self._recovery_actions:
                self._startup_recovery.finish()
                self._finish_warmup()
                return
            self._state = WarmupState.RECOVERING
            self._execute_next_recovery()
        except Exception:
            self._state = WarmupState.FAILED
            raise

    def _execute_next_recovery(self) -> None:
        if not self._recovery_actions:
            try:
                if self._startup_recovery is not None:
                    self._startup_recovery.finish()
                self._state = WarmupState.REQUESTING
                self._finish_warmup()
            except Exception:
                self._state = WarmupState.FAILED
                raise
            return
        action = self._recovery_actions.popleft()
        execute_livenode_action(
            action,
            self._target,
            callback=lambda _request_id: self._execute_next_recovery(),
        )

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
