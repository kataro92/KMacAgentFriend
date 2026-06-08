import AppKit
import Combine
import Foundation

/// Push-to-talk: Right Option global hotkey when Accessibility is granted,
/// plus a programmatic API used by the menu bar hold button.
@MainActor
final class PTTController: ObservableObject {
    @Published private(set) var isPressed = false

    var onPress: (() -> Void)?
    var onRelease: (() -> Void)?

    private var flagsMonitor: Any?
    private var localMonitor: Any?

    func start() {
        stop()
        flagsMonitor = NSEvent.addGlobalMonitorForEvents(matching: .flagsChanged) { [weak self] event in
            Task { @MainActor in
                self?.handleFlagsChanged(event)
            }
        }
        localMonitor = NSEvent.addLocalMonitorForEvents(matching: .flagsChanged) { [weak self] event in
            Task { @MainActor in
                self?.handleFlagsChanged(event)
            }
            return event
        }
    }

    func stop() {
        if let flagsMonitor {
            NSEvent.removeMonitor(flagsMonitor)
            self.flagsMonitor = nil
        }
        if let localMonitor {
            NSEvent.removeMonitor(localMonitor)
            self.localMonitor = nil
        }
        if isPressed {
            isPressed = false
            onRelease?()
        }
    }

    func press() {
        guard !isPressed else { return }
        isPressed = true
        onPress?()
    }

    func release() {
        guard isPressed else { return }
        isPressed = false
        onRelease?()
    }

    private func handleFlagsChanged(_ event: NSEvent) {
        // keyCode 61 = Right Option on US keyboards
        guard event.keyCode == 61 else { return }
        let optionDown = event.modifierFlags.intersection(.deviceIndependentFlagsMask).contains(.option)
        if optionDown && !isPressed {
            press()
        } else if !optionDown && isPressed {
            release()
        }
    }
}
