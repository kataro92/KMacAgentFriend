"""Sliding-window rate limiter for tool execution."""

from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    """Per-key sliding-window limiter. ``limit <= 0`` disables limiting."""

    def __init__(self, *, window_seconds: float = 60.0) -> None:
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, *, now: float | None = None) -> bool:
        if limit <= 0:
            return True
        now = now if now is not None else time.monotonic()
        bucket = self._events[key]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True

    def remaining(self, key: str, limit: int, *, now: float | None = None) -> int:
        if limit <= 0:
            return -1
        now = now if now is not None else time.monotonic()
        bucket = self._events[key]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        return max(0, limit - len(bucket))

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._events.clear()
        else:
            self._events.pop(key, None)


tool_rate_limiter = RateLimiter()
