from __future__ import annotations

from pathlib import Path

import pytest
from markeitech.persistence import SQLiteCompactionStatus
from markeitech.persistence.compact import (
    SQLITE_COMPACTION_CONFIRMATION,
    run_sqlite_compaction,
)


def temporary_config(tmp_path: Path) -> Path:
    content = Path("config/market-data.example.toml").read_text()
    content = (
        content.replace(
            'catalog_path = "data/catalog"',
            f'catalog_path = "{tmp_path / "catalog"}"',
        )
        .replace(
            'metadata_path = "data/runtime/markeitech.sqlite3"',
            f'metadata_path = "{tmp_path / "metadata.sqlite3"}"',
        )
        .replace(
            'journal_path = "data/runtime/ingress-journal"',
            f'journal_path = "{tmp_path / "journal"}"',
        )
    )
    path = tmp_path / "market-data.toml"
    path.write_text(content)
    return path


def test_compaction_command_requires_explicit_confirmation(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="explicit confirmation"):
        run_sqlite_compaction(
            temporary_config(tmp_path),
            confirmation=None,
        )


def test_compaction_command_uses_configured_database_and_threshold(tmp_path: Path) -> None:
    report = run_sqlite_compaction(
        temporary_config(tmp_path),
        confirmation=SQLITE_COMPACTION_CONFIRMATION,
        minimum_reclaimable_bytes=2**63 - 1,
    )

    assert report.status == SQLiteCompactionStatus.SKIPPED_THRESHOLD
    assert report.database_path == tmp_path / "metadata.sqlite3"
    assert report.reclaimed_bytes == 0
