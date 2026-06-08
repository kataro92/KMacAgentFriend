import ApplicationServices
import AVFoundation

/// Requests macOS privacy permissions once at app launch.
@MainActor
enum PermissionsManager {
    static func requestAllIfNeeded() async {
        let mic = await requestMicrophone()
        ActivityLogStore.shared.log(
            level: mic ? "info" : "warn",
            category: "permissions",
            message: mic ? "Microphone access granted" : "Microphone access denied or restricted"
        )

        let camera = await requestCamera()
        ActivityLogStore.shared.log(
            level: camera ? "info" : "warn",
            category: "permissions",
            message: camera ? "Camera access granted" : "Camera access denied or restricted"
        )

        let accessibility = requestAccessibilityPromptIfNeeded()
        ActivityLogStore.shared.log(
            level: accessibility ? "info" : "warn",
            category: "permissions",
            message: accessibility
                ? "Accessibility access granted"
                : "Accessibility not granted — text inject disabled until enabled in System Settings"
        )
    }

    static func requestMicrophone() async -> Bool {
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .authorized:
            return true
        case .notDetermined:
            return await AVCaptureDevice.requestAccess(for: .audio)
        default:
            return false
        }
    }

    static func requestCamera() async -> Bool {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            return true
        case .notDetermined:
            return await AVCaptureDevice.requestAccess(for: .video)
        default:
            return false
        }
    }

    /// Shows the system Accessibility prompt once when the app is not yet trusted.
    @discardableResult
    static func requestAccessibilityPromptIfNeeded() -> Bool {
        if AXIsProcessTrusted() {
            return true
        }
        let promptKey = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String
        let options = [promptKey: true] as CFDictionary
        return AXIsProcessTrustedWithOptions(options)
    }
}
