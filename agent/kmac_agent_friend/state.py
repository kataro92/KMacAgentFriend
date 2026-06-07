"""In-memory agent state (per daemon process)."""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field


class AgentStatus(str, enum.Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ACTING = "acting"
    BACKGROUND = "background"
    ERROR = "error"


@dataclass
class AgentState:
    status: AgentStatus = AgentStatus.IDLE
    current_action: str = ""
    started_at: float = field(default_factory=time.time)
    message_count: int = 0
    connected_clients: int = 0
    background_task: str = ""

    def uptime_seconds(self) -> float:
        return time.time() - self.started_at

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "current_action": self.current_action,
            "uptime_seconds": round(self.uptime_seconds(), 1),
            "message_count": self.message_count,
            "connected_clients": self.connected_clients,
            "background_task": self.background_task,
        }


# Singleton for Phase 0 — replace with proper DI later if needed.
agent_state = AgentState()
