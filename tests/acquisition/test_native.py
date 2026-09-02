from __future__ import annotations

import pytest

from markeitech.acquisition import (
    FeedKind,
    FeedRequirement,
    NautilusSubscriptionPort,
    UnsupportedNativeFeedError,
)


class RecordingActor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None, dict]] = []

    def __getattr__(self, name: str):  # noqa: ANN204
        if not name.startswith(("subscribe_", "unsubscribe_")):
            raise AttributeError(name)

        def record(value, *, client_id=None, params=None) -> None:  # noqa: ANN001
            self.calls.append(
                (name, str(value), None if client_id is None else str(client_id), params or {}),
            )

        return record


@pytest.mark.parametrize(
    "kind,suffix",
    [
        (FeedKind.INSTRUMENT, "instrument"),
        (FeedKind.QUOTES, "quotes"),
        (FeedKind.TRADES, "trades"),
        (FeedKind.INSTRUMENT_STATUS, "instrument_status"),
        (FeedKind.OPTION_GREEKS, "option_greeks"),
    ],
)
def test_simple_requirements_map_to_native_actor_calls(kind: FeedKind, suffix: str) -> None:
    actor = RecordingActor()
    port = NautilusSubscriptionPort(actor)
    requirement = FeedRequirement("SPY.ARCA", kind, parameters={"source": "test"})

    port.subscribe(requirement)
    port.unsubscribe(requirement)

    assert actor.calls == [
        (f"subscribe_{suffix}", "SPY.ARCA", "IB", {"source": "test"}),
        (f"unsubscribe_{suffix}", "SPY.ARCA", "IB", {"source": "test"}),
    ]


def test_bar_selector_maps_to_native_bar_type() -> None:
    actor = RecordingActor()
    port = NautilusSubscriptionPort(actor)
    requirement = FeedRequirement("SPY.ARCA", FeedKind.BARS, selector="5-MINUTE-LAST-EXTERNAL")

    port.subscribe(requirement)
    port.unsubscribe(requirement)

    assert actor.calls == [
        ("subscribe_bars", "SPY.ARCA-5-MINUTE-LAST-EXTERNAL", "IB", {}),
        ("unsubscribe_bars", "SPY.ARCA-5-MINUTE-LAST-EXTERNAL", "IB", {}),
    ]


@pytest.mark.parametrize("kind", [FeedKind.BOOK, FeedKind.OPTION_CHAIN])
def test_richer_native_feeds_are_rejected_until_their_contracts_exist(kind: FeedKind) -> None:
    port = NautilusSubscriptionPort(RecordingActor())

    with pytest.raises(UnsupportedNativeFeedError, match="richer native subscription contract"):
        port.subscribe(FeedRequirement("SPY.ARCA", kind))
