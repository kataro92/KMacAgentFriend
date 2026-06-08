import pytest
from kmac_agent_friend.missions import MissionStatus, MissionStore


def test_create_and_get(tmp_path):
    store = MissionStore(tmp_path / "m.db")
    mission = store.create("Learn the codebase", "Index all project files")
    assert mission.title == "Learn the codebase"
    assert mission.status == MissionStatus.PENDING
    assert mission.progress == 0
    fetched = store.get(mission.id)
    assert fetched is not None
    assert fetched.id == mission.id


def test_create_requires_title(tmp_path):
    store = MissionStore(tmp_path / "m.db")
    with pytest.raises(ValueError):
        store.create("   ")


def test_update_status_progress_note(tmp_path):
    store = MissionStore(tmp_path / "m.db")
    mission = store.create("Task")
    updated = store.update(
        mission.id, status=MissionStatus.ACTIVE, progress=150, note="started work"
    )
    assert updated is not None
    assert updated.status == MissionStatus.ACTIVE
    assert updated.progress == 100  # clamped
    assert any("started work" in n for n in updated.notes)


def test_list_filter_and_next_active(tmp_path):
    store = MissionStore(tmp_path / "m.db")
    a = store.create("A")
    b = store.create("B")
    store.update(b.id, status=MissionStatus.ACTIVE)

    pending = store.list(status=MissionStatus.PENDING)
    assert [m.id for m in pending] == [a.id]

    nxt = store.next_active()
    assert nxt is not None
    assert nxt.id == b.id  # active beats pending


def test_delete(tmp_path):
    store = MissionStore(tmp_path / "m.db")
    mission = store.create("Temp")
    assert store.delete(mission.id) is True
    assert store.get(mission.id) is None
    assert store.delete("nonexistent") is False
