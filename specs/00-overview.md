# KMacAgentFriend — Overview

## Purpose

Mac-native personal AI agent: **menu bar gadget** (Swift) + **Python daemon** (Ollama, tools, memory). Voice-first Siri-like UX, 100% local, grows capabilities over time.

## Confirmed requirements (summary)

| Area | Decision |
|------|----------|
| Platform | macOS M1+, 16 GB RAM |
| LLM | Ollama only (local) |
| Voice | PTT + wake word; English + Vietnamese |
| UI | Pixel robot HUD + optional full panel |
| Camera | On-demand; voice or click confirm |
| Safety | Auto-write in sandbox/projects only; always confirm destructive |
| Background | Learn + missions + forum; visible activity indicator |
| Self-code | Out — use `WISHLIST.md` + Cursor |
| Repo | Standalone — not KMacAgent |

## Repository layout

```
KMacAgentFriend/
├── KMacAgentFriendApp/       # Swift menu bar app
├── agent/kmac_agent_friend/  # Python daemon
├── specs/                    # Requirements (this folder)
├── scripts/
├── tests/
├── AGENTS.md
└── WISHLIST.md
```

## Build phases

| Phase | Deliverable |
|-------|-------------|
| **0** | Daemon + IPC + menu bar connection status |
| **1** | Voice loop (PTT, STT, TTS) |
| **2** | Tools + sandbox + Accessibility |
| **3** | Memory + CLI/MCP tools |
| **4** | Camera + VLM |
| **5** | Background + Moltbook |
| **6** | Full dashboard + remaining features |
| 5 | Background + Moltbook |
| 6 | Full dashboard + remaining features |

## Spec index

- [`technical/TR-ipc-websocket.md`](technical/TR-ipc-websocket.md) — Phase 0 IPC
- [`technical/TR-voice-loop.md`](technical/TR-voice-loop.md) — Phase 1 voice
- [`technical/TR-tools-sandbox.md`](technical/TR-tools-sandbox.md) — Phase 2 sandboxed file tools
- [`technical/TR-memory.md`](technical/TR-memory.md) — Phase 3 conversation history
- [`technical/TR-vision.md`](technical/TR-vision.md) — Phase 4 camera + VLM
- [`technical/TR-dashboard.md`](technical/TR-dashboard.md) — Phase 6 dashboard
- [`technical/TR-memory.md`](technical/TR-memory.md) — Phase 3 conversation history
