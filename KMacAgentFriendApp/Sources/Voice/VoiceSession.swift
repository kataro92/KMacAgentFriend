import Foundation

@MainActor
final class VoiceSession: ObservableObject {
    @Published var isRecording = false
    @Published var isReplaying = false
    @Published var statusMessage: String?

    var canReplayLastReply: Bool {
        guard let connection, !isRecording, !isReplaying else { return false }
        guard let reply = connection.lastReply, !reply.isEmpty else { return false }
        return true
    }

    private weak var connection: DaemonConnection?
    private let recorder = AudioRecorder()
    private let ptt = PTTController()

    func bind(_ connection: DaemonConnection) {
        self.connection = connection
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
            ActivityLogStore.shared.log(
                level: "error",
                category: "voice",
                message: "Microphone permission denied"
            )
            return
        }

        do {
            try recorder.start()
            isRecording = true
            statusMessage = "Listening…"
            ActivityLogStore.shared.log(level: "info", category: "voice", message: "PTT started")
            try await connection.sendEvent("ptt_start")
        } catch {
            isRecording = false
            statusMessage = error.localizedDescription
            ActivityLogStore.shared.log(
                level: "error",
                category: "voice",
                message: "PTT start failed",
                detail: error.localizedDescription
            )
        }
    }

    func endPTT() async {
        guard isRecording, let connection else { return }
        isRecording = false
        statusMessage = "Processing…"
        connection.voiceProgressMessage = "Sending audio to daemon…"
        ActivityLogStore.shared.log(level: "info", category: "voice", message: "PTT ended, sending voice turn")

        guard let wavURL = recorder.stop() else {
            statusMessage = "No recording captured."
            ActivityLogStore.shared.log(level: "warn", category: "voice", message: "No audio captured")
            return
        }

        defer { try? FileManager.default.removeItem(at: wavURL) }

        do {
            try await connection.sendEvent("ptt_end")
            let result = try await connection.submitVoiceTurn(fileURL: wavURL)
            if result.ok {
                connection.lastTranscript = result.transcript
                connection.lastReply = result.reply
                connection.lastReplyLanguage = result.language
                statusMessage = nil
                connection.voiceProgressMessage = nil
                ActivityLogStore.shared.log(
                    level: "info",
                    category: "voice",
                    message: "Voice turn completed",
                    detail: result.transcript
                )
            } else {
                connection.voiceProgressMessage = nil
                statusMessage = result.error ?? "Voice turn failed."
                ActivityLogStore.shared.log(
                    level: "error",
                    category: "voice",
                    message: "Voice turn failed",
                    detail: result.error
                )
            }
        } catch {
            connection.voiceProgressMessage = nil
            statusMessage = error.localizedDescription
            ActivityLogStore.shared.log(
                level: "error",
                category: "voice",
                message: "Voice turn error",
                detail: error.localizedDescription
            )
        }
    }

    func replayLastReply() async {
        guard canReplayLastReply, let connection, let text = connection.lastReply else { return }
        isReplaying = true
        statusMessage = "Replaying…"
        defer {
            isReplaying = false
            statusMessage = nil
        }

        let language = connection.lastReplyLanguage ?? "en"
        do {
            let result = try await connection.speakText(text, language: language)
            if result.ok {
                ActivityLogStore.shared.log(level: "info", category: "voice", message: "Replayed last reply")
            } else {
                statusMessage = result.error ?? "Replay failed."
                ActivityLogStore.shared.log(
                    level: "error",
                    category: "voice",
                    message: "Replay failed",
                    detail: result.error
                )
            }
        } catch {
            statusMessage = error.localizedDescription
            ActivityLogStore.shared.log(
                level: "error",
                category: "voice",
                message: "Replay error",
                detail: error.localizedDescription
            )
        }
    }
}
