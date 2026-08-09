from __future__ import annotations

import json

import pytest

from markeitech.system.messages import (
    ACQUISITION_STATUS_SCHEMA_VERSION,
    COMPONENT_FAILURE_SCHEMA_VERSION,
    INSTRUMENTS_READY,
    INSTRUMENTS_RESOLVING,
    SYSTEM_HEALTH_SCHEMA_VERSION,
    AcquisitionStatusEvent,
    AcquisitionStatusRequest,
    ComponentFailureEvent,
    SystemHealthEvent,
)


def test_acquisition_status_request_round_trips_as_deterministic_json_text() -> None:
    request = AcquisitionStatusRequest(requester=" SYSTEM-CONTROL ")

    encoded = request.to_signal_value()

    assert encoded == '{"requester":"SYSTEM-CONTROL","schema_version":1}'
    assert AcquisitionStatusRequest.from_signal_value(encoded) == request


def test_resolving_acquisition_status_round_trips_and_reports_missing() -> None:
    event = AcquisitionStatusEvent(
        state=INSTRUMENTS_RESOLVING,
        reason="resolving definitions",
        source="DATA-ACQUISITION",
        expected_instrument_ids=("SPY.ARCA", "ESU6.CME"),
        available_instrument_ids=("ESU6.CME",),
    )

    encoded = event.to_signal_value()

    assert event.expected_instrument_ids == ("ESU6.CME", "SPY.ARCA")
    assert event.missing_instrument_ids == ("SPY.ARCA",)
    assert AcquisitionStatusEvent.from_signal_value(encoded) == event


def test_ready_acquisition_status_requires_every_expected_instrument() -> None:
    event = AcquisitionStatusEvent(
        state=INSTRUMENTS_READY,
        reason="definitions available",
        source="DATA-ACQUISITION",
        expected_instrument_ids=("ESU6.CME", "SPY.ARCA"),
        available_instrument_ids=("SPY.ARCA", "ESU6.CME"),
    )

    assert event.missing_instrument_ids == ()


@pytest.mark.parametrize(
    "overrides, match",
    [
        ({"available_instrument_ids": ("NQU6.CME",)}, "subset"),
        ({"state": INSTRUMENTS_READY}, "requires every expected"),
        (
            {
                "state": INSTRUMENTS_RESOLVING,
                "available_instrument_ids": ("ESU6.CME", "SPY.ARCA"),
            },
            "requires at least one missing",
        ),
        ({"expected_instrument_ids": ("ESU6.CME", "ESU6.CME")}, "duplicates"),
    ],
)
def test_acquisition_status_rejects_inconsistent_state(
    overrides: dict[str, object],
    match: str,
) -> None:
    values: dict[str, object] = {
        "state": INSTRUMENTS_RESOLVING,
        "reason": "resolving definitions",
        "source": "DATA-ACQUISITION",
        "expected_instrument_ids": ("ESU6.CME", "SPY.ARCA"),
        "available_instrument_ids": ("ESU6.CME",),
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=match):
        AcquisitionStatusEvent(**values)  # type: ignore[arg-type]


def test_acquisition_status_rejects_unsupported_schema() -> None:
    value = json.dumps(
        {
            "schema_version": ACQUISITION_STATUS_SCHEMA_VERSION + 1,
            "state": INSTRUMENTS_READY,
            "reason": "available",
            "source": "DATA-ACQUISITION",
            "expected_instrument_ids": ["ESU6.CME"],
            "available_instrument_ids": ["ESU6.CME"],
        },
    )

    with pytest.raises(ValueError, match="unsupported acquisition status schema"):
        AcquisitionStatusEvent.from_signal_value(value)


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


def test_component_failure_event_round_trips_as_deterministic_json_text() -> None:
    event = ComponentFailureEvent(
        component="operational_persistence",
        code="health_event_write_failed",
        reason="operational persistence is unavailable",
        evidence={"attempts": 3, "error_code": "OperationalError"},
    )

    encoded = event.to_signal_value()

    assert encoded == json.dumps(json.loads(encoded), separators=(",", ":"), sort_keys=True)
    assert ComponentFailureEvent.from_signal_value(encoded) == event


@pytest.mark.parametrize(
    "value, match",
    [
        ("not-json", "valid JSON text"),
        ('{"component":"operational_persistence"}', "missing"),
        (
            json.dumps(
                {
                    "schema_version": COMPONENT_FAILURE_SCHEMA_VERSION + 1,
                    "component": "operational_persistence",
                    "code": "failed",
                    "reason": "unavailable",
                    "evidence": {},
                },
            ),
            "unsupported component failure schema",
        ),
    ],
)
def test_component_failure_event_rejects_invalid_signal_values(value: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        ComponentFailureEvent.from_signal_value(value)
