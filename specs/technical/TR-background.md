# TR-background — Background worker + forum (Phase 5)

## Purpose

Run low-priority background tasks (forum check, learning) with visible agent status.

## Requirements

**TR-BG-001** Daemon SHALL expose `GET /api/background/status` and `POST /api/background/toggle`.

**TR-BG-002** When background work runs, agent status SHALL be `background` with `background_task` set.

**TR-BG-003** Moltbook client SHALL be local HTTP only (configurable base URL).

## Acceptance criteria

```bash
pytest tests/test_background.py -q
```
