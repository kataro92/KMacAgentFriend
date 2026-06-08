import pytest
from httpx import ASGITransport, AsyncClient
from kmac_agent_friend.config import get_settings
from kmac_agent_friend.main import app


@pytest.fixture
def token(tmp_path, monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KAF_API_TOKEN", "test-token-inject")
    get_settings.cache_clear()
    return "test-token-inject"


@pytest.mark.asyncio
async def test_inject_text_broadcasts(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/tools/inject",
            headers=headers,
            json={"text": "hello"},
        )
    assert response.status_code == 200
    assert response.json()["ok"] is True
