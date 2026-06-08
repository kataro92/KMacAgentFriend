import AVFoundation
import Foundation

enum CameraCaptureError: LocalizedError {
    case permissionDenied
    case noImage

    var errorDescription: String? {
        switch self {
        case .permissionDenied:
            return "Camera permission denied. Enable it in System Settings → Privacy."
        case .noImage:
            return "Could not capture a still frame."
        }
    }
}

/// Single-frame JPEG capture for on-demand vision (Phase 4).
@MainActor
final class CameraCapture: NSObject, AVCapturePhotoCaptureDelegate {
    private let session = AVCaptureSession()
    private let output = AVCapturePhotoOutput()
    private var continuation: CheckedContinuation<Data, Error>?

    func requestPermission() async -> Bool {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            return true
        case .notDetermined:
            return await AVCaptureDevice.requestAccess(for: .video)
        default:
            return false
        }
    }

    func captureJPEG() async throws -> Data {
        guard await requestPermission() else {
            throw CameraCaptureError.permissionDenied
        }

        session.beginConfiguration()
        session.sessionPreset = .photo
        if let device = AVCaptureDevice.default(for: .video),
           let input = try? AVCaptureDeviceInput(device: device),
           session.inputs.isEmpty {
            if session.canAddInput(input) { session.addInput(input) }
        }
        if session.outputs.isEmpty, session.canAddOutput(output) {
            session.addOutput(output)
        }
        session.commitConfiguration()

        if !session.isRunning {
            session.startRunning()
        }

        return try await withCheckedThrowingContinuation { continuation in
            self.continuation = continuation
            let settings = AVCapturePhotoSettings(format: [AVVideoCodecKey: AVVideoCodecType.jpeg])
            output.capturePhoto(with: settings, delegate: self)
        }
    }

    func photoOutput(
        _ output: AVCapturePhotoOutput,
        didFinishProcessingPhoto photo: AVCapturePhoto,
        error: Error?
    ) {
        if let error {
            continuation?.resume(throwing: error)
            continuation = nil
            return
        }
        guard let data = photo.fileDataRepresentation() else {
            continuation?.resume(throwing: CameraCaptureError.noImage)
            continuation = nil
            return
        }
        continuation?.resume(returning: data)
        continuation = nil
        session.stopRunning()
    }
}
