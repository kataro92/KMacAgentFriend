import Foundation

struct WhisperModelOption: Identifiable, Hashable {
    var id: String { modelId }
    let modelId: String
    let title: String
    let detail: String

    static let catalog: [WhisperModelOption] = [
        WhisperModelOption(
            modelId: "mlx-community/whisper-tiny",
            title: "Tiny",
            detail: "Fastest · lowest accuracy · ~40 MB"
        ),
        WhisperModelOption(
            modelId: "mlx-community/whisper-base-mlx",
            title: "Base",
            detail: "Fast · basic quality · ~75 MB"
        ),
        WhisperModelOption(
            modelId: "mlx-community/whisper-small-mlx",
            title: "Small (recommended)",
            detail: "Best balance on M1 · ~150 MB"
        ),
        WhisperModelOption(
            modelId: "mlx-community/whisper-medium-mlx",
            title: "Medium",
            detail: "Higher quality · slower · ~750 MB"
        ),
        WhisperModelOption(
            modelId: "mlx-community/whisper-large-v3-turbo",
            title: "Large v3 Turbo",
            detail: "High quality · first download ~1.5 GB"
        ),
        WhisperModelOption(
            modelId: "mlx-community/whisper-large-v3-mlx",
            title: "Large v3",
            detail: "Highest quality · slowest · ~1.5 GB"
        ),
    ]
}

struct AppSettings: Codable, Equatable {
    var ollamaHost: String
    var ollamaModel: String
    var ollamaVlmModel: String
    var whisperModel: String
    var ttsLanguage: String
    var kafProjectDirs: String
    var moltbookUrl: String
    var backgroundIntervalSeconds: Double

    enum CodingKeys: String, CodingKey {
        case ollamaHost = "ollama_host"
        case ollamaModel = "ollama_model"
        case ollamaVlmModel = "ollama_vlm_model"
        case whisperModel = "whisper_model"
        case ttsLanguage = "tts_language"
        case kafProjectDirs = "kaf_project_dirs"
        case moltbookUrl = "moltbook_url"
        case backgroundIntervalSeconds = "background_interval_seconds"
    }
}

@MainActor
final class ControlPanelStore: ObservableObject {
    @Published var settings = AppSettings(
        ollamaHost: "http://127.0.0.1:11434",
        ollamaModel: "llama3.2",
        ollamaVlmModel: "llava",
        whisperModel: "mlx-community/whisper-small-mlx",
        ttsLanguage: "en",
        kafProjectDirs: "",
        moltbookUrl: "",
        backgroundIntervalSeconds: 120
    )
    @Published var ollamaModels: [String] = []
    @Published var ollamaReachable = false
    @Published var isLoading = false
    @Published var isSaving = false
    @Published var statusMessage: String?
    @Published var errorMessage: String?
    @Published var userSettingsPath: String = ""
    @Published var dataDirPath: String = ""
    @Published var whisperStatus = VoiceModelStatus(
        model: "",
        cached: false,
        ready: false,
        downloadInProgress: false,
        needsDownload: true,
        mlxWhisper: false
    )
    @Published var isWhisperDownloading = false

    private let client = DaemonClient()
    private var savedSnapshot: AppSettings?
    private var whisperPollTask: Task<Void, Never>?

    var hasUnsavedChanges: Bool {
        guard let savedSnapshot else { return false }
        return settings != savedSnapshot
    }

    var whisperModelDetail: String {
        WhisperModelOption.catalog.first { $0.modelId == settings.whisperModel }?.detail
            ?? "Custom mlx-whisper model ID"
    }

    var isActivelyDownloadingWhisper: Bool {
        isWhisperDownloading || (whisperStatus.downloadInProgress && whisperStatus.needsDownload)
    }

    var showWhisperDownloadButton: Bool {
        whisperStatus.mlxWhisper
            && whisperStatus.needsDownload
            && !isActivelyDownloadingWhisper
    }

    var whisperStatusLabel: String {
        if !whisperStatus.mlxWhisper {
            return "mlx-whisper not installed"
        }
        if isActivelyDownloadingWhisper {
            return "Downloading…"
        }
        if whisperStatus.ready {
            return "Ready"
        }
        if whisperStatus.cached {
            return "Downloaded (not loaded yet)"
        }
        return "Not downloaded"
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let payload = try await client.fetchSettings()
            settings = payload.settings
            savedSnapshot = payload.settings
            userSettingsPath = payload.userSettingsPath
            dataDirPath = payload.dataDirPath
            statusMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }

        await refreshOllamaModels()
        await refreshWhisperStatus()
    }

    func refreshWhisperStatus(for model: String? = nil) async {
        let target = model ?? settings.whisperModel
        do {
            whisperStatus = try await client.fetchVoiceStatus(model: target)
            if !whisperStatus.downloadInProgress {
                isWhisperDownloading = false
            }
            if whisperStatus.cached {
                stopWhisperPolling()
                isWhisperDownloading = false
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func downloadSelectedWhisperModel() async {
        let model = settings.whisperModel
        isWhisperDownloading = true
        errorMessage = nil
        do {
            let result = try await client.downloadWhisperModel(model)
            guard result.ok else {
                errorMessage = result.error ?? "Download failed"
                isWhisperDownloading = false
                return
            }
            startWhisperPolling(for: model)
        } catch {
            errorMessage = error.localizedDescription
            isWhisperDownloading = false
        }
    }

    func onWhisperModelChanged() {
        stopWhisperPolling()
        isWhisperDownloading = false
        Task { await refreshWhisperStatus(for: settings.whisperModel) }
    }

    private func startWhisperPolling(for model: String) {
        stopWhisperPolling()
        whisperPollTask = Task {
            while !Task.isCancelled {
                await refreshWhisperStatus(for: model)
                if !whisperStatus.needsDownload {
                    break
                }
                if !whisperStatus.downloadInProgress {
                    break
                }
                try? await Task.sleep(nanoseconds: 2_000_000_000)
            }
            isWhisperDownloading = false
        }
    }

    private func stopWhisperPolling() {
        whisperPollTask?.cancel()
        whisperPollTask = nil
    }

    func refreshOllamaModels() async {
        do {
            let result = try await client.fetchOllamaModels()
            ollamaReachable = result.reachable
            ollamaModels = result.models
        } catch {
            ollamaReachable = false
            ollamaModels = []
        }
    }

    func save() async {
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }

        do {
            let updated = try await client.updateSettings(settings)
            settings = updated
            savedSnapshot = updated
            statusMessage = "Settings saved."
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func revert() {
        if let savedSnapshot {
            settings = savedSnapshot
        }
        statusMessage = nil
        errorMessage = nil
    }
}
