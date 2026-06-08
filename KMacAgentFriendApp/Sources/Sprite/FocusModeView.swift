import SwiftUI

/// A distraction-free, large avatar window that mirrors the agent's live state
/// and shows the latest exchange. Toggle fullscreen with the green window button.
struct FocusModeView: View {
    @EnvironmentObject private var connection: DaemonConnection
    @EnvironmentObject private var voice: VoiceSession

    private var state: SpriteState { SpriteState(agentStatus: connection.agentStatus) }

    var body: some View {
        ZStack {
            CyberTheme.background.ignoresSafeArea()
            RadialGradient(
                colors: [state.tint.opacity(0.18), .clear],
                center: .center,
                startRadius: 10,
                endRadius: 400
            )
            .ignoresSafeArea()

            VStack(spacing: 32) {
                Spacer()
                AgentSprite(state: state, size: 240)

                if let transcript = connection.lastTranscript, !transcript.isEmpty {
                    Text(transcript)
                        .font(CyberFont.body)
                        .foregroundStyle(CyberTheme.mutedForeground)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: 600)
                }
                if let reply = connection.lastReply, !reply.isEmpty {
                    Text(reply)
                        .font(.system(.title3, design: .monospaced))
                        .foregroundStyle(CyberTheme.foreground)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: 600)
                        .transition(.opacity)
                }

                Spacer()

                HStack(spacing: 16) {
                    Button(voice.isRecording ? "RELEASE TO SEND" : "HOLD TO TALK") {}
                        .buttonStyle(CyberButtonStyle(variant: voice.isRecording ? .glitch : .default))
                        .simultaneousGesture(
                            DragGesture(minimumDistance: 0)
                                .onChanged { _ in
                                    if !voice.isRecording { Task { await voice.beginPTT() } }
                                }
                                .onEnded { _ in Task { await voice.endPTT() } }
                        )
                    Button("Replay") { Task { await voice.replayLastReply() } }
                        .buttonStyle(CyberButtonStyle(variant: .outline))
                        .disabled(!voice.canReplayLastReply)
                }
                .padding(.bottom, 40)
            }
            .animation(.easeInOut, value: connection.lastReply)
        }
        .frame(minWidth: 480, minHeight: 520)
    }
}
