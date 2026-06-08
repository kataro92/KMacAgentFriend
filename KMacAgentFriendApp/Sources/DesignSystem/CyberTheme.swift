import AppKit
import SwiftUI

/// Cyberpunk / glitch design tokens — single source of truth for the macOS UI.
enum CyberTheme {
  // MARK: - Colors

  static let background = Color(hex: 0x0a0a0f)
  static let foreground = Color(hex: 0xe0e0e0)
  static let card = Color(hex: 0x12121a)
  static let muted = Color(hex: 0x1c1c2e)
  static let mutedForeground = Color(hex: 0x6b7280)
  static let accent = Color(hex: 0x00ff88)
  static let accentSecondary = Color(hex: 0xff00ff)
  static let accentTertiary = Color(hex: 0x00d4ff)
  static let border = Color(hex: 0x2a2a3a)
  static let input = Color(hex: 0x12121a)
  static let destructive = Color(hex: 0xff3366)

  // MARK: - Layout

  static let chamfer: CGFloat = 10
  static let chamferSm: CGFloat = 6
  static let spacing: CGFloat = 8
  static let panelWidth: CGFloat = 320

  // MARK: - Status mapping

  static func statusColor(for status: String) -> Color {
    switch status.lowercased() {
    case "connected", "online", "idle", "listening": return accent
    case "connecting", "thinking", "background": return accentTertiary
    case "speaking": return accentSecondary
    case "error", "offline": return destructive
    default: return mutedForeground
    }
  }

  static func levelColor(_ level: String) -> Color {
    switch level.lowercased() {
    case "error": return destructive
    case "warn", "warning": return Color(hex: 0xffaa00)
    case "debug": return accentSecondary
    default: return accentTertiary
    }
  }
}

extension Color {
  init(hex: UInt32, opacity: Double = 1) {
    let r = Double((hex >> 16) & 0xff) / 255
    let g = Double((hex >> 8) & 0xff) / 255
    let b = Double(hex & 0xff) / 255
    self.init(.sRGB, red: r, green: g, blue: b, opacity: opacity)
  }
}

enum CyberFont {
  static func heading(_ size: CGFloat) -> Font {
    if NSFont(name: "Orbitron-Bold", size: size) != nil {
      return .custom("Orbitron-Bold", size: size)
    }
    return .system(size: size, weight: .black, design: .monospaced)
  }

  static func title(_ size: CGFloat) -> Font {
    if NSFont(name: "Orbitron-Medium", size: size) != nil {
      return .custom("Orbitron-Medium", size: size)
    }
    return .system(size: size, weight: .bold, design: .monospaced)
  }

  static let body = Font.system(.body, design: .monospaced)
  static let caption = Font.system(.caption, design: .monospaced)
  static let label = Font.system(.caption2, design: .monospaced).weight(.semibold)
}
