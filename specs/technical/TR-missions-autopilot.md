# TR-missions-autopilot — Career missions, autopilot policy, decision audit

## Purpose

Track long-running goals (missions), gate autonomous actions behind an autopilot
policy, and record every autonomous decision in an audit trail.

## Requirements

**TR-MA-001** Missions SHALL persist in SQLite with status and 0–100 progress.

**TR-MA-002** Daemon SHALL expose CRUD at `/api/missions` (+ `PATCH`/`DELETE`).

**TR-MA-003** With autopilot OFF the agent SHALL be suggestion-only; destructive actions are NEVER auto-approved.

**TR-MA-004** Daemon SHALL expose `GET/POST /api/autopilot/policy` and `GET /api/autopilot/decisions`.

**TR-MA-005** The background "missions" task SHALL advance missions only when autopilot is enabled and record a decision either way.

## Acceptance criteria

```bash
pytest tests/test_missions.py tests/test_autopilot.py -q
```
