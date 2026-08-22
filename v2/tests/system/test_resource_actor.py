from __future__ import annotations

import json

import pytest

from markeitech.system.resource_actor import ProcessResourceSample, _cpu_percent
from markeitech.system.resource_contracts import RuntimeResourceEvent


def _event(**overrides: object) -> RuntimeResourceEvent:
    values: dict[str, object] = {
        "event_id": "runtime-resource:RUNTIME-RESOURCES:100",
        "source": "RUNTIME-RESOURCES",
        "observed_ts_ns": 100,
        "sample_sequence": 1,
        "sample_interval_ms": 10000,
        "rss_bytes": 500,
        "peak_rss_bytes": 500,
        "vms_bytes": 1000,
        "cpu_user_seconds": 1.0,
        "cpu_system_seconds": 0.5,
        "cpu_percent": 15.0,
        "thread_count": 8,
        "open_fd_count": 12,
        "open_fd_soft_limit": 1024,
        "host_cpu_percent": 30.0,
        "host_memory_total_bytes": 32_000,
        "host_memory_available_bytes": 16_000,
        "host_memory_available_percent": 50.0,
        "host_swap_used_bytes": 100,
        "host_swap_percent": 1.0,
        "disk_path": "/",
        "disk_total_bytes": 100_000,
        "disk_free_bytes": 50_000,
        "disk_free_percent": 50.0,
        "cache_observed": True,
        "cache_error": None,
        "cache_instrument_count": 2,
        "cache_quote_tick_count": 20,
        "cache_trade_tick_count": 10,
        "cache_bar_type_count": 3,
        "cache_bar_count": 30,
    }
    values.update(overrides)
    return RuntimeResourceEvent(**values)  # type: ignore[arg-type]


def test_runtime_resource_contract_round_trips_exact_payload() -> None:
    event = _event()

    decoded = RuntimeResourceEvent.from_signal_value(event.to_signal_value())

    assert decoded == event
    assert json.loads(event.to_signal_value())["cache_quote_tick_count"] == 20


def test_runtime_resource_contract_preserves_unavailable_cache_evidence() -> None:
    event = _event(
        cache_observed=False,
        cache_error="RuntimeError: unavailable",
        cache_instrument_count=None,
        cache_quote_tick_count=None,
        cache_trade_tick_count=None,
        cache_bar_type_count=None,
        cache_bar_count=None,
    )

    assert event.cache_error == "RuntimeError: unavailable"


def test_runtime_resource_contract_rejects_partial_observed_cache() -> None:
    with pytest.raises(ValueError, match="requires all counts"):
        _event(cache_bar_count=None)


def test_cpu_percent_uses_process_time_delta_over_wall_time() -> None:
    common = {
        "rss_bytes": 1,
        "vms_bytes": 1,
        "thread_count": 1,
        "open_fd_count": 1,
        "open_fd_soft_limit": 1024,
        "host_cpu_percent": 10.0,
        "host_memory_total_bytes": 100,
        "host_memory_available_bytes": 50,
        "host_memory_available_percent": 50.0,
        "host_swap_used_bytes": 0,
        "host_swap_percent": 0.0,
        "disk_total_bytes": 100,
        "disk_free_bytes": 50,
        "disk_free_percent": 50.0,
    }
    previous = ProcessResourceSample(
        **common,
        cpu_user_seconds=2.0,
        cpu_system_seconds=1.0,
        monotonic_seconds=10.0,
    )
    current = ProcessResourceSample(
        **common,
        cpu_user_seconds=2.5,
        cpu_system_seconds=1.5,
        monotonic_seconds=12.0,
    )

    assert _cpu_percent(previous, current) == pytest.approx(50.0)
    assert _cpu_percent(None, current) == 0.0
