from __future__ import annotations

from pathlib import Path

import pytest

from markeitech.system.config import load_system_config

VALID_CONFIG = """\
schema_version = 22

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

[metrics.session_measurements.rolling_measurements]
enabled = true
minimum_coverage_ratio = 0.9
minimum_coverage_ratio_floor = 0.7
minimum_coverage_ratio_ceiling = 1.0
minimum_coverage_ratio_step = 0.05
minimum_coverage_ratio_dynamic = true
maximum_retained_observations = 500
maximum_output_age_ms = 120000

[metrics.session_measurements.rolling_measurements.baseline]
eligible_reference_health = ["READY"]
eligible_reference_fidelities = ["REPORTED", "DERIVED"]
recent_reference_count = 8
recent_reference_count_minimum = 8
recent_reference_count_maximum = 64
recent_reference_count_step = 1
recent_reference_count_dynamic = true
minimum_recent_references = 8
phase_reference_count = 5
phase_reference_count_minimum = 5
phase_reference_count_maximum = 30
phase_reference_count_step = 1
phase_reference_count_dynamic = true
minimum_phase_references = 5

[[metrics.session_measurements.rolling_measurements.families]]
family_id = "fast"
source_selector = "1-MINUTE-LAST-EXTERNAL"
input_selector = "1-MINUTE-LAST-EXTERNAL"
input_interval_seconds = 60
aggregation_policy = "identity"
selected_context_candidate_id = "context_1m"

[[metrics.session_measurements.rolling_measurements.families.candidates]]
candidate_id = "context_1m"
purpose = "context"
duration_seconds = 60
minimum_duration_seconds = 60
maximum_duration_seconds = 600
duration_step_seconds = 60
dynamic = true
active = true

[[metrics.session_measurements.profiles]]
profile_id = "cme_equity_primary"
version = 1
calendar_id = "cme_equity"
primary_phase = "GLOBEX"
overnight_enabled = false
overnight_phase = "GLOBEX"
volume_supported = true

[[metrics.session_measurements.profiles.windows]]
window_id = "opening_range_fast"
purpose = "opening_range"
anchor_phase = "GLOBEX"
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
anchor_phase = "GLOBEX"
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

[metrics.entity_analysis]
enabled = false
required_watchlist_capability = "watchlist_last"
catalog_version = 2
parameter_source = "operator-reviewed-config"
parameter_effective_from = "2026-08-23T00:00:00Z"
maximum_entities_global = 20000
maximum_entities_per_instrument = 1000
maximum_entities_per_instrument_type = 250
completed_session_retention = 2
completed_session_maximum_age_days = 14
maximum_input_age_ms = 120000
maximum_metric_values = 20000
market_state_reconciliation_interval_ms = 1000
minimum_snapshot_interval_ms = 1000
maximum_publications_per_cycle = 500
definitions = []

[watchlist]
consumer_retry_interval_ms = 1000

[[watchlist.members]]
instrument_id = "ESU6.CME"
calendar_id = "cme_equity"
owner_ids = ["config:system"]
capabilities = ["top_of_book", "watchlist_last"]
"""

ENTITY_DEFINITIONS = (Path(__file__).with_name("entity-analysis-definitions.toml")).read_text()
CALENDAR_CATALOG = (
    Path(__file__).parents[2] / "config/market-calendars.toml"
).read_text()


@pytest.fixture(autouse=True)
def _write_calendar_catalog(tmp_path: Path) -> None:
    (tmp_path / "market-calendars.toml").write_text(CALENDAR_CATALOG)


def _entity_enabled_config() -> str:
    return VALID_CONFIG.replace(
        "[metrics.entity_analysis]\nenabled = false",
        "[metrics.entity_analysis]\nenabled = true",
    ).replace("definitions = []", ENTITY_DEFINITIONS)


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
    assert config.visual_debug_capture.enabled is False
    assert config.visual_debug_capture.instrument_id == "ESU6.CME"
    assert config.visual_debug_capture.bar_specification == "1-MINUTE-LAST-EXTERNAL"
    assert config.visual_debug_capture.target_historical_bars == 5
    assert config.visual_debug_capture.target_live_bars == 5
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
    assert config.acquisition.native_consumer_probe_enabled is True
    assert config.acquisition.native_consumer_probe_unsubscribe_after_seconds == 15
    assert config.historical.maximum_in_flight_requests == 1
    assert config.historical.probe.instrument_id == "ESU6.CME"
    assert config.historical.probe.enabled is False
    assert config.historical.probe.actor_ids == (
        "HISTORICAL-PROBE-A",
        "HISTORICAL-PROBE-B",
    )
    assert config.sessions.current_state_delivery.policy_version == 1
    assert config.sessions.current_state_delivery.maximum_attempts == 3
    assert config.sessions.current_state_delivery.maximum_total_buffered_transitions == 32
    cme_equity = next(
        calendar
        for calendar in config.sessions.calendars
        if calendar.calendar_id == "cme_equity"
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
    assert config.metrics.session_measurements.rolling_measurements.enabled is True
    assert (
        config.metrics.session_measurements.rolling_measurements.baseline.recent_reference_count
        == 8
    )
    assert (
        config.metrics.session_measurements.rolling_measurements.baseline.eligible_reference_health
        == ("READY",)
    )
    assert (
        config.metrics.session_measurements.rolling_measurements.families[
            0
        ].selected_context_candidate_id
        == "context_1m"
    )
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
        config.metrics.session_measurements.profiles[0].windows[1].maximum_historical_observations
        == 4
    )
    assert config.schema_version == 22
    assert config.metrics.entity_analysis.enabled is False
    assert config.metrics.entity_analysis.catalog_version == 2
    assert config.metrics.entity_analysis.completed_session_retention == 2
    assert config.metrics.entity_analysis.completed_session_maximum_age_days == 14
    assert config.metrics.entity_analysis.maximum_metric_values == 20000
    assert config.metrics.entity_analysis.market_state_reconciliation_interval_ms == 1000
    assert config.metrics.entity_analysis.definitions == ()
    assert config.instrument_ids == ("ESU6.CME",)
    assert config.watchlist.consumer_retry_interval_ms == 1000
    assert config.watchlist.members[0].owner_ids == ("config:system",)
    assert config.watchlist.members[0].capabilities == ("top_of_book", "watchlist_last")


def test_tracked_example_disables_faulty_session_metrics_surface() -> None:
    root = Path(__file__).parents[2]

    config = load_system_config(root / "config/system.example.toml")

    assert config.metrics.session_measurements.enabled is False
    assert config.metrics.entity_analysis.enabled is False
    assert config.visual_debug_capture.enabled is False


def test_rejects_completed_bar_historical_selector_interval_mismatch(
    tmp_path: Path,
) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'historical_selector = "1-MINUTE-LAST-EXTERNAL"',
            'historical_selector = "5-MINUTE-LAST-EXTERNAL"',
            1,
        ),
    )

    with pytest.raises(ValueError, match="historical selector interval"):
        load_system_config(path)


def test_rejects_completed_bar_live_selector_that_does_not_divide_target(
    tmp_path: Path,
) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'live_selector = "5-SECOND-LAST-EXTERNAL"',
            'live_selector = "2-MINUTE-LAST-EXTERNAL"',
            1,
        ),
    )

    with pytest.raises(ValueError, match="live selector interval"):
        load_system_config(path)


def test_loads_complete_entity_analysis_configuration_envelope(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(_entity_enabled_config())

    config = load_system_config(path).metrics.entity_analysis

    assert config.enabled is True
    assert {item.group for item in config.definitions} == {
        "objective_session_reference_level",
        "volatility_compression_expansion",
        "direction_trend_rotation_reference",
        "swing_fvg_zone",
        "inferred_bar_volume_distribution",
    }
    ema = next(
        item for item in config.definitions if item.definition_id == "dynamic-ema-reference-v1"
    )
    assert ema.applications[0].horizon == "fast"
    assert ema.metric_inputs[0].parameter_version == 1
    assert ema.parameters[0].dynamic is True
    assert ema.parameters[0].minimum == 5
    assert ema.parameters[0].maximum == 34
    assert ema.parameter_sets[0].values == (("period", 10),)
    volatility = next(
        item for item in config.definitions if item.definition_id == "volatility-state-v1"
    )
    assert volatility.market_state is not None
    assert volatility.market_state.parameter_set_id == "volatility-percentile-fixture"
    assert volatility.market_state.normalization == "recent_range_percentile"
    assert volatility.market_state.policies[0].measure_role == "normalized_volatility"
    assert [band.category for band in volatility.market_state.policies[0].bands] == [
        "LOW",
        "TYPICAL",
        "HIGH",
    ]


def test_rejects_market_state_binding_in_legacy_entity_catalog(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(_entity_enabled_config().replace("catalog_version = 2", "catalog_version = 1"))

    with pytest.raises(ValueError, match="market-state bindings require.*version 2"):
        load_system_config(path)


def test_rejects_market_state_binding_without_explicit_runtime_limits(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        _entity_enabled_config().replace(
            "maximum_input_age_ms = 120000\nmaximum_metric_values = 20000\n"
            "market_state_reconciliation_interval_ms = 1000\n",
            "maximum_input_age_ms = 120000\nmarket_state_reconciliation_interval_ms = 1000\n",
        ),
    )

    with pytest.raises(ValueError, match="require explicit runtime limits.*maximum_metric_values"):
        load_system_config(path)


def test_rejects_market_state_policy_with_unknown_boundary_parameter(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        _entity_enabled_config().replace(
            'upper_bound_parameter_id = "volatility_low_upper"',
            'upper_bound_parameter_id = "missing_boundary"',
            1,
        ),
    )

    with pytest.raises(ValueError, match="unknown configured parameter: missing_boundary"):
        load_system_config(path)


def test_entity_application_accepts_direct_high_timeframe_selector(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        _entity_enabled_config().replace(
            'source_selector = "5-MINUTE-LAST-EXTERNAL"',
            'source_selector = "1-DAY-LAST-EXTERNAL"',
        ),
    )

    config = load_system_config(path)

    selectors = {
        application.source_selector
        for definition in config.metrics.entity_analysis.definitions
        for application in definition.applications
    }
    assert "1-DAY-LAST-EXTERNAL" in selectors


def test_rejects_entity_catalog_missing_an_enabled_group(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        _entity_enabled_config().replace(
            'group = "inferred_bar_volume_distribution"',
            'group = "swing_fvg_zone"',
        ),
    )

    with pytest.raises(ValueError, match="lacks definition groups.*inferred_bar_volume"):
        load_system_config(path)


def test_rejects_entity_parameter_set_outside_optimization_envelope(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        _entity_enabled_config().replace(
            "values = { period = 10 }",
            "values = { period = 35 }",
        ),
    )

    with pytest.raises(ValueError, match="period.*outside its configured envelope"):
        load_system_config(path)


def test_rejects_entity_parameter_value_off_optimization_step(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        _entity_enabled_config().replace(
            "minimum = 5, maximum = 34, step = 1",
            "minimum = 5, maximum = 34, step = 2",
        ),
    )

    with pytest.raises(ValueError, match="does not align with its configured step"):
        load_system_config(path)


def test_rejects_duplicate_entity_parameter_versions(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        _entity_enabled_config()
        .replace(
            'parameter_sets = [{ parameter_set_id = "ema-dynamic-10", parameter_version = 1,',
            'parameter_sets = [{ parameter_set_id = "ema-dynamic-10", parameter_version = 1,',
        )
        .replace(
            "values = { period = 10 } }]",
            'values = { period = 10 } }, { parameter_set_id = "ema-dynamic-11", '
            'parameter_version = 1, effective_from = "2026-08-23T00:00:00Z", '
            'source = "operator-reviewed-config", values = { period = 11 } }]',
            1,
        ),
    )

    with pytest.raises(ValueError, match="parameter versions must be unique"):
        load_system_config(path)


def test_rejects_volume_entity_for_profile_without_volume_support(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        _entity_enabled_config().replace("volume_supported = true", "volume_supported = false"),
    )

    with pytest.raises(ValueError, match="volume-dependent.*unsupported profiles"):
        load_system_config(path)


def test_rejects_unknown_configuration(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG.replace("environment =", "legacy_option = true\nenvironment ="))

    with pytest.raises(ValueError, match="runtime has unknown keys: legacy_option"):
        load_system_config(path)


@pytest.mark.parametrize("section", ["visual_acceptance", "live_evidence_review"])
def test_rejects_retired_visual_review_sections(tmp_path: Path, section: str) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG + f"\n[{section}]\nenabled = false\n")

    with pytest.raises(ValueError, match=rf"root has unknown keys: {section}"):
        load_system_config(path)


def test_rejects_pre_current_state_delivery_schema(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(VALID_CONFIG.replace("schema_version = 22", "schema_version = 21", 1))

    with pytest.raises(ValueError, match="unsupported schema_version: 21"):
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
            'maximum_calendars_per_request = 8\ncalendar_catalog',
            'maximum_calendars_per_request = 1\ncalendar_catalog',
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
    original = next(
        item for item in first.sessions.calendars if item.calendar_id == "cme_equity"
    )
    repeated = next(
        item for item in second.sessions.calendars if item.calendar_id == "cme_equity"
    )

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
    revised = next(
        item for item in changed.sessions.calendars if item.calendar_id == "cme_equity"
    )

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
        item
        for item in original_config.sessions.calendars
        if item.calendar_id == "cme_equity"
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
        item
        for item in changed_config.sessions.calendars
        if item.calendar_id == "cme_equity"
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
    (tmp_path / "market-calendars.toml").write_text(
        CALENDAR_CATALOG
        + """

[[calendars]]
calendar_id = "second_calendar"
calendar_engine = "pandas_market_calendars"
provider_calendar = "NYSE"
schedule_columns = ["market_open", "market_close"]
definition_version = 2
effective_from = "2026-08-30T00:00:00Z"
correction_ids = []

[[calendars.phases]]
name = "EXCHANGE_SESSION"
timezone = "provider"
start_kind = "schedule_boundary"
start_value = "market_open"
start_day_offset = 0
end_kind = "schedule_boundary"
end_value = "market_close"
end_day_offset = 0
exchange_constraint = "clip"
""",
    )
    path.write_text(
        VALID_CONFIG.replace("maximum_active_sessions = 3", "maximum_active_sessions = 1")
        .replace(
            'calendar_ids = ["cme_equity"]',
            'calendar_ids = ["cme_equity", "second_calendar"]',
        )
        + """

[[metrics.session_measurements.profiles]]
profile_id = "second_profile"
version = 1
calendar_id = "second_calendar"
primary_phase = "EXCHANGE_SESSION"
overnight_enabled = false
overnight_phase = "EXCHANGE_SESSION"
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
    (tmp_path / "market-calendars.toml").write_text(
        (
            CALENDAR_CATALOG
            + """

[[calendars]]
calendar_id = "other_calendar"
calendar_engine = "pandas_market_calendars"
provider_calendar = "NYSE"
schedule_columns = ["market_open", "market_close"]
definition_version = 2
effective_from = "2026-08-30T00:00:00Z"
correction_ids = []

[[calendars.phases]]
name = "EXCHANGE_SESSION"
timezone = "provider"
start_kind = "schedule_boundary"
start_value = "market_open"
start_day_offset = 0
end_kind = "schedule_boundary"
end_value = "market_close"
end_day_offset = 0
exchange_constraint = "clip"
"""
        ),
    )
    path.write_text(
        VALID_CONFIG.replace(
            'calendar_id = "cme_equity"\nowner_ids',
            'calendar_id = "other_calendar"\nowner_ids',
        ).replace(
            'calendar_ids = ["cme_equity"]',
            'calendar_ids = ["cme_equity", "other_calendar"]',
        ),
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


def test_rejects_rolling_retention_that_cannot_satisfy_recent_baseline(
    tmp_path: Path,
) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            "[metrics.session_measurements.rolling_measurements]\n"
            "enabled = true\n"
            "minimum_coverage_ratio = 0.9\n"
            "minimum_coverage_ratio_floor = 0.7\n"
            "minimum_coverage_ratio_ceiling = 1.0\n"
            "minimum_coverage_ratio_step = 0.05\n"
            "minimum_coverage_ratio_dynamic = true\n"
            "maximum_retained_observations = 500",
            "[metrics.session_measurements.rolling_measurements]\n"
            "enabled = true\n"
            "minimum_coverage_ratio = 0.9\n"
            "minimum_coverage_ratio_floor = 0.7\n"
            "minimum_coverage_ratio_ceiling = 1.0\n"
            "minimum_coverage_ratio_step = 0.05\n"
            "minimum_coverage_ratio_dynamic = true\n"
            "maximum_retained_observations = 8",
        ),
    )

    with pytest.raises(ValueError, match="cannot satisfy.*minimum recent"):
        load_system_config(path)


def test_rejects_unknown_session_measurement_profile_calendar(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'calendar_id = "cme_equity"\nprimary_phase = "GLOBEX"',
            'calendar_id = "unknown"\nprimary_phase = "GLOBEX"',
        ),
    )

    with pytest.raises(ValueError, match="profiles reference unknown calendars: unknown"):
        load_system_config(path)


def test_rejects_duplicate_analytical_window_ids(tmp_path: Path) -> None:
    path = tmp_path / "system.toml"
    path.write_text(
        VALID_CONFIG.replace(
            'window_id = "power_hour"',
            'window_id = "opening_range_fast"',
        ),
    )

    with pytest.raises(ValueError, match="window IDs must be unique"):
        load_system_config(path)
