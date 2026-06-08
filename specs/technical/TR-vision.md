# TR-vision — Camera + VLM (Phase 4)

## Purpose

On-demand camera capture (user-confirmed) and local Ollama vision analysis.

## Requirements

**TR-VISION-001** Vision capture SHALL require explicit user confirmation before the daemon processes an image.

**TR-VISION-002** Daemon SHALL expose `POST /api/vision/analyze` accepting JPEG/PNG and a prompt.

**TR-VISION-003** VLM SHALL use local Ollama only (`llava` or configured model).

**TR-VISION-004** Captured frames SHALL NOT be persisted by default.

## Acceptance criteria

```bash
pytest tests/test_vision.py -q
```
