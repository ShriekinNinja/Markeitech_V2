from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextEventCommitResult:
    submitted_event_count: int
    committed_event_count: int
    duplicate_event_count: int
    checkpoint_advanced: bool
