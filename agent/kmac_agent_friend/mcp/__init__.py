"""MCP server supervision.

Per project policy we prefer CLI tools over MCP and never spin up many MCP
servers at startup. This supervisor lazily starts MCP server subprocesses on
demand and keeps at most ``max_processes`` resident, evicting the
least-recently-used server when the pool is full.
"""

from kmac_agent_friend.mcp.supervisor import (
    MCPServerConfig,
    MCPSupervisor,
    load_server_configs,
    mcp_config_path,
)

__all__ = [
    "MCPServerConfig",
    "MCPSupervisor",
    "load_server_configs",
    "mcp_config_path",
]
