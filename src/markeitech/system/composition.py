from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from nautilus_trader.common import ImportableActorConfig

from markeitech.system.config import SystemConfig
from markeitech.system.discord import SYSTEM_HEALTH_WEBHOOK_ENV


def _canonical_calendar_payload(calendar) -> dict[str, object]:  # noqa: ANN001
    return {
        "calendar_id": calendar.calendar_id,
        "schedule_version": calendar.schedule_version,
        "calendar_engine": calendar.calendar_engine,
        "calendar_engine_version": calendar.calendar_engine_version,
        "provider_calendar": calendar.provider_calendar,
        "provider_calendar_class": calendar.provider_calendar_class,
        "exchange_timezone": calendar.exchange_timezone,
        "schedule_columns": list(calendar.schedule_columns),
        "definition_version": calendar.definition_version,
        "effective_from_ns": calendar.effective_from_ns,
        "definition_digest": calendar.definition_digest,
        "phases": [
            {
                "name": phase.name,
                "timezone": phase.timezone,
                "start_kind": phase.start_kind,
                "start_value": phase.start_value,
                "start_day_offset": phase.start_day_offset,
                "end_kind": phase.end_kind,
                "end_value": phase.end_value,
                "end_day_offset": phase.end_day_offset,
                "exchange_constraint": phase.exchange_constraint,
            }
            for phase in calendar.phases
        ],
        "corrections": [
            {
                "correction_id": correction.correction_id,
                "kind": correction.kind,
                "source_id": correction.source_id,
                "product_roots": list(correction.product_roots),
                "effective_from_trade_date": correction.effective_from_trade_date,
                "timezone": correction.timezone,
                "expected_start": correction.expected_start,
                "expected_end": correction.expected_end,
            }
            for correction in calendar.corrections
        ],
        "sources": [
            {
                "source_id": source.source_id,
                "title": source.title,
                "url": source.url,
                "retrieved_at_ns": source.retrieved_at_ns,
                "content_sha256": source.content_sha256,
                "retrieval_status": source.retrieval_status,
            }
            for source in calendar.sources
        ],
    }


def _watchlist_feeds(config: SystemConfig) -> list[dict[str, str]]:
    feeds: list[dict[str, str]] = []
    for member in config.watchlist.members:
        capabilities = set(member.capabilities)
        if "top_of_book" in capabilities:
            feeds.append(
                {
                    "instrument_id": member.instrument_id,
                    "calendar_id": member.calendar_id,
                    "kind": "quotes",
                    "selector": "default",
                },
            )
        if "watchlist_last" in capabilities:
            feeds.append(
                {
                    "instrument_id": member.instrument_id,
                    "calendar_id": member.calendar_id,
                    "kind": "bars",
                    "selector": "5-SECOND-LAST-EXTERNAL",
                },
            )
    return feeds


@dataclass(frozen=True, slots=True)
class StartupPrerequisites:
    run_id: UUID
    operational_persistence_ready: bool
    evidence_recency_profiles: tuple[dict[str, object], ...] = ()


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

    # Inputs used by the previous full registration plan below.
    # instrument_ids = list(config.instrument_ids)
    # projection_retry = {
    #     "response_timeout_ms": config.sessions.projection_retry.response_timeout_ms,
    #     "maximum_attempts": config.sessions.projection_retry.maximum_attempts,
    #     "retry_backoff_ms": config.sessions.projection_retry.retry_backoff_ms,
    #     "maximum_elapsed_ms": config.sessions.projection_retry.maximum_elapsed_ms,
    # }
    # current_state_delivery = {
    #     "policy_version": config.sessions.current_state_delivery.policy_version,
    #     "response_timeout_ms": config.sessions.current_state_delivery.response_timeout_ms,
    #     "maximum_attempts": config.sessions.current_state_delivery.maximum_attempts,
    #     "retry_backoff_ms": config.sessions.current_state_delivery.retry_backoff_ms,
    #     "maximum_elapsed_ms": config.sessions.current_state_delivery.maximum_elapsed_ms,
    #     "maximum_buffered_transitions_per_calendar": (
    #         config.sessions.current_state_delivery.maximum_buffered_transitions_per_calendar
    #     ),
    #     "maximum_total_buffered_transitions": (
    #         config.sessions.current_state_delivery.maximum_total_buffered_transitions
    #     ),
    #     "boundary_delivery_grace_ms": (
    #         config.sessions.current_state_delivery.boundary_delivery_grace_ms
    #     ),
    # }
    # allowed_current_state_requesters = [
    #     "EVIDENCE-HEALTH",
    #     "HISTORICAL-EVIDENCE-PLANNER",
    # ]
    run_id = str(prerequisites.run_id)
    system_control = config.system_control
    persistence = config.persistence
    resources = config.runtime_resources
    health = resources.health
    registrations = [
        ActorRegistration(
            key="system_control",
            actor_id="SYSTEM-CONTROL",
            config=ImportableActorConfig(
                actor_path="markeitech.system.actor:SystemControlActor",
                config_path="markeitech.system.actor:SystemControlActorConfig",
                config={
                    "actor_id": "SYSTEM-CONTROL",
                    "run_id": run_id,
                    "resource_threshold_version": health.threshold_version,
                    "operational_persistence_ready": True,
                    "failure_policy": [
                        {
                            "component": rule.component,
                            "startup": rule.startup,
                            "running": rule.running,
                        }
                        for rule in system_control.component_failures
                    ],
                },
            ),
        ),
    ]

    if config.discord.enabled:
        # Subscribe before the remaining startup actors can complete readiness.
        registrations.append(
            ActorRegistration(
                key="discord_webhooks",
                actor_id="DISCORD-WEBHOOKS",
                config=ImportableActorConfig(
                    actor_path="markeitech.system.discord:DiscordWebhooksActor",
                    config_path="markeitech.system.discord:DiscordWebhooksActorConfig",
                    config={
                        "actor_id": "DISCORD-WEBHOOKS",
                        "request_timeout_seconds": config.discord.request_timeout_seconds,
                        "queue_capacity": config.discord.queue_capacity,
                        "ping_critical_resource_alerts": (
                            config.discord.ping_critical_resource_alerts
                        ),
                        "webhook_env": SYSTEM_HEALTH_WEBHOOK_ENV,
                    },
                ),
            ),
        )

    registrations.extend(
        [
            ActorRegistration(
                key="operational_persistence",
                actor_id="OPERATIONAL-PERSISTENCE",
                config=ImportableActorConfig(
                    actor_path="markeitech.system.persistence:OperationalPersistenceActor",
                    config_path="markeitech.system.persistence:OperationalPersistenceActorConfig",
                    config={
                        "actor_id": "OPERATIONAL-PERSISTENCE",
                        "run_id": run_id,
                        "dsn_env": persistence.dsn_env,
                        "connect_timeout_seconds": persistence.connect_timeout_seconds,
                        "queue_capacity": persistence.queue_capacity,
                        "critical_queue_reserve": persistence.critical_queue_reserve,
                        "write_batch_size": persistence.write_batch_size,
                        "result_poll_interval_ms": persistence.result_poll_interval_ms,
                        "shutdown_timeout_seconds": persistence.shutdown_timeout_seconds,
                        "write_max_attempts": persistence.write_max_attempts,
                        "write_retry_backoff_ms": persistence.write_retry_backoff_ms,
                    },
                ),
            ),
            # The sampler schedules periodic work before Health evaluates its samples.
            ActorRegistration(
                key="runtime_resources",
                actor_id="RUNTIME-RESOURCES",
                config=ImportableActorConfig(
                    actor_path="markeitech.system.resource_actor:RuntimeResourceActor",
                    config_path="markeitech.system.resource_actor:RuntimeResourceActorConfig",
                    config={
                        "actor_id": "RUNTIME-RESOURCES",
                        "run_id": run_id,
                        "sample_interval_ms": resources.sample_interval_ms,
                        "log_every_samples": resources.log_every_samples,
                        "include_cache_counts": resources.include_cache_counts,
                        "disk_path": resources.disk_path,
                    },
                ),
            ),
            # Health acknowledges the first sampler event it actually evaluates.
            ActorRegistration(
                key="runtime_resource_health",
                actor_id="RUNTIME-RESOURCE-HEALTH",
                config=ImportableActorConfig(
                    actor_path="markeitech.system.resource_health_actor:RuntimeResourceHealthActor",
                    config_path=(
                        "markeitech.system.resource_health_actor:RuntimeResourceHealthActorConfig"
                    ),
                    config={
                        "actor_id": "RUNTIME-RESOURCE-HEALTH",
                        "run_id": run_id,
                        "sample_interval_ms": resources.sample_interval_ms,
                        "threshold_version": health.threshold_version,
                        "warning_consecutive_samples": health.warning_consecutive_samples,
                        "critical_consecutive_samples": health.critical_consecutive_samples,
                        "recovery_consecutive_samples": health.recovery_consecutive_samples,
                        "notification_cooldown_ms": health.notification_cooldown_ms,
                        "rss_growth_window_samples": health.rss_growth_window_samples,
                        "stale_warning_ms": health.stale_warning_ms,
                        "stale_critical_ms": health.stale_critical_ms,
                        "warning": health.warning.to_dict(),
                        "critical": health.critical.to_dict(),
                    },
                ),
            ),
        ]
    )

    # Remaining pre-redesign registrations, retained for the actors not yet restored.
    # Original order: session_state -> evidence_health -> historical_evidence_planner ->
    # [watchlist] -> data_acquisition. Brackets mark optional registration.
    # registrations = [
    #     ActorRegistration(
    #         key="session_state",
    #         actor_id="SESSION-STATE",
    #         config=ImportableActorConfig(
    #             actor_path="markeitech.intelligence.actors:SessionStateActor",
    #             config_path="markeitech.intelligence.actors:SessionStateActorConfig",
    #             config={
    #                 "actor_id": "SESSION-STATE",
    #                 "evaluation_interval_ms": config.sessions.evaluation_interval_ms,
    #                 "source_epoch": str(prerequisites.run_id),
    #                 "maximum_projection_days": config.sessions.maximum_projection_days,
    #                 "maximum_calendars_per_request": (
    #                     config.sessions.maximum_calendars_per_request
    #                 ),
    #                 "current_state_delivery": current_state_delivery,
    #                 "allowed_current_state_requesters": allowed_current_state_requesters,
    #                 "calendars": [
    #                     _canonical_calendar_payload(calendar)
    #                     for calendar in config.sessions.calendars
    #                 ],
    #             },
    #         ),
    #     ),
    #     ActorRegistration(
    #         key="evidence_health",
    #         actor_id="EVIDENCE-HEALTH",
    #         config=ImportableActorConfig(
    #             actor_path="markeitech.intelligence.actors:EvidenceHealthActor",
    #             config_path="markeitech.intelligence.actors:EvidenceHealthActorConfig",
    #             config={
    #                 "actor_id": "EVIDENCE-HEALTH",
    #                 "feeds": _watchlist_feeds(config),
    #                 "evaluation_interval_ms": config.evidence_health.evaluation_interval_ms,
    #                 "consumer_retry_interval_ms": (
    #                     config.evidence_health.consumer_retry_interval_ms
    #                 ),
    #                 "provider_id": config.evidence_health.provider_id,
    #                 "profile_checkpoint_samples": (
    #                     config.evidence_health.profile_checkpoint_samples
    #                 ),
    #                 "recency_profiles": list(prerequisites.evidence_recency_profiles),
    #                 "calendar_source": "SESSION-STATE",
    #                 "calendar_source_epoch": str(prerequisites.run_id),
    #                 "current_state_delivery": current_state_delivery,
    #                 "calendar_expectations": [
    #                     {
    #                         "calendar_id": calendar.calendar_id,
    #                         "definition_version": calendar.definition_version,
    #                         "definition_digest": calendar.definition_digest,
    #                         "definition_effective_from_ns": calendar.effective_from_ns,
    #                     }
    #                     for calendar in config.sessions.calendars
    #                 ],
    #                 "policies": [
    #                     {
    #                         "feed_kind": policy.feed_kind,
    #                         "selector": policy.selector,
    #                         "fresh_for_ms": policy.fresh_for_ms,
    #                         "stale_after_ms": policy.stale_after_ms,
    #                         "unavailable_after_ms": policy.unavailable_after_ms,
    #                         "adaptive": policy.adaptive,
    #                         "minimum_samples": policy.minimum_samples,
    #                         "decay_factor": policy.decay_factor,
    #                         "fresh_stddev_multiplier": policy.fresh_stddev_multiplier,
    #                         "stale_stddev_multiplier": policy.stale_stddev_multiplier,
    #                         "unavailable_stddev_multiplier": (
    #                             policy.unavailable_stddev_multiplier
    #                         ),
    #                         "min_fresh_ms": policy.min_fresh_ms,
    #                         "max_fresh_ms": policy.max_fresh_ms,
    #                         "min_stale_ms": policy.min_stale_ms,
    #                         "max_stale_ms": policy.max_stale_ms,
    #                         "min_unavailable_ms": policy.min_unavailable_ms,
    #                         "max_unavailable_ms": policy.max_unavailable_ms,
    #                     }
    #                     for policy in config.evidence_health.policies
    #                 ],
    #             },
    #         ),
    #     ),
    # ]
    # registrations.extend(
    #     [
    #         ActorRegistration(
    #             key="historical_evidence_planner",
    #             actor_id="HISTORICAL-EVIDENCE-PLANNER",
    #             config=ImportableActorConfig(
    #                 actor_path=(
    #                     "markeitech.system.historical_planner:HistoricalEvidencePlannerActor"
    #                 ),
    #                 config_path=(
    #                     "markeitech.system.historical_planner:"
    #                     "HistoricalEvidencePlannerActorConfig"
    #                 ),
    #                 config={
    #                     "actor_id": "HISTORICAL-EVIDENCE-PLANNER",
    #                     "instrument_ids": instrument_ids,
    #                     "instrument_calendars": {
    #                         member.instrument_id: member.calendar_id
    #                         for member in config.watchlist.members
    #                     },
    #                     "expected_calendar_digests": {
    #                         calendar.calendar_id: calendar.definition_digest
    #                         for calendar in config.sessions.calendars
    #                     },
    #                     "projection_lookback_days": config.sessions.projection_lookback_days,
    #                     "projection_lookahead_days": config.sessions.projection_lookahead_days,
    #                     "calendar_source": "SESSION-STATE",
    #                     "calendar_source_epoch": str(prerequisites.run_id),
    #                     "projection_retry": projection_retry,
    #                     "current_state_delivery": current_state_delivery,
    #                     "calendar_expectations": [
    #                         {
    #                             "calendar_id": calendar.calendar_id,
    #                             "definition_version": calendar.definition_version,
    #                             "definition_digest": calendar.definition_digest,
    #                             "definition_effective_from_ns": calendar.effective_from_ns,
    #                         }
    #                         for calendar in config.sessions.calendars
    #                     ],
    #                     "historical": {
    #                         "maximum_plan_requests": config.historical.maximum_plan_requests,
    #                         "maximum_observations_per_request": (
    #                             config.historical.maximum_observations_per_request
    #                         ),
    #                         "maximum_total_observations": (
    #                             config.historical.maximum_total_observations
    #                         ),
    #                     },
    #                 },
    #             ),
    #         ),
    #     ],
    # )
    # if config.watchlist.enabled:
    #     registrations.append(
    #         ActorRegistration(
    #             key="watchlist",
    #             actor_id="WATCHLIST",
    #             config=ImportableActorConfig(
    #                 actor_path="markeitech.system.watchlist:WatchlistActor",
    #                 config_path="markeitech.system.watchlist:WatchlistActorConfig",
    #                 config={
    #                     "actor_id": "WATCHLIST",
    #                     "consumer_retry_interval_ms": config.watchlist.consumer_retry_interval_ms,
    #                     "members": [
    #                         {
    #                             "instrument_id": member.instrument_id,
    #                             "calendar_id": member.calendar_id,
    #                             "owner_ids": list(member.owner_ids),
    #                             "capabilities": list(member.capabilities),
    #                         }
    #                         for member in config.watchlist.members
    #                     ],
    #                 },
    #             ),
    #         ),
    #     )
    # registrations.append(
    #     ActorRegistration(
    #         key="data_acquisition",
    #         actor_id="DATA-ACQUISITION",
    #         config=ImportableActorConfig(
    #             actor_path="markeitech.system.acquisition:DataAcquisitionActor",
    #             config_path="markeitech.system.acquisition:DataAcquisitionActorConfig",
    #             config={
    #                 "actor_id": "DATA-ACQUISITION",
    #                 "instrument_ids": instrument_ids,
    #                 "historical": {
    #                     "maximum_plan_requests": config.historical.maximum_plan_requests,
    #                     "maximum_observations_per_request": (
    #                         config.historical.maximum_observations_per_request
    #                     ),
    #                     "maximum_total_observations": (
    #                         config.historical.maximum_total_observations
    #                     ),
    #                     "maximum_outstanding_requests": (
    #                         config.historical.maximum_outstanding_requests
    #                     ),
    #                     "maximum_in_flight_requests": (
    #                         config.historical.maximum_in_flight_requests
    #                     ),
    #                     "timeout_seconds": config.historical.timeout_seconds,
    #                     "maximum_attempts": config.historical.maximum_attempts,
    #                     "retry_backoff_ms": config.historical.retry_backoff_ms,
    #                     "poll_interval_ms": config.historical.poll_interval_ms,
    #                 },
    #             },
    #         ),
    #     ),
    # )
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
