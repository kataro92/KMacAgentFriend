import AppKit
import SwiftUI

private enum ControlPanelTab: String, CaseIterable, Identifiable {
    case overview, models, voice, tools, system, debug

    var id: String { rawValue }

    var title: String {
        switch self {
        case .overview: return "Overview"
        case .models: return "Models"
        case .voice: return "Voice"
        case .tools: return "Tools"
        case .system: return "System"
        case .debug: return "Debug"
        }
    }

    var symbol: String {
        switch self {
        case .overview: return "gauge"
        case .models: return "brain.head.profile"
        case .voice: return "waveform"
        case .tools: return "wrench.and.screwdriver"
        case .system: return "gearshape"
        case .debug: return "ladybug"
        }
    }
}

struct ControlPanelView: View {
    @EnvironmentObject private var connection: DaemonConnection
    @EnvironmentObject private var daemonProcess: DaemonProcessManager
    @StateObject private var store = ControlPanelStore()
    @ObservedObject private var activityLog = ActivityLogStore.shared
    @ObservedObject private var loginItem = LoginItemManager.shared
    @State private var selection: ControlPanelTab = .overview
    @State private var expandedEntryIDs: Set<UUID> = []
    @State private var upcomingEvents: [CalendarEventSummary] = []
    @State private var calendarBusy = false
    private let calendar = CalendarSidecar()

    var body: some View {
        NavigationSplitView {
            sidebar
        } detail: {
            ZStack {
                CyberTheme.background.ignoresSafeArea()
                CyberGridBackground().ignoresSafeArea()
                CyberScanlines().ignoresSafeArea()
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        if selection != .debug { pageHeader }
                        switch selection {
                        case .overview: overviewSection
                        case .models: modelsSection
                        case .voice: voiceSection
                        case .tools: toolsSection
                        case .system: systemSection
                        case .debug: debugSection
                        }
                    }
                    .padding(selection == .debug ? 0 : 24)
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .toolbar { toolbarContent }
            .preferredColorScheme(.dark)
        }
        .frame(minWidth: 720, minHeight: 560)
        .background(CyberTheme.background)
        .task {
            await store.load()
            await activityLog.loadHistory()
        }
    }

    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text("KMAC")
                    .font(CyberFont.heading(22))
                    .tracking(4)
                    .cyberGlitchText()
                Text("CONTROL PANEL")
                    .font(CyberFont.label)
                    .foregroundStyle(CyberTheme.mutedForeground)
                    .tracking(2)
            }
            .padding(.bottom, 8)

            ForEach(ControlPanelTab.allCases) { tab in
                Button { selection = tab } label: {
                    CyberSidebarTab(title: tab.title, symbol: tab.symbol, isSelected: selection == tab)
                }
                .buttonStyle(.plain)
            }
            Spacer()
            CyberBadge(text: connection.status.rawValue, color: CyberTheme.statusColor(for: connection.status.rawValue))
        }
        .padding(14)
        .frame(minWidth: 190)
        .background(CyberTheme.muted)
        .overlay(alignment: .trailing) {
            Rectangle()
                .fill(CyberTheme.accent.opacity(0.25))
                .frame(width: 1)
        }
    }

    @ToolbarContentBuilder
    private var toolbarContent: some ToolbarContent {
        ToolbarItemGroup(placement: .primaryAction) {
            if store.hasUnsavedChanges {
                Button("Revert") { store.revert() }
                    .buttonStyle(CyberButtonStyle(variant: .ghost))
                Button("Save") { Task { await store.save() } }
                    .buttonStyle(CyberButtonStyle(variant: .glitch))
                    .keyboardShortcut("s", modifiers: .command)
                    .disabled(store.isSaving)
            }
            Button { Task { await store.load() } } label: {
                Image(systemName: "arrow.clockwise")
            }
            .help("Reload settings")
            .disabled(store.isLoading)
        }
    }

    private var pageHeader: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(selection.title.uppercased())
                .font(CyberFont.heading(28))
                .tracking(3)
                .cyberGlitchText(selection == .overview)
                .neonGlow(radius: 8)
            if let message = store.statusMessage {
                CyberBadge(text: message, color: CyberTheme.accent)
            }
            if let error = store.errorMessage ?? daemonProcess.lastError {
                CyberPromptLine(prefix: "!", text: error)
            }
        }
    }

    // MARK: - Overview

    private var overviewSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            CyberCard(title: "Status", variant: .holographic, hoverEffect: true) {
                VStack(alignment: .leading, spacing: 8) {
                    CyberStatusRow(label: "Daemon", value: connection.status.rawValue.capitalized, color: CyberTheme.statusColor(for: connection.status.rawValue))
                    CyberStatusRow(label: "Agent", value: connection.agentStatus, color: CyberTheme.statusColor(for: connection.agentStatus))
                    CyberStatusRow(label: "Ollama", value: connection.ollamaReachable ? "online" : "offline", color: connection.ollamaReachable ? CyberTheme.accent : CyberTheme.destructive)
                    CyberStatusRow(label: "Chat model", value: store.settings.ollamaModel, color: CyberTheme.mutedForeground)
                    if !connection.backgroundTask.isEmpty {
                        CyberStatusRow(label: "Background", value: connection.backgroundTask, color: CyberTheme.accentSecondary)
                    }
                    if let ms = connection.lastLatencyMs {
                        CyberStatusRow(label: "WS latency", value: String(format: "%.1f ms", ms), color: CyberTheme.accentTertiary)
                    }
                }
            }

            CyberCard(title: "Last conversation", variant: .terminal) {
                VStack(alignment: .leading, spacing: 8) {
                    if let transcript = connection.lastTranscript {
                        CyberPromptLine(prefix: "YOU>", text: transcript)
                    }
                    if let reply = connection.lastReply {
                        CyberPromptLine(prefix: "AGENT>", text: reply, muted: true)
                    }
                    if connection.lastTranscript == nil && connection.lastReply == nil {
                        HStack(spacing: 4) {
                            CyberPromptLine(prefix: ">", text: "Awaiting voice uplink", muted: true)
                            BlinkingCursor()
                        }
                    }
                }
            }

            HStack(spacing: 10) {
                Button("Reconnect") { connection.reconnect() }
                    .buttonStyle(CyberButtonStyle(variant: .outline))
                Button("Refresh models") { Task { await store.refreshOllamaModels() } }
                    .buttonStyle(CyberButtonStyle(variant: .secondary))
            }
        }
    }

    // MARK: - Models

    private var modelsSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("LOCAL OLLAMA MODELS — CHANGES APPLY ON NEXT REQUEST")
                .font(CyberFont.label)
                .foregroundStyle(CyberTheme.mutedForeground)
                .tracking(1)

            CyberCard(title: "Chat (LLM)") {
                modelPicker(title: "Model", selection: $store.settings.ollamaModel, suggestions: store.ollamaModels)
            }

            CyberCard(title: "Vision (VLM)") {
                VStack(alignment: .leading, spacing: 8) {
                    modelPicker(title: "Model", selection: $store.settings.ollamaVlmModel, suggestions: store.ollamaModels.filter { name in
                        name.localizedCaseInsensitiveContains("llava")
                            || name.localizedCaseInsensitiveContains("vision")
                            || name.localizedCaseInsensitiveContains("vl")
                    })
                    Text("Used when you confirm a camera capture from the menu bar.")
                        .font(CyberFont.label)
                        .foregroundStyle(CyberTheme.mutedForeground)
                }
            }

            if !store.ollamaReachable {
                CyberCard(variant: .holographic) {
                    Label("Ollama offline — check host in System tab", systemImage: "exclamationmark.triangle")
                        .font(CyberFont.caption)
                        .foregroundStyle(Color(hex: 0xffaa00))
                }
            }
        }
    }

    // MARK: - Voice

    private var voiceSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            CyberCard(title: "Speech recognition", variant: .terminal) {
                whisperModelPicker
            }

            CyberCard(title: "Speech output") {
                VStack(alignment: .leading, spacing: 10) {
                    Picker("Language", selection: $store.settings.ttsLanguage) {
                        Text("English").tag("en")
                        Text("Vietnamese").tag("vi")
                    }
                    .pickerStyle(.segmented)
                    Text("FALLBACK WHEN STT LANGUAGE IS UNKNOWN")
                        .font(CyberFont.label)
                        .foregroundStyle(CyberTheme.mutedForeground)
                }
            }
        }
    }

    // MARK: - Tools

    private var toolsSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            CyberCard(title: "Capabilities") {
                VStack(alignment: .leading, spacing: 8) {
                    capabilityRow("File read/write (sandboxed)", systemImage: "doc.text", enabled: true)
                    capabilityRow("Shell commands (blocklist)", systemImage: "terminal", enabled: true)
                    capabilityRow("Accessibility text inject", systemImage: "keyboard", enabled: AXTextInjector.isTrusted)
                    capabilityRow("Camera / vision", systemImage: "camera", enabled: true)
                }
            }

            CyberCard(title: "Project access") {
                VStack(alignment: .leading, spacing: 10) {
                    CyberTextField(label: "Allowed folders", text: $store.settings.kafProjectDirs, axis: .vertical)
                    Button("Choose project folder") { ProjectRootAccess.requestFolderAccess() }
                        .buttonStyle(CyberButtonStyle(variant: .outline, fullWidth: true))
                    if !AXTextInjector.isTrusted {
                        Button("Open Accessibility Settings") { AXTextInjector.openSettings() }
                            .buttonStyle(CyberButtonStyle(variant: .ghost, fullWidth: true))
                    }
                }
            }
        }
    }

    // MARK: - Debug

    private var debugSection: some View {
        VStack(alignment: .leading, spacing: 0) {
            debugToolbar
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(CyberTheme.muted)

            CyberDivider()

            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 0) {
                        if activityLog.filteredEntries.isEmpty {
                            HStack(spacing: 6) {
                                CyberPromptLine(prefix: ">", text: "No activity logged", muted: true)
                                BlinkingCursor()
                            }
                            .padding(24)
                        } else {
                            ForEach(activityLog.filteredEntries) { entry in
                                debugRow(entry)
                                Rectangle().fill(CyberTheme.border.opacity(0.5)).frame(height: 1)
                            }
                        }
                        Color.clear.frame(height: 1).id("debug-bottom")
                    }
                }
                .onChange(of: activityLog.filteredEntries.count) { _, _ in
                    guard activityLog.autoScroll else { return }
                    withAnimation(.easeOut(duration: 0.2)) {
                        proxy.scrollTo("debug-bottom", anchor: .bottom)
                    }
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var debugToolbar: some View {
        HStack(spacing: 12) {
            Picker("Level", selection: $activityLog.filter) {
                ForEach(ActivityLevelFilter.allCases) { level in
                    Text(level.title).tag(level)
                }
            }
            .pickerStyle(.segmented)
            .frame(maxWidth: 280)

            Picker("Category", selection: $activityLog.categoryFilter) {
                Text("All").tag("all")
                ForEach(activityLog.categories, id: \.self) { category in
                    Text(category).tag(category)
                }
            }
            .frame(maxWidth: 160)

            Toggle("Auto-scroll", isOn: $activityLog.autoScroll)
                .toggleStyle(.checkbox)
                .font(CyberFont.label)

            Spacer()

            Button("Refresh") { Task { await activityLog.loadHistory() } }
                .buttonStyle(CyberButtonStyle(variant: .ghost))
            Button("Copy") {
                NSPasteboard.general.clearContents()
                NSPasteboard.general.setString(activityLog.exportText(), forType: .string)
            }
            .buttonStyle(CyberButtonStyle(variant: .outline))
            Button("Clear") { Task { await activityLog.clear() } }
                .buttonStyle(CyberButtonStyle(variant: .destructive))
        }
    }

    private func debugRow(_ entry: ActivityEntry) -> some View {
        let isExpanded = expandedEntryIDs.contains(entry.id)
        return VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: entry.levelSymbol)
                    .foregroundStyle(CyberTheme.levelColor(entry.level))
                    .frame(width: 16)
                    .neonGlow(CyberTheme.levelColor(entry.level), radius: 3)
                Text(entry.timestamp.formatted(date: .omitted, time: .standard))
                    .font(CyberFont.label)
                    .foregroundStyle(CyberTheme.mutedForeground)
                CyberBadge(text: entry.source, color: CyberTheme.accentTertiary)
                CyberBadge(text: entry.category, color: CyberTheme.accentSecondary)
                Text(entry.message)
                    .font(CyberFont.caption)
                    .textSelection(.enabled)
                Spacer(minLength: 0)
                if entry.detail != nil {
                    Button(isExpanded ? "Hide" : "Detail") {
                        if isExpanded { expandedEntryIDs.remove(entry.id) }
                        else { expandedEntryIDs.insert(entry.id) }
                    }
                    .buttonStyle(CyberButtonStyle(variant: .ghost))
                }
            }
            if isExpanded, let detail = entry.detail {
                Text(detail)
                    .font(CyberFont.caption)
                    .foregroundStyle(CyberTheme.mutedForeground)
                    .textSelection(.enabled)
                    .padding(.leading, 24)
                    .padding(.bottom, 8)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .contentShape(Rectangle())
    }

    // MARK: - System

    private var systemSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            CyberCard(title: "Ollama") {
                CyberTextField(label: "Host URL", text: $store.settings.ollamaHost)
            }

            CyberCard(title: "Background learning") {
                VStack(alignment: .leading, spacing: 8) {
                    Stepper("Interval: \(Int(store.settings.backgroundIntervalSeconds))s", value: $store.settings.backgroundIntervalSeconds, in: 30...3600, step: 30)
                        .font(CyberFont.caption)
                    CyberTextField(label: "Moltbook URL", text: $store.settings.moltbookUrl)
                }
            }

            CyberCard(title: "Daemon", variant: .terminal) {
                VStack(alignment: .leading, spacing: 8) {
                    CyberStatusRow(label: "Endpoint", value: "127.0.0.1:18750")
                    CyberStatusRow(label: "Token", value: tokenPreview, color: CyberTheme.accentTertiary)
                    CyberStatusRow(label: "Data dir", value: store.dataDirPath.isEmpty ? "—" : store.dataDirPath, color: CyberTheme.mutedForeground)
                    CyberStatusRow(label: "Settings", value: store.userSettingsPath.isEmpty ? "—" : store.userSettingsPath, color: CyberTheme.mutedForeground)
                }
            }

            CyberCard(title: "Startup") {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle(isOn: Binding(
                        get: { loginItem.isEnabled },
                        set: { loginItem.setEnabled($0) }
                    )) {
                        Text("Launch KMacAgentFriend at login")
                            .font(CyberFont.caption)
                            .foregroundStyle(CyberTheme.foreground)
                    }
                    .toggleStyle(.switch)
                    .tint(CyberTheme.accent)
                    CyberStatusRow(label: "Login item", value: loginItem.statusDescription, color: CyberTheme.mutedForeground)
                    if let error = loginItem.lastError {
                        CyberPromptLine(prefix: "!", text: error)
                            .foregroundStyle(CyberTheme.destructive)
                    }
                }
            }

            CyberCard(title: "Calendar & Reminders") {
                VStack(alignment: .leading, spacing: 8) {
                    Button(calendarBusy ? "Loading…" : "Load upcoming events") {
                        Task {
                            calendarBusy = true
                            upcomingEvents = await calendar.upcomingEvents(within: 7)
                            calendarBusy = false
                        }
                    }
                    .buttonStyle(CyberButtonStyle(variant: .outline, fullWidth: true))
                    .disabled(calendarBusy)
                    if upcomingEvents.isEmpty {
                        Text("Grant Calendar access, then load to preview the next 7 days.")
                            .font(CyberFont.label)
                            .foregroundStyle(CyberTheme.mutedForeground)
                    } else {
                        ForEach(upcomingEvents.prefix(8)) { event in
                            CyberStatusRow(
                                label: event.start.formatted(date: .abbreviated, time: .shortened),
                                value: event.title,
                                color: CyberTheme.accentTertiary
                            )
                        }
                    }
                }
            }

            CyberCard(title: "About") {
                Text("KMacAgentFriend v0.1.0 — local voice agent with Ollama, tools, and vision.")
                    .font(CyberFont.caption)
                    .foregroundStyle(CyberTheme.mutedForeground)
            }
        }
    }

    // MARK: - Helpers

    private var whisperModelPicker: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("WHISPER MODEL")
                .font(CyberFont.label)
                .foregroundStyle(CyberTheme.mutedForeground)
                .tracking(1.5)

            Picker("Whisper model", selection: $store.settings.whisperModel) {
                if !WhisperModelOption.catalog.contains(where: { $0.modelId == store.settings.whisperModel }) {
                    Text(store.settings.whisperModel).tag(store.settings.whisperModel)
                }
                ForEach(WhisperModelOption.catalog) { option in
                    Text(option.title).tag(option.modelId)
                }
            }
            .pickerStyle(.menu)
            .labelsHidden()
            .font(CyberFont.body)
            .foregroundStyle(CyberTheme.foreground)

            Text(store.whisperModelDetail)
                .font(CyberFont.label)
                .foregroundStyle(CyberTheme.mutedForeground)

            HStack(spacing: 8) {
                Text(store.settings.whisperModel)
                    .font(CyberFont.label)
                    .foregroundStyle(CyberTheme.accent.opacity(0.8))
                    .textSelection(.enabled)
                Spacer()
                Text(store.whisperStatusLabel.uppercased())
                    .font(CyberFont.label)
                    .foregroundStyle(whisperStatusColor)
            }

            if store.showWhisperDownloadButton {
                Button("Download model") {
                    Task { await store.downloadSelectedWhisperModel() }
                }
                .buttonStyle(CyberButtonStyle(variant: .default, fullWidth: true))
            } else if store.isActivelyDownloadingWhisper {
                HStack(spacing: 8) {
                    ProgressView()
                        .controlSize(.small)
                    Text("Downloading weights from Hugging Face…")
                        .font(CyberFont.label)
                        .foregroundStyle(CyberTheme.mutedForeground)
                }
            }
        }
        .onChange(of: store.settings.whisperModel) { _, _ in
            store.onWhisperModelChanged()
        }
        .onAppear {
            Task { await store.refreshWhisperStatus(for: store.settings.whisperModel) }
        }
    }

    private var whisperStatusColor: Color {
        if store.whisperStatus.ready {
            return CyberTheme.accent
        }
        if store.isActivelyDownloadingWhisper {
            return CyberTheme.accentTertiary
        }
        if store.whisperStatus.needsDownload {
            return Color(hex: 0xffaa00)
        }
        return CyberTheme.mutedForeground
    }

    private func modelPicker(title: String, selection: Binding<String>, suggestions: [String]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            if suggestions.isEmpty {
                CyberTextField(label: title, text: selection)
            } else {
                Picker(title, selection: selection) {
                    if !suggestions.contains(selection.wrappedValue) && !selection.wrappedValue.isEmpty {
                        Text(selection.wrappedValue).tag(selection.wrappedValue)
                    }
                    ForEach(suggestions, id: \.self) { model in
                        Text(model).tag(model)
                    }
                }
                CyberTextField(label: "Custom model", text: selection)
            }
        }
    }

    private func capabilityRow(_ title: String, systemImage: String, enabled: Bool) -> some View {
        HStack(spacing: 10) {
            Image(systemName: enabled ? "checkmark.square.fill" : "xmark.square")
                .foregroundStyle(enabled ? CyberTheme.accent : Color(hex: 0xffaa00))
                .neonGlow(enabled ? CyberTheme.accent : .clear, radius: 3)
            Image(systemName: systemImage)
                .foregroundStyle(CyberTheme.mutedForeground)
            Text(title)
                .font(CyberFont.caption)
        }
    }

    private var tokenPreview: String {
        guard let token = AppDataPaths.resolveApiToken(), token.count > 8 else {
            return "not found"
        }
        return String(token.prefix(4)) + "…" + String(token.suffix(4))
    }
}
