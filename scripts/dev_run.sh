#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -d .venv ]] && ! .venv/bin/python -c 'import sys' 2>/dev/null; then
  echo "Removing stale .venv (project moved or Python upgraded)..."
  rm -rf .venv
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

pip install -q -r requirements.txt
pip install -q -e .

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

KAF_PORT="${KAF_PORT:-18750}"
KAF_HOST="${KAF_HOST:-127.0.0.1}"

_resolve_token() {
  python -c "from kmac_agent_friend.config import get_settings, resolve_api_token; get_settings.cache_clear(); print(resolve_api_token(get_settings()))"
}

_daemon_healthy() {
  local token="$1"
  [[ -n "$token" ]] && curl -sf -H "Authorization: Bearer $token" \
    "http://${KAF_HOST}:${KAF_PORT}/health" >/dev/null 2>&1
}

if lsof -nP -iTCP:"$KAF_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  pid="$(lsof -nP -iTCP:"$KAF_PORT" -sTCP:LISTEN -t 2>/dev/null | head -1)"
  token="$(_resolve_token)"
  if _daemon_healthy "$token"; then
    echo "Daemon already running on http://${KAF_HOST}:${KAF_PORT} (PID ${pid:-unknown})"
    echo "Stop it with: kill ${pid:-<pid>}"
    exit 0
  fi
  if [[ -n "$pid" ]] && ps -p "$pid" -o args= 2>/dev/null | grep -q "kmac_agent_friend"; then
    echo "Restarting stale KMacAgentFriend daemon (PID ${pid})..."
    kill "$pid" 2>/dev/null || true
    for _ in 1 2 3 4 5; do
      sleep 0.5
      lsof -nP -iTCP:"$KAF_PORT" -sTCP:LISTEN >/dev/null 2>&1 || break
    done
  else
    echo "Port ${KAF_PORT} is in use by another process." >&2
    lsof -nP -iTCP:"$KAF_PORT" -sTCP:LISTEN >&2 || true
    exit 1
  fi
fi

echo "Starting KMacAgentFriend daemon..."
exec python -m kmac_agent_friend.main
