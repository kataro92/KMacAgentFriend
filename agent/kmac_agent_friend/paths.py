"""Path allowlist for sandboxed file tools."""

from __future__ import annotations

from pathlib import Path

from kmac_agent_friend.config import PROJECT_ROOT, Settings


class PathNotAllowedError(ValueError):
    """Raised when a path is outside allowed roots."""


# Sensitive files that must never be read or written through the sandbox, even
# when they live inside an allowed root (e.g. ``.env`` in the project root).
DENIED_BASENAMES = frozenset(
    {
        ".env",
        ".api_token",
        "user_settings.json",
        "id_rsa",
        "id_ed25519",
        ".netrc",
        ".pgpass",
    }
)
DENIED_SUFFIXES = frozenset({".pem", ".key", ".keychain", ".p12"})


def is_sensitive_path(path: Path) -> bool:
    name = path.name
    if name in DENIED_BASENAMES:
        return True
    return path.suffix.lower() in DENIED_SUFFIXES


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
    allow_sensitive: bool = False,
) -> Path:
    """Resolve a user path and ensure it stays inside an allowed root.

    Defenses: rejects NUL bytes, fully resolves symlinks (an escaping symlink
    resolves outside the roots and is rejected), and blocks sensitive files
    such as ``.env`` / private keys even inside allowed roots.
    """
    if "\x00" in path_str:
        raise PathNotAllowedError("Path contains a NUL byte")

    raw = Path(path_str).expanduser()
    # ``resolve()`` canonicalizes ``..`` and follows symlinks, so a symlink that
    # points outside an allowed root will be rejected by the containment check.
    if not raw.is_absolute():
        anchor = (base or settings.sandbox_dir).resolve()
        candidate = (anchor / raw).resolve()
    else:
        candidate = raw.resolve()

    if not allow_sensitive and is_sensitive_path(candidate):
        raise PathNotAllowedError(f"Access to sensitive file is blocked: {candidate.name}")

    for root in allowed_roots(settings):
        if _is_under_root(candidate, root):
            return candidate

    raise PathNotAllowedError(f"Path not allowed: {path_str}")
