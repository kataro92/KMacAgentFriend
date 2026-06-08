# TR-knowledge — Knowledge domain files & ingestion (Phase 3)

## Purpose

Let users drop reference files into knowledge domains and have the agent ingest
them into searchable long-term memory.

## Requirements

**TR-KN-001** Knowledge files SHALL live under `KAF_DATA_DIR/knowledge/<domain>/` as `.md`/`.txt`.

**TR-KN-002** Ingestion SHALL chunk files and embed each chunk into the `knowledge` memory collection.

**TR-KN-003** Ingestion SHALL skip unchanged files using a content-hash index.

**TR-KN-004** Daemon SHALL expose `GET /api/knowledge/domains` and `POST /api/knowledge/ingest`.

## Acceptance criteria

```bash
pytest tests/test_knowledge.py -q
```
