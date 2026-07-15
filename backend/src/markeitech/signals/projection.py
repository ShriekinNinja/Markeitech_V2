from __future__ import annotations

import time
from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from threading import Condition, Thread

from markeitech.domain.base import require_utc
from markeitech.signals.contracts import (
    SignalEvidenceStage,
    SignalSnapshot,
    SignalStatus,
    SignalTransitionEvent,
)


class SignalLifecycleProjectionKind(StrEnum):
    RESTORED = "restored"
    TRANSITION = "transition"


@dataclass(frozen=True)
class SignalLifecycleProjection:
    kind: SignalLifecycleProjectionKind
    occurred_ts: datetime
    signal: SignalSnapshot
    transition_id: str | None
    from_status: SignalStatus | None
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        require_utc(self.occurred_ts)
        if not self.reason_codes:
            raise ValueError("signal lifecycle projection requires reason codes")
        if self.kind == SignalLifecycleProjectionKind.RESTORED:
            if self.transition_id is not None or self.from_status is not None:
                raise ValueError("restored projection cannot carry transition identity")
            if self.signal.status not in {SignalStatus.ARMED, SignalStatus.TRIGGERED}:
                raise ValueError("only open signal state can be projected as restored")
        elif self.transition_id is None or self.from_status is None:
            raise ValueError("transition projection requires prior and transition identity")

    @classmethod
    def restored(cls, signal: SignalSnapshot, occurred_ts: datetime) -> SignalLifecycleProjection:
        return cls(
            kind=SignalLifecycleProjectionKind.RESTORED,
            occurred_ts=occurred_ts,
            signal=signal,
            transition_id=None,
            from_status=None,
            reason_codes=("verified_open_signal_restored",),
        )

    @classmethod
    def transitioned(cls, event: SignalTransitionEvent) -> SignalLifecycleProjection:
        return cls(
            kind=SignalLifecycleProjectionKind.TRANSITION,
            occurred_ts=event.occurred_ts,
            signal=event.current,
            transition_id=event.transition_id,
            from_status=event.from_status,
            reason_codes=event.reason_codes,
        )

    @property
    def dedupe_key(self) -> str:
        if self.transition_id is not None:
            return f"transition:{self.transition_id}"
        return f"restored:{self.signal.signal_id}:{self.signal.content_hash}"


class SignalRuntimeProjectionKind(StrEnum):
    STARTED = "started"
    HEARTBEAT = "heartbeat"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass(frozen=True)
class SignalRuntimeProjection:
    kind: SignalRuntimeProjectionKind
    occurred_ts: datetime
    status: str
    startup_watermark: datetime | None
    restored_open_signal_count: int
    processed_revision_count: int
    stale_evaluation_count: int
    evaluation_count: int
    lifecycle_write_count: int
    open_signal_count: int
    projection_rejected_count: int
    projection_callback_error_count: int

    def __post_init__(self) -> None:
        require_utc(self.occurred_ts)
        if self.startup_watermark is not None:
            require_utc(self.startup_watermark)
        if not self.status:
            raise ValueError("signal runtime projection requires status")
        counters = (
            self.restored_open_signal_count,
            self.processed_revision_count,
            self.stale_evaluation_count,
            self.evaluation_count,
            self.lifecycle_write_count,
            self.open_signal_count,
            self.projection_rejected_count,
            self.projection_callback_error_count,
        )
        if any(value < 0 for value in counters):
            raise ValueError("signal runtime projection counters cannot be negative")


type SignalOperatorProjection = SignalLifecycleProjection | SignalRuntimeProjection


class SignalProjectionWriterStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass(frozen=True)
class SignalProjectionWriterSnapshot:
    status: SignalProjectionWriterStatus
    pending_count: int
    accepted_count: int
    rendered_count: int
    duplicate_count: int
    rejected_count: int
    failed_count: int
    last_error: str | None


class BoundedSignalProjectionWriter:
    """Isolates sparse operator presentation from the signal runtime thread."""

    def __init__(
        self,
        sink: Callable[[str], None],
        role_resolver: Callable[[str], str],
        *,
        queue_size: int,
        dedupe_size: int,
        poll_seconds: float = 0.1,
    ) -> None:
        if queue_size < 1:
            raise ValueError("signal projection queue size must be positive")
        if dedupe_size < queue_size:
            raise ValueError("signal projection dedupe size cannot be smaller than queue")
        if poll_seconds <= 0:
            raise ValueError("signal projection poll interval must be positive")
        self._sink = sink
        self._role_resolver = role_resolver
        self._queue_size = queue_size
        self._dedupe_size = dedupe_size
        self._poll_seconds = poll_seconds
        self._condition = Condition()
        self._queue: deque[SignalOperatorProjection] = deque()
        self._dedupe: OrderedDict[str, None] = OrderedDict()
        self._status = SignalProjectionWriterStatus.CREATED
        self._accepted_count = 0
        self._rendered_count = 0
        self._duplicate_count = 0
        self._rejected_count = 0
        self._failed_count = 0
        self._last_error: str | None = None
        self._thread: Thread | None = None

    @property
    def snapshot(self) -> SignalProjectionWriterSnapshot:
        with self._condition:
            return SignalProjectionWriterSnapshot(
                status=self._status,
                pending_count=len(self._queue),
                accepted_count=self._accepted_count,
                rendered_count=self._rendered_count,
                duplicate_count=self._duplicate_count,
                rejected_count=self._rejected_count,
                failed_count=self._failed_count,
                last_error=self._last_error,
            )

    def start(self) -> None:
        with self._condition:
            if self._status != SignalProjectionWriterStatus.CREATED:
                raise RuntimeError("signal projection writer can only start once")
            self._status = SignalProjectionWriterStatus.RUNNING
            self._thread = Thread(
                target=self._run,
                name="markeitech-signal-projection",
                daemon=True,
            )
            self._thread.start()

    def submit(self, projection: SignalOperatorProjection) -> bool:
        with self._condition:
            if self._status != SignalProjectionWriterStatus.RUNNING:
                self._rejected_count += 1
                return False
            dedupe_key = _projection_dedupe_key(projection)
            if dedupe_key is not None and dedupe_key in self._dedupe:
                self._dedupe.move_to_end(dedupe_key)
                self._duplicate_count += 1
                return True
            if len(self._queue) >= self._queue_size:
                self._rejected_count += 1
                return False
            if dedupe_key is not None:
                self._dedupe[dedupe_key] = None
                while len(self._dedupe) > self._dedupe_size:
                    self._dedupe.popitem(last=False)
            self._queue.append(projection)
            self._accepted_count += 1
            self._condition.notify_all()
            return True

    def stop(self, timeout: float) -> bool:
        if timeout <= 0:
            raise ValueError("signal projection stop timeout must be positive")
        with self._condition:
            if self._status == SignalProjectionWriterStatus.STOPPED:
                return True
            if self._status == SignalProjectionWriterStatus.CREATED:
                self._status = SignalProjectionWriterStatus.STOPPED
                return True
            self._status = SignalProjectionWriterStatus.STOPPING
            thread = self._thread
            self._condition.notify_all()
        if thread is not None:
            thread.join(timeout)
        return thread is None or not thread.is_alive()

    def _run(self) -> None:
        while True:
            with self._condition:
                while not self._queue and self._status == SignalProjectionWriterStatus.RUNNING:
                    self._condition.wait(self._poll_seconds)
                if not self._queue and self._status == SignalProjectionWriterStatus.STOPPING:
                    self._status = SignalProjectionWriterStatus.STOPPED
                    self._condition.notify_all()
                    return
                projection = self._queue.popleft()
            try:
                line = format_signal_operator_projection(
                    projection,
                    role_resolver=self._role_resolver,
                )
                if isinstance(projection, SignalRuntimeProjection):
                    line += f" | render_errors={self._failed_count}"
                self._sink(line)
            except Exception as exc:
                with self._condition:
                    self._failed_count += 1
                    self._last_error = f"{type(exc).__name__}: {exc}"
                    self._condition.notify_all()
                continue
            with self._condition:
                self._rendered_count += 1
                self._condition.notify_all()

    def wait_until_empty(self, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        with self._condition:
            while self._queue:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return True


def format_signal_operator_projection(
    projection: SignalOperatorProjection,
    *,
    role_resolver: Callable[[str], str],
) -> str:
    if isinstance(projection, SignalRuntimeProjection):
        watermark = (
            "n/a"
            if projection.startup_watermark is None
            else projection.startup_watermark.isoformat()
        )
        return (
            f"SIGNAL_RUNTIME | event={projection.kind.value.upper()} "
            f"| status={projection.status.upper()} | watermark={watermark} "
            f"| restored={projection.restored_open_signal_count} "
            f"| revisions={projection.processed_revision_count} "
            f"| stale={projection.stale_evaluation_count} "
            f"| evaluations={projection.evaluation_count} "
            f"| writes={projection.lifecycle_write_count} "
            f"| open={projection.open_signal_count} "
            f"| projection_rejected={projection.projection_rejected_count} "
            f"| projection_errors={projection.projection_callback_error_count}"
        )

    signal = projection.signal
    token = (
        "SIGNAL_RESTORED"
        if projection.kind == SignalLifecycleProjectionKind.RESTORED
        else f"SIGNAL_{signal.status.value.upper()}"
    )
    transition = "n/a" if projection.transition_id is None else projection.transition_id[:12]
    previous = "n/a" if projection.from_status is None else projection.from_status.value
    evidence = _evidence_summary(signal)
    locations = _location_summary(signal)
    reasons = ",".join(projection.reason_codes)
    role = role_resolver(signal.instrument_id).upper()
    return (
        f"{token} | role={role} | {signal.instrument_id} "
        f"| definition={signal.definition_id} | direction={signal.direction.value.upper()} "
        f"| from={previous.upper()} | location={locations} | evidence={evidence} "
        f"| reason={reasons} | as_of={projection.occurred_ts.isoformat()} "
        f"| signal={signal.signal_id[:12]} | transition={transition}"
    )


def _projection_dedupe_key(projection: SignalOperatorProjection) -> str | None:
    if isinstance(projection, SignalLifecycleProjection):
        return projection.dedupe_key
    return None


def _evidence_summary(signal: SignalSnapshot) -> str:
    counts = {stage: 0 for stage in SignalEvidenceStage}
    fidelities: set[str] = set()
    for evidence in signal.evidence:
        counts[evidence.stage] += 1
        fidelities.add(evidence.fidelity.value)
    stages = ",".join(
        f"{stage.value[0].upper()}:{counts[stage]}"
        for stage in SignalEvidenceStage
        if counts[stage]
    )
    fidelity = "+".join(sorted(fidelities)) or "n/a"
    confirmation_methods = sorted(
        {
            item.source.rsplit(":", 1)[-1]
            for item in signal.evidence
            if item.stage == SignalEvidenceStage.AGGRESSION and ":" in item.source
        }
    )
    confirmation = (
        "" if not confirmation_methods else f";confirmation={'+'.join(confirmation_methods)}"
    )
    return f"{stages or 'none'};fidelity={fidelity}{confirmation}"


def _location_summary(signal: SignalSnapshot) -> str:
    if not signal.location_matches:
        return "n/a"
    values: list[str] = []
    seen: set[str] = set()
    for match in sorted(signal.location_matches, key=lambda item: item.zone.zone_id):
        zone = match.zone
        if zone.zone_id in seen:
            continue
        seen.add(zone.zone_id)
        values.append(
            f"{zone.zone_kind.value}@{zone.timeframe.value}:"
            f"{_decimal(zone.lower_price)}-{_decimal(zone.upper_price)}"
        )
    visible = values[:3]
    suffix = "" if len(values) <= 3 else f",+{len(values) - 3}"
    return ",".join(visible) + suffix


def _decimal(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered
