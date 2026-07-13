from __future__ import annotations

from collections.abc import Sequence
from threading import Lock
from typing import Any, Protocol

from nautilus_trader.model.data import CustomData, QuoteTick, TradeTick
from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog

from markeitech.domain.base import utc_datetime_from_unix_ns
from markeitech.domain.market_data import OneMinuteBar
from markeitech.persistence.catalog_data import (
    CanonicalOneMinuteBarRecord,
    canonical_bar_to_record,
    record_to_canonical_bar,
)
from markeitech.persistence.config import PersistenceConfig
from markeitech.persistence.contracts import (
    DataFidelity,
    PersistenceEventIdentity,
    PersistenceEventKind,
)

CatalogEvent = TradeTick | QuoteTick | OneMinuteBar


class CatalogBackend(Protocol):
    def write_data(self, data: list[object]) -> None: ...

    def query(
        self,
        data_cls: type,
        identifiers: list[str] | None = None,
        **kwargs: Any,
    ) -> list[Any]: ...


class NautilusParquetTimeSeriesStore:
    def __init__(
        self,
        config: PersistenceConfig,
        *,
        catalog: CatalogBackend | None = None,
        source: str = "ib",
    ) -> None:
        self._config = config
        self._catalog = catalog or ParquetDataCatalog.from_uri(str(config.catalog_path))
        self._source = source
        self._write_lock = Lock()

    def write(self, events: Sequence[object]) -> tuple[PersistenceEventIdentity, ...]:
        if not events:
            return ()
        if len(events) > self._config.catalog_batch_size:
            raise ValueError(
                f"catalog batch contains {len(events)} events; "
                f"maximum is {self._config.catalog_batch_size}"
            )

        validated = tuple(self._require_supported(event) for event in events)
        identities = tuple(self._identity(event) for event in validated)
        catalog_data = [
            canonical_bar_to_record(event) if isinstance(event, OneMinuteBar) else event
            for event in validated
        ]
        with self._write_lock:
            self._catalog.write_data(catalog_data)
        return identities

    def query_trade_ticks(self, instrument_id: str) -> tuple[TradeTick, ...]:
        with self._write_lock:
            return tuple(self._catalog.query(data_cls=TradeTick, identifiers=[instrument_id]))

    def query_quote_ticks(self, instrument_id: str) -> tuple[QuoteTick, ...]:
        with self._write_lock:
            return tuple(self._catalog.query(data_cls=QuoteTick, identifiers=[instrument_id]))

    def query_one_minute_bars(self, instrument_id: str) -> tuple[OneMinuteBar, ...]:
        with self._write_lock:
            stored = self._catalog.query(
                data_cls=CanonicalOneMinuteBarRecord,
                identifiers=[instrument_id],
            )
        records = [item.data if isinstance(item, CustomData) else item for item in stored]
        return tuple(record_to_canonical_bar(record) for record in records)

    @staticmethod
    def _require_supported(event: object) -> CatalogEvent:
        if not isinstance(event, TradeTick | QuoteTick | OneMinuteBar):
            raise TypeError(f"unsupported catalog event type: {type(event).__name__}")
        if isinstance(event, OneMinuteBar) and not event.is_complete:
            raise ValueError("only completed canonical one-minute bars can be persisted")
        return event

    def _identity(self, event: CatalogEvent) -> PersistenceEventIdentity:
        if isinstance(event, TradeTick):
            event_ts = utc_datetime_from_unix_ns(event.ts_event)
            price = event.price.as_decimal()
            size = event.size.as_decimal()
            return PersistenceEventIdentity(
                event_kind=PersistenceEventKind.TRADE_TICK,
                instrument_id=event.instrument_id.value,
                source=self._source,
                fidelity=DataFidelity.REPORTED,
                dedupe_key=(
                    f"trade:{event.instrument_id}:{event.ts_event}:{price}:{size}:"
                    f"none:{event.trade_id}:{self._source}"
                ),
                event_ts=event_ts,
                event_ts_ns=event.ts_event,
                init_ts=utc_datetime_from_unix_ns(event.ts_init),
                init_ts_ns=event.ts_init,
            )
        if isinstance(event, QuoteTick):
            event_ts = utc_datetime_from_unix_ns(event.ts_event)
            return PersistenceEventIdentity(
                event_kind=PersistenceEventKind.QUOTE_TICK,
                instrument_id=event.instrument_id.value,
                source=self._source,
                fidelity=DataFidelity.REPORTED,
                dedupe_key=(
                    f"quote:{event.instrument_id}:{event.ts_event}:"
                    f"{event.bid_price.as_decimal()}:{event.ask_price.as_decimal()}:"
                    f"{event.bid_size.as_decimal()}:{event.ask_size.as_decimal()}:"
                    f"none:{self._source}"
                ),
                event_ts=event_ts,
                event_ts_ns=event.ts_event,
                init_ts=utc_datetime_from_unix_ns(event.ts_init),
                init_ts_ns=event.ts_init,
            )

        fidelity = (
            DataFidelity.INFERRED if event.source == "classified_ticks" else DataFidelity.REPORTED
        )
        derivation_method = (
            "quote_test_classified_ticks" if fidelity == DataFidelity.INFERRED else None
        )
        return PersistenceEventIdentity(
            event_kind=PersistenceEventKind.ONE_MINUTE_BAR,
            instrument_id=event.instrument_id,
            source=event.source,
            fidelity=fidelity,
            dedupe_key=event.dedupe_key,
            event_ts=event.event_ts,
            event_ts_ns=event.event_ts_ns,
            init_ts=event.ts_init,
            init_ts_ns=event.ts_init_ns,
            derivation_method=derivation_method,
        )

    def identify(self, events: Sequence[object]) -> tuple[PersistenceEventIdentity, ...]:
        validated = tuple(self._require_supported(event) for event in events)
        return tuple(self._identity(event) for event in validated)
