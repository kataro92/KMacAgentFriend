"""Ollama vision model analysis."""

from __future__ import annotations

import base64

import httpx
from pydantic import BaseModel


class VisionResult(BaseModel):
    ok: bool
    description: str = ""
    error: str = ""


async def analyze_image(
    image_bytes: bytes,
    prompt: str,
    *,
    ollama_host: str,
    model: str,
    timeout: float = 120.0,
) -> VisionResult:
    cleaned = prompt.strip() or "Describe what you see."
    if not image_bytes:
        return VisionResult(ok=False, error="Empty image")

    encoded = base64.b64encode(image_bytes).decode("ascii")
    url = f"{ollama_host.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": cleaned,
                "images": [encoded],
            }
        ],
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        return VisionResult(ok=False, error=f"Ollama vision unreachable: {exc}")

    message = data.get("message") or {}
    description = (message.get("content") or "").strip()
    if not description:
        return VisionResult(ok=False, error="Ollama returned an empty vision reply")
    return VisionResult(ok=True, description=description)
