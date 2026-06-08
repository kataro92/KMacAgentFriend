# TR-memory — Conversation history (Phase 3)

## Purpose

Persist chat turns in local SQLite and feed recent history into Ollama requests.

## Requirements

**TR-MEM-001** Daemon SHALL store messages in SQLite under `KAF_DATA_DIR`.

**TR-MEM-002** Voice and chat endpoints SHALL append user and assistant messages.

**TR-MEM-003** Chat SHALL include the last N messages (default 10) as Ollama context.

**TR-MEM-004** Daemon SHALL expose `GET /api/conversations` and `GET /api/conversations/{id}/messages`.

## Acceptance criteria

```bash
pytest tests/test_memory.py -q
```
