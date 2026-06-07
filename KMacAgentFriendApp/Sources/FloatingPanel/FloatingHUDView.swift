import SwiftUI

/// Compact floating HUD — pixel robot head placeholder (Phase 0).
struct FloatingHUDView: View {
    @EnvironmentObject private var connection: DaemonConnection

    var body: some View {
        VStack(spacing: 16) {
            robotHead
            stats
            Text("Voice & tools — Phase 1+")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(24)
        .frame(width: 220, height: 280)
    }

    private var robotHead: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(nsColor: .windowBackgroundColor))
                .frame(width: 96, height: 96)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .strokeBorder(Color.primary.opacity(0.2), lineWidth: 2)
                )
            VStack(spacing: 8) {
                HStack(spacing: 16) {
                    eye
                    eye
                }
                Rectangle()
                    .fill(Color.primary.opacity(0.6))
                    .frame(width: 40, height: 4)
            }
        }
    }

    private var eye: some View {
        Circle()
            .fill(connection.status == .connected ? Color.green : Color.orange)
            .frame(width: 12, height: 12)
    }

    private var stats: some View {
        VStack(spacing: 4) {
            Text(connection.agentStatus.uppercased())
                .font(.system(.caption, design: .monospaced))
                .fontWeight(.bold)
            if let ms = connection.lastLatencyMs {
                Text(String(format: "%.0f ms", ms))
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
    }
}
