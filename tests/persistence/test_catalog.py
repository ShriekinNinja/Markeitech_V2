from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from threading import Lock

import pytest
from markeitech.domain import OneMinuteBar
from markeitech.persistence import (
    DataFidelity,
    NautilusParquetTimeSeriesStore,
    PersistenceConfig,
)
from nautilus_trader.model.data import QuoteTick, TradeTick
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.identifiers import InstrumentId, TradeId
from nautilus_trader.model.objects import Price, Quantity

EVENT_NS = 1_786_360_100_123_456_789
INIT_NS = 1_786_360_100_223_456_789


def trade_tick(instrument_id: str = "NQU6.CME", *, offset_ns: int = 0) -> TradeTick:
    return TradeTick(
        instrument_id=InstrumentId.from_str(instrument_id),
        price=Price.from_str("20000.25"),
        size=Quantity.from_str("3.125"),
        aggressor_side=AggressorSide.BUYER,
        trade_id=TradeId(f"trade-{123 + offset_ns}"),
        ts_event=EVENT_NS + offset_ns,
        ts_init=INIT_NS + offset_ns,
    )


def quote_tick(instrument_id: str = "NQU6.CME") -> QuoteTick:
    return QuoteTick(
        instrument_id=InstrumentId.from_str(instrument_id),
        bid_price=Price.from_str("20000.00"),
        ask_price=Price.from_str("20000.50"),
        bid_size=Quantity.from_str("4.25"),
        ask_size=Quantity.from_str("6.75"),
        ts_event=EVENT_NS + 1,
        ts_init=INIT_NS + 1,
    )


def canonical_bar(instrument_id: str = "NQU6.CME") -> OneMinuteBar:
    return OneMinuteBar(
        instrument_id=instrument_id,
        event_ts=datetime(2026, 8, 10, 11, 9, tzinfo=UTC),
        ts_init=datetime(2026, 8, 10, 11, 9, 0, 123456, tzinfo=UTC),
        event_ts_ns=1_786_360_140_000_000_000,
        ts_init_ns=1_786_360_140_123_456_789,
        open_ts=datetime(2026, 8, 10, 11, 8, tzinfo=UTC),
        close_ts=datetime(2026, 8, 10, 11, 9, tzinfo=UTC),
        open=Decimal("20000.125"),
        high=Decimal("20002.875"),
        low=Decimal("19999.625"),
        close=Decimal("20001.375"),
        volume=Decimal("12.50000001"),
        buy_volume=Decimal("7.25000001"),
        sell_volume=Decimal("4.25"),
        unknown_volume=Decimal("1"),
        source="classified_ticks",
    )


@pytest.fixture
def store(tmp_path: Path) -> NautilusParquetTimeSeriesStore:
    config = PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        catalog_batch_size=10,
    )
    return NautilusParquetTimeSeriesStore(config)


def test_native_ticks_round_trip_with_nanosecond_and_decimal_identity(
    store: NautilusParquetTimeSeriesStore,
) -> None:
    trade = trade_tick()
    quote = quote_tick()

    identities = store.write([trade, quote])
    stored_trade = store.query_trade_ticks("NQU6.CME")[0]
    stored_quote = store.query_quote_ticks("NQU6.CME")[0]

    assert stored_trade.ts_event == trade.ts_event
    assert stored_trade.price.as_decimal() == Decimal("20000.25")
    assert stored_trade.size.as_decimal() == Decimal("3.125")
    assert stored_trade.trade_id == trade.trade_id
    assert stored_quote.ts_event == quote.ts_event
    assert stored_quote.bid_size.as_decimal() == Decimal("4.25")
    assert stored_quote.ask_size.as_decimal() == Decimal("6.75")
    assert all(identity.fidelity == DataFidelity.REPORTED for identity in identities)


def test_canonical_bar_custom_data_round_trip_preserves_all_fields(
    store: NautilusParquetTimeSeriesStore,
) -> None:
    bar = canonical_bar()

    identity = store.write([bar])[0]
    stored = store.query_one_minute_bars("NQU6.CME")[0]

    assert stored == bar
    assert stored.ts_init_ns == bar.ts_init_ns
    assert stored.volume == Decimal("12.50000001")
    assert stored.buy_volume == Decimal("7.25000001")
    assert stored.dedupe_key == bar.dedupe_key
    assert identity.fidelity == DataFidelity.INFERRED
    assert identity.derivation_method == "quote_test_classified_ticks"


def test_catalog_keeps_instruments_isolated(store: NautilusParquetTimeSeriesStore) -> None:
    store.write([trade_tick("NQU6.CME"), trade_tick("ESU6.CME")])

    assert len(store.query_trade_ticks("NQU6.CME")) == 1
    assert len(store.query_trade_ticks("ESU6.CME")) == 1


def test_distinct_ticks_with_shared_boundary_timestamp_are_consolidated(
    store: NautilusParquetTimeSeriesStore,
) -> None:
    first = trade_tick()
    boundary = TradeTick(
        instrument_id=first.instrument_id,
        price=Price.from_str("20000.375"),
        size=first.size,
        aggressor_side=first.aggressor_side,
        trade_id=TradeId("trade-boundary"),
        ts_event=first.ts_event + 1,
        ts_init=first.ts_init + 1,
    )
    second = TradeTick(
        instrument_id=first.instrument_id,
        price=Price.from_str("20000.50"),
        size=first.size,
        aggressor_side=first.aggressor_side,
        trade_id=TradeId("trade-124"),
        ts_event=first.ts_event + 2,
        ts_init=boundary.ts_init,
    )

    store.write([first, boundary])
    store.write([second])

    stored = store.query_trade_ticks("NQU6.CME")
    assert {tick.trade_id for tick in stored} == {
        first.trade_id,
        boundary.trade_id,
        second.trade_id,
    }
    assert len(store._catalog.get_intervals(TradeTick, "NQU6.CME")) == 1


def test_empty_batch_is_harmless(store: NautilusParquetTimeSeriesStore) -> None:
    assert store.write([]) == ()


def test_unsupported_and_provisional_events_fail_before_catalog_write(
    store: NautilusParquetTimeSeriesStore,
) -> None:
    with pytest.raises(TypeError, match="unsupported catalog event type"):
        store.write([object()])

    with pytest.raises(ValueError, match="only completed"):
        store.write([canonical_bar().model_copy(update={"is_complete": False})])


def test_batch_limit_is_enforced(store: NautilusParquetTimeSeriesStore) -> None:
    with pytest.raises(ValueError, match="maximum is 10"):
        store.write([trade_tick(offset_ns=index) for index in range(11)])


class DetectingCatalog:
    def __init__(self, *, fail: bool = False) -> None:
        self._state_lock = Lock()
        self._active_writes = 0
        self.max_active_writes = 0
        self.fail = fail

    def write_data(self, data: list[object], **kwargs: object) -> None:
        if self.fail:
            raise RuntimeError("catalog unavailable")
        with self._state_lock:
            self._active_writes += 1
            self.max_active_writes = max(self.max_active_writes, self._active_writes)
        time.sleep(0.01)
        with self._state_lock:
            self._active_writes -= 1

    def get_intervals(
        self,
        data_cls: type,
        identifier: str | None = None,
    ) -> list[tuple[int, int]]:
        return []

    def consolidate_data(self, *args: object, **kwargs: object) -> None:
        return None


def test_store_serializes_concurrent_catalog_writes(tmp_path: Path) -> None:
    catalog = DetectingCatalog()
    store = NautilusParquetTimeSeriesStore(
        PersistenceConfig(
            catalog_path=tmp_path / "catalog",
            metadata_path=tmp_path / "metadata.sqlite3",
        ),
        catalog=catalog,
    )

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(store.write, [trade_tick()]) for _ in range(8)]
        for future in futures:
            assert len(future.result()) == 1

    assert catalog.max_active_writes == 1


def test_catalog_failure_propagates_without_success_result(tmp_path: Path) -> None:
    store = NautilusParquetTimeSeriesStore(
        PersistenceConfig(
            catalog_path=tmp_path / "catalog",
            metadata_path=tmp_path / "metadata.sqlite3",
        ),
        catalog=DetectingCatalog(fail=True),
    )

    with pytest.raises(RuntimeError, match="catalog unavailable"):
        store.write([trade_tick()])
