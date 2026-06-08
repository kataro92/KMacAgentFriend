"""Ollama chat with optional tool loop."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from kmac_agent_friend.config import Settings
from kmac_agent_friend.memory.history import DEFAULT_CONVERSATION_ID, ConversationStore
from kmac_agent_friend.memory.service import MemoryService
from kmac_agent_friend.tools import list_dir, read_file, run_shell
from kmac_agent_friend.voice.chat import ChatResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are KMacAgentFriend, a helpful local Mac assistant. "
    "Reply concisely in the same language the user spoke. "
    "Use tools when needed to read files, list directories, or run safe shell commands."
)

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file inside allowed project or sandbox paths.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files in an allowed directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": (
                "Run a shell command in an allowed directory. "
                "Destructive commands need confirm."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "cwd": {"type": "string"},
                    "confirm": {"type": "boolean"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": (
                "Search long-term semantic memory for relevant past facts or "
                "conversations. Use before answering questions about the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "k": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
]


async def _execute_tool(name: str, arguments: dict[str, Any], settings: Settings) -> str:
    if name == "read_file":
        result = read_file(str(arguments.get("path", "")), settings)
    elif name == "list_dir":
        result = list_dir(str(arguments.get("path", ".")), settings)
    elif name == "run_shell":
        result = await run_shell(
            str(arguments.get("command", "")),
            settings,
            cwd=str(arguments.get("cwd", ".")),
            confirm=bool(arguments.get("confirm", False)),
        )
    elif name == "recall_memory":
        recall = await MemoryService(settings).recall(
            str(arguments.get("query", "")),
            k=int(arguments.get("k", 5) or 5),
        )
        return json.dumps(
            {
                "ok": recall.ok,
                "error": recall.error,
                "memories": [
                    {"text": r.text, "score": round(r.score, 4)}
                    for r in (recall.records or [])
                ],
            }
        )
    else:
        return json.dumps({"ok": False, "error": f"Unknown tool: {name}"})

    if hasattr(result, "entries") and result.entries is not None:
        return json.dumps({"ok": result.ok, "entries": result.entries, "error": result.error})
    if hasattr(result, "content") and result.content:
        return json.dumps({"ok": result.ok, "content": result.content, "error": result.error})
    if hasattr(result, "stdout"):
        return json.dumps(
            {
                "ok": result.ok,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "error": result.error,
                "needs_confirmation": getattr(result, "needs_confirmation", False),
            }
        )
    return json.dumps({"ok": result.ok, "error": getattr(result, "error", "")})


async def _ollama_chat(
    messages: list[dict[str, Any]],
    *,
    ollama_host: str,
    model: str,
    tools: list[dict[str, Any]] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    url = f"{ollama_host.rstrip('/')}/api/chat"
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


async def chat_with_tools(
    user_text: str,
    *,
    settings: Settings,
    store: ConversationStore,
    conversation_id: str = DEFAULT_CONVERSATION_ID,
    history_limit: int = 10,
    max_tool_rounds: int = 5,
) -> ChatResult:
    prompt = user_text.strip()
    if not prompt:
        return ChatResult(ok=False, error="Empty user text")

    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(store.recent(limit=history_limit, conversation_id=conversation_id))
    messages.append({"role": "user", "content": prompt})

    try:
        for _ in range(max_tool_rounds):
            data = await _ollama_chat(
                messages,
                ollama_host=settings.ollama_host,
                model=settings.ollama_model,
                tools=TOOL_DEFINITIONS,
            )
            message = data.get("message") or {}
            tool_calls = message.get("tool_calls") or []

            if tool_calls:
                messages.append(message)
                for call in tool_calls:
                    fn = call.get("function") or {}
                    name = fn.get("name", "")
                    raw_args = fn.get("arguments") or "{}"
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except json.JSONDecodeError:
                        args = {}
                    tool_output = await _execute_tool(name, args, settings)
                    messages.append({"role": "tool", "content": tool_output})
                continue

            reply = (message.get("content") or "").strip()
            if not reply:
                return ChatResult(ok=False, error="Ollama returned an empty reply")

            store.append("user", prompt, conversation_id=conversation_id)
            store.append("assistant", reply, conversation_id=conversation_id)
            return ChatResult(ok=True, reply=reply)

        return ChatResult(ok=False, error="Tool loop exceeded max rounds")
    except httpx.HTTPError as exc:
        return ChatResult(ok=False, error=f"Ollama unreachable: {exc}")
