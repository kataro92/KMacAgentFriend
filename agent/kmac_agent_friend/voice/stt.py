"""Local speech-to-text via mlx-whisper (optional dependency)."""

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import io
import struct
import tempfile
import wave
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

INSTALL_HINT = (
    "mlx-whisper not installed. On Apple Silicon run: "
    "pip install -e '.[voice]'"
)

# Lighter default for Apple Silicon; large-v3-turbo is higher quality but slow to load.
DEFAULT_WHISPER_MODEL = "mlx-community/whisper-small-mlx"
FAST_WHISPER_MODEL = DEFAULT_WHISPER_MODEL

# Legacy / incorrect IDs that do not exist on Hugging Face Hub.
WHISPER_MODEL_ALIASES: dict[str, str] = {
    "mlx-community/whisper-small": "mlx-community/whisper-small-mlx",
    "mlx-community/whisper-base": "mlx-community/whisper-base-mlx",
    "mlx-community/whisper-medium": "mlx-community/whisper-medium-mlx",
    "mlx-community/whisper-large-v3": "mlx-community/whisper-large-v3-mlx",
}


def normalize_whisper_model(model: str) -> str:
    """Map deprecated repo IDs to valid mlx-community checkpoints."""
    stripped = model.strip()
    return WHISPER_MODEL_ALIASES.get(stripped, stripped)

_warmed_model: str | None = None

ProgressCallback = Callable[[str, str, int | None], Awaitable[None]]


@dataclass
class TranscribeResult:
    ok: bool
    text: str = ""
    language: str = ""
    error: str = ""


def mlx_whisper_available() -> bool:
    return importlib.util.find_spec("mlx_whisper") is not None


def is_model_warmed(model: str) -> bool:
    return _warmed_model == normalize_whisper_model(model)


def is_heavy_model(model: str) -> bool:
    lowered = model.lower()
    return "large" in lowered or "medium" in lowered


def _hf_model_cache_path(model: str) -> Path:
    slug = model.replace("/", "--")
    return Path.home() / ".cache/huggingface/hub" / f"models--{slug}"


def is_model_cached(model: str) -> bool:
    """True when weight files exist locally (download complete)."""
    cache_root = _hf_model_cache_path(model)
    snapshots = cache_root / "snapshots"
    if not snapshots.is_dir():
        return False
    for snapshot in snapshots.iterdir():
        if not snapshot.is_dir():
            continue
        weights = list(snapshot.glob("*.safetensors"))
        weights.extend(snapshot.glob("weights/*.safetensors"))
        weights.extend(snapshot.glob("*.npz"))
        weights.extend(snapshot.glob("weights/*.npz"))
        if weights:
            return True
    return False


def whisper_availability(model: str) -> dict[str, object]:
    """Download/cache state for a specific Whisper repo."""
    model = normalize_whisper_model(model)
    cached = is_model_cached(model)
    ready = is_model_warmed(model)
    return {
        "model": model,
        "cached": cached,
        "ready": ready,
        "needs_download": not cached,
    }


def has_incomplete_download(model: str) -> bool:
    blobs = _hf_model_cache_path(model) / "blobs"
    if not blobs.is_dir():
        return False
    return any(blobs.glob("*.incomplete"))


def resolve_whisper_model(configured: str) -> tuple[str, str | None]:
    """Pick the model to run now; fall back to small when heavy weights are missing."""
    configured = normalize_whisper_model(configured)
    if configured == FAST_WHISPER_MODEL or is_model_warmed(configured):
        return configured, None
    if is_model_cached(configured):
        return configured, None
    if is_heavy_model(configured):
        if has_incomplete_download(configured):
            detail = "download in progress"
        elif _hf_model_cache_path(configured).is_dir():
            detail = "download incomplete"
        else:
            detail = "not downloaded"
        return (
            FAST_WHISPER_MODEL,
            f"{configured} ({detail}) — using {FAST_WHISPER_MODEL} for faster response",
        )
    return configured, None


def model_status(configured: str) -> dict[str, object]:
    configured = normalize_whisper_model(configured)
    active, _ = resolve_whisper_model(configured)
    return {
        "configured_model": configured,
        "active_model": active,
        "fast_model": FAST_WHISPER_MODEL,
        "configured_cached": is_model_cached(configured),
        "active_ready": is_model_warmed(active),
        "using_fallback": active != configured,
    }


def _minimal_wav_bytes(sample_rate: int = 16_000, duration_ms: int = 200) -> bytes:
    frame_count = max(1, int(sample_rate * duration_ms / 1000))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack(f"<{frame_count}h", *([0] * frame_count)))
    return buffer.getvalue()


def _transcribe_sync(wav_bytes: bytes, model: str) -> TranscribeResult:
    if not mlx_whisper_available():
        return TranscribeResult(ok=False, error=INSTALL_HINT)

    model = normalize_whisper_model(model)
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
        message = str(exc)
        if "401" in message or "Invalid username or password" in message:
            return TranscribeResult(
                ok=False,
                error=(
                    "Hugging Face authentication failed. Check HF_TOKEN in .env "
                    "(create a read token at huggingface.co/settings/tokens)."
                ),
            )
        if "Repository Not Found" in message or "404" in message:
            resolved = normalize_whisper_model(model)
            if resolved != model:
                hint = f" Did you mean {resolved}?"
            else:
                hint = " Use a valid mlx-community repo (e.g. mlx-community/whisper-small-mlx)."
            return TranscribeResult(
                ok=False,
                error=f"Whisper model not found on Hugging Face.{hint}",
            )
        return TranscribeResult(ok=False, error=message)
    finally:
        tmp_path.unlink(missing_ok=True)


async def transcribe_wav(wav_bytes: bytes, *, model: str) -> TranscribeResult:
    model = normalize_whisper_model(model)
    result = await asyncio.to_thread(_transcribe_sync, wav_bytes, model)
    if result.ok or result.error == "No speech detected in audio":
        global _warmed_model
        _warmed_model = model
    return result


async def _heartbeat(
    on_progress: ProgressCallback | None,
    model: str,
    *,
    interval_seconds: float = 5.0,
) -> None:
    elapsed = 0.0
    while True:
        await asyncio.sleep(interval_seconds)
        elapsed += interval_seconds
        if on_progress is None:
            continue
        if not is_model_warmed(model) and not is_model_cached(model):
            step = "download"
            message = f"Downloading Whisper weights… ({int(elapsed)}s)"
        elif not is_model_warmed(model):
            step = "load"
            message = f"Loading Whisper into memory… ({int(elapsed)}s)"
        else:
            step = "stt"
            message = f"Transcribing speech… ({int(elapsed)}s)"
        await on_progress(step, message, None)


async def transcribe_wav_with_progress(
    wav_bytes: bytes,
    *,
    model: str,
    on_progress: ProgressCallback | None = None,
    timeout_seconds: float | None = None,
) -> TranscribeResult:
    if on_progress:
        await on_progress("stt", f"Starting Whisper ({model})", None)
        if not is_model_warmed(model):
            if not is_model_cached(model):
                await on_progress(
                    "download",
                    f"First run: downloading {model} "
                    "(use whisper-small in Settings for speed)",
                    0,
                )
            else:
                await on_progress("load", f"Loading {model} into memory", None)

    heartbeat = asyncio.create_task(_heartbeat(on_progress, model))
    try:
        coro = transcribe_wav(wav_bytes, model=model)
        if timeout_seconds is not None:
            result = await asyncio.wait_for(coro, timeout=timeout_seconds)
        else:
            result = await coro
    except TimeoutError:
        return TranscribeResult(
            ok=False,
            error=f"Speech recognition timed out after {int(timeout_seconds or 0)}s",
        )
    finally:
        heartbeat.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat

    if result.ok and on_progress:
        await on_progress("stt", "Transcription complete", 100)
    return result


async def transcribe_for_turn(
    wav_bytes: bytes,
    configured_model: str,
    *,
    on_progress: ProgressCallback | None = None,
) -> tuple[TranscribeResult, str, str | None]:
    """Transcribe with auto-fallback to the fast model when the configured one is slow."""
    configured_model = normalize_whisper_model(configured_model)
    model, fallback_note = resolve_whisper_model(configured_model)
    if fallback_note and on_progress:
        await on_progress("fallback", fallback_note, None)

    timeout = 90.0 if model == FAST_WHISPER_MODEL else 180.0
    result = await transcribe_wav_with_progress(
        wav_bytes,
        model=model,
        on_progress=on_progress,
        timeout_seconds=timeout,
    )

    if (
        not result.ok
        and "timed out" in result.error.lower()
        and model != FAST_WHISPER_MODEL
    ):
        retry_note = f"Timed out on {model}; retrying with {FAST_WHISPER_MODEL}"
        if on_progress:
            await on_progress("fallback", retry_note, None)
        result = await transcribe_wav_with_progress(
            wav_bytes,
            model=FAST_WHISPER_MODEL,
            on_progress=on_progress,
            timeout_seconds=90.0,
        )
        return result, FAST_WHISPER_MODEL, retry_note

    return result, model, fallback_note


async def warm_whisper_model(model: str) -> TranscribeResult:
    """Load weights (and download on first run). Silent clip avoids 'no speech' as failure."""
    model = normalize_whisper_model(model)
    if not mlx_whisper_available():
        return TranscribeResult(ok=False, error=INSTALL_HINT)
    if is_model_warmed(model):
        return TranscribeResult(ok=True, text="", language="")
    return await transcribe_wav(_minimal_wav_bytes(), model=model)
