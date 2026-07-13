from datetime import date

import pytest
from markeitech.domain import (
    AnalysisProfile,
    CryptoContractConfig,
    EquityLikeContractConfig,
    FuturesContractConfig,
    InstrumentDataMode,
    InstrumentRegistryConfig,
    InstrumentRole,
    InstrumentRuntimeConfig,
    InstrumentWarmupConfig,
    NQContractConfig,
    SecurityType,
    WarmupTimeframe,
)
from pydantic import ValidationError


def nq_contract() -> NQContractConfig:
    return NQContractConfig(
        expiry=date(2026, 9, 18),
        instrument_id="NQU6.CME",
        ib_last_trade_date_or_contract_month="20260918",
        calendar_id="CME_Equity",
        session_profile="full",
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
        calendar_id="CME_Equity",
        session_profile="full",
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
        calendar_id="NYSE",
        session_profile="regular",
    )


def test_paxos_crypto_contract_uses_currency_pair_identity() -> None:
    contract = CryptoContractConfig(
        root_symbol="btc",
        exchange="paxos",
        instrument_id="BTC/USD.PAXOS",
        ib_symbol="btc",
        ib_exchange="paxos",
        session_timezone="UTC",
        calendar_id="24/7",
        session_profile="continuous",
    )

    assert contract.root_symbol == "BTC"
    assert contract.quote_currency == "USD"
    assert contract.security_type == SecurityType.CRYPTO


def test_crypto_contract_rejects_non_pair_instrument_identity() -> None:
    with pytest.raises(ValidationError, match="crypto instrument id must be BTC/USD.PAXOS"):
        CryptoContractConfig(
            root_symbol="BTC",
            exchange="PAXOS",
            instrument_id="BTC.PAXOS",
            ib_symbol="BTC",
            ib_exchange="PAXOS",
            session_timezone="UTC",
            calendar_id="24/7",
            session_profile="continuous",
        )


def test_continuous_profile_requires_native_24_7_calendar() -> None:
    with pytest.raises(ValidationError, match="used together"):
        CryptoContractConfig(
            root_symbol="BTC",
            exchange="PAXOS",
            instrument_id="BTC/USD.PAXOS",
            ib_symbol="BTC",
            ib_exchange="PAXOS",
            session_timezone="UTC",
            calendar_id="NYSE",
            session_profile="continuous",
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
        data_mode=InstrumentDataMode.LIVE_1M_BARS,
        analysis_profile=AnalysisProfile.BACKGROUND_BAR,
        priority=50,
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
            calendar_id="CME_Equity",
            session_profile="full",
        )


def test_rejects_fixed_offset_session_timezone() -> None:
    with pytest.raises(ValidationError, match="fixed UTC offsets"):
        NQContractConfig(
            expiry=date(2026, 9, 18),
            instrument_id="NQU6.CME",
            ib_last_trade_date_or_contract_month="20260918",
            session_timezone="UTC-04:00",
            calendar_id="CME_Equity",
            session_profile="full",
        )


def test_rejects_mismatched_ib_expiry() -> None:
    with pytest.raises(ValidationError, match="IB expiry must match"):
        NQContractConfig(
            expiry=date(2026, 9, 18),
            instrument_id="NQU6.CME",
            ib_last_trade_date_or_contract_month="20261218",
            calendar_id="CME_Equity",
            session_profile="full",
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
    for runtime in registry.instruments:
        assert runtime.warmup is not None
        assert WarmupTimeframe.ONE_MINUTE in runtime.warmup.timeframes


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
            data_mode=InstrumentDataMode.LIVE_1M_BARS,
            analysis_profile=AnalysisProfile.ACTIVE_TICK,
        )


def test_background_instrument_requires_live_1m_bar_mode() -> None:
    with pytest.raises(ValidationError, match="live 1m bar"):
        InstrumentRuntimeConfig(
            contract=es_contract(),
            role=InstrumentRole.BACKGROUND,
            data_mode=InstrumentDataMode.HISTORICAL_WARMUP_ONLY,
            analysis_profile=AnalysisProfile.BACKGROUND_BAR,
        )


def test_enabled_instrument_requires_warmup_configuration() -> None:
    with pytest.raises(ValidationError, match="warmup configuration"):
        InstrumentRuntimeConfig(
            contract=es_contract(),
            role=InstrumentRole.BACKGROUND,
            data_mode=InstrumentDataMode.LIVE_1M_BARS,
            analysis_profile=AnalysisProfile.BACKGROUND_BAR,
            warmup=None,
        )


def test_warmup_config_describes_multi_timeframe_annotation() -> None:
    warmup = InstrumentWarmupConfig(lookback_sessions=10)

    assert warmup.lookback_sessions == 10
    assert WarmupTimeframe.FIFTEEN_MINUTE in warmup.timeframes
    assert warmup.annotate_support_resistance is True
    assert warmup.annotate_emas is True
    assert warmup.annotate_trend is True
    assert warmup.annotate_vwap is True
    assert warmup.annotate_fvgs is True
