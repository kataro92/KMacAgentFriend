from unittest.mock import patch

import pytest
from kmac_agent_friend.config import Settings
from kmac_agent_friend.memory import (
    EmbedResult,
    LongTermMemory,
    MemoryService,
    cosine_similarity,
)


def test_cosine_similarity_basic():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_vector_store_add_and_search(tmp_path):
    store = LongTermMemory(tmp_path / "mem.db")
    store.add("the cat sat", [1.0, 0.0, 0.0], metadata={"k": "v"})
    store.add("a dog barked", [0.0, 1.0, 0.0])
    store.add("kittens are cats", [0.9, 0.1, 0.0])
    assert store.count() == 3

    results = store.search([1.0, 0.0, 0.0], k=2)
    assert len(results) == 2
    assert results[0].text == "the cat sat"
    assert results[0].metadata == {"k": "v"}
    assert results[0].score >= results[1].score


def test_vector_store_rejects_empty(tmp_path):
    store = LongTermMemory(tmp_path / "mem.db")
    with pytest.raises(ValueError):
        store.add("", [1.0])
    with pytest.raises(ValueError):
        store.add("text", [])


def test_vector_store_clear(tmp_path):
    store = LongTermMemory(tmp_path / "mem.db")
    store.add("a", [1.0])
    store.add("b", [0.5])
    assert store.clear() == 2
    assert store.count() == 0


@pytest.mark.asyncio
async def test_memory_service_remember_and_recall(tmp_path):
    settings = Settings(kaf_data_dir=tmp_path)
    store = LongTermMemory(tmp_path / "mem.db")
    service = MemoryService(settings, store=store)

    fake_vectors = {
        "I like espresso": [1.0, 0.0, 0.0],
        "tell me about coffee": [0.95, 0.05, 0.0],
    }

    async def fake_embed(text, *, ollama_host, model, timeout=30.0):
        return EmbedResult(ok=True, embedding=fake_vectors[text])

    with patch("kmac_agent_friend.memory.service.embed_text", side_effect=fake_embed):
        remembered = await service.remember("I like espresso", metadata={"source": "test"})
        assert remembered.ok
        recalled = await service.recall("tell me about coffee", k=1)

    assert recalled.ok
    assert recalled.records
    assert recalled.records[0].text == "I like espresso"


@pytest.mark.asyncio
async def test_memory_service_recall_empty_store(tmp_path):
    settings = Settings(kaf_data_dir=tmp_path)
    store = LongTermMemory(tmp_path / "mem.db")
    service = MemoryService(settings, store=store)
    result = await service.recall("anything")
    assert result.ok
    assert result.records == []
