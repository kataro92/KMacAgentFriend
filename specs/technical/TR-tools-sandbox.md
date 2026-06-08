# TR-tools-sandbox — Sandboxed file tools (Phase 2)

## Purpose

Allow the agent to read and write files only inside the agent sandbox and configured project directories.

## Requirements

**TR-TOOL-001** Writes SHALL be allowed only under `sandbox/` or `KAF_PROJECT_DIRS`.

**TR-TOOL-002** Reads SHALL be allowed only under the same roots.

**TR-TOOL-003** Path traversal (`..`, symlinks escaping roots) SHALL be rejected.

**TR-TOOL-004** Daemon SHALL expose `GET /api/tools/list`, `GET /api/tools/read`, `POST /api/tools/write`.

**TR-TOOL-005** Destructive overwrites SHALL require explicit `confirm: true` in the write body (Phase 2 — Swift confirmation sheet follows).

## Constraints

- SHALL NOT read or write outside allowed roots
- SHALL NOT follow symlinks that resolve outside allowed roots

## Acceptance criteria

```bash
pytest tests/test_tools.py -q
```
