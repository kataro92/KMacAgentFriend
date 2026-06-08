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

struct VoiceTurnResponse: Decodable {
    let ok: Bool
    let transcript: String?
    let reply: String?
    let error: String?
}

struct VisionResponse: Decodable {
    let ok: Bool
    let description: String?
    let error: String?
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

    func submitVoiceTurn(fileURL: URL) async throws -> VoiceTurnResponse {
        guard !apiToken.isEmpty else {
            throw DaemonError.missingToken
        }

        let boundary = "KAF-\(UUID().uuidString)"
        var request = URLRequest(url: baseURL.appendingPathComponent("api/voice/turn"))
        request.httpMethod = "POST"
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let audioData = try Data(contentsOf: fileURL)
        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"ptt.wav\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: audio/wav\r\n\r\n".data(using: .utf8)!)
        body.append(audioData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw DaemonError.httpError((response as? HTTPURLResponse)?.statusCode ?? -1)
        }
        return try JSONDecoder().decode(VoiceTurnResponse.self, from: data)
    }

    func submitVisionAnalyze(jpeg: Data, prompt: String, confirmed: Bool) async throws -> VisionResponse {
        guard !apiToken.isEmpty else { throw DaemonError.missingToken }

        var components = URLComponents(url: baseURL.appendingPathComponent("api/vision/analyze"), resolvingAgainstBaseURL: false)!
        if confirmed {
            components.queryItems = [URLQueryItem(name: "confirmed", value: "true")]
        }

        let boundary = "KAF-\(UUID().uuidString)"
        var request = URLRequest(url: components.url!)
        request.httpMethod = "POST"
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"capture.jpg\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(jpeg)
        body.append("\r\n--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"prompt\"\r\n\r\n".data(using: .utf8)!)
        body.append(prompt.data(using: .utf8)!)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw DaemonError.httpError((response as? HTTPURLResponse)?.statusCode ?? -1)
        }
        return try JSONDecoder().decode(VisionResponse.self, from: data)
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
