# TR-mock-mode — Mock daemon for UI without Ollama

## Purpose

Let the Swift UI run end-to-end without a local model by serving deterministic
canned responses.

## Requirements

**TR-MOCK-001** When `mock_mode` is on, `/health` SHALL report `mock_mode: true` and `ollama: true`.

**TR-MOCK-002** `/api/chat`, `/api/voice/turn`, and `/api/vision/analyze` SHALL return canned replies.

**TR-MOCK-003** Memory embeddings SHALL use a deterministic local hash in mock mode.

## Acceptance criteria

```bash
pytest tests/test_mock_mode.py -q
```
