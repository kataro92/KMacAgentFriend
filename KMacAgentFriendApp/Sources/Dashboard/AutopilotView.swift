import SwiftUI

/// Autopilot policy controls, career missions, and the decision audit log.
struct AutopilotView: View {
    @StateObject private var store = AutopilotStore()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: CyberTheme.spacing * 2) {
                policyCard
                missionsCard
                auditCard
            }
            .padding(20)
        }
        .frame(minWidth: 520, minHeight: 560)
        .cyberScreen()
        .task { await store.load() }
    }

    private var policyCard: some View {
        CyberCard(title: "AUTOPILOT POLICY", variant: .holographic) {
            VStack(alignment: .leading, spacing: 10) {
                Toggle(isOn: Binding(
                    get: { store.enabled },
                    set: { value in Task { await store.toggle(value) } }
                )) {
                    Text(store.enabled ? "Autopilot ENABLED" : "Suggestion-only (Autopilot off)")
                        .font(CyberFont.body)
                        .foregroundStyle(CyberTheme.foreground)
                }
                .toggleStyle(.switch)
                .tint(CyberTheme.accent)

                Text("Allowed autonomous actions:")
                    .font(CyberFont.label)
                    .foregroundStyle(CyberTheme.mutedForeground)
                if store.allowedActions.isEmpty {
                    Text("none").font(CyberFont.caption).foregroundStyle(CyberTheme.mutedForeground)
                } else {
                    FlowRow(items: store.allowedActions)
                }
                Text("Destructive actions always require explicit confirmation.")
                    .font(CyberFont.caption)
                    .foregroundStyle(CyberTheme.accentTertiary)
            }
        }
    }

    private var missionsCard: some View {
        CyberCard(title: "CAREER MISSIONS") {
            VStack(alignment: .leading, spacing: 10) {
                ForEach(store.missions) { mission in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(mission.title)
                                .font(CyberFont.body)
                                .foregroundStyle(CyberTheme.foreground)
                            Spacer()
                            CyberBadge(
                                text: mission.status,
                                color: CyberTheme.statusColor(for: mission.status)
                            )
                        }
                        ProgressView(value: Double(mission.progress), total: 100)
                            .tint(CyberTheme.accent)
                    }
                    .padding(8)
                    .background(CyberTheme.muted.opacity(0.4))
                    .clipShape(RoundedRectangle(cornerRadius: CyberTheme.chamferSm))
                }
                if store.missions.isEmpty {
                    Text("No missions yet.")
                        .font(CyberFont.caption)
                        .foregroundStyle(CyberTheme.mutedForeground)
                }

                TextField("New mission title", text: $store.newMissionTitle)
                    .textFieldStyle(.roundedBorder)
                TextField("Description (optional)", text: $store.newMissionDescription)
                    .textFieldStyle(.roundedBorder)
                Button("Add Mission") { Task { await store.addMission() } }
                    .buttonStyle(CyberButtonStyle(variant: .default, fullWidth: true))
                    .disabled(store.newMissionTitle.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
    }

    private var auditCard: some View {
        CyberCard(title: "DECISION AUDIT LOG", variant: .terminal) {
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text("Recent autonomous decisions")
                        .font(CyberFont.label)
                        .foregroundStyle(CyberTheme.mutedForeground)
                    Spacer()
                    Button("Refresh") { Task { await store.refreshDecisions() } }
                        .buttonStyle(CyberButtonStyle(variant: .ghost))
                }
                if store.decisions.isEmpty {
                    Text("No decisions recorded.")
                        .font(CyberFont.caption)
                        .foregroundStyle(CyberTheme.mutedForeground)
                }
                ForEach(store.decisions) { entry in
                    HStack(alignment: .top, spacing: 8) {
                        Image(systemName: entry.allowed ? "checkmark.seal.fill" : "hand.raised.fill")
                            .foregroundStyle(entry.allowed ? CyberTheme.accent : CyberTheme.destructive)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(entry.summary.isEmpty ? entry.action : entry.summary)
                                .font(CyberFont.caption)
                                .foregroundStyle(CyberTheme.foreground)
                            if !entry.reason.isEmpty {
                                Text(entry.reason)
                                    .font(CyberFont.caption)
                                    .foregroundStyle(CyberTheme.mutedForeground)
                            }
                        }
                    }
                    .padding(.vertical, 2)
                }
            }
        }
    }
}

/// Simple wrapping row of badges.
private struct FlowRow: View {
    let items: [String]

    var body: some View {
        let columns = [GridItem(.adaptive(minimum: 70), spacing: 6)]
        LazyVGrid(columns: columns, alignment: .leading, spacing: 6) {
            ForEach(items, id: \.self) { item in
                CyberBadge(text: item, color: CyberTheme.accentTertiary)
            }
        }
    }
}
