"""In-memory activity ring buffer for the debug panel."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any

MAX_ENTRIES = 500


@dataclass
class ActivityEntry:
    ts: float
    level: str
    category: str
    message: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ActivityLog:
    def __init__(self, max_entries: int = MAX_ENTRIES) -> None:
        self._entries: deque[ActivityEntry] = deque(maxlen=max_entries)

    def append(
        self,
        level: str,
        category: str,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> ActivityEntry:
        entry = ActivityEntry(
            ts=time.time(),
            level=level,
            category=category,
            message=message,
            detail=detail or {},
        )
        self._entries.append(entry)
        return entry

    def recent(self, limit: int = 200) -> list[dict[str, Any]]:
        items = list(self._entries)
        if limit < len(items):
            items = items[-limit:]
        return [entry.to_dict() for entry in items]

    def clear(self) -> None:
        self._entries.clear()


activity_log = ActivityLog()
