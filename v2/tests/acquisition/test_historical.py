from __future__ import annotations

from types import MappingProxyType

import pytest

from markeitech.acquisition import (
    CapabilityDeclaration,
    CapabilityHistoricalRequirement,
    FeedKind,
    HistoricalCapabilityBinding,
    HistoricalDependencyCompiler,
    HistoricalPlanningError,
    HistoricalResourcePolicy,
    HistoricalWindow,
    HistoricalWindowBounds,
)


def _capability(*, maximum: int = 80) -> CapabilityDeclaration:
    return CapabilityDeclaration(
        capability_id="session_vwap",
        version=2,
        historical_requirements=(
            CapabilityHistoricalRequirement(
                kind=FeedKind.BARS,
                selector="1-MINUTE-LAST-EXTERNAL",
                window=HistoricalWindow.SESSION_TO_DATE,
                minimum_observations=20,
                maximum_observations=maximum,
                window_parameters={"phase": "RTH"},
                parameters={"regular_hours": True},
            ),
        ),
    )


def _binding(consumer_id: str, *, priority: int = 50) -> HistoricalCapabilityBinding:
    return HistoricalCapabilityBinding(
        consumer_id=consumer_id,
        instrument_id="SPY.ARCA",
        capability=_capability(),
        purpose="initialize session VWAP",
        priority=priority,
    )


def _bounds() -> MappingProxyType:
    return MappingProxyType(
        {
            ("SPY.ARCA", HistoricalWindow.SESSION_TO_DATE): HistoricalWindowBounds(
                window=HistoricalWindow.SESSION_TO_DATE,
                start_ns=100,
                end_ns=200,
            ),
        },
    )


def _compiler(**overrides: int) -> HistoricalDependencyCompiler:
    values = {
        "maximum_requests": 10,
        "maximum_observations_per_request": 500,
        "maximum_total_observations": 2_000,
    }
    values.update(overrides)
    return HistoricalDependencyCompiler(HistoricalResourcePolicy(**values))


def test_compiles_exact_bounded_request_with_lineage() -> None:
    request = _compiler().compile((_binding("metric:spy-vwap"),), _bounds())[0]

    assert request.instrument_id == "SPY.ARCA"
    assert request.selector == "1-MINUTE-LAST-EXTERNAL"
    assert request.start_ns == 100
    assert request.end_ns == 200
    assert request.limit == 80
    assert request.parameters == {"regular_hours": True}
    assert _capability().historical_requirements[0].window_parameters == {"phase": "RTH"}
    assert request.dependencies[0].minimum_observations == 20
    assert request.dependencies[0].capability_id == "session_vwap"
    assert request.request_id.startswith("historical:")


def test_deduplicates_provider_request_and_retains_all_consumers() -> None:
    requests = _compiler().compile(
        (_binding("metric:a", priority=20), _binding("metric:b", priority=90)),
        _bounds(),
    )

    assert len(requests) == 1
    assert requests[0].priority == 90
    assert tuple(item.consumer_id for item in requests[0].dependencies) == (
        "metric:a",
        "metric:b",
    )


def test_compilation_is_deterministic_independent_of_binding_order() -> None:
    compiler = _compiler()
    first = compiler.compile((_binding("metric:b"), _binding("metric:a")), _bounds())
    second = compiler.compile((_binding("metric:a"), _binding("metric:b")), _bounds())

    assert first == second


def test_rejects_unresolved_session_window() -> None:
    with pytest.raises(HistoricalPlanningError, match="window is unresolved"):
        _compiler().compile((_binding("metric:a"),), {})


def test_rejects_request_above_resource_policy() -> None:
    with pytest.raises(HistoricalPlanningError, match="per-request policy"):
        _compiler(maximum_observations_per_request=50).compile(
            (_binding("metric:a"),),
            _bounds(),
        )


def test_rejects_unsupported_historical_feed_kind() -> None:
    with pytest.raises(ValueError, match="historical bar requirements only"):
        CapabilityHistoricalRequirement(
            kind=FeedKind.TRADES,
            selector="default",
            window=HistoricalWindow.RECENT_COMPLETED,
            minimum_observations=10,
            maximum_observations=20,
        )
