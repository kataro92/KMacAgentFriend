import io
import subprocess
import wave
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from kmac_agent_friend.config import get_settings
from kmac_agent_friend.main import app
from kmac_agent_friend.voice.chat import ChatResult
from kmac_agent_friend.voice.stt import TranscribeResult
from kmac_agent_friend.voice.tts import SpeakResult


@pytest.fixture
def token(tmp_path, monkeypatch):
    monkeypatch.setenv("KAF_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KAF_API_TOKEN", "test-token-voice")
    get_settings.cache_clear()
    return "test-token-voice"


def _silent_wav(duration_s: float = 0.2) -> bytes:
    rate = 16_000
    frames = int(rate * duration_s)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x00\x00" * frames)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_voice_speak_ok(token):
    headers = {"Authorization": f"Bearer {token}"}
    with patch(
        "kmac_agent_friend.main.speak_text",
        AsyncMock(return_value=SpeakResult(ok=True, voice="Samantha")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/voice/speak",
                headers=headers,
                json={"text": "Hello"},
            )
    assert response.status_code == 200
    assert response.json()["ok"] is True


@pytest.mark.asyncio
async def test_voice_transcribe_missing_stt(token):
    headers = {"Authorization": f"Bearer {token}"}
    with patch(
        "kmac_agent_friend.main.transcribe_wav",
        AsyncMock(return_value=TranscribeResult(ok=False, error="mlx-whisper not installed")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/voice/transcribe",
                headers=headers,
                files={"file": ("sample.wav", _silent_wav(), "audio/wav")},
            )
    data = response.json()
    assert data["ok"] is False
    assert "mlx-whisper" in data["error"]


@pytest.mark.asyncio
async def test_tts_voice_fallback(monkeypatch):
    from kmac_agent_friend.voice import tts

    tts._installed_voices.cache_clear()
    monkeypatch.setattr(tts, "_installed_voices", lambda: frozenset({"Samantha"}))

    with patch.object(tts, "_run_say") as mock_say:
        mock_say.return_value = subprocess.CompletedProcess(
            args=["say"], returncode=0, stdout="", stderr=""
        )
        result = await tts.speak_text("Hello", language="vi")

    assert result.ok is True
    assert result.voice == "Samantha"
    mock_say.assert_called_once_with("Hello", "Samantha")


@pytest.mark.asyncio
async def test_voice_turn_happy_path(token):
    headers = {"Authorization": f"Bearer {token}"}
    with (
        patch(
            "kmac_agent_friend.main.transcribe_wav",
            AsyncMock(return_value=TranscribeResult(ok=True, text="hi", language="en")),
        ),
        patch(
            "kmac_agent_friend.main.chat_reply",
            AsyncMock(return_value=ChatResult(ok=True, reply="Hello!")),
        ),
        patch(
            "kmac_agent_friend.main.speak_text",
            AsyncMock(return_value=SpeakResult(ok=True, voice="Samantha")),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/voice/turn",
                headers=headers,
                files={"file": ("sample.wav", _silent_wav(), "audio/wav")},
            )
    data = response.json()
    assert data["ok"] is True
    assert data["transcript"] == "hi"
    assert data["reply"] == "Hello!"
    assert data["spoken"] is True
