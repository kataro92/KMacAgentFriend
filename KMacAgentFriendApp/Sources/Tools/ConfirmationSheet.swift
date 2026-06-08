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
            Label("Confirm action", systemImage: "exclamationmark.shield")
                .font(.headline)
            Text(request.message)
                .font(.body)
            if !request.detail.isEmpty {
                Text(request.detail)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)
            }
            HStack {
                Button("Cancel", role: .cancel) { onDeny() }
                Spacer()
                Button("Allow", role: .destructive) { onApprove() }
                    .keyboardShortcut(.defaultAction)
            }
        }
        .padding(20)
        .frame(width: 360)
    }
}
