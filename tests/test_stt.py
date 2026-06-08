from unittest.mock import patch

from kmac_agent_friend.voice.stt import (
    FAST_WHISPER_MODEL,
    has_incomplete_download,
    is_heavy_model,
    is_model_cached,
    normalize_whisper_model,
    resolve_whisper_model,
)


def test_normalize_whisper_model_aliases():
    assert normalize_whisper_model("mlx-community/whisper-small") == (
        "mlx-community/whisper-small-mlx"
    )
    assert normalize_whisper_model("mlx-community/whisper-small-mlx") == (
        "mlx-community/whisper-small-mlx"
    )


def test_is_heavy_model():
    assert is_heavy_model("mlx-community/whisper-large-v3-turbo") is True
    assert is_heavy_model("mlx-community/whisper-small-mlx") is False


def test_resolve_whisper_falls_back_when_large_not_cached():
    configured = "mlx-community/whisper-large-v3-turbo"
    with (
        patch("kmac_agent_friend.voice.stt.is_model_warmed", return_value=False),
        patch("kmac_agent_friend.voice.stt.is_model_cached", return_value=False),
        patch("kmac_agent_friend.voice.stt.has_incomplete_download", return_value=True),
    ):
        model, note = resolve_whisper_model(configured)
    assert model == FAST_WHISPER_MODEL
    assert note is not None
    assert "download in progress" in note


def test_resolve_whisper_keeps_cached_heavy_model():
    configured = "mlx-community/whisper-large-v3-turbo"
    with (
        patch("kmac_agent_friend.voice.stt.is_model_warmed", return_value=False),
        patch("kmac_agent_friend.voice.stt.is_model_cached", return_value=True),
    ):
        model, note = resolve_whisper_model(configured)
    assert model == configured
    assert note is None


def test_has_incomplete_download_false_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "kmac_agent_friend.voice.stt._hf_model_cache_path",
        lambda _model: tmp_path,
    )
    assert has_incomplete_download("mlx-community/whisper-large-v3-turbo") is False


def test_is_model_cached_detects_weights(tmp_path, monkeypatch):
    snapshot = tmp_path / "snapshots" / "abc"
    snapshot.mkdir(parents=True)
    (snapshot / "weights.safetensors").write_bytes(b"x")
    monkeypatch.setattr(
        "kmac_agent_friend.voice.stt._hf_model_cache_path",
        lambda _model: tmp_path,
    )
    assert is_model_cached("mlx-community/whisper-small-mlx") is True


def test_is_model_cached_detects_npz(tmp_path, monkeypatch):
    snapshot = tmp_path / "snapshots" / "abc"
    snapshot.mkdir(parents=True)
    (snapshot / "weights.npz").write_bytes(b"x")
    monkeypatch.setattr(
        "kmac_agent_friend.voice.stt._hf_model_cache_path",
        lambda _model: tmp_path,
    )
    assert is_model_cached("mlx-community/whisper-small-mlx") is True


def test_whisper_availability_needs_download(tmp_path, monkeypatch):
    from kmac_agent_friend.voice.stt import whisper_availability

    monkeypatch.setattr(
        "kmac_agent_friend.voice.stt._hf_model_cache_path",
        lambda _model: tmp_path,
    )
    status = whisper_availability("mlx-community/whisper-small-mlx")
    assert status["needs_download"] is True
    assert status["cached"] is False
