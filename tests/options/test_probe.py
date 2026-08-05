from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from ibapi.ticktype import TickTypeEnum
from markeitech.options import (
    OptionChainDefinition,
    OptionChainProbeConfig,
    OptionContractObservation,
    build_probe_report,
    select_atm_strikes,
    select_option_chain,
)
from markeitech.options.probe import IbOptionChainProbe, _valid_ib_float


def chain(
    *,
    exchange: str = "SMART",
    trading_class: str = "SPY",
    expirations: tuple[str, ...] = ("20260728",),
    strikes: tuple[str, ...] = ("630", "631", "632", "633", "634"),
) -> OptionChainDefinition:
    return OptionChainDefinition(
        exchange=exchange,
        underlying_con_id=756733,
        trading_class=trading_class,
        multiplier="100",
        expirations=expirations,
        strikes=tuple(Decimal(value) for value in strikes),
    )


def test_select_option_chain_requires_exact_expiry_exchange_and_class() -> None:
    selected = select_option_chain(
        (
            chain(exchange="CBOE"),
            chain(trading_class="SPY1"),
            chain(),
        ),
        expiry="20260728",
        exchange="SMART",
        trading_class="SPY",
    )

    assert selected.exchange == "SMART"
    assert selected.trading_class == "SPY"


def test_select_option_chain_rejects_missing_zero_dte_expiry() -> None:
    with pytest.raises(ValueError, match="no option chain found"):
        select_option_chain(
            (chain(expirations=("20260729",)),),
            expiry="20260728",
            exchange="SMART",
            trading_class="SPY",
        )


def test_select_atm_strikes_builds_bounded_centered_window() -> None:
    selected = select_atm_strikes(
        tuple(Decimal(value) for value in ("629", "630", "631", "632", "633", "634")),
        spot=Decimal("631.40"),
        strikes_each_side=2,
    )

    assert selected == (
        Decimal("629"),
        Decimal("630"),
        Decimal("631"),
        Decimal("632"),
        Decimal("633"),
    )


def test_select_atm_strikes_keeps_target_size_near_chain_edge() -> None:
    selected = select_atm_strikes(
        tuple(Decimal(value) for value in ("630", "631", "632", "633", "634")),
        spot=Decimal("629.75"),
        strikes_each_side=1,
    )

    assert selected == (Decimal("630"), Decimal("631"), Decimal("632"))


def test_build_probe_report_exposes_quote_and_greeks_coverage() -> None:
    config = OptionChainProbeConfig(
        host="127.0.0.1",
        port=4002,
        client_id=21,
        expiry=date(2026, 7, 28),
    )
    with_data = OptionContractObservation(
        request_id=10_000,
        local_symbol="SPY   260728C00632000",
        right="C",
        strike=Decimal("632"),
        bid=1.2,
        ask=1.22,
        option_computations={"MODEL_OPTION": {"delta": 0.51}},
    )
    without_data = OptionContractObservation(
        request_id=10_001,
        local_symbol="SPY   260728P00632000",
        right="P",
        strike=Decimal("632"),
    )

    report = build_probe_report(
        config=config,
        spot=Decimal("632.10"),
        chain=chain(),
        selected_strikes=(Decimal("632"),),
        observations=(with_data, without_data),
        errors=(),
    )

    assert report["purpose"] == "read_only_spy_0dte_capability_probe"
    assert report["coverage"] == {
        "requested_contracts": 2,
        "contracts_with_quotes": 1,
        "contracts_with_greeks": 1,
        "quote_pct": 50.0,
        "greeks_pct": 50.0,
    }


@pytest.mark.parametrize(
    ("right", "accepted_tick", "ignored_tick"),
    (
        (
            "C",
            TickTypeEnum.OPTION_CALL_OPEN_INTEREST,
            TickTypeEnum.OPTION_PUT_OPEN_INTEREST,
        ),
        (
            "P",
            TickTypeEnum.OPTION_PUT_OPEN_INTEREST,
            TickTypeEnum.OPTION_CALL_OPEN_INTEREST,
        ),
    ),
)
def test_open_interest_ignores_the_opposite_option_side(
    right: str,
    accepted_tick: int,
    ignored_tick: int,
) -> None:
    probe = IbOptionChainProbe(
        OptionChainProbeConfig(
            host="127.0.0.1",
            port=4002,
            client_id=21,
            expiry=date(2026, 7, 28),
        )
    )
    observation = OptionContractObservation(
        request_id=10_000,
        local_symbol=f"SPY   260728{right}00632000",
        right=right,
        strike=Decimal("632"),
    )
    probe._observations_by_request[observation.request_id] = observation

    probe.tickSize(observation.request_id, accepted_tick, Decimal("1234"))
    probe.tickSize(observation.request_id, ignored_tick, Decimal("0"))

    assert observation.open_interest == Decimal("1234")


@pytest.mark.parametrize("value", (None, float("nan"), float("inf"), 1.7976931348623157e308))
def test_ib_missing_float_values_are_normalized_to_none(value: float | None) -> None:
    assert _valid_ib_float(value) is None
