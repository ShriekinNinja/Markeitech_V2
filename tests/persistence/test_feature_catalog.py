from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from markeitech.analytics import (
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    FeatureInputLineage,
    MarketContextFeatureSnapshot,
    MarketContextSnapshot,
    TrendState,
    VwapPosition,
)
from markeitech.persistence import (
    MarketContextFeatureRecord,
    ParquetFeatureStore,
    PersistenceConfig,
)
from markeitech.persistence.feature_catalog import feature_to_record, record_to_feature

AS_OF = datetime(2026, 7, 14, 10, 1, tzinfo=UTC)


def feature(
    *,
    instrument_id: str = "NQU6.CME",
    as_of: datetime = AS_OF,
    input_hash: str = "1" * 64,
    close: str = "29605.25",
    configuration_hash: str = "a" * 64,
) -> MarketContextFeatureSnapshot:
    snapshot = MarketContextSnapshot(
        instrument_id=instrument_id,
        timeframe=AnalyticsTimeframe.ONE_MINUTE,
        as_of=as_of,
        source="classified_ticks",
        input_fidelity=AnalyticsInputFidelity.INFERRED,
        bar_count=251,
        close=Decimal(close),
        session_open=Decimal("29420"),
        session_high=Decimal("29649.75"),
        session_low=Decimal("29320"),
        session_range_position=Decimal("0.865"),
        vwap_position=VwapPosition.ABOVE,
        trend=TrendState.BULLISH,
        trend_reason_codes=("ema20_above_ema50",),
    )
    return MarketContextFeatureSnapshot(
        configuration_hash=configuration_hash,
        input_lineage=(
            FeatureInputLineage(
                instrument_id=instrument_id,
                timeframe=AnalyticsTimeframe.ONE_MINUTE,
                source="classified_ticks",
                input_fidelity=AnalyticsInputFidelity.INFERRED,
                start_ts=as_of - timedelta(minutes=250),
                end_ts=as_of,
                event_count=251,
                identity_hash=input_hash,
            ),
        ),
        snapshot=snapshot,
    )


@pytest.fixture
def store(tmp_path: Path) -> ParquetFeatureStore:
    return ParquetFeatureStore(
        PersistenceConfig(
            catalog_path=tmp_path / "catalog",
            metadata_path=tmp_path / "metadata.sqlite3",
        )
    )


def test_feature_record_round_trip_preserves_envelope_and_verifies_metadata() -> None:
    value = feature()
    record = feature_to_record(value)

    assert record_to_feature(record) == value
    assert record.feature_id == value.feature_id
    assert record.content_hash == value.content_hash

    tampered = MarketContextFeatureRecord(
        instrument_id=record.instrument_id,
        feature_id="f" * 64,
        content_hash=record.content_hash,
        envelope_schema_version=record.envelope_schema_version,
        feature_set=record.feature_set,
        calculation_version=record.calculation_version,
        configuration_hash=record.configuration_hash,
        timeframe=record.timeframe,
        as_of_ns=record.as_of_ns,
        source=record.source,
        input_fidelity=record.input_fidelity,
        envelope_json=record.envelope_json,
    )
    with pytest.raises(ValueError, match="metadata does not match"):
        record_to_feature(tampered)


def test_catalog_round_trip_and_restart_retry_are_idempotent(
    store: ParquetFeatureStore,
) -> None:
    value = feature()

    first = store.write([value])
    retried = store.write([value, value])

    assert first.written_count == 1
    assert first.duplicate_count == 0
    assert retried.written_count == 0
    assert retried.duplicate_count == 2
    assert store.query_history("NQU6.CME") == (value,)


def test_catalog_retains_revised_input_lineage_at_same_as_of(
    store: ParquetFeatureStore,
) -> None:
    original = feature()
    revised = feature(input_hash="2" * 64, close="29606.00")

    store.write([original])
    result = store.write([revised])

    assert result.written_count == 1
    assert set(
        store.query_latest_variants(
            "NQU6.CME",
            timeframe=AnalyticsTimeframe.ONE_MINUTE,
        )
    ) == {
        original,
        revised,
    }


def test_catalog_rejects_same_identity_with_different_content(
    store: ParquetFeatureStore,
) -> None:
    original = feature()
    nondeterministic = feature(close="29606.00")
    assert original.feature_id == nondeterministic.feature_id

    store.write([original])

    with pytest.raises(ValueError, match="different persisted content"):
        store.write([nondeterministic])
    assert store.query_history("NQU6.CME") == (original,)


def test_catalog_keeps_instruments_and_query_filters_isolated(
    store: ParquetFeatureStore,
) -> None:
    nq = feature()
    nq_next = feature(as_of=AS_OF + timedelta(minutes=1), input_hash="2" * 64)
    es = feature(instrument_id="ESU6.CME", close="7558.75")
    different_config = feature(
        as_of=AS_OF + timedelta(minutes=2),
        input_hash="3" * 64,
        configuration_hash="b" * 64,
    )

    store.write([nq, nq_next, es, different_config])

    assert store.query_history("ESU6.CME") == (es,)
    assert store.query_history("NQU6.CME", configuration_hash="a" * 64) == (
        nq,
        nq_next,
    )
    assert store.query_latest_variants(
        "NQU6.CME",
        timeframe=AnalyticsTimeframe.ONE_MINUTE,
        configuration_hash="a" * 64,
    ) == (nq_next,)


def test_empty_feature_batch_is_harmless(store: ParquetFeatureStore) -> None:
    result = store.write([])

    assert result.submitted_count == 0
    assert result.written_count == 0
    assert result.duplicate_count == 0
