from __future__ import annotations

import pytest

from markeitech.system.native_consumer_probe import _build_probe_requirements


def test_builds_quote_and_trade_probe_requirements() -> None:
    requirements = _build_probe_requirements(
        (
            {"instrument_id": "ESU6.CME", "kind": "quotes", "selector": "default"},
            {"instrument_id": "ESU6.CME", "kind": "trades", "selector": "default"},
        ),
    )

    assert tuple(item.stream_key for item in requirements) == (
        ("ESU6.CME", "quotes", "default"),
        ("ESU6.CME", "trades", "default"),
    )


def test_rejects_non_tick_probe_feed() -> None:
    with pytest.raises(ValueError, match="quote and trade feeds only"):
        _build_probe_requirements(
            (
                {
                    "instrument_id": "ESU6.CME",
                    "kind": "bars",
                    "selector": "5-MINUTE-LAST-EXTERNAL",
                },
            ),
        )
