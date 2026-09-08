"""OpenAI Responses boundary for SL-01's claim-selection plan."""

from __future__ import annotations

import json
from typing import Protocol

from openai import AsyncOpenAI

from markeitech.sir_loke.config import ModelRuntimeConfig
from markeitech.sir_loke.contracts import (
    CapabilityReadinessSnapshotV1,
    ProviderReplyV1,
    ProviderUsageV1,
    SirLokeReplyPlanV1,
)

_INSTRUCTIONS = """You are the bounded planning component for Sir Loke SL-01.
Answer only capability-readiness questions about the exact supplied snapshot.
Return only the strict SirLokeReplyPlanV1 structure. Select claim_id values that appear in the
snapshot. Never introduce facts, prose, advice, market interpretation, prices, recommendations,
orders, or capabilities. For a current-market, options, trade-assessment, monitoring, execution,
or unrelated request, select the relevant limitation claims and ABSTAIN. You have no tools.
For a broad "what can you see" question, select configured instrument, current-evidence,
live-market, and analytical-readiness claims. For a follow-up about one named capability, select
the smallest directly relevant claim set. For a request to buy, sell, enter, stop, target, or
otherwise assess a trade, ABSTAIN and select the current-evidence and trade-assessment limitations.
"""


class ReplyPlanProvider(Protocol):
    async def plan_reply(
        self,
        *,
        question: str,
        snapshot: CapabilityReadinessSnapshotV1,
        prior_exchange: tuple[str, str] | None,
    ) -> ProviderReplyV1: ...

    async def close(self) -> None: ...


class OpenAIResponsesProvider:
    def __init__(self, config: ModelRuntimeConfig, api_key: str) -> None:
        self._config = config
        self._observed_ready = False
        self._client = AsyncOpenAI(
            api_key=api_key,
            timeout=float(config.timeout_seconds),
            max_retries=0,
        )

    async def plan_reply(
        self,
        *,
        question: str,
        snapshot: CapabilityReadinessSnapshotV1,
        prior_exchange: tuple[str, str] | None,
    ) -> ProviderReplyV1:
        payload: dict[str, object] = {
            "question": question,
            "snapshot": snapshot.model_dump(mode="json"),
        }
        if prior_exchange is not None:
            payload["prior_accepted_exchange"] = {
                "question": prior_exchange[0],
                "answer": prior_exchange[1],
            }
        response = await self._client.responses.parse(
            model=self._config.model,
            instructions=_INSTRUCTIONS,
            input=json.dumps(payload, sort_keys=True, separators=(",", ":")),
            text_format=SirLokeReplyPlanV1,
            reasoning={"effort": self._config.reasoning_effort},
            max_output_tokens=self._config.max_output_tokens,
            tools=[],
            store=False,
            truncation="disabled",
        )
        plan = response.output_parsed
        if plan is None:
            raise RuntimeError("model response did not contain a structured reply plan")
        usage = response.usage
        if usage is None:
            raise RuntimeError("model response did not include token usage")
        self._observed_ready = True
        return ProviderReplyV1(
            request_id=response.id,
            requested_model=self._config.model,
            returned_model=response.model,
            plan=plan,
            usage=ProviderUsageV1(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            ),
        )

    async def close(self) -> None:
        await self._client.close()

    @property
    def observed_ready(self) -> bool:
        return self._observed_ready
