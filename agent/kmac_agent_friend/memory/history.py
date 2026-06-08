"""SQLite conversation history."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from uuid import uuid4

from kmac_agent_friend.config import Settings

DEFAULT_CONVERSATION_ID = "main"


class ConversationStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @classmethod
    def from_settings(cls, settings: Settings) -> ConversationStore:
        return cls(settings.kaf_data_dir / "conversations.db")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conv
                    ON messages(conversation_id, created_at);
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO conversations (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (DEFAULT_CONVERSATION_ID, "Main", time.time(), time.time()),
            )

    def append(
        self,
        role: str,
        content: str,
        *,
        conversation_id: str = DEFAULT_CONVERSATION_ID,
    ) -> None:
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO conversations (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, conversation_id, now, now),
            )
            conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, role, content, now),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )

    def recent(
        self,
        *,
        limit: int = 10,
        conversation_id: str = DEFAULT_CONVERSATION_ID,
    ) -> list[dict[str, str]]:
        return self.get_messages(conversation_id, limit=limit)

    def get_messages(
        self,
        conversation_id: str = DEFAULT_CONVERSATION_ID,
        *,
        limit: int = 10,
    ) -> list[dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (conversation_id, limit),
            ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def list_conversations(self, *, limit: int = 20) -> list[dict[str, str | float]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, title, updated_at FROM conversations
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {"id": row["id"], "title": row["title"], "updated_at": row["updated_at"]}
            for row in rows
        ]

    def export_conversations(self) -> list[dict]:
        with self._connect() as conn:
            convs = conn.execute(
                "SELECT id, title, created_at, updated_at FROM conversations ORDER BY created_at"
            ).fetchall()
            result: list[dict] = []
            for conv in convs:
                msgs = conn.execute(
                    """
                    SELECT role, content, created_at FROM messages
                    WHERE conversation_id = ? ORDER BY created_at
                    """,
                    (conv["id"],),
                ).fetchall()
                result.append(
                    {
                        "id": conv["id"],
                        "title": conv["title"],
                        "created_at": conv["created_at"],
                        "updated_at": conv["updated_at"],
                        "messages": [
                            {
                                "role": m["role"],
                                "content": m["content"],
                                "created_at": m["created_at"],
                            }
                            for m in msgs
                        ],
                    }
                )
        return result

    def import_conversations(self, conversations: list[dict]) -> int:
        imported = 0
        with self._connect() as conn:
            for conv in conversations:
                conv_id = str(conv.get("id") or uuid4().hex)
                now = time.time()
                conn.execute(
                    """
                    INSERT OR IGNORE INTO conversations (id, title, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        conv_id,
                        str(conv.get("title", conv_id)),
                        float(conv.get("created_at", now)),
                        float(conv.get("updated_at", now)),
                    ),
                )
                for msg in conv.get("messages", []):
                    conn.execute(
                        """
                        INSERT INTO messages (conversation_id, role, content, created_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            conv_id,
                            str(msg.get("role", "user")),
                            str(msg.get("content", "")),
                            float(msg.get("created_at", time.time())),
                        ),
                    )
                    imported += 1
        return imported

    def new_conversation(self, title: str = "") -> str:
        conv_id = uuid4().hex
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (conv_id, title or f"Chat {conv_id[:8]}", now, now),
            )
        return conv_id
