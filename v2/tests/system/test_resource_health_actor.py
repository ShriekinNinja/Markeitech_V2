from __future__ import annotations

from markeitech.system.resource_contracts import (
    RUNTIME_RESOURCE_HEALTH_SIGNAL,
    RUNTIME_RESOURCE_SIGNAL,
    RuntimeResourceEvent,
    RuntimeResourceHealthEvent,
)
from markeitech.system.resource_health_actor import (
    ResourceHealthPolicy,
    RuntimeResourceHealthEvaluator,
)


def _policy() -> ResourceHealthPolicy:
    warning = {
        "host_memory_available_percent": 15.0,
        "host_cpu_percent": 90.0,
        "host_swap_percent": 50.0,
        "disk_free_bytes": 15_000,
        "disk_free_percent": 10.0,
        "rss_bytes": 4_000,
        "rss_growth_bytes": 500,
        "cpu_percent": 400.0,
        "thread_count": 100,
        "open_fd_ratio": 0.70,
    }
    critical = {
        "host_memory_available_percent": 8.0,
        "host_cpu_percent": 98.0,
        "host_swap_percent": 80.0,
        "disk_free_bytes": 5_000,
        "disk_free_percent": 5.0,
        "rss_bytes": 8_000,
        "rss_growth_bytes": 1_000,
        "cpu_percent": 800.0,
        "thread_count": 250,
        "open_fd_ratio": 0.90,
    }
    return ResourceHealthPolicy(
        threshold_version="test-v1",
        warning_consecutive_samples=2,
        critical_consecutive_samples=1,
        recovery_consecutive_samples=2,
        notification_cooldown_ms=60_000,
        rss_growth_window_samples=3,
        stale_warning_ms=30_000,
        stale_critical_ms=120_000,
        warning=warning,
        critical=critical,
    )


def _sample(sequence: int, **overrides: object) -> RuntimeResourceEvent:
    values: dict[str, object] = {
        "event_id": f"runtime-resource:RUNTIME-RESOURCES:{sequence}",
        "source": "RUNTIME-RESOURCES",
        "observed_ts_ns": sequence * 10_000_000_000,
        "sample_sequence": sequence,
        "sample_interval_ms": 10_000,
        "rss_bytes": 500,
        "peak_rss_bytes": 500,
        "vms_bytes": 1_000,
        "cpu_user_seconds": 1.0,
        "cpu_system_seconds": 0.5,
        "cpu_percent": 15.0,
        "thread_count": 8,
        "open_fd_count": 12,
        "open_fd_soft_limit": 1_024,
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


def test_resource_health_contract_round_trips_exactly() -> None:
    event = RuntimeResourceHealthEvent(
        event_id="runtime-resource-health:RUNTIME-RESOURCE-HEALTH:1:WARNING",
        source="RUNTIME-RESOURCE-HEALTH",
        observed_ts_ns=1,
        state="WARNING",
        previous_state="NORMAL",
        reason_codes=("host_memory_available_percent",),
        observations={"host_memory_available_percent": 14.0},
        thresholds={"host_memory_available_percent": 15.0},
        notification_eligible=True,
        threshold_version="test-v1",
    )

    assert RuntimeResourceHealthEvent.from_signal_value(event.to_signal_value()) == event


def test_resource_signal_names_do_not_overlap_under_prefix_routing() -> None:
    assert not RUNTIME_RESOURCE_HEALTH_SIGNAL.startswith(RUNTIME_RESOURCE_SIGNAL)
    assert not RUNTIME_RESOURCE_SIGNAL.startswith(RUNTIME_RESOURCE_HEALTH_SIGNAL)


def test_evaluator_requires_sustained_warning_and_recovery() -> None:
    evaluator = RuntimeResourceHealthEvaluator(_policy(), "RESOURCE-HEALTH")

    assert evaluator.evaluate(_sample(1, host_memory_available_percent=14.0)) is None
    warning = evaluator.evaluate(_sample(2, host_memory_available_percent=14.0))
    assert warning is not None
    assert warning.state == "WARNING"
    assert warning.reason_codes == ("host_memory_available_percent",)
    assert evaluator.evaluate(_sample(3)) is None
    recovered = evaluator.evaluate(_sample(4))
    assert recovered is not None
    assert recovered.state == "NORMAL"
    assert recovered.previous_state == "WARNING"
    assert recovered.reason_codes == ("resources_recovered",)


def test_evaluator_escalates_critical_immediately_after_configured_count() -> None:
    evaluator = RuntimeResourceHealthEvaluator(_policy(), "RESOURCE-HEALTH")

    critical = evaluator.evaluate(_sample(1, disk_free_bytes=4_000))

    assert critical is not None
    assert critical.state == "CRITICAL"
    assert critical.reason_codes == ("disk_free_bytes",)
    assert critical.notification_eligible is True


def test_evaluator_uses_rolling_rss_growth_without_treating_absence_as_flow() -> None:
    evaluator = RuntimeResourceHealthEvaluator(_policy(), "RESOURCE-HEALTH")

    assert evaluator.evaluate(_sample(1, rss_bytes=500)) is None
    assert evaluator.evaluate(_sample(2, rss_bytes=1_100)) is None
    warning = evaluator.evaluate(_sample(3, rss_bytes=1_300))

    assert warning is not None
    assert warning.state == "WARNING"
    assert warning.reason_codes == ("rss_growth_bytes",)
    assert warning.observations["rss_growth_bytes"] == 800


def test_evaluator_handles_unavailable_file_descriptor_capacity() -> None:
    evaluator = RuntimeResourceHealthEvaluator(_policy(), "RESOURCE-HEALTH")

    assert evaluator.evaluate(_sample(1, open_fd_count=None, open_fd_soft_limit=None)) is None


def test_evaluator_transitions_on_sustained_sample_staleness() -> None:
    evaluator = RuntimeResourceHealthEvaluator(_policy(), "RESOURCE-HEALTH")

    assert evaluator.evaluate_staleness(30_000_000_000, 30_000) is None
    warning = evaluator.evaluate_staleness(40_000_000_000, 40_000)
    critical = evaluator.evaluate_staleness(120_000_000_000, 120_000)

    assert warning is not None and warning.state == "WARNING"
    assert critical is not None and critical.state == "CRITICAL"
    assert critical.reason_codes == ("resource_samples_stale",)


def test_evaluator_persists_repeated_warning_but_marks_cooldown_for_projection() -> None:
    evaluator = RuntimeResourceHealthEvaluator(_policy(), "RESOURCE-HEALTH")
    assert evaluator.evaluate(_sample(1, host_memory_available_percent=14.0)) is None
    first_warning = evaluator.evaluate(_sample(2, host_memory_available_percent=14.0))
    assert first_warning is not None and first_warning.notification_eligible is True
    assert evaluator.evaluate(_sample(3)) is None
    assert evaluator.evaluate(_sample(4)) is not None
    assert evaluator.evaluate(_sample(5, host_memory_available_percent=14.0)) is None
    repeated_warning = evaluator.evaluate(_sample(6, host_memory_available_percent=14.0))

    assert repeated_warning is not None
    assert repeated_warning.state == "WARNING"
    assert repeated_warning.notification_eligible is False
