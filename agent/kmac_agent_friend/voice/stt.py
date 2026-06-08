"""Local speech-to-text via mlx-whisper (optional dependency)."""

from __future__ import annotations

import asyncio
import importlib.util
import tempfile
from dataclasses import dataclass
from pathlib import Path

INSTALL_HINT = (
    "mlx-whisper not installed. On Apple Silicon run: "
    "pip install -e '.[voice]'"
)


@dataclass
class TranscribeResult:
    ok: bool
    text: str = ""
    language: str = ""
    error: str = ""


def mlx_whisper_available() -> bool:
    return importlib.util.find_spec("mlx_whisper") is not None


def _transcribe_sync(wav_bytes: bytes, model: str) -> TranscribeResult:
    if not mlx_whisper_available():
        return TranscribeResult(ok=False, error=INSTALL_HINT)

    import mlx_whisper  # type: ignore[import-untyped]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = Path(tmp.name)

    try:
        result = mlx_whisper.transcribe(str(tmp_path), path_or_hf_repo=model)
        text = (result.get("text") or "").strip()
        language = result.get("language") or ""
        if not text:
            return TranscribeResult(ok=False, error="No speech detected in audio")
        return TranscribeResult(ok=True, text=text, language=language)
    except Exception as exc:
        return TranscribeResult(ok=False, error=str(exc))
    finally:
        tmp_path.unlink(missing_ok=True)


async def transcribe_wav(wav_bytes: bytes, *, model: str) -> TranscribeResult:
    return await asyncio.to_thread(_transcribe_sync, wav_bytes, model)
