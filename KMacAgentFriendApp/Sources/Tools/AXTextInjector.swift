import AppKit
import ApplicationServices
import Foundation

/// Type text into the focused UI element when Accessibility is granted.
@MainActor
enum AXTextInjector {
    static var isTrusted: Bool { AXIsProcessTrusted() }

    static func inject(_ text: String) -> Bool {
        guard isTrusted, !text.isEmpty else { return false }

        let system = AXUIElementCreateSystemWide()
        var focusedValue: CFTypeRef?
        let copyResult = AXUIElementCopyAttributeValue(
            system,
            kAXFocusedUIElementAttribute as CFString,
            &focusedValue
        )
        guard copyResult == .success, let focusedValue else { return false }

        let element = focusedValue as! AXUIElement
        if AXUIElementSetAttributeValue(element, kAXValueAttribute as CFString, text as CFTypeRef) == .success {
            return true
        }

        // Fallback: paste via clipboard for fields that reject direct value set.
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(text, forType: .string)
        return AXUIElementPerformAction(element, kAXPressAction as CFString) == .success
            || simulatePaste()
    }

    private static func simulatePaste() -> Bool {
        let source = CGEventSource(stateID: .hidSystemState)
        let keyVDown = CGEvent(keyboardEventSource: source, virtualKey: 0x09, keyDown: true)
        keyVDown?.flags = .maskCommand
        let keyVUp = CGEvent(keyboardEventSource: source, virtualKey: 0x09, keyDown: false)
        keyVUp?.flags = .maskCommand
        keyVDown?.post(tap: .cghidEventTap)
        keyVUp?.post(tap: .cghidEventTap)
        return true
    }
}
