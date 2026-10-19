from __future__ import annotations

import asyncio
import random


class RateLimiter:
    def __init__(self, requests_per_second: float) -> None:
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        self.min_interval = 1.0 / requests_per_second
        self._lock = asyncio.Lock()
        self._next_allowed = 0.0

    async def wait(self) -> None:
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            delay = max(0.0, self._next_allowed - now)
            if delay:
                await asyncio.sleep(delay)
                now = loop.time()
            jitter = random.uniform(0, self.min_interval * 0.2)
            self._next_allowed = max(now, self._next_allowed) + self.min_interval + jitter
