from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from kmac_agent_friend.config import get_settings, reload_settings
from kmac_agent_friend.main import app
from kmac_agent_friend.settings_store import user_settings_path


@pytest.fixture
def token(tmp_path, monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KAF_API_TOKEN", "test-token-settings")
    get_settings.cache_clear()
    return "test-token-settings"


@pytest.mark.asyncio
async def test_get_settings(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/settings", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["settings"]["ollama_model"] == "llama3.2"
    assert data["daemon"]["port"] == 18750


@pytest.mark.asyncio
async def test_patch_settings_persists(token, tmp_path):
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/api/settings",
            headers=headers,
            json={"ollama_model": "mistral", "tts_language": "vi"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["ollama_model"] == "mistral"
    assert data["settings"]["tts_language"] == "vi"

    settings_file = user_settings_path(tmp_path)
    assert settings_file.is_file()

    reload_settings()
    assert get_settings().ollama_model == "mistral"
    assert get_settings().tts_language == "vi"


@pytest.mark.asyncio
async def test_list_ollama_models(token):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"models": [{"name": "llama3.2:latest"}, {"name": "llava"}]}
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = payload
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    with patch("kmac_agent_friend.main.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/ollama/models", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["models"] == ["llama3.2:latest", "llava"]
