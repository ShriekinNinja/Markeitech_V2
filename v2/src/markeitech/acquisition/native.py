from __future__ import annotations

from typing import Protocol

from nautilus_trader.model import BarType, InstrumentId

from markeitech.acquisition.demand import FeedKind, FeedRequirement


class NativeSubscriptionActor(Protocol):
    def subscribe_instrument(
        self,
        instrument_id: InstrumentId,
        *,
        params: dict | None = None,
    ) -> None: ...

    def unsubscribe_instrument(
        self,
        instrument_id: InstrumentId,
        *,
        params: dict | None = None,
    ) -> None: ...

    def subscribe_quotes(
        self,
        instrument_id: InstrumentId,
        *,
        params: dict | None = None,
    ) -> None: ...

    def unsubscribe_quotes(
        self,
        instrument_id: InstrumentId,
        *,
        params: dict | None = None,
    ) -> None: ...

    def subscribe_trades(
        self,
        instrument_id: InstrumentId,
        *,
        params: dict | None = None,
    ) -> None: ...

    def unsubscribe_trades(
        self,
        instrument_id: InstrumentId,
        *,
        params: dict | None = None,
    ) -> None: ...

    def subscribe_bars(self, bar_type: BarType, *, params: dict | None = None) -> None: ...

    def unsubscribe_bars(self, bar_type: BarType, *, params: dict | None = None) -> None: ...

    def subscribe_instrument_status(
        self,
        instrument_id: InstrumentId,
        *,
        params: dict | None = None,
    ) -> None: ...

    def unsubscribe_instrument_status(
        self,
        instrument_id: InstrumentId,
        *,
        params: dict | None = None,
    ) -> None: ...

    def subscribe_option_greeks(
        self,
        instrument_id: InstrumentId,
        *,
        params: dict | None = None,
    ) -> None: ...

    def unsubscribe_option_greeks(
        self,
        instrument_id: InstrumentId,
        *,
        params: dict | None = None,
    ) -> None: ...


class UnsupportedNativeFeedError(ValueError):
    pass


class NautilusSubscriptionPort:
    """Translates simple provider-neutral requirements into native actor calls."""

    def __init__(self, actor: NativeSubscriptionActor) -> None:
        self._actor = actor

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
            getattr(self._actor, f"{prefix}_bars")(bar_type, params=parameters)
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
        getattr(self._actor, f"{prefix}_{method_suffix}")(instrument_id, params=parameters)
