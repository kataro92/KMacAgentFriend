import pytest
from httpx import ASGITransport, AsyncClient
from kmac_agent_friend.config import get_settings
from kmac_agent_friend.main import app
from kmac_agent_friend.mock import mock_chat_reply, mock_embedding, mock_vision_result


def test_mock_chat_reply():
    result = mock_chat_reply("hello there")
    assert result.ok
    assert "hello there" in result.reply
    assert not mock_chat_reply("").ok


def test_mock_vision_result():
    assert mock_vision_result().ok


def test_mock_embedding_deterministic():
    a = mock_embedding("same text")
    b = mock_embedding("same text")
    assert a.ok and b.ok
    assert a.embedding == b.embedding
    assert len(a.embedding) == 64
    assert mock_embedding("different") != b


@pytest.fixture
def mock_token(tmp_path, monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KAF_API_TOKEN", "mock-token")
    monkeypatch.setenv("MOCK_MODE", "true")
    get_settings.cache_clear()
    yield "mock-token"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_chat_endpoint_mock_mode(mock_token):
    headers = {"Authorization": f"Bearer {mock_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/chat", headers=headers, json={"message": "hi"})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data.get("mock") is True
    assert "hi" in data["reply"]


@pytest.mark.asyncio
async def test_health_mock_mode(mock_token):
    headers = {"Authorization": f"Bearer {mock_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health", headers=headers)
    data = response.json()
    assert data["mock_mode"] is True
    assert data["ollama"] is True
