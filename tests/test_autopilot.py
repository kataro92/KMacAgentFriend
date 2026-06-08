import pytest
from kmac_agent_friend.autopilot import (
    ActionKind,
    AutopilotPolicy,
    DecisionAuditLog,
)
from kmac_agent_friend.background.handlers import build_mission_handler
from kmac_agent_friend.config import Settings
from kmac_agent_friend.missions import MissionStatus, MissionStore


def test_policy_passive_always_allowed(tmp_path):
    settings = Settings(kaf_data_dir=tmp_path, autopilot_enabled=False)
    policy = AutopilotPolicy(settings)
    assert policy.allows(ActionKind.READ)
    assert policy.allows(ActionKind.SUGGEST)
    assert not policy.allows(ActionKind.WRITE)
    assert not policy.allows(ActionKind.DESTRUCTIVE)


def test_policy_autopilot_enabled(tmp_path):
    settings = Settings(kaf_data_dir=tmp_path, autopilot_enabled=True)
    policy = AutopilotPolicy(settings)
    assert policy.allows(ActionKind.WRITE)
    assert policy.allows(ActionKind.SHELL)
    assert policy.allows(ActionKind.FORUM_POST)
    # Destructive never auto-approved, even with autopilot on.
    assert not policy.allows(ActionKind.DESTRUCTIVE)
    assert "write" in policy.allowed_actions()


def test_audit_log_record_and_recent(tmp_path):
    log = DecisionAuditLog(tmp_path / "d.db")
    log.record("test_action", allowed=True, reason="ok", summary="did a thing")
    log.record("other", allowed=False, reason="blocked")
    recent = log.recent()
    assert len(recent) == 2
    assert recent[0]["action"] == "other"
    assert recent[0]["allowed"] is False
    assert recent[1]["summary"] == "did a thing"


@pytest.mark.asyncio
async def test_mission_handler_suggestion_only_when_autopilot_off(tmp_path):
    settings = Settings(kaf_data_dir=tmp_path, autopilot_enabled=False)
    store = MissionStore.from_settings(settings)
    mission = store.create("Goal")
    store.update(mission.id, status=MissionStatus.ACTIVE)

    handler = build_mission_handler(settings)
    await handler()

    refreshed = store.get(mission.id)
    assert refreshed is not None
    assert refreshed.progress == 0  # no autonomous advance
    decisions = DecisionAuditLog.from_settings(settings).recent()
    assert decisions[0]["allowed"] is False


@pytest.mark.asyncio
async def test_mission_handler_advances_when_autopilot_on(tmp_path):
    settings = Settings(kaf_data_dir=tmp_path, autopilot_enabled=True)
    store = MissionStore.from_settings(settings)
    mission = store.create("Goal")
    store.update(mission.id, status=MissionStatus.ACTIVE)

    handler = build_mission_handler(settings)
    await handler()

    refreshed = store.get(mission.id)
    assert refreshed is not None
    assert refreshed.progress == 10
    decisions = DecisionAuditLog.from_settings(settings).recent()
    assert decisions[0]["allowed"] is True
