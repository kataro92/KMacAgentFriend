# TR-security — Sandbox audit & tool rate limiting

## Purpose

Harden the sandbox against path escapes and sensitive-file access, and throttle
tool execution to contain runaway loops.

## Requirements

**TR-SEC-001** Path resolution SHALL reject NUL bytes and symlink escapes from allowed roots.

**TR-SEC-002** Sensitive files (`.env`, `.api_token`, private keys, …) SHALL be blocked even inside allowed roots.

**TR-SEC-003** Shell and file-write tools SHALL honor `tool_rate_limit_per_minute` (sliding window; `0` disables).

**TR-SEC-004** Daemon SHALL expose `GET /api/security/audit` reporting risky roots/permissions.

## Acceptance criteria

```bash
pytest tests/test_security.py -q
```
