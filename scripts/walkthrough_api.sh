#!/usr/bin/env bash
# Exercise daemon HTTP/WebSocket APIs and print a summary.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate

TOKEN=$(python -c "from kmac_agent_friend.config import get_settings, resolve_api_token; print(resolve_api_token(get_settings()))")
BASE="http://127.0.0.1:18750"
AUTH="Authorization: Bearer $TOKEN"
FAIL=0

check() {
  local name="$1" code="$2" expect="$3"
  if [[ "$code" == "$expect" ]]; then
    echo "OK  $name ($code)"
  else
    echo "FAIL $name (got $code, want $expect)"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== KMacAgentFriend API walkthrough ==="
echo "Token: ${TOKEN:0:4}…"

code=$(curl -s -o /tmp/kaf_health.json -w "%{http_code}" -H "$AUTH" "$BASE/health")
check "GET /health" "$code" "200"
cat /tmp/kaf_health.json | python -m json.tool | head -12

code=$(curl -s -o /tmp/kaf_settings.json -w "%{http_code}" -H "$AUTH" "$BASE/api/settings")
check "GET /api/settings" "$code" "200"

code=$(curl -s -o /tmp/kaf_models.json -w "%{http_code}" -H "$AUTH" "$BASE/api/ollama/models")
check "GET /api/ollama/models" "$code" "200"

code=$(curl -s -o /tmp/kaf_state.json -w "%{http_code}" -H "$AUTH" "$BASE/api/state")
check "GET /api/state" "$code" "200"

code=$(curl -s -o /tmp/kaf_ping.json -w "%{http_code}" -X POST -H "$AUTH" "$BASE/api/ping")
check "POST /api/ping" "$code" "200"

code=$(curl -s -o /tmp/kaf_bg.json -w "%{http_code}" -H "$AUTH" "$BASE/api/background/status")
check "GET /api/background/status" "$code" "200"

code=$(curl -s -o /tmp/kaf_tools.json -w "%{http_code}" -H "$AUTH" "$BASE/api/tools/list?path=.")
check "GET /api/tools/list" "$code" "200"

code=$(curl -s -o /tmp/kaf_conv.json -w "%{http_code}" -H "$AUTH" "$BASE/api/conversations")
check "GET /api/conversations" "$code" "200"

code=$(curl -s -o /tmp/kaf_forum.json -w "%{http_code}" -H "$AUTH" "$BASE/api/forum/feed")
check "GET /api/forum/feed" "$code" "200"

code=$(curl -s -o /tmp/kaf_speak.json -w "%{http_code}" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"text":"walkthrough test"}' "$BASE/api/voice/speak")
check "POST /api/voice/speak" "$code" "200"

code=$(curl -s -o /tmp/kaf_patch.json -w "%{http_code}" -X PATCH -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"ollama_model":"llama3.2"}' "$BASE/api/settings")
check "PATCH /api/settings" "$code" "200"

code=$(curl -s -o /tmp/kaf_chat.json -w "%{http_code}" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"message":"Say hi in one word"}' "$BASE/api/chat")
check "POST /api/chat" "$code" "200"

code=$(curl -s -o /tmp/kaf_bg_start.json -w "%{http_code}" -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"task":"walkthrough","interval_seconds":60}' "$BASE/api/background/start")
check "POST /api/background/start" "$code" "200"

code=$(curl -s -o /tmp/kaf_bg_stop.json -w "%{http_code}" -X POST -H "$AUTH" "$BASE/api/background/stop")
check "POST /api/background/stop" "$code" "200"

python3 - <<'PY' || FAIL=$((FAIL + 1))
import asyncio, json, os, sys
try:
    import websockets
except ImportError:
    print("SKIP WebSocket (websockets not installed)")
    sys.exit(0)

async def main():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    token_path = root / "data" / ".api_token"
    if not token_path.is_file():
        token_path = Path.home() / "Library/Application Support/KMacAgentFriend/.api_token"
    token = token_path.read_text(encoding="utf-8").strip()
    uri = f"ws://127.0.0.1:18750/ws?token={token}"
    async with websockets.connect(uri) as ws:
        first = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        assert first.get("type") == "state", first
        await ws.send(json.dumps({"type": "ping"}))
        pong = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        assert pong.get("type") == "pong", pong
    print("OK  WebSocket ping/pong")

asyncio.run(main())
PY

code=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH" "$BASE/health")
check "GET /health (no auth should fail)" "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health")" "401"

echo "=== done: $FAIL failure(s) ==="
exit "$FAIL"
