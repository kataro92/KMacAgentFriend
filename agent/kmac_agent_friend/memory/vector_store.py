"""Long-term semantic memory.

Uses ChromaDB when installed; otherwise falls back to a self-contained SQLite
store with brute-force cosine search. The store is embedding-agnostic: callers
supply vectors (see :mod:`kmac_agent_friend.memory.embeddings`), which keeps it
testable without Ollama running.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from kmac_agent_friend.memory.embeddings import cosine_similarity


@dataclass
class MemoryRecord:
    id: str
    text: str
    score: float
    metadata: dict[str, str]


def chromadb_available() -> bool:
    return importlib.util.find_spec("chromadb") is not None


class LongTermMemory:
    """Persistent vector memory with a pluggable backend."""

    def __init__(self, db_path: Path, *, collection: str = "memories") -> None:
        self.db_path = db_path
        self.collection = collection
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @classmethod
    def from_settings(cls, settings) -> LongTermMemory:
        return cls(settings.kaf_data_dir / "memory" / "longterm.db")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    collection TEXT NOT NULL DEFAULT 'memories',
                    text TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_collection ON memories(collection)"
            )

    def add(
        self,
        text: str,
        embedding: list[float],
        *,
        metadata: dict[str, str] | None = None,
        record_id: str | None = None,
    ) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            raise ValueError("Cannot store empty memory text")
        if not embedding:
            raise ValueError("Cannot store memory without an embedding")
        record_id = record_id or uuid4().hex
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memories
                    (id, collection, text, embedding, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    self.collection,
                    cleaned,
                    json.dumps(embedding),
                    json.dumps(metadata or {}),
                    time.time(),
                ),
            )
        return record_id

    def search(
        self,
        query_embedding: list[float],
        *,
        k: int = 5,
        min_score: float = 0.0,
    ) -> list[MemoryRecord]:
        if not query_embedding:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, text, embedding, metadata FROM memories WHERE collection = ?",
                (self.collection,),
            ).fetchall()

        scored: list[MemoryRecord] = []
        for row in rows:
            try:
                vector = json.loads(row["embedding"])
            except (json.JSONDecodeError, TypeError):
                continue
            score = cosine_similarity(query_embedding, vector)
            if score < min_score:
                continue
            try:
                metadata = json.loads(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                metadata = {}
            scored.append(
                MemoryRecord(id=row["id"], text=row["text"], score=score, metadata=metadata)
            )
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[: max(0, k)]

    def export_records(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, text, embedding, metadata, created_at
                FROM memories WHERE collection = ?
                """,
                (self.collection,),
            ).fetchall()
        records: list[dict] = []
        for row in rows:
            try:
                embedding = json.loads(row["embedding"])
                metadata = json.loads(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                continue
            records.append(
                {
                    "id": row["id"],
                    "text": row["text"],
                    "embedding": embedding,
                    "metadata": metadata,
                    "created_at": row["created_at"],
                }
            )
        return records

    def import_records(self, records: list[dict]) -> int:
        imported = 0
        with self._connect() as conn:
            for rec in records:
                text = str(rec.get("text", "")).strip()
                embedding = rec.get("embedding")
                if not text or not isinstance(embedding, list) or not embedding:
                    continue
                conn.execute(
                    """
                    INSERT OR REPLACE INTO memories
                        (id, collection, text, embedding, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(rec.get("id") or uuid4().hex),
                        self.collection,
                        text,
                        json.dumps(embedding),
                        json.dumps(rec.get("metadata") or {}),
                        float(rec.get("created_at", time.time())),
                    ),
                )
                imported += 1
        return imported

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM memories WHERE collection = ?",
                (self.collection,),
            ).fetchone()
        return int(row["n"]) if row else 0

    def clear(self) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM memories WHERE collection = ?", (self.collection,)
            )
            return cursor.rowcount
