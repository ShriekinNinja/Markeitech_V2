from __future__ import annotations

from typing import Protocol

from nautilus_trader.model import BarType, ClientId, InstrumentId

from markeitech.acquisition.demand import FeedKind, FeedRequirement


class NativeSubscriptionActor(Protocol):
    """Nautilus actor subscription operations used by the native port."""

    def subscribe_instrument(
        self,
        instrument_id: InstrumentId,
        *,
        client_id: ClientId | None = None,
        params: dict | None = None,
    ) -> None: ...

    def unsubscribe_instrument(
        self,
        instrument_id: InstrumentId,
        *,
        client_id: ClientId | None = None,
        params: dict | None = None,
    ) -> None: ...

    def subscribe_quotes(
        self,
        instrument_id: InstrumentId,
        *,
        client_id: ClientId | None = None,
        params: dict | None = None,
    ) -> None: ...

    def unsubscribe_quotes(
        self,
        instrument_id: InstrumentId,
        *,
        client_id: ClientId | None = None,
        params: dict | None = None,
    ) -> None: ...

    def subscribe_trades(
        self,
        instrument_id: InstrumentId,
        *,
        client_id: ClientId | None = None,
        params: dict | None = None,
    ) -> None: ...

    def unsubscribe_trades(
        self,
        instrument_id: InstrumentId,
        *,
        client_id: ClientId | None = None,
        params: dict | None = None,
    ) -> None: ...

    def subscribe_bars(
        self,
        bar_type: BarType,
        *,
        client_id: ClientId | None = None,
        params: dict | None = None,
    ) -> None: ...

    def unsubscribe_bars(
        self,
        bar_type: BarType,
        *,
        client_id: ClientId | None = None,
        params: dict | None = None,
    ) -> None: ...

    def subscribe_instrument_status(
        self,
        instrument_id: InstrumentId,
        *,
        client_id: ClientId | None = None,
        params: dict | None = None,
    ) -> None: ...

    def unsubscribe_instrument_status(
        self,
        instrument_id: InstrumentId,
        *,
        client_id: ClientId | None = None,
        params: dict | None = None,
    ) -> None: ...

    def subscribe_option_greeks(
        self,
        instrument_id: InstrumentId,
        *,
        client_id: ClientId | None = None,
        params: dict | None = None,
    ) -> None: ...

    def unsubscribe_option_greeks(
        self,
        instrument_id: InstrumentId,
        *,
        client_id: ClientId | None = None,
        params: dict | None = None,
    ) -> None: ...


class UnsupportedNativeFeedError(ValueError):
    """Report a feed that requires a richer native subscription contract."""


class NautilusSubscriptionPort:
    """Translates simple provider-neutral requirements into native actor calls."""

    def __init__(
        self,
        actor: NativeSubscriptionActor,
        client_id: ClientId | None = None,
    ) -> None:
        self._actor = actor
        self._client_id = client_id or ClientId.from_str("IB")

    def subscribe(self, requirement: FeedRequirement) -> None:
        self._dispatch(requirement, subscribe=True)

    def unsubscribe(self, requirement: FeedRequirement) -> None:
        self._dispatch(requirement, subscribe=False)

    def _dispatch(self, requirement: FeedRequirement, *, subscribe: bool) -> None:
        instrument_id = InstrumentId.from_str(requirement.instrument_id)
        parameters = dict(requirement.parameters)
        prefix = "subscribe" if subscribe else "unsubscribe"

        if requirement.kind is FeedKind.BARS:
            bar_type = BarType.from_str(f"{requirement.instrument_id}-{requirement.selector}")
            getattr(self._actor, f"{prefix}_bars")(
                bar_type,
                client_id=self._client_id,
                params=parameters,
            )
            return
        method_suffix = {
            FeedKind.INSTRUMENT: "instrument",
            FeedKind.QUOTES: "quotes",
            FeedKind.TRADES: "trades",
            FeedKind.INSTRUMENT_STATUS: "instrument_status",
            FeedKind.OPTION_GREEKS: "option_greeks",
        }.get(requirement.kind)
        if method_suffix is None:
            raise UnsupportedNativeFeedError(
                f"{requirement.kind.value} requires a richer native subscription contract",
            )
        getattr(self._actor, f"{prefix}_{method_suffix}")(
            instrument_id,
            client_id=self._client_id,
            params=parameters,
        )
