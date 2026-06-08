"""Audit sandbox/allowed roots for risky configuration."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from kmac_agent_friend.config import Settings
from kmac_agent_friend.paths import allowed_roots


@dataclass
class SandboxFinding:
    level: str  # "info" | "warn" | "error"
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"level": self.level, "path": self.path, "message": self.message}


# Roots that would expose far too much of the filesystem.
_DANGEROUS_ROOTS = (Path("/"), Path.home())


def audit_sandbox(settings: Settings) -> list[SandboxFinding]:
    findings: list[SandboxFinding] = []
    roots = allowed_roots(settings)

    for root in roots:
        if not root.exists():
            findings.append(SandboxFinding("info", str(root), "Allowed root does not exist yet"))
            continue

        resolved = root.resolve()
        if resolved in (p.resolve() for p in _DANGEROUS_ROOTS):
            findings.append(
                SandboxFinding(
                    "error",
                    str(root),
                    "Allowed root is the filesystem root or home directory — far too broad",
                )
            )

        if root.is_symlink():
            findings.append(
                SandboxFinding("warn", str(root), "Allowed root is a symlink (escape risk)")
            )

        try:
            mode = root.stat().st_mode
            if mode & stat.S_IWOTH:
                findings.append(
                    SandboxFinding("warn", str(root), "Allowed root is world-writable")
                )
        except OSError as exc:
            findings.append(SandboxFinding("warn", str(root), f"Cannot stat root: {exc}"))

    # Overlapping roots make containment reasoning harder.
    for i, a in enumerate(roots):
        for b in roots[i + 1 :]:
            try:
                a.relative_to(b)
                findings.append(
                    SandboxFinding(
                        "info", str(a), f"Allowed root is nested inside another root ({b})"
                    )
                )
            except ValueError:
                pass

    token_file = settings.kaf_data_dir / ".api_token"
    if token_file.is_file():
        mode = token_file.stat().st_mode
        if mode & (stat.S_IRWXG | stat.S_IRWXO):
            findings.append(
                SandboxFinding(
                    "warn", str(token_file), "API token file is group/other accessible"
                )
            )

    if not findings:
        findings.append(
            SandboxFinding("info", os.fspath(settings.sandbox_dir), "No issues detected")
        )
    return findings
