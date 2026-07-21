from __future__ import annotations

from collections import defaultdict
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
    def write_data(self, data: list[object], **kwargs: Any) -> None: ...

    def get_intervals(
        self,
        data_cls: type,
        identifier: str | None = None,
    ) -> list[tuple[int, int]]: ...

    def consolidate_data(
        self,
        data_cls: type,
        identifier: str | None = None,
        start: int | None = None,
        end: int | None = None,
        ensure_contiguous_files: bool = True,
        deduplicate: bool = False,
    ) -> None: ...

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
        validated = tuple(self._require_supported(event) for event in events)
        identities = tuple(self._identity(event) for event in validated)
        if len(events) > self._config.catalog_batch_size and not _shares_init_timestamp(identities):
            raise ValueError(
                f"catalog batch contains {len(events)} events; "
                f"maximum is {self._config.catalog_batch_size}"
            )
        catalog_data = [
            canonical_bar_to_record(event) if isinstance(event, OneMinuteBar) else event
            for event in validated
        ]
        with self._write_lock:
            repairs = self._overlapping_groups(catalog_data)
            if repairs and self._contains_all(validated, identities):
                return identities
            self._catalog.write_data(
                catalog_data,
                skip_disjoint_check=bool(repairs),
            )
            for data_cls, identifier, bucket_start_ns, bucket_end_ns in repairs:
                if data_cls in {QuoteTick, TradeTick}:
                    continue
                self._catalog.consolidate_data(
                    data_cls=data_cls,
                    identifier=identifier,
                    start=bucket_start_ns,
                    end=bucket_end_ns - 1,
                    ensure_contiguous_files=False,
                    deduplicate=True,
                )
        return identities

    def _contains_all(
        self,
        events: tuple[CatalogEvent, ...],
        identities: tuple[PersistenceEventIdentity, ...],
    ) -> bool:
        expected = {identity.dedupe_key for identity in identities}
        grouped: dict[tuple[type, str], list[CatalogEvent]] = defaultdict(list)
        for event in events:
            data_cls = (
                CanonicalOneMinuteBarRecord
                if isinstance(event, OneMinuteBar)
                else type(event)
            )
            grouped[(data_cls, str(event.instrument_id))].append(event)

        observed: set[str] = set()
        for (data_cls, identifier), values in grouped.items():
            start = min(_catalog_init_ns(value) for value in values)
            end = max(_catalog_init_ns(value) for value in values) + 1
            stored = self._catalog.query(
                data_cls=data_cls,
                identifiers=[identifier],
                start=start,
                end=end,
            )
            for item in stored:
                value = item.data if isinstance(item, CustomData) else item
                event = (
                    record_to_canonical_bar(value)
                    if isinstance(value, CanonicalOneMinuteBarRecord)
                    else value
                )
                observed.add(self._identity(self._require_supported(event)).dedupe_key)
        return expected <= observed

    def _overlapping_groups(
        self,
        catalog_data: list[object],
    ) -> tuple[tuple[type, str, int, int], ...]:
        grouped: dict[tuple[type, str, int], list[int]] = defaultdict(list)
        interval_ns = self._config.persistence_batch_interval_seconds * 1_000_000_000
        for event in catalog_data:
            init_ns = int(event.ts_init)
            identifier = str(event.instrument_id)
            bucket_start_ns = (init_ns // interval_ns) * interval_ns
            grouped[(type(event), identifier, bucket_start_ns)].append(init_ns)

        repairs: list[tuple[type, str, int, int]] = []
        for (data_cls, identifier, bucket_start_ns), timestamps in grouped.items():
            new_start, new_end = min(timestamps), max(timestamps)
            intervals = self._catalog.get_intervals(data_cls, identifier)
            if any(start <= new_end and new_start <= end for start, end in intervals):
                repairs.append(
                    (data_cls, identifier, bucket_start_ns, bucket_start_ns + interval_ns)
                )
        return tuple(repairs)

    def query_trade_ticks(self, instrument_id: str) -> tuple[TradeTick, ...]:
        with self._write_lock:
            stored = self._catalog.query(data_cls=TradeTick, identifiers=[instrument_id])
        return tuple(self._deduplicate_native(stored))

    def query_quote_ticks(self, instrument_id: str) -> tuple[QuoteTick, ...]:
        with self._write_lock:
            stored = self._catalog.query(data_cls=QuoteTick, identifiers=[instrument_id])
        return tuple(self._deduplicate_native(stored))

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

    def _deduplicate_native(
        self,
        events: Sequence[TradeTick | QuoteTick],
    ) -> tuple[TradeTick | QuoteTick, ...]:
        unique: dict[str, TradeTick | QuoteTick] = {}
        for event in events:
            key = self._identity(event).dedupe_key
            existing = unique.get(key)
            if existing is None or int(event.ts_init) < int(existing.ts_init):
                unique[key] = event
        return tuple(
            sorted(
                unique.values(),
                key=lambda event: (int(event.ts_init), self._identity(event).dedupe_key),
            )
        )


def _shares_init_timestamp(identities: Sequence[PersistenceEventIdentity]) -> bool:
    return len({identity.init_ts_ns for identity in identities}) == 1


def _catalog_init_ns(event: CatalogEvent) -> int:
    return event.ts_init_ns if isinstance(event, OneMinuteBar) else int(event.ts_init)
