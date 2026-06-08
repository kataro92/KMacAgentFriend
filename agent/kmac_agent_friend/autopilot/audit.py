"""Persistent decision audit log for autonomous actions."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from kmac_agent_friend.config import Settings


class DecisionAuditLog:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @classmethod
    def from_settings(cls, settings: Settings) -> DecisionAuditLog:
        return cls(settings.kaf_data_dir / "decisions.db")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    action TEXT NOT NULL,
                    allowed INTEGER NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL DEFAULT '',
                    detail TEXT NOT NULL DEFAULT '{}'
                )
                """
            )

    def record(
        self,
        action: str,
        *,
        allowed: bool,
        reason: str = "",
        summary: str = "",
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ts = time.time()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO decisions (ts, action, allowed, reason, summary, detail)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ts, action, 1 if allowed else 0, reason, summary, json.dumps(detail or {})),
            )
            entry_id = cursor.lastrowid
        return {
            "id": entry_id,
            "ts": ts,
            "action": action,
            "allowed": allowed,
            "reason": reason,
            "summary": summary,
            "detail": detail or {},
        }

    def recent(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM decisions ORDER BY ts DESC LIMIT ?", (limit,)
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            try:
                detail = json.loads(row["detail"])
            except (json.JSONDecodeError, TypeError):
                detail = {}
            result.append(
                {
                    "id": row["id"],
                    "ts": row["ts"],
                    "action": row["action"],
                    "allowed": bool(row["allowed"]),
                    "reason": row["reason"],
                    "summary": row["summary"],
                    "detail": detail,
                }
            )
        return result

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM decisions")
