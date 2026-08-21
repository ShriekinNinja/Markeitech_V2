from __future__ import annotations

from pathlib import Path

import pytest

from markeitech.system.config import load_system_config

VALID_CONFIG = """\
schema_version = 13

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

[acquisition]
native_consumer_probe_enabled = true
native_consumer_probe_unsubscribe_after_seconds = 15

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

[historical.probe]
enabled = false
actor_ids = ["HISTORICAL-PROBE-A", "HISTORICAL-PROBE-B"]
instrument_id = "ESU6.CME"
selector = "1-MINUTE-LAST-EXTERNAL"
window = "recent_completed"
minimum_observations = 5
maximum_observations = 10
priority = 10

[sessions]
evaluation_interval_ms = 1000

[[sessions.calendars]]
calendar_id = "cme_equity"
provider_calendar = "CME_Equity"
timezone = "America/New_York"
schedule_version = "test-1"
phases = []
overrides = []

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

[metrics.quote_quality]
enabled = true
required_watchlist_capability = "top_of_book"
parameter_version = 1
minimum_update_interval_ms = 250
maximum_output_age_ms = 15000
demand_retry_interval_ms = 1000
evidence_snapshot_retry_interval_ms = 1000
priority = 50

[metrics.session_measurements]
enabled = true
required_watchlist_capability = "watchlist_last"
parameter_version = 1
parameter_source = "operator-reviewed-config"
parameter_effective_from = "2026-08-20T00:00:00Z"
conflict_policy = "reject_conflict"
maximum_active_sessions = 3
demand_retry_interval_ms = 1000
evidence_snapshot_retry_interval_ms = 1000
priority = 40

[metrics.session_measurements.completed_bars]
live_selector = "5-SECOND-LAST-EXTERNAL"
historical_selector = "1-MINUTE-LAST-EXTERNAL"
historical_window = "recent_completed"
minimum_historical_observations = 2
maximum_historical_observations = 4
calculation_interval_seconds = 60
minimum_interval_seconds = 5
maximum_interval_seconds = 3600
interval_step_seconds = 5
interval_dynamic = true
aggregation_boundary_policy = "utc_fixed_intraday"
timestamp_policy = "interval_start"
revision_policy = "reject_revision"
maximum_retained_observations = 500
maximum_output_age_ms = 120000

[metrics.session_measurements.session_references]
enabled = true
historical_selector = "15-MINUTE-LAST-EXTERNAL"
active_window = "session_to_date"
previous_window = "previous_sessions"
overnight_window = "current_overnight"
minimum_historical_observations = 1
maximum_historical_observations = 100
vwap_price_basis = "typical"
vwap_price_basis_dynamic = true
minimum_coverage_ratio = 0.8
minimum_coverage_ratio_floor = 0.5
minimum_coverage_ratio_ceiling = 1.0
minimum_coverage_ratio_step = 0.05
minimum_coverage_ratio_dynamic = true
maximum_retained_sessions = 4
maximum_output_age_ms = 120000

[metrics.session_measurements.session_windows]
enabled = true
price_basis = "typical"
price_basis_dynamic = true
minimum_coverage_ratio = 0.8
minimum_coverage_ratio_floor = 0.5
minimum_coverage_ratio_ceiling = 1.0
minimum_coverage_ratio_step = 0.05
minimum_coverage_ratio_dynamic = true
maximum_retained_sessions = 4
maximum_output_age_ms = 120000

[[metrics.session_measurements.profiles]]
profile_id = "cme_equity_primary"
version = 1
calendar_id = "cme_equity"
primary_phase = "OPEN"
overnight_enabled = false
overnight_phase = "OPEN"
volume_supported = true

[[metrics.session_measurements.profiles.windows]]
window_id = "opening_range"
purpose = "opening_range"
anchor_phase = "OPEN"
anchor_boundary = "start"
offset_seconds = 0
duration_seconds = 300
minimum_duration_seconds = 60
maximum_duration_seconds = 1800
duration_step_seconds = 60
dynamic = true
historical_selector = "1-MINUTE-LAST-EXTERNAL"
minimum_historical_observations = 1
maximum_historical_observations = 5

[[metrics.session_measurements.profiles.windows]]
window_id = "power_hour"
purpose = "power_hour"
anchor_phase = "OPEN"
anchor_boundary = "end"
offset_seconds = -3600
duration_seconds = 3600
minimum_duration_seconds = 1800
maximum_duration_seconds = 7200
duration_step_seconds = 300
dynamic = true
historical_selector = "15-MINUTE-LAST-EXTERNAL"
minimum_historical_observations = 1
maximum_historical_observations = 4

[[metrics.session_measurements.profile_bindings]]
profile_id = "cme_equity_primary"
instrument_ids = ["ESU6.CME"]

[watchlist]
consumer_retry_interval_ms = 1000

[[watchlist.members]]
instrument_id = "ESU6.CME"
calendar_id = "cme_equity"
owner_ids = ["config:system"]
capabilities = ["top_of_book", "watchlist_last"]
"""


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
    assert config.persistence.dsn_env == "MARKEITECH_POSTGRES_DSN"
    assert config.persistence.queue_capacity == 64
    assert config.persistence.critical_queue_reserve == 8
    assert config.persistence.write_batch_size == 16
    assert config.persistence.result_poll_interval_ms == 250
    assert config.persistence.write_max_attempts == 3
    assert config.persistence.write_retry_backoff_ms == 100
    assert config.acquisition.native_consumer_probe_enabled is True
    assert config.acquisition.native_consumer_probe_unsubscribe_after_seconds == 15
    assert config.historical.maximum_in_flight_requests == 1
    assert config.historical.probe.instrument_id == "ESU6.CME"
    assert config.historical.probe.enabled is False
    assert config.historical.probe.actor_ids == (
        "HISTORICAL-PROBE-A",
        "HISTORICAL-PROBE-B",
    )
    assert config.sessions.calendars[0].calendar_id == "cme_equity"
    assert config.evidence_health.policies[0].fresh_for_ms == 2000
    assert config.evidence_health.consumer_retry_interval_ms == 1000
    assert config.metrics.quote_quality.enabled is True
    assert config.metrics.quote_quality.required_watchlist_capability == "top_of_book"
    assert config.metrics.quote_quality.minimum_update_interval_ms == 250
    assert config.metrics.session_measurements.enabled is True
    assert config.metrics.session_measurements.completed_bars.calculation_interval_seconds == 60
    assert config.metrics.session_measurements.completed_bars.interval_dynamic is True
    assert (
        config.metrics.session_measurements.completed_bars.aggregation_boundary_policy
        == "utc_fixed_intraday"
    )
    assert config.metrics.session_measurements.completed_bars.timestamp_policy == "interval_start"
    assert config.metrics.session_measurements.session_references.historical_selector == (
        "15-MINUTE-LAST-EXTERNAL"
    )
    assert config.metrics.session_measurements.session_references.previous_window == (
        "previous_sessions"
    )
    assert config.metrics.session_measurements.session_references.minimum_coverage_ratio == 0.8
    assert config.metrics.session_measurements.session_windows.minimum_coverage_ratio == 0.8
    assert config.metrics.session_measurements.parameter_source == "operator-reviewed-config"
    assert config.metrics.session_measurements.parameter_effective_from_ns > 0
    assert config.metrics.session_measurements.profiles[0].profile_id == "cme_equity_primary"
    assert config.metrics.session_measurements.profiles[0].overnight_enabled is False
    assert config.metrics.session_measurements.profile_bindings[0].instrument_ids == ("ESU6.CME",)
    assert config.metrics.session_measurements.profiles[0].windows[1].anchor_boundary == "end"
    assert (
        config.metrics.session_measurements.profiles[0].windows[0].historical_selector
        == "1-MINUTE-LAST-EXTERNAL"
    )
    assert (
        config.metrics.session_measurements.profiles[0]
        .windows[1]
        .maximum_historical_observations
        == 4
    )
    assert config.instrument_ids == ("ESU6.CME",)
    assert config.watchlist.consumer_retry_interval_ms == 1000
    assert config.watchlist.members[0].owner_ids == ("config:system",)
    assert config.watchlist.members[0].capabilities == ("top_of_book", "watchlist_last")


def test_rejects_unknown_configuration(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG.replace("environment =", "legacy_option = true\nenvironment ="))

    with pytest.raises(ValueError, match="runtime has unknown keys: legacy_option"):
        load_system_config(path)


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


def test_rejects_removed_bootstrap_feed_configuration(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            "native_consumer_probe_enabled = true",
            "native_consumer_probe_enabled = true\nbootstrap_feeds = []",
        ),
    )

    with pytest.raises(ValueError, match="acquisition has unknown keys: bootstrap_feeds"):
        load_system_config(path)


def test_accepts_feed_specific_watchlist_capabilities(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'capabilities = ["top_of_book", "watchlist_last"]',
            'capabilities = ["top_of_book"]',
        ).replace(
            "[metrics.session_measurements]\nenabled = true",
            "[metrics.session_measurements]\nenabled = false",
        ),
    )

    config = load_system_config(path)

    assert config.watchlist.members[0].capabilities == ("top_of_book",)


def test_rejects_enabled_session_measurements_without_profile_binding(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG
        + '\n[[watchlist.members]]\ninstrument_id = "NQU6.CME"\n'
        + 'calendar_id = "cme_equity"\n'
        + 'owner_ids = ["config:system"]\n'
        + 'capabilities = ["watchlist_last"]\n',
    )

    with pytest.raises(ValueError, match="lack analytical profile bindings"):
        load_system_config(path)


def test_rejects_session_measurements_above_active_calendar_bound(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace("maximum_active_sessions = 3", "maximum_active_sessions = 1")
        + """

[[sessions.calendars]]
calendar_id = "second_calendar"
provider_calendar = "NYSE"
timezone = "America/New_York"
schedule_version = "test-1"
phases = []
overrides = []

[[metrics.session_measurements.profiles]]
profile_id = "second_profile"
version = 1
calendar_id = "second_calendar"
primary_phase = "OPEN"
overnight_enabled = false
overnight_phase = "OPEN"
volume_supported = true
windows = []

[[metrics.session_measurements.profile_bindings]]
profile_id = "second_profile"
instrument_ids = ["SPY.ARCA"]

[[watchlist.members]]
instrument_id = "SPY.ARCA"
calendar_id = "second_calendar"
owner_ids = ["config:system"]
capabilities = ["watchlist_last"]
""",
    )

    with pytest.raises(ValueError, match="exceed maximum_active_sessions"):
        load_system_config(path)


def test_rejects_duplicate_session_measurement_profile_binding(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'instrument_ids = ["ESU6.CME"]',
            'instrument_ids = ["ESU6.CME"]\n\n'
            "[[metrics.session_measurements.profile_bindings]]\n"
            'profile_id = "cme_equity_primary"\n'
            'instrument_ids = ["ESU6.CME"]',
        ),
    )

    with pytest.raises(ValueError, match="exactly one profile binding"):
        load_system_config(path)


def test_rejects_profile_binding_calendar_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'calendar_id = "cme_equity"\nowner_ids',
            'calendar_id = "other_calendar"\nowner_ids',
        )
        + '\n[[sessions.calendars]]\ncalendar_id = "other_calendar"\n'
        + 'provider_calendar = "NYSE"\n'
        + 'timezone = "America/New_York"\n'
        + 'schedule_version = "test-1"\nphases = []\noverrides = []\n',
    )

    with pytest.raises(ValueError, match="profile binding calendar mismatch"):
        load_system_config(path)


def test_rejects_revised_bars_for_current_session_measurement_policy(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace("handle_revised_bars = false", "handle_revised_bars = true"),
    )

    with pytest.raises(ValueError, match="handle_revised_bars = false"):
        load_system_config(path)


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


def test_rejects_session_override_for_an_undefined_phase(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            "phases = []\noverrides = []",
            """
phases = []

[[sessions.calendars.overrides]]
trade_date = "2026-08-17"
phase = "GTH"
start = "20:15"
end = "09:25"
start_day_offset = -1
""",
        ),
    )

    with pytest.raises(ValueError, match="overrides reference undefined phases: GTH"):
        load_system_config(path)


def test_rejects_session_measurement_interval_outside_optimization_envelope(
    tmp_path: Path,
) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            "calculation_interval_seconds = 60",
            "calculation_interval_seconds = 2",
        ),
    )

    with pytest.raises(ValueError, match="outside its configured envelope"):
        load_system_config(path)


def test_rejects_unknown_session_measurement_profile_calendar(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'calendar_id = "cme_equity"\nprimary_phase = "OPEN"',
            'calendar_id = "unknown"\nprimary_phase = "OPEN"',
        ),
    )

    with pytest.raises(ValueError, match="profiles reference unknown calendars: unknown"):
        load_system_config(path)


def test_rejects_duplicate_analytical_window_ids(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'window_id = "power_hour"',
            'window_id = "opening_range"',
        ),
    )

    with pytest.raises(ValueError, match="window IDs must be unique"):
        load_system_config(path)
