# TR-mcp — Pooled MCP supervisor

## Purpose

Run MCP servers only when needed, keeping a small resident pool instead of
spawning many at startup (CLI-over-MCP policy).

## Requirements

**TR-MCP-001** Server definitions SHALL be loaded from `KAF_DATA_DIR/mcp_servers.json`.

**TR-MCP-002** Servers SHALL start lazily on first use.

**TR-MCP-003** At most `max_processes` SHALL run; the least-recently-used is evicted when full.

**TR-MCP-004** Daemon SHALL expose `GET /api/mcp/status`, `POST /api/mcp/start`, `POST /api/mcp/stop`, and stop all on shutdown.

## Acceptance criteria

```bash
pytest tests/test_mcp.py -q
```
