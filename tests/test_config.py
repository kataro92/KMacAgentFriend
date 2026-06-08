from kmac_agent_friend.config import DEFAULT_DATA_DIR, get_settings, resolve_api_token


def test_empty_kaf_data_dir_uses_default(monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", "")
    monkeypatch.setenv("KAF_API_TOKEN", "fixed-token")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.kaf_data_dir == DEFAULT_DATA_DIR
    assert settings.kaf_api_token == "fixed-token"


def test_empty_kaf_api_token_reads_persisted_file(tmp_path, monkeypatch):
    data_dir = tmp_path / "kaf-data"
    data_dir.mkdir()
    (data_dir / ".api_token").write_text("persisted-token", encoding="utf-8")
    monkeypatch.setenv("KAF_DATA_DIR", str(data_dir))
    monkeypatch.setenv("KAF_API_TOKEN", "")
    get_settings.cache_clear()
    settings = get_settings()
    assert resolve_api_token(settings) == "persisted-token"
