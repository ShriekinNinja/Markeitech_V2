from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from types import MappingProxyType

import pytest

from markeitech.acquisition import (
    FeedKind,
    HistoricalDependencyRef,
    HistoricalRequest,
    HistoricalWindow,
    NautilusHistoricalPort,
)
from markeitech.acquisition.historical_native import (
    HistoricalResponseMismatch,
    validate_historical_bars,
)


class RecordingActor:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object, object, object, object, object]] = []

    def request_bars(self, bar_type, start=None, end=None, limit=None, client_id=None, params=None):
        self.calls.append((bar_type, start, end, limit, client_id, params))


@dataclass(frozen=True)
class StubBar:
    bar_type: object
    ts_event: int


def test_native_port_preserves_bar_type_start_and_limit() -> None:
    actor = RecordingActor()
    port = NautilusHistoricalPort(actor)
    request = HistoricalRequest(
        request_id="historical:1",
        instrument_id="ESU6.CME",
        kind=FeedKind.BARS,
        selector="1-MINUTE-LAST-EXTERNAL",
        window=HistoricalWindow.RECENT_COMPLETED,
        start_ns=60_000_000_000,
        end_ns=120_000_000_000,
        limit=10,
        priority=10,
        parameters=MappingProxyType({"source": "acceptance"}),
        dependencies=(
            HistoricalDependencyRef(
                consumer_id="probe",
                capability_id="probe",
                capability_version=1,
                requirement_index=0,
                minimum_observations=5,
                purpose="acceptance",
            ),
        ),
    )

    port.submit(request)

    bar_type, start, end, limit, client_id, params = actor.calls[0]
    assert str(bar_type) == "ESU6.CME-1-MINUTE-LAST-EXTERNAL"
    assert start.tzinfo is UTC
    assert end.tzinfo is UTC
    assert start.isoformat() == "1970-01-01T00:01:00+00:00"
    assert end.isoformat() == "1970-01-01T00:02:00+00:00"
    assert limit == 10
    assert str(client_id) == "IB"
    assert params == {"source": "acceptance"}


def test_native_port_submits_completed_exclusive_end_boundary() -> None:
    actor = RecordingActor()
    port = NautilusHistoricalPort(actor)
    request = _request(start_ns=60_000_000_000, end_ns=119_999_999_999)

    port.submit(request)

    _, _, end, _, _, _ = actor.calls[0]
    assert end.isoformat() == "1970-01-01T00:02:00+00:00"


def test_native_port_submits_exact_five_minute_completed_window() -> None:
    actor = RecordingActor()
    port = NautilusHistoricalPort(actor)
    minute_ns = 60_000_000_000
    request = _request(
        start_ns=49 * minute_ns,
        end_ns=54 * minute_ns - 1,
    )

    port.submit(request)

    _, start, end, _, _, _ = actor.calls[0]
    assert start.isoformat() == "1970-01-01T00:49:00+00:00"
    assert end.isoformat() == "1970-01-01T00:54:00+00:00"
    assert request.end_ns == 54 * minute_ns - 1


def test_native_port_rejects_timestamp_outside_datetime_range() -> None:
    actor = RecordingActor()
    port = NautilusHistoricalPort(actor)
    request = _request(start_ns=60_000_000_000, end_ns=10**30)

    with pytest.raises(ValueError, match="outside datetime range"):
        port.submit(request)

    assert actor.calls == []


def test_historical_response_matches_requested_contract() -> None:
    request = _request(start_ns=60_000_000_000, end_ns=179_999_999_999)
    bar_type = "ESU6.CME-1-MINUTE-LAST-EXTERNAL"

    validate_historical_bars(
        request,
        (
            StubBar(bar_type, 120_000_000_000),
            StubBar(bar_type, 180_000_000_000),
        ),
    )


@pytest.mark.parametrize(
    ("observations", "reason"),
    [
        ((StubBar("NQU6.CME-1-MINUTE-LAST-EXTERNAL", 120_000_000_000),), "bar type"),
        (
            (
                StubBar("ESU6.CME-1-MINUTE-LAST-EXTERNAL", 120_000_000_000),
                StubBar("ESU6.CME-1-MINUTE-LAST-EXTERNAL", 120_000_000_000),
            ),
            "duplicate or unordered",
        ),
        ((StubBar("ESU6.CME-1-MINUTE-LAST-EXTERNAL", 1),), "outside"),
    ],
)
def test_historical_response_rejects_mismatched_data(
    observations: tuple[StubBar, ...],
    reason: str,
) -> None:
    with pytest.raises(HistoricalResponseMismatch, match=reason):
        validate_historical_bars(
            _request(start_ns=60_000_000_000, end_ns=179_999_999_999),
            observations,
        )


def _request(*, start_ns: int, end_ns: int) -> HistoricalRequest:
    return HistoricalRequest(
        request_id="historical:test",
        instrument_id="ESU6.CME",
        kind=FeedKind.BARS,
        selector="1-MINUTE-LAST-EXTERNAL",
        window=HistoricalWindow.RECENT_COMPLETED,
        start_ns=start_ns,
        end_ns=end_ns,
        limit=10,
        priority=10,
        parameters=MappingProxyType({}),
        dependencies=(
            HistoricalDependencyRef(
                consumer_id="probe",
                capability_id="probe",
                capability_version=1,
                requirement_index=0,
                minimum_observations=1,
                purpose="acceptance",
            ),
        ),
    )
