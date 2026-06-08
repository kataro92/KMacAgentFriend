# WISHLIST — Cursor-only improvements

Items here are **not** implemented by the agent at runtime. Use Cursor sessions to pick these up.

Priority: **P0** (next) · **P1** (soon) · **P2** (later)

---

## Phase 1 — Voice

- [x] **P0** Integrate mlx-whisper sidecar for EN + VI STT
- [x] **P0** Push-to-talk global hotkey (Swift)
- [x] **P1** Wake word (Porcupine or openWakeWord)
- [x] **P1** Local TTS via `say` + Vietnamese voice selection
- [x] **P1** Barge-in: stop TTS when user speaks

## Phase 2 — Tools & safety

- [x] **P0** Sandboxed file tools (project dirs + `~/Library/Application Support/KMacAgentFriend/sandbox`)
- [x] **P0** Confirmation sheet in Swift for destructive actions
- [x] **P0** Accessibility text injection (AXUIElement)
- [x] **P1** CLI-first tool layer (git, docker via shell before MCP)
- [x] **P1** Command blocklist (`sudo`, `rm -rf`, etc.)

## Phase 3 — Memory & agent core

- [x] **P0** SQLite conversation history
- [x] **P1** ChromaDB long-term memory + Ollama embeddings
- [x] **P1** Ollama chat runner with tool loop
- [x] **P2** Knowledge domain files + ingestion worker
- [x] **P2** Reincarnation export/import

## Phase 4 — Vision

- [x] **P1** Camera confirm gate (voice + click)
- [x] **P1** Ollama VLM (llava / moondream) on-demand
- [x] **P2** No frame persistence by default

## Phase 5 — Background & forum

- [x] **P1** Background worker with menu bar activity indicator
- [x] **P1** Moltbook client (fresh implementation)
- [x] **P1** Forum content sanitizer
- [x] **P2** Career missions port
- [x] **P2** Autopilot policy UI

## UI / gadget

- [x] **P0** Pixel robot HUD head with status stats
- [x] **P1** Full dashboard panel (brain, limbs, chat, knowledge)
- [x] **P1** Sprite states: idle, listening, thinking, acting, error
- [x] **P2** Focus mode fullscreen avatar

## macOS integration

- [x] **P2** SMAppService daemon lifecycle
- [x] **P2** Keychain for API keys
- [x] **P2** Shortcuts app integration
- [x] **P2** Calendar + Reminders Swift sidecar

## Developer experience

- [x] **P0** `make dev` — start daemon + print token
- [x] **P1** Mock daemon for Swift UI without Ollama
- [x] **P1** GitHub Actions: pytest + swift build
- [x] **P2** Spec template generator script

## Performance (16 GB RAM)

- [x] **P1** Pin Ollama models: chat, embed, optional VLM
- [x] **P1** Avoid concurrent STT + LLM + VLM without queue
- [x] **P2** MCP supervisor process pool

## Security

- [x] **P1** Security audit of sandbox paths
- [x] **P2** Rate limits on tool execution
- [x] **P2** Decision audit log UI

---

*Add new items at the top of the relevant section. Mark done with `[x]`.*
