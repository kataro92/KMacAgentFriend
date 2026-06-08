"""Periodic background task runner."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

TickHandler = Callable[[], Awaitable[None]]


@dataclass
class BackgroundWorker:
    interval_seconds: float = 120.0
    task_name: str = ""
    running: bool = False
    last_tick: float = 0.0
    tick_count: int = 0
    _handle: asyncio.Task[None] | None = field(default=None, repr=False)
    _on_tick: TickHandler | None = field(default=None, repr=False)

    def status(self) -> dict[str, object]:
        return {
            "running": self.running,
            "task": self.task_name,
            "tick_count": self.tick_count,
            "last_tick": self.last_tick,
            "interval_seconds": self.interval_seconds,
        }

    def set_tick_handler(self, handler: TickHandler) -> None:
        self._on_tick = handler

    async def start(self, task_name: str = "background", *, interval: float | None = None) -> None:
        if self.running:
            return
        if interval is not None:
            self.interval_seconds = interval
        self.task_name = task_name
        self.running = True
        self._handle = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self.running = False
        if self._handle:
            self._handle.cancel()
            try:
                await self._handle
            except asyncio.CancelledError:
                pass
            self._handle = None
        self.task_name = ""

    async def _loop(self) -> None:
        while self.running:
            self.last_tick = time.time()
            self.tick_count += 1
            logger.info("Background tick %d (%s)", self.tick_count, self.task_name)
            if self._on_tick:
                try:
                    await self._on_tick()
                except Exception:
                    logger.exception("Background tick handler failed")
            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break


background_worker = BackgroundWorker()


def register_default_handlers(worker: BackgroundWorker, moltbook) -> None:
    async def on_tick() -> None:
        result = await moltbook.check_feed()
        posts = result.get("posts", 0)
        worker.task_name = f"forum-check ({posts} posts)"

    worker.set_tick_handler(on_tick)
