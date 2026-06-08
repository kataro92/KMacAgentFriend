"""Text embeddings via Ollama's local embedding API."""

from __future__ import annotations

import math
from dataclasses import dataclass

import httpx

DEFAULT_EMBED_MODEL = "nomic-embed-text"


@dataclass
class EmbedResult:
    ok: bool
    embedding: list[float] | None = None
    error: str = ""


async def embed_text(
    text: str,
    *,
    ollama_host: str,
    model: str = DEFAULT_EMBED_MODEL,
    timeout: float = 30.0,
) -> EmbedResult:
    """Return a single embedding vector for ``text`` from a local Ollama model."""
    cleaned = (text or "").strip()
    if not cleaned:
        return EmbedResult(ok=False, error="Empty text")

    url = f"{ollama_host.rstrip('/')}/api/embeddings"
    payload = {"model": model, "prompt": cleaned}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        return EmbedResult(ok=False, error=f"Ollama embeddings unreachable: {exc}")

    vector = data.get("embedding")
    if not isinstance(vector, list) or not vector:
        return EmbedResult(ok=False, error="Ollama returned an empty embedding")
    return EmbedResult(ok=True, embedding=[float(x) for x in vector])


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors (0 when degenerate)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
