import Foundation

/// Runtime data lives under ``<project>/data`` (not Application Support).
enum AppDataPaths {
    static let legacyDataDir = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Application Support/KMacAgentFriend", isDirectory: true)

    static func dataDirectory(projectRoot: URL) -> URL {
        projectRoot.appendingPathComponent("data", isDirectory: true)
    }

    static func logsDirectory(projectRoot: URL) -> URL {
        dataDirectory(projectRoot: projectRoot).appendingPathComponent("logs", isDirectory: true)
    }

    static func apiTokenFile(projectRoot: URL) -> URL {
        dataDirectory(projectRoot: projectRoot).appendingPathComponent(".api_token")
    }

    static func resolveProjectRoot() -> URL? {
        ProjectRootAccess.resolveRoot() ?? DaemonProcessManager.findProjectRoot()
    }

    static func resolveApiToken(projectRoot: URL? = nil) -> String? {
        if let env = ProcessInfo.processInfo.environment["KAF_API_TOKEN"], !env.isEmpty {
            return env
        }
        if let stored = KeychainStore.apiToken, !stored.isEmpty {
            return stored
        }

        let root = projectRoot ?? resolveProjectRoot()
        if let root {
            let path = apiTokenFile(projectRoot: root)
            if let token = try? String(contentsOf: path, encoding: .utf8)?
                .trimmingCharacters(in: .whitespacesAndNewlines),
               !token.isEmpty {
                return token
            }
        }

        let legacyPath = legacyDataDir.appendingPathComponent(".api_token")
        if let token = try? String(contentsOf: legacyPath, encoding: .utf8)?
            .trimmingCharacters(in: .whitespacesAndNewlines),
           !token.isEmpty {
            return token
        }
        return nil
    }
}
