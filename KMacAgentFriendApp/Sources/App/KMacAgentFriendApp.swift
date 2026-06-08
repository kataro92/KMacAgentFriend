import SwiftUI

@main
struct KMacAgentFriendApp: App {
    @StateObject private var connection = DaemonConnection()
    @StateObject private var voice = VoiceSession()

    var body: some Scene {
        MenuBarExtra("KMacAgentFriend", systemImage: connection.menuBarSymbol) {
            MenuBarView()
                .environmentObject(connection)
                .environmentObject(voice)
                .onAppear {
                    voice.bind(connection)
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
