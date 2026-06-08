import json
from unittest.mock import patch

import pytest
from kmac_agent_friend.agent.runner import chat_with_tools
from kmac_agent_friend.config import get_settings
from kmac_agent_friend.memory import ConversationStore


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    return ConversationStore.from_settings(get_settings())


@pytest.mark.asyncio
async def test_chat_with_tools_executes_read_file(store):
    settings = get_settings()

    calls = 0

    async def fake_ollama(messages, *, ollama_host, model, tools=None, timeout=60.0):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "read_file",
                                "arguments": json.dumps({"path": "note.txt"}),
                            }
                        }
                    ],
                }
            }
        return {"message": {"role": "assistant", "content": "File says hi"}}

    settings.sandbox_dir.mkdir(parents=True, exist_ok=True)
    (settings.sandbox_dir / "note.txt").write_text("hi", encoding="utf-8")

    with patch("kmac_agent_friend.agent.runner._ollama_chat", side_effect=fake_ollama):
        result = await chat_with_tools("read my note", settings=settings, store=store)

    assert result.ok is True
    assert result.reply == "File says hi"
    recent = store.recent()
    assert recent[-2]["role"] == "user"
    assert recent[-1]["role"] == "assistant"
