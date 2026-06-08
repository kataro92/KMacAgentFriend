import pytest
from httpx import ASGITransport, AsyncClient
from kmac_agent_friend.config import get_settings
from kmac_agent_friend.main import app, background_worker


@pytest.fixture
def token(tmp_path, monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KAF_API_TOKEN", "test-token-bg")
    get_settings.cache_clear()
    return "test-token-bg"


@pytest.mark.asyncio
async def test_background_start_stop(token):
    await background_worker.stop()
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start = await client.post(
            "/api/background/start",
            headers=headers,
            json={"task": "moltbook", "interval_seconds": 3600},
        )
        assert start.status_code == 200
        assert start.json()["ok"] is True

        status = await client.get("/api/background/status", headers=headers)
        assert status.json()["running"] is True
        assert status.json()["agent"]["status"] == "background"

        stop = await client.post("/api/background/stop", headers=headers)
        assert stop.json()["ok"] is True

        status2 = await client.get("/api/background/status", headers=headers)
        assert status2.json()["running"] is False

    await background_worker.stop()
