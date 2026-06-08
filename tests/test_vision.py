from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from kmac_agent_friend.config import get_settings
from kmac_agent_friend.main import app
from kmac_agent_friend.vision.vlm import VisionResult


@pytest.fixture
def token(tmp_path, monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KAF_API_TOKEN", "test-token-vision")
    get_settings.cache_clear()
    return "test-token-vision"


@pytest.mark.asyncio
async def test_vision_requires_confirmation(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/vision/analyze",
            headers=headers,
            files={"file": ("shot.jpg", b"\xff\xd8\xff", "image/jpeg")},
            data={"prompt": "what is this"},
        )
    data = response.json()
    assert data["ok"] is False
    assert data["needs_confirmation"] is True


@pytest.mark.asyncio
async def test_vision_analyze_ok(token):
    headers = {"Authorization": f"Bearer {token}"}
    with patch(
        "kmac_agent_friend.main.analyze_image",
        AsyncMock(return_value=VisionResult(ok=True, description="A desk")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/vision/analyze?confirmed=true",
                headers=headers,
                files={"file": ("shot.jpg", b"\xff\xd8\xff", "image/jpeg")},
                data={"prompt": "what is this"},
            )
    data = response.json()
    assert data["ok"] is True
    assert data["description"] == "A desk"
