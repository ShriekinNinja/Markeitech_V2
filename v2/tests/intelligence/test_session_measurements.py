from __future__ import annotations

import pytest

from markeitech.acquisition import HistoricalWindow
from markeitech.intelligence import MetricRegistry, ParameterMutability
from markeitech.intelligence.session_measurements import (
    COMPLETED_BAR_METRIC_IDS,
    COMPLETED_BAR_SIMPLE_RETURN_METRIC_ID,
    COMPLETED_BAR_VOLUME_METRIC_ID,
    CompletedBarCatalogPolicy,
    completed_bar_metric_definitions,
)


def _policy(**changes: object) -> CompletedBarCatalogPolicy:
    values = {
        "live_selector": "5-SECOND-LAST-EXTERNAL",
        "historical_selector": "1-MINUTE-LAST-EXTERNAL",
        "historical_window": HistoricalWindow.RECENT_COMPLETED,
        "minimum_historical_observations": 2,
        "maximum_historical_observations": 500,
        "calculation_interval_seconds": 60,
        "minimum_interval_seconds": 5,
        "maximum_interval_seconds": 3600,
        "interval_step_seconds": 5,
        "interval_dynamic": True,
        "maximum_retained_observations": 2000,
        "maximum_output_age_ms": 120_000,
    }
    values.update(changes)
    return CompletedBarCatalogPolicy(**values)  # type: ignore[arg-type]


def test_completed_bar_catalog_declares_exact_configured_dependencies() -> None:
    definitions = completed_bar_metric_definitions(_policy())
    registry = MetricRegistry(definitions)

    assert tuple(definition.metric_id for definition in definitions) == COMPLETED_BAR_METRIC_IDS
    volume = registry.get(COMPLETED_BAR_VOLUME_METRIC_ID, 1)
    assert volume.live_inputs[0].selector == "5-SECOND-LAST-EXTERNAL"
    assert volume.historical_inputs[0].selector == "1-MINUTE-LAST-EXTERNAL"
    assert volume.historical_inputs[0].window is HistoricalWindow.RECENT_COMPLETED
    assert volume.historical_inputs[0].parameters == {
        "calculation_interval_seconds": 60,
        "purpose": "completed_bar_foundation",
    }
    assert volume.parameters[0].dynamic is True
    assert volume.parameters[0].mutability is ParameterMutability.POLICY_CONTROLLED_RUNTIME
    assert registry.get(COMPLETED_BAR_SIMPLE_RETURN_METRIC_ID, 1).warmup.minimum_observations == 2


def test_completed_bar_catalog_keeps_resolution_policy_configurable() -> None:
    definitions = completed_bar_metric_definitions(
        _policy(
            live_selector="1-MINUTE-LAST-EXTERNAL",
            historical_selector="1-HOUR-LAST-EXTERNAL",
            calculation_interval_seconds=3600,
            interval_dynamic=False,
        ),
    )

    definition = definitions[0]
    assert definition.live_inputs[0].selector == "1-MINUTE-LAST-EXTERNAL"
    assert definition.historical_inputs[0].selector == "1-HOUR-LAST-EXTERNAL"
    assert definition.parameters[0].default == 3600
    assert definition.parameters[0].mutability is ParameterMutability.STARTUP_ONLY


def test_completed_bar_catalog_rejects_invalid_resolution_envelopes() -> None:
    with pytest.raises(ValueError, match="inside its configured envelope"):
        _policy(calculation_interval_seconds=1)
    with pytest.raises(ValueError, match="align"):
        _policy(calculation_interval_seconds=62)
