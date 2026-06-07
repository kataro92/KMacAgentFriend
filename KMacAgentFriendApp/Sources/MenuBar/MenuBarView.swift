import SwiftUI

struct MenuBarView: View {
    @EnvironmentObject private var connection: DaemonConnection
    @State private var showHUD = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            header
            statusSection
            actions
            Divider()
            footer
        }
        .padding()
        .frame(width: 300)
        .onAppear { connection.connect() }
        .sheet(isPresented: $showHUD) {
            FloatingHUDView()
                .environmentObject(connection)
        }
    }

    private var header: some View {
        HStack {
            Image(systemName: "cpu")
                .font(.title2)
            VStack(alignment: .leading) {
                Text("KMacAgentFriend")
                    .font(.headline)
                Text("Phase 0 — gadget shell")
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
            Button("Show HUD") { showHUD = true }
            Button("Reconnect") { connection.reconnect() }
            Button("Open Full Panel…") {
                // Phase 6 — full KMacAgent-style dashboard
            }
            .disabled(true)
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
