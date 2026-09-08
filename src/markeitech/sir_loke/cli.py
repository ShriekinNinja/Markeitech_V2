"""Connected owner for the private Sir Loke SL-01 Discord runtime."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
from collections.abc import Sequence
from pathlib import Path
from time import time
from uuid import uuid4

from markeitech.sir_loke.audit import SirLokeAuditWriter
from markeitech.sir_loke.config import (
    DISCORD_TOKEN_ENV,
    OPENAI_API_KEY_ENV,
    POSTGRES_DSN_ENV,
    load_sir_loke_config,
)
from markeitech.sir_loke.conversation import SirLokeConversation
from markeitech.sir_loke.discord_transport import SirLokeDiscordClient
from markeitech.sir_loke.model_provider import OpenAIResponsesProvider
from markeitech.sir_loke.read_model import LocalDependencyState, build_readiness_snapshot
from markeitech.system.config import load_system_config
from markeitech.system.persistence import OperationalStore


async def _prune_audit_forever(audit: SirLokeAuditWriter, interval_seconds: int) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        await audit.prune()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m markeitech.sir_loke.cli",
        description="Run the exact-identity Sir Loke SL-01 Discord bot.",
    )
    parser.add_argument("config", type=Path)
    return parser


def _required_secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"required environment variable is missing: {name}")
    return value


def _configure_logging(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)sZ %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=[logging.FileHandler(path, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )
    logging.Formatter.converter = __import__("time").gmtime


async def _run(config_path: Path) -> int:
    config = load_sir_loke_config(config_path)
    system_config = load_system_config(config.system_config_path)
    _configure_logging(config.log_path)
    discord_token = _required_secret(DISCORD_TOKEN_ENV)
    openai_key = _required_secret(OPENAI_API_KEY_ENV)

    store = OperationalStore.from_environment(
        POSTGRES_DSN_ENV,
        config.audit.connect_timeout_seconds,
    )
    await asyncio.to_thread(store.initialize)
    await asyncio.to_thread(store.check)
    run_id = await asyncio.to_thread(store.start_run, "SIR-LOKE-SL01")
    provider: OpenAIResponsesProvider | None = None
    client: SirLokeDiscordClient | None = None
    client_task: asyncio.Task[None] | None = None
    stop_task: asyncio.Task[bool] | None = None
    prune_task: asyncio.Task[None] | None = None
    terminal_state = "FAILED"
    terminal_reason = "SL-01 startup did not complete"
    try:
        audit = SirLokeAuditWriter(store, run_id, uuid4(), config.audit)
        await audit.prune()
        utc_day_start_ns = int(time() // 86_400) * 86_400_000_000_000
        daily_calls, daily_cost_usd = await asyncio.to_thread(
            store.load_sir_loke_budget_usage,
            utc_day_start_ns,
        )
        provider = OpenAIResponsesProvider(config.model, openai_key)
        client_ref: list[SirLokeDiscordClient] = []

        def snapshot_factory():  # noqa: ANN202
            discord_ready = bool(client_ref and client_ref[0].identity_verified)
            return build_readiness_snapshot(
                config,
                system_config,
                LocalDependencyState(
                    discord_ready=discord_ready,
                    model_ready=provider.observed_ready,
                    audit_ready=True,
                ),
            )

        conversation = SirLokeConversation(
            config,
            provider,
            audit,
            snapshot_factory,
            initial_daily_calls=daily_calls,
            initial_daily_cost_usd=daily_cost_usd,
        )
        client = SirLokeDiscordClient(config.discord, conversation)
        client_ref.append(client)
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for handled_signal in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            loop.add_signal_handler(handled_signal, stop_event.set)

        client_task = asyncio.create_task(client.start(discord_token, reconnect=True))
        stop_task = asyncio.create_task(stop_event.wait())
        prune_task = asyncio.create_task(
            _prune_audit_forever(audit, config.audit.prune_interval_seconds)
        )
        completed, _ = await asyncio.wait(
            {client_task, stop_task, prune_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if client_task in completed:
            exception = client_task.exception()
            terminal_reason = client.failure_reason or (
                f"Discord runtime failed: {type(exception).__name__}"
                if exception is not None
                else "Discord runtime ended unexpectedly"
            )
            logging.getLogger(__name__).error(terminal_reason)
            return 1
        if prune_task in completed:
            exception = prune_task.exception()
            terminal_reason = (
                f"SL-01 audit maintenance failed: {type(exception).__name__}"
                if exception is not None
                else "SL-01 audit maintenance ended unexpectedly"
            )
            logging.getLogger(__name__).error(terminal_reason)
            return 1
        terminal_state = "STOPPED"
        terminal_reason = "operator requested shutdown"
        return 0
    except Exception as exc:
        terminal_reason = f"SL-01 runtime failed: {type(exc).__name__}"
        logging.getLogger(__name__).error(terminal_reason)
        return 1
    finally:
        if stop_task is not None:
            stop_task.cancel()
        if prune_task is not None:
            prune_task.cancel()
        if client is not None:
            await client.close()
        if client_task is not None:
            if not client_task.done():
                client_task.cancel()
        tasks = tuple(task for task in (client_task, stop_task, prune_task) if task is not None)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if provider is not None:
            await provider.close()
        await asyncio.to_thread(store.close_run, run_id, terminal_state, terminal_reason)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return asyncio.run(_run(args.config))
    except Exception as exc:
        print(f"ERROR: Sir Loke SL-01 startup failed: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
