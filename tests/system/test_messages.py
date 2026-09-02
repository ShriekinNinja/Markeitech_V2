from __future__ import annotations

import json

import pytest

from markeitech.system.messages import (
    ACQUISITION_STATUS_SCHEMA_VERSION,
    ACQUISITION_STREAM_SCHEMA_VERSION,
    COMPONENT_FAILURE_SCHEMA_VERSION,
    INSTRUMENTS_READY,
    INSTRUMENTS_RESOLVING,
    PERSISTENCE_READY_SCHEMA_VERSION,
    SYSTEM_HEALTH_SCHEMA_VERSION,
    WATCHLIST_LIFECYCLE_SCHEMA_VERSION,
    WATCHLIST_MEMBERSHIP_SCHEMA_VERSION,
    AcquisitionStatusEvent,
    AcquisitionStatusRequest,
    AcquisitionStreamEvent,
    AnalyticalDemandEvent,
    ComponentFailureEvent,
    PersistenceReadyEvent,
    PersistenceReadyRequest,
    SystemHealthEvent,
    WatchlistDemandEvent,
    WatchlistLifecycleEvent,
    WatchlistMember,
    WatchlistMembershipEvent,
)


def test_watchlist_demand_round_trip_and_validation() -> None:
    event = WatchlistDemandEvent(
        demand_id="watchlist:1:ESU6.CME/quotes/default",
        action="REQUEST",
        instrument_id="ESU6.CME",
        capability="top_of_book",
        feed_kind="quotes",
        selector="default",
        owner_id="config:system",
        purpose="static watchlist top_of_book",
    )

    assert WatchlistDemandEvent.from_signal_value(event.to_signal_value()) == event
    with pytest.raises(ValueError, match="unsupported watchlist demand action"):
        WatchlistDemandEvent(
            demand_id=event.demand_id,
            action="MAYBE",
            instrument_id=event.instrument_id,
            capability=event.capability,
            feed_kind=event.feed_kind,
            selector=event.selector,
            owner_id=event.owner_id,
            purpose=event.purpose,
        )


def test_analytical_demand_round_trip_and_validation() -> None:
    event = AnalyticalDemandEvent(
        demand_id="metric:quote-quality:ESU6.CME:quotes:default",
        action="REQUEST",
        instrument_id="ESU6.CME",
        capability_id="metric:quote-quality",
        capability_version=1,
        feed_kind="quotes",
        selector="default",
        owner_id="QUOTE-QUALITY-METRICS",
        purpose="calculate bounded quote-quality metrics",
    )

    assert AnalyticalDemandEvent.from_signal_value(event.to_signal_value()) == event
    with pytest.raises(ValueError, match="capability_version"):
        AnalyticalDemandEvent(
            demand_id=event.demand_id,
            action=event.action,
            instrument_id=event.instrument_id,
            capability_id=event.capability_id,
            capability_version=0,
            feed_kind=event.feed_kind,
            selector=event.selector,
            owner_id=event.owner_id,
            purpose=event.purpose,
        )


def test_persistence_readiness_contracts_round_trip() -> None:
    request = PersistenceReadyRequest(requester=" WATCHLIST ")
    ready = PersistenceReadyEvent(
        source=" OPERATIONAL-PERSISTENCE ",
        run_id="36a468b3-df4b-49fa-809e-c60e8d19d9a0",
    )

    assert PersistenceReadyRequest.from_signal_value(request.to_signal_value()) == request
    assert PersistenceReadyEvent.from_signal_value(ready.to_signal_value()) == ready
    assert ready.schema_version == PERSISTENCE_READY_SCHEMA_VERSION


def test_persistence_readiness_contracts_reject_unknown_fields() -> None:
    payload = json.loads(PersistenceReadyRequest(requester="WATCHLIST").to_signal_value())
    payload["unexpected"] = True

    with pytest.raises(ValueError, match="unknown"):
        PersistenceReadyRequest.from_signal_value(json.dumps(payload))


def test_watchlist_membership_round_trips_with_sorted_effective_members() -> None:
    event = WatchlistMembershipEvent(
        event_id="watchlist-membership:1",
        membership_revision=1,
        source="WATCHLIST",
        reason="configured baseline established",
        members=(
            WatchlistMember(
                instrument_id="SPY.ARCA",
                calendar_id="us_equities",
                capabilities=("watchlist_last", "top_of_book"),
                owner_ids=("config:system",),
            ),
            WatchlistMember(
                instrument_id="ESU6.CME",
                calendar_id="cme_equity",
                capabilities=("top_of_book", "watchlist_last"),
                owner_ids=("config:system",),
            ),
        ),
    )

    encoded = event.to_signal_value()
    decoded = WatchlistMembershipEvent.from_signal_value(encoded)

    assert decoded == event
    assert decoded.schema_version == WATCHLIST_MEMBERSHIP_SCHEMA_VERSION
    assert [member.instrument_id for member in decoded.members] == ["ESU6.CME", "SPY.ARCA"]
    assert decoded.members[0].capabilities == ("top_of_book", "watchlist_last")


def test_watchlist_membership_rejects_duplicate_instruments_and_empty_ownership() -> None:
    member = WatchlistMember(
        instrument_id="ESU6.CME",
        calendar_id="cme_equity",
        capabilities=("top_of_book",),
        owner_ids=("config:system",),
    )
    with pytest.raises(ValueError, match="duplicate instruments"):
        WatchlistMembershipEvent(
            event_id="watchlist-membership:1",
            membership_revision=1,
            source="WATCHLIST",
            reason="invalid duplicate",
            members=(member, member),
        )
    with pytest.raises(ValueError, match="owner_ids must not be empty"):
        WatchlistMember(
            instrument_id="ESU6.CME",
            calendar_id="cme_equity",
            capabilities=("top_of_book",),
            owner_ids=(),
        )


def test_watchlist_lifecycle_round_trips_with_audit_identity() -> None:
    event = WatchlistLifecycleEvent(
        event_id="watchlist-lifecycle:7",
        membership_revision=1,
        state="INSTRUMENT_OBSERVED",
        source="WATCHLIST",
        reason="required quote and bar-derived last observed",
        instrument_id="ESU6.CME",
        owner_id="config:system",
        correlation_id="watchlist-membership:1",
    )

    encoded = event.to_signal_value()

    assert WatchlistLifecycleEvent.from_signal_value(encoded) == event
    assert json.loads(encoded)["schema_version"] == WATCHLIST_LIFECYCLE_SCHEMA_VERSION


def test_watchlist_lifecycle_rejects_unknown_state_and_incomplete_observation() -> None:
    values = {
        "event_id": "watchlist-lifecycle:7",
        "membership_revision": 1,
        "source": "WATCHLIST",
        "reason": "test",
    }
    with pytest.raises(ValueError, match="unsupported watchlist lifecycle state"):
        WatchlistLifecycleEvent(state="MAYBE_ACTIVE", **values)
    with pytest.raises(ValueError, match="requires instrument_id"):
        WatchlistLifecycleEvent(state="INSTRUMENT_OBSERVED", **values)


def test_watchlist_contracts_reject_unknown_fields_and_schema_versions() -> None:
    lifecycle = WatchlistLifecycleEvent(
        event_id="watchlist-lifecycle:1",
        membership_revision=1,
        state="CONFIGURED",
        source="WATCHLIST",
        reason="baseline configured",
    )
    payload = json.loads(lifecycle.to_signal_value())
    payload["unexpected"] = True
    with pytest.raises(ValueError, match="unknown"):
        WatchlistLifecycleEvent.from_signal_value(json.dumps(payload))

    payload.pop("unexpected")
    payload["schema_version"] = WATCHLIST_LIFECYCLE_SCHEMA_VERSION + 1
    with pytest.raises(ValueError, match="unsupported watchlist lifecycle schema"):
        WatchlistLifecycleEvent.from_signal_value(json.dumps(payload))


def test_acquisition_stream_event_round_trips_with_demand_identity() -> None:
    event = AcquisitionStreamEvent(
        state="SUBSCRIBED",
        instrument_id="ESU6.CME",
        feed_kind="trades",
        selector="default",
        source="DATA-ACQUISITION",
        demand_id="bootstrap:0:ESU6.CME/trades/default",
        consumer_ids=("bootstrap:0:ESU6.CME/trades/default",),
        detail="native subscription command issued",
    )

    encoded = event.to_signal_value()

    assert AcquisitionStreamEvent.from_signal_value(encoded) == event
    assert json.loads(encoded)["schema_version"] == ACQUISITION_STREAM_SCHEMA_VERSION


def test_acquisition_stream_event_allows_stream_level_event_without_demand_id() -> None:
    event = AcquisitionStreamEvent(
        state="ACTIVE",
        instrument_id="SPY.ARCA",
        feed_kind="quotes",
        selector="default",
        source="DATA-ACQUISITION",
        demand_id=None,
        consumer_ids=("bootstrap:2:SPY.ARCA/quotes/default",),
        detail="first native observation received",
    )

    assert AcquisitionStreamEvent.from_signal_value(event.to_signal_value()) == event


def test_acquisition_stream_event_rejects_unknown_lifecycle_state() -> None:
    with pytest.raises(ValueError, match="unsupported acquisition stream state"):
        AcquisitionStreamEvent(
            state="FLOWING_MAYBE",
            instrument_id="SPY.ARCA",
            feed_kind="quotes",
            selector="default",
            source="DATA-ACQUISITION",
            demand_id=None,
            consumer_ids=(),
            detail="ambiguous lifecycle",
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
