"""Build the bounded, factual SL-01 capability-readiness snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from time import time_ns
from uuid import uuid4

from markeitech.sir_loke.config import SirLokeConfig
from markeitech.sir_loke.contracts import (
    CapabilityReadinessSnapshotV1,
    CapabilityStatusV1,
    ConfigurationState,
    EvidenceState,
    RuntimeState,
    SnapshotClaimV1,
)
from markeitech.system.config import SystemConfig


@dataclass(frozen=True, slots=True)
class LocalDependencyState:
    discord_ready: bool
    model_ready: bool
    audit_ready: bool


def build_readiness_snapshot(
    config: SirLokeConfig,
    system: SystemConfig,
    dependencies: LocalDependencyState,
    *,
    now_ns: int | None = None,
) -> CapabilityReadinessSnapshotV1:
    """Describe only configured state and this dedicated process's observed dependencies."""

    generated_at_ns = time_ns() if now_ns is None else now_ns
    instruments = system.instrument_ids
    metrics_enabled = system.metrics.session_measurements.enabled
    entities_enabled = system.metrics.entity_analysis.enabled

    capabilities = (
        _capability(
            "sir_loke.conversation",
            ConfigurationState.ENABLED,
            RuntimeState.READY
            if all((dependencies.discord_ready, dependencies.model_ready, dependencies.audit_ready))
            else RuntimeState.DEGRADED,
            EvidenceState.OBSERVED,
            "The private SL-01 capability-readiness conversation is configured in this process.",
        ),
        _capability(
            "discord.private_dm",
            ConfigurationState.ENABLED,
            RuntimeState.READY if dependencies.discord_ready else RuntimeState.UNAVAILABLE,
            EvidenceState.OBSERVED if dependencies.discord_ready else EvidenceState.NOT_OBSERVED,
            "Discord admission is restricted to one configured application, user, and DM channel.",
        ),
        _capability(
            "model.structured_reply_plan",
            ConfigurationState.ENABLED,
            RuntimeState.READY if dependencies.model_ready else RuntimeState.UNKNOWN,
            EvidenceState.OBSERVED if dependencies.model_ready else EvidenceState.CONFIGURED_ONLY,
            "The model may select admitted claim identifiers; it has no tools or "
            "market-data access.",
        ),
        _capability(
            "audit.postgresql",
            ConfigurationState.ENABLED,
            RuntimeState.READY if dependencies.audit_ready else RuntimeState.UNAVAILABLE,
            EvidenceState.OBSERVED if dependencies.audit_ready else EvidenceState.NOT_OBSERVED,
            "PostgreSQL is the required durable audit boundary for every accepted turn.",
        ),
        _capability(
            "instruments.configured",
            ConfigurationState.PRESENT if instruments else ConfigurationState.ABSENT,
            RuntimeState.NOT_RUNNING,
            EvidenceState.CONFIGURED_ONLY,
            "The system profile declares the instruments listed in this snapshot.",
            instruments,
        ),
        _capability(
            "market.live_observation",
            ConfigurationState.ABSENT,
            RuntimeState.NOT_RUNNING,
            EvidenceState.NOT_OBSERVED,
            "SL-01 does not start Interactive Brokers or observe current market data.",
            instruments,
        ),
        _capability(
            "evidence.current",
            ConfigurationState.ABSENT,
            RuntimeState.UNAVAILABLE,
            EvidenceState.NOT_OBSERVED,
            "No current market-evidence stream is admitted to the SL-01 process.",
            instruments,
        ),
        _capability(
            "historical.analysis",
            ConfigurationState.PRESENT
            if system.historical.probe.enabled
            else ConfigurationState.DISABLED,
            RuntimeState.NOT_RUNNING,
            EvidenceState.CONFIGURED_ONLY,
            "A system-profile historical probe may be configured, but SL-01 does not run it.",
            instruments,
        ),
        _capability(
            "analytics.market_measurements",
            ConfigurationState.ENABLED if metrics_enabled else ConfigurationState.DISABLED,
            RuntimeState.NOT_RUNNING,
            EvidenceState.NOT_OBSERVED,
            "Market measurements are not running in the dedicated SL-01 process.",
            instruments,
        ),
        _capability(
            "analytics.market_entities",
            ConfigurationState.ENABLED if entities_enabled else ConfigurationState.DISABLED,
            RuntimeState.NOT_RUNNING,
            EvidenceState.NOT_OBSERVED,
            "Market entities are not running in the dedicated SL-01 process.",
            instruments,
        ),
        _capability(
            "options.analysis",
            ConfigurationState.ABSENT,
            RuntimeState.NOT_APPLICABLE,
            EvidenceState.NOT_APPLICABLE,
            "Options analysis is not implemented or admitted in SL-01.",
        ),
        _capability(
            "trade.assessment",
            ConfigurationState.ABSENT,
            RuntimeState.NOT_APPLICABLE,
            EvidenceState.NOT_APPLICABLE,
            "Trade assessment is not implemented or admitted in SL-01.",
        ),
        _capability(
            "trade.monitoring",
            ConfigurationState.ABSENT,
            RuntimeState.NOT_APPLICABLE,
            EvidenceState.NOT_APPLICABLE,
            "Trade monitoring is not implemented or admitted in SL-01.",
        ),
        _capability(
            "order.execution",
            ConfigurationState.ABSENT,
            RuntimeState.NOT_APPLICABLE,
            EvidenceState.NOT_APPLICABLE,
            "Sir Loke has no submit, modify, cancel, replace, close, or other execution "
            "capability.",
        ),
    )
    claims = _claims(capabilities, instruments, config)
    if len(capabilities) > config.limits.maximum_capabilities:
        raise RuntimeError("readiness snapshot exceeds the configured capability bound")
    if len(claims) > config.limits.maximum_claims:
        raise RuntimeError("readiness snapshot exceeds the configured claim bound")
    return CapabilityReadinessSnapshotV1(
        snapshot_id=uuid4(),
        generated_at_ns=generated_at_ns,
        expires_at_ns=generated_at_ns + config.limits.snapshot_max_age_seconds * 1_000_000_000,
        system_profile_id=system.runtime.name,
        capabilities=capabilities,
        claims=claims,
    )


def _capability(
    capability_id: str,
    configuration_state: ConfigurationState,
    runtime_state: RuntimeState,
    evidence_state: EvidenceState,
    detail: str,
    instrument_ids: tuple[str, ...] = (),
) -> CapabilityStatusV1:
    return CapabilityStatusV1(
        capability_id=capability_id,
        configuration_state=configuration_state,
        runtime_state=runtime_state,
        evidence_state=evidence_state,
        detail=detail,
        instrument_ids=instrument_ids,
    )


def _claims(
    capabilities: tuple[CapabilityStatusV1, ...],
    instruments: tuple[str, ...],
    config: SirLokeConfig,
) -> tuple[SnapshotClaimV1, ...]:
    claims = [
        SnapshotClaimV1(
            claim_id="identity.sl01",
            capability_id="sir_loke.conversation",
            text="I am Sir Loke's SL-01 private capability-readiness bot.",
        ),
        SnapshotClaimV1(
            claim_id="scope.capability_only",
            capability_id="sir_loke.conversation",
            text="In this task I can explain what this exact profile can and cannot do.",
        ),
        SnapshotClaimV1(
            claim_id="scope.unrelated",
            capability_id="sir_loke.conversation",
            text="That request is outside SL-01's capability-readiness scope.",
        ),
        SnapshotClaimV1(
            claim_id="model.identity",
            capability_id="model.structured_reply_plan",
            text=f"The requested model alias is {config.model.model} with low reasoning effort.",
        ),
        SnapshotClaimV1(
            claim_id="model.no_tools",
            capability_id="model.structured_reply_plan",
            text=(
                "The model receives no tools and can only select factual claim identifiers "
                "from a fresh snapshot."
            ),
        ),
        SnapshotClaimV1(
            claim_id="instruments.configured",
            capability_id="instruments.configured",
            text=(
                f"Configured instruments: {', '.join(instruments)}."
                if instruments
                else "No instruments are configured in the selected system profile."
            ),
        ),
        SnapshotClaimV1(
            claim_id="market.not_live",
            capability_id="market.live_observation",
            text=(
                "This SL-01 process does not connect to Interactive Brokers and has no "
                "live market observations."
            ),
        ),
        SnapshotClaimV1(
            claim_id="evidence.none_current",
            capability_id="evidence.current",
            text=(
                "I have no current market evidence in this profile, so I cannot answer "
                "current-market questions."
            ),
        ),
        SnapshotClaimV1(
            claim_id="historical.not_running",
            capability_id="historical.analysis",
            text="Historical analysis is not running in this SL-01 process.",
        ),
        SnapshotClaimV1(
            claim_id="analytics.not_running",
            capability_id="analytics.market_measurements",
            text=(
                "Market measurements and analytical entities are not running in this SL-01 process."
            ),
        ),
        SnapshotClaimV1(
            claim_id="options.absent",
            capability_id="options.analysis",
            text="Options analysis is not implemented or admitted in SL-01.",
        ),
        SnapshotClaimV1(
            claim_id="assessment.absent",
            capability_id="trade.assessment",
            text="Trade assessment is not implemented or admitted in SL-01.",
        ),
        SnapshotClaimV1(
            claim_id="monitoring.absent",
            capability_id="trade.monitoring",
            text="Trade monitoring is not implemented or admitted in SL-01.",
        ),
        SnapshotClaimV1(
            claim_id="execution.never",
            capability_id="order.execution",
            text="I cannot submit, modify, cancel, replace, close, or otherwise execute an order.",
        ),
        SnapshotClaimV1(
            claim_id="next.live_test",
            capability_id="sir_loke.conversation",
            text="You can test another capability question in this same private DM.",
        ),
    ]
    capability_by_id = {item.capability_id: item for item in capabilities}
    for dependency, claim_id, label in (
        ("discord.private_dm", "dependency.discord", "Discord"),
        ("model.structured_reply_plan", "dependency.model", "Model"),
        ("audit.postgresql", "dependency.audit", "PostgreSQL audit"),
    ):
        state = capability_by_id[dependency].runtime_state
        claims.append(
            SnapshotClaimV1(
                claim_id=claim_id,
                capability_id=dependency,
                text=f"{label} dependency state for this snapshot is {state.value}.",
            )
        )
    return tuple(claims)
