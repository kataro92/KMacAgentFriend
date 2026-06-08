from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from kmac_agent_friend.config import get_settings
from kmac_agent_friend.forum.moltbook import ForumFeed, ForumPost
from kmac_agent_friend.forum.sanitizer import sanitize_forum_text
from kmac_agent_friend.main import app


def test_sanitizer_strips_script():
    raw = "Hello<script>alert(1)</script> world"
    assert "<script" not in sanitize_forum_text(raw)
    assert "Hello" in sanitize_forum_text(raw)


@pytest.fixture
def token(tmp_path, monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KAF_API_TOKEN", "test-token-forum")
    monkeypatch.setenv("MOLTBOOK_URL", "http://moltbook.test")
    get_settings.cache_clear()
    return "test-token-forum"


@pytest.mark.asyncio
async def test_forum_feed(token):
    headers = {"Authorization": f"Bearer {token}"}
    mock_feed = ForumFeed(
        ok=True,
        posts=[ForumPost(id="1", author="bot", title="Hi", body="Clean post")],
    )
    with patch(
        "kmac_agent_friend.main.ForumClient.fetch_feed",
        AsyncMock(return_value=mock_feed),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/forum/feed", headers=headers)
    data = response.json()
    assert data["ok"] is True
    assert data["posts"][0]["title"] == "Hi"
