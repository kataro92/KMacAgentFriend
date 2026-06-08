import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var connection: DaemonConnection

    var body: some View {
        Form {
            Section("Daemon") {
                LabeledContent("Host", value: "127.0.0.1:18750")
                LabeledContent("Connection", value: connection.status.rawValue)
                LabeledContent("Token", value: tokenPreview)
            }
            Section("About") {
                Text("KMacAgentFriend v0.1.0 — Phase 1")
                Text("Start daemon: make dev")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .frame(width: 420, height: 240)
    }

    private var tokenPreview: String {
        let path = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/KMacAgentFriend/.api_token")
        guard let token = try? String(contentsOf: path, encoding: .utf8), token.count > 8 else {
            return "not found — run daemon"
        }
        return String(token.prefix(4)) + "…" + String(token.suffix(4))
    }
}
