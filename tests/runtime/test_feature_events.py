from datetime import UTC, datetime
from types import SimpleNamespace

from markeitech.runtime import BoundedEventLoopBridge, FeatureCommitEventFanout
from markeitech.runtime.events import MarkeitechBusTopic
from markeitech.runtime.feature_events import feature_committed_event

COMMITTED_TS = datetime(2026, 7, 16, 9, 30, tzinfo=UTC)


def revision(sequence: int = 7):
    snapshot = SimpleNamespace(
        instrument_id="NQU6.CME",
        timeframe=SimpleNamespace(value="1m"),
    )
    feature = SimpleNamespace(
        feature_set="market_context",
        feature_id="feature-abc",
        snapshot=snapshot,
    )
    return SimpleNamespace(
        feature=feature,
        committed_ts=COMMITTED_TS,
        commit_sequence=sequence,
    )


def test_feature_revision_maps_to_stable_committed_notice() -> None:
    event = feature_committed_event(revision())

    assert event.topic == MarkeitechBusTopic.FEATURE_COMMITTED
    assert event.event_id == "feature-committed:7:feature-abc"
    assert event.aggregate_id == "NQU6.CME:market_context:1m"
    assert event.payload_id == "feature-abc"
    assert event.instrument_id == "NQU6.CME"
    assert event.commit_sequence == 7


def test_bus_rejection_is_accounted_without_rejecting_durable_commit() -> None:
    bridge = BoundedEventLoopBridge(1)
    fanout = FeatureCommitEventFanout(bridge)

    assert fanout.offer((revision(1),))
    assert fanout.offer((revision(2),))

    assert fanout.snapshot.offered_count == 2
    assert fanout.snapshot.rejected_count == 1
    assert fanout.snapshot.last_rejection == "queue_full"


def test_critical_handoff_rejection_prevents_bus_offer() -> None:
    bridge = BoundedEventLoopBridge(1)
    fanout = FeatureCommitEventFanout(bridge, critical_sink=lambda _values: False)

    assert not fanout.offer((revision(),))
    assert bridge.snapshot.pending_count == 0
    assert fanout.snapshot.offered_count == 0
