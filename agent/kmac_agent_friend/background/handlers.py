"""Background tick handlers for autonomous tasks (forum, missions)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from kmac_agent_friend.autopilot import ActionKind, AutopilotPolicy, DecisionAuditLog
from kmac_agent_friend.config import Settings
from kmac_agent_friend.forum import MoltbookClient
from kmac_agent_friend.missions import MissionStatus, MissionStore

logger = logging.getLogger(__name__)

TickHandler = Callable[[], Awaitable[None]]


def build_forum_handler(settings: Settings) -> TickHandler:
    async def on_tick() -> None:
        client = MoltbookClient(settings.moltbook_url)
        feed = await client.fetch_feed()
        DecisionAuditLog.from_settings(settings).record(
            "forum_check",
            allowed=True,
            reason="Read-only feed poll",
            summary=f"Polled forum: {'ok' if feed.ok else feed.error}",
            detail={"posts": len(feed.posts)},
        )

    return on_tick


def build_mission_handler(settings: Settings) -> TickHandler:
    """Advance the next active mission, honoring the autopilot policy."""

    async def on_tick() -> None:
        store = MissionStore.from_settings(settings)
        audit = DecisionAuditLog.from_settings(settings)
        policy = AutopilotPolicy(settings)

        mission = store.next_active()
        if mission is None:
            audit.record(
                "mission_advance",
                allowed=True,
                reason="No active missions",
                summary="Idle — no missions to advance",
            )
            return

        decision = policy.evaluate(ActionKind.WRITE)
        if not decision.allowed:
            # Suggestion-only: log a recommendation but make no autonomous change.
            audit.record(
                "mission_advance",
                allowed=False,
                reason=decision.reason,
                summary=f"Suggest progressing mission: {mission.title}",
                detail={"mission_id": mission.id},
            )
            store.update(
                mission.id,
                note="Autopilot off — suggested next step (no autonomous action taken)",
            )
            return

        # Autopilot enabled: take a small, safe step toward the goal.
        new_progress = min(100, mission.progress + 10)
        status = MissionStatus.DONE if new_progress >= 100 else MissionStatus.ACTIVE
        store.update(
            mission.id,
            status=status,
            progress=new_progress,
            note=f"Autopilot advanced progress to {new_progress}%",
        )
        audit.record(
            "mission_advance",
            allowed=True,
            reason=decision.reason,
            summary=f"Advanced mission '{mission.title}' to {new_progress}%",
            detail={"mission_id": mission.id, "progress": new_progress},
        )

    return on_tick


def build_tick_handler(task: str, settings: Settings) -> TickHandler | None:
    if task in {"missions", "mission"}:
        return build_mission_handler(settings)
    if task in {"moltbook", "forum", "forum-check"}:
        return build_forum_handler(settings)
    return None
