from kmac_agent_friend.config import Settings
from kmac_agent_friend.vision import captures_dir, maybe_persist_frame


def test_no_persistence_by_default(tmp_path):
    settings = Settings(kaf_data_dir=tmp_path)
    assert settings.vision_persist_frames is False
    result = maybe_persist_frame(b"fake-jpeg-bytes", settings)
    assert result is None
    assert not captures_dir(settings).exists()


def test_persist_when_opted_in(tmp_path):
    settings = Settings(kaf_data_dir=tmp_path, vision_persist_frames=True)
    result = maybe_persist_frame(b"fake-jpeg-bytes", settings)
    assert result is not None
    assert result.exists()
    assert result.read_bytes() == b"fake-jpeg-bytes"
    assert result.parent == captures_dir(settings)


def test_persist_skips_empty_frame(tmp_path):
    settings = Settings(kaf_data_dir=tmp_path, vision_persist_frames=True)
    assert maybe_persist_frame(b"", settings) is None
