"""Short Ollama chat turn for voice replies."""

from __future__ import annotations

import httpx
from pydantic import BaseModel


class ChatResult(BaseModel):
    ok: bool
    reply: str = ""
    error: str = ""


SYSTEM_PROMPT = (
    "You are KMacAgentFriend, a helpful local Mac assistant. "
    "Reply concisely in the same language the user spoke. "
    "Keep answers short enough to speak aloud."
)


async def chat_reply(
    user_text: str,
    *,
    ollama_host: str,
    model: str,
    history: list[dict[str, str]] | None = None,
    timeout: float = 60.0,
) -> ChatResult:
    prompt = user_text.strip()
    if not prompt:
        return ChatResult(ok=False, error="Empty user text")

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    url = f"{ollama_host.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        return ChatResult(ok=False, error=f"Ollama unreachable: {exc}")

    message = data.get("message") or {}
    reply = (message.get("content") or "").strip()
    if not reply:
        return ChatResult(ok=False, error="Ollama returned an empty reply")
    return ChatResult(ok=True, reply=reply)
