import Foundation

@MainActor
final class AutopilotStore: ObservableObject {
    @Published var enabled = false
    @Published var allowedActions: [String] = []
    @Published var decisions: [DecisionEntry] = []
    @Published var missions: [Mission] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    @Published var newMissionTitle = ""
    @Published var newMissionDescription = ""

    private let client = DaemonClient()

    func load() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            let policy = try await client.fetchAutopilotPolicy()
            enabled = policy.enabled
            allowedActions = policy.allowedActions
            decisions = try await client.fetchDecisions()
            missions = try await client.fetchMissions()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func toggle(_ value: Bool) async {
        do {
            let policy = try await client.setAutopilot(enabled: value)
            enabled = policy.enabled
            allowedActions = policy.allowedActions
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func addMission() async {
        let title = newMissionTitle.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty else { return }
        do {
            try await client.createMission(title: title, description: newMissionDescription)
            newMissionTitle = ""
            newMissionDescription = ""
            missions = try await client.fetchMissions()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func refreshDecisions() async {
        do {
            decisions = try await client.fetchDecisions()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
