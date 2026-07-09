from __future__ import annotations

from datetime import date

from pydantic import Field, field_validator, model_validator

from markeitech.domain.base import VersionedDomainModel, require_iana_timezone


class NQContractConfig(VersionedDomainModel):
    root_symbol: str = Field(default="NQ")
    exchange: str = Field(default="CME")
    expiry: date
    instrument_id: str = Field(min_length=1)
    ib_symbol: str = Field(default="NQ")
    ib_exchange: str = Field(default="CME")
    ib_security_type: str = Field(default="FUT")
    ib_last_trade_date_or_contract_month: str = Field(min_length=6)
    session_timezone: str = Field(default="America/New_York")

    @field_validator("root_symbol", "ib_symbol")
    @classmethod
    def _must_be_nq(cls, value: str) -> str:
        if value.upper() != "NQ":
            raise ValueError("initial contract support is NQ only")
        return value.upper()

    @field_validator("exchange", "ib_exchange")
    @classmethod
    def _exchange_must_be_cme(cls, value: str) -> str:
        if value.upper() != "CME":
            raise ValueError("initial NQ futures support requires CME exchange")
        return value.upper()

    @field_validator("ib_security_type")
    @classmethod
    def _security_type_must_be_future(cls, value: str) -> str:
        if value.upper() != "FUT":
            raise ValueError("initial contract support requires individual FUT contracts")
        return value.upper()

    @field_validator("session_timezone")
    @classmethod
    def _session_timezone_must_be_iana(cls, value: str) -> str:
        return require_iana_timezone(value)

    @model_validator(mode="after")
    def _reject_continuous_or_front_month_identity(self) -> NQContractConfig:
        instrument_id_upper = self.instrument_id.upper()
        if self.ib_security_type == "CONTFUT":
            raise ValueError("continuous futures are prohibited for canonical NQ data")
        if instrument_id_upper in {"NQ.CME", "NQ.XCME"}:
            raise ValueError("front-month or continuous NQ identity is prohibited")
        if not instrument_id_upper.startswith("NQ"):
            raise ValueError("NQ instrument id must start with NQ")
        if not instrument_id_upper.endswith((".CME", ".XCME")):
            raise ValueError("NQ instrument id must use CME or XCME venue suffix")
        expiry_text = self.expiry.strftime("%Y%m%d")
        if self.ib_last_trade_date_or_contract_month not in {
            expiry_text,
            expiry_text[:6],
        }:
            raise ValueError("IB expiry must match the configured contract expiry")
        return self

    @property
    def identity_key(self) -> str:
        return f"{self.root_symbol}.{self.exchange}.{self.expiry:%Y%m%d}.{self.instrument_id}"
