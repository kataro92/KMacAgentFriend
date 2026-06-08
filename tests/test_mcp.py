import sys

import pytest
from kmac_agent_friend.config import Settings
from kmac_agent_friend.mcp import MCPServerConfig, load_server_configs, mcp_config_path
from kmac_agent_friend.mcp.supervisor import MCPSupervisor


def _sleeper(name: str, seconds: int = 30) -> MCPServerConfig:
    return MCPServerConfig(
        name=name,
        command=sys.executable,
        args=["-c", f"import time;time.sleep({seconds})"],
    )


def test_load_server_configs(tmp_path):
    settings = Settings(kaf_data_dir=tmp_path)
    assert load_server_configs(settings) == {}
    mcp_config_path(settings).write_text(
        '{"servers": [{"name": "fs", "command": "echo", "args": ["hi"]}]}',
        encoding="utf-8",
    )
    configs = load_server_configs(settings)
    assert "fs" in configs
    assert configs["fs"].command == "echo"


@pytest.mark.asyncio
async def test_lazy_start_and_status():
    sup = MCPSupervisor(max_processes=2)
    sup.register(_sleeper("a"))
    assert sup.available() == ["a"]
    assert sup.status()["running"] == []

    assert await sup.ensure("a") is True
    status = sup.status()
    assert len(status["running"]) == 1
    assert status["running"][0]["alive"] is True

    # Idempotent — does not spawn a second process.
    assert await sup.ensure("a") is True
    assert len(sup.status()["running"]) == 1

    await sup.stop_all()
    assert sup.status()["running"] == []


@pytest.mark.asyncio
async def test_unknown_server_returns_false():
    sup = MCPSupervisor()
    assert await sup.ensure("missing") is False


@pytest.mark.asyncio
async def test_pool_evicts_lru():
    sup = MCPSupervisor(max_processes=1)
    sup.register(_sleeper("a"))
    sup.register(_sleeper("b"))
    assert await sup.ensure("a")
    assert await sup.ensure("b")  # should evict "a"
    running = {r["name"] for r in sup.status()["running"]}
    assert running == {"b"}
    await sup.stop_all()
