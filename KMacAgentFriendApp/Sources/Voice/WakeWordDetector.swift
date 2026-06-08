import AVFoundation
import Foundation

/// Always-listening wake-word trigger.
///
/// This ships with a lightweight, on-device **energy-onset** detector so the
/// feature works with zero extra downloads: when sustained speech-level audio is
/// detected after a quiet period it fires `onWake`, which the voice session uses
/// to begin a turn hands-free. For a true keyword model, swap `process(buffer:)`
/// for an openWakeWord / Porcupine inference call — the surrounding lifecycle
/// (engine setup, debouncing, enable/disable) stays the same.
@MainActor
final class WakeWordDetector: ObservableObject {
    @Published private(set) var isListening = false

    /// Called on the main actor when the wake condition is met.
    var onWake: (() -> Void)?

    /// RMS threshold above which a frame counts as speech. Tunable.
    var energyThreshold: Float = 0.06
    /// Consecutive speech frames required before firing (debounce).
    var triggerFrames = 6
    /// Cooldown after a trigger so a single utterance fires once.
    var cooldownSeconds: TimeInterval = 2.5

    private let engine = AVAudioEngine()
    private var speechFrameCount = 0
    private var lastTrigger = Date.distantPast

    func start() {
        guard !isListening else { return }
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, _ in
            let level = Self.rms(buffer)
            Task { @MainActor in
                self?.process(level: level)
            }
        }
        do {
            engine.prepare()
            try engine.start()
            isListening = true
            ActivityLogStore.shared.log(
                level: "info",
                category: "voice",
                message: "Wake-word listening started"
            )
        } catch {
            isListening = false
            ActivityLogStore.shared.log(
                level: "error",
                category: "voice",
                message: "Wake-word engine failed to start",
                detail: error.localizedDescription
            )
        }
    }

    func stop() {
        guard isListening else { return }
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        isListening = false
        speechFrameCount = 0
        ActivityLogStore.shared.log(
            level: "info",
            category: "voice",
            message: "Wake-word listening stopped"
        )
    }

    private func process(level: Float) {
        if level >= energyThreshold {
            speechFrameCount += 1
        } else {
            speechFrameCount = max(0, speechFrameCount - 1)
        }

        guard speechFrameCount >= triggerFrames else { return }
        guard Date().timeIntervalSince(lastTrigger) > cooldownSeconds else { return }

        lastTrigger = Date()
        speechFrameCount = 0
        ActivityLogStore.shared.log(
            level: "info",
            category: "voice",
            message: "Wake word detected"
        )
        onWake?()
    }

    private static func rms(_ buffer: AVAudioPCMBuffer) -> Float {
        guard let channel = buffer.floatChannelData?[0] else { return 0 }
        let count = Int(buffer.frameLength)
        guard count > 0 else { return 0 }
        var sum: Float = 0
        for i in 0..<count {
            let sample = channel[i]
            sum += sample * sample
        }
        return (sum / Float(count)).squareRoot()
    }
}
