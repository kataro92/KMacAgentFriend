from kmac_agent_friend.config import (
    DEFAULT_DATA_DIR,
    PROJECT_ROOT,
    get_settings,
    migrate_legacy_data_dir,
    resolve_api_token,
)


def test_empty_kaf_data_dir_uses_project_data_folder(monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", "")
    monkeypatch.setenv("KAF_API_TOKEN", "fixed-token")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.kaf_data_dir == DEFAULT_DATA_DIR
    assert settings.kaf_data_dir == PROJECT_ROOT / "data"
    assert settings.kaf_api_token == "fixed-token"


def test_migrate_legacy_data_dir_moves_files(tmp_path):
    from kmac_agent_friend.config import Settings

    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / ".api_token").write_text("legacy-token", encoding="utf-8")
    (legacy / "user_settings.json").write_text("{}", encoding="utf-8")

    target = tmp_path / "data"
    settings = Settings(kaf_data_dir=target)
    assert migrate_legacy_data_dir(settings, legacy_dir=legacy) is True
    assert (target / ".api_token").read_text(encoding="utf-8") == "legacy-token"
    assert not legacy.exists()
    assert migrate_legacy_data_dir(settings, legacy_dir=legacy) is False


def test_empty_kaf_api_token_reads_persisted_file(tmp_path, monkeypatch):
    data_dir = tmp_path / "kaf-data"
    data_dir.mkdir()
    (data_dir / ".api_token").write_text("persisted-token", encoding="utf-8")
    monkeypatch.setenv("KAF_DATA_DIR", str(data_dir))
    monkeypatch.setenv("KAF_API_TOKEN", "")
    get_settings.cache_clear()
    settings = get_settings()
    assert resolve_api_token(settings) == "persisted-token"
