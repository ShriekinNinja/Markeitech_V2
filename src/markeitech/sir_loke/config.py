"""Strict configuration for the isolated Sir Loke SL-01 runtime."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DISCORD_TOKEN_ENV = "MARKEITECH_SIR_LOKE_DISCORD_BOT_TOKEN"
OPENAI_API_KEY_ENV = "MARKEITECH_SIR_LOKE_OPENAI_API_KEY"
POSTGRES_DSN_ENV = "MARKEITECH_POSTGRES_DSN"


@dataclass(frozen=True, slots=True)
class DiscordRuntimeConfig:
    application_id: int
    user_id: int
    dm_channel_id: int
    maximum_recent_message_ids: int


@dataclass(frozen=True, slots=True)
class ModelRuntimeConfig:
    model: str
    reasoning_effort: str
    timeout_seconds: int
    max_output_tokens: int
    input_price_per_million_usd: float
    output_price_per_million_usd: float


@dataclass(frozen=True, slots=True)
class ConversationLimitsConfig:
    snapshot_max_age_seconds: int
    maximum_capabilities: int
    maximum_claims: int
    maximum_input_characters: int
    maximum_total_input_tokens: int
    maximum_reply_characters: int
    maximum_calls_per_session: int
    maximum_calls_per_day: int
    idle_timeout_seconds: int
    absolute_timeout_seconds: int
    maximum_call_cost_usd: float
    maximum_session_cost_usd: float
    maximum_daily_cost_usd: float


@dataclass(frozen=True, slots=True)
class AuditConfig:
    connect_timeout_seconds: int
    prune_interval_seconds: int
    content_retention_days: int
    metadata_retention_days: int


@dataclass(frozen=True, slots=True)
class SirLokeConfig:
    schema_version: int
    profile_id: str
    system_config_path: Path
    log_path: Path
    discord: DiscordRuntimeConfig
    model: ModelRuntimeConfig
    limits: ConversationLimitsConfig
    audit: AuditConfig


def load_sir_loke_config(path: str | Path) -> SirLokeConfig:
    config_path = Path(path).resolve()
    with config_path.open("rb") as file:
        raw = tomllib.load(file)
    _keys(
        raw,
        {
            "schema_version",
            "profile_id",
            "system_config",
            "log_path",
            "discord",
            "model",
            "limits",
            "audit",
        },
        "root",
    )
    if raw["schema_version"] != 1:
        raise ValueError(f"unsupported Sir Loke schema_version: {raw['schema_version']!r}")
    if raw["profile_id"] != "SL-01":
        raise ValueError("profile_id must be 'SL-01'")

    discord = _table(raw["discord"], "discord")
    _keys(
        discord,
        {
            "application_id",
            "user_id",
            "dm_channel_id",
            "maximum_recent_message_ids",
        },
        "discord",
    )
    model = _table(raw["model"], "model")
    _keys(
        model,
        {
            "name",
            "reasoning_effort",
            "timeout_seconds",
            "max_output_tokens",
            "input_price_per_million_usd",
            "output_price_per_million_usd",
        },
        "model",
    )
    limits = _table(raw["limits"], "limits")
    _keys(
        limits,
        {
            "snapshot_max_age_seconds",
            "maximum_capabilities",
            "maximum_claims",
            "maximum_input_characters",
            "maximum_total_input_tokens",
            "maximum_reply_characters",
            "maximum_calls_per_session",
            "maximum_calls_per_day",
            "idle_timeout_seconds",
            "absolute_timeout_seconds",
            "maximum_call_cost_usd",
            "maximum_session_cost_usd",
            "maximum_daily_cost_usd",
        },
        "limits",
    )
    audit = _table(raw["audit"], "audit")
    _keys(
        audit,
        {
            "connect_timeout_seconds",
            "prune_interval_seconds",
            "content_retention_days",
            "metadata_retention_days",
        },
        "audit",
    )

    config = SirLokeConfig(
        schema_version=1,
        profile_id="SL-01",
        system_config_path=_relative_path(raw["system_config"], config_path, "system_config"),
        log_path=_relative_path(raw["log_path"], config_path, "log_path"),
        discord=DiscordRuntimeConfig(
            application_id=_positive_int(discord["application_id"], "discord.application_id"),
            user_id=_positive_int(discord["user_id"], "discord.user_id"),
            dm_channel_id=_positive_int(discord["dm_channel_id"], "discord.dm_channel_id"),
            maximum_recent_message_ids=_positive_int(
                discord["maximum_recent_message_ids"],
                "discord.maximum_recent_message_ids",
            ),
        ),
        model=ModelRuntimeConfig(
            model=_non_empty(model["name"], "model.name"),
            reasoning_effort=_non_empty(model["reasoning_effort"], "model.reasoning_effort"),
            timeout_seconds=_positive_int(model["timeout_seconds"], "model.timeout_seconds"),
            max_output_tokens=_positive_int(model["max_output_tokens"], "model.max_output_tokens"),
            input_price_per_million_usd=_positive_number(
                model["input_price_per_million_usd"], "model.input_price_per_million_usd"
            ),
            output_price_per_million_usd=_positive_number(
                model["output_price_per_million_usd"], "model.output_price_per_million_usd"
            ),
        ),
        limits=ConversationLimitsConfig(
            **{
                name: (
                    _positive_number(value, f"limits.{name}")
                    if name.endswith("_usd")
                    else _positive_int(value, f"limits.{name}")
                )
                for name, value in limits.items()
            }
        ),
        audit=AuditConfig(
            connect_timeout_seconds=_positive_int(
                audit["connect_timeout_seconds"], "audit.connect_timeout_seconds"
            ),
            prune_interval_seconds=_positive_int(
                audit["prune_interval_seconds"], "audit.prune_interval_seconds"
            ),
            content_retention_days=_positive_int(
                audit["content_retention_days"], "audit.content_retention_days"
            ),
            metadata_retention_days=_positive_int(
                audit["metadata_retention_days"], "audit.metadata_retention_days"
            ),
        ),
    )
    _validate(config)
    return config


def _validate(config: SirLokeConfig) -> None:
    discord_ids = (
        config.discord.application_id,
        config.discord.user_id,
        config.discord.dm_channel_id,
    )
    if len(set(discord_ids)) != 3 or any(value > 2**64 - 1 for value in discord_ids):
        raise ValueError("SL-01 Discord identities must be distinct unsigned 64-bit snowflakes")
    if config.discord.maximum_recent_message_ids > 256:
        raise ValueError("SL-01 Discord deduplication bound cannot exceed 256 messages")
    if config.model.model != "gpt-5.6-luna" or config.model.reasoning_effort != "low":
        raise ValueError("SL-01 requires gpt-5.6-luna with low reasoning effort")
    if config.model.timeout_seconds > 20:
        raise ValueError("SL-01 model timeout cannot exceed 20 seconds")
    if config.model.max_output_tokens != 512:
        raise ValueError("SL-01 max_output_tokens must equal 512")
    if (
        config.model.input_price_per_million_usd != 0.20
        or config.model.output_price_per_million_usd != 1.20
    ):
        raise ValueError("SL-01 pricing identity must match the approved model prices")
    if config.limits.snapshot_max_age_seconds > 5:
        raise ValueError("SL-01 snapshot age cannot exceed five seconds")
    if config.limits.maximum_capabilities > 16 or config.limits.maximum_claims > 64:
        raise ValueError("SL-01 snapshot bounds exceed the accepted envelope")
    if config.limits.maximum_input_characters > 2000:
        raise ValueError("SL-01 input-character bound exceeds 2000")
    if config.limits.maximum_total_input_tokens > 4096:
        raise ValueError("SL-01 input-token bound exceeds 4096")
    if config.limits.maximum_reply_characters > 1900:
        raise ValueError("SL-01 reply-character bound exceeds 1900")
    if config.limits.maximum_calls_per_session > 3 or config.limits.maximum_calls_per_day > 50:
        raise ValueError("SL-01 call bounds exceed the accepted envelope")
    if (
        config.limits.idle_timeout_seconds > 600
        or config.limits.absolute_timeout_seconds > 900
    ):
        raise ValueError("SL-01 session duration exceeds the accepted envelope")
    if (
        config.limits.maximum_call_cost_usd > 0.0015
        or config.limits.maximum_session_cost_usd > 0.0045
        or config.limits.maximum_daily_cost_usd > 0.075
    ):
        raise ValueError("SL-01 cost bounds exceed the accepted envelope")
    if config.audit.content_retention_days > 7 or config.audit.metadata_retention_days > 30:
        raise ValueError("SL-01 audit retention exceeds the accepted envelope")
    if config.audit.connect_timeout_seconds > 5 or config.audit.prune_interval_seconds > 3_600:
        raise ValueError("SL-01 audit timing exceeds the accepted envelope")
    worst_case = (
        config.limits.maximum_total_input_tokens * config.model.input_price_per_million_usd
        + config.model.max_output_tokens * config.model.output_price_per_million_usd
    ) / 1_000_000
    if worst_case > config.limits.maximum_call_cost_usd:
        raise ValueError("configured per-call cap cannot admit the accepted worst-case request")


def _keys(raw: dict[str, Any], expected: set[str], label: str) -> None:
    missing = sorted(expected - set(raw))
    extra = sorted(set(raw) - expected)
    if missing or extra:
        raise ValueError(f"{label} keys differ: missing={missing}, extra={extra}")


def _table(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a table")
    return value


def _positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _positive_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive number")
    return float(value)


def _non_empty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _relative_path(value: Any, config_path: Path, label: str) -> Path:
    raw = _non_empty(value, label)
    path = Path(raw)
    return path.resolve() if path.is_absolute() else (config_path.parent / path).resolve()
