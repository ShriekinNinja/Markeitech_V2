from __future__ import annotations

from pathlib import Path

import pytest

from markeitech.system.config import load_system_config

VALID_CONFIG = """\
schema_version = 25

[runtime]
name = "MARKEITECH-V2-TEST-001"
trader_id = "MARKEITECH-001"
environment = "sandbox"

[ib]
host = "127.0.0.1"
port = 4002
client_id = 20
symbology_method = "simplified"
convert_exchange_to_mic_venue = false
market_data_type = "realtime"
use_regular_trading_hours = false
batch_quotes = true
ignore_quote_tick_size_updates = false
handle_revised_bars = false
connection_timeout_seconds = 30
request_timeout_seconds = 30

[logging]
directory = "../data/logs"
file_name = "markeitech-v2.log"

[discord]
enabled = true
request_timeout_seconds = 5
queue_capacity = 32
ping_critical_resource_alerts = true

[runtime_resources]
enabled = true
sample_interval_ms = 10000
log_every_samples = 1
include_cache_counts = true
disk_path = "/"

[runtime_resources.health]
enabled = true
threshold_version = "test-v1"
warning_consecutive_samples = 3
critical_consecutive_samples = 2
recovery_consecutive_samples = 3
notification_cooldown_ms = 60000
rss_growth_window_samples = 6
stale_warning_ms = 30000
stale_critical_ms = 120000

[runtime_resources.health.warning]
host_memory_available_percent = 15.0
host_cpu_percent = 90.0
host_swap_percent = 50.0
disk_free_bytes = 16106127360
disk_free_percent = 10.0
process_rss_bytes = 4294967296
process_rss_growth_bytes = 536870912
process_cpu_percent = 400.0
thread_count = 100
open_fd_ratio = 0.70

[runtime_resources.health.critical]
host_memory_available_percent = 8.0
host_cpu_percent = 98.0
host_swap_percent = 80.0
disk_free_bytes = 5368709120
disk_free_percent = 5.0
process_rss_bytes = 8589934592
process_rss_growth_bytes = 1073741824
process_cpu_percent = 800.0
thread_count = 250
open_fd_ratio = 0.90

[persistence]
dsn_env = "MARKEITECH_POSTGRES_DSN"
connect_timeout_seconds = 5
queue_capacity = 64
critical_queue_reserve = 8
write_batch_size = 16
result_poll_interval_ms = 250
shutdown_timeout_seconds = 10
write_max_attempts = 3
write_retry_backoff_ms = 100

[historical]
maximum_plan_requests = 8
maximum_observations_per_request = 100
maximum_total_observations = 500
maximum_outstanding_requests = 8
maximum_in_flight_requests = 1
timeout_seconds = 30
maximum_attempts = 3
retry_backoff_ms = 500
poll_interval_ms = 100

[sessions]
evaluation_interval_ms = 1000
projection_lookback_days = 120
projection_lookahead_days = 14
maximum_projection_days = 400
maximum_calendars_per_request = 8
calendar_catalog = "market-calendars.toml"
calendar_ids = ["cme_equity"]

[sessions.projection_retry]
response_timeout_ms = 5000
maximum_attempts = 3
retry_backoff_ms = 1000
maximum_elapsed_ms = 60000

[sessions.current_state_delivery]
policy_version = 1
response_timeout_ms = 5000
maximum_attempts = 3
retry_backoff_ms = 1000
maximum_elapsed_ms = 60000
maximum_buffered_transitions_per_calendar = 8
maximum_total_buffered_transitions = 32
boundary_delivery_grace_ms = 2000

[evidence_health]
evaluation_interval_ms = 1000
consumer_retry_interval_ms = 1000
provider_id = "IB"
profile_checkpoint_samples = 25

[[evidence_health.policies]]
feed_kind = "quotes"
selector = "default"
fresh_for_ms = 2000
stale_after_ms = 5000
unavailable_after_ms = 15000
adaptive = true
minimum_samples = 20
decay_factor = 0.95
fresh_stddev_multiplier = 2.0
stale_stddev_multiplier = 4.0
unavailable_stddev_multiplier = 8.0
min_fresh_ms = 2000
max_fresh_ms = 15000
min_stale_ms = 5000
max_stale_ms = 45000
min_unavailable_ms = 15000
max_unavailable_ms = 120000

[[evidence_health.policies]]
feed_kind = "bars"
selector = "5-SECOND-LAST-EXTERNAL"
fresh_for_ms = 7000
stale_after_ms = 15000
unavailable_after_ms = 30000
adaptive = false
minimum_samples = 20
decay_factor = 0.95
fresh_stddev_multiplier = 2.0
stale_stddev_multiplier = 4.0
unavailable_stddev_multiplier = 8.0
min_fresh_ms = 5000
max_fresh_ms = 10000
min_stale_ms = 10000
max_stale_ms = 20000
min_unavailable_ms = 20000
max_unavailable_ms = 60000

[watchlist]
consumer_retry_interval_ms = 1000

[[watchlist.members]]
instrument_id = "ESU6.CME"
calendar_id = "cme_equity"
owner_ids = ["config:system"]
capabilities = ["top_of_book", "watchlist_last"]
"""

CALENDAR_CATALOG = (Path(__file__).parents[2] / "config/market-calendars.toml").read_text()


@pytest.fixture(autouse=True)
def _write_calendar_catalog(tmp_path: Path) -> None:
    (tmp_path / "market-calendars.toml").write_text(CALENDAR_CATALOG)


def test_loads_standalone_system_config(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG)

    config = load_system_config(path)

    assert config.runtime.name == "MARKEITECH-V2-TEST-001"
    assert config.ib.port == 4002
    assert config.ib.symbology_method == "simplified"
    assert config.ib.convert_exchange_to_mic_venue is False
    assert config.ib.batch_quotes is True
    assert config.ib.ignore_quote_tick_size_updates is False
    assert config.ib.handle_revised_bars is False
    assert config.logging.directory == tmp_path.parent / "data/logs"
    assert config.logging.file_name == "markeitech-v2.log"
    assert config.discord.request_timeout_seconds == 5
    assert config.discord.enabled is True
    assert config.discord.queue_capacity == 32
    assert config.discord.ping_critical_resource_alerts is True
    assert config.runtime_resources.enabled is True
    assert config.runtime_resources.sample_interval_ms == 10000
    assert config.runtime_resources.log_every_samples == 1
    assert config.runtime_resources.include_cache_counts is True
    assert config.runtime_resources.disk_path == "/"
    assert config.runtime_resources.health.enabled is True
    assert config.runtime_resources.health.threshold_version == "test-v1"
    assert config.runtime_resources.health.warning.host_memory_available_percent == 15.0
    assert config.runtime_resources.health.critical.process_rss_bytes == 8_589_934_592
    assert config.persistence.dsn_env == "MARKEITECH_POSTGRES_DSN"
    assert config.persistence.queue_capacity == 64
    assert config.persistence.critical_queue_reserve == 8
    assert config.persistence.write_batch_size == 16
    assert config.persistence.result_poll_interval_ms == 250
    assert config.persistence.write_max_attempts == 3
    assert config.persistence.write_retry_backoff_ms == 100
    assert config.historical.maximum_in_flight_requests == 1
    assert config.sessions.current_state_delivery.policy_version == 1
    assert config.sessions.current_state_delivery.maximum_attempts == 3
    assert config.sessions.current_state_delivery.maximum_total_buffered_transitions == 32
    cme_equity = next(
        calendar for calendar in config.sessions.calendars if calendar.calendar_id == "cme_equity"
    )
    assert cme_equity.provider_calendar == "CME_Equity"
    assert cme_equity.exchange_timezone == "America/Chicago"
    assert cme_equity.phases[0].timezone == "provider"
    assert cme_equity.phases[0].name == "GLOBEX"
    assert tuple(phase.name for phase in cme_equity.phases) == (
        "GLOBEX",
        "ASIA",
        "LONDON",
        "NEW_YORK",
    )
    assert cme_equity.phases[1].timezone == "America/Chicago"
    assert cme_equity.phases[2].timezone == "Europe/London"
    assert cme_equity.phases[3].timezone == "America/New_York"
    assert cme_equity.schedule_columns == (
        "market_open",
        "break_start",
        "break_end",
        "market_close",
    )
    assert len(cme_equity.definition_digest) == 64
    assert config.evidence_health.policies[0].fresh_for_ms == 2000
    assert config.evidence_health.consumer_retry_interval_ms == 1000
    assert config.schema_version == 25
    assert config.instrument_ids == ("ESU6.CME",)
    assert config.watchlist.consumer_retry_interval_ms == 1000
    assert config.watchlist.members[0].owner_ids == ("config:system",)
    assert config.watchlist.members[0].capabilities == ("top_of_book", "watchlist_last")


def test_rejects_unknown_configuration(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG.replace("environment =", "legacy_option = true\nenvironment ="))

    with pytest.raises(ValueError, match="runtime has unknown keys: legacy_option"):
        load_system_config(path)


@pytest.mark.parametrize(
    "section",
    ["visual_acceptance", "live_evidence_review", "acquisition", "visual_debug_capture"],
)
def test_rejects_retired_root_sections(tmp_path: Path, section: str) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG + f"\n[{section}]\nenabled = false\n")

    with pytest.raises(ValueError, match=rf"root has unknown keys: {section}"):
        load_system_config(path)


@pytest.mark.parametrize("version", [22, 23, 24])
def test_rejects_older_system_schema(tmp_path: Path, version: int) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG.replace("schema_version = 25", f"schema_version = {version}", 1))

    with pytest.raises(ValueError, match=f"unsupported schema_version: {version}"):
        load_system_config(path)


@pytest.mark.parametrize(
    ("original", "replacement", "message"),
    [
        ("response_timeout_ms = 5000", "response_timeout_ms = 99", "response_timeout_ms"),
        (
            "response_timeout_ms = 5000\nmaximum_attempts = 3\nretry_backoff_ms",
            "response_timeout_ms = 5000\nmaximum_attempts = 11\nretry_backoff_ms",
            "maximum_attempts",
        ),
        ("retry_backoff_ms = 1000", "retry_backoff_ms = 60001", "retry_backoff_ms"),
        ("maximum_elapsed_ms = 60000", "maximum_elapsed_ms = 999", "maximum_elapsed_ms"),
    ],
)
def test_rejects_projection_retry_values_outside_safety_envelopes(
    tmp_path: Path,
    original: str,
    replacement: str,
    message: str,
) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG.replace(original, replacement, 1))

    with pytest.raises(ValueError, match=message):
        load_system_config(path)


@pytest.mark.parametrize(
    ("original", "replacement", "message"),
    [
        ("policy_version = 1", "policy_version = 2", "policy_version must be 1"),
        (
            "[sessions.current_state_delivery]\npolicy_version = 1\n"
            "response_timeout_ms = 5000\nmaximum_attempts = 3",
            "[sessions.current_state_delivery]\npolicy_version = 1\n"
            "response_timeout_ms = 5000\nmaximum_attempts = 11",
            "maximum_attempts",
        ),
        (
            "maximum_buffered_transitions_per_calendar = 8\n"
            "maximum_total_buffered_transitions = 32",
            "maximum_buffered_transitions_per_calendar = 33\n"
            "maximum_total_buffered_transitions = 32",
            "maximum_total_buffered_transitions",
        ),
    ],
)
def test_rejects_invalid_current_state_delivery_policy(
    tmp_path: Path,
    original: str,
    replacement: str,
    message: str,
) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG.replace(original, replacement, 1))

    with pytest.raises(ValueError, match=message):
        load_system_config(path)


def test_rejects_missing_or_unknown_current_state_delivery_configuration(
    tmp_path: Path,
) -> None:
    block = """\
[sessions.current_state_delivery]
policy_version = 1
response_timeout_ms = 5000
maximum_attempts = 3
retry_backoff_ms = 1000
maximum_elapsed_ms = 60000
maximum_buffered_transitions_per_calendar = 8
maximum_total_buffered_transitions = 32
boundary_delivery_grace_ms = 2000
"""
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG.replace(block, ""))
    with pytest.raises(ValueError, match="sessions missing keys: current_state_delivery"):
        load_system_config(path)

    path.write_text(
        VALID_CONFIG.replace(
            "boundary_delivery_grace_ms = 2000",
            "boundary_delivery_grace_ms = 2000\nmaximum_cached_responses = 99",
            1,
        ),
    )
    with pytest.raises(
        ValueError,
        match="current_state_delivery has unknown keys: maximum_cached_responses",
    ):
        load_system_config(path)


def test_rejects_missing_dedicated_calendar_catalog(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG.replace("market-calendars.toml", "missing.toml", 1))

    with pytest.raises(ValueError, match="session calendar catalog does not exist"):
        load_system_config(path)


def test_rejects_pre_cleanup_calendar_catalog_schema(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    (tmp_path / "market-calendars.toml").write_text(
        CALENDAR_CATALOG.replace("schema_version = 3", "schema_version = 2", 1),
    )
    path.write_text(VALID_CONFIG)

    with pytest.raises(ValueError, match="unsupported calendar_catalog.schema_version: 2"):
        load_system_config(path)


def test_rejects_calendar_catalog_for_a_different_engine_version(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    (tmp_path / "market-calendars.toml").write_text(
        CALENDAR_CATALOG.replace(
            'calendar_engine_version = "5.4.0"',
            'calendar_engine_version = "5.5.0"',
            1,
        ),
    )
    path.write_text(VALID_CONFIG)

    with pytest.raises(
        ValueError,
        match="requires pandas-market-calendars 5.5.0, installed 5.4.0",
    ):
        load_system_config(path)


def test_rejects_inline_session_calendars(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'calendar_catalog = "market-calendars.toml"',
            'calendar_catalog = "market-calendars.toml"\ncalendars = []',
        ),
    )

    with pytest.raises(ValueError, match="sessions has unknown keys: calendars"):
        load_system_config(path)


def test_rejects_default_projection_window_above_runtime_bound(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            "maximum_projection_days = 400",
            "maximum_projection_days = 134",
        ),
    )

    with pytest.raises(ValueError, match="lookback and lookahead exceed"):
        load_system_config(path)


def test_rejects_selected_calendars_above_request_bound(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            "maximum_calendars_per_request = 8\ncalendar_catalog",
            "maximum_calendars_per_request = 1\ncalendar_catalog",
        ).replace(
            'calendar_ids = ["cme_equity"]',
            'calendar_ids = ["cme_equity", "cme_energy"]',
        ),
    )

    with pytest.raises(ValueError, match="calendar_ids exceed"):
        load_system_config(path)


def test_rejects_invalid_product_phase_timezone(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    catalog_path = tmp_path / "market-calendars.toml"
    catalog_path.write_text(
        CALENDAR_CATALOG.replace(
            '[[calendars.phases]]\nname = "GLOBEX"\ntimezone = "provider"',
            '[[calendars.phases]]\nname = "GLOBEX"\ntimezone = "Not/AZone"',
            1,
        ),
    )
    path.write_text(VALID_CONFIG)

    with pytest.raises(
        ValueError,
        match=r"phases\[GLOBEX\]\.timezone is not an IANA timezone",
    ):
        load_system_config(path)


def test_rejects_calendar_correction_without_product_scope(
    tmp_path: Path,
) -> None:
    path = tmp_path / "system.toml"
    (tmp_path / "market-calendars.toml").write_text(
        CALENDAR_CATALOG.replace(
            'product_roots = ["ES", "NQ", "YM"]',
            "product_roots = []",
            1,
        ),
    )
    path.write_text(VALID_CONFIG)

    with pytest.raises(ValueError, match="product_roots must be a non-empty array"):
        load_system_config(path)


def test_rejects_unavailable_provider_schedule_column(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    catalog_path = tmp_path / "market-calendars.toml"
    catalog_path.write_text(
        CALENDAR_CATALOG.replace(
            'schedule_columns = ["market_open", "market_close"]',
            'schedule_columns = ["market_open", "break_start", "break_end", "market_close"]',
            1,
        ),
    )
    path.write_text(VALID_CONFIG)

    with pytest.raises(ValueError, match="schedule_columns are unavailable"):
        load_system_config(path)


def test_calendar_definition_digest_is_stable_and_content_derived(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG)
    first = load_system_config(path)
    second = load_system_config(path)
    original = next(item for item in first.sessions.calendars if item.calendar_id == "cme_equity")
    repeated = next(item for item in second.sessions.calendars if item.calendar_id == "cme_equity")

    assert original.definition_digest == repeated.definition_digest
    assert first.sessions.catalog_digest == second.sessions.catalog_digest

    catalog_path = tmp_path / "market-calendars.toml"
    catalog_path.write_text(
        CALENDAR_CATALOG.replace(
            'calendar_id = "cme_equity"\n'
            'calendar_engine = "pandas_market_calendars"\n'
            'provider_calendar = "CME_Equity"\n'
            'schedule_columns = ["market_open", "break_start", "break_end", "market_close"]\n'
            "definition_version = 4",
            'calendar_id = "cme_equity"\n'
            'calendar_engine = "pandas_market_calendars"\n'
            'provider_calendar = "CME_Equity"\n'
            'schedule_columns = ["market_open", "break_start", "break_end", "market_close"]\n'
            "definition_version = 5",
            1,
        ),
    )
    changed = load_system_config(path)
    revised = next(item for item in changed.sessions.calendars if item.calendar_id == "cme_equity")

    assert revised.definition_version == 5
    assert revised.definition_digest != original.definition_digest
    assert changed.sessions.catalog_digest != first.sessions.catalog_digest


def test_equal_definition_versions_with_unequal_content_have_unequal_digests(
    tmp_path: Path,
) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG)
    original_config = load_system_config(path)
    original = next(
        item for item in original_config.sessions.calendars if item.calendar_id == "cme_equity"
    )
    (tmp_path / "market-calendars.toml").write_text(
        CALENDAR_CATALOG.replace(
            'calendar_id = "cme_equity"\n'
            'calendar_engine = "pandas_market_calendars"\n'
            'provider_calendar = "CME_Equity"\n'
            'schedule_columns = ["market_open", "break_start", "break_end", "market_close"]',
            'calendar_id = "cme_equity"\n'
            'calendar_engine = "pandas_market_calendars"\n'
            'provider_calendar = "CME_Equity"\n'
            'schedule_columns = ["market_open", "market_close"]',
            1,
        ),
    )
    changed_config = load_system_config(path)
    changed = next(
        item for item in changed_config.sessions.calendars if item.calendar_id == "cme_equity"
    )

    assert original.definition_version == changed.definition_version == 4
    assert original.definition_digest != changed.definition_digest


def test_rejects_legacy_instrument_mappings_in_calendar_catalog(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    (tmp_path / "market-calendars.toml").write_text(
        CALENDAR_CATALOG.replace(
            'calendar_engine_version = "5.4.0"',
            'calendar_engine_version = "5.4.0"\ninstrument_mappings = []',
            1,
        ),
    )
    path.write_text(VALID_CONFIG)

    with pytest.raises(
        ValueError,
        match="calendar_catalog has unknown keys: instrument_mappings",
    ):
        load_system_config(path)


def test_futures_contract_roll_does_not_require_calendar_catalog_edit(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG.replace("ESU6.CME", "ESZ6.CME"))

    config = load_system_config(path)

    assert config.watchlist.members[0].instrument_id == "ESZ6.CME"
    assert config.watchlist.members[0].calendar_id == "cme_equity"


def test_rejects_duplicate_watchlist_instruments(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG
        + '\n[[watchlist.members]]\ninstrument_id = "ESU6.CME"\n'
        + 'calendar_id = "cme_equity"\n'
        + 'owner_ids = ["config:system"]\n'
        + 'capabilities = ["top_of_book", "watchlist_last"]\n',
    )

    with pytest.raises(ValueError, match="duplicate watchlist instrument id: ESU6.CME"):
        load_system_config(path)


def test_rejects_unknown_ib_symbology_method(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'symbology_method = "simplified"',
            'symbology_method = "guess"',
        ),
    )

    with pytest.raises(ValueError, match="unsupported ib.symbology_method: 'guess'"):
        load_system_config(path)


def test_accepts_feed_specific_watchlist_capabilities(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'capabilities = ["top_of_book", "watchlist_last"]',
            'capabilities = ["top_of_book"]',
        )
    )

    config = load_system_config(path)

    assert config.watchlist.members[0].capabilities == ("top_of_book",)


def test_rejects_duplicate_watchlist_owners(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'owner_ids = ["config:system"]',
            'owner_ids = ["config:system", "config:system"]',
        ),
    )

    with pytest.raises(ValueError, match="owner_ids must contain unique values"):
        load_system_config(path)


def test_rejects_missing_evidence_policy_for_a_watchlist_feed(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    bars_policy = """
[[evidence_health.policies]]
feed_kind = "bars"
selector = "5-SECOND-LAST-EXTERNAL"
fresh_for_ms = 7000
stale_after_ms = 15000
unavailable_after_ms = 30000
adaptive = false
minimum_samples = 20
decay_factor = 0.95
fresh_stddev_multiplier = 2.0
stale_stddev_multiplier = 4.0
unavailable_stddev_multiplier = 8.0
min_fresh_ms = 5000
max_fresh_ms = 10000
min_stale_ms = 10000
max_stale_ms = 20000
min_unavailable_ms = 20000
max_unavailable_ms = 60000
"""
    path.write_text(VALID_CONFIG.replace(bars_policy, ""))

    with pytest.raises(
        ValueError,
        match="watchlist feeds lack evidence-health policies: bars/5-SECOND-LAST-EXTERNAL",
    ):
        load_system_config(path)


def test_rejects_obsolete_calendar_overrides(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    (tmp_path / "market-calendars.toml").write_text(
        CALENDAR_CATALOG.replace(
            'calendar_id = "us_equities"\ncalendar_engine = "pandas_market_calendars"',
            'calendar_id = "us_equities"\noverrides = []\n'
            'calendar_engine = "pandas_market_calendars"',
            1,
        ),
    )
    path.write_text(VALID_CONFIG)

    with pytest.raises(ValueError, match="unknown keys: overrides"):
        load_system_config(path)


def test_rejects_retired_historical_diagnostic_section(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG + "\n[historical.probe]\nenabled = false\n")

    with pytest.raises(ValueError, match="historical has unknown keys: probe"):
        load_system_config(path)


@pytest.mark.parametrize("section", ["quote_quality", "session_measurements", "entity_analysis"])
def test_rejects_removed_metrics_sections(tmp_path: Path, section: str) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG + f"\n[metrics.{section}]\nenabled = false\n")
    with pytest.raises(ValueError, match="root has unknown keys: metrics"):
        load_system_config(path)
