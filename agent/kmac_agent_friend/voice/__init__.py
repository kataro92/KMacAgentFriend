"""Local voice pipeline — STT, TTS, and Ollama chat."""

from kmac_agent_friend.voice.chat import chat_reply
from kmac_agent_friend.voice.stt import (
    FAST_WHISPER_MODEL,
    is_model_warmed,
    model_status,
    normalize_whisper_model,
    resolve_whisper_model,
    transcribe_for_turn,
    transcribe_wav,
    warm_whisper_model,
    whisper_availability,
)
from kmac_agent_friend.voice.tts import is_speaking, speak_text, stop_speech

__all__ = [
    "FAST_WHISPER_MODEL",
    "chat_reply",
    "is_model_warmed",
    "is_speaking",
    "model_status",
    "normalize_whisper_model",
    "whisper_availability",
    "resolve_whisper_model",
    "speak_text",
    "stop_speech",
    "transcribe_for_turn",
    "transcribe_wav",
    "warm_whisper_model",
]
