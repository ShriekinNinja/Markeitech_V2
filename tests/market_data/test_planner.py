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
    WarmupTimeframe,
)
from markeitech.market_data import (
    InteractiveBrokersConnectionConfig,
    MarketDataRuntimeConfig,
    NautilusIntentKind,
    PlannedSubscription,
    SubscriptionKind,
    build_market_data_plan,
    build_nautilus_request_plan,
    build_trading_node_config,
)
from markeitech.market_data.planner import MarketDataRuntimePlan
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


def registry() -> InstrumentRegistryConfig:
    return InstrumentRegistryConfig(
        active_instrument_id="NQU6.CME",
        instruments=(
            InstrumentRuntimeConfig(
                contract=nq_contract(),
                role=InstrumentRole.ACTIVE,
                data_mode=InstrumentDataMode.TICK_BY_TICK,
                analysis_profile=AnalysisProfile.ACTIVE_TICK,
            ),
            InstrumentRuntimeConfig(
                contract=es_contract(),
                role=InstrumentRole.BACKGROUND,
                data_mode=InstrumentDataMode.LIVE_1M_BARS,
                analysis_profile=AnalysisProfile.BACKGROUND_BAR,
            ),
            InstrumentRuntimeConfig(
                contract=spx_contract(),
                role=InstrumentRole.BACKGROUND,
                data_mode=InstrumentDataMode.LIVE_1M_BARS,
                analysis_profile=AnalysisProfile.BACKGROUND_BAR,
            ),
        ),
    )


def test_market_data_plan_warms_every_enabled_instrument() -> None:
    plan = build_market_data_plan(registry())

    assert {warmup.instrument_id for warmup in plan.warmups} == {
        "NQU6.CME",
        "ESU6.CME",
        "^SPX.CBOE",
    }
    for warmup in plan.warmups:
        assert WarmupTimeframe.ONE_MINUTE in warmup.timeframes
        assert warmup.annotate_support_resistance is True
        assert warmup.annotate_emas is True
        assert warmup.annotate_trend is True
        assert warmup.annotate_vwap is True
        assert warmup.annotate_fvgs is True


def test_market_data_plan_assigns_active_tick_and_background_bar_streams() -> None:
    plan = build_market_data_plan(registry())

    subscriptions = {
        (subscription.instrument_id, subscription.kind) for subscription in plan.subscriptions
    }
    assert ("NQU6.CME", SubscriptionKind.TICK_LAST) in subscriptions
    assert ("NQU6.CME", SubscriptionKind.TICK_BID_ASK) in subscriptions
    assert ("NQU6.CME", SubscriptionKind.BAR_1M) in subscriptions
    assert ("ESU6.CME", SubscriptionKind.BAR_1M) in subscriptions
    assert ("^SPX.CBOE", SubscriptionKind.BAR_1M) in subscriptions
    assert ("ESU6.CME", SubscriptionKind.TICK_LAST) not in subscriptions
    assert ("^SPX.CBOE", SubscriptionKind.TICK_BID_ASK) not in subscriptions


def test_nautilus_request_plan_maps_warmups_and_subscriptions() -> None:
    plan = build_market_data_plan(registry())
    request_plan = build_nautilus_request_plan(plan, data_client_name="IB")

    assert {warmup.instrument_id for warmup in request_plan.warmups} == {
        "NQU6.CME",
        "ESU6.CME",
        "^SPX.CBOE",
    }
    nq_warmup = next(
        warmup for warmup in request_plan.warmups if warmup.instrument_id == "NQU6.CME"
    )
    assert "NQU6.CME-1-MINUTE-LAST-EXTERNAL" in nq_warmup.bar_types
    assert "NQU6.CME-15-MINUTE-LAST-EXTERNAL" in nq_warmup.bar_types

    subscriptions = {
        (subscription.instrument_id, subscription.kind, subscription.bar_type)
        for subscription in request_plan.subscriptions
    }
    assert ("NQU6.CME", NautilusIntentKind.SUBSCRIBE_TRADE_TICKS, None) in subscriptions
    assert ("NQU6.CME", NautilusIntentKind.SUBSCRIBE_QUOTE_TICKS, None) in subscriptions
    assert (
        "NQU6.CME",
        NautilusIntentKind.SUBSCRIBE_BARS,
        "NQU6.CME-1-MINUTE-LAST-EXTERNAL",
    ) in subscriptions
    assert (
        "ESU6.CME",
        NautilusIntentKind.SUBSCRIBE_BARS,
        "ESU6.CME-1-MINUTE-LAST-EXTERNAL",
    ) in subscriptions


def test_market_data_plan_rejects_duplicate_stream_ownership() -> None:
    plan = build_market_data_plan(registry())

    with pytest.raises(ValidationError, match="duplicate stream ownership"):
        MarketDataRuntimePlan(
            active_instrument_id=plan.active_instrument_id,
            warmups=plan.warmups,
            subscriptions=(
                *plan.subscriptions,
                PlannedSubscription(
                    instrument_id=plan.subscriptions[0].instrument_id,
                    kind=plan.subscriptions[0].kind,
                ),
            ),
        )


def test_runtime_config_remains_data_only_and_read_only() -> None:
    with pytest.raises(ValidationError, match="data-only"):
        MarketDataRuntimeConfig(
            instrument_registry=registry(),
            data_only=False,
        )

    with pytest.raises(ValidationError, match="read-only"):
        MarketDataRuntimeConfig(
            instrument_registry=registry(),
            ib=InteractiveBrokersConnectionConfig(read_only=False),
        )


def test_builds_nautilus_trading_node_config_without_execution_clients() -> None:
    config = MarketDataRuntimeConfig(
        instrument_registry=registry(),
        ib=InteractiveBrokersConnectionConfig(
            host="127.0.0.1",
            port=7497,
            client_id=7,
            use_regular_trading_hours=False,
        ),
        trader_id="MARK-001",
    )

    node_config = build_trading_node_config(config)

    assert str(node_config.trader_id) == "MARK-001"
    assert set(node_config.data_clients) == {"IB"}
    assert {
        str(instrument_id)
        for instrument_id in node_config.data_clients["IB"].instrument_provider.load_ids
    } == {"NQU6.CME", "ESU6.CME", "^SPX.CBOE"}
    assert node_config.exec_clients == {}
    assert node_config.strategies == []
    assert node_config.actors == []
