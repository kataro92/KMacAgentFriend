# WISHLIST — Cursor-only improvements

Items here are **not** implemented by the agent at runtime. Use Cursor sessions to pick these up.

Priority: **P0** (next) · **P1** (soon) · **P2** (later)

---

## Phase 1 — Voice

- [ ] **P0** Integrate mlx-whisper sidecar for EN + VI STT
- [ ] **P0** Push-to-talk global hotkey (Swift)
- [ ] **P1** Wake word (Porcupine or openWakeWord)
- [ ] **P1** Local TTS via `say` + Vietnamese voice selection
- [ ] **P1** Barge-in: stop TTS when user speaks

## Phase 2 — Tools & safety

- [ ] **P0** Sandboxed file tools (project dirs + `~/Library/Application Support/KMacAgentFriend/sandbox`)
- [ ] **P0** Confirmation sheet in Swift for destructive actions
- [ ] **P0** Accessibility text injection (AXUIElement)
- [ ] **P1** CLI-first tool layer (git, docker via shell before MCP)
- [ ] **P1** Command blocklist (`sudo`, `rm -rf`, etc.)

## Phase 3 — Memory & agent core

- [ ] **P0** SQLite conversation history
- [ ] **P1** ChromaDB long-term memory + Ollama embeddings
- [ ] **P1** Ollama chat runner with tool loop
- [ ] **P2** Knowledge domain files + ingestion worker
- [ ] **P2** Reincarnation export/import

## Phase 4 — Vision

- [ ] **P1** Camera confirm gate (voice + click)
- [ ] **P1** Ollama VLM (llava / moondream) on-demand
- [ ] **P2** No frame persistence by default

## Phase 5 — Background & forum

- [ ] **P1** Background worker with menu bar activity indicator
- [ ] **P1** Moltbook client (fresh implementation)
- [ ] **P1** Forum content sanitizer
- [ ] **P2** Career missions port
- [ ] **P2** Autopilot policy UI

## UI / gadget

- [ ] **P0** Pixel robot HUD head with status stats
- [ ] **P1** Full dashboard panel (brain, limbs, chat, knowledge)
- [ ] **P1** Sprite states: idle, listening, thinking, acting, error
- [ ] **P2** Focus mode fullscreen avatar

## macOS integration

- [ ] **P2** SMAppService daemon lifecycle
- [ ] **P2** Keychain for API keys
- [ ] **P2** Shortcuts app integration
- [ ] **P2** Calendar + Reminders Swift sidecar

## Developer experience

- [ ] **P0** `make dev` — start daemon + print token
- [ ] **P1** Mock daemon for Swift UI without Ollama
- [ ] **P1** GitHub Actions: pytest + swift build
- [ ] **P2** Spec template generator script

## Performance (16 GB RAM)

- [ ] **P1** Pin Ollama models: chat, embed, optional VLM
- [ ] **P1** Avoid concurrent STT + LLM + VLM without queue
- [ ] **P2** MCP supervisor process pool

## Security

- [ ] **P1** Security audit of sandbox paths
- [ ] **P2** Rate limits on tool execution
- [ ] **P2** Decision audit log UI

---

*Add new items at the top of the relevant section. Mark done with `[x]`.*
