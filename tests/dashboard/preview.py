"""Offline visual fixture: a real dashboard lifecycle with explicitly synthetic observations.

Run with ``.venv/bin/python -m tests.dashboard.preview``. No provider, database,
Discord, or model is configured. Ctrl-C stops the node and its dashboard server.
"""

from __future__ import annotations

import math
import time
from dataclasses import asdict

from nautilus_trader.common import Environment
from nautilus_trader.live import LiveNode
from nautilus_trader.model import Bar, BarType, InstrumentId, Price, Quantity, QuoteTick, TraderId

from markeitech.dashboard.actor import DashboardActor, DashboardActorConfig
from markeitech.dashboard.config import DashboardConfig
from markeitech.dashboard.state import DashboardState

_BASES = {
    "ESU6.CME": 6482.25,
    "NQU6.CME": 23714.50,
    "CLV6.NYMEX": 68.42,
    "SPY.ARCA": 647.83,
    "QQQ.NASDAQ": 577.36,
    "^SPX.CBOE": 6481.92,
    "^VIX.CBOE": 15.84,
}


class _PreviewState(DashboardState):
    def snapshot(self) -> dict:
        return {**super().snapshot(), "preview": True}


class _PreviewActor(DashboardActor):
    def on_start(self) -> None:
        self._display = _PreviewState(self._policy, "synthetic")
        super().on_start()
        self._display.set_members(
            [
                {
                    "instrument_id": key,
                    "capabilities": ["watchlist_last"]
                    if key.startswith("^")
                    else ["top_of_book", "watchlist_last"],
                }
                for key in _BASES
            ]
        )
        self._sample = 0
        end = int(time.time()) // 5 * 5
        for stamp in range(end - 80 * 5, end, 5):
            self._emit(stamp)
        self.clock.set_timer_ns("preview-synthetic-data", 5_000_000_000, callback=self._tick)

    def _tick(self, _event) -> None:  # noqa: ANN001
        self._emit(int(time.time()) // 5 * 5)

    def _emit(self, stamp: int) -> None:
        for index, (instrument, base) in enumerate(_BASES.items()):
            scale = base / 6500
            value = base + (math.sin(self._sample / 9) * 3 + self._sample * 0.02) * scale
            opening = value + math.sin(self._sample * 1.8 + index) * scale
            high, low = max(value, opening) + 0.35 * scale, min(value, opening) - 0.35 * scale
            native_price = lambda value: Price.from_str(f"{value:.2f}")  # noqa: E731
            self.on_bar(
                Bar(
                    BarType.from_str(f"{instrument}-5-SECOND-LAST-EXTERNAL"),
                    native_price(opening),
                    native_price(high),
                    native_price(low),
                    native_price(value),
                    Quantity.from_int(100),
                    stamp * 1_000_000_000,
                    stamp * 1_000_000_000,
                )
            )
            if not instrument.startswith("^"):
                self.on_quote(
                    QuoteTick(
                        InstrumentId.from_str(instrument),
                        native_price(value - 0.01),
                        native_price(value + 0.01),
                        Quantity.from_int(1),
                        Quantity.from_int(2),
                        stamp * 1_000_000_000,
                        stamp * 1_000_000_000,
                    )
                )
        self._sample += 1

    def on_stop(self) -> None:
        if "preview-synthetic-data" in self.clock.timer_names():
            self.clock.cancel_timer("preview-synthetic-data")
        super().on_stop()


if __name__ == "__main__":
    node = (
        LiveNode.builder(
            "DASHBOARD-OFFLINE-PREVIEW",
            TraderId.from_str("DASHBOARD-PREVIEW-001"),
            Environment.SANDBOX,
        )
        .with_delay_post_stop_secs(0)
        .build()
    )
    node.add_actor(
        _PreviewActor(
            DashboardActorConfig(dashboard=asdict(DashboardConfig()), watchlist_enabled=False)
        )
    )
    print("OFFLINE PREVIEW: http://127.0.0.1:8765 — synthetic data only", flush=True)
    node.run()
