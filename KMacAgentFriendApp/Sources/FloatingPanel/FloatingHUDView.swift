import SwiftUI

/// Compact floating HUD — pixel robot head with live agent status.
struct FloatingHUDView: View {
    @EnvironmentObject private var connection: DaemonConnection
    @EnvironmentObject private var voice: VoiceSession

    var body: some View {
        VStack(spacing: 12) {
            robotHead
            stats
            statusLine
            conversation
        }
        .padding(20)
        .frame(width: 240)
        .frame(minHeight: 280)
    }

    @ViewBuilder
    private var statusLine: some View {
        if voice.isRecording || connection.isListening {
            Text("Listening…")
                .font(.caption)
                .foregroundStyle(.green)
        } else if connection.agentStatus == "thinking" {
            Text("Thinking…")
                .font(.caption)
                .foregroundStyle(.yellow)
        } else if connection.agentStatus == "speaking" {
            Text("Speaking…")
                .font(.caption)
                .foregroundStyle(.blue)
        } else if let msg = voice.statusMessage {
            Text(msg)
                .font(.caption2)
                .foregroundStyle(.orange)
                .multilineTextAlignment(.center)
        }
    }

    @ViewBuilder
    private var conversation: some View {
        if connection.lastTranscript != nil || connection.lastReply != nil {
            VStack(alignment: .leading, spacing: 6) {
                if let transcript = connection.lastTranscript {
                    Text("You: \(transcript)")
                        .font(.caption2)
                        .fixedSize(horizontal: false, vertical: true)
                }
                if let reply = connection.lastReply {
                    Text("Agent: \(reply)")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var robotHead: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(nsColor: .windowBackgroundColor))
                .frame(width: 96, height: 96)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .strokeBorder(headBorderColor, lineWidth: 2)
                )
            VStack(spacing: 8) {
                HStack(spacing: 16) {
                    eye
                    eye
                }
                Rectangle()
                    .fill(Color.primary.opacity(0.6))
                    .frame(width: mouthWidth, height: 4)
            }
        }
        .animation(.easeInOut(duration: 0.2), value: connection.agentStatus)
    }

    private var headBorderColor: Color {
        if voice.isRecording || connection.isListening { return .green }
        if connection.agentStatus == "error" { return .red }
        if connection.status == .connected { return .primary.opacity(0.2) }
        return .orange
    }

    private var mouthWidth: CGFloat {
        connection.agentStatus == "speaking" ? 52 : 40
    }

    private var eye: some View {
        Circle()
            .fill(eyeColor)
            .frame(width: 12, height: 12)
    }

    private var eyeColor: Color {
        switch connection.agentStatus {
        case "listening": return .green
        case "thinking": return .yellow
        case "speaking": return .blue
        case "error": return .red
        default:
            return connection.status == .connected ? .green : .orange
        }
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
