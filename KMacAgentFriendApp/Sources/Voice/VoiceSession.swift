import Foundation

@MainActor
final class VoiceSession: ObservableObject {
    @Published var isRecording = false
    @Published var isReplaying = false
    @Published var statusMessage: String?
    @Published var wakeWordEnabled = false

    var canReplayLastReply: Bool {
        guard let connection, !isRecording, !isReplaying else { return false }
        guard let reply = connection.lastReply, !reply.isEmpty else { return false }
        return true
    }

    private weak var connection: DaemonConnection?
    private let recorder = AudioRecorder()
    private let ptt = PTTController()
    private let wakeWord = WakeWordDetector()
    private let client = DaemonClient()

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

        wakeWord.onWake = { [weak self] in
            Task { await self?.handleWake() }
        }
    }

    func stop() {
        ptt.stop()
        wakeWord.stop()
    }

    func setWakeWord(enabled: Bool) {
        wakeWordEnabled = enabled
        if enabled {
            wakeWord.start()
        } else {
            wakeWord.stop()
        }
    }

    /// Wake word fired: barge-in on any current speech, then start a turn.
    private func handleWake() async {
        await bargeInIfSpeaking()
        await beginPTT()
        // Give the speaker a short window, then submit the captured audio.
        try? await Task.sleep(nanoseconds: 4_000_000_000)
        if isRecording {
            await endPTT()
        }
    }

    /// Interrupt in-progress TTS both locally and on the daemon.
    func bargeInIfSpeaking() async {
        guard let connection else { return }
        if connection.agentStatus == "speaking" || isReplaying {
            isReplaying = false
            try? await client.stopSpeech()
            ActivityLogStore.shared.log(
                level: "info",
                category: "voice",
                message: "Barge-in: interrupted speech"
            )
        }
    }

    func beginPTT() async {
        guard !isRecording, let connection else { return }
        // Pressing to talk while the agent is speaking interrupts it.
        await bargeInIfSpeaking()
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
