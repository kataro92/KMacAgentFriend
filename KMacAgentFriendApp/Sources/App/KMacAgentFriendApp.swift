import SwiftUI

@main
struct KMacAgentFriendApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var connection = DaemonConnection()
    @StateObject private var voice = VoiceSession()
    var body: some Scene {
        MenuBarExtra("KMacAgentFriend", systemImage: connection.menuBarSymbol) {
            MenuBarView()
                .environmentObject(connection)
                .environmentObject(voice)
                .environmentObject(DaemonProcessManager.shared)
                .onAppear {
                    voice.bind(connection)
                    voice.start()
                }
        }
        .menuBarExtraStyle(.window)

        Window("KMacAgentFriend", id: "control-panel") {
            ControlPanelView()
                .environmentObject(connection)
                .environmentObject(DaemonProcessManager.shared)
                .preferredColorScheme(.dark)
        }
        .defaultSize(width: 760, height: 580)

        Window("Focus Mode", id: "focus-mode") {
            FocusModeView()
                .environmentObject(connection)
                .environmentObject(voice)
                .preferredColorScheme(.dark)
        }
        .defaultSize(width: 520, height: 600)

        Window("Autopilot", id: "autopilot") {
            AutopilotView()
                .environmentObject(connection)
                .preferredColorScheme(.dark)
        }
        .defaultSize(width: 560, height: 640)
    }
}
