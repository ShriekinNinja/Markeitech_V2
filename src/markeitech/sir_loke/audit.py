"""Durable PostgreSQL audit adapter for Sir Loke SL-01."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from time import time_ns
from uuid import UUID, uuid4

from markeitech.sir_loke.config import AuditConfig
from markeitech.system.persistence import OperationalStore, SirLokeAuditEventRecord

_DAY_NS = 86_400_000_000_000


class SirLokeAuditWriter:
    def __init__(
        self,
        store: OperationalStore,
        run_id: UUID,
        conversation_id: UUID,
        config: AuditConfig,
    ) -> None:
        self._store = store
        self._run_id = run_id
        self._conversation_id = conversation_id
        self._config = config

    @property
    def conversation_id(self) -> UUID:
        return self._conversation_id

    def reset_conversation(self, conversation_id: UUID) -> None:
        self._conversation_id = conversation_id

    async def write(
        self,
        *,
        turn_id: UUID,
        invocation_id: UUID | None,
        phase: str,
        content: Mapping[str, object] | None,
        metadata: Mapping[str, object],
        occurred_at_ns: int | None = None,
    ) -> None:
        occurred = time_ns() if occurred_at_ns is None else occurred_at_ns
        record = SirLokeAuditEventRecord(
            audit_event_id=uuid4(),
            run_id=self._run_id,
            conversation_id=self._conversation_id,
            turn_id=turn_id,
            invocation_id=invocation_id,
            phase=phase,
            content=content,
            metadata=metadata,
            occurred_at_ns=occurred,
            content_expires_at_ns=(occurred + self._config.content_retention_days * _DAY_NS),
            metadata_expires_at_ns=(occurred + self._config.metadata_retention_days * _DAY_NS),
        )
        await asyncio.to_thread(self._store.write_sir_loke_audit_event, record)

    async def prune(self) -> tuple[int, int]:
        return await asyncio.to_thread(self._store.prune_sir_loke_audit)
