from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from markeitech.system.composition import (
    StartupPrerequisites,
    build_actor_plan,
    validate_runtime_environment,
)
from markeitech.system.config import load_system_config
from markeitech.system.discord import (
    OPERATIONAL_EVENTS_WEBHOOK_ENV,
    SYSTEM_HEALTH_WEBHOOK_ENV,
)


def _config():  # noqa: ANN202
    root = Path(__file__).parents[2]
    return load_system_config(root / "config/system.example.toml")


def _prerequisites(ready: bool = True) -> StartupPrerequisites:
    return StartupPrerequisites(
        run_id=uuid4(),
        operational_persistence_ready=ready,
    )


def test_actor_plan_has_mandatory_core_and_enabled_discord() -> None:
    plan = build_actor_plan(_config(), _prerequisites())

    assert [registration.key for registration in plan] == [
        "system_control",
        "session_state",
        "evidence_health",
        "discord_health",
        "quote_quality_metrics",
        "session_metrics",
        "watchlist",
        "data_acquisition",
        "runtime_resources",
        "runtime_resource_health",
        "operational_persistence",
    ]
    assert len({registration.actor_id for registration in plan}) == len(plan)
    acquisition = next(item for item in plan if item.key == "data_acquisition")
    assert acquisition.config.config["actor_id"] == "DATA-ACQUISITION"
    assert acquisition.config.config["instrument_ids"] == list(_config().instrument_ids)
    assert acquisition.config.config["historical"] == {
        "maximum_plan_requests": 64,
        "maximum_observations_per_request": 5000,
        "maximum_total_observations": 20000,
        "maximum_outstanding_requests": 64,
        "maximum_in_flight_requests": 1,
        "timeout_seconds": 30,
        "maximum_attempts": 3,
        "retry_backoff_ms": 500,
        "poll_interval_ms": 100,
    }
    assert acquisition.config.config["instrument_calendars"]["ESU6.CME"] == "cme_equity"
    assert {value["calendar_id"] for value in acquisition.config.config["calendars"]} == {
        "cboe_spxw",
        "us_equities",
        "cme_equity",
        "cme_energy",
    }
    watchlist = next(item for item in plan if item.key == "watchlist")
    assert watchlist.config.config["consumer_retry_interval_ms"] == 1000
    assert watchlist.config.config["members"] == [
        {
            "instrument_id": instrument_id,
            "calendar_id": (
                "cme_equity"
                if instrument_id in {"ESU6.CME", "NQU6.CME", "YMU6.CBOT"}
                else "cme_energy"
                if instrument_id == "CLV6.NYMEX"
                else "us_equities"
            ),
            "owner_ids": ["config:system"],
            "capabilities": (
                ["watchlist_last"]
                if instrument_id in {"^SPX.CBOE", "^VIX.CBOE"}
                else ["top_of_book", "watchlist_last"]
            ),
        }
        for instrument_id in [
            "ESU6.CME",
            "NQU6.CME",
            "YMU6.CBOT",
            "CLV6.NYMEX",
            "SPY.ARCA",
            "QQQ.NASDAQ",
            "^SPX.CBOE",
            "^VIX.CBOE",
            "NVDA.NASDAQ",
            "AAPL.NASDAQ",
            "GOOGL.NASDAQ",
            "MSFT.NASDAQ",
            "AMZN.NASDAQ",
            "TSM.NYSE",
            "AVGO.NASDAQ",
            "SPCX.NASDAQ",
            "META.NASDAQ",
            "TSLA.NASDAQ",
        ]
    ]
    evidence = next(item for item in plan if item.key == "evidence_health")
    assert evidence.config.config["consumer_retry_interval_ms"] == 1000
    quote_metrics = next(item for item in plan if item.key == "quote_quality_metrics")
    assert quote_metrics.config.config["instrument_ids"] == [
        instrument_id
        for instrument_id in _config().instrument_ids
        if instrument_id not in {"^SPX.CBOE", "^VIX.CBOE"}
    ]
    assert quote_metrics.config.config["minimum_update_interval_ms"] == 250
    assert quote_metrics.config.config["parameter_version"] == 1
    resources = next(item for item in plan if item.key == "runtime_resources")
    assert resources.config.config == {
        "actor_id": "RUNTIME-RESOURCES",
        "sample_interval_ms": 10000,
        "log_every_samples": 1,
        "include_cache_counts": True,
        "disk_path": "/",
    }
    health = next(item for item in plan if item.key == "runtime_resource_health")
    assert health.config.config["threshold_version"] == "2026-08-22-v2"
    assert health.config.config["warning"]["host_memory_available_percent"] == 15.0
    assert health.config.config["critical"]["disk_free_percent"] == 2.0
    discord = next(item for item in plan if item.key == "discord_health")
    assert discord.config.config["operational_events_webhook_env"] == (
        OPERATIONAL_EVENTS_WEBHOOK_ENV
    )


def test_actor_plan_omits_disabled_discord_but_never_core() -> None:
    config = _config()
    config = replace(config, discord=replace(config.discord, enabled=False))

    plan = build_actor_plan(config, _prerequisites())

    assert [registration.key for registration in plan] == [
        "system_control",
        "session_state",
        "evidence_health",
        "quote_quality_metrics",
        "session_metrics",
        "watchlist",
        "data_acquisition",
        "runtime_resources",
        "runtime_resource_health",
        "operational_persistence",
    ]


def test_actor_plan_omits_disabled_runtime_resource_telemetry() -> None:
    config = _config()
    config = replace(
        config,
        runtime_resources=replace(config.runtime_resources, enabled=False),
    )

    plan = build_actor_plan(config, _prerequisites())

    assert "runtime_resources" not in {registration.key for registration in plan}
    assert "runtime_resource_health" not in {registration.key for registration in plan}


def test_actor_plan_adds_enabled_visual_acceptance_before_analytical_producers() -> None:
    config = _config()
    config = replace(
        config,
        visual_acceptance=replace(config.visual_acceptance, enabled=True),
    )

    plan = build_actor_plan(config, _prerequisites())

    keys = [registration.key for registration in plan]
    assert keys.index("visual_acceptance") < keys.index("quote_quality_metrics")
    visual = next(item for item in plan if item.key == "visual_acceptance")
    assert visual.config.config["instrument_ids"] == list(config.instrument_ids)
    assert visual.config.config["bar_specifications"] == [
        "1-MINUTE-LAST-EXTERNAL",
        "5-MINUTE-LAST-EXTERNAL",
        "15-MINUTE-LAST-EXTERNAL",
    ]
    assert visual.config.config["refresh_interval_ms"] == 60000
    assert visual.config.config["view_windows_ms"] == {
        "1-MINUTE-LAST-EXTERNAL": 2_700_000,
        "5-MINUTE-LAST-EXTERNAL": 14_400_000,
        "15-MINUTE-LAST-EXTERNAL": 28_800_000,
    }
    assert visual.config.config["selected_metric_prefixes"] == {
        "1-MINUTE-LAST-EXTERNAL": ["rolling.fast.context_45m."],
        "5-MINUTE-LAST-EXTERNAL": ["rolling.tactical.context_4h."],
        "15-MINUTE-LAST-EXTERNAL": [
            "rolling.structural_intraday.context_8h.",
        ],
    }
    assert visual.config.config["annotation_expectations"] == []


def test_actor_plan_omits_disabled_native_consumer_probe() -> None:
    config = _config()
    config = replace(
        config,
        acquisition=replace(config.acquisition, native_consumer_probe_enabled=False),
    )

    plan = build_actor_plan(config, _prerequisites())

    assert "native_consumer_probe" not in {registration.key for registration in plan}


def test_actor_plan_adds_enabled_historical_dependency_probe() -> None:
    config = _config()
    config = replace(
        config,
        historical=replace(
            config.historical,
            probe=replace(config.historical.probe, enabled=True),
        ),
    )

    plan = build_actor_plan(config, _prerequisites())

    probes = [item for item in plan if item.key.startswith("historical_dependency_probe:")]
    assert [probe.actor_id for probe in probes] == [
        "HISTORICAL-PROBE-A",
        "HISTORICAL-PROBE-B",
    ]
    assert probes[0].config.config == {
        "actor_id": "HISTORICAL-PROBE-A",
        "instrument_id": "ESU6.CME",
        "selector": "1-MINUTE-LAST-EXTERNAL",
        "window": "recent_completed",
        "minimum_observations": 5,
        "maximum_observations": 10,
        "priority": 10,
    }


def test_actor_plan_adds_enabled_native_consumer_probe() -> None:
    config = _config()
    config = replace(
        config,
        acquisition=replace(config.acquisition, native_consumer_probe_enabled=True),
    )

    plan = build_actor_plan(config, _prerequisites())

    probe = next(item for item in plan if item.key == "native_consumer_probe")
    assert len(probe.config.config["feeds"]) == 34
    assert probe.config.config["feeds"][0] == {
        "instrument_id": "ESU6.CME",
        "calendar_id": "cme_equity",
        "kind": "quotes",
        "selector": "default",
    }
    assert probe.config.config["unsubscribe_after_seconds"] == 15


def test_actor_plan_adds_enabled_session_metrics_with_explicit_profiles() -> None:
    config = _config()
    config = replace(
        config,
        metrics=replace(
            config.metrics,
            session_measurements=replace(
                config.metrics.session_measurements,
                enabled=True,
            ),
        ),
    )

    plan = build_actor_plan(config, _prerequisites())

    actor = next(item for item in plan if item.key == "session_metrics")
    assert actor.actor_id == "SESSION-METRICS"
    assert actor.config.config["instrument_ids"] == list(config.instrument_ids)
    assert actor.config.config["profile_bindings"]["ESU6.CME"] == "cme_equity_primary"
    assert actor.config.config["profile_bindings"]["^SPX.CBOE"] == "us_index_primary"
    assert actor.config.config["profiles"][0]["overnight_enabled"] is False
    assert actor.config.config["completed_bars"] == {
        "live_selector": "5-SECOND-LAST-EXTERNAL",
        "historical_selector": "1-MINUTE-LAST-EXTERNAL",
        "historical_window": "recent_completed",
        "minimum_historical_observations": 2,
        "maximum_historical_observations": 720,
        "calculation_interval_seconds": 60,
        "minimum_interval_seconds": 5,
        "maximum_interval_seconds": 3600,
        "interval_step_seconds": 5,
        "interval_dynamic": True,
        "aggregation_boundary_policy": "utc_fixed_intraday",
        "timestamp_policy": "interval_start",
        "revision_policy": "reject_revision",
        "maximum_retained_observations": 8000,
        "maximum_output_age_ms": 120000,
    }
    assert actor.config.config["session_references"] == {
        "enabled": True,
        "historical_selector": "15-MINUTE-LAST-EXTERNAL",
        "active_window": "session_to_date",
        "previous_window": "previous_sessions",
        "overnight_window": "current_overnight",
        "minimum_historical_observations": 1,
        "maximum_historical_observations": 100,
        "vwap_price_basis": "typical",
        "vwap_price_basis_dynamic": True,
        "minimum_coverage_ratio": 0.8,
        "minimum_coverage_ratio_floor": 0.5,
        "minimum_coverage_ratio_ceiling": 1.0,
        "minimum_coverage_ratio_step": 0.05,
        "minimum_coverage_ratio_dynamic": True,
        "maximum_retained_sessions": 4,
        "maximum_output_age_ms": 120000,
    }
    assert actor.config.config["session_windows"] == {
        "enabled": True,
        "price_basis": "typical",
        "price_basis_dynamic": True,
        "minimum_coverage_ratio": 0.8,
        "minimum_coverage_ratio_floor": 0.5,
        "minimum_coverage_ratio_ceiling": 1.0,
        "minimum_coverage_ratio_step": 0.05,
        "minimum_coverage_ratio_dynamic": True,
        "maximum_retained_sessions": 4,
        "maximum_output_age_ms": 120000,
    }
    rolling = actor.config.config["rolling_measurements"]
    assert rolling["baseline"]["recent_reference_count"] == 20
    assert rolling["baseline"]["eligible_reference_health"] == ["READY"]
    assert [family["family_id"] for family in rolling["families"]] == [
        "fast",
        "tactical",
        "structural_intraday",
    ]
    assert rolling["families"][0]["selected_context_candidate_id"] == "context_45m"
    assert actor.config.config["profiles"][0]["windows"] == [
        {
            "window_id": "opening_range_fast",
            "purpose": "opening_range",
            "anchor_phase": "OPEN",
            "anchor_boundary": "start",
            "offset_seconds": 0,
            "duration_seconds": 300,
            "minimum_duration_seconds": 60,
            "maximum_duration_seconds": 1800,
            "duration_step_seconds": 60,
            "dynamic": True,
            "historical_selector": "1-MINUTE-LAST-EXTERNAL",
            "minimum_historical_observations": 1,
            "maximum_historical_observations": 5,
        },
        {
            "window_id": "opening_range_slow",
            "purpose": "opening_range",
            "anchor_phase": "OPEN",
            "anchor_boundary": "start",
            "offset_seconds": 0,
            "duration_seconds": 900,
            "minimum_duration_seconds": 300,
            "maximum_duration_seconds": 3600,
            "duration_step_seconds": 300,
            "dynamic": True,
            "historical_selector": "1-MINUTE-LAST-EXTERNAL",
            "minimum_historical_observations": 1,
            "maximum_historical_observations": 15,
        },
        {
            "window_id": "power_hour",
            "purpose": "power_hour",
            "anchor_phase": "OPEN",
            "anchor_boundary": "end",
            "offset_seconds": -3600,
            "duration_seconds": 3600,
            "minimum_duration_seconds": 1800,
            "maximum_duration_seconds": 7200,
            "duration_step_seconds": 300,
            "dynamic": True,
            "historical_selector": "15-MINUTE-LAST-EXTERNAL",
            "minimum_historical_observations": 1,
            "maximum_historical_observations": 4,
        },
    ]


def test_actor_plan_adds_enabled_session_reference_entity_owner(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    source = (root / "config/system.example.toml").read_text()
    definitions = (Path(__file__).with_name("entity-analysis-definitions.toml")).read_text()
    path = tmp_path / "system.toml"
    path.write_text(
        source.replace(
            "[metrics.entity_analysis]\nenabled = false",
            "[metrics.entity_analysis]\nenabled = true",
        ).replace("definitions = []", definitions),
    )
    config = load_system_config(path)

    plan = build_actor_plan(config, _prerequisites())

    actor = next(item for item in plan if item.key == "session_reference_entities")
    assert actor.actor_id == "SESSION-REFERENCE-ENTITIES"
    assert len(actor.config.config["instrument_profiles"]) == len(config.instrument_ids)
    assert {definition["entity_type"] for definition in actor.config.config["definitions"]} == {
        "analytical_session",
        "previous_session_reference",
        "opening_range",
        "gap",
        "objective_level.previous_session_high",
        "objective_level.previous_session_low",
        "objective_level.opening_range_high",
        "objective_level.opening_range_low",
    }
    assert actor.config.config["maximum_publications_per_cycle"] == 500


def test_actor_plan_adds_only_runtime_bound_market_state_definitions(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    source = (root / "config/system.example.toml").read_text()
    definitions = (Path(__file__).with_name("entity-analysis-definitions.toml")).read_text()
    path = tmp_path / "system.toml"
    path.write_text(
        source.replace(
            "[metrics.entity_analysis]\nenabled = false",
            "[metrics.entity_analysis]\nenabled = true",
        ).replace("definitions = []", definitions),
    )
    config = load_system_config(path)

    plan = build_actor_plan(config, _prerequisites())

    actor = next(item for item in plan if item.key == "market_state_entities")
    assert actor.actor_id == "MARKET-STATE-ENTITIES"
    assert actor.config.config["maximum_metric_values"] == 20000
    assert actor.config.config["reconciliation_interval_ms"] == 1000
    assert [item["definition_id"] for item in actor.config.config["definitions"]] == [
        "volatility-state-v1",
    ]
    definition = actor.config.config["definitions"][0]
    assert definition["market_state"]["parameter_set_id"] == ("volatility-percentile-fixture")
    assert definition["market_state"]["policies"][0]["measure_role"] == ("normalized_volatility")


def test_actor_plan_rejects_market_state_metric_without_runtime_producer(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    source = (root / "config/system.example.toml").read_text()
    definitions = (Path(__file__).with_name("entity-analysis-definitions.toml")).read_text()
    definitions = definitions.replace(
        "rolling.fast.context_45m.range_percentile_recent",
        "rolling.fast.missing_candidate.range_percentile_recent",
    )
    path = tmp_path / "system.toml"
    path.write_text(
        source.replace(
            "[metrics.entity_analysis]\nenabled = false",
            "[metrics.entity_analysis]\nenabled = true",
        ).replace("definitions = []", definitions),
    )
    config = load_system_config(path)

    with pytest.raises(ValueError, match="require unavailable runtime metrics"):
        build_actor_plan(config, _prerequisites())


def test_actor_plan_rejects_entity_metric_without_configured_producer(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    source = (root / "config/system.example.toml").read_text()
    definitions = (Path(__file__).with_name("entity-analysis-definitions.toml")).read_text()
    definitions = definitions.replace(
        "opening_range.cme_equity_primary.opening_range_fast.high",
        "opening_range.cme_equity_primary.missing_window.high",
    )
    path = tmp_path / "system.toml"
    path.write_text(
        source.replace(
            "[metrics.entity_analysis]\nenabled = false",
            "[metrics.entity_analysis]\nenabled = true",
        ).replace("definitions = []", definitions),
    )
    config = load_system_config(path)

    with pytest.raises(ValueError, match="require unavailable metrics"):
        build_actor_plan(config, _prerequisites())


def test_actor_plan_rejects_missing_required_preflight() -> None:
    with pytest.raises(ValueError, match="persistence must pass preflight"):
        build_actor_plan(_config(), _prerequisites(ready=False))


def test_enabled_discord_and_postgres_environment_are_required() -> None:
    config = _config()

    with pytest.raises(RuntimeError, match=SYSTEM_HEALTH_WEBHOOK_ENV):
        validate_runtime_environment(
            config,
            {config.persistence.dsn_env: "postgresql://configured"},
        )

    with pytest.raises(RuntimeError, match=OPERATIONAL_EVENTS_WEBHOOK_ENV):
        validate_runtime_environment(
            config,
            {
                config.persistence.dsn_env: "postgresql://configured",
                SYSTEM_HEALTH_WEBHOOK_ENV: "https://configured",
            },
        )


def test_disabled_discord_requires_only_postgres_environment() -> None:
    config = _config()
    config = replace(config, discord=replace(config.discord, enabled=False))

    validate_runtime_environment(
        config,
        {config.persistence.dsn_env: "postgresql://configured"},
    )
