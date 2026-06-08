import Foundation
import ServiceManagement

/// Manages launch-at-login via `SMAppService` (macOS 13+).
///
/// The Python daemon itself is spawned by `DaemonProcessManager` when the app
/// launches; registering the app as a login item means the whole agent comes up
/// automatically after a reboot.
@MainActor
final class LoginItemManager: ObservableObject {
    static let shared = LoginItemManager()

    @Published private(set) var isEnabled = false
    @Published var lastError: String?

    private let service = SMAppService.mainApp

    private init() {
        refresh()
    }

    func refresh() {
        isEnabled = service.status == .enabled
    }

    var statusDescription: String {
        switch service.status {
        case .enabled: return "Enabled"
        case .notRegistered: return "Not enabled"
        case .requiresApproval: return "Requires approval in System Settings → Login Items"
        case .notFound: return "Service not found"
        @unknown default: return "Unknown"
        }
    }

    func setEnabled(_ enabled: Bool) {
        lastError = nil
        do {
            if enabled {
                if service.status != .enabled {
                    try service.register()
                }
            } else {
                if service.status == .enabled {
                    try service.unregister()
                }
            }
            refresh()
            ActivityLogStore.shared.log(
                level: "info",
                category: "system",
                message: enabled ? "Enabled launch at login" : "Disabled launch at login"
            )
        } catch {
            lastError = error.localizedDescription
            ActivityLogStore.shared.log(
                level: "error",
                category: "system",
                message: "Login item update failed",
                detail: error.localizedDescription
            )
        }
    }
}
