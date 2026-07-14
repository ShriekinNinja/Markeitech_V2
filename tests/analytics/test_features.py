from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from markeitech.analytics import (
    AnalyticsInputFidelity,
    AnalyticsTimeframe,
    FeatureInputLineage,
    MarketContextCalculationConfig,
    MarketContextFeatureSnapshot,
    MarketContextSnapshot,
    TrendState,
    VwapPosition,
    configuration_fingerprint,
)
from markeitech.persistence import PersistenceConfig
from pydantic import ValidationError

AS_OF = datetime(2026, 7, 14, 10, 1, tzinfo=UTC)
CONFIGURATION_HASH = "a" * 64


def context_snapshot(**updates: object) -> MarketContextSnapshot:
    values: dict[str, object] = {
        "instrument_id": "NQU6.CME",
        "timeframe": AnalyticsTimeframe.ONE_MINUTE,
        "as_of": AS_OF,
        "source": "classified_ticks",
        "input_fidelity": AnalyticsInputFidelity.INFERRED,
        "bar_count": 251,
        "close": Decimal("29605.25"),
        "session_open": Decimal("29420"),
        "session_high": Decimal("29649.75"),
        "session_low": Decimal("29320"),
        "session_range_position": Decimal("0.865"),
        "vwap_position": VwapPosition.ABOVE,
        "trend": TrendState.BULLISH,
        "trend_reason_codes": ("ema20_above_ema50",),
    }
    values.update(updates)
    return MarketContextSnapshot(**values)


def lineage(**updates: object) -> FeatureInputLineage:
    values: dict[str, object] = {
        "instrument_id": "NQU6.CME",
        "timeframe": AnalyticsTimeframe.ONE_MINUTE,
        "source": "classified_ticks",
        "input_fidelity": AnalyticsInputFidelity.INFERRED,
        "start_ts": AS_OF - timedelta(minutes=250),
        "end_ts": AS_OF,
        "event_count": 251,
        "identity_hash": "1" * 64,
    }
    values.update(updates)
    return FeatureInputLineage(**values)


def test_feature_identity_is_stable_and_independent_of_lineage_order() -> None:
    one_minute = lineage()
    session_input = lineage(
        timeframe=AnalyticsTimeframe.FIVE_MINUTES,
        start_ts=AS_OF - timedelta(hours=5),
        event_count=60,
        identity_hash="2" * 64,
    )
    first = MarketContextFeatureSnapshot(
        configuration_hash=CONFIGURATION_HASH,
        input_lineage=(one_minute, session_input),
        snapshot=context_snapshot(),
    )
    reordered = first.model_copy(
        update={"input_lineage": (session_input, one_minute)},
    )

    assert first.feature_id == reordered.feature_id
    assert first.content_hash == reordered.content_hash
    assert len(first.feature_id) == 64


def test_same_inputs_and_calculation_expose_nondeterministic_content() -> None:
    original = MarketContextFeatureSnapshot(
        configuration_hash=CONFIGURATION_HASH,
        input_lineage=(lineage(),),
        snapshot=context_snapshot(),
    )
    changed = original.model_copy(
        update={"snapshot": context_snapshot(close=Decimal("29606.00"))},
    )

    assert original.feature_id == changed.feature_id
    assert original.content_hash != changed.content_hash


def test_feature_identity_changes_with_input_or_calculation_configuration() -> None:
    original = MarketContextFeatureSnapshot(
        configuration_hash=CONFIGURATION_HASH,
        input_lineage=(lineage(),),
        snapshot=context_snapshot(),
    )
    revised_input = original.model_copy(
        update={"input_lineage": (lineage(identity_hash="3" * 64),)},
    )
    revised_config = original.model_copy(update={"configuration_hash": "b" * 64})

    assert len({original.feature_id, revised_input.feature_id, revised_config.feature_id}) == 3


def test_feature_lineage_rejects_wrong_instrument_missing_timeframe_and_future_data() -> None:
    with pytest.raises(ValidationError, match="instrument must match"):
        MarketContextFeatureSnapshot(
            configuration_hash=CONFIGURATION_HASH,
            input_lineage=(lineage(instrument_id="ESU6.CME"),),
            snapshot=context_snapshot(),
        )
    with pytest.raises(ValidationError, match="include the snapshot timeframe"):
        MarketContextFeatureSnapshot(
            configuration_hash=CONFIGURATION_HASH,
            input_lineage=(lineage(timeframe=AnalyticsTimeframe.FIVE_MINUTES),),
            snapshot=context_snapshot(),
        )
    with pytest.raises(ValidationError, match="cannot extend beyond"):
        MarketContextFeatureSnapshot(
            configuration_hash=CONFIGURATION_HASH,
            input_lineage=(lineage(end_ts=AS_OF + timedelta(minutes=1)),),
            snapshot=context_snapshot(),
        )


def test_configuration_fingerprint_uses_canonical_model_content() -> None:
    first = PersistenceConfig(catalog_path="catalog", metadata_path="metadata.sqlite3")
    same = PersistenceConfig(metadata_path="metadata.sqlite3", catalog_path="catalog")
    changed = PersistenceConfig(catalog_path="other", metadata_path="metadata.sqlite3")

    assert configuration_fingerprint(first) == configuration_fingerprint(same)
    assert configuration_fingerprint(first) != configuration_fingerprint(changed)


def test_market_context_configuration_fingerprint_includes_session_policy() -> None:
    regular = MarketContextCalculationConfig(
        session_policies={"NQU6.CME": "CME_Equity|regular|America/New_York"},
    )
    full = MarketContextCalculationConfig(
        session_policies={"NQU6.CME": "CME_Equity|full|America/New_York"},
    )

    assert regular.configuration_hash != full.configuration_hash
