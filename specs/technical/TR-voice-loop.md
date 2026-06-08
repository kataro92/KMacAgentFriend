# TR-voice-loop — Voice interaction (Phase 1)

## Purpose

Push-to-talk voice loop: capture audio in Swift, transcribe locally, get an Ollama reply, speak via macOS TTS.

## Requirements

**TR-VOICE-001** Swift SHALL capture microphone audio while PTT is held.

**TR-VOICE-002** PTT SHALL be available via menu bar hold button; global hotkey (Right Option) when Accessibility is granted.

**TR-VOICE-003** Audio SHALL be sent to `POST /api/voice/transcribe` as `audio/wav` multipart.

**TR-VOICE-004** STT SHALL use local mlx-whisper when installed; otherwise return a clear install hint.

**TR-VOICE-005** After transcription, daemon SHALL call Ollama chat and return assistant text.

**TR-VOICE-006** TTS SHALL use macOS `say` via `POST /api/voice/speak` (no cloud TTS).

**TR-VOICE-007** Agent status SHALL transition: `idle` → `listening` → `thinking` → `speaking` → `idle`, broadcast on WebSocket.

**TR-VOICE-008** WebSocket clients MAY send `ptt_start` / `ptt_end` to update state without audio.

**TR-VOICE-009** Swift SHALL offer an optional always-listening wake-word trigger (on-device energy detector; swappable for openWakeWord/Porcupine) that starts a turn hands-free.

**TR-VOICE-010** Barge-in: `POST /api/voice/stop` and the `barge_in` / `ptt_start`-while-speaking WebSocket paths SHALL interrupt in-progress TTS, broadcasting `tts_stopped`.

## Constraints

- SHALL NOT use cloud STT/TTS
- SHALL NOT stream audio over WebSocket in Phase 1 (REST multipart only)
- English + Vietnamese STT via whisper model language auto-detect

## Scenarios

### Scenario: Hold PTT and get spoken reply

```
GIVEN daemon running with Ollama and mlx-whisper available
WHEN user holds PTT, speaks, and releases
THEN transcript and assistant reply appear in the menu bar
AND agent status returns to idle after TTS completes
```

### Scenario: STT unavailable

```
GIVEN mlx-whisper is not installed
WHEN user submits audio for transcription
THEN response SHALL include ok=false and an install hint
AND agent status SHALL return to idle
```

## Acceptance criteria

```bash
# Install voice extras (optional, Apple Silicon)
pip install -e ".[voice]"

# Run tests
pytest tests/test_voice.py -q

# Transcribe (requires TOKEN and a sample WAV)
curl -sf -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample.wav" http://127.0.0.1:18750/api/voice/transcribe | jq

# Speak
curl -sf -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello"}' http://127.0.0.1:18750/api/voice/speak | jq -e '.ok == true'
```

## Not included (Phase 1)

- Streaming STT partial results
- Audio over WebSocket
