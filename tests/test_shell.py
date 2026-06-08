import pytest
from httpx import ASGITransport, AsyncClient
from kmac_agent_friend.config import get_settings
from kmac_agent_friend.main import app
from kmac_agent_friend.tools.shell import check_command, run_shell


@pytest.fixture
def token(tmp_path, monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KAF_API_TOKEN", "test-token-shell")
    monkeypatch.setenv("KAF_PROJECT_DIRS", str(tmp_path / "projects"))
    get_settings.cache_clear()
    (tmp_path / "sandbox").mkdir()
    (tmp_path / "projects").mkdir()
    return "test-token-shell"


def test_blocks_sudo():
    result = check_command("sudo rm file.txt", confirm=False)
    assert result is not None
    assert result.ok is False
    assert "Blocked" in result.error


def test_rm_needs_confirmation():
    result = check_command("rm notes.txt", confirm=False)
    assert result is not None
    assert result.needs_confirmation is True


@pytest.mark.asyncio
async def test_rm_allowed_with_confirm(token):
    settings = get_settings()
    sandbox = settings.sandbox_dir
    target = sandbox / "gone.txt"
    target.write_text("bye", encoding="utf-8")
    result = await run_shell(f"rm {target.name}", settings, cwd=str(sandbox), confirm=True)
    assert result.ok is True
    assert not target.exists()


@pytest.mark.asyncio
async def test_run_api_blocked(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/tools/run",
            headers=headers,
            json={"command": "sudo ls"},
        )
    data = response.json()
    assert data["ok"] is False
    assert "Blocked" in data["error"]
