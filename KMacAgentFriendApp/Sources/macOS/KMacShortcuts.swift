import AppIntents
import Foundation

/// Shortcuts / Siri intent: send a prompt to the local daemon and return the reply.
struct AskKMacAgentIntent: AppIntent {
    static var title: LocalizedStringResource = "Ask KMacAgent"
    static var description = IntentDescription(
        "Send a message to your local KMacAgentFriend and get a reply."
    )

    @Parameter(title: "Message")
    var message: String

    static var parameterSummary: some ParameterSummary {
        Summary("Ask KMacAgent \(\.$message)")
    }

    @MainActor
    func perform() async throws -> some IntentResult & ReturnsValue<String> & ProvidesDialog {
        let reply = try await DaemonClient().sendChat(message: message)
        return .result(value: reply, dialog: IntentDialog(stringLiteral: reply))
    }
}

/// Shortcuts intent: speak text aloud via the daemon's local TTS.
struct SpeakWithKMacAgentIntent: AppIntent {
    static var title: LocalizedStringResource = "Speak with KMacAgent"
    static var description = IntentDescription("Have KMacAgentFriend speak text aloud locally.")

    @Parameter(title: "Text")
    var text: String

    @Parameter(title: "Language", default: "en")
    var language: String

    @MainActor
    func perform() async throws -> some IntentResult {
        _ = try await DaemonClient().speakText(text, language: language)
        return .result()
    }
}

/// Shortcuts intent: create a new background career mission.
struct AddMissionIntent: AppIntent {
    static var title: LocalizedStringResource = "Add KMacAgent Mission"
    static var description = IntentDescription("Create a long-running goal for KMacAgentFriend.")

    @Parameter(title: "Title")
    var title: String

    @Parameter(title: "Details", default: "")
    var details: String

    @MainActor
    func perform() async throws -> some IntentResult {
        try await DaemonClient().createMission(title: title, description: details)
        return .result()
    }
}

struct KMacShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: AskKMacAgentIntent(),
            phrases: ["Ask \(.applicationName)", "Ask \(.applicationName) \(\.$message)"],
            shortTitle: "Ask KMacAgent",
            systemImageName: "brain.head.profile"
        )
        AppShortcut(
            intent: SpeakWithKMacAgentIntent(),
            phrases: ["Speak with \(.applicationName)"],
            shortTitle: "Speak",
            systemImageName: "waveform"
        )
        AppShortcut(
            intent: AddMissionIntent(),
            phrases: ["Add a \(.applicationName) mission"],
            shortTitle: "Add Mission",
            systemImageName: "target"
        )
    }
}
