"""Autopilot policy — decides what autonomous actions are permitted.

When autopilot is off the agent is suggestion-only: it may read and propose, but
not write, run shell commands, or post to the forum on its own. Destructive
actions are *never* auto-approved and always require explicit user confirmation,
matching the project's safety constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from kmac_agent_friend.config import Settings


class ActionKind(StrEnum):
    READ = "read"
    SUGGEST = "suggest"
    WRITE = "write"
    SHELL = "shell"
    FORUM_POST = "forum_post"
    DESTRUCTIVE = "destructive"


# Always allowed regardless of autopilot — purely passive / advisory.
_PASSIVE = frozenset({ActionKind.READ, ActionKind.SUGGEST})

# Permitted autonomously only when autopilot is enabled.
_AUTOPILOT = frozenset({ActionKind.WRITE, ActionKind.SHELL, ActionKind.FORUM_POST})


@dataclass
class PolicyDecision:
    action: ActionKind
    allowed: bool
    reason: str


class AutopilotPolicy:
    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.autopilot_enabled

    def allowed_actions(self) -> list[str]:
        actions = set(_PASSIVE)
        if self.enabled:
            actions |= _AUTOPILOT
        return sorted(a.value for a in actions)

    def evaluate(self, action: ActionKind) -> PolicyDecision:
        if action == ActionKind.DESTRUCTIVE:
            return PolicyDecision(
                action,
                allowed=False,
                reason="Destructive actions always require explicit confirmation",
            )
        if action in _PASSIVE:
            return PolicyDecision(action, allowed=True, reason="Passive action always allowed")
        if action in _AUTOPILOT:
            if self.enabled:
                return PolicyDecision(action, allowed=True, reason="Autopilot enabled")
            return PolicyDecision(
                action,
                allowed=False,
                reason="Autopilot disabled — suggestion only",
            )
        return PolicyDecision(action, allowed=False, reason="Unknown action kind")

    def allows(self, action: ActionKind) -> bool:
        return self.evaluate(action).allowed
