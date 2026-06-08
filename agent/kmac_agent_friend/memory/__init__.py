"""Persistent memory (Phase 3+)."""

from kmac_agent_friend.memory.embeddings import EmbedResult, cosine_similarity, embed_text
from kmac_agent_friend.memory.history import ConversationStore
from kmac_agent_friend.memory.service import MemoryService, RecallResult, RememberResult
from kmac_agent_friend.memory.vector_store import (
    LongTermMemory,
    MemoryRecord,
    chromadb_available,
)

__all__ = [
    "ConversationStore",
    "EmbedResult",
    "LongTermMemory",
    "MemoryRecord",
    "MemoryService",
    "RecallResult",
    "RememberResult",
    "chromadb_available",
    "cosine_similarity",
    "embed_text",
]
