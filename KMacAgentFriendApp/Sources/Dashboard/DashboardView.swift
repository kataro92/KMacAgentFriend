import SwiftUI

struct DashboardView: View {
    @EnvironmentObject private var connection: DaemonConnection

    var body: some View {
        NavigationSplitView {
            List(selection: .constant("brain")) {
                Section("Agent") {
                    Label("Brain", systemImage: "brain.head.profile").tag("brain")
                    Label("Limbs", systemImage: "hand.raised").tag("limbs")
                }
                Section("Data") {
                    Label("Chat", systemImage: "bubble.left.and.bubble.right").tag("chat")
                    Label("Knowledge", systemImage: "books.vertical").tag("knowledge")
                }
            }
            .navigationSplitViewColumnWidth(min: 160, ideal: 180)
        } detail: {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    brainSection
                    chatSection
                    limbsSection
                    knowledgeSection
                }
                .padding(24)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .frame(minWidth: 640, minHeight: 480)
    }

    private var brainSection: some View {
        GroupBox("Brain") {
            VStack(alignment: .leading, spacing: 8) {
                LabeledContent("Daemon", value: connection.status.rawValue.capitalized)
                LabeledContent("Agent", value: connection.agentStatus)
                LabeledContent("Ollama", value: connection.ollamaReachable ? "online" : "offline")
                if !connection.backgroundTask.isEmpty {
                    LabeledContent("Background", value: connection.backgroundTask)
                }
                if let ms = connection.lastLatencyMs {
                    LabeledContent("WS latency", value: String(format: "%.1f ms", ms))
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var chatSection: some View {
        GroupBox("Chat") {
            VStack(alignment: .leading, spacing: 8) {
                if let transcript = connection.lastTranscript {
                    Text("You: \(transcript)")
                        .textSelection(.enabled)
                }
                if let reply = connection.lastReply {
                    Text("Agent: \(reply)")
                        .foregroundStyle(.secondary)
                        .textSelection(.enabled)
                }
                if connection.lastTranscript == nil && connection.lastReply == nil {
                    Text("No messages yet — use Hold to Talk.")
                        .foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var limbsSection: some View {
        GroupBox("Limbs") {
            VStack(alignment: .leading, spacing: 6) {
                Label("File tools", systemImage: "doc.text")
                Label("Shell (blocklist)", systemImage: "terminal")
                Label("Accessibility inject", systemImage: "keyboard")
                    .foregroundStyle(AXTextInjector.isTrusted ? .primary : .secondary)
                Label("Camera / VLM", systemImage: "camera")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var knowledgeSection: some View {
        GroupBox("Knowledge") {
            Text("Long-term memory and domains — Phase 3+ (ChromaDB, ingestion).")
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
