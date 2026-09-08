"""Typed Sir Loke SL-01 model and audit contracts."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictFrozenModel(BaseModel):
    """Reject undeclared fields and mutation at every contract level."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ConfigurationState(StrEnum):
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"


class RuntimeState(StrEnum):
    READY = "READY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_RUNNING = "NOT_RUNNING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class EvidenceState(StrEnum):
    OBSERVED = "OBSERVED"
    CONFIGURED_ONLY = "CONFIGURED_ONLY"
    NOT_OBSERVED = "NOT_OBSERVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class CapabilityStatusV1(StrictFrozenModel):
    capability_id: str = Field(min_length=1, max_length=80)
    configuration_state: ConfigurationState
    runtime_state: RuntimeState
    evidence_state: EvidenceState
    detail: str = Field(min_length=1, max_length=300)
    instrument_ids: tuple[str, ...] = Field(default=(), max_length=16)


class SnapshotClaimV1(StrictFrozenModel):
    claim_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,79}$")
    capability_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=400)


class CapabilityReadinessSnapshotV1(StrictFrozenModel):
    schema_version: Literal[1] = 1
    snapshot_id: UUID
    generated_at_ns: int = Field(ge=0)
    expires_at_ns: int = Field(gt=0)
    system_profile_id: str = Field(min_length=1, max_length=120)
    profile_id: Literal["SL-01"] = "SL-01"
    capabilities: tuple[CapabilityStatusV1, ...] = Field(max_length=16)
    claims: tuple[SnapshotClaimV1, ...] = Field(max_length=64)

    @model_validator(mode="after")
    def validate_identity(self) -> CapabilityReadinessSnapshotV1:
        if self.expires_at_ns <= self.generated_at_ns:
            raise ValueError("snapshot expiry must follow generation")
        capability_ids = [item.capability_id for item in self.capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("capability ids must be unique")
        claim_ids = [item.claim_id for item in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("claim ids must be unique")
        unknown = sorted({item.capability_id for item in self.claims} - set(capability_ids))
        if unknown:
            raise ValueError(f"claims reference unknown capabilities: {', '.join(unknown)}")
        return self

    @property
    def digest(self) -> str:
        payload = self.model_dump(mode="json")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


class ReplyDisposition(StrEnum):
    ANSWER = "ANSWER"
    CLARIFY = "CLARIFY"
    ABSTAIN = "ABSTAIN"


class ReplySegmentV1(StrictFrozenModel):
    claim_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,79}$")
    framing: Literal["FACT", "LIMITATION", "NEXT_STEP"]


class SirLokeReplyPlanV1(StrictFrozenModel):
    schema_version: Literal[1] = 1
    disposition: ReplyDisposition
    segments: tuple[ReplySegmentV1, ...] = Field(min_length=1, max_length=8)
    closing: Literal["NONE", "ASK_CAPABILITY_QUESTION", "SUGGEST_LIVE_TEST"] = "NONE"

    @model_validator(mode="after")
    def validate_claim_selection(self) -> SirLokeReplyPlanV1:
        claim_ids = [item.claim_id for item in self.segments]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("reply-plan claim ids must be unique")
        return self


class ProviderUsageV1(StrictFrozenModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


class ProviderReplyV1(StrictFrozenModel):
    request_id: str = Field(min_length=1, max_length=200)
    requested_model: str = Field(min_length=1, max_length=100)
    returned_model: str = Field(min_length=1, max_length=100)
    plan: SirLokeReplyPlanV1
    usage: ProviderUsageV1


class ConversationReplyV1(StrictFrozenModel):
    turn_id: UUID
    invocation_id: UUID | None
    content: str = Field(min_length=1, max_length=1900)
    paid_dispatch: bool
    provider_request_id: str | None = None
    cost_usd: float = Field(ge=0)
