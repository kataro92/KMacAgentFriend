import Foundation

@MainActor
final class VoiceSession: ObservableObject {
    @Published var isRecording = false
    @Published var statusMessage: String?

    private weak var connection: DaemonConnection?
    private weak var hud: FloatingPanelController?
    private let recorder = AudioRecorder()
    private let ptt = PTTController()

    func bind(_ connection: DaemonConnection, hud: FloatingPanelController) {
        self.connection = connection
        self.hud = hud
    }

    func start() {
        ptt.onPress = { [weak self] in
            Task { await self?.beginPTT() }
        }
        ptt.onRelease = { [weak self] in
            Task { await self?.endPTT() }
        }
        ptt.start()
    }

    func stop() {
        ptt.stop()
    }

    func beginPTT() async {
        guard !isRecording, let connection else { return }
        let allowed = await recorder.requestPermission()
        guard allowed else {
            statusMessage = AudioRecorderError.permissionDenied.localizedDescription
            return
        }

        do {
            hud?.show()
            try recorder.start()
            isRecording = true
            statusMessage = "Listening…"
            try await connection.sendEvent("ptt_start")
        } catch {
            isRecording = false
            statusMessage = error.localizedDescription
        }
    }

    func endPTT() async {
        guard isRecording, let connection else { return }
        isRecording = false
        statusMessage = "Processing…"

        guard let wavURL = recorder.stop() else {
            statusMessage = "No recording captured."
            return
        }

        defer { try? FileManager.default.removeItem(at: wavURL) }

        do {
            try await connection.sendEvent("ptt_end")
            let result = try await connection.submitVoiceTurn(fileURL: wavURL)
            if result.ok {
                connection.lastTranscript = result.transcript
                connection.lastReply = result.reply
                statusMessage = nil
            } else {
                statusMessage = result.error ?? "Voice turn failed."
            }
        } catch {
            statusMessage = error.localizedDescription
        }
    }
}
