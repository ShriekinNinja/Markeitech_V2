from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from nautilus_trader.common import ImportableActorConfig

from markeitech.system.config import SystemConfig
from markeitech.system.discord import SYSTEM_HEALTH_WEBHOOK_ENV


@dataclass(frozen=True, slots=True)
class StartupPrerequisites:
    run_id: UUID
    operational_persistence_ready: bool


@dataclass(frozen=True, slots=True)
class ActorRegistration:
    key: str
    actor_id: str
    config: ImportableActorConfig


def build_actor_plan(
    config: SystemConfig,
    prerequisites: StartupPrerequisites,
) -> tuple[ActorRegistration, ...]:
    if not prerequisites.operational_persistence_ready:
        raise ValueError("operational persistence must pass preflight before actor composition")

    instrument_ids = [item.id for item in config.instruments]
    registrations = [
        ActorRegistration(
            key="system_control",
            actor_id="SYSTEM-CONTROL",
            config=ImportableActorConfig(
                actor_path="markeitech.system.actor:SystemControlActor",
                config_path="markeitech.system.actor:SystemControlActorConfig",
                config={
                    "actor_id": "SYSTEM-CONTROL",
                    "instrument_ids": instrument_ids,
                    "operational_persistence_ready": True,
                },
            ),
        ),
    ]
    if config.discord.enabled:
        registrations.append(
            ActorRegistration(
                key="discord_health",
                actor_id="DISCORD-HEALTH",
                config=ImportableActorConfig(
                    actor_path="markeitech.system.discord:DiscordHealthActor",
                    config_path="markeitech.system.discord:DiscordHealthActorConfig",
                    config={
                        "actor_id": "DISCORD-HEALTH",
                        "request_timeout_seconds": config.discord.request_timeout_seconds,
                        "webhook_env": SYSTEM_HEALTH_WEBHOOK_ENV,
                    },
                ),
            ),
        )
    registrations.append(
        ActorRegistration(
            key="operational_persistence",
            actor_id="OPERATIONAL-PERSISTENCE",
            config=ImportableActorConfig(
                actor_path="markeitech.system.persistence:OperationalPersistenceActor",
                config_path=(
                    "markeitech.system.persistence:OperationalPersistenceActorConfig"
                ),
                config={
                    "actor_id": "OPERATIONAL-PERSISTENCE",
                    "run_id": str(prerequisites.run_id),
                    "dsn_env": config.persistence.dsn_env,
                    "connect_timeout_seconds": config.persistence.connect_timeout_seconds,
                    "queue_capacity": config.persistence.queue_capacity,
                    "result_poll_interval_ms": config.persistence.result_poll_interval_ms,
                    "shutdown_timeout_seconds": config.persistence.shutdown_timeout_seconds,
                },
            ),
        ),
    )
    _reject_duplicate_actor_ids(registrations)
    return tuple(registrations)


def validate_runtime_environment(
    config: SystemConfig,
    environment: Mapping[str, str],
) -> None:
    required = [config.persistence.dsn_env]
    if config.discord.enabled:
        required.append(SYSTEM_HEALTH_WEBHOOK_ENV)
    missing = [name for name in required if not environment.get(name, "").strip()]
    if missing:
        raise RuntimeError(f"required runtime environment is missing: {', '.join(sorted(missing))}")


def _reject_duplicate_actor_ids(registrations: list[ActorRegistration]) -> None:
    actor_ids = [registration.actor_id for registration in registrations]
    duplicates = sorted({actor_id for actor_id in actor_ids if actor_ids.count(actor_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate actor ids: {', '.join(duplicates)}")
