# Persistence Maintenance

## Retention

Retention runs only at the quiescent startup boundary and is disabled by default. Enable it explicitly in the local market-data configuration:

```toml
[persistence]
retention_maintenance_enabled = true
tick_retention_sessions = 5
bar_retention_sessions = 250
```

The current incomplete session is retained in addition to the configured number of completed product sessions. WAL files, incomplete persistence batches, mixed-age Parquet files, and instruments without calendar policy all prevent unsafe deletion. Every enabled attempt writes a durable audit row.

Keep expired futures contracts as disabled instrument entries until their retention window has elapsed. This preserves their product-calendar policy without subscribing to them.

## SQLite Compaction

Retention can free SQLite pages without shrinking the database file. Compaction is intentionally offline and never runs from the LiveNode.

1. Stop the LiveNode completely.
2. Run the PyCharm configuration `Persistence - Compact SQLite (Offline)` or:

```bash
uv run markeitech-sqlite-compact config/market-data.local.toml \
  --confirm I_UNDERSTAND_THIS_REWRITES_SQLITE
```

The command refuses pending ingress WAL, incomplete batches, and conflicting SQLite activity. It skips the rewrite unless reclaimable pages meet `sqlite_compaction_min_reclaimable_bytes`, which defaults to 16 MiB. JSON output and a durable audit row record the before/after result.
