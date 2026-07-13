from __future__ import annotations

import hashlib
import os
import struct
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from msgspec import msgpack
from nautilus_trader.model.data import QuoteTick, TradeTick
from nautilus_trader.serialization.serializer import MsgSpecSerializer

from markeitech.domain.market_data import OneMinuteBar
from markeitech.persistence.config import PersistenceConfig
from markeitech.persistence.contracts import PersistenceEventIdentity

_MAGIC = b"MKWAL1\n"
_LENGTH = struct.Struct(">I")
_CHECKSUM_SIZE = hashlib.sha256().digest_size
_TRADE_TICK = 1
_QUOTE_TICK = 2
_ONE_MINUTE_BAR = 3


class JournalError(RuntimeError):
    pass


class JournalCapacityError(JournalError):
    pass


class JournalCorruptionError(JournalError):
    pass


@dataclass(frozen=True)
class JournalEntry:
    event: object
    path: Path


class DurableIngressJournal:
    """Checksummed bucket WAL for native ticks and completed canonical bars."""

    def __init__(self, config: PersistenceConfig) -> None:
        self._config = config
        self._path = config.journal_path
        self._serializer = MsgSpecSerializer(msgpack)
        self._path.mkdir(parents=True, exist_ok=True)
        self._total_bytes = sum(path.stat().st_size for path in self._wal_paths())
        if self._total_bytes > config.journal_max_bytes:
            raise JournalCapacityError("ingress journal exceeds configured capacity")

    @property
    def total_bytes(self) -> int:
        return self._total_bytes

    def append(
        self,
        events: Sequence[tuple[object, PersistenceEventIdentity]],
    ) -> tuple[JournalEntry, ...]:
        encoded: list[tuple[object, Path, bytes]] = []
        projected_bytes = self._total_bytes
        new_paths: set[Path] = set()
        for event, identity in events:
            path = self.path_for(identity)
            record = self._encode_record(event)
            if len(record) > self._config.journal_max_record_bytes + _LENGTH.size + _CHECKSUM_SIZE:
                raise JournalCapacityError("journal record exceeds configured maximum")
            if not path.exists() and path not in new_paths:
                projected_bytes += len(_MAGIC)
                new_paths.add(path)
            projected_bytes += len(record)
            encoded.append((event, path, record))
        if projected_bytes > self._config.journal_max_bytes:
            raise JournalCapacityError("ingress journal capacity exhausted")

        grouped: dict[Path, list[tuple[object, bytes]]] = defaultdict(list)
        for event, path, record in encoded:
            grouped[path].append((event, record))
        for path, records in grouped.items():
            is_new = not path.exists()
            with path.open("ab") as stream:
                if is_new:
                    stream.write(_MAGIC)
                for _, record in records:
                    stream.write(record)
                stream.flush()
                if self._config.journal_fsync:
                    os.fsync(stream.fileno())
        if new_paths and self._config.journal_fsync:
            self._fsync_directory()
        self._total_bytes = projected_bytes
        return tuple(JournalEntry(event=event, path=path) for event, path, _ in encoded)

    def recover(self) -> tuple[JournalEntry, ...]:
        recovered: list[JournalEntry] = []
        for path in self._wal_paths():
            events = self._read(path)
            if not events:
                path.unlink()
                if self._config.journal_fsync:
                    self._fsync_directory()
                continue
            recovered.extend(JournalEntry(event=event, path=path) for event in events)
        self._total_bytes = sum(path.stat().st_size for path in self._wal_paths())
        return tuple(recovered)

    def acknowledge(self, path: Path) -> None:
        if not path.exists():
            return
        size = path.stat().st_size
        path.unlink()
        if self._config.journal_fsync:
            self._fsync_directory()
        self._total_bytes -= size

    def path_for(self, identity: PersistenceEventIdentity) -> Path:
        init_ns = identity.init_ts_ns
        if init_ns is None:
            raise ValueError("journal identity requires nanosecond initialization time")
        interval_ns = self._config.persistence_batch_interval_seconds * 1_000_000_000
        bucket = init_ns // interval_ns
        stream = f"{identity.source}|{identity.instrument_id}|{identity.event_kind.value}"
        stream_hash = hashlib.sha256(stream.encode()).hexdigest()
        return self._path / f"{bucket:020d}-{stream_hash}.wal"

    def _wal_paths(self) -> tuple[Path, ...]:
        return tuple(sorted(self._path.glob("*.wal"))) if self._path.exists() else ()

    def _fsync_directory(self) -> None:
        descriptor = os.open(self._path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _encode_record(self, event: object) -> bytes:
        if isinstance(event, TradeTick):
            body = bytes([_TRADE_TICK]) + self._serializer.serialize(event)
        elif isinstance(event, QuoteTick):
            body = bytes([_QUOTE_TICK]) + self._serializer.serialize(event)
        elif isinstance(event, OneMinuteBar):
            body = (
                bytes([_ONE_MINUTE_BAR])
                + event.model_dump_json(exclude_computed_fields=True).encode()
            )
        else:
            raise TypeError(f"unsupported journal event type: {type(event).__name__}")
        if len(body) > self._config.journal_max_record_bytes:
            raise JournalCapacityError("journal payload exceeds configured maximum")
        return _LENGTH.pack(len(body)) + hashlib.sha256(body).digest() + body

    def _read(self, path: Path) -> tuple[object, ...]:
        events: list[object] = []
        with path.open("r+b") as stream:
            magic = stream.read(len(_MAGIC))
            if magic != _MAGIC:
                if len(magic) < len(_MAGIC):
                    stream.truncate(0)
                    return ()
                raise JournalCorruptionError(f"invalid journal header: {path.name}")
            while True:
                record_start = stream.tell()
                raw_length = stream.read(_LENGTH.size)
                if not raw_length:
                    break
                if len(raw_length) < _LENGTH.size:
                    stream.truncate(record_start)
                    break
                (body_length,) = _LENGTH.unpack(raw_length)
                if body_length == 0 or body_length > self._config.journal_max_record_bytes:
                    raise JournalCorruptionError(f"invalid journal record length: {path.name}")
                checksum = stream.read(_CHECKSUM_SIZE)
                body = stream.read(body_length)
                if len(checksum) < _CHECKSUM_SIZE or len(body) < body_length:
                    stream.truncate(record_start)
                    break
                if hashlib.sha256(body).digest() != checksum:
                    raise JournalCorruptionError(f"journal checksum mismatch: {path.name}")
                events.append(self._decode_body(body, path))
        return tuple(events)

    def _decode_body(self, body: bytes, path: Path) -> object:
        event_type, payload = body[0], body[1:]
        if event_type == _TRADE_TICK:
            event = self._serializer.deserialize(payload)
            if not isinstance(event, TradeTick):
                raise JournalCorruptionError(f"invalid trade tick payload: {path.name}")
            return event
        if event_type == _QUOTE_TICK:
            event = self._serializer.deserialize(payload)
            if not isinstance(event, QuoteTick):
                raise JournalCorruptionError(f"invalid quote tick payload: {path.name}")
            return event
        if event_type == _ONE_MINUTE_BAR:
            try:
                return OneMinuteBar.model_validate_json(payload)
            except ValueError as exc:
                raise JournalCorruptionError(f"invalid canonical bar payload: {path.name}") from exc
        raise JournalCorruptionError(f"unknown journal event type: {path.name}")
