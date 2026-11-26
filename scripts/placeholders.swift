// Imagens provisórias do caso de estudo Get It Vac (#53), em src/images/get-it-vac/<nome>.png.
// Cada uma tem a largura maior do srcset e a proporção da imagem final (#54 troca-as pelas finais).
// Corre com: swift scripts/placeholders.swift  e depois  python3 scripts/images.py
import AppKit

let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
let dir = root.appendingPathComponent("src/images/get-it-vac")
try! FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)

func rgb(_ hex: Int) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
            blue: CGFloat(hex & 0xFF) / 255, alpha: 1)
}

// nome, largura, altura, fundo, frente (paleta do site: Tinta, Pedra, Lagoa, Atlântico, Telha, Cal)
let images: [(String, Int, Int, Int, Int)] = [
    ("hero", 2080, 1170, 0x121212, 0xE8552D),
    ("comando", 992, 744, 0x2C7564, 0xF3F0E8),
    ("multijogador", 992, 744, 0x3A3FD9, 0xF3F0E8),
    ("selfie", 480, 600, 0xE8552D, 0x121212),
    ("cartaz-ar", 480, 600, 0x6B675F, 0xF3F0E8),
    ("cartao", 928, 580, 0x121212, 0xE8552D),
]

for (name, width, height, bg, fg) in images {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height, bitsPerSample: 8,
                               samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
                               bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    let ctx = NSGraphicsContext.current!.cgContext
    ctx.setFillColor(rgb(bg))
    ctx.fill(CGRect(x: 0, y: 0, width: width, height: height))
    // Grelha de pixels, a lembrar a pixel art do jogo.
    let step = max(width, height) / 24
    ctx.setStrokeColor(rgb(fg).copy(alpha: 0.12)!)
    ctx.setLineWidth(CGFloat(max(1, width / 640)))
    for x in stride(from: 0, through: width, by: step) { ctx.move(to: CGPoint(x: x, y: 0)); ctx.addLine(to: CGPoint(x: x, y: height)) }
    for y in stride(from: 0, through: height, by: step) { ctx.move(to: CGPoint(x: 0, y: y)); ctx.addLine(to: CGPoint(x: width, y: y)) }
    ctx.strokePath()
    let color = NSColor(cgColor: rgb(fg))!
    let big = NSFont.monospacedSystemFont(ofSize: CGFloat(width) / 14, weight: .bold)
    let small = NSFont.monospacedSystemFont(ofSize: CGFloat(width) / 36, weight: .regular)
    let title = NSAttributedString(string: "GET IT VAC", attributes: [.font: big, .foregroundColor: color])
    let sub = NSAttributedString(string: "\(name) · \(width)×\(height) · placeholder",
                                 attributes: [.font: small, .foregroundColor: color.withAlphaComponent(0.75)])
    let t = title.size(), s = sub.size()
    title.draw(at: CGPoint(x: (CGFloat(width) - t.width) / 2, y: CGFloat(height) / 2))
    sub.draw(at: CGPoint(x: (CGFloat(width) - s.width) / 2, y: CGFloat(height) / 2 - s.height * 1.6))
    NSGraphicsContext.restoreGraphicsState()
    try! rep.representation(using: .png, properties: [:])!.write(to: dir.appendingPathComponent("\(name).png"))
    print("Gerado src/images/get-it-vac/\(name).png")
}
