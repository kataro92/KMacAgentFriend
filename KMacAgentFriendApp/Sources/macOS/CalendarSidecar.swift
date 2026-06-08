import EventKit
import Foundation

struct CalendarEventSummary: Identifiable {
    let id: String
    let title: String
    let start: Date
    let end: Date
    let calendar: String
}

struct ReminderSummary: Identifiable {
    let id: String
    let title: String
    let dueDate: Date?
    let completed: Bool
}

/// EventKit bridge for reading upcoming calendar events and reading/creating
/// reminders. Access is permission-gated and only invoked on demand.
final class CalendarSidecar {
    private let store = EKEventStore()

    // MARK: Authorization

    func requestCalendarAccess() async -> Bool {
        if #available(macOS 14.0, *) {
            return (try? await store.requestFullAccessToEvents()) ?? false
        } else {
            return await withCheckedContinuation { cont in
                store.requestAccess(to: .event) { granted, _ in cont.resume(returning: granted) }
            }
        }
    }

    func requestReminderAccess() async -> Bool {
        if #available(macOS 14.0, *) {
            return (try? await store.requestFullAccessToReminders()) ?? false
        } else {
            return await withCheckedContinuation { cont in
                store.requestAccess(to: .reminder) { granted, _ in cont.resume(returning: granted) }
            }
        }
    }

    // MARK: Calendar

    func upcomingEvents(within days: Int = 7) async -> [CalendarEventSummary] {
        guard await requestCalendarAccess() else { return [] }
        let now = Date()
        let end = Calendar.current.date(byAdding: .day, value: days, to: now) ?? now
        let predicate = store.predicateForEvents(withStart: now, end: end, calendars: nil)
        return store.events(matching: predicate)
            .sorted { $0.startDate < $1.startDate }
            .map {
                CalendarEventSummary(
                    id: $0.eventIdentifier ?? UUID().uuidString,
                    title: $0.title ?? "(untitled)",
                    start: $0.startDate,
                    end: $0.endDate,
                    calendar: $0.calendar?.title ?? ""
                )
            }
    }

    // MARK: Reminders

    func openReminders() async -> [ReminderSummary] {
        guard await requestReminderAccess() else { return [] }
        let predicate = store.predicateForReminders(in: nil)
        let reminders: [EKReminder] = await withCheckedContinuation { cont in
            store.fetchReminders(matching: predicate) { cont.resume(returning: $0 ?? []) }
        }
        return reminders
            .filter { !$0.isCompleted }
            .map {
                ReminderSummary(
                    id: $0.calendarItemIdentifier,
                    title: $0.title ?? "(untitled)",
                    dueDate: $0.dueDateComponents?.date,
                    completed: $0.isCompleted
                )
            }
    }

    @discardableResult
    func createReminder(title: String, due: Date? = nil) async -> Bool {
        guard await requestReminderAccess() else { return false }
        let reminder = EKReminder(eventStore: store)
        reminder.title = title
        reminder.calendar = store.defaultCalendarForNewReminders()
        if let due {
            reminder.dueDateComponents = Calendar.current.dateComponents(
                [.year, .month, .day, .hour, .minute],
                from: due
            )
        }
        do {
            try store.save(reminder, commit: true)
            return true
        } catch {
            return false
        }
    }
}

private extension DateComponents {
    var date: Date? { Calendar.current.date(from: self) }
}
