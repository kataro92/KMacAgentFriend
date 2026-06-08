"""Persistent store for career missions.

A mission is a long-running goal (e.g. "learn the user's codebase",
"draft weekly forum digest") that the background worker advances over time.
Progress notes form an audit trail of what the agent did toward each goal.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from kmac_agent_friend.config import Settings


class MissionStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    DONE = "done"
    ABANDONED = "abandoned"


@dataclass
class Mission:
    id: str
    title: str
    description: str
    status: MissionStatus
    progress: int
    notes: list[str]
    created_at: float
    updated_at: float

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "progress": self.progress,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class MissionStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @classmethod
    def from_settings(cls, settings: Settings) -> MissionStore:
        return cls(settings.kaf_data_dir / "missions.db")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS missions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    progress INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '[]',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )

    def _row_to_mission(self, row: sqlite3.Row) -> Mission:
        try:
            notes = json.loads(row["notes"])
        except (json.JSONDecodeError, TypeError):
            notes = []
        return Mission(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=MissionStatus(row["status"]),
            progress=int(row["progress"]),
            notes=notes,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create(self, title: str, description: str = "") -> Mission:
        cleaned = title.strip()
        if not cleaned:
            raise ValueError("Mission title is required")
        mission_id = uuid4().hex
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO missions
                    (id, title, description, status, progress, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (mission_id, cleaned, description.strip(), MissionStatus.PENDING.value,
                 0, "[]", now, now),
            )
        return self.get(mission_id)  # type: ignore[return-value]

    def get(self, mission_id: str) -> Mission | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM missions WHERE id = ?", (mission_id,)
            ).fetchone()
        return self._row_to_mission(row) if row else None

    def list(self, *, status: MissionStatus | None = None) -> list[Mission]:
        query = "SELECT * FROM missions"
        params: tuple = ()
        if status is not None:
            query += " WHERE status = ?"
            params = (status.value,)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_mission(row) for row in rows]

    def update(
        self,
        mission_id: str,
        *,
        status: MissionStatus | None = None,
        progress: int | None = None,
        note: str | None = None,
    ) -> Mission | None:
        mission = self.get(mission_id)
        if mission is None:
            return None
        if status is not None:
            mission.status = status
        if progress is not None:
            mission.progress = max(0, min(100, progress))
        if note:
            mission.notes.append(f"{time.strftime('%Y-%m-%d %H:%M')} — {note.strip()}")
        mission.updated_at = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE missions
                SET status = ?, progress = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    mission.status.value,
                    mission.progress,
                    json.dumps(mission.notes),
                    mission.updated_at,
                    mission_id,
                ),
            )
        return mission

    def delete(self, mission_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM missions WHERE id = ?", (mission_id,))
            return cursor.rowcount > 0

    def next_active(self) -> Mission | None:
        """Return the highest-priority mission to work on (active, then pending)."""
        for status in (MissionStatus.ACTIVE, MissionStatus.PENDING):
            missions = [m for m in self.list(status=status) if m.progress < 100]
            if missions:
                return sorted(missions, key=lambda m: m.created_at)[0]
        return None
