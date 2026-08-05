from __future__ import annotations

import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from math import isfinite
from typing import Any

from ibapi.client import EClient
from ibapi.common import TickAttrib
from ibapi.contract import Contract, ContractDetails
from ibapi.ticktype import TickTypeEnum
from ibapi.wrapper import EWrapper

INFORMATIONAL_IB_ERROR_CODES = frozenset(
    {
        2104,  # Market data farm connection is OK.
        2106,  # Historical data farm connection is OK.
        2107,  # Historical data farm is inactive until needed.
        2108,  # Market data farm is inactive until needed.
        2158,  # Security definition farm connection is OK.
    }
)


@dataclass(frozen=True)
class OptionChainProbeConfig:
    host: str
    port: int
    client_id: int
    expiry: date
    strikes_each_side: int = 3
    observation_seconds: float = 5.0
    request_timeout_seconds: float = 60.0
    symbol: str = "SPY"
    exchange: str = "SMART"
    primary_exchange: str = "ARCA"
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.strikes_each_side < 0:
            raise ValueError("strikes_each_side must be non-negative")
        if self.observation_seconds <= 0:
            raise ValueError("observation_seconds must be positive")
        if self.request_timeout_seconds <= 0:
            raise ValueError("request_timeout_seconds must be positive")

    @property
    def expiry_text(self) -> str:
        return self.expiry.strftime("%Y%m%d")


@dataclass(frozen=True)
class OptionChainDefinition:
    exchange: str
    underlying_con_id: int
    trading_class: str
    multiplier: str
    expirations: tuple[str, ...]
    strikes: tuple[Decimal, ...]


@dataclass
class OptionContractObservation:
    request_id: int
    local_symbol: str
    right: str
    strike: Decimal
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    bid_size: Decimal | None = None
    ask_size: Decimal | None = None
    volume: Decimal | None = None
    open_interest: Decimal | None = None
    option_computations: dict[str, dict[str, float | int | None]] = field(
        default_factory=dict,
    )

    @property
    def has_quote(self) -> bool:
        return self.bid is not None and self.ask is not None

    @property
    def has_greeks(self) -> bool:
        return bool(self.option_computations)


def select_option_chain(
    chains: Sequence[OptionChainDefinition],
    *,
    expiry: str,
    exchange: str = "SMART",
    trading_class: str | None = None,
) -> OptionChainDefinition:
    eligible = [
        chain
        for chain in chains
        if expiry in chain.expirations
        and chain.exchange == exchange
        and (trading_class is None or chain.trading_class == trading_class)
    ]
    if not eligible:
        raise ValueError(
            f"no option chain found for expiry={expiry} exchange={exchange} "
            f"trading_class={trading_class or 'any'}"
        )
    return max(eligible, key=lambda chain: len(chain.strikes))


def select_atm_strikes(
    strikes: Sequence[Decimal],
    *,
    spot: Decimal,
    strikes_each_side: int,
) -> tuple[Decimal, ...]:
    if strikes_each_side < 0:
        raise ValueError("strikes_each_side must be non-negative")
    ordered = sorted(set(strikes))
    if not ordered:
        raise ValueError("option chain has no strikes")
    atm_index = min(
        range(len(ordered)),
        key=lambda index: (abs(ordered[index] - spot), ordered[index]),
    )
    start = max(0, atm_index - strikes_each_side)
    end = min(len(ordered), atm_index + strikes_each_side + 1)
    target_size = min(len(ordered), strikes_each_side * 2 + 1)
    if end - start < target_size:
        if start == 0:
            end = min(len(ordered), target_size)
        else:
            start = max(0, len(ordered) - target_size)
    return tuple(ordered[start:end])


def build_probe_report(
    *,
    config: OptionChainProbeConfig,
    spot: Decimal,
    chain: OptionChainDefinition,
    selected_strikes: Sequence[Decimal],
    observations: Sequence[OptionContractObservation],
    errors: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    ordered = sorted(observations, key=lambda item: (item.strike, item.right))
    quote_count = sum(item.has_quote for item in ordered)
    greeks_count = sum(item.has_greeks for item in ordered)
    return {
        "status": "complete",
        "purpose": "read_only_spy_0dte_capability_probe",
        "underlying": {
            "symbol": config.symbol,
            "spot": float(spot),
            "exchange": config.exchange,
            "primary_exchange": config.primary_exchange,
        },
        "chain": {
            "expiry": config.expiry_text,
            "exchange": chain.exchange,
            "trading_class": chain.trading_class,
            "multiplier": chain.multiplier,
            "available_strikes": len(chain.strikes),
            "selected_strikes": [float(value) for value in selected_strikes],
        },
        "coverage": {
            "requested_contracts": len(ordered),
            "contracts_with_quotes": quote_count,
            "contracts_with_greeks": greeks_count,
            "quote_pct": _percentage(quote_count, len(ordered)),
            "greeks_pct": _percentage(greeks_count, len(ordered)),
        },
        "contracts": [
            {
                "local_symbol": item.local_symbol,
                "right": item.right,
                "strike": float(item.strike),
                "bid": item.bid,
                "ask": item.ask,
                "last": item.last,
                "bid_size": _optional_float(item.bid_size),
                "ask_size": _optional_float(item.ask_size),
                "volume": _optional_float(item.volume),
                "open_interest": _optional_float(item.open_interest),
                "option_computations": item.option_computations,
            }
            for item in ordered
        ],
        "ib_errors": list(errors),
    }


class IbOptionChainProbe(EWrapper, EClient):
    UNDERLYING_CONTRACT_REQUEST_ID = 10
    UNDERLYING_MARKET_DATA_REQUEST_ID = 20
    OPTION_CHAIN_REQUEST_ID = 30
    OPTION_CONTRACT_REQUEST_START = 1_000
    OPTION_MARKET_DATA_REQUEST_START = 10_000

    def __init__(self, config: OptionChainProbeConfig) -> None:
        EWrapper.__init__(self)
        EClient.__init__(self, self)
        self.config = config
        self.connected = threading.Event()
        self.underlying_contract_complete = threading.Event()
        self.spot_available = threading.Event()
        self.option_chain_complete = threading.Event()
        self._underlying_details: list[ContractDetails] = []
        self._underlying_prices: dict[str, float] = {}
        self._chains: list[OptionChainDefinition] = []
        self._contract_details_by_request: dict[int, list[ContractDetails]] = {}
        self._contract_events: dict[int, threading.Event] = {}
        self._observations_by_request: dict[int, OptionContractObservation] = {}
        self.errors: list[dict[str, Any]] = []

    def execute(self) -> dict[str, Any]:
        network_thread: threading.Thread | None = None
        market_data_request_ids: list[int] = []
        try:
            self.connect(self.config.host, self.config.port, self.config.client_id)
            network_thread = threading.Thread(
                target=self.run,
                name="markeitech-option-chain-probe",
                daemon=True,
            )
            network_thread.start()
            self._wait(self.connected, "IB connection")

            self.reqContractDetails(
                self.UNDERLYING_CONTRACT_REQUEST_ID,
                self._underlying_contract(),
            )
            self._wait(self.underlying_contract_complete, "SPY contract details")
            underlying = self._select_underlying()

            self.reqMktData(
                self.UNDERLYING_MARKET_DATA_REQUEST_ID,
                underlying,
                "",
                False,
                False,
                [],
            )
            self._wait(self.spot_available, "SPY market price")
            spot = self._spot()
            self.cancelMktData(self.UNDERLYING_MARKET_DATA_REQUEST_ID)

            self.reqSecDefOptParams(
                self.OPTION_CHAIN_REQUEST_ID,
                underlying.symbol,
                "",
                underlying.secType,
                underlying.conId,
            )
            self._wait(self.option_chain_complete, "SPY option-chain definition")
            chain = select_option_chain(
                self._chains,
                expiry=self.config.expiry_text,
                exchange=self.config.exchange,
                trading_class=self.config.symbol,
            )
            selected_strikes = select_atm_strikes(
                chain.strikes,
                spot=spot,
                strikes_each_side=self.config.strikes_each_side,
            )
            qualified = self._qualify_options(chain, selected_strikes)
            for offset, contract in enumerate(qualified):
                request_id = self.OPTION_MARKET_DATA_REQUEST_START + offset
                observation = OptionContractObservation(
                    request_id=request_id,
                    local_symbol=contract.localSymbol,
                    right=contract.right,
                    strike=Decimal(str(contract.strike)),
                )
                self._observations_by_request[request_id] = observation
                market_data_request_ids.append(request_id)
                self.reqMktData(
                    request_id,
                    contract,
                    "100,101,106",
                    False,
                    False,
                    [],
                )

            time.sleep(self.config.observation_seconds)
            return build_probe_report(
                config=self.config,
                spot=spot,
                chain=chain,
                selected_strikes=selected_strikes,
                observations=tuple(self._observations_by_request.values()),
                errors=self.errors,
            )
        finally:
            if self.isConnected():
                for request_id in market_data_request_ids:
                    self.cancelMktData(request_id)
                self.disconnect()
            if network_thread is not None:
                network_thread.join(timeout=2.0)

    def nextValidId(self, orderId: int) -> None:  # noqa: N802
        del orderId
        self.connected.set()

    def contractDetails(  # noqa: N802
        self,
        reqId: int,
        contractDetails: ContractDetails,
    ) -> None:
        if reqId == self.UNDERLYING_CONTRACT_REQUEST_ID:
            self._underlying_details.append(contractDetails)
            return
        self._contract_details_by_request.setdefault(reqId, []).append(contractDetails)

    def contractDetailsEnd(self, reqId: int) -> None:  # noqa: N802
        if reqId == self.UNDERLYING_CONTRACT_REQUEST_ID:
            self.underlying_contract_complete.set()
            return
        event = self._contract_events.get(reqId)
        if event is not None:
            event.set()

    def securityDefinitionOptionParameter(  # noqa: N802
        self,
        reqId: int,
        exchange: str,
        underlyingConId: int,
        tradingClass: str,
        multiplier: str,
        expirations: set[str],
        strikes: set[float],
    ) -> None:
        if reqId != self.OPTION_CHAIN_REQUEST_ID:
            return
        self._chains.append(
            OptionChainDefinition(
                exchange=exchange,
                underlying_con_id=underlyingConId,
                trading_class=tradingClass,
                multiplier=multiplier,
                expirations=tuple(sorted(expirations)),
                strikes=tuple(sorted(Decimal(str(value)) for value in strikes)),
            )
        )

    def securityDefinitionOptionParameterEnd(self, reqId: int) -> None:  # noqa: N802
        if reqId == self.OPTION_CHAIN_REQUEST_ID:
            self.option_chain_complete.set()

    def tickPrice(  # noqa: N802
        self,
        reqId: int,
        tickType: int,
        price: float,
        attrib: TickAttrib,
    ) -> None:
        del attrib
        if price < 0:
            return
        if reqId == self.UNDERLYING_MARKET_DATA_REQUEST_ID:
            self._record_underlying_price(tickType, price)
            return
        observation = self._observations_by_request.get(reqId)
        if observation is None:
            return
        if tickType in {TickTypeEnum.BID, TickTypeEnum.DELAYED_BID}:
            observation.bid = price
        elif tickType in {TickTypeEnum.ASK, TickTypeEnum.DELAYED_ASK}:
            observation.ask = price
        elif tickType in {TickTypeEnum.LAST, TickTypeEnum.DELAYED_LAST}:
            observation.last = price

    def tickSize(self, reqId: int, tickType: int, size: Decimal) -> None:  # noqa: N802
        observation = self._observations_by_request.get(reqId)
        if observation is None:
            return
        if tickType == TickTypeEnum.BID_SIZE:
            observation.bid_size = size
        elif tickType == TickTypeEnum.ASK_SIZE:
            observation.ask_size = size
        elif tickType == TickTypeEnum.VOLUME:
            observation.volume = size
        elif (
            tickType == TickTypeEnum.OPTION_CALL_OPEN_INTEREST
            and observation.right == "C"
        ) or (
            tickType == TickTypeEnum.OPTION_PUT_OPEN_INTEREST
            and observation.right == "P"
        ):
            observation.open_interest = size

    def tickOptionComputation(  # noqa: N802
        self,
        reqId: int,
        tickType: int,
        tickAttrib: int,
        impliedVol: float,
        delta: float,
        optPrice: float,
        pvDividend: float,
        gamma: float,
        vega: float,
        theta: float,
        undPrice: float,
    ) -> None:
        observation = self._observations_by_request.get(reqId)
        if observation is None:
            return
        observation.option_computations[TickTypeEnum.toStr(tickType)] = {
            "tick_attrib": tickAttrib,
            "implied_volatility": _valid_ib_float(impliedVol),
            "delta": _valid_ib_float(delta),
            "option_price": _valid_ib_float(optPrice),
            "present_value_dividend": _valid_ib_float(pvDividend),
            "gamma": _valid_ib_float(gamma),
            "vega": _valid_ib_float(vega),
            "theta": _valid_ib_float(theta),
            "underlying_price": _valid_ib_float(undPrice),
        }

    def error(  # type: ignore[override]
        self,
        reqId: int,
        errorTime: int,
        errorCode: int,
        errorString: str,
        advancedOrderRejectJson: str = "",
    ) -> None:
        del errorTime
        if errorCode in INFORMATIONAL_IB_ERROR_CODES:
            return
        self.errors.append(
            {
                "request_id": reqId,
                "code": errorCode,
                "message": errorString,
                "advanced_order_reject": advancedOrderRejectJson or None,
            }
        )

    def _wait(self, event: threading.Event, description: str) -> None:
        if not event.wait(self.config.request_timeout_seconds):
            raise TimeoutError(f"timed out waiting for {description}")

    def _underlying_contract(self) -> Contract:
        contract = Contract()
        contract.symbol = self.config.symbol
        contract.secType = "STK"
        contract.exchange = self.config.exchange
        contract.primaryExchange = self.config.primary_exchange
        contract.currency = self.config.currency
        return contract

    def _select_underlying(self) -> Contract:
        if not self._underlying_details:
            raise RuntimeError("IB returned no SPY contract details")
        matching = [
            details.contract
            for details in self._underlying_details
            if details.contract.symbol == self.config.symbol and details.contract.secType == "STK"
        ]
        if not matching:
            raise RuntimeError("IB returned no matching SPY stock contract")
        return matching[0]

    def _record_underlying_price(self, tick_type: int, price: float) -> None:
        if tick_type in {TickTypeEnum.LAST, TickTypeEnum.DELAYED_LAST}:
            self._underlying_prices["last"] = price
            self.spot_available.set()
        elif tick_type in {TickTypeEnum.BID, TickTypeEnum.DELAYED_BID}:
            self._underlying_prices["bid"] = price
        elif tick_type in {TickTypeEnum.ASK, TickTypeEnum.DELAYED_ASK}:
            self._underlying_prices["ask"] = price
        if {"bid", "ask"} <= self._underlying_prices.keys():
            self.spot_available.set()

    def _spot(self) -> Decimal:
        if "last" in self._underlying_prices:
            return Decimal(str(self._underlying_prices["last"]))
        bid = self._underlying_prices.get("bid")
        ask = self._underlying_prices.get("ask")
        if bid is None or ask is None:
            raise RuntimeError("SPY market data did not produce a usable spot price")
        return (Decimal(str(bid)) + Decimal(str(ask))) / 2

    def _qualify_options(
        self,
        chain: OptionChainDefinition,
        strikes: Sequence[Decimal],
    ) -> tuple[Contract, ...]:
        requests: list[int] = []
        request_id = self.OPTION_CONTRACT_REQUEST_START
        for strike in strikes:
            for right in ("C", "P"):
                contract = Contract()
                contract.symbol = self.config.symbol
                contract.secType = "OPT"
                contract.exchange = self.config.exchange
                contract.currency = self.config.currency
                contract.lastTradeDateOrContractMonth = self.config.expiry_text
                contract.strike = float(strike)
                contract.right = right
                contract.multiplier = chain.multiplier
                contract.tradingClass = chain.trading_class
                self._contract_events[request_id] = threading.Event()
                self.reqContractDetails(request_id, contract)
                requests.append(request_id)
                request_id += 1

        qualified: list[Contract] = []
        for current in requests:
            self._wait(self._contract_events[current], f"option contract request {current}")
            details = self._contract_details_by_request.get(current, [])
            if len(details) != 1:
                raise RuntimeError(
                    f"expected one option contract for request {current}, got {len(details)}"
                )
            qualified.append(details[0].contract)
        return tuple(qualified)


def _percentage(value: int, total: int) -> float:
    return round(value / total * 100, 1) if total else 0.0


def _optional_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _valid_ib_float(value: float | None) -> float | None:
    return value if value is not None and isfinite(value) and abs(value) < 1e300 else None
