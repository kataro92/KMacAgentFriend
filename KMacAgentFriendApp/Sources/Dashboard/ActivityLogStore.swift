import Foundation

struct ActivityEntry: Identifiable, Equatable {
    let id: UUID
    let timestamp: Date
    let level: String
    let category: String
    let message: String
    let detail: String?
    let source: String

    init(
        id: UUID = UUID(),
        timestamp: Date = Date(),
        level: String,
        category: String,
        message: String,
        detail: String? = nil,
        source: String = "daemon"
    ) {
        self.id = id
        self.timestamp = timestamp
        self.level = level
        self.category = category
        self.message = message
        self.detail = detail
        self.source = source
    }

    init(daemonPayload: [String: Any]) {
        let ts = daemonPayload["ts"] as? Double ?? Date().timeIntervalSince1970
        self.id = UUID()
        self.timestamp = Date(timeIntervalSince1970: ts)
        self.level = daemonPayload["level"] as? String ?? "info"
        self.category = daemonPayload["category"] as? String ?? "system"
        self.message = daemonPayload["message"] as? String ?? ""
        if let detailDict = daemonPayload["detail"] as? [String: Any],
           let data = try? JSONSerialization.data(withJSONObject: detailDict, options: [.prettyPrinted, .sortedKeys]),
           let text = String(data: data, encoding: .utf8), !text.isEmpty, text != "{}" {
            self.detail = text
        } else {
            self.detail = nil
        }
        self.source = "daemon"
    }

    var levelSymbol: String {
        switch level.lowercased() {
        case "error": return "exclamationmark.octagon.fill"
        case "warn", "warning": return "exclamationmark.triangle.fill"
        case "debug": return "ant.fill"
        default: return "info.circle.fill"
        }
    }
}

enum ActivityLevelFilter: String, CaseIterable, Identifiable {
    case all
    case info
    case debug
    case error

    var id: String { rawValue }

    var title: String {
        switch self {
        case .all: return "All"
        case .info: return "Info+"
        case .debug: return "Debug+"
        case .error: return "Errors"
        }
    }

    func matches(_ level: String) -> Bool {
        switch self {
        case .all: return true
        case .info: return level != "debug"
        case .debug: return true
        case .error: return level.lowercased() == "error"
        }
    }
}

@MainActor
final class ActivityLogStore: ObservableObject {
    static let shared = ActivityLogStore()
    private static let maxEntries = 500

    @Published private(set) var entries: [ActivityEntry] = []
    @Published var filter: ActivityLevelFilter = .all
    @Published var categoryFilter: String = "all"
    @Published var autoScroll = true

    private let client = DaemonClient()

    var filteredEntries: [ActivityEntry] {
        entries.filter { entry in
            filter.matches(entry.level)
                && (categoryFilter == "all" || entry.category == categoryFilter)
        }
    }

    var categories: [String] {
        Array(Set(entries.map(\.category))).sorted()
    }

    private init() {}

    func log(
        level: String,
        category: String,
        message: String,
        detail: String? = nil,
        source: String = "app"
    ) {
        append(ActivityEntry(
            level: level,
            category: category,
            message: message,
            detail: detail,
            source: source
        ))
    }

    func append(_ entry: ActivityEntry) {
        if let last = entries.last,
           last.source == entry.source,
           last.category == entry.category,
           last.message == entry.message,
           abs(last.timestamp.timeIntervalSince(entry.timestamp)) < 0.5 {
            return
        }
        entries.append(entry)
        if entries.count > Self.maxEntries {
            entries.removeFirst(entries.count - Self.maxEntries)
        }
    }

    func loadHistory() async {
        do {
            let history = try await client.fetchActivity(limit: 200)
            let daemonEntries = history.map { ActivityEntry(daemonPayload: $0) }
            let appEntries = entries.filter { $0.source == "app" }
            entries = (daemonEntries + appEntries).sorted { $0.timestamp < $1.timestamp }
            if entries.count > Self.maxEntries {
                entries = Array(entries.suffix(Self.maxEntries))
            }
        } catch {
            log(level: "error", category: "app", message: "Failed to load activity history", detail: error.localizedDescription)
        }
    }

    func clear() async {
        entries.removeAll()
        do {
            try await client.clearActivity()
            log(level: "info", category: "app", message: "Activity log cleared")
        } catch {
            log(level: "error", category: "app", message: "Failed to clear daemon activity log", detail: error.localizedDescription)
        }
    }

    func exportText() -> String {
        filteredEntries.map { entry in
            var line = "[\(entry.timestamp.formatted(date: .omitted, time: .standard))] "
            line += "[\(entry.source)/\(entry.category)/\(entry.level)] \(entry.message)"
            if let detail = entry.detail {
                line += "\n  \(detail.replacingOccurrences(of: "\n", with: "\n  "))"
            }
            return line
        }.joined(separator: "\n")
    }
}
