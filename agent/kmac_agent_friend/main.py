"""FastAPI daemon entry point."""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from kmac_agent_friend.auth import verify_token
from kmac_agent_friend.config import ensure_data_dirs, get_settings, resolve_api_token
from kmac_agent_friend.state import AgentStatus, agent_state

logger = logging.getLogger(__name__)


async def _ollama_reachable(host: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{host.rstrip('/')}/api/tags")
            return response.status_code == 200
    except httpx.HTTPError:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    ensure_data_dirs(settings)
    token = resolve_api_token(settings)
    logger.info("KMacAgentFriend daemon starting on %s", settings.bind_url)
    if not settings.kaf_api_token:
        logger.info("API token (save to .env as KAF_API_TOKEN): %s", token)
    yield
    logger.info("KMacAgentFriend daemon stopped")


app = FastAPI(title="KMacAgentFriend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # localhost only — Swift app uses token auth
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health(_: str = Depends(verify_token)):
    settings = get_settings()
    ollama_ok = await _ollama_reachable(settings.ollama_host)
    return {
        "ok": True,
        "service": "kmac-agent-friend",
        "version": "0.1.0",
        "ollama": ollama_ok,
        "ollama_host": settings.ollama_host,
        "model": settings.ollama_model,
        "agent": agent_state.to_dict(),
    }


@app.get("/api/state")
async def get_state(_: str = Depends(verify_token)):
    return agent_state.to_dict()


@app.post("/api/ping")
async def ping(_: str = Depends(verify_token)):
    """Round-trip latency check for Swift shell."""
    return {"pong": True, "ts": time.time()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    settings = get_settings()
    token = websocket.query_params.get("token")
    expected = resolve_api_token(settings)

    if token != expected:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await websocket.accept()
    agent_state.connected_clients += 1
    logger.info("WebSocket client connected (%d total)", agent_state.connected_clients)

    try:
        await websocket.send_json(
            {
                "type": "state",
                "status": agent_state.status.value,
                "action": agent_state.current_action,
            }
        )

        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "code": "invalid_json", "message": "Expected JSON"})
                continue

            msg_type = message.get("type")

            if msg_type == "ping":
                started = time.perf_counter()
                await websocket.send_json(
                    {
                        "type": "pong",
                        "ts": time.time(),
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    }
                )
            elif msg_type == "get_state":
                await websocket.send_json({"type": "state", **agent_state.to_dict()})
            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "unknown_type",
                        "message": f"Unsupported message type: {msg_type}",
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        agent_state.connected_clients = max(0, agent_state.connected_clients - 1)
        logger.info("WebSocket client disconnected (%d remaining)", agent_state.connected_clients)


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    uvicorn.run(
        "kmac_agent_friend.main:app",
        host=settings.kaf_host,
        port=settings.kaf_port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    run()
