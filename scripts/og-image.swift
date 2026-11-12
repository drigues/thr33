// Gera a imagem de partilha (Open Graph) em public/assets/og-image.png, 1200x630.
// Corre com: swift scripts/og-image.swift
import AppKit
import CoreText

let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
let fontURL = root.appendingPathComponent("public/assets/fonts/space-grotesk.ttf")
let outURL = root.appendingPathComponent("public/assets/og-image.png")

CTFontManagerRegisterFontsForURL(fontURL as CFURL, .process, nil)

let width = 1200, height = 630
let accent = NSColor(srgbRed: 0xE8 / 255, green: 0x87 / 255, blue: 0x3A / 255, alpha: 1)
let text = NSColor(srgbRed: 0xF4 / 255, green: 0xF4 / 255, blue: 0xF2 / 255, alpha: 1)
let dim = NSColor(srgbRed: 0xA3 / 255, green: 0xA3 / 255, blue: 0xA8 / 255, alpha: 1)

func font(_ size: CGFloat, weight: CGFloat) -> NSFont {
    let base = NSFontDescriptor(fontAttributes: [.family: "Space Grotesk"])
    let variation = NSFontDescriptor.AttributeName(rawValue: kCTFontVariationAttribute as String)
    let wght = 0x77676874 // 'wght'
    return NSFont(descriptor: base.addingAttributes([variation: [wght: weight]]), size: size)!
}

let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height, bitsPerSample: 8,
                           samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
                           bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
let ctx = NSGraphicsContext.current!.cgContext

// Fundo: o mesmo gradiente radial do site, do cinzento ao quase preto.
let space = CGColorSpace(name: CGColorSpace.sRGB)!
let gradient = CGGradient(colorsSpace: space, colors: [
    CGColor(srgbRed: 0x23 / 255, green: 0x23 / 255, blue: 0x27 / 255, alpha: 1),
    CGColor(srgbRed: 0x1C / 255, green: 0x1C / 255, blue: 0x20 / 255, alpha: 1),
    CGColor(srgbRed: 0x0B / 255, green: 0x0B / 255, blue: 0x0D / 255, alpha: 1),
] as CFArray, locations: [0, 0.4, 1])!
ctx.setFillColor(CGColor(srgbRed: 0x0B / 255, green: 0x0B / 255, blue: 0x0D / 255, alpha: 1))
ctx.fill(CGRect(x: 0, y: 0, width: width, height: height))
ctx.drawRadialGradient(gradient, startCenter: CGPoint(x: 600, y: 630), startRadius: 0,
                       endCenter: CGPoint(x: 600, y: 630), endRadius: 1100, options: [])

// Grelha de pontos discreta.
ctx.setFillColor(CGColor(gray: 1, alpha: 0.05))
for x in stride(from: 13, to: width, by: 26) {
    for y in stride(from: 13, to: height, by: 26) {
        ctx.fillEllipse(in: CGRect(x: x, y: y, width: 2, height: 2))
    }
}

func draw(_ string: String, at point: CGPoint, font: NSFont, color: NSColor, kern: CGFloat = 0) {
    NSAttributedString(string: string, attributes: [.font: font, .foregroundColor: color, .kern: kern]).draw(at: point)
}

let left: CGFloat = 96

// Selo "Digital Product Studio"
let badgeFont = NSFont.monospacedSystemFont(ofSize: 20, weight: .medium)
let badgeText = "DIGITAL PRODUCT STUDIO"
let badgeSize = NSAttributedString(string: badgeText, attributes: [.font: badgeFont, .kern: 4]).size()
let badge = CGRect(x: left, y: 420, width: badgeSize.width + 72, height: 52)
ctx.setStrokeColor(CGColor(gray: 1, alpha: 0.14))
ctx.setLineWidth(1.5)
ctx.addPath(CGPath(roundedRect: badge, cornerWidth: 26, cornerHeight: 26, transform: nil))
ctx.strokePath()
ctx.setFillColor(accent.cgColor)
ctx.fillEllipse(in: CGRect(x: left + 26, y: badge.midY - 5, width: 10, height: 10))
draw(badgeText, at: CGPoint(x: left + 50, y: badge.midY - badgeSize.height / 2), font: badgeFont, color: dim, kern: 4)

// Marca e frase
draw("Thr33 Labs", at: CGPoint(x: left - 6, y: 250), font: font(132, weight: 700), color: text, kern: -4)
let line = NSMutableAttributedString(string: "Digital products that people ", attributes: [.font: font(44, weight: 500), .foregroundColor: dim])
line.append(NSAttributedString(string: "use.", attributes: [.font: font(44, weight: 500), .foregroundColor: accent]))
line.draw(at: CGPoint(x: left, y: 170))

draw("thr33.xyz", at: CGPoint(x: left, y: 72), font: NSFont.monospacedSystemFont(ofSize: 24, weight: .regular), color: dim, kern: 2)

NSGraphicsContext.restoreGraphicsState()
try! rep.representation(using: .png, properties: [:])!.write(to: outURL)
print("Gerado \(outURL.path)")
