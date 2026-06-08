import Combine
import Foundation

enum ConnectionStatus: String {
    case disconnected
    case connecting
    case connected
    case error
}

@MainActor
final class DaemonConnection: ObservableObject {
    @Published var status: ConnectionStatus = .disconnected
    @Published var agentStatus: String = "idle"
    @Published var lastLatencyMs: Double?
    @Published var ollamaReachable: Bool = false
    @Published var errorMessage: String?
    @Published var lastTranscript: String?
    @Published var lastReply: String?
    @Published var backgroundTask: String = ""
    @Published var pendingConfirmation: ConfirmationRequest?

    private let client = DaemonClient()
    private var webSocketTask: URLSessionWebSocketTask?
    private var receiveTask: Task<Void, Never>?
    private var pingTask: Task<Void, Never>?

    var menuBarSymbol: String {
        switch agentStatus {
        case "listening": return "mic.fill"
        case "thinking": return "brain.head.profile"
        case "speaking": return "waveform"
        case "background": return "arrow.triangle.2.circlepath"
        case "error": return "exclamationmark.triangle.fill"
        default:
            switch status {
            case .connected: return "face.smiling.inverse"
            case .connecting: return "arrow.triangle.2.circlepath"
            case .error: return "exclamationmark.triangle.fill"
            case .disconnected: return "face.dashed"
            }
        }
    }

    var isListening: Bool { agentStatus == "listening" }

    func connect() {
        guard status != .connecting && status != .connected else { return }
        status = .connecting
        errorMessage = nil

        Task {
            do {
                let health = try await client.fetchHealth()
                ollamaReachable = health.ollama
                agentStatus = health.agentStatus
                try await openWebSocket()
                status = .connected
                startPingLoop()
            } catch {
                status = .error
                errorMessage = error.localizedDescription
            }
        }
    }

    func disconnect() {
        pingTask?.cancel()
        receiveTask?.cancel()
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        webSocketTask = nil
        status = .disconnected
    }

    func reconnect() {
        disconnect()
        connect()
    }

    func sendEvent(_ type: String) async throws {
        try await sendJSON(["type": type])
    }

    func submitVoiceTurn(fileURL: URL) async throws -> VoiceTurnResponse {
        try await client.submitVoiceTurn(fileURL: fileURL)
    }

    func sendConfirmResponse(requestId: String, approved: Bool) async throws {
        try await sendJSON([
            "type": "confirm_response",
            "request_id": requestId,
            "approved": approved,
        ])
    }

    func sendInjectResult(ok: Bool, detail: String) async {
        try? await sendJSON([
            "type": "inject_result",
            "ok": ok,
            "detail": detail,
        ])
    }

    func respondToConfirmation(approved: Bool) async {
        guard let request = pendingConfirmation else { return }
        pendingConfirmation = nil
        try? await sendJSON([
            "type": "confirm_response",
            "request_id": request.id,
            "approved": approved,
        ])
    }

    private func openWebSocket() async throws {
        let task = try client.makeWebSocketTask()
        webSocketTask = task
        task.resume()

        receiveTask = Task { [weak self] in
            await self?.receiveLoop(task: task)
        }

        try await sendJSON(["type": "get_state"])
    }

    private func receiveLoop(task: URLSessionWebSocketTask) async {
        while !Task.isCancelled {
            do {
                let message = try await task.receive()
                switch message {
                case .string(let text):
                    await handleMessage(text)
                case .data(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        await handleMessage(text)
                    }
                @unknown default:
                    break
                }
            } catch {
                if !Task.isCancelled {
                    status = .error
                    errorMessage = error.localizedDescription
                }
                break
            }
        }
    }

    private func handleMessage(_ text: String) async {
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else { return }

        switch type {
        case "state":
            if let s = json["status"] as? String {
                agentStatus = s
            }
            if let task = json["background_task"] as? String {
                backgroundTask = task
            }
        case "transcript":
            if let t = json["text"] as? String {
                lastTranscript = t
            }
        case "reply":
            if let t = json["text"] as? String {
                lastReply = t
            }
        case "pong":
            if let ms = json["latency_ms"] as? Double {
                lastLatencyMs = ms
            }
        case "error":
            errorMessage = json["message"] as? String
        case "confirm_request":
            let requestId = json["request_id"] as? String ?? UUID().uuidString
            let action = json["action"] as? String ?? "action"
            let message = (json["message"] as? String) ?? (json["title"] as? String) ?? "Allow this action?"
            let detail = (json["path"] as? String) ?? (json["command"] as? String) ?? (json["detail"] as? String) ?? ""
            pendingConfirmation = ConfirmationRequest(
                id: requestId,
                action: action,
                message: message,
                detail: detail
            )
        case "inject_text":
            if let text = json["text"] as? String {
                let ok = AXTextInjector.inject(text)
                if !ok {
                    errorMessage = "Text injection failed. Grant Accessibility access in System Settings."
                }
                try? await sendJSON([
                    "type": "inject_result",
                    "ok": ok,
                    "detail": ok ? "" : "Accessibility not granted or no focused field",
                ])
            }
        default:
            break
        }
    }

    private func startPingLoop() {
        pingTask?.cancel()
        pingTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 5_000_000_000)
                try? await self?.sendJSON(["type": "ping"])
            }
        }
    }

    private func sendJSON(_ object: [String: Any]) async throws {
        guard let task = webSocketTask else { return }
        let data = try JSONSerialization.data(withJSONObject: object)
        guard let text = String(data: data, encoding: .utf8) else { return }
        try await task.send(.string(text))
    }
}
