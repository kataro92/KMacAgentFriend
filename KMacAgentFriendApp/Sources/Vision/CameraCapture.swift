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

private final class PhotoCaptureDelegate: NSObject, AVCapturePhotoCaptureDelegate {
    private let onFinish: (Result<Data, Error>) -> Void

    init(onFinish: @escaping (Result<Data, Error>) -> Void) {
        self.onFinish = onFinish
    }

    func photoOutput(
        _ output: AVCapturePhotoOutput,
        didFinishProcessingPhoto photo: AVCapturePhoto,
        error: Error?
    ) {
        if let error {
            onFinish(.failure(error))
            return
        }
        guard let data = photo.fileDataRepresentation() else {
            onFinish(.failure(CameraCaptureError.noImage))
            return
        }
        onFinish(.success(data))
    }
}

/// Single-frame JPEG capture for on-demand vision (Phase 4).
@MainActor
final class CameraCapture {
    private let session = AVCaptureSession()
    private let output = AVCapturePhotoOutput()
    private var photoDelegate: PhotoCaptureDelegate?

    func requestPermission() async -> Bool {
        await PermissionsManager.requestCamera()
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
            let delegate = PhotoCaptureDelegate { [weak self] result in
                Task { @MainActor in
                    self?.session.stopRunning()
                    self?.photoDelegate = nil
                }
                continuation.resume(with: result)
            }
            photoDelegate = delegate
            let settings = AVCapturePhotoSettings(format: [AVVideoCodecKey: AVVideoCodecType.jpeg])
            output.capturePhoto(with: settings, delegate: delegate)
        }
    }
}
