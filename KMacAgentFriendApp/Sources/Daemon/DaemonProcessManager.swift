import Foundation

enum DaemonProcessError: LocalizedError {
    case projectRootNotFound
    case venvMissing(String)
    case startFailed(String)
    case startupTimeout

    var errorDescription: String? {
        switch self {
        case .projectRootNotFound:
            return "Could not find the KMacAgentFriend project folder (.venv missing)."
        case .venvMissing(let path):
            return "Python venv not found at \(path). Run: make install"
        case .startFailed(let detail):
            return "Failed to start daemon: \(detail)"
        case .startupTimeout:
            return "Daemon did not become healthy in time."
        }
    }
}

/// Starts and stops the Python daemon when the menu bar app launches and quits.
@MainActor
final class DaemonProcessManager: ObservableObject {
    static let shared = DaemonProcessManager()

    @Published private(set) var managedByApp = false
    @Published private(set) var lastError: String?

    private var process: Process?
    private let host = "127.0.0.1"
    private let port = 18750
    /// Bump when daemon API/settings behavior changes; stale daemons are restarted.
    private let requiredApiVersion = 4

    private init() {}

    func startIfNeeded() async {
        lastError = nil

        if await isHealthy() {
            if await supportsCurrentAPI() {
                managedByApp = false
                ActivityLogStore.shared.log(level: "info", category: "daemon", message: "Daemon already running")
                return
            }
            ActivityLogStore.shared.log(
                level: "warn",
                category: "daemon",
                message: "Outdated daemon detected — restarting with current code"
            )
            await terminateStaleDaemonIfNeeded()
        }

        guard var root = ProjectRootAccess.resolveRoot() else {
            lastError = DaemonProcessError.projectRootNotFound.localizedDescription
            return
        }

        if !ProjectRootAccess.canReadProject(at: root) {
            if let granted = ProjectRootAccess.requestFolderAccess() {
                root = granted
            } else {
                lastError = """
                Cannot access the project folder (external drives need one-time folder permission). \
                Open Settings → choose the KMacAgentFriend repo, or move the project to your home folder.
                """
                return
            }
        }

        guard ProjectRootAccess.beginAccess(to: root) else {
            lastError = "Could not access project files at \(root.path)."
            return
        }

        let python = root.appendingPathComponent(".venv/bin/python")
        guard FileManager.default.isExecutableFile(atPath: python.path) else {
            ProjectRootAccess.endAccess()
            lastError = DaemonProcessError.venvMissing(python.path).localizedDescription
            return
        }

        await terminateStaleDaemonIfNeeded()

        let proc = Process()
        proc.executableURL = python
        proc.arguments = ["-m", "kmac_agent_friend.main"]
        proc.currentDirectoryURL = root
        proc.environment = Self.daemonEnvironment(projectRoot: root)
        proc.standardOutput = FileHandle.nullDevice
        proc.standardError = Self.daemonLogHandle()

        do {
            try proc.run()
        } catch {
            ProjectRootAccess.endAccess()
            lastError = DaemonProcessError.startFailed(error.localizedDescription).localizedDescription
            return
        }

        process = proc
        managedByApp = true
        ActivityLogStore.shared.log(
            level: "info",
            category: "daemon",
            message: "Started Python daemon",
            detail: python.path
        )

        let ready = await waitForHealthy(timeoutSeconds: 30)
        if !ready {
            lastError = DaemonProcessError.startupTimeout.localizedDescription
            ActivityLogStore.shared.log(level: "error", category: "daemon", message: "Daemon startup timeout")
            stopIfManaged()
        } else {
            ActivityLogStore.shared.log(level: "info", category: "daemon", message: "Daemon healthy")
        }
    }

    func stopIfManaged() {
        stopManagedProcess()
    }

    /// Called from `applicationWillTerminate` — must complete before the app exits.
    nonisolated func stopIfManagedSynchronously() {
        if Thread.isMainThread {
            MainActor.assumeIsolated {
                stopManagedProcess()
            }
        } else {
            DispatchQueue.main.sync {
                MainActor.assumeIsolated {
                    stopManagedProcess()
                }
            }
        }
    }

    private func stopManagedProcess() {
        guard managedByApp, let proc = process else { return }
        if proc.isRunning {
            proc.terminate()
            let deadline = Date().addingTimeInterval(3)
            while proc.isRunning && Date() < deadline {
                Thread.sleep(forTimeInterval: 0.1)
            }
            if proc.isRunning {
                proc.interrupt()
            }
        }
        process = nil
        managedByApp = false
        ProjectRootAccess.endAccess()
        ActivityLogStore.shared.log(level: "info", category: "daemon", message: "Stopped managed daemon")
    }

    private func waitForHealthy(timeoutSeconds: TimeInterval) async -> Bool {
        let deadline = Date().addingTimeInterval(timeoutSeconds)
        while Date() < deadline {
            if await isHealthy() { return true }
            try? await Task.sleep(nanoseconds: 250_000_000)
        }
        return false
    }

    private func isHealthy() async -> Bool {
        if let token = Self.readApiToken(), !token.isEmpty {
            return await healthCheck(token: token)
        }
        return await portIsOpen()
    }

    /// Detect an old daemon left on :18750 from a previous code version.
    private func supportsCurrentAPI() async -> Bool {
        guard let token = Self.readApiToken(), !token.isEmpty else { return false }
        guard let base = URL(string: "http://\(host):\(port)/"),
              let activityURL = URL(string: "api/activity?limit=1", relativeTo: base),
              let healthURL = URL(string: "health", relativeTo: base) else {
            return false
        }

        var activityRequest = URLRequest(url: activityURL)
        activityRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        activityRequest.timeoutInterval = 3

        var healthRequest = URLRequest(url: healthURL)
        healthRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        healthRequest.timeoutInterval = 3

        do {
            let (_, activityResponse) = try await URLSession.shared.data(for: activityRequest)
            guard (activityResponse as? HTTPURLResponse)?.statusCode == 200 else { return false }

            let (healthData, healthResponse) = try await URLSession.shared.data(for: healthRequest)
            guard (healthResponse as? HTTPURLResponse)?.statusCode == 200 else { return false }
            guard let json = try JSONSerialization.jsonObject(with: healthData) as? [String: Any],
                  let apiVersion = json["api_version"] as? Int else {
                return false
            }
            return apiVersion >= requiredApiVersion
        } catch {
            return false
        }
    }

    private func portIsOpen() async -> Bool {
        let script = "lsof -nP -iTCP:\(port) -sTCP:LISTEN >/dev/null 2>&1"
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/bin/bash")
        proc.arguments = ["-c", script]
        let pipe = Pipe()
        proc.standardOutput = pipe
        proc.standardError = pipe
        do {
            try proc.run()
            proc.waitUntilExit()
            return proc.terminationStatus == 0
        } catch {
            return false
        }
    }

    private func healthCheck(token: String) async -> Bool {
        guard let url = URL(string: "http://\(host):\(port)/health") else { return false }

        var request = URLRequest(url: url)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.timeoutInterval = 2

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    private func terminateStaleDaemonIfNeeded() async {
        // Best-effort: stop orphaned dev daemons before spawning a fresh one.
        let script = """
        for pid in $(pgrep -f "kmac_agent_friend.main" 2>/dev/null); do
          kill "$pid" 2>/dev/null
        done
        pid=$(lsof -nP -iTCP:\(port) -sTCP:LISTEN -t 2>/dev/null | head -1)
        if [ -n "$pid" ]; then
          kill "$pid" 2>/dev/null
        fi
        """
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/bin/bash")
        proc.arguments = ["-c", script]
        try? proc.run()
        proc.waitUntilExit()
        try? await Task.sleep(nanoseconds: 500_000_000)
    }

    private static func daemonLogHandle() -> FileHandle {
        let logDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/KMacAgentFriend", isDirectory: true)
        try? FileManager.default.createDirectory(at: logDir, withIntermediateDirectories: true)
        let logURL = logDir.appendingPathComponent("daemon.log")
        if !FileManager.default.fileExists(atPath: logURL.path) {
            FileManager.default.createFile(atPath: logURL.path, contents: nil)
        }
        if let handle = try? FileHandle(forWritingTo: logURL) {
            handle.seekToEndOfFile()
            return handle
        }
        return FileHandle.nullDevice
    }

    /// Avoid inheriting the menu bar app's environment — it can hang Python startup.
    private static func daemonEnvironment(projectRoot: URL) -> [String: String] {
        let venv = projectRoot.appendingPathComponent(".venv")
        let inherited = ProcessInfo.processInfo.environment
        var env: [String: String] = [
            "HOME": FileManager.default.homeDirectoryForCurrentUser.path,
            "USER": NSUserName(),
            "LOGNAME": NSUserName(),
            "SHELL": inherited["SHELL"] ?? "/bin/zsh",
            "LANG": inherited["LANG"] ?? "en_US.UTF-8",
            "PYTHONUNBUFFERED": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "VIRTUAL_ENV": venv.path,
            "PATH": "\(venv.path)/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        ]
        for key in ["KAF_API_TOKEN", "KAF_DATA_DIR", "KAF_PROJECT_ROOT", "OLLAMA_HOST", "OLLAMA_MODEL", "HF_TOKEN", "WHISPER_MODEL"] {
            if let value = inherited[key], !value.isEmpty {
                env[key] = value
            }
        }
        for key in ["HF_TOKEN", "WHISPER_MODEL"] {
            if env[key] != nil { continue }
            if let value = readDotEnvValue(key: key, projectRoot: projectRoot), !value.isEmpty {
                env[key] = value
                if key == "HF_TOKEN" {
                    env["HUGGING_FACE_HUB_TOKEN"] = value
                }
            }
        }
        return env
    }

    private static func readDotEnvValue(key: String, projectRoot: URL) -> String? {
        let envURL = projectRoot.appendingPathComponent(".env")
        guard let text = try? String(contentsOf: envURL, encoding: .utf8) else { return nil }
        for lineSub in text.split(separator: "\n", omittingEmptySubsequences: false) {
            var line = lineSub.trimmingCharacters(in: .whitespaces)
            if line.isEmpty || line.hasPrefix("#") { continue }
            guard let eq = line.firstIndex(of: "=") else { continue }
            let name = String(line[..<eq]).trimmingCharacters(in: .whitespaces)
            guard name == key else { continue }
            var value = String(line[line.index(after: eq)...]).trimmingCharacters(in: .whitespaces)
            if (value.hasPrefix("\"") && value.hasSuffix("\"")) || (value.hasPrefix("'") && value.hasSuffix("'")) {
                value = String(value.dropFirst().dropLast())
            }
            return value
        }
        return nil
    }

    static func findProjectRoot() -> URL? {
        if let env = ProcessInfo.processInfo.environment["KAF_PROJECT_ROOT"],
           !env.isEmpty,
           isProjectRoot(URL(fileURLWithPath: env)) {
            return URL(fileURLWithPath: env)
        }

        if let plist = Bundle.main.object(forInfoDictionaryKey: "KAFProjectRoot") as? String,
           !plist.isEmpty,
           !plist.contains("$"),
           isProjectRoot(URL(fileURLWithPath: plist)) {
            return URL(fileURLWithPath: plist)
        }

        var url = Bundle.main.bundleURL
        for _ in 0..<10 {
            if isProjectRoot(url) { return url }
            let parent = url.deletingLastPathComponent()
            if parent.path == url.path { break }
            url = parent
        }

        return nil
    }

    static func isProjectRoot(_ url: URL) -> Bool {
        let venvPython = url.appendingPathComponent(".venv/bin/python")
        let mainPy = url.appendingPathComponent("agent/kmac_agent_friend/main.py")
        return FileManager.default.isExecutableFile(atPath: venvPython.path)
            && FileManager.default.fileExists(atPath: mainPy.path)
    }

    static func readApiToken() -> String? {
        if let env = ProcessInfo.processInfo.environment["KAF_API_TOKEN"], !env.isEmpty {
            return env
        }
        let tokenPath = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/KMacAgentFriend/.api_token")
        return try? String(contentsOf: tokenPath, encoding: .utf8)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
