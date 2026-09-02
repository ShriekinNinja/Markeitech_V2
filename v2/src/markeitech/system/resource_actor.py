from __future__ import annotations

from dataclasses import dataclass
from resource import RLIMIT_NOFILE, getrlimit
from time import monotonic

import psutil
from nautilus_trader.common import DataActor, DataActorConfig
from nautilus_trader.model import ActorId, AggregationSource

from markeitech.system.resource_contracts import (
    RUNTIME_RESOURCE_SIGNAL,
    RuntimeResourceEvent,
)

_RESOURCE_TIMER = "runtime-resource-sample"


@dataclass(frozen=True, slots=True)
class ProcessResourceSample:
    rss_bytes: int
    vms_bytes: int
    cpu_user_seconds: float
    cpu_system_seconds: float
    thread_count: int
    open_fd_count: int | None
    open_fd_soft_limit: int | None
    host_cpu_percent: float
    host_memory_total_bytes: int
    host_memory_available_bytes: int
    host_memory_available_percent: float
    host_swap_used_bytes: int
    host_swap_percent: float
    disk_total_bytes: int
    disk_free_bytes: int
    disk_free_percent: float
    monotonic_seconds: float


@dataclass(frozen=True, slots=True)
class CacheResourceSample:
    observed: bool
    error: str | None
    instrument_count: int | None
    quote_tick_count: int | None
    trade_tick_count: int | None
    bar_type_count: int | None
    bar_count: int | None


class ProcessResourceSampler:
    def __init__(self, disk_path: str) -> None:
        self._process = psutil.Process()
        self._disk_path = disk_path

    def sample(self) -> ProcessResourceSample:
        memory = self._process.memory_info()
        cpu = self._process.cpu_times()
        host_memory = psutil.virtual_memory()
        host_swap = psutil.swap_memory()
        disk = psutil.disk_usage(self._disk_path)
        open_fd_count = None
        num_fds = getattr(self._process, "num_fds", None)
        if num_fds is not None:
            try:
                open_fd_count = num_fds()
            except (OSError, psutil.Error):
                open_fd_count = None
        try:
            soft_limit, _ = getrlimit(RLIMIT_NOFILE)
            open_fd_soft_limit = soft_limit if soft_limit > 0 else None
        except (OSError, ValueError):
            open_fd_soft_limit = None
        return ProcessResourceSample(
            rss_bytes=memory.rss,
            vms_bytes=memory.vms,
            cpu_user_seconds=cpu.user,
            cpu_system_seconds=cpu.system,
            thread_count=self._process.num_threads(),
            open_fd_count=open_fd_count,
            open_fd_soft_limit=open_fd_soft_limit,
            host_cpu_percent=psutil.cpu_percent(interval=None),
            host_memory_total_bytes=host_memory.total,
            host_memory_available_bytes=host_memory.available,
            host_memory_available_percent=100.0 - host_memory.percent,
            host_swap_used_bytes=host_swap.used,
            host_swap_percent=host_swap.percent,
            disk_total_bytes=disk.total,
            disk_free_bytes=disk.free,
            disk_free_percent=(disk.free / disk.total * 100.0 if disk.total else 0.0),
            monotonic_seconds=monotonic(),
        )


class RuntimeResourceActorConfig(DataActorConfig):
    def __new__(
        cls,
        sample_interval_ms: int,
        log_every_samples: int,
        include_cache_counts: bool,
        disk_path: str,
        actor_id: str | ActorId = "RUNTIME-RESOURCES",
    ) -> RuntimeResourceActorConfig:
        resolved_actor_id = (
            actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        )
        obj = super().__new__(cls, actor_id=resolved_actor_id)
        obj.sample_interval_ms = sample_interval_ms
        obj.log_every_samples = log_every_samples
        obj.include_cache_counts = include_cache_counts
        obj.disk_path = disk_path
        return obj


class RuntimeResourceActor(DataActor):
    """Observe bounded runtime resource samples.

    Markeitech Metadata:
        architecture.component.id: actor.runtime-resources
        architecture.component.label: Runtime Resources
        architecture.component.kind: markeitech_actor
        architecture.component.boundary: boundary.system
    """

    def __init__(self, config: RuntimeResourceActorConfig) -> None:
        super().__init__(config)
        self._sample_interval_ms = config.sample_interval_ms
        self._sample_interval_ns = config.sample_interval_ms * 1_000_000
        self._log_every_samples = config.log_every_samples
        self._include_cache_counts = config.include_cache_counts
        self._disk_path = config.disk_path
        self._sampler = ProcessResourceSampler(config.disk_path)
        self._sequence = 0
        self._failures = 0
        self._previous: ProcessResourceSample | None = None
        self._initial_rss_bytes: int | None = None
        self._latest_rss_bytes: int | None = None
        self._minimum_rss_bytes: int | None = None
        self._peak_rss_bytes = 0
        self._maximum_cpu_percent = 0.0
        self._maximum_thread_count = 0
        self._maximum_open_fd_count: int | None = None
        self._maximum_cache_instrument_count: int | None = None
        self._maximum_cache_quote_tick_count: int | None = None
        self._maximum_cache_trade_tick_count: int | None = None
        self._maximum_cache_bar_type_count: int | None = None
        self._maximum_cache_bar_count: int | None = None

    def on_start(self) -> None:
        self.clock.set_timer_ns(
            _RESOURCE_TIMER,
            self._sample_interval_ns,
            callback=self._sample,
        )
        self.log.info(
            "RUNTIME_RESOURCE_STARTED"
            f" | sample_interval_ms={self._sample_interval_ms}"
            f" | include_cache_counts={self._include_cache_counts}"
            f" | disk_path={self._disk_path}",
        )

    def on_stop(self) -> None:
        if _RESOURCE_TIMER in self.clock.timer_names():
            self.clock.cancel_timer(_RESOURCE_TIMER)
        growth = (
            None
            if self._initial_rss_bytes is None or self._latest_rss_bytes is None
            else self._latest_rss_bytes - self._initial_rss_bytes
        )
        self.log.info(
            "RUNTIME_RESOURCE_SUMMARY"
            f" | samples={self._sequence}"
            f" | failures={self._failures}"
            f" | initial_rss_bytes={self._initial_rss_bytes}"
            f" | min_rss_bytes={self._minimum_rss_bytes}"
            f" | final_rss_bytes={self._latest_rss_bytes}"
            f" | peak_rss_bytes={self._peak_rss_bytes}"
            f" | rss_growth_bytes={growth}"
            f" | max_cpu_pct={self._maximum_cpu_percent:.2f}"
            f" | max_threads={self._maximum_thread_count}"
            f" | max_open_fds={self._maximum_open_fd_count}"
            f" | max_cache_instruments={self._maximum_cache_instrument_count}"
            f" | max_cache_quotes={self._maximum_cache_quote_tick_count}"
            f" | max_cache_trades={self._maximum_cache_trade_tick_count}"
            f" | max_cache_bar_types={self._maximum_cache_bar_type_count}"
            f" | max_cache_bars={self._maximum_cache_bar_count}",
        )

    def _sample(self, _event) -> None:  # noqa: ANN001
        try:
            process = self._sampler.sample()
            cache = self._sample_cache()
            cpu_percent = _cpu_percent(self._previous, process)
            self._sequence += 1
            if self._initial_rss_bytes is None:
                self._initial_rss_bytes = process.rss_bytes
            self._latest_rss_bytes = process.rss_bytes
            self._minimum_rss_bytes = min(
                self._minimum_rss_bytes or process.rss_bytes,
                process.rss_bytes,
            )
            self._peak_rss_bytes = max(self._peak_rss_bytes, process.rss_bytes)
            self._maximum_cpu_percent = max(self._maximum_cpu_percent, cpu_percent)
            self._maximum_thread_count = max(self._maximum_thread_count, process.thread_count)
            if process.open_fd_count is not None:
                self._maximum_open_fd_count = max(
                    self._maximum_open_fd_count or 0,
                    process.open_fd_count,
                )
            if cache.observed:
                self._maximum_cache_instrument_count = _optional_max(
                    self._maximum_cache_instrument_count,
                    cache.instrument_count,
                )
                self._maximum_cache_quote_tick_count = _optional_max(
                    self._maximum_cache_quote_tick_count,
                    cache.quote_tick_count,
                )
                self._maximum_cache_trade_tick_count = _optional_max(
                    self._maximum_cache_trade_tick_count,
                    cache.trade_tick_count,
                )
                self._maximum_cache_bar_type_count = _optional_max(
                    self._maximum_cache_bar_type_count,
                    cache.bar_type_count,
                )
                self._maximum_cache_bar_count = _optional_max(
                    self._maximum_cache_bar_count,
                    cache.bar_count,
                )
            observed_ts_ns = self.clock.timestamp_ns()
            resource = RuntimeResourceEvent(
                event_id=f"runtime-resource:{self.actor_id}:{observed_ts_ns}",
                source=str(self.actor_id),
                observed_ts_ns=observed_ts_ns,
                sample_sequence=self._sequence,
                sample_interval_ms=self._sample_interval_ms,
                rss_bytes=process.rss_bytes,
                peak_rss_bytes=self._peak_rss_bytes,
                vms_bytes=process.vms_bytes,
                cpu_user_seconds=process.cpu_user_seconds,
                cpu_system_seconds=process.cpu_system_seconds,
                cpu_percent=cpu_percent,
                thread_count=process.thread_count,
                open_fd_count=process.open_fd_count,
                open_fd_soft_limit=process.open_fd_soft_limit,
                host_cpu_percent=process.host_cpu_percent,
                host_memory_total_bytes=process.host_memory_total_bytes,
                host_memory_available_bytes=process.host_memory_available_bytes,
                host_memory_available_percent=process.host_memory_available_percent,
                host_swap_used_bytes=process.host_swap_used_bytes,
                host_swap_percent=process.host_swap_percent,
                disk_path=self._disk_path,
                disk_total_bytes=process.disk_total_bytes,
                disk_free_bytes=process.disk_free_bytes,
                disk_free_percent=process.disk_free_percent,
                cache_observed=cache.observed,
                cache_error=cache.error,
                cache_instrument_count=cache.instrument_count,
                cache_quote_tick_count=cache.quote_tick_count,
                cache_trade_tick_count=cache.trade_tick_count,
                cache_bar_type_count=cache.bar_type_count,
                cache_bar_count=cache.bar_count,
            )
            self.publish_signal(RUNTIME_RESOURCE_SIGNAL, resource.to_signal_value())
            if self._sequence % self._log_every_samples == 0:
                self._log_sample(resource)
            self._previous = process
        except Exception as exc:  # noqa: BLE001
            self._failures += 1
            self.log.warning(
                "RUNTIME_RESOURCE_SAMPLE_FAILED"
                f" | failures={self._failures}"
                f" | error={type(exc).__name__}: {exc}",
            )

    def _sample_cache(self) -> CacheResourceSample:
        if not self._include_cache_counts:
            return CacheResourceSample(False, "disabled", None, None, None, None, None)
        try:
            instrument_ids = tuple(self.cache.instrument_ids())
            bar_types = set(self.cache.bar_types(aggregation_source=AggregationSource.EXTERNAL))
            bar_types.update(
                self.cache.bar_types(aggregation_source=AggregationSource.INTERNAL),
            )
            return CacheResourceSample(
                observed=True,
                error=None,
                instrument_count=len(instrument_ids),
                quote_tick_count=sum(
                    self.cache.quote_count(instrument_id) for instrument_id in instrument_ids
                ),
                trade_tick_count=sum(
                    self.cache.trade_count(instrument_id) for instrument_id in instrument_ids
                ),
                bar_type_count=len(bar_types),
                bar_count=sum(self.cache.bar_count(bar_type) for bar_type in bar_types),
            )
        except Exception as exc:  # noqa: BLE001
            return CacheResourceSample(
                False,
                f"{type(exc).__name__}: {exc}",
                None,
                None,
                None,
                None,
                None,
            )

    def _log_sample(self, resource: RuntimeResourceEvent) -> None:
        self.log.info(
            "RUNTIME_RESOURCE"
            f" | sample={resource.sample_sequence}"
            f" | rss_mb={resource.rss_bytes / 1_048_576:.1f}"
            f" | peak_rss_mb={resource.peak_rss_bytes / 1_048_576:.1f}"
            f" | cpu_pct={resource.cpu_percent:.2f}"
            f" | threads={resource.thread_count}"
            f" | open_fds={resource.open_fd_count}"
            f" | open_fd_soft_limit={resource.open_fd_soft_limit}"
            f" | host_cpu_pct={resource.host_cpu_percent:.2f}"
            f" | host_memory_available_pct={resource.host_memory_available_percent:.2f}"
            f" | swap_pct={resource.host_swap_percent:.2f}"
            f" | disk_free_gb={resource.disk_free_bytes / 1_073_741_824:.1f}"
            f" | disk_free_pct={resource.disk_free_percent:.2f}"
            f" | cache_instruments={resource.cache_instrument_count}"
            f" | cache_quotes={resource.cache_quote_tick_count}"
            f" | cache_trades={resource.cache_trade_tick_count}"
            f" | cache_bar_types={resource.cache_bar_type_count}"
            f" | cache_bars={resource.cache_bar_count}"
            f" | cache_error={resource.cache_error}",
        )


def _cpu_percent(
    previous: ProcessResourceSample | None,
    current: ProcessResourceSample,
) -> float:
    if previous is None:
        return 0.0
    elapsed = current.monotonic_seconds - previous.monotonic_seconds
    if elapsed <= 0:
        return 0.0
    cpu_delta = (
        current.cpu_user_seconds
        + current.cpu_system_seconds
        - previous.cpu_user_seconds
        - previous.cpu_system_seconds
    )
    return max(0.0, cpu_delta / elapsed * 100.0)


def _optional_max(current: int | None, candidate: int | None) -> int | None:
    if candidate is None:
        return current
    return max(current or 0, candidate)
