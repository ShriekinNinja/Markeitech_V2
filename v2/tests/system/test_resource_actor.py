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
    previous = ProcessResourceSample(1, 1, 2.0, 1.0, 1, 1, 10.0)
    current = ProcessResourceSample(1, 1, 2.5, 1.5, 1, 1, 12.0)

    assert _cpu_percent(previous, current) == pytest.approx(50.0)
    assert _cpu_percent(None, current) == 0.0
