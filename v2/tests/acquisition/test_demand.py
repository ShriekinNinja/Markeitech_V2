from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from markeitech.acquisition import (
    AcquisitionLifecycleState,
    CapabilityDeclaration,
    CapabilityFeedRequirement,
    CapabilityHistoricalRequirement,
    DemandConflictError,
    DemandOwner,
    DemandOwnerKind,
    DemandReconciler,
    FeedKind,
    FeedRequirement,
    HistoricalWindow,
    ObservationDemand,
)

NOW = datetime(2026, 8, 12, 12, tzinfo=UTC)


def _demand(
    demand_id: str,
    *,
    owner_kind: DemandOwnerKind = DemandOwnerKind.ANALYZER,
    requirement: FeedRequirement | None = None,
    priority: int = 50,
    expires_at: datetime | None = None,
) -> ObservationDemand:
    return ObservationDemand(
        demand_id=demand_id,
        owner=DemandOwner(owner_kind, f"{owner_kind.value}-one"),
        requirement=requirement or FeedRequirement("ESU6.CME", FeedKind.TRADES),
        priority=priority,
        expires_at=expires_at,
        purpose="test demand",
    )


def test_feed_requirement_has_stable_stream_identity_and_immutable_parameters() -> None:
    parameters = {"aggregation_source": "external", "regular_hours": False}
    requirement = FeedRequirement(
        " ESU6.CME ",
        FeedKind.BARS,
        selector="5-MINUTE-LAST",
        parameters=parameters,
    )

    parameters["regular_hours"] = True

    assert requirement.stream_key == ("ESU6.CME", "bars", "5-MINUTE-LAST")
    assert requirement.parameters == {
        "aggregation_source": "external",
        "regular_hours": False,
    }
    with pytest.raises(TypeError):
        requirement.parameters["regular_hours"] = True  # type: ignore[index]


def test_capability_declares_feed_requirements_without_becoming_provider_demand() -> None:
    declaration = CapabilityDeclaration(
        capability_id="trade_response",
        version=1,
        live_feeds=(
            CapabilityFeedRequirement(FeedKind.TRADES),
            CapabilityFeedRequirement(FeedKind.QUOTES),
        ),
        historical_requirements=(
            CapabilityHistoricalRequirement(
                kind=FeedKind.BARS,
                selector="5-MINUTE-LAST",
                window=HistoricalWindow.RECENT_COMPLETED,
                minimum_observations=50,
                maximum_observations=60,
            ),
        ),
    )

    assert declaration.capability_id == "trade_response"
    assert tuple(feed.kind for feed in declaration.live_feeds) == (
        FeedKind.TRADES,
        FeedKind.QUOTES,
    )
    assert declaration.historical_requirements[0].minimum_observations == 50
    assert declaration.live_feeds[0].bind("NQU6.CME") == FeedRequirement(
        "NQU6.CME",
        FeedKind.TRADES,
    )


def test_capability_can_be_historical_only() -> None:
    declaration = CapabilityDeclaration(
        capability_id="daily_reference",
        version=1,
        historical_requirements=(
            CapabilityHistoricalRequirement(
                kind=FeedKind.BARS,
                selector="1-DAY-LAST",
                window=HistoricalWindow.PREVIOUS_RTH,
                minimum_observations=20,
                maximum_observations=20,
            ),
        ),
    )

    assert declaration.live_feeds == ()


def test_reconciles_multiple_consumers_into_one_provider_demand() -> None:
    reconciler = DemandReconciler()
    permanent = _demand("bootstrap-es-trades", owner_kind=DemandOwnerKind.BOOTSTRAP, priority=20)
    focused = _demand(
        "agent-es-trades",
        owner_kind=DemandOwnerKind.AGENT,
        priority=90,
        expires_at=NOW + timedelta(minutes=5),
    )

    assert reconciler.add(permanent, now=NOW) is True
    assert reconciler.add(focused, now=NOW) is True
    assert reconciler.add(focused, now=NOW) is False

    provider_demands = reconciler.provider_demands(now=NOW)

    assert len(provider_demands) == 1
    assert provider_demands[0].consumer_ids == (
        "agent-es-trades",
        "bootstrap-es-trades",
    )
    assert provider_demands[0].priority == 90
    assert provider_demands[0].expires_at is None


def test_removing_one_consumer_preserves_shared_provider_demand() -> None:
    reconciler = DemandReconciler()
    reconciler.add(_demand("analyzer-a"), now=NOW)
    reconciler.add(_demand("analyzer-b"), now=NOW)

    assert reconciler.remove("analyzer-a") is True
    assert reconciler.remove("analyzer-a") is False

    provider_demands = reconciler.provider_demands(now=NOW)
    assert len(provider_demands) == 1
    assert provider_demands[0].consumer_ids == ("analyzer-b",)


def test_distinct_bar_selectors_are_independent_provider_demands() -> None:
    reconciler = DemandReconciler()
    one_minute = FeedRequirement("SPY.ARCA", FeedKind.BARS, selector="1-MINUTE-LAST")
    five_minute = FeedRequirement("SPY.ARCA", FeedKind.BARS, selector="5-MINUTE-LAST")

    reconciler.add(_demand("one-minute", requirement=one_minute), now=NOW)
    reconciler.add(_demand("five-minute", requirement=five_minute), now=NOW)

    assert len(reconciler.provider_demands(now=NOW)) == 2


def test_rejects_incompatible_parameters_for_same_logical_stream() -> None:
    reconciler = DemandReconciler()
    realtime = FeedRequirement(
        "SPY.ARCA",
        FeedKind.QUOTES,
        parameters={"delivery_mode": "realtime"},
    )
    delayed = FeedRequirement(
        "SPY.ARCA",
        FeedKind.QUOTES,
        parameters={"delivery_mode": "delayed"},
    )
    reconciler.add(_demand("realtime", requirement=realtime), now=NOW)

    with pytest.raises(DemandConflictError, match="incompatible parameters"):
        reconciler.add(_demand("delayed", requirement=delayed), now=NOW)


def test_expiry_removes_only_elapsed_demands() -> None:
    reconciler = DemandReconciler()
    reconciler.add(_demand("permanent"), now=NOW)
    reconciler.add(_demand("short", expires_at=NOW + timedelta(seconds=1)), now=NOW)
    reconciler.add(_demand("long", expires_at=NOW + timedelta(minutes=5)), now=NOW)

    expired = reconciler.expire(now=NOW + timedelta(seconds=2))

    assert expired == ("short",)
    assert tuple(demand.demand_id for demand in reconciler.demands) == ("long", "permanent")


def test_rejects_expired_demand_and_duplicate_identity_with_different_meaning() -> None:
    reconciler = DemandReconciler()
    original = _demand("same-id")
    reconciler.add(original, now=NOW)

    with pytest.raises(ValueError, match="expired"):
        reconciler.add(_demand("expired", expires_at=NOW), now=NOW)
    with pytest.raises(DemandConflictError, match="demand_id already exists"):
        reconciler.add(_demand("same-id", priority=99), now=NOW)


def test_owner_kinds_and_lifecycle_vocabulary_are_explicit() -> None:
    assert {kind.value for kind in DemandOwnerKind} == {
        "bootstrap",
        "watchlist",
        "operator",
        "analyzer",
        "agent",
    }
    assert {state.value for state in AcquisitionLifecycleState} == {
        "REQUESTED",
        "ACCEPTED",
        "SUBSCRIBED",
        "ACTIVE",
        "COMPLETED",
        "REJECTED",
        "FAILED",
        "CANCELED",
        "EXPIRED",
    }


@pytest.mark.parametrize(
    "factory, match",
    [
        (lambda: DemandOwner(DemandOwnerKind.AGENT, ""), "owner_id"),
        (lambda: FeedRequirement("", FeedKind.TRADES), "instrument_id"),
        (lambda: _demand("bad-priority", priority=101), "priority"),
        (
            lambda: FeedRequirement(
                "ESU6.CME",
                FeedKind.TRADES,
                parameters={"weight": float("nan")},
            ),
            "non-finite",
        ),
        (
            lambda: _demand(
                "naive-expiry",
                expires_at=datetime(2026, 8, 12, 12),
            ),
            "timezone-aware",
        ),
    ],
)
def test_contracts_reject_ambiguous_values(factory, match: str) -> None:  # noqa: ANN001
    with pytest.raises(ValueError, match=match):
        factory()
