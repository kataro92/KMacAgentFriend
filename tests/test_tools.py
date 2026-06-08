import pytest
from httpx import ASGITransport, AsyncClient
from kmac_agent_friend.config import get_settings
from kmac_agent_friend.main import app
from kmac_agent_friend.paths import resolve_allowed_path
from kmac_agent_friend.tools.files import list_dir, read_file, write_file


@pytest.fixture
def token(tmp_path, monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KAF_API_TOKEN", "test-token-tools")
    monkeypatch.setenv("KAF_PROJECT_DIRS", str(tmp_path / "projects"))
    get_settings.cache_clear()
    (tmp_path / "sandbox").mkdir()
    (tmp_path / "projects").mkdir()
    return "test-token-tools"


def test_resolve_rejects_escape(tmp_path, token):
    settings = get_settings()
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")
    with pytest.raises(ValueError, match="not allowed"):
        resolve_allowed_path(str(outside), settings)


def test_write_and_read_in_sandbox(token):
    settings = get_settings()
    result = write_file("notes.txt", "hello", settings)
    assert result.ok is True
    read = read_file("notes.txt", settings)
    assert read.ok is True
    assert read.content == "hello"


def test_write_requires_confirm_to_overwrite(token):
    settings = get_settings()
    write_file("dup.txt", "first", settings)
    blocked = write_file("dup.txt", "second", settings)
    assert blocked.ok is False
    allowed = write_file("dup.txt", "second", settings, confirm=True)
    assert allowed.ok is True
    assert read_file("dup.txt", settings).content == "second"


def test_list_dir(token):
    settings = get_settings()
    write_file("a.txt", "a", settings)
    write_file("b.txt", "b", settings)
    listing = list_dir(".", settings)
    assert listing.ok is True
    names = {entry["name"] for entry in listing.entries or []}
    assert "a.txt" in names
    assert "b.txt" in names


@pytest.mark.asyncio
async def test_tools_api_write_read(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        write = await client.post(
            "/api/tools/write",
            headers=headers,
            json={"path": "api.txt", "content": "via api"},
        )
        assert write.status_code == 200
        assert write.json()["ok"] is True

        read = await client.get("/api/tools/read", headers=headers, params={"path": "api.txt"})
        assert read.status_code == 200
        assert read.json()["content"] == "via api"

        listing = await client.get("/api/tools/list", headers=headers, params={"path": "."})
        assert listing.status_code == 200
        names = {e["name"] for e in listing.json()["entries"]}
        assert "api.txt" in names
