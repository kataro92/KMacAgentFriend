"""Sandboxed shell execution with command blocklist."""

from __future__ import annotations

import asyncio
import re
import subprocess
from dataclasses import dataclass

from kmac_agent_friend.config import Settings
from kmac_agent_friend.paths import PathNotAllowedError, resolve_allowed_path
from kmac_agent_friend.security.ratelimit import tool_rate_limiter

BLOCKED_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bsudo\b", re.I), "sudo"),
    (re.compile(r"\bsu\b\s", re.I), "su"),
    (re.compile(r"rm\s+(-\w*f\w*\s+|\S+\s+)*(/|\.\.)", re.I), "rm -rf"),
    (re.compile(r"\bmkfs\b", re.I), "mkfs"),
    (re.compile(r"\bdd\b", re.I), "dd"),
    (re.compile(r">\s*/dev/", re.I), "redirect to /dev"),
    (re.compile(r"\bchmod\s+777\b", re.I), "chmod 777"),
    (re.compile(r"\bchown\b", re.I), "chown"),
)

DESTRUCTIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\brm\b", re.I),
    re.compile(r"\bmv\b", re.I),
    re.compile(r"\bcp\b", re.I),
)


class BlockedCommandError(ValueError):
    """Raised when a command matches the safety blocklist."""


@dataclass
class ShellResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    error: str = ""
    needs_confirmation: bool = False


def validate_command(command: str) -> None:
    cleaned = command.strip()
    if not cleaned:
        raise BlockedCommandError("Empty command")
    for pattern, label in BLOCKED_PATTERNS:
        if pattern.search(cleaned):
            raise BlockedCommandError(f"Blocked command pattern: {label}")


def check_command(command: str, *, confirm: bool = False) -> ShellResult | None:
    """Return a result when blocked or confirmation is required; otherwise None."""
    try:
        validate_command(command)
    except BlockedCommandError as exc:
        return ShellResult(ok=False, error=str(exc))

    if not confirm:
        for pattern in DESTRUCTIVE_PATTERNS:
            if pattern.search(command):
                return ShellResult(
                    ok=False,
                    error="Destructive command requires confirm=true",
                    needs_confirmation=True,
                )
    return None


def _run_sync(command: str, cwd: str) -> ShellResult:
    proc = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    return ShellResult(
        ok=proc.returncode == 0,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        returncode=proc.returncode,
        error="" if proc.returncode == 0 else (proc.stderr or "command failed").strip(),
    )


async def run_shell(
    command: str,
    settings: Settings,
    *,
    cwd: str = ".",
    confirm: bool = False,
) -> ShellResult:
    preflight = check_command(command, confirm=confirm)
    if preflight is not None:
        return preflight

    if not tool_rate_limiter.allow("shell", settings.tool_rate_limit_per_minute):
        return ShellResult(
            ok=False,
            error=(
                f"Tool rate limit exceeded "
                f"({settings.tool_rate_limit_per_minute}/min). Try again shortly."
            ),
        )

    try:
        workdir = resolve_allowed_path(cwd, settings)
    except PathNotAllowedError as exc:
        return ShellResult(ok=False, error=str(exc))

    if not workdir.is_dir():
        return ShellResult(ok=False, error="Working directory does not exist")

    try:
        return await asyncio.to_thread(_run_sync, command, str(workdir))
    except subprocess.TimeoutExpired:
        return ShellResult(ok=False, error="Command timed out after 30s")
