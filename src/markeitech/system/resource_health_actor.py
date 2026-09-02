from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId

from markeitech.system.resource_contracts import (
    RUNTIME_RESOURCE_HEALTH_SIGNAL,
    RUNTIME_RESOURCE_SIGNAL,
    RuntimeResourceEvent,
    RuntimeResourceHealthEvent,
)

_STALE_TIMER = "runtime-resource-health-stale"
_SEVERITY = {"NORMAL": 0, "WARNING": 1, "CRITICAL": 2}
_LOWER_IS_WORSE = frozenset(
    {"host_memory_available_percent", "disk_free_bytes", "disk_free_percent"},
)


@dataclass(frozen=True, slots=True)
class ResourceHealthPolicy:
    threshold_version: str
    warning_consecutive_samples: int
    critical_consecutive_samples: int
    recovery_consecutive_samples: int
    notification_cooldown_ms: int
    rss_growth_window_samples: int
    stale_warning_ms: int
    stale_critical_ms: int
    warning: dict[str, int | float]
    critical: dict[str, int | float]


@dataclass(frozen=True, slots=True)
class ResourceAssessment:
    state: str
    reason_codes: tuple[str, ...]
    observations: dict[str, int | float | str | None]
    thresholds: dict[str, int | float]


class RuntimeResourceHealthEvaluator:
    def __init__(self, policy: ResourceHealthPolicy, source: str) -> None:
        self._policy = policy
        self._source = source
        self._state = "NORMAL"
        self._candidate_state: str | None = None
        self._candidate_count = 0
        self._rss_history: deque[int] = deque(maxlen=policy.rss_growth_window_samples)
        self._last_notification_ns: int | None = None

    @property
    def state(self) -> str:
        return self._state

    def evaluate(self, sample: RuntimeResourceEvent) -> RuntimeResourceHealthEvent | None:
        self._rss_history.append(sample.rss_bytes)
        observations = _observations(sample, self._rss_history)
        assessment = _assess(observations, self._policy)
        return self._advance(assessment, sample.observed_ts_ns)

    def evaluate_staleness(
        self,
        observed_ts_ns: int,
        elapsed_ms: int,
    ) -> RuntimeResourceHealthEvent | None:
        if elapsed_ms >= self._policy.stale_critical_ms:
            state = "CRITICAL"
            threshold = self._policy.stale_critical_ms
        elif elapsed_ms >= self._policy.stale_warning_ms:
            state = "WARNING"
            threshold = self._policy.stale_warning_ms
        else:
            return None
        assessment = ResourceAssessment(
            state=state,
            reason_codes=("resource_samples_stale",),
            observations={"sample_age_ms": elapsed_ms},
            thresholds={"sample_age_ms": threshold},
        )
        return self._advance(assessment, observed_ts_ns)

    def _advance(
        self,
        assessment: ResourceAssessment,
        observed_ts_ns: int,
    ) -> RuntimeResourceHealthEvent | None:
        target = assessment.state
        if target == self._state:
            self._candidate_state = None
            self._candidate_count = 0
            return None
        if target != self._candidate_state:
            self._candidate_state = target
            self._candidate_count = 1
        else:
            self._candidate_count += 1
        required = self._required_samples(target)
        if self._candidate_count < required:
            return None

        previous = self._state
        self._state = target
        self._candidate_state = None
        self._candidate_count = 0
        notification_eligible = self._notification_eligible(target, observed_ts_ns)
        reasons = ("resources_recovered",) if target == "NORMAL" else assessment.reason_codes
        return RuntimeResourceHealthEvent(
            event_id=f"runtime-resource-health:{self._source}:{observed_ts_ns}:{target}",
            source=self._source,
            observed_ts_ns=observed_ts_ns,
            state=target,
            previous_state=previous,
            reason_codes=reasons,
            observations=assessment.observations,
            thresholds=assessment.thresholds,
            notification_eligible=notification_eligible,
            threshold_version=self._policy.threshold_version,
        )

    def _required_samples(self, target: str) -> int:
        if _SEVERITY[target] < _SEVERITY[self._state]:
            return self._policy.recovery_consecutive_samples
        if target == "CRITICAL":
            return self._policy.critical_consecutive_samples
        return self._policy.warning_consecutive_samples

    def _notification_eligible(self, target: str, observed_ts_ns: int) -> bool:
        if target == "NORMAL":
            return True
        if target == "CRITICAL":
            self._last_notification_ns = observed_ts_ns
            return True
        cooldown_ns = self._policy.notification_cooldown_ms * 1_000_000
        eligible = (
            self._last_notification_ns is None
            or observed_ts_ns - self._last_notification_ns >= cooldown_ns
        )
        if eligible:
            self._last_notification_ns = observed_ts_ns
        return eligible


class RuntimeResourceHealthActorConfig(DataActorConfig):
    def __new__(
        cls,
        sample_interval_ms: int,
        threshold_version: str,
        warning_consecutive_samples: int,
        critical_consecutive_samples: int,
        recovery_consecutive_samples: int,
        notification_cooldown_ms: int,
        rss_growth_window_samples: int,
        stale_warning_ms: int,
        stale_critical_ms: int,
        warning: dict[str, int | float],
        critical: dict[str, int | float],
        actor_id: str | ActorId = "RUNTIME-RESOURCE-HEALTH",
    ) -> RuntimeResourceHealthActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.sample_interval_ms = sample_interval_ms
        obj.threshold_version = threshold_version
        obj.warning_consecutive_samples = warning_consecutive_samples
        obj.critical_consecutive_samples = critical_consecutive_samples
        obj.recovery_consecutive_samples = recovery_consecutive_samples
        obj.notification_cooldown_ms = notification_cooldown_ms
        obj.rss_growth_window_samples = rss_growth_window_samples
        obj.stale_warning_ms = stale_warning_ms
        obj.stale_critical_ms = stale_critical_ms
        obj.warning = warning
        obj.critical = critical
        return obj


class RuntimeResourceHealthActor(DataActor):
    """Evaluate runtime resource health from bounded samples.

    Markeitech Metadata:
        architecture.component.id: actor.runtime-resource-health
        architecture.component.label: Runtime Resource Health
        architecture.component.kind: markeitech_actor
        architecture.component.boundary: boundary.system
    """

    def __init__(self, config: RuntimeResourceHealthActorConfig) -> None:
        super().__init__(config)
        policy = ResourceHealthPolicy(
            threshold_version=config.threshold_version,
            warning_consecutive_samples=config.warning_consecutive_samples,
            critical_consecutive_samples=config.critical_consecutive_samples,
            recovery_consecutive_samples=config.recovery_consecutive_samples,
            notification_cooldown_ms=config.notification_cooldown_ms,
            rss_growth_window_samples=config.rss_growth_window_samples,
            stale_warning_ms=config.stale_warning_ms,
            stale_critical_ms=config.stale_critical_ms,
            warning=dict(config.warning),
            critical=dict(config.critical),
        )
        self._evaluator = RuntimeResourceHealthEvaluator(policy, str(self.actor_id))
        self._sample_interval_ns = config.sample_interval_ms * 1_000_000
        self._last_sample_ts_ns: int | None = None
        self._started_ts_ns: int | None = None
        self._samples = 0
        self._transitions = 0
        self._rejected = 0

    def on_start(self) -> None:
        self._started_ts_ns = self.clock.timestamp_ns()
        self.subscribe_signal(RUNTIME_RESOURCE_SIGNAL)
        self.clock.set_timer_ns(
            _STALE_TIMER,
            self._sample_interval_ns,
            callback=self._check_staleness,
        )
        self.log.info("RUNTIME_RESOURCE_HEALTH_STARTED")

    def on_signal(self, signal: Signal) -> None:
        if signal.name != RUNTIME_RESOURCE_SIGNAL:
            return
        try:
            sample = RuntimeResourceEvent.from_signal_value(signal.value)
        except ValueError as exc:
            self._rejected += 1
            self.log.error(
                "RUNTIME_RESOURCE_HEALTH_REJECTED"
                f" | rejected={self._rejected} | error={type(exc).__name__}: {exc}",
            )
            return
        self._samples += 1
        self._last_sample_ts_ns = sample.observed_ts_ns
        self._publish(self._evaluator.evaluate(sample))

    def on_stop(self) -> None:
        self.unsubscribe_signal(RUNTIME_RESOURCE_SIGNAL)
        if _STALE_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_STALE_TIMER)
        self.log.info(
            "RUNTIME_RESOURCE_HEALTH_SUMMARY"
            f" | state={self._evaluator.state} | samples={self._samples}"
            f" | transitions={self._transitions} | rejected={self._rejected}",
        )

    def _check_staleness(self, _event) -> None:  # noqa: ANN001
        now_ns = self.clock.timestamp_ns()
        reference_ns = self._last_sample_ts_ns or self._started_ts_ns
        if reference_ns is None:
            return
        elapsed_ms = max(0, (now_ns - reference_ns) // 1_000_000)
        self._publish(self._evaluator.evaluate_staleness(now_ns, elapsed_ms))

    def _publish(self, event: RuntimeResourceHealthEvent | None) -> None:
        if event is None:
            return
        self._transitions += 1
        self.publish_signal(RUNTIME_RESOURCE_HEALTH_SIGNAL, event.to_signal_value())
        self.log.warning(
            "RUNTIME_RESOURCE_HEALTH"
            f" | state={event.previous_state}->{event.state}"
            f" | reasons={','.join(event.reason_codes)}"
            f" | threshold_version={event.threshold_version}"
            f" | notification_eligible={event.notification_eligible}",
        )


def _observations(
    sample: RuntimeResourceEvent,
    rss_history: deque[int],
) -> dict[str, int | float | str | None]:
    rss_growth = sample.rss_bytes - rss_history[0] if len(rss_history) > 1 else 0
    open_fd_ratio = (
        sample.open_fd_count / sample.open_fd_soft_limit
        if sample.open_fd_count is not None and sample.open_fd_soft_limit
        else None
    )
    return {
        "host_memory_available_percent": sample.host_memory_available_percent,
        "host_cpu_percent": sample.host_cpu_percent,
        "host_swap_percent": sample.host_swap_percent,
        "disk_free_bytes": sample.disk_free_bytes,
        "disk_free_percent": sample.disk_free_percent,
        "rss_bytes": sample.rss_bytes,
        "rss_growth_bytes": rss_growth,
        "cpu_percent": sample.cpu_percent,
        "thread_count": sample.thread_count,
        "open_fd_ratio": open_fd_ratio,
    }


def _assess(
    observations: dict[str, int | float | str | None],
    policy: ResourceHealthPolicy,
) -> ResourceAssessment:
    for state, thresholds in (("CRITICAL", policy.critical), ("WARNING", policy.warning)):
        breached: list[str] = []
        used_thresholds: dict[str, int | float] = {}
        for metric, threshold in thresholds.items():
            observed = observations.get(metric)
            if not isinstance(observed, int | float) or isinstance(observed, bool):
                continue
            is_breached = (
                observed <= threshold if metric in _LOWER_IS_WORSE else observed >= threshold
            )
            if is_breached:
                breached.append(metric)
                used_thresholds[metric] = threshold
        if breached:
            return ResourceAssessment(
                state=state,
                reason_codes=tuple(sorted(breached)),
                observations=observations,
                thresholds=used_thresholds,
            )
    return ResourceAssessment(
        state="NORMAL",
        reason_codes=("within_configured_thresholds",),
        observations=observations,
        thresholds=policy.warning,
    )
