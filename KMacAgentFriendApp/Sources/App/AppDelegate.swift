import AppKit

extension Notification.Name {
    static let kafDaemonBootstrapComplete = Notification.Name("kafDaemonBootstrapComplete")
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        Task { @MainActor in
            await PermissionsManager.requestAllIfNeeded()
            await DaemonProcessManager.shared.startIfNeeded()
            NotificationCenter.default.post(name: .kafDaemonBootstrapComplete, object: nil)
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        DaemonProcessManager.shared.stopIfManagedSynchronously()
    }
}
