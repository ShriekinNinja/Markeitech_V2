from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from markeitech.intelligence import (
    MetricFidelity,
    MetricHealth,
    MetricSubjectIdentity,
    MetricValue,
    MetricValueKind,
)
from markeitech.intelligence.metric_value_admission import (
    _MetricValueAdmissionBook,
    _MetricValueAdmissionDisposition,
)

SECOND_NS = 1_000_000_000
RUN_EPOCH = UUID("11111111-1111-1111-1111-111111111111")
OTHER_RUN_EPOCH = UUID("22222222-2222-2222-2222-222222222222")


def _subject(metric_id: str = "quote.midpoint") -> MetricSubjectIdentity:
    return MetricSubjectIdentity(
        metric_id=metric_id,
        metric_version=1,
        parameter_version=1,
        parameter_effective_from_ns=SECOND_NS,
        parameter_epoch=UUID("33333333-3333-3333-3333-333333333333"),
        configuration_epoch=UUID("44444444-4444-4444-4444-444444444444"),
        configuration_digest="a" * 64,
        instrument_id="ESU6.CME",
        output_schema_version=2,
        canonical_producer_id="QUOTE-QUALITY-METRICS",
    )


def _value(
    revision: int,
    *,
    subject: MetricSubjectIdentity | None = None,
    run_epoch: UUID = RUN_EPOCH,
    value: Decimal = Decimal("100.25"),
    published_ts_ns: int | None = None,
) -> MetricValue:
    published = 2 * SECOND_NS + 3 if published_ts_ns is None else published_ts_ns
    return MetricValue(
        subject=_subject() if subject is None else subject,
        kind=MetricValueKind.NUMBER,
        value=value,
        unit_id="price",
        effective_ts_ns=2 * SECOND_NS,
        observed_ts_ns=2 * SECOND_NS,
        received_ts_ns=2 * SECOND_NS + 1,
        calculated_ts_ns=2 * SECOND_NS + 2,
        published_ts_ns=published,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.DERIVED,
        reasons=(),
        evidence_refs=("quote:1",),
        run_epoch=run_epoch,
        revision=revision,
        previous_revision=None if revision == 1 else revision - 1,
    )


def test_first_value_requires_revision_one_and_does_not_create_state_on_gap() -> None:
    book = _MetricValueAdmissionBook()

    result = book.admit(_value(2))

    assert result.disposition is _MetricValueAdmissionDisposition.REJECTED_GAP
    assert result.current_value is None
    assert book.current(_subject(), RUN_EPOCH) is None
    assert book.counters.gaps == 1


def test_identical_repeat_is_duplicate_and_unequal_same_revision_is_conflict() -> None:
    book = _MetricValueAdmissionBook()
    first = _value(1)
    assert book.admit(first).disposition is _MetricValueAdmissionDisposition.ACCEPTED

    duplicate = book.admit(first)
    conflict = book.admit(replace(first, value=Decimal("100.50")))

    assert duplicate.disposition is _MetricValueAdmissionDisposition.DUPLICATE
    assert duplicate.current_value == first
    assert conflict.disposition is _MetricValueAdmissionDisposition.REJECTED_CONFLICT
    assert conflict.current_value == first
    assert book.current(first.subject, first.run_epoch) == first
    assert book.counters.duplicates == 1
    assert book.counters.conflicts == 1


def test_conflict_preserves_chain_and_later_contiguous_revision_is_accepted() -> None:
    book = _MetricValueAdmissionBook()
    first = _value(1)
    book.admit(first)
    book.admit(replace(first, value=Decimal("999")))

    second = _value(2, value=Decimal("101"))
    result = book.admit(second)

    assert result.disposition is _MetricValueAdmissionDisposition.ACCEPTED
    assert book.current(second.subject, second.run_epoch) == second
    assert book.counters.accepted == 2


def test_stale_and_gapped_revisions_are_counted_without_timestamp_substitution() -> None:
    book = _MetricValueAdmissionBook()
    first = _value(1)
    second = _value(2, value=Decimal("101"))
    book.admit(first)

    same_revision_later_timestamp = replace(
        first,
        published_ts_ns=first.published_ts_ns + 100,
    )
    assert book.admit(same_revision_later_timestamp).disposition is (
        _MetricValueAdmissionDisposition.REJECTED_CONFLICT
    )
    gap = _value(3, value=Decimal("103"), published_ts_ns=first.published_ts_ns + 1_000)
    assert book.admit(gap).disposition is _MetricValueAdmissionDisposition.REJECTED_GAP
    assert book.admit(second).disposition is _MetricValueAdmissionDisposition.ACCEPTED
    assert book.admit(first).disposition is _MetricValueAdmissionDisposition.REJECTED_STALE
    assert book.current(first.subject, first.run_epoch) == second
    assert book.counters.conflicts == 1
    assert book.counters.gaps == 1
    assert book.counters.stale == 1


def test_complete_subject_and_run_epoch_have_independent_revision_chains() -> None:
    book = _MetricValueAdmissionBook(maximum_subjects=3)
    first = _value(1)
    other_subject = _value(1, subject=_subject("quote.absolute_spread"))
    other_run = _value(1, run_epoch=OTHER_RUN_EPOCH)

    assert book.admit(first).disposition is _MetricValueAdmissionDisposition.ACCEPTED
    assert book.admit(other_subject).disposition is _MetricValueAdmissionDisposition.ACCEPTED
    assert book.admit(other_run).disposition is _MetricValueAdmissionDisposition.ACCEPTED
    assert book.subject_count == 3


def test_subject_capacity_rejection_is_bounded_and_preserves_existing_state() -> None:
    book = _MetricValueAdmissionBook(maximum_subjects=1)
    first = _value(1)
    book.admit(first)

    rejected = book.admit(_value(1, subject=_subject("quote.absolute_spread")))

    assert rejected.disposition is _MetricValueAdmissionDisposition.REJECTED_CAPACITY
    assert rejected.current_value is None
    assert book.current(first.subject, first.run_epoch) == first
    assert book.subject_count == 1
    assert book.counters.capacity_rejections == 1
