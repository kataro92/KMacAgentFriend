import SwiftUI

struct ConfirmationRequest: Identifiable, Equatable {
    let id: String
    let action: String
    let message: String
    let detail: String
}

struct ConfirmationSheet: View {
    let request: ConfirmationRequest
    let onApprove: () -> Void
    let onDeny: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Image(systemName: "exclamationmark.shield")
                    .foregroundStyle(CyberTheme.destructive)
                    .neonGlow(CyberTheme.destructive, radius: 6)
                Text("CONFIRM ACTION")
                    .font(CyberFont.title(16))
                    .tracking(2)
                    .cyberGlitchText()
            }
            CyberPromptLine(prefix: ">", text: request.message)
            if !request.detail.isEmpty {
                CyberCard(variant: .terminal) {
                    Text(request.detail)
                        .font(CyberFont.caption)
                        .foregroundStyle(CyberTheme.mutedForeground)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            HStack(spacing: 12) {
                Button("Cancel") { onDeny() }
                    .buttonStyle(CyberButtonStyle(variant: .outline))
                Spacer()
                Button("Allow") { onApprove() }
                    .buttonStyle(CyberButtonStyle(variant: .destructive))
                    .keyboardShortcut(.defaultAction)
            }
        }
        .padding(20)
        .frame(width: 380)
        .cyberScreen()
    }
}
