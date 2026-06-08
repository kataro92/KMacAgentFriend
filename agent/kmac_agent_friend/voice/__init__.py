"""Local voice pipeline — STT, TTS, and Ollama chat."""

from kmac_agent_friend.voice.chat import chat_reply
from kmac_agent_friend.voice.stt import transcribe_wav
from kmac_agent_friend.voice.tts import speak_text

__all__ = ["chat_reply", "speak_text", "transcribe_wav"]
