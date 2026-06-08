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
    let language: String?
    let error: String?
}

struct SpeakResponse: Decodable {
    let ok: Bool
    let voice: String?
    let error: String?
}

struct VisionResponse: Decodable {
    let ok: Bool
    let description: String?
    let error: String?
}

struct SettingsPayload {
    let settings: AppSettings
    let userSettingsPath: String
    let dataDirPath: String
}

struct OllamaModelsResult {
    let reachable: Bool
    let models: [String]
}

struct VoiceModelStatus {
    let model: String
    let cached: Bool
    let ready: Bool
    let downloadInProgress: Bool
    let needsDownload: Bool
    let mlxWhisper: Bool
}

struct VoiceDownloadResult {
    let ok: Bool
    let model: String
    let state: String
    let error: String?
}

struct AutopilotPolicy {
    let enabled: Bool
    let allowedActions: [String]
}

struct DecisionEntry: Identifiable {
    let id: Int
    let ts: Double
    let action: String
    let allowed: Bool
    let reason: String
    let summary: String

    init(payload: [String: Any]) {
        id = payload["id"] as? Int ?? Int.random(in: 0..<Int.max)
        ts = payload["ts"] as? Double ?? 0
        action = payload["action"] as? String ?? ""
        allowed = payload["allowed"] as? Bool ?? false
        reason = payload["reason"] as? String ?? ""
        summary = payload["summary"] as? String ?? ""
    }
}

struct Mission: Identifiable {
    let id: String
    let title: String
    let description: String
    let status: String
    let progress: Int

    init(payload: [String: Any]) {
        id = payload["id"] as? String ?? UUID().uuidString
        title = payload["title"] as? String ?? ""
        description = payload["description"] as? String ?? ""
        status = payload["status"] as? String ?? "pending"
        progress = payload["progress"] as? Int ?? 0
    }
}

final class DaemonClient {
    private let host = "127.0.0.1"
    private let port = 18750

    /// Voice turns include STT + Ollama + TTS; first Whisper load can take several minutes.
    private static let longSession: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 300
        config.timeoutIntervalForResource = 600
        return URLSession(configuration: config)
    }()

    private var baseURL: URL {
        URL(string: "http://\(host):\(port)/")!
    }

    /// Build daemon URLs; supports query strings (appendingPathComponent encodes `?`).
    private func daemonURL(path: String) -> URL {
        URL(string: path, relativeTo: baseURL) ?? baseURL.appendingPathComponent(path)
    }

    private var apiToken: String {
        if let env = ProcessInfo.processInfo.environment["KAF_API_TOKEN"], !env.isEmpty {
            return env
        }
        let tokenPath = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/KMacAgentFriend/.api_token")
        return (try? String(contentsOf: tokenPath, encoding: .utf8))?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    }

    func fetchSettings() async throws -> SettingsPayload {
        let data = try await authorizedGET(path: "api/settings")
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        guard let settingsObj = json?["settings"] as? [String: Any],
              let settingsData = try? JSONSerialization.data(withJSONObject: settingsObj),
              let settings = try? JSONDecoder().decode(AppSettings.self, from: settingsData) else {
            throw DaemonError.invalidResponse
        }
        let paths = json?["paths"] as? [String: Any] ?? [:]
        return SettingsPayload(
            settings: settings,
            userSettingsPath: paths["user_settings"] as? String ?? "",
            dataDirPath: paths["data_dir"] as? String ?? ""
        )
    }

    func updateSettings(_ settings: AppSettings) async throws -> AppSettings {
        let body = try JSONEncoder().encode(settings)
        let data = try await authorizedRequest(path: "api/settings", method: "PATCH", body: body)
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        guard let settingsObj = json?["settings"] as? [String: Any],
              let settingsData = try? JSONSerialization.data(withJSONObject: settingsObj),
              let updated = try? JSONDecoder().decode(AppSettings.self, from: settingsData) else {
            throw DaemonError.invalidResponse
        }
        return updated
    }

    func fetchActivity(limit: Int = 200) async throws -> [[String: Any]] {
        let data = try await authorizedGET(path: "api/activity?limit=\(limit)")
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        return json?["entries"] as? [[String: Any]] ?? []
    }

    func clearActivity() async throws {
        _ = try await authorizedRequest(path: "api/activity/clear", method: "POST", body: nil)
    }

    func fetchVoiceStatus(model: String? = nil) async throws -> VoiceModelStatus {
        var path = "api/voice/status"
        if let model, !model.isEmpty {
            let encoded = model.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? model
            path += "?model=\(encoded)"
        }
        let data = try await authorizedGET(path: path)
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
        return VoiceModelStatus(
            model: json["model"] as? String ?? model ?? "",
            cached: json["cached"] as? Bool ?? false,
            ready: json["ready"] as? Bool ?? false,
            downloadInProgress: json["download_in_progress"] as? Bool ?? false,
            needsDownload: json["needs_download"] as? Bool ?? true,
            mlxWhisper: json["mlx_whisper"] as? Bool ?? false
        )
    }

    func downloadWhisperModel(_ model: String) async throws -> VoiceDownloadResult {
        let body = try JSONSerialization.data(withJSONObject: ["model": model])
        let data = try await authorizedRequest(path: "api/voice/download", method: "POST", body: body)
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
        return VoiceDownloadResult(
            ok: json["ok"] as? Bool ?? false,
            model: json["model"] as? String ?? model,
            state: json["state"] as? String ?? "",
            error: json["error"] as? String
        )
    }

    func fetchOllamaModels() async throws -> OllamaModelsResult {
        let data = try await authorizedGET(path: "api/ollama/models")
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        let reachable = json?["reachable"] as? Bool ?? false
        let models = json?["models"] as? [String] ?? []
        return OllamaModelsResult(reachable: reachable, models: models)
    }

    func fetchHealth() async throws -> HealthResponse {
        var request = URLRequest(url: daemonURL(path: "health"))
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
        var request = URLRequest(url: daemonURL(path: "api/voice/turn"))
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
        request.timeoutInterval = 300

        let (data, response) = try await Self.longSession.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw DaemonError.httpError((response as? HTTPURLResponse)?.statusCode ?? -1)
        }
        return try JSONDecoder().decode(VoiceTurnResponse.self, from: data)
    }

    /// Barge-in: ask the daemon to interrupt any in-progress TTS playback.
    @discardableResult
    func stopSpeech() async throws -> Int {
        let data = try await authorizedRequest(path: "api/voice/stop", method: "POST", body: nil)
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
        return json["stopped"] as? Int ?? 0
    }

    // MARK: Autopilot

    func fetchAutopilotPolicy() async throws -> AutopilotPolicy {
        let data = try await authorizedGET(path: "api/autopilot/policy")
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
        return AutopilotPolicy(
            enabled: json["enabled"] as? Bool ?? false,
            allowedActions: json["allowed_actions"] as? [String] ?? []
        )
    }

    func setAutopilot(enabled: Bool) async throws -> AutopilotPolicy {
        let body = try JSONSerialization.data(withJSONObject: ["enabled": enabled])
        let data = try await authorizedRequest(path: "api/autopilot/policy", method: "POST", body: body)
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
        return AutopilotPolicy(
            enabled: json["enabled"] as? Bool ?? false,
            allowedActions: json["allowed_actions"] as? [String] ?? []
        )
    }

    func fetchDecisions(limit: Int = 100) async throws -> [DecisionEntry] {
        let data = try await authorizedGET(path: "api/autopilot/decisions?limit=\(limit)")
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
        let rows = json["decisions"] as? [[String: Any]] ?? []
        return rows.map { DecisionEntry(payload: $0) }
    }

    // MARK: Missions

    func fetchMissions() async throws -> [Mission] {
        let data = try await authorizedGET(path: "api/missions")
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
        let rows = json["missions"] as? [[String: Any]] ?? []
        return rows.map { Mission(payload: $0) }
    }

    func createMission(title: String, description: String) async throws {
        let body = try JSONSerialization.data(withJSONObject: [
            "title": title,
            "description": description,
        ])
        _ = try await authorizedRequest(path: "api/missions", method: "POST", body: body)
    }

    func speakText(_ text: String, language: String = "en") async throws -> SpeakResponse {
        let payload: [String: String] = ["text": text, "language": language]
        let body = try JSONSerialization.data(withJSONObject: payload)
        let data = try await authorizedRequest(path: "api/voice/speak", method: "POST", body: body)
        return try JSONDecoder().decode(SpeakResponse.self, from: data)
    }

    func submitVisionAnalyze(jpeg: Data, prompt: String, confirmed: Bool) async throws -> VisionResponse {
        guard !apiToken.isEmpty else { throw DaemonError.missingToken }

        var components = URLComponents(url: daemonURL(path: "api/vision/analyze"), resolvingAgainstBaseURL: false)!
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

    private func authorizedGET(path: String) async throws -> Data {
        try await authorizedRequest(path: path, method: "GET", body: nil)
    }

    private func authorizedRequest(path: String, method: String, body: Data?) async throws -> Data {
        guard !apiToken.isEmpty else { throw DaemonError.missingToken }
        var request = URLRequest(url: daemonURL(path: path))
        request.httpMethod = method
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw DaemonError.httpError((response as? HTTPURLResponse)?.statusCode ?? -1)
        }
        return data
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
    case invalidResponse
    case httpError(Int)

    var errorDescription: String? {
        switch self {
        case .missingToken:
            return "No API token. Start the Python daemon first or set KAF_API_TOKEN."
        case .invalidURL:
            return "Invalid daemon WebSocket URL."
        case .invalidResponse:
            return "Unexpected response from daemon."
        case .httpError(let code):
            if code == 404 {
                return "Daemon endpoint not found (404). Quit and reopen the app to restart the Python backend."
            }
            return "Daemon HTTP error (\(code)). Is the Python daemon running?"
        }
    }
}
