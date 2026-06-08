"""Sandboxed file read/write/list tools."""

from __future__ import annotations

from dataclasses import dataclass

from kmac_agent_friend.config import Settings
from kmac_agent_friend.paths import PathNotAllowedError, resolve_allowed_path
from kmac_agent_friend.security.ratelimit import tool_rate_limiter


@dataclass
class FileOpResult:
    ok: bool
    path: str = ""
    content: str = ""
    entries: list[dict[str, str | bool]] | None = None
    error: str = ""
    needs_confirmation: bool = False


def list_dir(path_str: str, settings: Settings) -> FileOpResult:
    try:
        path = resolve_allowed_path(path_str or ".", settings)
    except PathNotAllowedError as exc:
        return FileOpResult(ok=False, error=str(exc))

    if not path.exists():
        return FileOpResult(ok=False, path=str(path), error="Path does not exist")
    if not path.is_dir():
        return FileOpResult(ok=False, path=str(path), error="Not a directory")

    entries: list[dict[str, str | bool]] = []
    for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        entries.append(
            {
                "name": child.name,
                "path": str(child),
                "is_dir": child.is_dir(),
            }
        )
    return FileOpResult(ok=True, path=str(path), entries=entries)


def read_file(path_str: str, settings: Settings) -> FileOpResult:
    try:
        path = resolve_allowed_path(path_str, settings)
    except PathNotAllowedError as exc:
        return FileOpResult(ok=False, error=str(exc))

    if not path.is_file():
        return FileOpResult(ok=False, path=str(path), error="Not a file")
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return FileOpResult(ok=False, path=str(path), error="File is not valid UTF-8 text")
    return FileOpResult(ok=True, path=str(path), content=content)


def write_file(
    path_str: str,
    content: str,
    settings: Settings,
    *,
    confirm: bool = False,
) -> FileOpResult:
    if not tool_rate_limiter.allow("write", settings.tool_rate_limit_per_minute):
        return FileOpResult(
            ok=False,
            error=f"Tool rate limit exceeded ({settings.tool_rate_limit_per_minute}/min).",
        )

    try:
        path = resolve_allowed_path(path_str, settings)
    except PathNotAllowedError as exc:
        return FileOpResult(ok=False, error=str(exc))

    if path.exists() and not confirm:
        return FileOpResult(
            ok=False,
            path=str(path),
            error="File exists — set confirm=true to overwrite",
            needs_confirmation=True,
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return FileOpResult(ok=True, path=str(path), content=content)
