from datetime import date

import pytest
from markeitech.domain import NQContractConfig
from pydantic import ValidationError


def test_explicit_nq_contract_identity() -> None:
    contract = NQContractConfig(
        expiry=date(2026, 9, 18),
        instrument_id="NQU6.CME",
        ib_last_trade_date_or_contract_month="20260918",
    )

    assert contract.identity_key == "NQ.CME.20260918.NQU6.CME"


def test_rejects_continuous_front_month_identity() -> None:
    with pytest.raises(ValidationError, match="front-month or continuous"):
        NQContractConfig(
            expiry=date(2026, 9, 18),
            instrument_id="NQ.CME",
            ib_last_trade_date_or_contract_month="20260918",
        )


def test_rejects_non_nq_contract() -> None:
    with pytest.raises(ValidationError, match="NQ only"):
        NQContractConfig(
            root_symbol="ES",
            ib_symbol="ES",
            expiry=date(2026, 9, 18),
            instrument_id="ESU6.CME",
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
