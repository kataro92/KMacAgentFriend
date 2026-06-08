# TR-reincarnation — Export / import the agent "soul"

## Purpose

Allow the agent's settings, conversations, memories, and knowledge to be exported
as a portable bundle and restored into a fresh install.

## Requirements

**TR-RC-001** Export SHALL include settings overrides, conversations, memories (with embeddings), and knowledge.

**TR-RC-002** Import SHALL restore all sections and optionally apply settings.

**TR-RC-003** Embeddings SHALL be carried in the bundle so import needs no Ollama call.

**TR-RC-004** Daemon SHALL expose `GET /api/reincarnation/export` and `POST /api/reincarnation/import`.

## Acceptance criteria

```bash
pytest tests/test_reincarnation.py -q
```
