"""Performance helpers for 16 GB Apple Silicon.

* ``InferenceGate`` serializes heavy local inference (STT, LLM chat, VLM) so we
  never run several large models concurrently and thrash memory.
* ``pin_models`` asks Ollama to keep the chat/embed/VLM models resident
  (``keep_alive``) to avoid cold-load latency on each turn.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from kmac_agent_friend.config import Settings

# Keep resident for a day; -1 would pin forever but risks stale memory pressure.
KEEP_ALIVE = "24h"


@dataclass
class GateStatus:
    active: str
    waiting: int
    started_at: float


class InferenceGate:
    """A single-slot async queue for heavy inference operations."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._waiting = 0
        self._active = ""
        self._started_at = 0.0

    @contextlib.asynccontextmanager
    async def slot(self, label: str) -> AsyncIterator[None]:
        self._waiting += 1
        acquired = False
        try:
            async with self._lock:
                acquired = True
                self._waiting = max(0, self._waiting - 1)
                self._active = label
                self._started_at = time.time()
                try:
                    yield
                finally:
                    self._active = ""
                    self._started_at = 0.0
        finally:
            # Cancelled before acquiring the lock: undo the pending increment.
            if not acquired:
                self._waiting = max(0, self._waiting - 1)

    def status(self) -> GateStatus:
        return GateStatus(
            active=self._active,
            waiting=self._waiting,
            started_at=self._started_at,
        )


inference_gate = InferenceGate()


async def _ping_model(client: httpx.AsyncClient, host: str, model: str) -> bool:
    """Touch a model so Ollama loads and keeps it resident."""
    url = f"{host.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [],
        "keep_alive": KEEP_ALIVE,
        "stream": False,
    }
    try:
        response = await client.post(url, json=payload)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


async def pin_models(settings: Settings, *, include_vlm: bool = True) -> dict[str, bool]:
    """Preload chat, embedding, and optionally VLM models into Ollama memory."""
    results: dict[str, bool] = {}
    host = settings.ollama_host
    async with httpx.AsyncClient(timeout=30.0) as client:
        results[settings.ollama_model] = await _ping_model(client, host, settings.ollama_model)
        # Embeddings use a dedicated endpoint.
        embed_url = f"{host.rstrip('/')}/api/embeddings"
        try:
            resp = await client.post(
                embed_url,
                json={
                    "model": settings.ollama_embed_model,
                    "prompt": "warmup",
                    "keep_alive": KEEP_ALIVE,
                },
            )
            results[settings.ollama_embed_model] = resp.status_code == 200
        except httpx.HTTPError:
            results[settings.ollama_embed_model] = False
        if include_vlm:
            results[settings.ollama_vlm_model] = await _ping_model(
                client, host, settings.ollama_vlm_model
            )
    return results
