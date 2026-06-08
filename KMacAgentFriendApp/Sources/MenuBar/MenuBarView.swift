import SwiftUI

struct MenuBarView: View {
    @EnvironmentObject private var connection: DaemonConnection
    @EnvironmentObject private var voice: VoiceSession
    @Environment(\.openWindow) private var openWindow
    @State private var showCameraConfirm = false
    @State private var visionStatus: String?
    private let camera = CameraCapture()
    private let daemon = DaemonClient()

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            header
            statusSection
            voiceSection
            actions
            Divider()
            footer
        }
        .padding()
        .frame(width: 300)
        .onAppear { connection.connect() }
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
        HStack {
            Image(systemName: "cpu")
                .font(.title2)
            VStack(alignment: .leading) {
                Text("KMacAgentFriend")
                    .font(.headline)
                Text("Phase 2 — tools & safety")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var statusSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label(connection.status.rawValue.capitalized, systemImage: "circle.fill")
                .foregroundStyle(statusColor)
            HStack {
                Text("Agent:")
                Text(connection.agentStatus)
                    .fontWeight(.medium)
            }
            .font(.caption)
            if connection.agentStatus == "background", !connection.backgroundTask.isEmpty {
                Text("Task: \(connection.backgroundTask)")
                    .font(.caption2)
                    .foregroundStyle(.purple)
            }
            HStack {
                Text("Ollama:")
                Text(connection.ollamaReachable ? "online" : "offline")
                    .foregroundStyle(connection.ollamaReachable ? .green : .orange)
            }
            .font(.caption)
            if let ms = connection.lastLatencyMs {
                Text(String(format: "WS latency: %.1f ms", ms))
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            if let err = connection.errorMessage {
                Text(err)
                    .font(.caption2)
                    .foregroundStyle(.red)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var voiceSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            HoldToTalkButton()
            Text("Hotkey: hold Right ⌥ Option")
                .font(.caption2)
                .foregroundStyle(.secondary)
            if let msg = voice.statusMessage {
                Text(msg)
                    .font(.caption2)
                    .foregroundStyle(.orange)
                    .fixedSize(horizontal: false, vertical: true)
            }
            if let transcript = connection.lastTranscript {
                Text("You: \(transcript)")
                    .font(.caption)
                    .fixedSize(horizontal: false, vertical: true)
            }
            if let reply = connection.lastReply {
                Text("Agent: \(reply)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var statusColor: Color {
        switch connection.status {
        case .connected: return .green
        case .connecting: return .yellow
        case .error: return .red
        case .disconnected: return .gray
        }
    }

    private var actions: some View {
        VStack(alignment: .leading, spacing: 8) {
            Button("Capture Vision…") { showCameraConfirm = true }
            if let visionStatus {
                Text(visionStatus)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Button("Inject Test Text") {
                _ = AXTextInjector.inject("Hello from KMacAgentFriend")
            }
            .disabled(!AXTextInjector.isTrusted)
            Button("Reconnect") { connection.reconnect() }
            Button("Open Full Panel…") {
                openWindow(id: "dashboard")
            }
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
        HStack {
            Button("Settings…") {
                NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
            }
            Spacer()
            Button("Quit") { NSApplication.shared.terminate(nil) }
        }
    }
}

private struct HoldToTalkButton: View {
    @EnvironmentObject private var voice: VoiceSession

    var body: some View {
        Button {
            // Tap toggles for accessibility without hotkey
        } label: {
            Text(voice.isRecording ? "Release to send" : "Hold to Talk")
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(.borderedProminent)
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
