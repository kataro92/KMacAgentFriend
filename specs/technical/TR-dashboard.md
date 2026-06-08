# TR-dashboard — Control panel (Phase 6)

## Purpose

Unified control panel window: live status, editable agent settings (models, voice, tools), and system info.

## Requirements

**TR-DASH-001** Swift SHALL expose a **Control Panel** window from the menu bar (replaces separate Settings scene).

**TR-DASH-002** Panel SHALL include Overview (status + last turn), Models (Ollama chat/VLM), Voice (Whisper + TTS language), Tools (capabilities + project dirs), System (Ollama host, background, daemon paths).

**TR-DASH-003** Editable settings SHALL persist via `PATCH /api/settings` to `user_settings.json` under the KAF data directory.

**TR-DASH-004** Control Panel SHALL include a **Debug** tab showing timestamped activity (daemon + app), with filter, copy, clear, and auto-scroll.

**TR-DASH-005** Daemon SHALL expose `GET /api/activity` and `POST /api/activity/clear`, and stream `activity` events over WebSocket.

## Acceptance criteria

```bash
cd KMacAgentFriendApp && xcodebuild -scheme KMacAgentFriend -configuration Debug build
```
