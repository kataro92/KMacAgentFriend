# AGENTS.md — KMacAgentFriend

Instructions for Cursor and other AI coding agents working in this repository.

## What this project is

Mac-only AI agent: **Swift menu bar gadget** + **Python daemon**. Voice-first, local Ollama, background learning, Moltbook forum. Successor inspired by KMacAgent but **this is a separate codebase**.

## Architecture

```
KMacAgentFriendApp/     Swift UI — menu bar, floating HUD, audio/camera (later)
agent/kmac_agent_friend/ Python — FastAPI daemon, agent loop, tools, memory
specs/                  Executable requirements (read before implementing features)
```

IPC: WebSocket + REST on `127.0.0.1` only, Bearer token auth.

## Confirmed constraints (do not violate)

- **macOS M1+ only** — no Windows/Linux/Docker/Intel/iOS code paths
- **100% local LLM** — Ollama only; no cloud LLM/STT/TTS without spec update
- **Camera on-demand** — user must confirm by voice or click before capture
- **Destructive actions** — always require user confirmation
- **Writes** — auto-allowed only in project folders + agent sandbox
- **No autonomous self-coding** — improvements go to `WISHLIST.md`; use Cursor for code changes
- **CLI over MCP** when possible — avoid requiring 21 MCP servers at startup

## Coding conventions

### Python

- Package: `kmac_agent_friend`
- Python 3.11+, type hints, Pydantic for API models
- FastAPI for HTTP/WebSocket
- Run: `python -m kmac_agent_friend.main`
- Test: `pytest`
- Lint: `ruff check agent tests`

### Swift

- macOS 14+, Swift 5.9+, SwiftUI + AppKit where needed (NSPanel, NSStatusItem)
- `LSUIElement = true` — menu bar only, no Dock icon
- Sources under `KMacAgentFriendApp/Sources/`

## Before implementing a feature

1. Read `specs/00-overview.md`
2. Check for a spec in `specs/business/` or `specs/technical/`
3. If no spec exists, draft one before large changes
4. Update acceptance criteria with executable commands

## Dev commands

```bash
# Python daemon
source .venv/bin/activate && python -m kmac_agent_friend.main

# Tests
pytest

# Lint
ruff check agent tests

# Swift (after xcodegen)
cd KMacAgentFriendApp && xcodebuild -scheme KMacAgentFriend -configuration Debug build
```

## Prohibitions

- Do not add cloud API dependencies without updating specs
- Do not bind the daemon to `0.0.0.0`
- Do not commit `.env`, tokens, or `data/` contents
- Do not copy files wholesale from the KMacAgent repo — port behavior, write fresh code
- Do not implement self-modifying agent code in production paths

## Current phase

**Phase 1:** Voice loop — PTT hotkey, mlx-whisper STT, Ollama chat, macOS `say` TTS.
