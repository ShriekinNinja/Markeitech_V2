from __future__ import annotations

from dataclasses import replace
from uuid import UUID

import pytest

from markeitech.intelligence import CompletedBarSeriesIdentity, MetricSubjectIdentity
from markeitech.intelligence.metric_producer_manifest import (
    CONSUMER_READINESS_TIMEOUT_MS,
    _AcknowledgementDisposition,
    _ActivationDisposition,
    _BarSeriesProducerClaim,
    _FoundationInstanceAssignment,
    _MetricProducerClaim,
    _ProducerManifestV1,
    _StartupConsumerRequirement,
    _StartupReadinessValidator,
    _SubscriptionReadinessAcknowledgement,
    _SubscriptionReadinessStatus,
)

SECOND_NS = 1_000_000_000
CONFIGURATION_EPOCH = UUID("11111111-1111-1111-1111-111111111111")
STARTUP_EPOCH = UUID("22222222-2222-2222-2222-222222222222")


def _series(series_id: str = "es_1m") -> CompletedBarSeriesIdentity:
    return CompletedBarSeriesIdentity(
        instrument_id="ESU6.CME",
        venue="CME",
        provider_id="IB",
        adapter_id="nautilus-ib",
        source_stream_id="watchlist-last-5s",
        source_selector="ESU6.CME-5-SECOND-LAST-EXTERNAL",
        canonical_bar_specification="ESU6.CME-1-MINUTE-LAST-EXTERNAL",
        interval_ns=60 * SECOND_NS,
        aggregation_policy="contiguous-fixed-interval",
        timestamp_policy="interval_end",
        completion_policy="closed-interval-complete-or-partial",
        revision_policy="reject",
        calendar_id="cme_equity",
        calendar_definition_version=4,
        calendar_definition_digest="a" * 64,
        calendar_definition_effective_from_ns=SECOND_NS,
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        configuration_epoch=CONFIGURATION_EPOCH,
        configuration_digest="b" * 64,
        canonical_producer_id="COMPLETED-BARS-1",
        output_schema_version=1,
        series_id=series_id,
    )


def _subject(metric_id: str = "completed_bar.close") -> MetricSubjectIdentity:
    return MetricSubjectIdentity(
        metric_id=metric_id,
        metric_version=1,
        parameter_version=1,
        parameter_effective_from_ns=SECOND_NS,
        parameter_epoch=UUID("33333333-3333-3333-3333-333333333333"),
        configuration_epoch=CONFIGURATION_EPOCH,
        configuration_digest="b" * 64,
        instrument_id="ESU6.CME",
        output_schema_version=2,
        canonical_producer_id="COMPLETED-BAR-METRICS",
        input_series_id="es_1m",
        calendar_id="cme_equity",
        calendar_definition_version=4,
        calendar_definition_digest="a" * 64,
        calendar_definition_effective_from_ns=SECOND_NS,
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
    )


def _bar_claim(series_id: str = "es_1m") -> _BarSeriesProducerClaim:
    return _BarSeriesProducerClaim(
        series_identity=_series(series_id),
        producer_actor_id="COMPLETED-BARS-1",
        producer_version=1,
        output_schema_version=1,
        dependencies=("watchlist",),
        activation=_ActivationDisposition.ENABLED,
        maximum_retained_completed_bars=16,
        maximum_history_live_overlap_bars=1,
        maximum_buffered_live_completed_bars=2,
    )


def _metric_claim(
    claim_id: str = "completed-bar-close",
    *,
    subject: MetricSubjectIdentity | None = None,
    dependencies: tuple[str, ...] = (),
    activation: _ActivationDisposition = _ActivationDisposition.ENABLED,
) -> _MetricProducerClaim:
    return _MetricProducerClaim(
        claim_id=claim_id,
        subject=_subject() if subject is None else subject,
        producer_actor_id="COMPLETED-BAR-METRICS",
        producer_version=1,
        output_schema_version=2,
        input_series_ids=("es_1m",),
        dependency_claim_ids=dependencies,
        parameter_set_id="completed-bar-v1",
        activation=activation,
    )


def _manifest() -> _ProducerManifestV1:
    return _ProducerManifestV1(
        configuration_epoch=CONFIGURATION_EPOCH,
        configuration_digest="b" * 64,
        instance_assignments=(_FoundationInstanceAssignment("COMPLETED-BARS-1", ("es_1m",)),),
        bar_claims=(_bar_claim(),),
        metric_claims=(_metric_claim(),),
    )


def test_manifest_is_deterministic_and_contains_only_derived_sorted_authority() -> None:
    first = _manifest()
    second = _manifest()

    assert first.manifest_digest == second.manifest_digest
    assert first.to_bytes() == second.to_bytes()
    assert first.to_dict()["bar_claims"][0]["series_identity_digest"] == _series().identity_digest


def test_partition_validation_rejects_duplicate_unknown_and_unassigned_series() -> None:
    with pytest.raises(ValueError, match="more than one instance"):
        replace(
            _manifest(),
            instance_assignments=(
                _FoundationInstanceAssignment("COMPLETED-BARS-1", ("es_1m",)),
                _FoundationInstanceAssignment("COMPLETED-BARS-2", ("es_1m",)),
            ),
        )
    with pytest.raises(ValueError, match="unassigned"):
        replace(_manifest(), instance_assignments=())
    with pytest.raises(ValueError, match="unknown or disabled"):
        replace(
            _manifest(),
            instance_assignments=(
                _FoundationInstanceAssignment("COMPLETED-BARS-1", ("es_1m", "unknown")),
            ),
        )


def test_partition_validation_enforces_instance_and_total_series_ceilings() -> None:
    with pytest.raises(ValueError, match="more than 16"):
        _FoundationInstanceAssignment(
            "COMPLETED-BARS-1",
            tuple(f"series_{index:02d}" for index in range(17)),
        )

    claims = tuple(_bar_claim(f"series_{index:02d}") for index in range(65))
    assignments = tuple(
        _FoundationInstanceAssignment(
            f"COMPLETED-BARS-{partition + 1}",
            tuple(
                f"series_{index:02d}"
                for index in range(partition * 16, min(65, (partition + 1) * 16))
            ),
        )
        for partition in range(5)
    )
    with pytest.raises(ValueError, match="64-series"):
        _ProducerManifestV1(
            configuration_epoch=CONFIGURATION_EPOCH,
            configuration_digest="b" * 64,
            instance_assignments=assignments,
            bar_claims=claims,
            metric_claims=(),
        )


@pytest.mark.parametrize(
    ("field_name", "value", "ceiling"),
    (
        ("maximum_retained_completed_bars", 10_000, 16),
        ("maximum_history_live_overlap_bars", 10_000, 1),
        ("maximum_buffered_live_completed_bars", 10_000, 2),
    ),
)
def test_bar_claim_resource_values_cannot_exceed_slice_1_ceilings(
    field_name: str,
    value: int,
    ceiling: int,
) -> None:
    with pytest.raises(ValueError, match=f"ceiling of {ceiling}"):
        replace(_bar_claim(), **{field_name: value})


def test_metric_claims_reject_complete_subject_overlap_missing_series_and_cycles() -> None:
    duplicate = replace(_metric_claim(), claim_id="duplicate-close")
    with pytest.raises(ValueError, match="overlap"):
        replace(_manifest(), metric_claims=(_metric_claim(), duplicate))

    missing_series_claim = replace(
        _metric_claim(),
        subject=replace(_subject(), input_series_id="missing"),
        input_series_ids=("missing",),
    )
    with pytest.raises(ValueError, match="missing input series"):
        replace(_manifest(), metric_claims=(missing_series_claim,))

    first = _metric_claim("first", dependencies=("second",))
    second = _metric_claim(
        "second",
        subject=replace(_subject(), metric_id="completed_bar.high"),
        dependencies=("first",),
    )
    with pytest.raises(ValueError, match="acyclic"):
        replace(_manifest(), metric_claims=(first, second))

    shadow_dependency = _metric_claim(
        "shadow",
        subject=replace(_subject(), metric_id="completed_bar.high"),
        activation=_ActivationDisposition.SHADOW,
    )
    enabled_dependent = _metric_claim(dependencies=("shadow",))
    with pytest.raises(ValueError, match="enabled dependency"):
        replace(_manifest(), metric_claims=(enabled_dependent, shadow_dependency))


def _requirements() -> tuple[_StartupConsumerRequirement, ...]:
    return (
        _StartupConsumerRequirement("COMPLETED-BAR-METRICS", "es_1m", "COMPLETED-BARS-1"),
        _StartupConsumerRequirement("ROLLING-MEASUREMENTS", "es_1m", "COMPLETED-BARS-1"),
    )


def _ack(
    consumer: str,
    manifest_digest: str,
    *,
    status: _SubscriptionReadinessStatus = _SubscriptionReadinessStatus.SUBSCRIBED,
    reason: str | None = None,
    timestamp: int = SECOND_NS + 1,
) -> _SubscriptionReadinessAcknowledgement:
    return _SubscriptionReadinessAcknowledgement(
        startup_epoch=STARTUP_EPOCH,
        consumer_actor_id=consumer,
        series_id="es_1m",
        manifest_digest=manifest_digest,
        status=status,
        acknowledged_ts_ns=timestamp,
        reason=reason,
    )


def _barrier() -> _StartupReadinessValidator:
    return _StartupReadinessValidator(
        requirements=_requirements(),
        startup_epoch=STARTUP_EPOCH,
        manifest_digest=_manifest().manifest_digest,
        started_at_ns=SECOND_NS,
        timeout_ms=CONSUMER_READINESS_TIMEOUT_MS,
    )


def test_readiness_seals_immediately_after_every_exact_pair_subscribes() -> None:
    barrier = _barrier()
    manifest_digest = _manifest().manifest_digest

    assert barrier.acknowledge(_ack("COMPLETED-BAR-METRICS", manifest_digest)) is (
        _AcknowledgementDisposition.ACCEPTED
    )
    waiting = barrier.evaluate(now_ns=SECOND_NS + 2)
    assert waiting.sealed is False
    assert waiting.demand_series_ids == ()
    assert barrier.acknowledge(_ack("ROLLING-MEASUREMENTS", manifest_digest)) is (
        _AcknowledgementDisposition.ACCEPTED
    )
    sealed = barrier.evaluate(now_ns=SECOND_NS + 3)

    assert sealed.sealed is True
    assert sealed.demand_series_ids == ("es_1m",)
    assert sealed.quarantined_pairs == ()


def test_readiness_timeout_quarantines_only_missing_and_rejects_late_ack() -> None:
    barrier = _barrier()
    manifest_digest = _manifest().manifest_digest
    barrier.acknowledge(_ack("COMPLETED-BAR-METRICS", manifest_digest))

    decision = barrier.evaluate(now_ns=SECOND_NS + 5 * SECOND_NS)

    assert decision.sealed is True
    assert decision.demand_series_ids == ("es_1m",)
    assert decision.quarantined_pairs == (("ROLLING-MEASUREMENTS", "es_1m"),)
    assert barrier.acknowledge(_ack("ROLLING-MEASUREMENTS", manifest_digest)) is (
        _AcknowledgementDisposition.LATE_REJECTED
    )


def test_readiness_ack_at_the_exact_deadline_is_late_and_seals_at_deadline() -> None:
    barrier = _barrier()

    assert (
        barrier.acknowledge(
            _ack(
                "COMPLETED-BAR-METRICS",
                _manifest().manifest_digest,
                timestamp=SECOND_NS + 5 * SECOND_NS,
            ),
        )
        is _AcknowledgementDisposition.LATE_REJECTED
    )
    decision = barrier.evaluate(now_ns=SECOND_NS + 5 * SECOND_NS)

    assert decision.sealed is True
    assert decision.sealed_at_ns == SECOND_NS + 5 * SECOND_NS
    assert decision.demand_series_ids == ()


def test_readiness_is_idempotent_and_conflict_quarantines_one_pair() -> None:
    barrier = _barrier()
    manifest_digest = _manifest().manifest_digest
    acknowledgement = _ack("COMPLETED-BAR-METRICS", manifest_digest)

    assert barrier.acknowledge(acknowledgement) is _AcknowledgementDisposition.ACCEPTED
    assert barrier.acknowledge(acknowledgement) is _AcknowledgementDisposition.DUPLICATE
    conflicting = _ack(
        "COMPLETED-BAR-METRICS",
        manifest_digest,
        status=_SubscriptionReadinessStatus.REJECTED,
        reason="subscription_rejected",
    )
    assert barrier.acknowledge(conflicting) is _AcknowledgementDisposition.CONFLICT
    barrier.acknowledge(_ack("ROLLING-MEASUREMENTS", manifest_digest))

    decision = barrier.evaluate(now_ns=SECOND_NS + 2)

    assert decision.sealed is True
    assert decision.subscribed_pairs == (("ROLLING-MEASUREMENTS", "es_1m"),)
    assert decision.quarantined_pairs == (("COMPLETED-BAR-METRICS", "es_1m"),)


def test_zero_subscribed_consumers_produce_no_demand() -> None:
    barrier = _barrier()
    digest_value = _manifest().manifest_digest
    barrier.acknowledge(
        _ack(
            "COMPLETED-BAR-METRICS",
            digest_value,
            status=_SubscriptionReadinessStatus.REJECTED,
            reason="manifest_mismatch",
        ),
    )
    barrier.acknowledge(
        _ack(
            "ROLLING-MEASUREMENTS",
            digest_value,
            status=_SubscriptionReadinessStatus.REJECTED,
            reason="series_mismatch",
        ),
    )

    decision = barrier.evaluate(now_ns=SECOND_NS + 2)

    assert decision.sealed is True
    assert decision.demand_series_ids == ()
    assert decision.quarantined_pairs == tuple(item.key for item in _requirements())


def test_wrong_epoch_digest_or_unknown_pair_is_rejected_without_mutating_accounting() -> None:
    barrier = _barrier()
    wrong_digest = _ack("COMPLETED-BAR-METRICS", "f" * 64)
    assert barrier.acknowledge(wrong_digest) is _AcknowledgementDisposition.REJECTED

    unknown = replace(
        _ack("COMPLETED-BAR-METRICS", _manifest().manifest_digest),
        consumer_actor_id="UNKNOWN-CONSUMER",
    )
    assert barrier.acknowledge(unknown) is _AcknowledgementDisposition.REJECTED
    assert barrier.evaluate(now_ns=SECOND_NS + 2).missing_pairs == tuple(
        item.key for item in _requirements()
    )
