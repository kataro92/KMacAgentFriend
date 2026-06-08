import SwiftUI

// MARK: - Button style

enum CyberButtonVariant {
  case `default`
  case secondary
  case outline
  case ghost
  case glitch
  case destructive
}

struct CyberButtonStyle: ButtonStyle {
  var variant: CyberButtonVariant = .default
  var fullWidth: Bool = false
  @Environment(\.isEnabled) private var isEnabled

  func makeBody(configuration: Configuration) -> some View {
    configuration.label
      .font(CyberFont.caption)
      .textCase(.uppercase)
      .tracking(1.2)
      .padding(.horizontal, 14)
      .padding(.vertical, 8)
      .frame(maxWidth: fullWidth ? .infinity : nil)
      .foregroundStyle(foreground(configuration))
      .background(background(configuration))
      .overlay(border(configuration))
      .cyberChamferClip(CyberTheme.chamferSm)
      .neonGlow(glowColor(configuration), radius: configuration.isPressed ? 4 : 10)
      .opacity(isEnabled ? 1 : 0.45)
      .scaleEffect(configuration.isPressed ? 0.98 : 1)
      .animation(.easeOut(duration: 0.1), value: configuration.isPressed)
  }

  private func foreground(_ configuration: Configuration) -> Color {
    switch variant {
    case .glitch: return CyberTheme.background
    case .ghost: return CyberTheme.accent
    case .destructive: return CyberTheme.destructive
    case .secondary: return CyberTheme.accentSecondary
    case .outline: return configuration.isPressed ? CyberTheme.accent : CyberTheme.foreground
    case .default: return configuration.isPressed ? CyberTheme.background : CyberTheme.accent
    }
  }

  @ViewBuilder
  private func background(_ configuration: Configuration) -> some View {
    switch variant {
    case .glitch:
      CyberTheme.accent.opacity(configuration.isPressed ? 0.85 : 1)
    case .ghost:
      CyberTheme.accent.opacity(configuration.isPressed ? 0.15 : 0.08)
    case .destructive:
      CyberTheme.destructive.opacity(configuration.isPressed ? 0.2 : 0.1)
    case .secondary:
      CyberTheme.accentSecondary.opacity(configuration.isPressed ? 0.2 : 0.08)
    case .outline, .default:
      configuration.isPressed ? CyberTheme.accent.opacity(variant == .default ? 1 : 0.12) : Color.clear
    }
  }

  @ViewBuilder
  private func border(_ configuration: Configuration) -> some View {
    ChamferedRectangle(cut: CyberTheme.chamferSm)
      .stroke(borderColor(configuration), lineWidth: variant == .ghost ? 0 : (variant == .outline ? 1 : 2))
  }

  private func borderColor(_ configuration: Configuration) -> Color {
    switch variant {
    case .secondary: return CyberTheme.accentSecondary
    case .destructive: return CyberTheme.destructive
    case .outline: return configuration.isPressed ? CyberTheme.accent : CyberTheme.border
    case .ghost: return .clear
    case .glitch: return CyberTheme.accent
    case .default: return CyberTheme.accent
    }
  }

  private func glowColor(_ configuration: Configuration) -> Color {
    switch variant {
    case .secondary: return CyberTheme.accentSecondary
    case .destructive: return CyberTheme.destructive
    case .glitch, .default: return CyberTheme.accent
    default: return configuration.isPressed ? CyberTheme.accent : .clear
    }
  }
}

// MARK: - Card

enum CyberCardVariant {
  case `default`
  case terminal
  case holographic
}

struct CyberCard<Content: View>: View {
  var title: String?
  var variant: CyberCardVariant = .default
  var hoverEffect: Bool = false
  @ViewBuilder var content: () -> Content

  @State private var hovering = false

  var body: some View {
    VStack(alignment: .leading, spacing: 12) {
      if variant == .terminal {
        terminalHeader
      } else if let title {
        CyberSectionHeader(title: title)
      }
      content()
    }
    .padding(variant == .terminal ? EdgeInsets(top: 28, leading: 14, bottom: 14, trailing: 14) : EdgeInsets(top: 14, leading: 14, bottom: 14, trailing: 14))
    .frame(maxWidth: .infinity, alignment: .leading)
    .background(cardBackground)
    .overlay(cardBorder)
    .overlay { if variant == .holographic { CyberCornerAccents() } }
    .cyberChamferClip()
    .offset(y: hoverEffect && hovering ? -1 : 0)
    .onHover { hovering = $0 }
    .animation(.easeOut(duration: 0.15), value: hovering)
  }

  @ViewBuilder
  private var cardBackground: some View {
    switch variant {
    case .terminal: CyberTheme.background
    case .holographic: CyberTheme.muted.opacity(0.35)
    case .default: CyberTheme.card
    }
  }

  @ViewBuilder
  private var cardBorder: some View {
    ChamferedRectangle()
      .stroke(
        hovering && hoverEffect ? CyberTheme.accent : borderColor,
        lineWidth: 1
      )
      .neonGlow(hovering && hoverEffect ? CyberTheme.accent : .clear, radius: 6)
  }

  private var borderColor: Color {
    switch variant {
    case .holographic: return CyberTheme.accent.opacity(0.35)
    default: return CyberTheme.border
    }
  }

  private var terminalHeader: some View {
    HStack(spacing: 6) {
      Circle().fill(CyberTheme.destructive).frame(width: 8, height: 8)
      Circle().fill(Color(hex: 0xffaa00)).frame(width: 8, height: 8)
      Circle().fill(CyberTheme.accent).frame(width: 8, height: 8)
      Spacer()
      Text(title ?? "TERMINAL")
        .font(CyberFont.label)
        .foregroundStyle(CyberTheme.mutedForeground)
        .textCase(.uppercase)
    }
    .padding(.horizontal, 12)
    .padding(.vertical, 8)
    .background(CyberTheme.muted.opacity(0.5))
    .frame(maxWidth: .infinity, alignment: .leading)
    .offset(y: -14)
    .padding(.bottom, -8)
  }
}

struct CyberSectionHeader: View {
  let title: String
  var glitch: Bool = false

  var body: some View {
    Text(title.uppercased())
      .font(CyberFont.title(13))
      .tracking(2)
      .foregroundStyle(CyberTheme.accent)
      .cyberGlitchText(glitch)
      .neonGlow(CyberTheme.accent, radius: 4)
  }
}

// MARK: - Inputs & labels

struct CyberTextField: View {
  let label: String
  @Binding var text: String
  var axis: Axis = .horizontal

  var body: some View {
    VStack(alignment: .leading, spacing: 6) {
      Text(label.uppercased())
        .font(CyberFont.label)
        .foregroundStyle(CyberTheme.mutedForeground)
        .tracking(1.5)
      HStack(alignment: axis == .vertical ? .top : .center, spacing: 6) {
        Text(">")
          .font(CyberFont.body)
          .foregroundStyle(CyberTheme.accent)
        if axis == .vertical {
          TextField("", text: $text, axis: .vertical)
            .textFieldStyle(.plain)
            .font(CyberFont.body)
            .foregroundStyle(CyberTheme.accent)
            .lineLimit(2...6)
        } else {
          TextField("", text: $text)
            .textFieldStyle(.plain)
            .font(CyberFont.body)
            .foregroundStyle(CyberTheme.foreground)
        }
      }
      .padding(.horizontal, 10)
      .padding(.vertical, 8)
      .background(CyberTheme.input)
      .overlay(
        ChamferedRectangle(cut: CyberTheme.chamferSm)
          .stroke(CyberTheme.border, lineWidth: 1)
      )
      .cyberChamferClip(CyberTheme.chamferSm)
    }
  }
}

struct CyberBadge: View {
  let text: String
  var color: Color = CyberTheme.accent

  var body: some View {
    Text(text.uppercased())
      .font(CyberFont.label)
      .tracking(1)
      .padding(.horizontal, 6)
      .padding(.vertical, 2)
      .foregroundStyle(color)
      .background(color.opacity(0.12))
      .overlay(
        RoundedRectangle(cornerRadius: 2)
          .stroke(color.opacity(0.5), lineWidth: 1)
      )
  }
}

struct CyberStatusRow: View {
  let label: String
  let value: String
  var color: Color = CyberTheme.foreground

  var body: some View {
    HStack {
      Text(label.uppercased())
        .font(CyberFont.label)
        .foregroundStyle(CyberTheme.mutedForeground)
        .tracking(1)
      Spacer()
      Text(value)
        .font(CyberFont.caption)
        .foregroundStyle(color)
    }
  }
}

struct CyberDivider: View {
  var body: some View {
    Rectangle()
      .fill(
        LinearGradient(
          colors: [.clear, CyberTheme.accent.opacity(0.4), .clear],
          startPoint: .leading,
          endPoint: .trailing
        )
      )
      .frame(height: 1)
  }
}

struct CyberSidebarTab: View {
  let title: String
  let symbol: String
  let isSelected: Bool

  var body: some View {
    HStack(spacing: 10) {
      Image(systemName: symbol)
        .font(.system(size: 14, weight: .semibold))
        .foregroundStyle(isSelected ? CyberTheme.accent : CyberTheme.mutedForeground)
        .frame(width: 18)
        .neonGlow(isSelected ? CyberTheme.accent : .clear, radius: 4)
      Text(title.uppercased())
        .font(CyberFont.label)
        .tracking(1.2)
        .foregroundStyle(isSelected ? CyberTheme.foreground : CyberTheme.mutedForeground)
      Spacer()
      if isSelected {
        Rectangle()
          .fill(CyberTheme.accent)
          .frame(width: 3, height: 14)
          .neonGlow()
      }
    }
    .padding(.horizontal, 10)
    .padding(.vertical, 8)
    .background(isSelected ? CyberTheme.accent.opacity(0.08) : .clear)
    .cyberChamferClip(CyberTheme.chamferSm)
  }
}

struct CyberPromptLine: View {
  let prefix: String
  let text: String
  var muted: Bool = false

  var body: some View {
    HStack(alignment: .top, spacing: 6) {
      Text(prefix)
        .font(CyberFont.caption)
        .foregroundStyle(CyberTheme.accent)
      Text(text)
        .font(CyberFont.caption)
        .foregroundStyle(muted ? CyberTheme.mutedForeground : CyberTheme.foreground)
        .fixedSize(horizontal: false, vertical: true)
        .textSelection(.enabled)
    }
  }
}

struct BlinkingCursor: View {
  @Environment(\.accessibilityReduceMotion) private var reduceMotion
  @State private var visible = true

  var body: some View {
    Rectangle()
      .fill(CyberTheme.accent)
      .frame(width: 8, height: 14)
      .opacity(visible ? 1 : 0)
      .neonGlow(radius: 3)
      .onAppear {
        guard !reduceMotion else { return }
        withAnimation(.easeInOut(duration: 0.5).repeatForever()) {
          visible.toggle()
        }
      }
  }
}
