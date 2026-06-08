"""Knowledge domain files and ingestion into long-term memory."""

from kmac_agent_friend.knowledge.ingest import (
    KnowledgeIngestor,
    chunk_text,
    knowledge_root,
)

__all__ = ["KnowledgeIngestor", "chunk_text", "knowledge_root"]
