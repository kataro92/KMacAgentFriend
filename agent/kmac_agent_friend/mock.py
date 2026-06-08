"""Mock responses so the Swift UI works without Ollama installed.

Enabled via the ``mock_mode`` setting. Replies are canned and deterministic so
UI development and demos don't require a running local model. Embeddings use a
stable hash so long-term memory still functions offline.
"""

from __future__ import annotations

import hashlib

from kmac_agent_friend.memory.embeddings import EmbedResult
from kmac_agent_friend.vision.vlm import VisionResult
from kmac_agent_friend.voice.chat import ChatResult

MOCK_EMBED_DIM = 64


def mock_chat_reply(user_text: str) -> ChatResult:
    cleaned = (user_text or "").strip()
    if not cleaned:
        return ChatResult(ok=False, error="Empty user text")
    reply = (
        f"[mock] I heard: “{cleaned}”. Ollama is not connected, so this is a "
        "canned reply for UI testing."
    )
    return ChatResult(ok=True, reply=reply)


def mock_vision_result() -> VisionResult:
    return VisionResult(
        ok=True,
        description="[mock] A placeholder scene description (no VLM connected).",
    )


def mock_embedding(text: str, *, dim: int = MOCK_EMBED_DIM) -> EmbedResult:
    cleaned = (text or "").strip()
    if not cleaned:
        return EmbedResult(ok=False, error="Empty text")
    digest = hashlib.sha256(cleaned.encode("utf-8")).digest()
    # Expand the digest deterministically to ``dim`` floats in [0, 1).
    vector: list[float] = []
    counter = 0
    while len(vector) < dim:
        block = hashlib.sha256(digest + counter.to_bytes(4, "big")).digest()
        vector.extend(b / 255.0 for b in block)
        counter += 1
    return EmbedResult(ok=True, embedding=vector[:dim])
