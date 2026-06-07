# TR-ipc-websocket — Local IPC (Phase 0)

## Purpose

Define how the Swift gadget shell talks to the Python daemon securely on localhost.

## Requirements

**TR-IPC-001** The daemon SHALL bind only to `127.0.0.1`.

**TR-IPC-002** All HTTP endpoints except WebSocket upgrade SHALL require `Authorization: Bearer <token>`.

**TR-IPC-003** WebSocket at `/ws` SHALL require `?token=<token>` query parameter.

**TR-IPC-004** The daemon SHALL expose `GET /health` returning service status and Ollama reachability.

**TR-IPC-005** The daemon SHALL expose `POST /api/ping` for HTTP latency checks.

**TR-IPC-006** WebSocket clients SHALL send `{"type":"ping"}` and receive `{"type":"pong","latency_ms":...}`.

**TR-IPC-007** Default port SHALL be `18750` (override via `KAF_PORT`).

## Constraints

- SHALL NOT bind to `0.0.0.0`
- SHALL NOT accept connections without valid token
- SHALL NOT use CORS for remote origins in production

## Scenarios

### Scenario: Swift connects on launch

```
GIVEN the daemon is running with a known token
WHEN the Swift app opens ws://127.0.0.1:18750/ws?token=...
THEN it SHALL receive a state event within 1 second
AND menu bar icon SHALL show connected status
```

### Scenario: Invalid token rejected

```
GIVEN token "wrong"
WHEN client calls GET /health
THEN response status SHALL be 401
```

## Acceptance criteria

```bash
# Start daemon
source .venv/bin/activate && python -m kmac_agent_friend.main

# Health (replace TOKEN)
curl -sf -H "Authorization: Bearer $TOKEN" http://127.0.0.1:18750/health | jq -e '.ok == true'

# Ping
curl -sf -H "Authorization: Bearer $TOKEN" -X POST http://127.0.0.1:18750/api/ping | jq -e '.pong == true'

# Tests
pytest tests/test_health.py -q
```

## Not included (Phase 0)

- Voice audio streaming over WebSocket
- Chat message protocol
- Camera frame upload
