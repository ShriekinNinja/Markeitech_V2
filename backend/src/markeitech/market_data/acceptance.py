from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from pydantic import Field, field_validator

from markeitech.analytics import MarketContextSnapshot
from markeitech.domain.base import VersionedDomainModel
from markeitech.domain.state import SourceStatus
from markeitech.market_data.actor import MarkeitechMarketDataActor
from markeitech.market_data.bootstrap import (
    LIVE_NODE_START_CONFIRMATION,
    ConfigurableLiveNodeLike,
    build_prepared_market_data_live_node,
    validate_live_node_start,
)
from markeitech.market_data.coordinator import WarmupState
from markeitech.market_data.health import MarketDataHealthSnapshot
from markeitech.market_data.loader import load_market_data_runtime_config
from markeitech.market_data.routing import InstrumentMarketDataSnapshot
from markeitech.persistence.startup_recovery import (
    StartupRecoverySnapshot,
    StartupRecoveryStatus,
)


class AcceptanceStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    REFUSED = "refused"
    ERROR = "error"


class AcceptanceCheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class AcceptanceCheck(VersionedDomainModel):
    name: str = Field(min_length=1)
    status: AcceptanceCheckStatus
    detail: str = Field(min_length=1)


class AcceptanceInstrumentResult(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    is_active: bool
    trade_ticks: int = Field(ge=0)
    quote_ticks: int = Field(ge=0)
    bars: int = Field(ge=0)
    dropped_events: int = Field(ge=0)


class AcceptanceRecoveryResult(VersionedDomainModel):
    instrument_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    missing_before: int = Field(ge=0)
    missing_after: int = Field(ge=0)
    request_count: int = Field(ge=0)
    confirmed_provider_empty_count: int = Field(ge=0)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)


class PaperIbAcceptanceReport(VersionedDomainModel):
    status: AcceptanceStatus
    started_ts: datetime
    ended_ts: datetime
    requested_duration_seconds: int = Field(ge=1)
    active_instrument_id: str = Field(min_length=1)
    instruments: tuple[AcceptanceInstrumentResult, ...] = Field(default_factory=tuple)
    checks: tuple[AcceptanceCheck, ...] = Field(default_factory=tuple)
    source_status: SourceStatus | None = None
    recovery_status: StartupRecoveryStatus | None = None
    recoveries: tuple[AcceptanceRecoveryResult, ...] = Field(default_factory=tuple)
    market_contexts: tuple[MarketContextSnapshot, ...] = Field(default_factory=tuple)
    error: str | None = None

    @field_validator("started_ts", "ended_ts")
    @classmethod
    def _timestamps_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("acceptance timestamps must be UTC")
        return value.astimezone(UTC)


class AcceptanceNode(Protocol):
    async def run_async(self) -> None: ...

    async def stop_async(self) -> None: ...


class AcceptanceActor(Protocol):
    @property
    def warmup_state(self) -> WarmupState: ...

    @property
    def market_data_snapshots(self) -> tuple[InstrumentMarketDataSnapshot, ...]: ...

    @property
    def market_data_health(self) -> MarketDataHealthSnapshot: ...

    @property
    def startup_recovery_snapshot(self) -> StartupRecoverySnapshot | None: ...

    @property
    def market_context_snapshots(self) -> tuple[MarketContextSnapshot, ...]: ...


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Duration-limited paper Interactive Brokers acceptance test.",
    )
    parser.add_argument("config", type=Path, help="Path to a local market-data TOML config.")
    parser.add_argument("--duration", type=int, default=90, help="Run duration in seconds.")
    parser.add_argument(
        "--confirm",
        default=None,
        help=f"Required token to connect: {LIVE_NODE_START_CONFIRMATION}",
    )
    args = parser.parse_args()
    if args.duration < 10 or args.duration > 600:
        parser.error("--duration must be between 10 and 600 seconds")

    report = asyncio.run(
        run_paper_ib_acceptance(
            args.config,
            duration_seconds=args.duration,
            confirmation=args.confirm,
        )
    )
    print(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))
    if report.status != AcceptanceStatus.PASSED:
        raise SystemExit(1)


async def run_paper_ib_acceptance(
    config_path: Path,
    *,
    duration_seconds: int,
    confirmation: str | None,
) -> PaperIbAcceptanceReport:
    return await run_paper_ib_acceptance_with_factories(
        config_path,
        duration_seconds=duration_seconds,
        confirmation=confirmation,
    )


async def run_paper_ib_acceptance_with_factories(
    config_path: Path,
    *,
    duration_seconds: int,
    confirmation: str | None,
    node_factory: Callable[..., ConfigurableLiveNodeLike] | None = None,
    actor_factory: Callable[..., AcceptanceActor] = MarkeitechMarketDataActor,
) -> PaperIbAcceptanceReport:
    if duration_seconds < 1:
        raise ValueError("acceptance duration must be positive")
    config = load_market_data_runtime_config(config_path)
    started_ts = datetime.now(UTC)

    try:
        validate_live_node_start(config, confirmation=confirmation)
    except RuntimeError as exc:
        return _refused_report(config, started_ts, duration_seconds, str(exc))

    actors: list[AcceptanceActor] = []

    def capture_actor(action_plan: Any, **kwargs: Any) -> AcceptanceActor:
        actor = actor_factory(action_plan, **kwargs)
        actors.append(actor)
        return actor

    build_kwargs: dict[str, Any] = {"actor_factory": capture_actor}
    if node_factory is not None:
        build_kwargs["node_factory"] = node_factory
    try:
        node = build_prepared_market_data_live_node(config, **build_kwargs)
        actor = actors[0]
    except Exception as exc:
        return _error_report(
            config,
            started_ts,
            duration_seconds,
            f"build failed: {type(exc).__name__}: {exc}",
        )
    runtime_error: str | None = None
    stopped_early = False
    run_task = asyncio.create_task(_run_node(node))

    try:
        await asyncio.wait_for(asyncio.shield(run_task), timeout=duration_seconds)
        stopped_early = True
    except TimeoutError:
        pass
    except Exception as exc:
        runtime_error = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            await node.stop_async()
        except Exception as exc:
            runtime_error = runtime_error or f"stop failed: {type(exc).__name__}: {exc}"
        if not run_task.done():
            try:
                await asyncio.wait_for(run_task, timeout=10)
            except Exception as exc:
                runtime_error = runtime_error or f"shutdown failed: {type(exc).__name__}: {exc}"

    return _build_report(
        config=config,
        actor=actor,
        started_ts=started_ts,
        duration_seconds=duration_seconds,
        runtime_error=runtime_error,
        stopped_early=stopped_early,
    )


async def _run_node(node: AcceptanceNode) -> None:
    await node.run_async()


def _build_report(
    *,
    config: Any,
    actor: AcceptanceActor,
    started_ts: datetime,
    duration_seconds: int,
    runtime_error: str | None,
    stopped_early: bool,
) -> PaperIbAcceptanceReport:
    snapshots = actor.market_data_snapshots
    market_contexts = actor.market_context_snapshots
    health = actor.market_data_health
    recovery = getattr(actor, "startup_recovery_snapshot", None)
    checks = [
        _check("read_only_ib", config.ib.read_only, "IB connection is read-only"),
        _check("execution_disabled", config.data_only, "runtime is data-only"),
        _check(
            "warmup_complete",
            actor.warmup_state == WarmupState.LIVE,
            f"warmup state is {actor.warmup_state}",
        ),
        _check(
            "runtime_duration",
            not stopped_early,
            "LiveNode remained running for the requested duration",
        ),
    ]
    for snapshot in snapshots:
        if snapshot.is_active:
            checks.extend(
                (
                    _check(
                        f"{snapshot.instrument_id}:trade_ticks",
                        snapshot.trade_tick_count > 0,
                        f"observed {snapshot.trade_tick_count} trade ticks",
                    ),
                    _check(
                        f"{snapshot.instrument_id}:quote_ticks",
                        snapshot.quote_tick_count > 0,
                        f"observed {snapshot.quote_tick_count} quote ticks",
                    ),
                )
            )
        checks.append(
            _check(
                f"{snapshot.instrument_id}:bars",
                snapshot.bar_count > 0,
                f"observed {snapshot.bar_count} completed external bars",
            )
        )
        instrument_contexts = tuple(
            context
            for context in market_contexts
            if context.instrument_id == snapshot.instrument_id
        )
        checks.append(
            _check(
                f"{snapshot.instrument_id}:market_context",
                bool(instrument_contexts),
                f"observed {len(instrument_contexts)} market context snapshots",
            )
        )
    checks.append(
        _check(
            "source_health",
            health.source.status == SourceStatus.HEALTHY,
            f"IB source status is {health.source.status}",
        )
    )
    if config.persistence is not None:
        recovery_terminal = recovery is not None and recovery.status in {
            StartupRecoveryStatus.COMPLETE,
            StartupRecoveryStatus.DEGRADED,
        }
        checks.append(
            _check(
                "startup_recovery_terminal",
                recovery_terminal,
                (
                    "startup recovery snapshot is unavailable"
                    if recovery is None
                    else f"startup recovery status is {recovery.status}"
                ),
            )
        )
    if runtime_error is not None:
        checks.append(_check("runtime_error", False, runtime_error))

    passed = all(check.status == AcceptanceCheckStatus.PASS for check in checks)
    return PaperIbAcceptanceReport(
        status=AcceptanceStatus.PASSED if passed else AcceptanceStatus.FAILED,
        started_ts=started_ts,
        ended_ts=datetime.now(UTC),
        requested_duration_seconds=duration_seconds,
        active_instrument_id=config.instrument_registry.active_instrument_id,
        instruments=tuple(
            AcceptanceInstrumentResult(
                instrument_id=snapshot.instrument_id,
                is_active=snapshot.is_active,
                trade_ticks=snapshot.trade_tick_count,
                quote_ticks=snapshot.quote_tick_count,
                bars=snapshot.bar_count,
                dropped_events=snapshot.dropped_event_count,
            )
            for snapshot in snapshots
        ),
        checks=tuple(checks),
        source_status=health.source.status,
        recovery_status=None if recovery is None else recovery.status,
        recoveries=(
            ()
            if recovery is None
            else tuple(
                AcceptanceRecoveryResult(
                    instrument_id=item.instrument_id,
                    status=item.status.value,
                    missing_before=item.missing_before,
                    missing_after=item.missing_after,
                    request_count=item.request_count,
                    confirmed_provider_empty_count=item.confirmed_provider_empty_count,
                    reason_codes=item.reason_codes,
                )
                for item in recovery.instruments
            )
        ),
        market_contexts=market_contexts,
        error=runtime_error,
    )


def _refused_report(
    config: Any,
    started_ts: datetime,
    duration_seconds: int,
    error: str,
) -> PaperIbAcceptanceReport:
    return PaperIbAcceptanceReport(
        status=AcceptanceStatus.REFUSED,
        started_ts=started_ts,
        ended_ts=datetime.now(UTC),
        requested_duration_seconds=duration_seconds,
        active_instrument_id=config.instrument_registry.active_instrument_id,
        checks=(AcceptanceCheck(name="startup_guard", status="fail", detail=error),),
        error=error,
    )


def _error_report(
    config: Any,
    started_ts: datetime,
    duration_seconds: int,
    error: str,
) -> PaperIbAcceptanceReport:
    return PaperIbAcceptanceReport(
        status=AcceptanceStatus.ERROR,
        started_ts=started_ts,
        ended_ts=datetime.now(UTC),
        requested_duration_seconds=duration_seconds,
        active_instrument_id=config.instrument_registry.active_instrument_id,
        checks=(AcceptanceCheck(name="runtime_build", status="fail", detail=error),),
        error=error,
    )


def _check(name: str, passed: bool, detail: str) -> AcceptanceCheck:
    return AcceptanceCheck(
        name=name,
        status=AcceptanceCheckStatus.PASS if passed else AcceptanceCheckStatus.FAIL,
        detail=detail,
    )
