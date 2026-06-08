import pytest
from httpx import ASGITransport, AsyncClient
from kmac_agent_friend.activity_log import activity_log
from kmac_agent_friend.config import get_settings
from kmac_agent_friend.main import app


@pytest.fixture
def token(tmp_path, monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KAF_API_TOKEN", "test-token-activity")
    get_settings.cache_clear()
    activity_log.clear()
    return "test-token-activity"


@pytest.mark.asyncio
async def test_activity_log_and_clear(token):
    headers = {"Authorization": f"Bearer {token}"}
    activity_log.append("info", "test", "hello", {"x": 1})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/activity", headers=headers)
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert any(entry["message"] == "hello" for entry in entries)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        clear = await client.post("/api/activity/clear", headers=headers)
    assert clear.status_code == 200
    assert activity_log.recent()[-1]["message"] == "Activity log cleared"
