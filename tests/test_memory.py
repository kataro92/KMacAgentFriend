from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from kmac_agent_friend.config import get_settings
from kmac_agent_friend.main import app
from kmac_agent_friend.memory import ConversationStore
from kmac_agent_friend.voice.chat import ChatResult


@pytest.fixture
def token(tmp_path, monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KAF_API_TOKEN", "test-token-memory")
    get_settings.cache_clear()
    return "test-token-memory"


def test_conversation_store_persists(token):
    settings = get_settings()
    store = ConversationStore.from_settings(settings)
    store.append("user", "hi")
    store.append("assistant", "hello")
    messages = store.get_messages()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["content"] == "hello"


@pytest.mark.asyncio
async def test_chat_api_stores_history(token):
    headers = {"Authorization": f"Bearer {token}"}
    with patch(
        "kmac_agent_friend.main.chat_reply",
        AsyncMock(return_value=ChatResult(ok=True, reply="Hey there")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/chat",
                headers=headers,
                json={"message": "hello"},
            )
    assert response.status_code == 200
    assert response.json()["reply"] == "Hey there"

    store = ConversationStore.from_settings(get_settings())
    recent = store.get_messages()
    assert recent[-2]["content"] == "hello"
    assert recent[-1]["content"] == "Hey there"
