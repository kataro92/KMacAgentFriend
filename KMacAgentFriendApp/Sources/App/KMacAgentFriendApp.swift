import SwiftUI

@main
struct KMacAgentFriendApp: App {
    @StateObject private var connection = DaemonConnection()

    var body: some Scene {
        MenuBarExtra("KMacAgentFriend", systemImage: connection.menuBarSymbol) {
            MenuBarView()
                .environmentObject(connection)
        }
        .menuBarExtraStyle(.window)

        Settings {
            SettingsView()
                .environmentObject(connection)
        }
    }
}
