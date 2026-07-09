from datetime import UTC, datetime, timedelta

import pytest
from markeitech.domain import (
    GapSeverity,
    GapState,
    GatewayEvent,
    GatewayEventType,
    ReadinessState,
    ReadinessStatus,
    SourceHealth,
    SourceStatus,
    StrategyState,
    StrategyStateEvent,
)
from pydantic import ValidationError


def utc_now() -> datetime:
    return datetime(2026, 7, 9, 12, 0, tzinfo=UTC)


def test_ready_state_has_no_reason_codes() -> None:
    state = ReadinessState(
        instrument_id="NQU6.CME",
        status=ReadinessStatus.READY,
        required_sessions=5,
        complete_sessions=5,
        updated_ts=utc_now(),
    )

    assert state.status == ReadinessStatus.READY


def test_degraded_readiness_requires_reasons() -> None:
    with pytest.raises(ValidationError, match="requires reason codes"):
        ReadinessState(
            instrument_id="NQU6.CME",
            status=ReadinessStatus.DEGRADED,
            required_sessions=5,
            complete_sessions=3,
            updated_ts=utc_now(),
        )


def test_gap_state_requires_reasons_when_active() -> None:
    with pytest.raises(ValidationError, match="requires reason codes"):
        GapState(
            instrument_id="NQU6.CME",
            severity=GapSeverity.DEGRADED,
            open_ts=utc_now(),
            missing_intervals=2,
            updated_ts=utc_now(),
        )


def test_gap_state_rejects_invalid_interval() -> None:
    with pytest.raises(ValidationError, match="after open"):
        GapState(
            instrument_id="NQU6.CME",
            severity=GapSeverity.WARNING,
            open_ts=utc_now(),
            close_ts=utc_now() - timedelta(minutes=1),
            missing_intervals=1,
            reason_codes=("missing_bar",),
            updated_ts=utc_now(),
        )


def test_source_health_requires_reasons_when_failed() -> None:
    with pytest.raises(ValidationError, match="requires reason codes"):
        SourceHealth(
            source="ib",
            status=SourceStatus.FAILED,
            updated_ts=utc_now(),
        )


def test_gateway_event_shape() -> None:
    event = GatewayEvent(
        event_type=GatewayEventType.READINESS_UPDATE,
        instrument_id="NQU6.CME",
        event_ts=utc_now(),
        ts_init=utc_now(),
        payload={"status": "ready"},
    )

    assert event.schema_version == "1.0"
    assert event.event_type == GatewayEventType.READINESS_UPDATE


def test_strategy_state_event_shape() -> None:
    event = StrategyStateEvent(
        strategy_id="strategy-a",
        instrument_id="NQU6.CME",
        deployment_id="paper-local",
        state=StrategyState.WARMING_UP,
        event_ts=utc_now(),
        ts_init=utc_now(),
    )

    assert event.state == StrategyState.WARMING_UP
