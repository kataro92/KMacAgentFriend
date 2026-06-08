"""High-level long-term memory service tying embeddings to the vector store."""

from __future__ import annotations

from dataclasses import dataclass

from kmac_agent_friend.config import Settings
from kmac_agent_friend.memory.embeddings import embed_text
from kmac_agent_friend.memory.vector_store import LongTermMemory, MemoryRecord


@dataclass
class RememberResult:
    ok: bool
    record_id: str = ""
    error: str = ""


@dataclass
class RecallResult:
    ok: bool
    records: list[MemoryRecord] | None = None
    error: str = ""


class MemoryService:
    def __init__(self, settings: Settings, store: LongTermMemory | None = None) -> None:
        self.settings = settings
        self.store = store or LongTermMemory.from_settings(settings)

    async def _embed(self, text: str):
        if self.settings.mock_mode:
            from kmac_agent_friend.mock import mock_embedding

            return mock_embedding(text)
        return await embed_text(
            text,
            ollama_host=self.settings.ollama_host,
            model=self.settings.ollama_embed_model,
        )

    async def remember(
        self,
        text: str,
        *,
        metadata: dict[str, str] | None = None,
    ) -> RememberResult:
        cleaned = (text or "").strip()
        if not cleaned:
            return RememberResult(ok=False, error="Empty memory text")
        embed = await self._embed(cleaned)
        if not embed.ok or embed.embedding is None:
            return RememberResult(ok=False, error=embed.error)
        record_id = self.store.add(cleaned, embed.embedding, metadata=metadata)
        return RememberResult(ok=True, record_id=record_id)

    async def recall(self, query: str, *, k: int = 5) -> RecallResult:
        cleaned = (query or "").strip()
        if not cleaned:
            return RecallResult(ok=False, error="Empty query")
        if self.store.count() == 0:
            return RecallResult(ok=True, records=[])
        embed = await self._embed(cleaned)
        if not embed.ok or embed.embedding is None:
            return RecallResult(ok=False, error=embed.error)
        records = self.store.search(embed.embedding, k=k)
        return RecallResult(ok=True, records=records)
