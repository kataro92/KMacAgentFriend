import SwiftUI

// MARK: - Screen chrome

struct CyberScreenModifier: ViewModifier {
  func body(content: Content) -> some View {
    content
      .background(CyberTheme.background)
      .foregroundStyle(CyberTheme.foreground)
      .tint(CyberTheme.accent)
      .background(CyberGridBackground())
      .overlay(CyberScanlines().allowsHitTesting(false))
  }
}

struct CyberGridBackground: View {
  var body: some View {
    Canvas { context, size in
      let step: CGFloat = 50
      var path = Path()
      stride(from: 0, through: size.width, by: step).forEach { x in
        path.move(to: CGPoint(x: x, y: 0))
        path.addLine(to: CGPoint(x: x, y: size.height))
      }
      stride(from: 0, through: size.height, by: step).forEach { y in
        path.move(to: CGPoint(x: 0, y: y))
        path.addLine(to: CGPoint(x: size.width, y: y))
      }
      context.stroke(path, with: .color(CyberTheme.accent.opacity(0.04)), lineWidth: 1)
    }
    .ignoresSafeArea()
  }
}

struct CyberScanlines: View {
  var body: some View {
    Canvas { context, size in
      for y in stride(from: 0, to: size.height, by: 4) {
        let rect = CGRect(x: 0, y: y, width: size.width, height: 2)
        context.fill(Path(rect), with: .color(.black.opacity(0.22)))
      }
    }
    .ignoresSafeArea()
    .allowsHitTesting(false)
  }
}

// MARK: - Neon & glitch

struct NeonGlowModifier: ViewModifier {
  var color: Color
  var radius: CGFloat

  func body(content: Content) -> some View {
    content
      .shadow(color: color.opacity(0.9), radius: radius * 0.3)
      .shadow(color: color.opacity(0.5), radius: radius * 0.6)
      .shadow(color: color.opacity(0.25), radius: radius)
  }
}

struct CyberGlitchText: ViewModifier {
  @Environment(\.accessibilityReduceMotion) private var reduceMotion
  @State private var glitchPhase = false

  var enabled: Bool

  func body(content: Content) -> some View {
    content
      .overlay(alignment: .leading) {
        content
          .foregroundStyle(CyberTheme.accentSecondary)
          .opacity(0.55)
          .offset(x: glitchPhase ? -1.5 : -0.5, y: 0)
          .blendMode(.screen)
      }
      .overlay(alignment: .leading) {
        content
          .foregroundStyle(CyberTheme.accentTertiary)
          .opacity(0.55)
          .offset(x: glitchPhase ? 1.5 : 0.5, y: 0)
          .blendMode(.screen)
      }
      .onAppear {
        guard enabled, !reduceMotion else { return }
        withAnimation(.easeInOut(duration: 0.08).repeatForever(autoreverses: true).delay(2)) {
          glitchPhase.toggle()
        }
      }
  }
}

extension View {
  func cyberScreen() -> some View {
    modifier(CyberScreenModifier())
  }

  func neonGlow(_ color: Color = CyberTheme.accent, radius: CGFloat = 8) -> some View {
    modifier(NeonGlowModifier(color: color, radius: radius))
  }

  func cyberGlitchText(_ enabled: Bool = true) -> some View {
    modifier(CyberGlitchText(enabled: enabled))
  }

  func cyberChamferClip(_ cut: CGFloat = CyberTheme.chamfer) -> some View {
    clipShape(ChamferedRectangle(cut: cut))
  }
}
