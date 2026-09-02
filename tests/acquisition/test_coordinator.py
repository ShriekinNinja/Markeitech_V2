from __future__ import annotations

from datetime import UTC, datetime, timedelta

from markeitech.acquisition import (
    AcquisitionCoordinator,
    AcquisitionLifecycleState,
    DemandOwner,
    DemandOwnerKind,
    FeedKind,
    FeedRequirement,
    ObservationDemand,
)

NOW = datetime(2026, 8, 12, 15, tzinfo=UTC)


class RecordingSubscriptionPort:
    def __init__(self) -> None:
        self.subscribed: list[FeedRequirement] = []
        self.unsubscribed: list[FeedRequirement] = []
        self.fail_subscribe = False
        self.fail_unsubscribe = False

    def subscribe(self, requirement: FeedRequirement) -> None:
        if self.fail_subscribe:
            raise RuntimeError("subscribe unavailable")
        self.subscribed.append(requirement)

    def unsubscribe(self, requirement: FeedRequirement) -> None:
        if self.fail_unsubscribe:
            raise RuntimeError("unsubscribe unavailable")
        self.unsubscribed.append(requirement)


def _demand(demand_id: str, *, expires_at: datetime | None = None) -> ObservationDemand:
    return ObservationDemand(
        demand_id=demand_id,
        owner=DemandOwner(DemandOwnerKind.ANALYZER, demand_id),
        requirement=FeedRequirement("ESU6.CME", FeedKind.TRADES),
        expires_at=expires_at,
        purpose="coordinator test",
    )


def test_shared_consumers_create_one_subscription_and_last_cancel_stops_it() -> None:
    port = RecordingSubscriptionPort()
    coordinator = AcquisitionCoordinator(port)

    first = coordinator.request(_demand("consumer-a"), now=NOW)
    second = coordinator.request(_demand("consumer-b"), now=NOW)

    assert [event.state for event in first] == [
        AcquisitionLifecycleState.REQUESTED,
        AcquisitionLifecycleState.ACCEPTED,
        AcquisitionLifecycleState.SUBSCRIBED,
    ]
    assert [event.state for event in second] == [
        AcquisitionLifecycleState.REQUESTED,
        AcquisitionLifecycleState.ACCEPTED,
    ]
    assert len(port.subscribed) == 1
    assert coordinator.subscribed_provider_demands[0].consumer_ids == (
        "consumer-a",
        "consumer-b",
    )

    assert [event.state for event in coordinator.cancel("consumer-a", now=NOW)] == [
        AcquisitionLifecycleState.CANCELED,
    ]
    assert port.unsubscribed == []
    assert [event.state for event in coordinator.cancel("consumer-b", now=NOW)] == [
        AcquisitionLifecycleState.CANCELED,
        AcquisitionLifecycleState.COMPLETED,
    ]
    assert len(port.unsubscribed) == 1


def test_expiration_preserves_subscription_until_last_consumer_expires() -> None:
    port = RecordingSubscriptionPort()
    coordinator = AcquisitionCoordinator(port)
    coordinator.request(_demand("short", expires_at=NOW + timedelta(seconds=1)), now=NOW)
    coordinator.request(_demand("long", expires_at=NOW + timedelta(seconds=2)), now=NOW)

    first = coordinator.expire(now=NOW + timedelta(milliseconds=1500))
    second = coordinator.expire(now=NOW + timedelta(seconds=3))

    assert [event.state for event in first] == [AcquisitionLifecycleState.EXPIRED]
    assert [event.state for event in second] == [
        AcquisitionLifecycleState.EXPIRED,
        AcquisitionLifecycleState.COMPLETED,
    ]
    assert len(port.subscribed) == 1
    assert len(port.unsubscribed) == 1


def test_failed_subscribe_is_not_recorded_active_and_can_be_retried() -> None:
    port = RecordingSubscriptionPort()
    port.fail_subscribe = True
    coordinator = AcquisitionCoordinator(port)

    events = coordinator.request(_demand("consumer"), now=NOW)

    assert events[-1].state is AcquisitionLifecycleState.FAILED
    assert events[-1].detail == "provider subscribe failed: RuntimeError"
    assert coordinator.subscribed_provider_demands == ()
    assert len(coordinator.demands) == 1

    port.fail_subscribe = False
    assert [event.state for event in coordinator.reconcile(now=NOW)] == [
        AcquisitionLifecycleState.SUBSCRIBED,
    ]


def test_failed_unsubscribe_remains_active_for_retry() -> None:
    port = RecordingSubscriptionPort()
    coordinator = AcquisitionCoordinator(port)
    coordinator.request(_demand("consumer"), now=NOW)
    port.fail_unsubscribe = True

    events = coordinator.cancel("consumer", now=NOW)

    assert [event.state for event in events] == [
        AcquisitionLifecycleState.CANCELED,
        AcquisitionLifecycleState.FAILED,
    ]
    assert len(coordinator.subscribed_provider_demands) == 1

    port.fail_unsubscribe = False
    assert [event.state for event in coordinator.reconcile(now=NOW)] == [
        AcquisitionLifecycleState.COMPLETED,
    ]
    assert coordinator.subscribed_provider_demands == ()


def test_duplicate_request_is_idempotent_and_retries_only_when_not_active() -> None:
    port = RecordingSubscriptionPort()
    coordinator = AcquisitionCoordinator(port)
    demand = _demand("consumer")

    coordinator.request(demand, now=NOW)
    events = coordinator.request(demand, now=NOW)

    assert [event.state for event in events] == [AcquisitionLifecycleState.REQUESTED]
    assert len(port.subscribed) == 1

    failed_port = RecordingSubscriptionPort()
    failed_port.fail_subscribe = True
    pending = AcquisitionCoordinator(failed_port)
    pending.request(demand, now=NOW)
    failed_port.fail_subscribe = False

    assert [event.state for event in pending.request(demand, now=NOW)] == [
        AcquisitionLifecycleState.REQUESTED,
        AcquisitionLifecycleState.SUBSCRIBED,
    ]


def test_changed_requirement_waits_for_successful_old_unsubscribe() -> None:
    port = RecordingSubscriptionPort()
    coordinator = AcquisitionCoordinator(port)
    old = _demand("old")
    coordinator.request(old, now=NOW)
    port.fail_unsubscribe = True
    coordinator.cancel("old", now=NOW)

    changed = ObservationDemand(
        demand_id="changed",
        owner=DemandOwner(DemandOwnerKind.ANALYZER, "changed"),
        requirement=FeedRequirement(
            "ESU6.CME",
            FeedKind.TRADES,
            parameters={"delivery_mode": "delayed"},
        ),
        purpose="changed provider parameters",
    )
    events = coordinator.request(changed, now=NOW)

    assert events[-1].state is AcquisitionLifecycleState.FAILED
    assert len(port.subscribed) == 1
    assert coordinator.subscribed_provider_demands[0].requirement == old.requirement

    port.fail_unsubscribe = False
    events = coordinator.reconcile(now=NOW)

    assert [event.state for event in events] == [
        AcquisitionLifecycleState.COMPLETED,
        AcquisitionLifecycleState.SUBSCRIBED,
    ]
    assert len(port.subscribed) == 2
    assert coordinator.subscribed_provider_demands[0].requirement == changed.requirement


def test_first_native_observation_is_the_only_transition_to_active() -> None:
    port = RecordingSubscriptionPort()
    coordinator = AcquisitionCoordinator(port)
    demand = _demand("consumer")
    events = coordinator.request(demand, now=NOW)

    assert events[-1].state is AcquisitionLifecycleState.SUBSCRIBED
    first = coordinator.observe(demand.requirement.stream_key)

    assert first is not None
    assert first.state is AcquisitionLifecycleState.ACTIVE
    assert first.detail == "first native observation received"
    assert coordinator.observe(demand.requirement.stream_key) is None
    assert coordinator.observe(("SPY.ARCA", "quotes", "default")) is None
