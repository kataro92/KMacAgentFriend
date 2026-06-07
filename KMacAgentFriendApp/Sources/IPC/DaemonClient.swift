import Foundation

struct HealthResponse: Decodable {
    let ok: Bool
    let ollama: Bool
    let agent: AgentInfo

    struct AgentInfo: Decodable {
        let status: String
    }

    var agentStatus: String { agent.status }
}

final class DaemonClient {
    private let host = "127.0.0.1"
    private let port = 18750

    private var baseURL: URL {
        URL(string: "http://\(host):\(port)")!
    }

    private var apiToken: String {
        if let env = ProcessInfo.processInfo.environment["KAF_API_TOKEN"], !env.isEmpty {
            return env
        }
        let tokenPath = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/KMacAgentFriend/.api_token")
        return (try? String(contentsOf: tokenPath, encoding: .utf8))?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    }

    func fetchHealth() async throws -> HealthResponse {
        var request = URLRequest(url: baseURL.appendingPathComponent("health"))
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw DaemonError.httpError((response as? HTTPURLResponse)?.statusCode ?? -1)
        }
        return try JSONDecoder().decode(HealthResponse.self, from: data)
    }

    func makeWebSocketTask() throws -> URLSessionWebSocketTask {
        guard !apiToken.isEmpty else {
            throw DaemonError.missingToken
        }
        var components = URLComponents()
        components.scheme = "ws"
        components.host = host
        components.port = port
        components.path = "/ws"
        components.queryItems = [URLQueryItem(name: "token", value: apiToken)]

        guard let url = components.url else {
            throw DaemonError.invalidURL
        }
        return URLSession.shared.webSocketTask(with: url)
    }
}

enum DaemonError: LocalizedError {
    case missingToken
    case invalidURL
    case httpError(Int)

    var errorDescription: String? {
        switch self {
        case .missingToken:
            return "No API token. Start the Python daemon first or set KAF_API_TOKEN."
        case .invalidURL:
            return "Invalid daemon WebSocket URL."
        case .httpError(let code):
            return "Daemon HTTP error (\(code)). Is the Python daemon running?"
        }
    }
}
