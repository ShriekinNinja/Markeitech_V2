"""Provider-free, single-calendar configuration for native delivery tests."""
from dataclasses import replace
from pathlib import Path

from markeitech.system.config import SystemConfig, load_system_config


def minimal_calendar_config() -> SystemConfig:
    """Derive a bounded ES-only fixture without maintaining a runtime profile."""
    config = load_system_config(Path(__file__).parents[2] / "config/system.example.toml")
    return replace(
        config,
        watchlist=replace(config.watchlist, members=(
            replace(config.watchlist.members[0], capabilities=("watchlist_last",)),
        )),
        sessions=replace(config.sessions, calendars=tuple(
            item for item in config.sessions.calendars if item.calendar_id == "cme_equity"
        )),
        discord=replace(config.discord, enabled=False),
        runtime_resources=replace(config.runtime_resources, enabled=False),
        dashboard=replace(config.dashboard, enabled=False),
        historical=replace(
            config.historical, maximum_plan_requests=1,
            maximum_observations_per_request=60, maximum_total_observations=60,
            maximum_outstanding_requests=1, maximum_in_flight_requests=1,
            maximum_attempts=1,
        ),
    )
