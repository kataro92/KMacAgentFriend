# TR-performance — Model pinning & inference queue (16 GB RAM)

## Purpose

Keep local models responsive and avoid memory thrash from concurrent heavy
inference on Apple Silicon with limited RAM.

## Requirements

**TR-PERF-001** When `pin_ollama_models` is on, the daemon SHALL preload chat, embed, and VLM models with `keep_alive`.

**TR-PERF-002** A single-slot inference gate SHALL serialize STT, LLM chat, and VLM operations.

**TR-PERF-003** Daemon SHALL expose `GET /api/performance/status` and `POST /api/performance/pin`.

## Acceptance criteria

```bash
pytest tests/test_performance.py -q
```
