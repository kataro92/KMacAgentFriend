import subprocess
import sys
import time

from kmac_agent_friend.voice.tts import SpeechRegistry


def _spawn_sleeper() -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])


def test_registry_tracks_and_stops():
    registry = SpeechRegistry()
    proc = _spawn_sleeper()
    registry.register(proc)
    assert registry.is_speaking() is True

    stopped = registry.stop_all()
    assert stopped == 1
    # Give the process a moment to die.
    for _ in range(50):
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    assert proc.poll() is not None
    assert registry.is_speaking() is False


def test_stop_all_when_idle():
    registry = SpeechRegistry()
    assert registry.stop_all() == 0
    assert registry.is_speaking() is False


def test_unregister_removes_process():
    registry = SpeechRegistry()
    proc = _spawn_sleeper()
    registry.register(proc)
    registry.unregister(proc)
    assert registry.is_speaking() is False
    proc.terminate()
    proc.wait()
