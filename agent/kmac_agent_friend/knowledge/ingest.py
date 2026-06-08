"""Ingest knowledge domain files into long-term memory.

Knowledge lives as plain ``.md``/``.txt`` files under
``<data_dir>/knowledge/<domain>/``. The ingestor chunks each file, embeds the
chunks, and stores them in a dedicated ``knowledge`` memory collection. An index
of ingested file hashes avoids re-embedding unchanged files.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from kmac_agent_friend.config import Settings
from kmac_agent_friend.memory.embeddings import EmbedResult, embed_text
from kmac_agent_friend.memory.vector_store import LongTermMemory

KNOWLEDGE_COLLECTION = "knowledge"
SUPPORTED_SUFFIXES = (".md", ".txt", ".markdown")

Embedder = Callable[[str], Awaitable[EmbedResult]]


@dataclass
class IngestReport:
    ok: bool
    files_scanned: int = 0
    files_ingested: int = 0
    chunks_added: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def knowledge_root(settings: Settings) -> Path:
    return settings.kaf_data_dir / "knowledge"


def chunk_text(text: str, *, max_chars: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks on paragraph/line boundaries."""
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(para) > max_chars:
            # Hard-split very long paragraphs.
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(para), max_chars - overlap):
                chunks.append(para[i : i + max_chars])
            continue
        if current and len(current) + len(para) + 2 > max_chars:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = (tail + "\n\n" + para).strip()
        else:
            current = (current + "\n\n" + para).strip() if current else para
    if current:
        chunks.append(current)
    return chunks


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class KnowledgeIngestor:
    def __init__(
        self,
        settings: Settings,
        *,
        store: LongTermMemory | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        self.settings = settings
        self.root = knowledge_root(settings)
        self.store = store or LongTermMemory(
            settings.kaf_data_dir / "memory" / "longterm.db",
            collection=KNOWLEDGE_COLLECTION,
        )
        self.embedder = embedder or self._default_embedder
        self.index_path = self.root / ".ingest_index.json"

    async def _default_embedder(self, text: str) -> EmbedResult:
        return await embed_text(
            text,
            ollama_host=self.settings.ollama_host,
            model=self.settings.ollama_embed_model,
        )

    def domains(self) -> list[dict[str, object]]:
        if not self.root.is_dir():
            return []
        domains: list[dict[str, object]] = []
        for child in sorted(self.root.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            files = [p for p in child.rglob("*") if p.suffix.lower() in SUPPORTED_SUFFIXES]
            domains.append({"name": child.name, "file_count": len(files)})
        return domains

    def _load_index(self) -> dict[str, str]:
        if not self.index_path.is_file():
            return {}
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save_index(self, index: dict[str, str]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    async def ingest_all(self, *, force: bool = False) -> IngestReport:
        report = IngestReport(ok=True)
        if not self.root.is_dir():
            return report

        index = self._load_index()
        for path in sorted(self.root.rglob("*")):
            if path.suffix.lower() not in SUPPORTED_SUFFIXES or not path.is_file():
                continue
            report.files_scanned += 1
            rel = str(path.relative_to(self.root))
            try:
                digest = _file_hash(path)
            except OSError as exc:
                report.errors.append(f"{rel}: {exc}")
                continue
            if not force and index.get(rel) == digest:
                report.skipped += 1
                continue

            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                report.errors.append(f"{rel}: {exc}")
                continue

            domain = path.relative_to(self.root).parts[0]
            added = 0
            for i, chunk in enumerate(chunk_text(text)):
                embed = await self.embedder(chunk)
                if not embed.ok or embed.embedding is None:
                    report.errors.append(f"{rel}#{i}: {embed.error}")
                    report.ok = False
                    continue
                self.store.add(
                    chunk,
                    embed.embedding,
                    metadata={
                        "domain": domain,
                        "source": rel,
                        "chunk": str(i),
                        "ingested_at": str(time.time()),
                    },
                    record_id=f"{rel}#{i}",
                )
                added += 1
            if added:
                report.files_ingested += 1
                report.chunks_added += added
                index[rel] = digest

        self._save_index(index)
        return report
