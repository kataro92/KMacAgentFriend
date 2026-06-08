import pytest
from kmac_agent_friend.config import Settings
from kmac_agent_friend.paths import (
    PathNotAllowedError,
    is_sensitive_path,
    resolve_allowed_path,
)
from kmac_agent_friend.security import RateLimiter, audit_sandbox
from kmac_agent_friend.tools.files import read_file, write_file


def _settings(tmp_path) -> Settings:
    (tmp_path / "sandbox").mkdir(parents=True, exist_ok=True)
    return Settings(kaf_data_dir=tmp_path, kaf_project_dirs=str(tmp_path / "proj"))


def test_sensitive_path_detection():
    from pathlib import Path

    assert is_sensitive_path(Path("/x/.env"))
    assert is_sensitive_path(Path("/x/server.pem"))
    assert not is_sensitive_path(Path("/x/notes.txt"))


def test_resolve_rejects_nul_byte(tmp_path):
    settings = _settings(tmp_path)
    with pytest.raises(PathNotAllowedError):
        resolve_allowed_path("foo\x00bar", settings)


def test_resolve_blocks_sensitive_file(tmp_path):
    settings = _settings(tmp_path)
    proj = tmp_path / "proj"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / ".env").write_text("SECRET=1", encoding="utf-8")
    result = read_file(str(proj / ".env"), settings)
    assert not result.ok
    assert "sensitive" in result.error.lower()


def test_resolve_blocks_symlink_escape(tmp_path):
    settings = _settings(tmp_path)
    sandbox = tmp_path / "sandbox"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("nope", encoding="utf-8")
    link = sandbox / "escape"
    link.symlink_to(outside)
    with pytest.raises(PathNotAllowedError):
        resolve_allowed_path(str(link / "secret.txt"), settings)


def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(window_seconds=60)
    now = 1000.0
    assert limiter.allow("k", 2, now=now)
    assert limiter.allow("k", 2, now=now)
    assert not limiter.allow("k", 2, now=now)
    # Window slides — events expire.
    assert limiter.allow("k", 2, now=now + 61)


def test_rate_limiter_zero_disables():
    limiter = RateLimiter()
    for _ in range(100):
        assert limiter.allow("k", 0)


def test_write_respects_rate_limit(tmp_path):
    settings = Settings(kaf_data_dir=tmp_path, tool_rate_limit_per_minute=1)
    (tmp_path / "sandbox").mkdir(parents=True, exist_ok=True)
    from kmac_agent_friend.security.ratelimit import tool_rate_limiter

    tool_rate_limiter.reset("write")
    first = write_file("a.txt", "x", settings)
    assert first.ok
    second = write_file("b.txt", "y", settings)
    assert not second.ok
    assert "rate limit" in second.error.lower()
    tool_rate_limiter.reset("write")


def test_audit_sandbox_returns_findings(tmp_path):
    settings = _settings(tmp_path)
    findings = audit_sandbox(settings)
    assert isinstance(findings, list)
    assert all(f.level in {"info", "warn", "error"} for f in findings)
