import SwiftUI

struct MenuBarView: View {
    @EnvironmentObject private var connection: DaemonConnection
    @EnvironmentObject private var voice: VoiceSession
    @EnvironmentObject private var daemonProcess: DaemonProcessManager
    @Environment(\.openWindow) private var openWindow
    @State private var showCameraConfirm = false
    @State private var visionStatus: String?
    private let camera = CameraCapture()
    private let daemon = DaemonClient()

    var body: some View {
        VStack(alignment: .leading, spacing: CyberTheme.spacing * 1.5) {
            header
            CyberCard(title: "LINK STATUS", variant: .holographic) {
                statusSection
            }
            CyberCard(title: "VOICE UPLINK", variant: .terminal) {
                voiceSection
            }
            CyberCard(title: "ACTIONS") {
                actions
            }
            CyberDivider()
            footer
        }
        .padding(16)
        .frame(width: CyberTheme.panelWidth)
        .cyberScreen()
        .task {
            if connection.status == .disconnected {
                connection.connect()
            }
        }
        .sheet(item: Binding(
            get: { connection.pendingConfirmation },
            set: { connection.pendingConfirmation = $0 }
        )) { request in
            ConfirmationSheet(
                request: request,
                onApprove: { Task { await connection.respondToConfirmation(approved: true) } },
                onDeny: { Task { await connection.respondToConfirmation(approved: false) } }
            )
        }
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 12) {
            AgentSprite(state: SpriteState(agentStatus: connection.agentStatus), size: 44)
            VStack(alignment: .leading, spacing: 4) {
                Text("KMACAGENT")
                    .font(CyberFont.heading(18))
                    .tracking(3)
                    .foregroundStyle(CyberTheme.foreground)
                    .cyberGlitchText()
                HStack(spacing: 4) {
                    Text("NODE ONLINE")
                        .font(CyberFont.label)
                        .foregroundStyle(CyberTheme.mutedForeground)
                    BlinkingCursor()
                }
            }
        }
    }

    private var statusSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                CyberBadge(text: connection.status.rawValue, color: statusColor)
                Spacer()
                CyberBadge(
                    text: connection.ollamaReachable ? "OLLAMA OK" : "OLLAMA DOWN",
                    color: connection.ollamaReachable ? CyberTheme.accent : CyberTheme.destructive
                )
            }
            CyberStatusRow(label: "Agent", value: connection.agentStatus, color: CyberTheme.statusColor(for: connection.agentStatus))
            if connection.agentStatus == "background", !connection.backgroundTask.isEmpty {
                CyberStatusRow(label: "Task", value: connection.backgroundTask, color: CyberTheme.accentSecondary)
            }
            if let ms = connection.lastLatencyMs {
                CyberStatusRow(label: "Latency", value: String(format: "%.1f ms", ms), color: CyberTheme.accentTertiary)
            }
            if let err = daemonProcess.lastError ?? connection.errorMessage {
                CyberPromptLine(prefix: "!", text: err)
                    .foregroundStyle(CyberTheme.destructive)
            }
        }
    }

    private var voiceSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                HoldToTalkButton()
                ReplayLastButton()
            }
            Text("HOTKEY: HOLD RIGHT ⌥ OPTION")
                .font(CyberFont.label)
                .foregroundStyle(CyberTheme.mutedForeground)
                .tracking(1)
            if let msg = voice.statusMessage {
                CyberPromptLine(prefix: ">", text: msg)
            }
            if let progress = connection.voiceProgressMessage {
                CyberPromptLine(prefix: "…", text: progress, muted: true)
            }
            if let transcript = connection.lastTranscript {
                CyberPromptLine(prefix: "YOU>", text: transcript)
            }
            if let reply = connection.lastReply {
                CyberPromptLine(prefix: "AGENT>", text: reply, muted: true)
            }
        }
    }

    private var statusColor: Color {
        switch connection.status {
        case .connected: return CyberTheme.accent
        case .connecting: return CyberTheme.accentTertiary
        case .error: return CyberTheme.destructive
        case .disconnected: return CyberTheme.mutedForeground
        }
    }

    private var actions: some View {
        VStack(alignment: .leading, spacing: 8) {
            Button("Capture Vision") { showCameraConfirm = true }
                .buttonStyle(CyberButtonStyle(variant: .outline, fullWidth: true))
            if let visionStatus {
                CyberPromptLine(prefix: ">", text: visionStatus, muted: true)
            }
            Button("Inject Test Text") {
                _ = AXTextInjector.inject("Hello from KMacAgentFriend")
            }
            .buttonStyle(CyberButtonStyle(variant: .ghost, fullWidth: true))
            .disabled(!AXTextInjector.isTrusted)
            HStack(spacing: 8) {
                Button("Focus Mode") { openWindow(id: "focus-mode") }
                    .buttonStyle(CyberButtonStyle(variant: .outline, fullWidth: true))
                Button("Autopilot") { openWindow(id: "autopilot") }
                    .buttonStyle(CyberButtonStyle(variant: .outline, fullWidth: true))
            }
            Toggle("Wake word", isOn: Binding(
                get: { voice.wakeWordEnabled },
                set: { voice.setWakeWord(enabled: $0) }
            ))
            .toggleStyle(.switch)
            .tint(CyberTheme.accent)
            .font(CyberFont.label)
            .foregroundStyle(CyberTheme.mutedForeground)
            Button("Reconnect") { connection.reconnect() }
                .buttonStyle(CyberButtonStyle(variant: .secondary, fullWidth: true))
        }
        .confirmationDialog(
            "Use the camera for vision analysis?",
            isPresented: $showCameraConfirm,
            titleVisibility: .visible
        ) {
            Button("Allow") { Task { await runVisionCapture() } }
            Button("Cancel", role: .cancel) {}
        }
    }

    private func runVisionCapture() async {
        visionStatus = "Capturing…"
        do {
            let jpeg = try await camera.captureJPEG()
            visionStatus = "Analyzing…"
            let result = try await daemon.submitVisionAnalyze(
                jpeg: jpeg,
                prompt: "Describe what you see.",
                confirmed: true
            )
            if result.ok, let description = result.description {
                connection.lastReply = description
                visionStatus = nil
            } else {
                visionStatus = result.error ?? "Vision failed."
            }
        } catch {
            visionStatus = error.localizedDescription
        }
    }

    private var footer: some View {
        HStack(spacing: 8) {
            Button("Control Panel") {
                openWindow(id: "control-panel")
            }
            .buttonStyle(CyberButtonStyle(variant: .default))
            Spacer()
            Button("Quit") { NSApplication.shared.terminate(nil) }
                .buttonStyle(CyberButtonStyle(variant: .destructive))
        }
    }
}

private struct ReplayLastButton: View {
    @EnvironmentObject private var voice: VoiceSession

    var body: some View {
        Button {
            Task { await voice.replayLastReply() }
        } label: {
            Image(systemName: voice.isReplaying ? "speaker.wave.3.fill" : "speaker.wave.2.fill")
                .font(.system(size: 13, weight: .semibold))
                .frame(width: 36, height: 36)
        }
        .buttonStyle(CyberButtonStyle(variant: .outline))
        .disabled(!voice.canReplayLastReply)
        .help("Replay last response")
    }
}

private struct HoldToTalkButton: View {
    @EnvironmentObject private var voice: VoiceSession

    var body: some View {
        Button {
            // Tap toggles for accessibility without hotkey
        } label: {
            Text(voice.isRecording ? "RELEASE TO SEND" : "HOLD TO TALK")
        }
        .buttonStyle(CyberButtonStyle(variant: voice.isRecording ? .glitch : .default, fullWidth: true))
        .frame(maxWidth: .infinity)
        .simultaneousGesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in
                    if !voice.isRecording {
                        Task { await voice.beginPTT() }
                    }
                }
                .onEnded { _ in
                    Task { await voice.endPTT() }
                }
        )
    }
}
