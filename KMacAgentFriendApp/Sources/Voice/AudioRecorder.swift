import AVFoundation
import Foundation

enum AudioRecorderError: LocalizedError {
    case permissionDenied
    case failed(String)

    var errorDescription: String? {
        switch self {
        case .permissionDenied:
            return "Microphone permission denied. Enable it in System Settings → Privacy."
        case .failed(let detail):
            return detail
        }
    }
}

/// Records 16 kHz mono WAV suitable for mlx-whisper.
final class AudioRecorder {
    private var recorder: AVAudioRecorder?
    private var outputURL: URL?

    func requestPermission() async -> Bool {
        await withCheckedContinuation { continuation in
            switch AVCaptureDevice.authorizationStatus(for: .audio) {
            case .authorized:
                continuation.resume(returning: true)
            case .notDetermined:
                AVCaptureDevice.requestAccess(for: .audio) { granted in
                    continuation.resume(returning: granted)
                }
            default:
                continuation.resume(returning: false)
            }
        }
    }

    func start() throws {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("kaf-ptt-\(UUID().uuidString).wav")
        outputURL = url

        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatLinearPCM),
            AVSampleRateKey: 16_000,
            AVNumberOfChannelsKey: 1,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsFloatKey: false,
            AVLinearPCMIsBigEndianKey: false,
        ]

        recorder = try AVAudioRecorder(url: url, settings: settings)
        recorder?.isMeteringEnabled = false
        guard recorder?.record() == true else {
            throw AudioRecorderError.failed("Could not start microphone recording.")
        }
    }

    func stop() -> URL? {
        recorder?.stop()
        recorder = nil
        return outputURL
    }
}
