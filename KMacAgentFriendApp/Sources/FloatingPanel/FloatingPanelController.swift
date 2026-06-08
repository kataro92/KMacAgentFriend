import AppKit
import Combine
import SwiftUI

/// Always-on-top floating HUD window (pixel robot head).
@MainActor
final class FloatingPanelController: NSObject, ObservableObject, NSWindowDelegate {
    @Published private(set) var isVisible = false

    private var panel: NSPanel?
    private weak var connection: DaemonConnection?
    private weak var voice: VoiceSession?

    func bind(connection: DaemonConnection, voice: VoiceSession) {
        self.connection = connection
        self.voice = voice
    }

    func toggle() {
        if isVisible {
            hide()
        } else {
            show()
        }
    }

    func show() {
        guard let connection, let voice else { return }

        if panel == nil {
            let panel = NSPanel(
                contentRect: NSRect(x: 0, y: 0, width: 260, height: 340),
                styleMask: [.nonactivatingPanel, .titled, .closable, .fullSizeContentView],
                backing: .buffered,
                defer: false
            )
            panel.isFloatingPanel = true
            panel.level = .floating
            panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
            panel.titleVisibility = .hidden
            panel.titlebarAppearsTransparent = true
            panel.isMovableByWindowBackground = true
            panel.backgroundColor = .clear
            panel.isReleasedWhenClosed = false
            panel.hidesOnDeactivate = false
            panel.delegate = self

            let hud = FloatingHUDView()
                .environmentObject(connection)
                .environmentObject(voice)
            panel.contentView = NSHostingView(rootView: hud)
            self.panel = panel
        }

        panel?.center()
        panel?.orderFrontRegardless()
        isVisible = true
    }

    func hide() {
        panel?.orderOut(nil)
        isVisible = false
    }

    func windowWillClose(_ notification: Notification) {
        isVisible = false
    }
}
