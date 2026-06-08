import pytest
from kmac_agent_friend.config import Settings
from kmac_agent_friend.knowledge import KnowledgeIngestor, chunk_text, knowledge_root
from kmac_agent_friend.memory.embeddings import EmbedResult
from kmac_agent_friend.memory.vector_store import LongTermMemory


def test_chunk_text_short():
    assert chunk_text("hello world") == ["hello world"]
    assert chunk_text("") == []


def test_chunk_text_splits_long():
    text = "\n\n".join(f"paragraph {i} " * 30 for i in range(10))
    chunks = chunk_text(text, max_chars=400, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)


def _make_settings(tmp_path) -> Settings:
    return Settings(kaf_data_dir=tmp_path)


async def _fake_embed(text: str) -> EmbedResult:
    # Deterministic toy embedding from char codes.
    vec = [float(sum(ord(c) for c in text) % 97), float(len(text))]
    return EmbedResult(ok=True, embedding=vec)


@pytest.mark.asyncio
async def test_ingest_all_and_domains(tmp_path):
    settings = _make_settings(tmp_path)
    root = knowledge_root(settings)
    (root / "cooking").mkdir(parents=True)
    (root / "cooking" / "pasta.md").write_text("Boil water. Add pasta.", encoding="utf-8")
    (root / "travel").mkdir(parents=True)
    (root / "travel" / "japan.txt").write_text("Tokyo is large.", encoding="utf-8")

    store = LongTermMemory(tmp_path / "k.db", collection="knowledge")
    ingestor = KnowledgeIngestor(settings, store=store, embedder=_fake_embed)

    domains = {d["name"]: d["file_count"] for d in ingestor.domains()}
    assert domains == {"cooking": 1, "travel": 1}

    report = await ingestor.ingest_all()
    assert report.ok
    assert report.files_ingested == 2
    assert report.chunks_added == 2
    assert store.count() == 2

    # Re-running skips unchanged files.
    report2 = await ingestor.ingest_all()
    assert report2.files_ingested == 0
    assert report2.skipped == 2


@pytest.mark.asyncio
async def test_ingest_force_reingest(tmp_path):
    settings = _make_settings(tmp_path)
    root = knowledge_root(settings)
    (root / "d").mkdir(parents=True)
    (root / "d" / "a.md").write_text("content", encoding="utf-8")
    store = LongTermMemory(tmp_path / "k.db", collection="knowledge")
    ingestor = KnowledgeIngestor(settings, store=store, embedder=_fake_embed)

    await ingestor.ingest_all()
    report = await ingestor.ingest_all(force=True)
    assert report.files_ingested == 1
