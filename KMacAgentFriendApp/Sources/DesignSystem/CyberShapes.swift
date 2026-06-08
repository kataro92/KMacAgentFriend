import SwiftUI

/// Chamfered corner clip (45° cuts) — cyber panel silhouette.
struct ChamferedRectangle: Shape {
  var cut: CGFloat = CyberTheme.chamfer

  func path(in rect: CGRect) -> Path {
    let c = min(cut, min(rect.width, rect.height) / 4)
    var path = Path()
    path.move(to: CGPoint(x: rect.minX, y: rect.minY + c))
    path.addLine(to: CGPoint(x: rect.minX + c, y: rect.minY))
    path.addLine(to: CGPoint(x: rect.maxX - c, y: rect.minY))
    path.addLine(to: CGPoint(x: rect.maxX, y: rect.minY + c))
    path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY - c))
    path.addLine(to: CGPoint(x: rect.maxX - c, y: rect.maxY))
    path.addLine(to: CGPoint(x: rect.minX + c, y: rect.maxY))
    path.addLine(to: CGPoint(x: rect.minX, y: rect.maxY - c))
    path.closeSubpath()
    return path
  }
}

struct CyberCornerAccents: View {
  var color: Color = CyberTheme.accent.opacity(0.6)
  var length: CGFloat = 12
  var lineWidth: CGFloat = 1

  var body: some View {
    GeometryReader { geo in
      let w = geo.size.width
      let h = geo.size.height
      ZStack {
        corner(x: 0, y: 0, dx: length, dy: 0, dx2: 0, dy2: length)
        corner(x: w, y: 0, dx: -length, dy: 0, dx2: 0, dy2: length)
        corner(x: w, y: h, dx: -length, dy: 0, dx2: 0, dy2: -length)
        corner(x: 0, y: h, dx: length, dy: 0, dx2: 0, dy2: -length)
      }
    }
    .allowsHitTesting(false)
  }

  private func corner(x: CGFloat, y: CGFloat, dx: CGFloat, dy: CGFloat, dx2: CGFloat, dy2: CGFloat) -> some View {
    Path { path in
      path.move(to: CGPoint(x: x + dx, y: y + dy))
      path.addLine(to: CGPoint(x: x, y: y))
      path.addLine(to: CGPoint(x: x + dx2, y: y + dy2))
    }
    .stroke(color, lineWidth: lineWidth)
  }
}
