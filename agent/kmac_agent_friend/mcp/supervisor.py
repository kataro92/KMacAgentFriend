"""Lazy, pooled supervisor for MCP server subprocesses."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from kmac_agent_friend.config import Settings

MCP_CONFIG_FILE = "mcp_servers.json"


@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> MCPServerConfig:
        return cls(
            name=str(data["name"]),
            command=str(data["command"]),
            args=[str(a) for a in data.get("args", [])],
            env={str(k): str(v) for k, v in (data.get("env") or {}).items()},
        )


def mcp_config_path(settings: Settings) -> Path:
    return settings.kaf_data_dir / MCP_CONFIG_FILE


def load_server_configs(settings: Settings) -> dict[str, MCPServerConfig]:
    path = mcp_config_path(settings)
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    servers = raw.get("servers", raw) if isinstance(raw, dict) else raw
    configs: dict[str, MCPServerConfig] = {}
    if isinstance(servers, list):
        for item in servers:
            if isinstance(item, dict) and item.get("name") and item.get("command"):
                cfg = MCPServerConfig.from_dict(item)
                configs[cfg.name] = cfg
    return configs


@dataclass
class _Running:
    process: asyncio.subprocess.Process
    started_at: float
    last_used: float


class MCPSupervisor:
    def __init__(self, max_processes: int = 4) -> None:
        self.max_processes = max(1, max_processes)
        self._configs: dict[str, MCPServerConfig] = {}
        self._running: dict[str, _Running] = {}
        self._lock = asyncio.Lock()

    def register(self, config: MCPServerConfig) -> None:
        self._configs[config.name] = config

    def register_all(self, configs: dict[str, MCPServerConfig]) -> None:
        self._configs.update(configs)

    def available(self) -> list[str]:
        return sorted(self._configs)

    def _alive(self, name: str) -> bool:
        running = self._running.get(name)
        return running is not None and running.process.returncode is None

    async def ensure(self, name: str) -> bool:
        """Start a server if not already running, evicting LRU when pool is full."""
        async with self._lock:
            if name not in self._configs:
                return False
            if self._alive(name):
                self._running[name].last_used = time.time()
                return True
            await self._reap_dead()
            if len(self._running) >= self.max_processes:
                await self._evict_lru()
            return await self._spawn(name)

    async def _spawn(self, name: str) -> bool:
        config = self._configs[name]
        try:
            process = await asyncio.create_subprocess_exec(
                config.command,
                *config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**config.env} or None,
            )
        except (OSError, ValueError):
            return False
        now = time.time()
        self._running[name] = _Running(process=process, started_at=now, last_used=now)
        return True

    async def _reap_dead(self) -> None:
        dead = [name for name, run in self._running.items() if run.process.returncode is not None]
        for name in dead:
            self._running.pop(name, None)

    async def _evict_lru(self) -> None:
        if not self._running:
            return
        victim = min(self._running.items(), key=lambda kv: kv[1].last_used)[0]
        await self._terminate(victim)

    async def _terminate(self, name: str) -> None:
        running = self._running.pop(name, None)
        if running is None:
            return
        process = running.process
        if process.returncode is None:
            try:
                process.terminate()
            except ProcessLookupError:
                return
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except TimeoutError:
                process.kill()
                await process.wait()

    async def stop(self, name: str) -> bool:
        async with self._lock:
            if name not in self._running:
                return False
            await self._terminate(name)
            return True

    async def stop_all(self) -> None:
        async with self._lock:
            for name in list(self._running):
                await self._terminate(name)

    def status(self) -> dict:
        return {
            "max_processes": self.max_processes,
            "available": self.available(),
            "running": [
                {
                    "name": name,
                    "pid": run.process.pid,
                    "alive": run.process.returncode is None,
                    "started_at": run.started_at,
                    "last_used": run.last_used,
                }
                for name, run in self._running.items()
            ],
        }


mcp_supervisor = MCPSupervisor()
