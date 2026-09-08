from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID, uuid4

import pytest

import markeitech.sir_loke.discord_transport as discord_transport
import markeitech.sir_loke.model_provider as model_provider
from markeitech.sir_loke.config import load_sir_loke_config
from markeitech.sir_loke.contracts import (
    CapabilityReadinessSnapshotV1,
    CapabilityStatusV1,
    ConfigurationState,
    EvidenceState,
    ProviderReplyV1,
    ProviderUsageV1,
    ReplyDisposition,
    ReplySegmentV1,
    RuntimeState,
    SirLokeReplyPlanV1,
    SnapshotClaimV1,
)
from markeitech.sir_loke.conversation import SirLokeConversation
from markeitech.sir_loke.discord_transport import SirLokeDiscordClient
from markeitech.sir_loke.model_provider import OpenAIResponsesProvider
from markeitech.sir_loke.read_model import LocalDependencyState, build_readiness_snapshot
from markeitech.system.config import load_system_config
from markeitech.system.persistence import SirLokeAuditEventRecord

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class FakeProvider:
    def __init__(self, plan: SirLokeReplyPlanV1) -> None:
        self.plan = plan
        self.calls = 0

    async def plan_reply(self, **_values: object) -> ProviderReplyV1:
        self.calls += 1
        return ProviderReplyV1(
            request_id="resp_test",
            requested_model="gpt-5.6-luna",
            returned_model="gpt-5.6-luna",
            plan=self.plan,
            usage=ProviderUsageV1(input_tokens=100, output_tokens=20),
        )

    async def close(self) -> None:
        return None


class FailingProvider(FakeProvider):
    async def plan_reply(self, **_values: object) -> ProviderReplyV1:
        self.calls += 1
        raise TimeoutError("provider timeout")


class FakeAudit:
    def __init__(self, *, fail: bool = False) -> None:
        self.conversation_id = uuid4()
        self.fail = fail
        self.events: list[dict[str, object]] = []

    def reset_conversation(self, conversation_id: UUID) -> None:
        self.conversation_id = conversation_id

    async def write(self, **values: object) -> None:
        if self.fail:
            raise RuntimeError("audit unavailable")
        self.events.append(values)


class FakeResponses:
    def __init__(self) -> None:
        self.arguments: dict[str, object] = {}

    async def parse(self, **values: object):  # noqa: ANN202
        self.arguments = values
        return type(
            "Response",
            (),
            {
                "id": "resp_test",
                "model": "gpt-5.6-luna",
                "output_parsed": SirLokeReplyPlanV1(
                    disposition=ReplyDisposition.ANSWER,
                    segments=(ReplySegmentV1(claim_id="identity.sl01", framing="FACT"),),
                ),
                "usage": type("Usage", (), {"input_tokens": 10, "output_tokens": 2})(),
            },
        )()


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()

    async def close(self) -> None:
        return None


def _config():  # noqa: ANN202
    return load_sir_loke_config(PROJECT_ROOT / "config/sir-loke.sl01.example.toml")


def _snapshot() -> CapabilityReadinessSnapshotV1:
    return CapabilityReadinessSnapshotV1(
        snapshot_id=uuid4(),
        generated_at_ns=1,
        expires_at_ns=9_999_999_999_999_999_999,
        system_profile_id="test",
        capabilities=(
            CapabilityStatusV1(
                capability_id="sir_loke.conversation",
                configuration_state=ConfigurationState.ENABLED,
                runtime_state=RuntimeState.READY,
                evidence_state=EvidenceState.OBSERVED,
                detail="test",
            ),
            CapabilityStatusV1(
                capability_id="market.live_observation",
                configuration_state=ConfigurationState.ABSENT,
                runtime_state=RuntimeState.NOT_RUNNING,
                evidence_state=EvidenceState.NOT_OBSERVED,
                detail="test",
            ),
        ),
        claims=(
            SnapshotClaimV1(
                claim_id="identity.sl01",
                capability_id="sir_loke.conversation",
                text="I am the SL-01 capability bot.",
            ),
            SnapshotClaimV1(
                claim_id="scope.unrelated",
                capability_id="sir_loke.conversation",
                text="That request is outside scope.",
            ),
            SnapshotClaimV1(
                claim_id="market.not_live",
                capability_id="market.live_observation",
                text="No live market observations are available.",
            ),
            SnapshotClaimV1(
                claim_id="evidence.none_current",
                capability_id="market.live_observation",
                text="No current market evidence is available.",
            ),
        ),
    )


def test_example_config_and_system_profile_build_an_honest_snapshot() -> None:
    config = _config()
    system = load_system_config(config.system_config_path)

    snapshot = build_readiness_snapshot(
        config,
        system,
        LocalDependencyState(discord_ready=True, model_ready=True, audit_ready=True),
        now_ns=100,
    )

    assert snapshot.profile_id == "SL-01"
    assert len(snapshot.capabilities) <= config.limits.maximum_capabilities
    assert len(snapshot.claims) <= config.limits.maximum_claims
    assert (
        next(
            item
            for item in snapshot.capabilities
            if item.capability_id == "market.live_observation"
        ).runtime_state
        is RuntimeState.NOT_RUNNING
    )
    assert (
        next(
            item for item in snapshot.capabilities if item.capability_id == "order.execution"
        ).configuration_state
        is ConfigurationState.ABSENT
    )
    assert "ESU6.CME" in next(
        item.text for item in snapshot.claims if item.claim_id == "instruments.configured"
    )


def test_conversation_renders_only_selected_snapshot_claims_and_audits() -> None:
    provider = FakeProvider(
        SirLokeReplyPlanV1(
            disposition=ReplyDisposition.ANSWER,
            segments=(ReplySegmentV1(claim_id="identity.sl01", framing="FACT"),),
        )
    )
    audit = FakeAudit()
    conversation = SirLokeConversation(_config(), provider, audit, _snapshot)  # type: ignore[arg-type]

    reply = asyncio.run(conversation.handle("What are you?"))

    assert reply.content == "I am the SL-01 capability bot."
    assert reply.paid_dispatch is True
    assert provider.calls == 1
    assert [event["phase"] for event in audit.events] == [
        "REQUEST_ADMITTED",
        "MODEL_COMPLETED",
    ]
    assert "snapshot" in audit.events[0]["content"]  # type: ignore[operator]


def test_current_market_question_rejects_non_abstaining_model_plan() -> None:
    provider = FakeProvider(
        SirLokeReplyPlanV1(
            disposition=ReplyDisposition.ANSWER,
            segments=(ReplySegmentV1(claim_id="identity.sl01", framing="FACT"),),
        )
    )
    audit = FakeAudit()
    conversation = SirLokeConversation(_config(), provider, audit, _snapshot)  # type: ignore[arg-type]

    reply = asyncio.run(conversation.handle("What is the market price now?"))

    assert "could not produce a validated reply" in reply.content
    assert [event["phase"] for event in audit.events] == [
        "REQUEST_ADMITTED",
        "MODEL_FAILED",
    ]


def test_current_market_question_accepts_only_bounded_abstention_claims() -> None:
    provider = FakeProvider(
        SirLokeReplyPlanV1(
            disposition=ReplyDisposition.ABSTAIN,
            segments=(ReplySegmentV1(claim_id="evidence.none_current", framing="LIMITATION"),),
        )
    )
    conversation = SirLokeConversation(  # type: ignore[arg-type]
        _config(), provider, FakeAudit(), _snapshot
    )

    reply = asyncio.run(conversation.handle("What is the market price now?"))

    assert reply.content == "Limit: No current market evidence is available."
    assert "price" not in reply.content.lower()


def test_unrelated_question_requires_explicit_scope_abstention() -> None:
    provider = FakeProvider(
        SirLokeReplyPlanV1(
            disposition=ReplyDisposition.ABSTAIN,
            segments=(ReplySegmentV1(claim_id="scope.unrelated", framing="LIMITATION"),),
        )
    )
    conversation = SirLokeConversation(  # type: ignore[arg-type]
        _config(), provider, FakeAudit(), _snapshot
    )

    reply = asyncio.run(conversation.handle("Tell me a joke."))

    assert reply.content == "Limit: That request is outside scope."


def test_unknown_claim_and_provider_timeout_return_no_model_prose() -> None:
    unknown_provider = FakeProvider(
        SirLokeReplyPlanV1(
            disposition=ReplyDisposition.ANSWER,
            segments=(ReplySegmentV1(claim_id="unknown.claim", framing="FACT"),),
        )
    )
    unknown_conversation = SirLokeConversation(  # type: ignore[arg-type]
        _config(), unknown_provider, FakeAudit(), _snapshot
    )
    timeout_provider = FailingProvider(unknown_provider.plan)
    timeout_conversation = SirLokeConversation(  # type: ignore[arg-type]
        _config(), timeout_provider, FakeAudit(), _snapshot
    )

    unknown_reply = asyncio.run(unknown_conversation.handle("What are you?"))
    timeout_reply = asyncio.run(timeout_conversation.handle("What are you?"))

    assert "validated reply" in unknown_reply.content
    assert "validated reply" in timeout_reply.content
    assert "unknown.claim" not in unknown_reply.content
    assert "provider timeout" not in timeout_reply.content


def test_secret_like_input_is_neither_stored_nor_dispatched() -> None:
    provider = FakeProvider(
        SirLokeReplyPlanV1(
            disposition=ReplyDisposition.ANSWER,
            segments=(ReplySegmentV1(claim_id="identity.sl01", framing="FACT"),),
        )
    )
    audit = FakeAudit()
    conversation = SirLokeConversation(_config(), provider, audit, _snapshot)  # type: ignore[arg-type]

    reply = asyncio.run(conversation.handle("api_key=secret-value"))

    assert reply.paid_dispatch is False
    assert provider.calls == 0
    assert audit.events[0]["content"] is None
    assert audit.events[0]["phase"] == "REQUEST_REJECTED"


def test_input_and_persisted_daily_bounds_stop_before_dispatch() -> None:
    plan = SirLokeReplyPlanV1(
        disposition=ReplyDisposition.ANSWER,
        segments=(ReplySegmentV1(claim_id="identity.sl01", framing="FACT"),),
    )
    input_provider = FakeProvider(plan)
    input_conversation = SirLokeConversation(  # type: ignore[arg-type]
        _config(), input_provider, FakeAudit(), _snapshot
    )
    daily_provider = FakeProvider(plan)
    daily_conversation = SirLokeConversation(  # type: ignore[arg-type]
        _config(),
        daily_provider,
        FakeAudit(),
        _snapshot,
        initial_daily_calls=50,
        initial_daily_cost_usd=0.07,
    )

    input_reply = asyncio.run(input_conversation.handle("x" * 2001))
    daily_reply = asyncio.run(daily_conversation.handle("What are you?"))

    assert input_reply.paid_dispatch is False
    assert daily_reply.paid_dispatch is False
    assert input_provider.calls == daily_provider.calls == 0


def test_execution_question_can_only_render_explicit_absence() -> None:
    snapshot = _snapshot().model_copy(
        update={
            "capabilities": (
                *_snapshot().capabilities,
                CapabilityStatusV1(
                    capability_id="order.execution",
                    configuration_state=ConfigurationState.ABSENT,
                    runtime_state=RuntimeState.NOT_APPLICABLE,
                    evidence_state=EvidenceState.NOT_APPLICABLE,
                    detail="test",
                ),
            ),
            "claims": (
                *_snapshot().claims,
                SnapshotClaimV1(
                    claim_id="execution.never",
                    capability_id="order.execution",
                    text="I cannot execute orders.",
                ),
            ),
        }
    )
    provider = FakeProvider(
        SirLokeReplyPlanV1(
            disposition=ReplyDisposition.ABSTAIN,
            segments=(ReplySegmentV1(claim_id="execution.never", framing="LIMITATION"),),
        )
    )
    conversation = SirLokeConversation(  # type: ignore[arg-type]
        _config(), provider, FakeAudit(), lambda: snapshot
    )

    reply = asyncio.run(conversation.handle("Execute an order for me."))

    assert reply.content == "Limit: I cannot execute orders."


def test_audit_failure_closes_before_paid_model_dispatch() -> None:
    provider = FakeProvider(
        SirLokeReplyPlanV1(
            disposition=ReplyDisposition.ANSWER,
            segments=(ReplySegmentV1(claim_id="identity.sl01", framing="FACT"),),
        )
    )
    conversation = SirLokeConversation(  # type: ignore[arg-type]
        _config(), provider, FakeAudit(fail=True), _snapshot
    )

    reply = asyncio.run(conversation.handle("What are you?"))

    assert "audit record could not be stored" in reply.content
    assert reply.paid_dispatch is False
    assert provider.calls == 0


def test_audit_record_rejects_inverted_retention() -> None:
    with pytest.raises(ValueError, match="metadata expiry"):
        SirLokeAuditEventRecord(
            audit_event_id=uuid4(),
            run_id=uuid4(),
            conversation_id=uuid4(),
            turn_id=uuid4(),
            invocation_id=None,
            phase="REQUEST_ADMITTED",
            content={},
            metadata={},
            occurred_at_ns=1,
            content_expires_at_ns=3,
            metadata_expires_at_ns=2,
        )


def test_openai_boundary_disables_storage_retries_and_tools() -> None:
    config = _config()
    provider = object.__new__(OpenAIResponsesProvider)
    provider._config = config.model  # type: ignore[attr-defined]
    provider._observed_ready = False  # type: ignore[attr-defined]
    client = FakeOpenAIClient()
    provider._client = client  # type: ignore[attr-defined]

    result = asyncio.run(
        provider.plan_reply(
            question="What are you?",
            snapshot=_snapshot(),
            prior_exchange=None,
        )
    )

    assert result.plan.segments[0].claim_id == "identity.sl01"
    assert provider.observed_ready is True
    assert client.responses.arguments["model"] == "gpt-5.6-luna"
    assert client.responses.arguments["reasoning"] == {"effort": "low"}
    assert client.responses.arguments["tools"] == []
    assert client.responses.arguments["store"] is False
    assert client.responses.arguments["truncation"] == "disabled"
    assert client.responses.arguments["max_output_tokens"] == 512


def test_openai_client_has_exact_timeout_and_no_sdk_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_client(**values: object) -> FakeOpenAIClient:
        captured.update(values)
        return FakeOpenAIClient()

    monkeypatch.setattr(model_provider, "AsyncOpenAI", fake_client)

    OpenAIResponsesProvider(_config().model, "test-key")

    assert captured["api_key"] == "test-key"
    assert captured["timeout"] == 20.0
    assert captured["max_retries"] == 0


def test_discord_transport_has_no_privileged_message_content_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()
    conversation = object()
    client = SirLokeDiscordClient(config.discord, conversation)  # type: ignore[arg-type]
    client._identity_verified = True  # type: ignore[attr-defined]

    class FakeDm:
        id = config.discord.dm_channel_id

    monkeypatch.setattr(discord_transport.discord, "DMChannel", FakeDm)
    message = type(
        "Message",
        (),
        {
            "guild": None,
            "channel": FakeDm(),
            "author": type(
                "Author",
                (),
                {"id": config.discord.user_id, "bot": False},
            )(),
            "webhook_id": None,
        },
    )()

    assert client.intents.dm_messages is True
    assert client.intents.message_content is False
    assert client._admitted_identity(message) is True  # type: ignore[arg-type]
    assert client._admit_message_id(10) is True
    assert client._admit_message_id(10) is False
    message.author.id += 1
    assert client._admitted_identity(message) is False  # type: ignore[arg-type]
