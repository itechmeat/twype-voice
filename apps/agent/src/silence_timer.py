from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger("twype-agent")


class SilenceTimer:
    __slots__ = (
        "_fired",
        "_long_timeout",
        "_on_long_timeout",
        "_on_short_timeout",
        "_short_timeout",
        "_stopped",
        "_task",
    )

    def __init__(
        self,
        *,
        short_timeout: float,
        long_timeout: float,
        on_short_timeout: Callable[[], Awaitable[None]],
        on_long_timeout: Callable[[], Awaitable[None]],
    ) -> None:
        if short_timeout <= 0:
            raise ValueError("short_timeout must be positive")
        if long_timeout <= short_timeout:
            raise ValueError("long_timeout must be greater than short_timeout")

        self._short_timeout = short_timeout
        self._long_timeout = long_timeout
        self._on_short_timeout = on_short_timeout
        self._on_long_timeout = on_long_timeout
        self._task: asyncio.Task[None] | None = None
        self._fired = False
        self._stopped = False

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def has_fired(self) -> bool:
        return self._fired

    def start(self) -> None:
        self._stopped = False
        self._fired = False
        self._cancel_task()
        self._task = asyncio.create_task(self._run())

    def reset(self) -> None:
        if self._stopped:
            return
        self._fired = False
        self._cancel_task()
        self._task = asyncio.create_task(self._run())

    def stop(self) -> None:
        self._stopped = True
        self._cancel_task()

    def _cancel_task(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self._task = None

    async def _run(self) -> None:
        try:
            await asyncio.sleep(self._short_timeout)

            if not self._fired:
                self._fired = True
                try:
                    await self._on_short_timeout()
                except Exception:
                    logger.exception("silence timer short callback failed")

            remaining = self._long_timeout - self._short_timeout
            await asyncio.sleep(remaining)

            try:
                await self._on_long_timeout()
            except Exception:
                logger.exception("silence timer long callback failed")

        except asyncio.CancelledError:
            pass
