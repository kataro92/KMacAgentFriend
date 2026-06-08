# TR-memory-longterm — Long-term semantic memory (Phase 3)

## Purpose

Give the agent durable, searchable memory across sessions using local Ollama
embeddings and a vector store (ChromaDB when installed, SQLite cosine fallback).

## Requirements

**TR-LTM-001** Daemon SHALL embed text via Ollama (`ollama_embed_model`, default `nomic-embed-text`).

**TR-LTM-002** Daemon SHALL persist memories with their embeddings under `KAF_DATA_DIR/memory`.

**TR-LTM-003** Search SHALL rank by cosine similarity and return the top-k records.

**TR-LTM-004** Daemon SHALL expose `GET /api/memory/status`, `POST /api/memory/add`, `POST /api/memory/search`.

**TR-LTM-005** The agent tool loop SHALL expose a `recall_memory` tool.

**TR-LTM-006** When ChromaDB is absent the SQLite backend SHALL be used transparently.

## Acceptance criteria

```bash
pytest tests/test_memory_longterm.py -q
```
