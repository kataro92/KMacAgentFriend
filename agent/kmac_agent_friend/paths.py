"""Path allowlist for sandboxed file tools."""

from __future__ import annotations

from pathlib import Path

from kmac_agent_friend.config import PROJECT_ROOT, Settings


class PathNotAllowedError(ValueError):
    """Raised when a path is outside allowed roots."""


def project_dirs(settings: Settings) -> list[Path]:
    raw = settings.kaf_project_dirs.strip()
    if not raw:
        return [PROJECT_ROOT.resolve()]
    return [Path(part.strip()).expanduser().resolve() for part in raw.split(",") if part.strip()]


def allowed_roots(settings: Settings) -> list[Path]:
    roots = [settings.sandbox_dir.resolve(), *project_dirs(settings)]
    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def _is_under_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_allowed_path(
    path_str: str,
    settings: Settings,
    *,
    base: Path | None = None,
) -> Path:
    """Resolve a user path and ensure it stays inside an allowed root."""
    raw = Path(path_str).expanduser()
    if not raw.is_absolute():
        anchor = (base or settings.sandbox_dir).resolve()
        candidate = (anchor / raw).resolve()
    else:
        candidate = raw.resolve()

    for root in allowed_roots(settings):
        if _is_under_root(candidate, root):
            return candidate

    raise PathNotAllowedError(f"Path not allowed: {path_str}")
