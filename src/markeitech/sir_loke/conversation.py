"""Bounded conversational orchestration for Sir Loke SL-01."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import time, time_ns
from uuid import UUID, uuid4

from markeitech.sir_loke.audit import SirLokeAuditWriter
from markeitech.sir_loke.config import SirLokeConfig
from markeitech.sir_loke.contracts import (
    CapabilityReadinessSnapshotV1,
    ConversationReplyV1,
    ProviderReplyV1,
    ReplyDisposition,
    SirLokeReplyPlanV1,
    SnapshotClaimV1,
)
from markeitech.sir_loke.model_provider import ReplyPlanProvider

_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b(?:mfa\.)?[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i)\b(?:api[_ -]?key|token|password|secret)\s*[:=]"),
)
_MARKET_TERMS = re.compile(
    r"(?i)\b(?:price|market|buy|sell|trade|position|option|call|put|order|stop|target|entry|exit|bullish|bearish|long|short)\b"
)
_CAPABILITY_TERMS = re.compile(
    r"(?i)\b(?:hello|hi|who|what|you|can|capability|see|know|access|connected|running|available|ready|configured|audit|discord|model|instrument|historical|analytics|evidence)\b"
)


@dataclass(slots=True)
class _SessionState:
    conversation_id: UUID
    started_at_seconds: float
    last_activity_seconds: float
    calls: int = 0
    cost_usd: float = 0.0
    prior_exchange: tuple[str, str] | None = None


class SirLokeConversation:
    def __init__(
        self,
        config: SirLokeConfig,
        provider: ReplyPlanProvider,
        audit: SirLokeAuditWriter,
        snapshot_factory: Callable[[], CapabilityReadinessSnapshotV1],
        *,
        initial_daily_calls: int = 0,
        initial_daily_cost_usd: float = 0.0,
    ) -> None:
        now = time()
        self._config = config
        self._provider = provider
        self._audit = audit
        self._snapshot_factory = snapshot_factory
        self._session = _SessionState(audit.conversation_id, now, now)
        self._daily_bucket = int(now // 86_400)
        self._daily_calls = initial_daily_calls
        self._daily_cost_usd = initial_daily_cost_usd
        self._lock = asyncio.Lock()

    async def handle(self, raw_content: str) -> ConversationReplyV1:
        turn_id = uuid4()
        if self._lock.locked():
            reply = ConversationReplyV1(
                turn_id=turn_id,
                invocation_id=None,
                content="I am still handling the previous request. Please wait for that reply.",
                paid_dispatch=False,
                cost_usd=0,
            )
            await self._safe_audit(
                turn_id=turn_id,
                invocation_id=None,
                phase="REQUEST_LIMITED",
                content=None,
                metadata={"reason": "one request is already in flight"},
            )
            return reply
        async with self._lock:
            return await self._handle_locked(turn_id, raw_content)

    async def reject_non_text(self) -> ConversationReplyV1:
        turn_id = uuid4()
        content = (
            "SL-01 accepts text-only capability questions; attachments and embeds are not admitted."
        )
        await self._safe_audit(
            turn_id=turn_id,
            invocation_id=None,
            phase="REQUEST_REJECTED",
            content=None,
            metadata={"reason": "non-text Discord content"},
        )
        return ConversationReplyV1(
            turn_id=turn_id,
            invocation_id=None,
            content=content,
            paid_dispatch=False,
            cost_usd=0,
        )

    async def _handle_locked(self, turn_id: UUID, raw_content: str) -> ConversationReplyV1:
        now_seconds = time()
        self._roll_session(now_seconds)
        content, rejection = _admit_content(raw_content, self._config)
        if rejection is not None:
            await self._safe_audit(
                turn_id=turn_id,
                invocation_id=None,
                phase="REQUEST_REJECTED",
                content=None,
                metadata={"reason": rejection},
            )
            return ConversationReplyV1(
                turn_id=turn_id,
                invocation_id=None,
                content=rejection,
                paid_dispatch=False,
                cost_usd=0,
            )

        limit_message = self._limit_message()
        if limit_message is not None:
            await self._safe_audit(
                turn_id=turn_id,
                invocation_id=None,
                phase="REQUEST_LIMITED",
                content={"input": content},
                metadata={"reason": limit_message},
            )
            return ConversationReplyV1(
                turn_id=turn_id,
                invocation_id=None,
                content=limit_message,
                paid_dispatch=False,
                cost_usd=0,
            )

        snapshot = self._snapshot_factory()
        invocation_id = uuid4()
        estimated_tokens = _estimate_input_tokens(content, snapshot, self._session.prior_exchange)
        if estimated_tokens > self._config.limits.maximum_total_input_tokens:
            reply = ConversationReplyV1(
                turn_id=turn_id,
                invocation_id=None,
                content=(
                    "That request exceeds this profile's bounded context. "
                    "Please ask a shorter capability question."
                ),
                paid_dispatch=False,
                cost_usd=0,
            )
            await self._audit_limit(turn_id, content, "estimated input-token bound")
            return reply
        estimated_cost = self._cost(
            estimated_tokens,
            self._config.model.max_output_tokens,
        )
        if estimated_cost > self._config.limits.maximum_call_cost_usd:
            reply = ConversationReplyV1(
                turn_id=turn_id,
                invocation_id=None,
                content="I cannot dispatch that request within the configured per-call budget.",
                paid_dispatch=False,
                cost_usd=0,
            )
            await self._audit_limit(turn_id, content, "per-call cost bound")
            return reply
        if self._session.cost_usd + estimated_cost > self._config.limits.maximum_session_cost_usd:
            reply = ConversationReplyV1(
                turn_id=turn_id,
                invocation_id=None,
                content="I cannot dispatch that request within the remaining session budget.",
                paid_dispatch=False,
                cost_usd=0,
            )
            await self._audit_limit(turn_id, content, "remaining session cost bound")
            return reply
        if self._daily_cost_usd + estimated_cost > self._config.limits.maximum_daily_cost_usd:
            reply = ConversationReplyV1(
                turn_id=turn_id,
                invocation_id=None,
                content="I cannot dispatch that request within the remaining daily budget.",
                paid_dispatch=False,
                cost_usd=0,
            )
            await self._audit_limit(turn_id, content, "remaining daily cost bound")
            return reply
        try:
            await self._audit.write(
                turn_id=turn_id,
                invocation_id=invocation_id,
                phase="REQUEST_ADMITTED",
                content={
                    "input": content,
                    "snapshot": snapshot.model_dump(mode="json"),
                    "prior_exchange": self._session.prior_exchange,
                },
                metadata={
                    "snapshot_id": str(snapshot.snapshot_id),
                    "snapshot_digest": snapshot.digest,
                    "requested_model": self._config.model.model,
                    "estimated_input_tokens": estimated_tokens,
                    "estimated_maximum_cost_usd": estimated_cost,
                },
            )
        except Exception:
            return ConversationReplyV1(
                turn_id=turn_id,
                invocation_id=None,
                content="I cannot continue because the required audit record could not be stored.",
                paid_dispatch=False,
                cost_usd=0,
            )

        self._session.calls += 1
        self._daily_calls += 1
        self._session.cost_usd += estimated_cost
        self._daily_cost_usd += estimated_cost
        charged_cost = estimated_cost
        try:
            provider_reply = await self._provider.plan_reply(
                question=content,
                snapshot=snapshot,
                prior_exchange=self._session.prior_exchange,
            )
            render_snapshot = self._snapshot_factory()
            rendered = _validate_and_render(
                content,
                render_snapshot,
                provider_reply,
                self._config.limits.maximum_reply_characters,
            )
            actual_cost = self._cost(
                provider_reply.usage.input_tokens,
                provider_reply.usage.output_tokens,
            )
            if actual_cost > self._config.limits.maximum_call_cost_usd:
                raise RuntimeError("provider usage exceeded the per-call cost cap")
            charged_cost = actual_cost
            await self._audit.write(
                turn_id=turn_id,
                invocation_id=invocation_id,
                phase="MODEL_COMPLETED",
                content={
                    "reply_plan": provider_reply.plan.model_dump(mode="json"),
                    "render_snapshot": render_snapshot.model_dump(mode="json"),
                    "rendered_reply": rendered,
                },
                metadata={
                    "provider_request_id": provider_reply.request_id,
                    "requested_model": provider_reply.requested_model,
                    "returned_model": provider_reply.returned_model,
                    "render_snapshot_id": str(render_snapshot.snapshot_id),
                    "render_snapshot_digest": render_snapshot.digest,
                    "input_tokens": provider_reply.usage.input_tokens,
                    "output_tokens": provider_reply.usage.output_tokens,
                    "cost_usd": actual_cost,
                    "validation": "ACCEPTED",
                },
            )
        except Exception as exc:
            await self._safe_audit(
                turn_id=turn_id,
                invocation_id=invocation_id,
                phase="MODEL_FAILED",
                content=None,
                metadata={"error_type": type(exc).__name__, "validation": "REJECTED"},
            )
            return ConversationReplyV1(
                turn_id=turn_id,
                invocation_id=invocation_id,
                content=(
                    "I could not produce a validated reply from the admitted evidence. "
                    "Please try again."
                ),
                paid_dispatch=True,
                cost_usd=charged_cost,
            )

        self._session.cost_usd += actual_cost - estimated_cost
        self._daily_cost_usd += actual_cost - estimated_cost
        self._session.last_activity_seconds = now_seconds
        self._session.prior_exchange = (content, rendered)
        return ConversationReplyV1(
            turn_id=turn_id,
            invocation_id=invocation_id,
            content=rendered,
            paid_dispatch=True,
            provider_request_id=provider_reply.request_id,
            cost_usd=actual_cost,
        )

    async def record_delivery(self, reply: ConversationReplyV1, *, delivered: bool) -> None:
        await self._safe_audit(
            turn_id=reply.turn_id,
            invocation_id=reply.invocation_id,
            phase="REPLY_DELIVERED" if delivered else "REPLY_DELIVERY_FAILED",
            content={"rendered_reply": reply.content},
            metadata={
                "provider_request_id": reply.provider_request_id,
                "paid_dispatch": reply.paid_dispatch,
                "cost_usd": reply.cost_usd,
            },
        )

    def _roll_session(self, now_seconds: float) -> None:
        day = int(now_seconds // 86_400)
        if day != self._daily_bucket:
            self._daily_bucket = day
            self._daily_calls = 0
            self._daily_cost_usd = 0
        idle = now_seconds - self._session.last_activity_seconds
        age = now_seconds - self._session.started_at_seconds
        if (
            idle >= self._config.limits.idle_timeout_seconds
            or age >= self._config.limits.absolute_timeout_seconds
        ):
            conversation_id = uuid4()
            self._session = _SessionState(conversation_id, now_seconds, now_seconds)
            self._audit.reset_conversation(conversation_id)

    def _limit_message(self) -> str | None:
        limits = self._config.limits
        if self._session.calls >= limits.maximum_calls_per_session:
            return (
                "This bounded conversation has reached its three-call session limit. "
                "Wait for the session to expire before testing again."
            )
        if self._daily_calls >= limits.maximum_calls_per_day:
            return "The SL-01 daily call limit has been reached. No model request was sent."
        if self._session.cost_usd >= limits.maximum_session_cost_usd:
            return "The SL-01 session cost limit has been reached. No model request was sent."
        if self._daily_cost_usd >= limits.maximum_daily_cost_usd:
            return "The SL-01 daily cost limit has been reached. No model request was sent."
        return None

    def _cost(self, input_tokens: int, output_tokens: int) -> float:
        model = self._config.model
        return (
            input_tokens * model.input_price_per_million_usd
            + output_tokens * model.output_price_per_million_usd
        ) / 1_000_000

    async def _safe_audit(
        self,
        *,
        turn_id: UUID,
        invocation_id: UUID | None,
        phase: str,
        content: Mapping[str, object] | None,
        metadata: Mapping[str, object],
    ) -> None:
        try:
            await self._audit.write(
                turn_id=turn_id,
                invocation_id=invocation_id,
                phase=phase,
                content=content,
                metadata=metadata,
            )
        except Exception:
            pass

    async def _audit_limit(self, turn_id: UUID, content: str, reason: str) -> None:
        await self._safe_audit(
            turn_id=turn_id,
            invocation_id=None,
            phase="REQUEST_LIMITED",
            content={"input": content},
            metadata={"reason": reason},
        )


def _admit_content(raw_content: str, config: SirLokeConfig) -> tuple[str, str | None]:
    content = raw_content.strip()
    if not content:
        return "", "Please send a non-empty capability question."
    if len(content) > config.limits.maximum_input_characters:
        return "", "That message exceeds the 2,000-character SL-01 input limit."
    if any(ord(character) < 32 and character not in "\n\t" for character in content):
        return "", "That message contains unsupported control characters."
    if any(pattern.search(content) for pattern in _SECRET_PATTERNS):
        return (
            "",
            "That message appears to contain a secret. It was not stored or sent to the model.",
        )
    return content, None


def _estimate_input_tokens(
    content: str,
    snapshot: CapabilityReadinessSnapshotV1,
    prior_exchange: tuple[str, str] | None,
) -> int:
    characters = len(content) + len(snapshot.model_dump_json()) + 900
    if prior_exchange is not None:
        characters += len(prior_exchange[0]) + len(prior_exchange[1])
    return (characters + 3) // 4


def _validate_and_render(
    question: str,
    snapshot: CapabilityReadinessSnapshotV1,
    provider_reply: ProviderReplyV1,
    maximum_characters: int,
) -> str:
    if time_ns() > snapshot.expires_at_ns:
        raise RuntimeError("readiness snapshot expired before reply validation")
    claim_by_id = {claim.claim_id: claim for claim in snapshot.claims}
    selected_ids = [segment.claim_id for segment in provider_reply.plan.segments]
    unknown = sorted(set(selected_ids) - set(claim_by_id))
    if unknown:
        raise RuntimeError(f"reply plan selected unknown claims: {', '.join(unknown)}")
    required = _required_limitation_claim(question)
    if required is not None:
        if provider_reply.plan.disposition is not ReplyDisposition.ABSTAIN:
            raise RuntimeError("out-of-scope question was not answered with abstention")
        if required not in selected_ids:
            raise RuntimeError("out-of-scope reply omitted its required limitation claim")
    rendered = _render(provider_reply.plan, claim_by_id)
    if len(rendered) > maximum_characters:
        raise RuntimeError("rendered reply exceeds the configured Discord bound")
    return rendered


def _required_limitation_claim(question: str) -> str | None:
    lowered = question.lower()
    if any(
        term in lowered for term in ("execute", "place order", "cancel order", "close position")
    ):
        return "execution.never"
    if "option" in lowered or re.search(r"\b(?:call|put)\b", lowered):
        return "options.absent"
    if any(term in lowered for term in ("assess", "setup", "entry", "exit", "target")):
        return "assessment.absent"
    if "monitor" in lowered or "position" in lowered:
        return "monitoring.absent"
    if _MARKET_TERMS.search(question):
        return "evidence.none_current"
    if not _CAPABILITY_TERMS.search(question):
        return "scope.unrelated"
    return None


def _render(
    plan: SirLokeReplyPlanV1,
    claim_by_id: dict[str, SnapshotClaimV1],
) -> str:
    lines: list[str] = []
    prefix = {"FACT": "", "LIMITATION": "Limit: ", "NEXT_STEP": "Next: "}
    for segment in plan.segments:
        claim = claim_by_id[segment.claim_id]
        lines.append(f"{prefix[segment.framing]}{claim.text}")
    if plan.closing == "ASK_CAPABILITY_QUESTION":
        lines.append("What other capability would you like me to check?")
    elif plan.closing == "SUGGEST_LIVE_TEST":
        lines.append("Next: Ask one more capability question in this private DM.")
    return "\n".join(lines)
