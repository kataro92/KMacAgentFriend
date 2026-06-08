import AppKit
import Foundation

/// Resolves the repo root and keeps security-scoped access for external volumes.
@MainActor
enum ProjectRootAccess {
    private static let bookmarkKey = "kafProjectRootBookmark"
    private static var scopedURL: URL?

    static func resolveRoot() -> URL? {
        if let bookmarked = loadBookmarkedRoot(), DaemonProcessManager.isProjectRoot(bookmarked) {
            return bookmarked
        }
        return DaemonProcessManager.findProjectRoot()
    }

    static func beginAccess(to root: URL) -> Bool {
        endAccess()
        if root.startAccessingSecurityScopedResource() {
            scopedURL = root
            return true
        }
        return canReadProject(at: root)
    }

    static func endAccess() {
        scopedURL?.stopAccessingSecurityScopedResource()
        scopedURL = nil
    }

    static func canReadProject(at root: URL) -> Bool {
        let python = root.appendingPathComponent(".venv/bin/python")
        guard FileManager.default.isExecutableFile(atPath: python.path) else { return false }
        return (try? Data(contentsOf: python, options: .mappedIfSafe).prefix(1)) != nil
    }

    @discardableResult
    static func requestFolderAccess() -> URL? {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.message = "Select your KMacAgentFriend project folder"
        panel.prompt = "Grant Access"
        guard panel.runModal() == .OK, let url = panel.url else { return nil }
        guard DaemonProcessManager.isProjectRoot(url) else { return nil }
        saveBookmark(url)
        _ = beginAccess(to: url)
        return url
    }

    private static func loadBookmarkedRoot() -> URL? {
        guard let data = UserDefaults.standard.data(forKey: bookmarkKey) else { return nil }
        var stale = false
        return try? URL(
            resolvingBookmarkData: data,
            options: [.withSecurityScope],
            relativeTo: nil,
            bookmarkDataIsStale: &stale
        )
    }

    private static func saveBookmark(_ url: URL) {
        guard let data = try? url.bookmarkData(
            options: .withSecurityScope,
            includingResourceValuesForKeys: nil,
            relativeTo: nil
        ) else { return }
        UserDefaults.standard.set(data, forKey: bookmarkKey)
    }
}
