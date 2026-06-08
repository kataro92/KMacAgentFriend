"""Reincarnation: export/import the agent's "soul".

A reincarnation bundle captures everything that makes one install unique —
user settings overrides, conversation history, long-term memories (with their
embeddings), and knowledge memories — so it can be restored into a fresh
install. Embeddings are included so imports never need to re-run Ollama.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from kmac_agent_friend.config import Settings
from kmac_agent_friend.knowledge.ingest import KNOWLEDGE_COLLECTION
from kmac_agent_friend.memory.history import ConversationStore
from kmac_agent_friend.memory.vector_store import LongTermMemory
from kmac_agent_friend.settings_store import load_user_overrides, save_user_overrides

BUNDLE_VERSION = 1


@dataclass
class ImportReport:
    ok: bool
    conversations: int = 0
    messages: int = 0
    memories: int = 0
    knowledge: int = 0
    settings_applied: bool = False
    errors: list[str] = field(default_factory=list)


def _longterm_store(settings: Settings, collection: str) -> LongTermMemory:
    return LongTermMemory(
        settings.kaf_data_dir / "memory" / "longterm.db",
        collection=collection,
    )


def export_bundle(settings: Settings) -> dict:
    conversations = ConversationStore.from_settings(settings).export_conversations()
    memories = _longterm_store(settings, "memories").export_records()
    knowledge = _longterm_store(settings, KNOWLEDGE_COLLECTION).export_records()
    return {
        "version": BUNDLE_VERSION,
        "exported_at": time.time(),
        "settings": load_user_overrides(settings.kaf_data_dir),
        "conversations": conversations,
        "memories": memories,
        "knowledge": knowledge,
    }


def import_bundle(
    settings: Settings,
    bundle: dict,
    *,
    apply_settings: bool = True,
) -> ImportReport:
    report = ImportReport(ok=True)
    if not isinstance(bundle, dict):
        return ImportReport(ok=False, errors=["Bundle must be a JSON object"])

    version = bundle.get("version")
    if version != BUNDLE_VERSION:
        report.errors.append(f"Unsupported bundle version: {version}")

    conversations = bundle.get("conversations") or []
    if isinstance(conversations, list):
        store = ConversationStore.from_settings(settings)
        report.messages = store.import_conversations(conversations)
        report.conversations = len(conversations)

    memories = bundle.get("memories") or []
    if isinstance(memories, list):
        report.memories = _longterm_store(settings, "memories").import_records(memories)

    knowledge = bundle.get("knowledge") or []
    if isinstance(knowledge, list):
        report.knowledge = _longterm_store(settings, KNOWLEDGE_COLLECTION).import_records(
            knowledge
        )

    if apply_settings and isinstance(bundle.get("settings"), dict) and bundle["settings"]:
        save_user_overrides(settings.kaf_data_dir, bundle["settings"])
        report.settings_applied = True

    return report
