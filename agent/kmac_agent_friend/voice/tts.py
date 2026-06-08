"""macOS local TTS via the `say` command."""

from __future__ import annotations

import asyncio
import subprocess
import threading
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class SpeakResult:
    ok: bool
    voice: str
    error: str = ""


class SpeechRegistry:
    """Tracks active `say` subprocesses so speech can be interrupted (barge-in)."""

    def __init__(self) -> None:
        self._procs: set[subprocess.Popen] = set()
        self._lock = threading.Lock()

    def register(self, proc: subprocess.Popen) -> None:
        with self._lock:
            self._procs.add(proc)

    def unregister(self, proc: subprocess.Popen) -> None:
        with self._lock:
            self._procs.discard(proc)

    def is_speaking(self) -> bool:
        with self._lock:
            return any(p.poll() is None for p in self._procs)

    def stop_all(self) -> int:
        with self._lock:
            procs = list(self._procs)
            self._procs.clear()
        stopped = 0
        for proc in procs:
            if proc.poll() is None:
                try:
                    proc.terminate()
                    stopped += 1
                except ProcessLookupError:
                    pass
        return stopped


speech_registry = SpeechRegistry()


def stop_speech() -> int:
    """Interrupt any in-progress TTS. Returns the number of processes stopped."""
    return speech_registry.stop_all()


def is_speaking() -> bool:
    return speech_registry.is_speaking()


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
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    speech_registry.register(proc)
    try:
        stdout, stderr = proc.communicate()
    finally:
        speech_registry.unregister(proc)
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


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
