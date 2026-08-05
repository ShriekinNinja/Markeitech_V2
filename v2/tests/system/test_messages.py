from __future__ import annotations

import json

import pytest

from markeitech.system.messages import (
    SYSTEM_HEALTH_SCHEMA_VERSION,
    SystemHealthEvent,
)


def test_system_health_event_round_trips_as_deterministic_json_text() -> None:
    event = SystemHealthEvent(
        state="READY",
        reason="instrument definitions available",
        source="SYSTEM-READINESS",
        evidence={"instrument_count": 2, "instruments": "ESU6.CME,SPY.ARCA"},
    )

    encoded = event.to_signal_value()

    assert isinstance(encoded, str)
    assert encoded == json.dumps(json.loads(encoded), separators=(",", ":"), sort_keys=True)
    assert SystemHealthEvent.from_signal_value(encoded) == event


@pytest.mark.parametrize(
    "value, match",
    [
        ("not-json", "valid JSON text"),
        ('{"state":"READY"}', "missing"),
        (
            json.dumps(
                {
                    "schema_version": SYSTEM_HEALTH_SCHEMA_VERSION + 1,
                    "state": "READY",
                    "reason": "available",
                    "source": "SYSTEM-READINESS",
                    "evidence": {},
                },
            ),
            "unsupported system health schema",
        ),
    ],
)
def test_system_health_event_rejects_invalid_signal_values(value: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        SystemHealthEvent.from_signal_value(value)


def test_system_health_event_copies_mutable_evidence() -> None:
    evidence = {"instrument_count": 2}
    event = SystemHealthEvent(
        state="READY",
        reason="available",
        source="SYSTEM-READINESS",
        evidence=evidence,
    )

    evidence["instrument_count"] = 3

    assert event.evidence["instrument_count"] == 2

    with pytest.raises(TypeError):
        event.evidence["instrument_count"] = 4  # type: ignore[index]
