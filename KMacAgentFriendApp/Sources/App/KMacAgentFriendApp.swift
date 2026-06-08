import SwiftUI

@main
struct KMacAgentFriendApp: App {
    @StateObject private var connection = DaemonConnection()
    @StateObject private var voice = VoiceSession()
    @StateObject private var hud = FloatingPanelController()

    var body: some Scene {
        MenuBarExtra("KMacAgentFriend", systemImage: connection.menuBarSymbol) {
            MenuBarView()
                .environmentObject(connection)
                .environmentObject(voice)
                .environmentObject(hud)
                .onAppear {
                    hud.bind(connection: connection, voice: voice)
                    voice.bind(connection, hud: hud)
                    voice.start()
                }
        }
        .menuBarExtraStyle(.window)

        Window("KMacAgentFriend Dashboard", id: "dashboard") {
            DashboardView()
                .environmentObject(connection)
                .environmentObject(voice)
        }
        .defaultSize(width: 720, height: 520)

        Settings {
            SettingsView()
                .environmentObject(connection)
        }
    }
}
