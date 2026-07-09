from datetime import date

import pytest
from markeitech.domain import (
    AnalysisProfile,
    EquityLikeContractConfig,
    FuturesContractConfig,
    InstrumentDataMode,
    InstrumentRegistryConfig,
    InstrumentRole,
    InstrumentRuntimeConfig,
    NQContractConfig,
    SecurityType,
)
from pydantic import ValidationError


def nq_contract() -> NQContractConfig:
    return NQContractConfig(
        expiry=date(2026, 9, 18),
        instrument_id="NQU6.CME",
        ib_last_trade_date_or_contract_month="20260918",
    )


def es_contract() -> FuturesContractConfig:
    return FuturesContractConfig(
        root_symbol="ES",
        exchange="CME",
        expiry=date(2026, 9, 18),
        instrument_id="ESU6.CME",
        ib_symbol="ES",
        ib_exchange="CME",
        ib_last_trade_date_or_contract_month="20260918",
    )


def spx_contract() -> EquityLikeContractConfig:
    return EquityLikeContractConfig(
        root_symbol="SPX",
        exchange="CBOE",
        instrument_id="^SPX.CBOE",
        security_type=SecurityType.INDEX,
        ib_symbol="SPX",
        ib_exchange="CBOE",
        ib_security_type="IND",
    )


def active_runtime(contract: FuturesContractConfig) -> InstrumentRuntimeConfig:
    return InstrumentRuntimeConfig(
        contract=contract,
        role=InstrumentRole.ACTIVE,
        data_mode=InstrumentDataMode.TICK_BY_TICK,
        analysis_profile=AnalysisProfile.ACTIVE_TICK,
        priority=0,
    )


def background_runtime(
    contract: EquityLikeContractConfig | FuturesContractConfig,
) -> InstrumentRuntimeConfig:
    return InstrumentRuntimeConfig(
        contract=contract,
        role=InstrumentRole.BACKGROUND,
        data_mode=InstrumentDataMode.HISTORICAL_1M,
        analysis_profile=AnalysisProfile.BACKGROUND_BAR,
        priority=50,
        historical_refresh_interval_seconds=60,
    )


def test_explicit_nq_contract_identity() -> None:
    contract = nq_contract()

    assert contract.identity_key == "NQ.CME.20260918.NQU6.CME"


def test_generic_futures_contract_allows_es_background() -> None:
    contract = es_contract()

    assert contract.identity_key == "ES.CME.20260918.ESU6.CME"


def test_rejects_continuous_front_month_identity_for_any_future_root() -> None:
    with pytest.raises(ValidationError, match="front-month or continuous"):
        FuturesContractConfig(
            root_symbol="ES",
            exchange="CME",
            expiry=date(2026, 9, 18),
            instrument_id="ES.CME",
            ib_symbol="ES",
            ib_exchange="CME",
            ib_last_trade_date_or_contract_month="20260918",
        )


def test_rejects_fixed_offset_session_timezone() -> None:
    with pytest.raises(ValidationError, match="fixed UTC offsets"):
        NQContractConfig(
            expiry=date(2026, 9, 18),
            instrument_id="NQU6.CME",
            ib_last_trade_date_or_contract_month="20260918",
            session_timezone="UTC-04:00",
        )


def test_rejects_mismatched_ib_expiry() -> None:
    with pytest.raises(ValidationError, match="IB expiry must match"):
        NQContractConfig(
            expiry=date(2026, 9, 18),
            instrument_id="NQU6.CME",
            ib_last_trade_date_or_contract_month="20261218",
        )


def test_registry_allows_one_active_and_multiple_background_instruments() -> None:
    registry = InstrumentRegistryConfig(
        active_instrument_id="NQU6.CME",
        instruments=(
            active_runtime(nq_contract()),
            background_runtime(es_contract()),
            background_runtime(spx_contract()),
        ),
    )

    assert registry.active_runtime.contract.instrument_id == "NQU6.CME"
    assert len(registry.instruments) == 3


def test_registry_rejects_multiple_active_instruments() -> None:
    with pytest.raises(ValidationError, match="exactly one active"):
        InstrumentRegistryConfig(
            active_instrument_id="NQU6.CME",
            instruments=(
                active_runtime(nq_contract()),
                active_runtime(es_contract()),
            ),
        )


def test_registry_rejects_active_instrument_without_tick_mode() -> None:
    with pytest.raises(ValidationError, match="tick-by-tick"):
        InstrumentRuntimeConfig(
            contract=nq_contract(),
            role=InstrumentRole.ACTIVE,
            data_mode=InstrumentDataMode.HISTORICAL_1M,
            analysis_profile=AnalysisProfile.ACTIVE_TICK,
        )


def test_background_instrument_requires_historical_refresh_interval() -> None:
    with pytest.raises(ValidationError, match="historical refresh interval"):
        InstrumentRuntimeConfig(
            contract=es_contract(),
            role=InstrumentRole.BACKGROUND,
            data_mode=InstrumentDataMode.HISTORICAL_1M,
            analysis_profile=AnalysisProfile.BACKGROUND_BAR,
        )
