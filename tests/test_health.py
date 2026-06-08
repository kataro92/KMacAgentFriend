from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from kmac_agent_friend.config import get_settings, resolve_api_token
from kmac_agent_friend.main import app


@pytest.fixture
def token(tmp_path, monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KAF_API_TOKEN", "test-token-phase0")
    get_settings.cache_clear()
    return "test-token-phase0"


@pytest.mark.asyncio
async def test_health_requires_auth(token):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_ok(token):
    headers = {"Authorization": f"Bearer {token}"}
    with patch("kmac_agent_friend.main._ollama_reachable", return_value=False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["service"] == "kmac-agent-friend"
    assert data["api_version"] == 4
    assert data["ollama"] is False
    assert data["agent"]["status"] == "idle"


@pytest.mark.asyncio
async def test_ping_round_trip(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/ping", headers=headers)
    assert response.status_code == 200
    assert response.json()["pong"] is True


def test_resolve_api_token_persists(tmp_path, monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KAF_API_TOKEN", "")
    get_settings.cache_clear()
    settings = get_settings()
    t1 = resolve_api_token(settings)
    t2 = resolve_api_token(settings)
    assert t1 == t2
    assert len(t1) > 20
