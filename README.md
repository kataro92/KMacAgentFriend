# KMacAgentFriend

A **Mac-native personal AI agent** — menu bar gadget with a Python brain. Voice-first, 100% local (Ollama), learns in the background, and participates in AI forums.

**Platform:** macOS 14+, Apple Silicon M1+ (16 GB RAM reference)

## Architecture

```
Swift gadget shell (menu bar + HUD)  ←WebSocket→  Python daemon (agent core)
```

## Prerequisites

- macOS 14+ on Apple Silicon
- Python 3.11+
- [Ollama](https://ollama.com) (for later phases)
- Xcode 15+ (for the Swift app)
- Optional: [XcodeGen](https://github.com/yonaskolb/XcodeGen) (`brew install xcodegen`)

## Quick start (Phase 1)

### 1. Python daemon

```bash
# From the repository root
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m kmac_agent_friend.main
```

Daemon listens on `http://127.0.0.1:18750` by default. The API token is printed on first start (or set `KAF_API_TOKEN` in `.env`).

### 2. Verify health

```bash
source .env
curl -sf -H "Authorization: Bearer $KAF_API_TOKEN" http://127.0.0.1:18750/health | jq
```

### 3. Swift app (menu bar)

```bash
cd KMacAgentFriendApp
xcodegen generate   # if using XcodeGen
open KMacAgentFriend.xcodeproj
```

Build and run in Xcode. The app **starts the Python daemon automatically** on launch and stops it when you quit. The menu bar icon shows connection status.

If the repo lives on an external drive, macOS may ask you to **choose the project folder once** (Settings → Choose project folder…) so the app can run `.venv`.

For a one-off daemon in Terminal (optional): `make dev`

### 4. Voice (optional)

```bash
pip install -e ".[voice]"   # mlx-whisper for local STT (Apple Silicon)
```

Hold **Right Option** or use **Hold to Talk** in the menu bar. Audio is transcribed locally, sent to Ollama, and spoken via macOS `say`. Enable **Wake word** in the menu bar for hands-free turns; speaking or pressing PTT during a reply **barges in** and stops playback.

### 5. Long-term memory & knowledge (optional)

```bash
ollama pull nomic-embed-text          # local embeddings
pip install -e ".[memory]"            # ChromaDB backend (SQLite fallback otherwise)
```

Drop reference files under `data/knowledge/<domain>/` in the project folder and run ingestion (`POST /api/knowledge/ingest`). Memories and conversations can be exported/imported as a portable "reincarnation" bundle.

### Run without Ollama (UI dev)

Set `MOCK_MODE=true` in `.env` to serve canned replies so the Swift UI works end-to-end without a local model.

### Dev script

```bash
./scripts/dev_run.sh
```

## Project docs


| File                                                                         | Purpose                             |
| ---------------------------------------------------------------------------- | ----------------------------------- |
| `[AGENTS.md](AGENTS.md)`                                                     | Instructions for Cursor / AI agents |
| `[WISHLIST.md](WISHLIST.md)`                                                 | Cursor-only improvement backlog     |
| `[specs/00-overview.md](specs/00-overview.md)`                               | Product and technical overview      |
| `[specs/technical/TR-ipc-websocket.md](specs/technical/TR-ipc-websocket.md)` | IPC contract (Phase 0)              |

New specs cover long-term memory, knowledge ingestion, reincarnation, missions/autopilot, performance, MCP supervisor, security, mock mode, and macOS integration — see `specs/technical/`.

Generate a new spec from the template: `make spec KIND=technical SLUG=my-feature TITLE="My feature"`.


## License

Private / TBD — see repository settings.