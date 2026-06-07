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

    private let client = DaemonClient()
    private var webSocketTask: URLSessionWebSocketTask?
    private var receiveTask: Task<Void, Never>?
    private var pingTask: Task<Void, Never>?

    var menuBarSymbol: String {
        switch status {
        case .connected: return "face.smiling.inverse"
        case .connecting: return "arrow.triangle.2.circlepath"
        case .error: return "exclamationmark.triangle.fill"
        case .disconnected: return "face.dashed"
        }
    }

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

    private func openWebSocket() async throws {
        let task = try client.makeWebSocketTask()
        webSocketTask = task
        task.resume()

        receiveTask = Task { [weak self] in
            await self?.receiveLoop(task: task)
        }

        // Initial state from server
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
        case "pong":
            if let ms = json["latency_ms"] as? Double {
                lastLatencyMs = ms
            }
        case "error":
            errorMessage = json["message"] as? String
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
