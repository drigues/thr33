// Passa SVG a PNG no tamanho pedido (o CoreSVG do macOS lê o SVG; a pixel art fica nítida porque a escala é inteira).
// Corre com: swift scripts/raster.swift <in.svg> <out.png> <largura> <altura> [<in.svg> <out.png> <l> <a> …]
// O scripts/art.py chama-o para as imagens-mestre da página Get It Vac (#59).
import AppKit

let args = Array(CommandLine.arguments.dropFirst())
precondition(args.count % 4 == 0, "argumentos: <in.svg> <out.png> <largura> <altura>, em grupos de 4")
for i in stride(from: 0, to: args.count, by: 4) {
    let image = NSImage(contentsOf: URL(fileURLWithPath: args[i]))!
    let width = Int(args[i + 2])!, height = Int(args[i + 3])!
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height, bitsPerSample: 8,
                               samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
                               bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    NSGraphicsContext.current!.imageInterpolation = .none
    image.draw(in: NSRect(x: 0, y: 0, width: width, height: height))
    NSGraphicsContext.restoreGraphicsState()
    try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: args[i + 1]))
    print("Gerado \(args[i + 1]) (\(width)×\(height))")
}
