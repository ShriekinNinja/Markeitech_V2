from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from markeitech.persistence import (
    NotificationOutboxRecord,
    OutboxStatus,
    PersistenceConfig,
    SignalPersistenceOutcome,
    SQLiteMetadataStore,
)
from markeitech.signals import (
    SignalDirection,
    SignalEvidenceFidelity,
    SignalEvidenceReference,
    SignalEvidenceStage,
    SignalEvidenceType,
    SignalFamily,
    SignalSnapshot,
    SignalStatus,
    SignalTransitionEvent,
    signal_setup_key,
    transition_signal,
)

NOW = datetime(2026, 7, 14, 13, 30, tzinfo=UTC)
OUTBOX_ID = UUID("89710d83-4811-49ab-9d60-3c8d0c8da565")


def config(path: Path) -> PersistenceConfig:
    return PersistenceConfig(
        catalog_path=path.parent / "catalog",
        metadata_path=path,
        journal_path=path.parent / "journal",
    )


def evidence(stage: SignalEvidenceStage) -> SignalEvidenceReference:
    evidence_ids = {
        SignalEvidenceStage.DIRECTION: "d" * 64,
        SignalEvidenceStage.LOCATION: "b" * 64,
        SignalEvidenceStage.AGGRESSION: "a" * 64,
        SignalEvidenceStage.FOLLOW_THROUGH: "f" * 64,
    }
    return SignalEvidenceReference(
        instrument_id="NQU6.CME",
        stage=stage,
        evidence_type=(
            SignalEvidenceType.MARKET_DATA_WINDOW
            if stage == SignalEvidenceStage.AGGRESSION
            else SignalEvidenceType.MARKET_CONTEXT_FEATURE
        ),
        evidence_id=evidence_ids[stage],
        observed_ts=NOW,
        source="market_context" if stage != SignalEvidenceStage.AGGRESSION else "ib",
        fidelity=SignalEvidenceFidelity.INFERRED,
        reason_codes=(f"{stage.value}_confirmed",),
    )


def candidate(**updates: object) -> SignalSnapshot:
    values: dict[str, object] = {
        "algorithm_version": "1.0",
        "configuration_hash": "c" * 64,
        "setup_key": signal_setup_key(
            family=SignalFamily.DIRECTION_LOCATION_AGGRESSION,
            instrument_id="NQU6.CME",
            direction=SignalDirection.LONG,
            anchor="2026-07-14:CME_Equity:prior_value_area_low",
        ),
        "instrument_id": "NQU6.CME",
        "direction": SignalDirection.LONG,
        "created_ts": NOW,
        "updated_ts": NOW,
        "evidence": (evidence(SignalEvidenceStage.DIRECTION),),
        "reason_codes": ("bullish_direction_candidate",),
    }
    values.update(updates)
    return SignalSnapshot(**values)


def armed_event(signal: SignalSnapshot) -> SignalTransitionEvent:
    return transition_signal(
        signal,
        SignalStatus.ARMED,
        occurred_ts=NOW + timedelta(seconds=1),
        reason_codes=("supportive_location_reached",),
        evidence=(evidence(SignalEvidenceStage.LOCATION),),
    )


def notification(
    event: SignalTransitionEvent,
    *,
    outbox_id: UUID = OUTBOX_ID,
    payload: dict[str, object] | None = None,
) -> NotificationOutboxRecord:
    return NotificationOutboxRecord(
        outbox_id=outbox_id,
        topic="signals.lifecycle",
        destination_key="discord.signals.lifecycle",
        aggregate_key=event.signal_id,
        event_type="signal.transition",
        event_schema_version=event.schema_version,
        payload=payload or event.model_dump(mode="json"),
        dedupe_key=f"signal-transition:{event.transition_id}",
        available_ts=event.occurred_ts,
        created_ts=event.occurred_ts,
        updated_ts=event.occurred_ts,
    )


def test_candidate_insert_is_idempotent_and_restores_after_restart(tmp_path: Path) -> None:
    path = tmp_path / "metadata.sqlite3"
    signal = candidate()
    with SQLiteMetadataStore(config(path)) as store:
        assert store.save_signal_candidate(signal) == SignalPersistenceOutcome.CREATED
        assert store.save_signal_candidate(signal) == SignalPersistenceOutcome.DUPLICATE

    with SQLiteMetadataStore(config(path)) as restarted:
        assert restarted.load_signal(signal.signal_id) == signal
        assert restarted.load_signals(instrument_id="NQU6.CME") == (signal,)
        assert restarted.load_signals(status=SignalStatus.ARMED) == ()


def test_same_signal_identity_rejects_different_initial_content(tmp_path: Path) -> None:
    signal = candidate()
    conflicting = candidate(reason_codes=("different_reason",))
    assert conflicting.signal_id == signal.signal_id
    assert conflicting.content_hash != signal.content_hash

    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        store.save_signal_candidate(signal)
        with pytest.raises(ValueError, match="different initial content"):
            store.save_signal_candidate(conflicting)


def test_transition_and_notification_commit_atomically_and_retry_idempotently(
    tmp_path: Path,
) -> None:
    signal = candidate()
    event = armed_event(signal)
    outbound = notification(event)
    path = tmp_path / "metadata.sqlite3"
    with SQLiteMetadataStore(config(path)) as store:
        store.save_signal_candidate(signal)
        assert (
            store.apply_signal_transition(event, notification=outbound)
            == SignalPersistenceOutcome.TRANSITIONED
        )
        assert (
            store.apply_signal_transition(event, notification=outbound)
            == SignalPersistenceOutcome.DUPLICATE
        )
        with pytest.raises(ValueError, match="notification content conflicts"):
            store.apply_signal_transition(
                event,
                notification=notification(event, payload={"changed": True}),
            )
        assert store.save_signal_candidate(signal) == SignalPersistenceOutcome.DUPLICATE

    with SQLiteMetadataStore(config(path)) as restarted:
        assert restarted.load_signal(signal.signal_id) == event.current
        assert restarted.load_signal_transitions(signal.signal_id) == (event,)
        assert restarted.load_outbox(OUTBOX_ID) == outbound


def test_transition_sequence_orders_equal_market_timestamps(tmp_path: Path) -> None:
    signal = candidate()
    armed = armed_event(signal)
    triggered = transition_signal(
        armed.current,
        SignalStatus.TRIGGERED,
        occurred_ts=armed.occurred_ts,
        reason_codes=("aggression_confirmed",),
        evidence=(evidence(SignalEvidenceStage.AGGRESSION),),
    )
    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        store.save_signal_candidate(signal)
        store.apply_signal_transition(armed)
        store.apply_signal_transition(triggered)

        assert store.load_signal_transitions(signal.signal_id) == (armed, triggered)
        assert store.load_signal(signal.signal_id) == triggered.current


def test_transition_retry_accepts_same_notification_after_delivery(tmp_path: Path) -> None:
    signal = candidate()
    event = armed_event(signal)
    outbound = notification(event)
    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        store.save_signal_candidate(signal)
        store.apply_signal_transition(event, notification=outbound)
        leased = store.lease_pending(
            lease_owner="discord-worker",
            now=event.occurred_ts,
            limit=1,
        )[0]
        delivered = store.mark_delivered(
            outbox_id=leased.outbox_id,
            lease_owner="discord-worker",
            delivered_ts=event.occurred_ts + timedelta(seconds=1),
        )

        assert delivered.status == OutboxStatus.DELIVERED
        assert (
            store.apply_signal_transition(event, notification=outbound)
            == SignalPersistenceOutcome.DUPLICATE
        )


def test_competing_transition_from_stale_content_is_rejected(tmp_path: Path) -> None:
    signal = candidate()
    armed = armed_event(signal)
    expired = transition_signal(
        signal,
        SignalStatus.EXPIRED,
        occurred_ts=NOW + timedelta(minutes=5),
        reason_codes=("candidate_timeout",),
    )
    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        store.save_signal_candidate(signal)
        store.apply_signal_transition(armed)

        with pytest.raises(ValueError, match="content hash is stale"):
            store.apply_signal_transition(expired)
        assert store.load_signal(signal.signal_id) == armed.current
        assert store.load_signal_transitions(signal.signal_id) == (armed,)


def test_two_connections_allow_only_one_competing_transition(tmp_path: Path) -> None:
    path = tmp_path / "metadata.sqlite3"
    signal = candidate()
    armed = armed_event(signal)
    expired = transition_signal(
        signal,
        SignalStatus.EXPIRED,
        occurred_ts=NOW + timedelta(minutes=5),
        reason_codes=("candidate_timeout",),
    )
    with SQLiteMetadataStore(config(path)) as setup:
        setup.save_signal_candidate(signal)

    first = SQLiteMetadataStore(config(path))
    second = SQLiteMetadataStore(config(path))
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (
                executor.submit(first.apply_signal_transition, armed),
                executor.submit(second.apply_signal_transition, expired),
            )
            outcomes: list[SignalPersistenceOutcome] = []
            errors: list[Exception] = []
            for future in futures:
                try:
                    outcomes.append(future.result())
                except Exception as exc:  # noqa: BLE001 - asserting one rejected contender
                    errors.append(exc)
    finally:
        first.close()
        second.close()

    assert outcomes == [SignalPersistenceOutcome.TRANSITIONED]
    assert len(errors) == 1
    assert "stale" in str(errors[0])


def test_outbox_conflict_rolls_back_complete_signal_transition(tmp_path: Path) -> None:
    signal = candidate()
    event = armed_event(signal)
    outbound = notification(event)
    conflicting = notification(
        event,
        outbox_id=UUID("8bdfc520-d457-4829-8535-b599317e7b1f"),
        payload={"different": True},
    )
    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        store.save_signal_candidate(signal)
        store.enqueue(conflicting)

        with pytest.raises(ValueError, match="conflicts with existing outbox"):
            store.apply_signal_transition(event, notification=outbound)
        assert store.load_signal(signal.signal_id) == signal
        assert store.load_signal_transitions(signal.signal_id) == ()
        assert store.load_outbox(conflicting.outbox_id) == conflicting


def test_restart_history_read_detects_broken_initial_hash_chain(tmp_path: Path) -> None:
    signal = candidate()
    event = armed_event(signal)
    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        store.save_signal_candidate(signal)
        store.apply_signal_transition(event)
        store._connection.execute(  # noqa: SLF001 - intentional corruption fixture
            "UPDATE signal_snapshots SET initial_content_hash=? WHERE signal_id=?",
            (bytes.fromhex("0" * 64), bytes.fromhex(signal.signal_id)),
        )

        with pytest.raises(ValueError, match="broken content chain"):
            store.load_signal_transitions(signal.signal_id)
        with pytest.raises(ValueError, match="broken content chain"):
            store.load_signal(signal.signal_id)


def test_transition_requires_existing_signal(tmp_path: Path) -> None:
    event = armed_event(candidate())
    with SQLiteMetadataStore(config(tmp_path / "metadata.sqlite3")) as store:
        with pytest.raises(KeyError, match="unknown signal"):
            store.apply_signal_transition(event)
