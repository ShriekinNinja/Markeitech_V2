"""Synthetic review input: shutdown should await completion of its one owned worker."""

import asyncio


class Worker:
    def __init__(self) -> None:
        self.task: asyncio.Task | None = None
        self.cleaned = False

    async def run(self) -> None:
        try:
            while True:
                try:
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    continue
        finally:
            self.cleaned = True

    def start(self) -> None:
        self.task = asyncio.create_task(self.run())

    async def stop(self) -> None:
        if self.task:
            self.task.cancel()
            while not self.cleaned:
                await asyncio.sleep(0)
