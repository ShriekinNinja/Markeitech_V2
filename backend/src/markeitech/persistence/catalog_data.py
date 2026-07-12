from decimal import Decimal

from nautilus_trader.model.custom import customdataclass
from nautilus_trader.model.identifiers import InstrumentId

from markeitech.domain.base import unix_ns_from_utc_datetime, utc_datetime_from_unix_ns
from markeitech.domain.market_data import OneMinuteBar


@customdataclass
class CanonicalOneMinuteBarRecord:
    instrument_id: InstrumentId
    schema_version: str
    interval: str
    open_ts_ns: int
    close_ts_ns: int
    open: str
    high: str
    low: str
    close: str
    volume: str
    buy_volume: str
    sell_volume: str
    unknown_volume: str
    source: str
    is_revision: bool
    is_complete: bool
    dedupe_key: str


def canonical_bar_to_record(bar: OneMinuteBar) -> CanonicalOneMinuteBarRecord:
    ts_event = bar.event_ts_ns or unix_ns_from_utc_datetime(bar.event_ts)
    ts_init = bar.ts_init_ns or unix_ns_from_utc_datetime(bar.ts_init)
    return CanonicalOneMinuteBarRecord(
        instrument_id=InstrumentId.from_str(bar.instrument_id),
        schema_version=bar.schema_version,
        interval=bar.interval.value,
        open_ts_ns=unix_ns_from_utc_datetime(bar.open_ts),
        close_ts_ns=unix_ns_from_utc_datetime(bar.close_ts),
        open=str(bar.open),
        high=str(bar.high),
        low=str(bar.low),
        close=str(bar.close),
        volume=str(bar.volume),
        buy_volume=str(bar.buy_volume),
        sell_volume=str(bar.sell_volume),
        unknown_volume=str(bar.unknown_volume),
        source=bar.source,
        is_revision=bar.is_revision,
        is_complete=bar.is_complete,
        dedupe_key=bar.dedupe_key,
        ts_event=ts_event,
        ts_init=ts_init,
    )


def record_to_canonical_bar(record: CanonicalOneMinuteBarRecord) -> OneMinuteBar:
    bar = OneMinuteBar(
        schema_version=record.schema_version,
        instrument_id=record.instrument_id.value,
        event_ts=utc_datetime_from_unix_ns(record.ts_event),
        ts_init=utc_datetime_from_unix_ns(record.ts_init),
        event_ts_ns=record.ts_event,
        ts_init_ns=record.ts_init,
        interval=record.interval,
        open_ts=utc_datetime_from_unix_ns(record.open_ts_ns),
        close_ts=utc_datetime_from_unix_ns(record.close_ts_ns),
        open=Decimal(record.open),
        high=Decimal(record.high),
        low=Decimal(record.low),
        close=Decimal(record.close),
        volume=Decimal(record.volume),
        buy_volume=Decimal(record.buy_volume),
        sell_volume=Decimal(record.sell_volume),
        unknown_volume=Decimal(record.unknown_volume),
        source=record.source,
        is_revision=record.is_revision,
        is_complete=record.is_complete,
    )
    if bar.dedupe_key != record.dedupe_key:
        raise ValueError("stored canonical bar dedupe key does not match reconstructed bar")
    return bar
