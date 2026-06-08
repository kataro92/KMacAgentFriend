# TR-background-forum — Background worker + Moltbook (Phase 5)

## Purpose

Run periodic background tasks with visible status, and interact with Moltbook forum posts locally.

## Requirements

**TR-BG-001** Daemon SHALL expose `GET /api/background/status`, `POST /api/background/start`, `POST /api/background/stop`.

**TR-BG-002** While running, agent status SHALL be `background` with `background_task` set.

**TR-FORUM-001** Forum text SHALL pass through a sanitizer before storage or display.

**TR-FORUM-002** Daemon SHALL expose `GET /api/forum/feed` using configured `MOLTBOOK_URL`.

## Acceptance criteria

```bash
pytest tests/test_background.py tests/test_forum.py -q
```
