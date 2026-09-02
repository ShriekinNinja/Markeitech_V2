from __future__ import annotations

import tomllib
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

from markeitech.intelligence.market_structure_runtime import (
    resolve_market_structure_definitions,
)


def _definitions() -> list[dict[str, object]]:
    path = Path(__file__).parents[1] / "system/entity-analysis-definitions.toml"
    raw = tomllib.loads(path.read_text())
    return [
        item
        for item in raw["metrics"]["entity_analysis"]["definitions"]
        if item["group"] == "swing_fvg_zone"
    ]


def test_resolves_every_reviewed_market_structure_contract() -> None:
    resolved = resolve_market_structure_definitions(
        _definitions(),
        eligible_instrument_ids=("ESU6.CME",),
    )

    assert resolved.definition_count == 5
    assert len(resolved.confirmed_swings) == 1
    assert len(resolved.relationships) == 1
    assert len(resolved.fvgs) == 1
    assert len(resolved.zones) == 1


def test_application_selects_its_exact_named_parameter_set() -> None:
    swing = deepcopy(
        next(item for item in _definitions() if item["entity_type"] == "confirmed_swing"),
    )
    selected = deepcopy(swing["parameter_sets"][0])
    selected["parameter_set_id"] = "swing-selected-v2"
    selected["parameter_version"] = 2
    selected["values"]["minimum_prominence"] = 2.0
    swing["parameter_sets"].append(selected)
    swing["applications"][0]["parameter_set_id"] = "swing-selected-v2"

    resolved = resolve_market_structure_definitions(
        [swing],
        eligible_instrument_ids=("ESU6.CME",),
    )

    application = resolved.confirmed_swings[0].applications[0]
    assert application.parameter_version == 2
    assert application.policy.minimum_prominence == Decimal("2.0")


def test_unknown_application_parameter_set_never_falls_back() -> None:
    swing = deepcopy(
        next(item for item in _definitions() if item["entity_type"] == "confirmed_swing"),
    )
    swing["applications"][0]["parameter_set_id"] = "missing-set"

    with pytest.raises(ValueError, match="parameter set is unavailable"):
        resolve_market_structure_definitions(
            [swing],
            eligible_instrument_ids=("ESU6.CME",),
        )


def test_relationship_runtime_rejects_missing_companion_definition() -> None:
    definitions = [
        item
        for item in _definitions()
        if item["entity_type"] in {"confirmed_swing", "pivot_structure_state"}
    ]

    with pytest.raises(ValueError, match="relationships require entity definitions"):
        resolve_market_structure_definitions(
            definitions,
            eligible_instrument_ids=("ESU6.CME",),
        )


def test_relationship_runtime_rejects_divergent_companion_policy() -> None:
    definitions = deepcopy(_definitions())
    swing_leg = next(item for item in definitions if item["entity_type"] == "swing_leg")
    swing_leg["parameter_sets"][0]["values"]["equality_tolerance"] = 1.0

    with pytest.raises(ValueError, match="companion parameter_sets must match exactly"):
        resolve_market_structure_definitions(
            definitions,
            eligible_instrument_ids=("ESU6.CME",),
        )


def test_relationship_runtime_rejects_uncovered_instrument_scope() -> None:
    definitions = deepcopy(_definitions())
    swing = next(item for item in definitions if item["entity_type"] == "confirmed_swing")
    swing["applications"][0]["instrument_ids"] = ["ESU6.CME"]
    for entity_type in {"swing_leg", "pivot_structure_state"}:
        relationship = next(item for item in definitions if item["entity_type"] == entity_type)
        relationship["applications"][0]["instrument_ids"] = ["NQU6.CME"]

    with pytest.raises(ValueError, match="uncovered swing scope"):
        resolve_market_structure_definitions(
            definitions,
            eligible_instrument_ids=("ESU6.CME", "NQU6.CME"),
        )


def test_zone_runtime_rejects_uncovered_source_scope() -> None:
    definitions = deepcopy(
        [
            item
            for item in _definitions()
            if item["entity_type"] in {"confirmed_swing", "fair_value_gap", "derived_zone"}
        ],
    )
    for source_type in {"confirmed_swing", "fair_value_gap"}:
        source = next(item for item in definitions if item["entity_type"] == source_type)
        source["applications"][0]["instrument_ids"] = ["ESU6.CME"]
    zone = next(item for item in definitions if item["entity_type"] == "derived_zone")
    zone["applications"][0]["instrument_ids"] = ["NQU6.CME"]

    with pytest.raises(ValueError, match="zone application .* has uncovered"):
        resolve_market_structure_definitions(
            definitions,
            eligible_instrument_ids=("ESU6.CME", "NQU6.CME"),
        )
