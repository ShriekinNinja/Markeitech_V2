from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from markeitech.intelligence import (
    MetricFidelity,
    MetricHealth,
    MetricReasonCode,
    MetricRegistry,
    MetricSubjectIdentity,
    MetricValue,
    MetricValueKind,
)
from markeitech.intelligence.metrics import _migrate_legacy_metric_value
from markeitech.intelligence.quote_metrics import (
    QuoteMetricCatalogPolicy,
    QuoteMetricInput,
    calculate_quote_metrics,
    quote_metric_definitions,
)

SECOND_NS = 1_000_000_000
RUN_EPOCH = UUID("11111111-1111-1111-1111-111111111111")
PARAMETER_EPOCH = UUID("22222222-2222-2222-2222-222222222222")
CONFIGURATION_EPOCH = UUID("33333333-3333-3333-3333-333333333333")


def _subject(metric_id: str = "quote.midpoint") -> MetricSubjectIdentity:
    return MetricSubjectIdentity(
        metric_id=metric_id,
        metric_version=1,
        parameter_version=1,
        parameter_effective_from_ns=SECOND_NS,
        parameter_epoch=PARAMETER_EPOCH,
        configuration_epoch=CONFIGURATION_EPOCH,
        configuration_digest="a" * 64,
        instrument_id="ESU6.CME",
        output_schema_version=2,
        canonical_producer_id="QUOTE-QUALITY-METRICS",
    )


def _calendar_dimensions() -> dict[str, object]:
    return {
        "calendar_id": "cme_equity",
        "calendar_definition_version": 4,
        "calendar_definition_digest": "b" * 64,
        "calendar_definition_effective_from_ns": SECOND_NS,
    }


def _value(
    *,
    kind: MetricValueKind = MetricValueKind.NUMBER,
    value: object | None = Decimal("100.125000001"),
    health: MetricHealth = MetricHealth.READY,
    reasons: tuple[MetricReasonCode, ...] = (),
    revision: int = 1,
) -> MetricValue:
    return MetricValue(
        subject=_subject(),
        kind=kind,
        value=value,  # type: ignore[arg-type]
        unit_id="price",
        effective_ts_ns=2 * SECOND_NS,
        observed_ts_ns=2 * SECOND_NS,
        received_ts_ns=2 * SECOND_NS + 1,
        calculated_ts_ns=2 * SECOND_NS + 2,
        published_ts_ns=2 * SECOND_NS + 3,
        health=health,
        fidelity=(
            MetricFidelity.DERIVED if health is MetricHealth.READY else MetricFidelity.PARTIAL
        ),
        reasons=reasons,
        evidence_refs=("quote:1",),
        run_epoch=RUN_EPOCH,
        revision=revision,
        previous_revision=None if revision == 1 else revision - 1,
    )


def test_metric_subject_digest_is_deterministic_and_complete_group_validation_fails_closed() -> (
    None
):
    subject = _subject()

    assert MetricSubjectIdentity.from_dict(subject.to_dict()) == subject
    assert subject.identity_digest == _subject().identity_digest
    assert (
        replace(subject, configuration_epoch=RUN_EPOCH).identity_digest != subject.identity_digest
    )
    with pytest.raises(ValueError, match="calendar subject dimensions"):
        replace(subject, calendar_id="cme_equity")
    with pytest.raises(ValueError, match="rolling subject dimensions"):
        replace(subject, rolling_family_id="fast")
    with pytest.raises(ValueError, match="require calendar identity"):
        replace(
            subject,
            session_id="CME-2026-08-17-GTH",
            trade_date=date(2026, 8, 17),
        )
    session_subject = replace(
        subject,
        session_id="CME-2026-08-17-GTH",
        trade_date=date(2026, 8, 17),
        **_calendar_dimensions(),
    )
    with pytest.raises(ValueError, match="trade_date"):
        replace(session_subject, trade_date=datetime(2026, 8, 17))


def test_window_and_rolling_subject_dependencies_reject_partial_identity() -> None:
    subject = _subject()
    with pytest.raises(ValueError, match="analytical-window subjects require"):
        replace(
            subject,
            analytical_window_id="opening_range_fast",
            analytical_window_version=1,
        )
    window = replace(
        subject,
        input_series_id="es_1m",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        analytical_window_id="opening_range_fast",
        analytical_window_version=1,
        **_calendar_dimensions(),
    )
    assert window.identity_digest

    rolling_dimensions = {
        "rolling_family_id": "fast",
        "rolling_candidate_id": "context_45m",
        "input_timeframe": "1m",
        "horizon": "45m",
        "baseline_policy_id": "phase_matched_v1",
    }
    with pytest.raises(ValueError, match="rolling subjects require"):
        replace(subject, **rolling_dimensions)
    rolling = replace(
        subject,
        input_series_id="es_1m",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        **_calendar_dimensions(),
        **rolling_dimensions,
    )
    assert rolling.identity_digest


def test_metric_value_round_trip_preserves_decimal_timestamps_and_revision_identity() -> None:
    value = _value()

    restored = MetricValue.from_dict(value.to_dict())

    assert restored == value
    assert restored.to_bytes() == value.to_bytes()
    assert restored.value == Decimal("100.125000001")
    assert restored.ts_event == value.effective_ts_ns
    assert restored.ts_init == value.published_ts_ns
    assert restored.identity_digest == value.identity_digest


def test_metric_value_deserialization_rejects_shape_type_and_decimal_coercion() -> None:
    canonical = _value().to_dict()

    with pytest.raises(ValueError, match="keys are not exact"):
        MetricValue.from_dict({**canonical, "unknown": "value"})
    missing = dict(canonical)
    missing.pop("unit_id")
    with pytest.raises(ValueError, match="keys are not exact"):
        MetricValue.from_dict(missing)
    with pytest.raises(ValueError, match="canonical Decimal string"):
        MetricValue.from_dict({**canonical, "value": 100.125})
    with pytest.raises(ValueError, match="canonical finite Decimal string"):
        MetricValue.from_dict({**canonical, "value": "0100.125"})
    with pytest.raises(ValueError, match="revision must be an integer"):
        MetricValue.from_dict({**canonical, "revision": "1"})
    with pytest.raises(ValueError, match="published_ts_ns must be an integer"):
        MetricValue.from_dict({**canonical, "published_ts_ns": True})


def test_metric_subject_deserialization_rejects_unknown_missing_and_coerced_fields() -> None:
    canonical = _subject().to_dict()

    with pytest.raises(ValueError, match="keys are not exact"):
        MetricSubjectIdentity.from_dict({**canonical, "unknown": None})
    missing = dict(canonical)
    missing.pop("configuration_digest")
    with pytest.raises(ValueError, match="keys are not exact"):
        MetricSubjectIdentity.from_dict(missing)
    with pytest.raises(ValueError, match="metric_version must be an integer"):
        MetricSubjectIdentity.from_dict({**canonical, "metric_version": "1"})
    with pytest.raises(ValueError, match="parameter_version must be an integer"):
        MetricSubjectIdentity.from_dict({**canonical, "parameter_version": True})


def test_metric_health_value_and_reason_invariants_are_enforced() -> None:
    degraded = _value(
        health=MetricHealth.DEGRADED,
        reasons=(MetricReasonCode.INPUT_PARTIAL,),
    )
    assert degraded.value is not None

    unavailable = _value(
        value=None,
        health=MetricHealth.UNAVAILABLE,
        reasons=(MetricReasonCode.EVIDENCE_UNAVAILABLE,),
    )
    assert unavailable.value is None

    with pytest.raises(ValueError, match="READY metrics require"):
        _value(reasons=(MetricReasonCode.INPUT_PARTIAL,))
    with pytest.raises(ValueError, match="require at least"):
        _value(health=MetricHealth.DEGRADED)
    with pytest.raises(ValueError, match="require a value"):
        _value(value=None, health=MetricHealth.DEGRADED, reasons=(MetricReasonCode.INPUT_PARTIAL,))
    with pytest.raises(ValueError, match="require a null"):
        _value(health=MetricHealth.UNAVAILABLE, reasons=(MetricReasonCode.EVIDENCE_UNAVAILABLE,))


def test_metric_scalar_kinds_reject_float_bool_as_integer_and_overlong_text() -> None:
    with pytest.raises(ValueError, match="NUMBER"):
        _value(value=1.25)
    with pytest.raises(ValueError, match="INTEGER"):
        _value(kind=MetricValueKind.INTEGER, value=True)
    with pytest.raises(ValueError, match="1 through 512"):
        _value(kind=MetricValueKind.TEXT, value="x" * 513)


def test_metric_registry_validates_v2_kind_even_when_value_is_null() -> None:
    registry = MetricRegistry(
        quote_metric_definitions(QuoteMetricCatalogPolicy(250, 15_000, 50)),
    )
    value = _value(
        kind=MetricValueKind.TEXT,
        value=None,
        health=MetricHealth.UNAVAILABLE,
        reasons=(MetricReasonCode.EVIDENCE_UNAVAILABLE,),
    )

    with pytest.raises(ValueError, match="kind"):
        registry.validate_value(value)


def test_metric_reason_codes_require_unique_canonical_order() -> None:
    with pytest.raises(ValueError, match="canonical"):
        _value(
            health=MetricHealth.DEGRADED,
            reasons=(MetricReasonCode.GAP, MetricReasonCode.INPUT_PARTIAL),
        )
    with pytest.raises(ValueError, match="unique"):
        _value(
            health=MetricHealth.DEGRADED,
            reasons=(MetricReasonCode.INPUT_PARTIAL, MetricReasonCode.INPUT_PARTIAL),
        )


def test_revision_chain_requires_contiguous_previous_revision() -> None:
    assert _value(revision=2).previous_revision == 1
    with pytest.raises(ValueError, match="immediately preceding"):
        replace(_value(revision=2), previous_revision=None)
    with pytest.raises(ValueError, match="revision 1"):
        replace(_value(), previous_revision=1)


def test_legacy_quote_calculation_migrates_purely_without_changing_active_wire() -> None:
    registry = MetricRegistry(
        quote_metric_definitions(QuoteMetricCatalogPolicy(250, 15_000, 50)),
    )
    legacy = calculate_quote_metrics(
        QuoteMetricInput(
            instrument_id="ESU6.CME",
            bid=Decimal("100"),
            ask=Decimal("101"),
            observed_ts_ns=2 * SECOND_NS,
            received_ts_ns=2 * SECOND_NS + 1,
            session_id=None,
            evidence_state="HEALTHY",
            evidence_ref="quote:1",
        ),
        registry=registry,
        parameter_version=1,
        calculated_ts_ns=2 * SECOND_NS + 2,
        published_ts_ns=2 * SECOND_NS + 3,
        source="QUOTE-QUALITY-METRICS",
        revision=1,
    )

    migrated = tuple(
        _migrate_legacy_metric_value(
            item,
            subject=_subject(item.metric_id),
            kind=MetricValueKind.NUMBER,
            run_epoch=RUN_EPOCH,
            previous_revision=None,
            reason_codes=(),
        )
        for item in legacy
    )

    assert tuple(item.value for item in migrated) == tuple(item.value for item in legacy)
    assert tuple(item.unit_id for item in migrated) == tuple(item.unit for item in legacy)
    assert all(isinstance(item, MetricValue) for item in migrated)
    for item in migrated:
        registry.validate_value(item)


def test_public_metric_value_is_v2_and_private_legacy_contract_is_not_exported() -> None:
    import markeitech.intelligence as intelligence

    assert MetricValue.__module__ == "markeitech.intelligence.metric_messages"
    assert "LegacyMetricValue" not in intelligence.__all__


def test_legacy_reason_migration_requires_explicit_typed_mapping() -> None:
    registry = MetricRegistry(
        quote_metric_definitions(QuoteMetricCatalogPolicy(250, 15_000, 50)),
    )
    legacy = calculate_quote_metrics(
        QuoteMetricInput(
            instrument_id="ESU6.CME",
            bid=None,
            ask=None,
            observed_ts_ns=2 * SECOND_NS,
            received_ts_ns=2 * SECOND_NS + 1,
            session_id=None,
            evidence_state="UNAVAILABLE",
            evidence_ref="quote:missing",
        ),
        registry=registry,
        parameter_version=1,
        calculated_ts_ns=2 * SECOND_NS + 2,
        published_ts_ns=2 * SECOND_NS + 3,
        source="QUOTE-QUALITY-METRICS",
        revision=1,
    )[0]

    with pytest.raises(ValueError, match="every legacy reason"):
        _migrate_legacy_metric_value(
            legacy,
            subject=_subject(legacy.metric_id),
            kind=MetricValueKind.NUMBER,
            run_epoch=RUN_EPOCH,
            previous_revision=None,
            reason_codes=(MetricReasonCode.EVIDENCE_UNAVAILABLE,),
        )
