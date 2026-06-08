import SwiftUI

/// Visual states for the pixel-robot avatar.
enum SpriteState: String, CaseIterable {
    case idle
    case listening
    case thinking
    case acting
    case error

    /// Map a daemon agent-status string onto a sprite state.
    init(agentStatus: String) {
        switch agentStatus.lowercased() {
        case "listening": self = .listening
        case "thinking": self = .thinking
        case "speaking", "acting", "background": self = .acting
        case "error": self = .error
        default: self = .idle
        }
    }

    var tint: Color {
        switch self {
        case .idle: return CyberTheme.accent
        case .listening: return CyberTheme.accentTertiary
        case .thinking: return CyberTheme.accentSecondary
        case .acting: return Color(hex: 0xffaa00)
        case .error: return CyberTheme.destructive
        }
    }

    var caption: String {
        switch self {
        case .idle: return "READY"
        case .listening: return "LISTENING"
        case .thinking: return "THINKING"
        case .acting: return "WORKING"
        case .error: return "ERROR"
        }
    }
}

/// A pixel robot head whose eyes and antenna animate per state.
struct AgentSprite: View {
    let state: SpriteState
    var size: CGFloat = 96

    @State private var blink = false
    @State private var pulse = false

    private var unit: CGFloat { size / 12 }

    var body: some View {
        VStack(spacing: unit) {
            head
            Text(state.caption)
                .font(CyberFont.label)
                .tracking(2)
                .foregroundStyle(state.tint)
        }
        .onAppear { startAnimations() }
        .onChange(of: state) { _, _ in startAnimations() }
    }

    private var head: some View {
        ZStack {
            // Antenna
            VStack(spacing: 0) {
                Circle()
                    .fill(state.tint)
                    .frame(width: unit, height: unit)
                    .opacity(pulse ? 1 : 0.4)
                Rectangle()
                    .fill(state.tint.opacity(0.6))
                    .frame(width: unit / 2, height: unit)
                Spacer().frame(height: size)
            }

            // Face plate
            RoundedRectangle(cornerRadius: unit)
                .fill(CyberTheme.card)
                .overlay(
                    RoundedRectangle(cornerRadius: unit)
                        .stroke(state.tint, lineWidth: 2)
                )
                .frame(width: size, height: size * 0.85)
                .shadow(color: state.tint.opacity(0.6), radius: pulse ? 12 : 4)

            // Eyes + mouth
            VStack(spacing: unit * 1.2) {
                HStack(spacing: unit * 2) {
                    eye
                    eye
                }
                mouth
            }
        }
        .frame(width: size + unit * 2, height: size * 1.4)
        .animation(.easeInOut(duration: 0.4), value: state)
    }

    private var eye: some View {
        RoundedRectangle(cornerRadius: unit / 2)
            .fill(state.tint)
            .frame(width: unit * 1.6, height: blink ? unit * 0.2 : unit * 1.6)
            .shadow(color: state.tint, radius: 4)
    }

    @ViewBuilder
    private var mouth: some View {
        switch state {
        case .thinking, .acting:
            HStack(spacing: unit / 2) {
                ForEach(0..<3, id: \.self) { i in
                    RoundedRectangle(cornerRadius: 1)
                        .fill(state.tint.opacity(pulse ? 1 : 0.3))
                        .frame(width: unit / 2, height: unit * (i == 1 ? 1.4 : 0.8))
                }
            }
        case .error:
            Text("×")
                .font(.system(size: unit * 2.2, weight: .black, design: .monospaced))
                .foregroundStyle(state.tint)
        default:
            RoundedRectangle(cornerRadius: unit / 2)
                .fill(state.tint)
                .frame(width: unit * 3, height: unit * 0.5)
        }
    }

    private func startAnimations() {
        blink = false
        pulse = false
        // Antenna pulse runs when busy; gentle blink otherwise.
        if state == .idle || state == .listening {
            withAnimation(.easeInOut(duration: 0.18).repeatForever(autoreverses: true).delay(2.0)) {
                blink = true
            }
        }
        let pulseDuration = state == .thinking || state == .acting ? 0.5 : 1.4
        withAnimation(.easeInOut(duration: pulseDuration).repeatForever(autoreverses: true)) {
            pulse = true
        }
    }
}

#Preview {
    HStack(spacing: 24) {
        ForEach(SpriteState.allCases, id: \.self) { state in
            AgentSprite(state: state)
        }
    }
    .padding(40)
    .background(CyberTheme.background)
}
