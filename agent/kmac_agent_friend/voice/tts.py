"""macOS local TTS via the `say` command."""

from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class SpeakResult:
    ok: bool
    voice: str
    error: str = ""


@lru_cache(maxsize=1)
def _installed_voices() -> frozenset[str]:
    proc = subprocess.run(
        ["say", "-v", "?"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return frozenset()
    voices: set[str] = set()
    for line in (proc.stdout or "").splitlines():
        name = line.split("#", 1)[0].strip()
        if name:
            voices.add(name)
    return frozenset(voices)


def _pick_voices(language: str) -> list[str]:
    lang = language.lower()
    installed = _installed_voices()
    if lang.startswith("vi"):
        candidates = ["Linh", "Mai", "Samantha"]
    else:
        candidates = ["Samantha", "Alex", "Daniel"]
    ordered = [v for v in candidates if v in installed]
    if ordered:
        return ordered
    if installed:
        return [next(iter(installed))]
    return []


def _run_say(text: str, voice: str | None) -> subprocess.CompletedProcess[str]:
    cmd = ["say"]
    if voice:
        cmd.extend(["-v", voice])
    cmd.append(text)
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


async def speak_text(text: str, *, language: str = "en") -> SpeakResult:
    cleaned = text.strip()
    if not cleaned:
        return SpeakResult(ok=False, voice="", error="Empty text")

    voices = _pick_voices(language)
    last_err = "No macOS voices available"

    def _try_all() -> SpeakResult:
        nonlocal last_err
        for voice in voices:
            proc = _run_say(cleaned, voice)
            if proc.returncode == 0:
                return SpeakResult(ok=True, voice=voice)
            last_err = (proc.stderr or proc.stdout or "say failed").strip()
        proc = _run_say(cleaned, None)
        if proc.returncode == 0:
            return SpeakResult(ok=True, voice="default")
        last_err = (proc.stderr or proc.stdout or last_err).strip()
        return SpeakResult(ok=False, voice=voices[0] if voices else "", error=last_err)

    return await asyncio.to_thread(_try_all)
